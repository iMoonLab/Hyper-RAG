"""Backend selector and adapters for hypergraph storage.

This module centralizes how we instantiate and persist hypergraph-like
datastores so both the core library and the web UI can swap implementations
via configuration (for example, using TuGraph in place of the default
``hypergraph-db`` package).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, Any
import requests


class HypergraphDriver(Protocol):
    """Protocol describing the minimal API we need from a hypergraph backend."""

    name: str
    requires_local_file: bool

    def load_or_create(self, storage_file: str):
        """Load a hypergraph from ``storage_file`` if it exists, otherwise create a new one."""

    def save(self, hypergraph: Any, storage_file: str):
        """Persist the hypergraph to disk."""

    def clear_cache(self, hypergraph: Any):
        """Clear any cached properties on the hypergraph instance."""


@dataclass
class HypergraphDBDriver:
    """Driver that wraps the ``hypergraph-db`` package (``hyperdb`` module)."""

    name: str = "hypergraph-db"
    requires_local_file: bool = True

    def __post_init__(self):
        try:
            from hyperdb import HypergraphDB  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive import guard
            raise RuntimeError(
                "hypergraph-db backend is not available; install the 'hypergraph-db' package"
            ) from exc
        self._impl = HypergraphDB

    def load_or_create(self, storage_file: str):
        return self._impl(storage_file=storage_file)

    def save(self, hypergraph: Any, storage_file: str):
        hypergraph.save(storage_file)

    def clear_cache(self, hypergraph: Any):
        if hasattr(hypergraph, "_clear_cache"):
            hypergraph._clear_cache()


@dataclass
class TuGraphDriver:
    """Stub driver for TuGraph.

    The implementation can be extended to use a real TuGraph client; for now it
    raises a clear error if selected without the dependency.
    """

    name: str = "tugraph"
    requires_local_file: bool = False

    def __post_init__(self):  # pragma: no cover - optional dependency path
        try:
            import tugraph  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "TuGraph backend requested but the 'tugraph' package is not installed."
            ) from exc

    def load_or_create(self, storage_file: str):  # pragma: no cover - placeholder
        endpoint = os.environ.get("TUGRAPH_REST_ENDPOINT")
        graph = os.environ.get("TUGRAPH_REST_GRAPH", "default")
        username = os.environ.get("TUGRAPH_REST_USERNAME")
        password = os.environ.get("TUGRAPH_REST_PASSWORD")

        if not endpoint:
            raise RuntimeError(
                "TuGraph backend requires TUGRAPH_REST_ENDPOINT to point to the REST service."
            )

        return TuGraphRestClient(
            endpoint=endpoint,
            graph=graph,
            username=username,
            password=password,
        )

    def save(self, hypergraph: Any, storage_file: str):  # pragma: no cover - placeholder
        # TuGraph persists data on the remote service, so there is nothing to flush locally.
        return None

    def clear_cache(self, hypergraph: Any):  # pragma: no cover - placeholder
        # TuGraph implementations are expected to manage cache internally.
        return None


@dataclass
class TuGraphRestClient:
    """Lightweight REST client wrapper to talk to TuGraph via Cypher endpoints."""

    endpoint: str
    graph: str = "default"
    username: str | None = None
    password: str | None = None

    def _request(self, cypher: str) -> Any:
        payload = {"cypher": cypher, "graph": self.graph}
        auth = (self.username, self.password) if self.username else None
        response = requests.post(self.endpoint, json=payload, auth=auth, timeout=30)
        response.raise_for_status()
        return response.json()

    def run_cypher(self, cypher: str) -> Any:
        """Execute a Cypher statement against TuGraph via REST."""

        return self._request(cypher)

    def __getattr__(self, name: str):  # pragma: no cover - convenience guard
        raise NotImplementedError(
            "TuGraph REST client only supports raw Cypher via run_cypher; "
            f"operation '{name}' is not implemented in this adapter."
        )


def get_hypergraph_driver(preferred: str | None = None) -> HypergraphDriver:
    """Return a hypergraph driver implementation.

    The driver can be chosen via ``preferred`` or the ``HYPERRAG_HYPERGRAPH_BACKEND``
    environment variable. Defaults to ``hypergraph-db``.
    """

    backend = (preferred or os.environ.get("HYPERRAG_HYPERGRAPH_BACKEND", "")).strip()
    backend = backend or "hypergraph-db"
    normalized = backend.lower()

    if normalized in {"hypergraph-db", "hyperdb", "default"}:
        return HypergraphDBDriver()
    if normalized == "tugraph":
        return TuGraphDriver()

    raise ValueError(f"Unknown hypergraph backend '{backend}'")
