# Storage architecture

This project currently mixes two ways of accessing the hypergraph store:

* **`hyperrag/storage.py`** imports `HypergraphDB` from the `hypergraph-db` PyPI package (referenced in the root `requirements.txt`).
* **`web-ui/backend/db.py`** imports a vendored `hyperdb` package that lives under `web-ui/backend/hyperdb` and calls its APIs directly.

Because `db.py` bypasses the storage abstraction defined in `hyperrag.storage.HypergraphStorage`, it is tightly coupled to the HypergraphDB API surface. That tight coupling makes swapping in another backend (for example, a TuGraph-based store) error prone: every direct call has to be revisited.

## Implemented adapter layer

* `hyperrag/hypergraph_backend.py` now exposes a `get_hypergraph_driver` selector and a `HypergraphDriver` protocol. The default driver wraps the PyPI `hypergraph-db` package, while the TuGraph driver targets a **remote** REST endpoint (via `TUGRAPH_REST_ENDPOINT` rather than a local file) and exposes a `run_cypher` helper for Cypher queries.
* `hyperrag/storage.py` and `web-ui/backend/db.py` both rely on this selector, so toggling `HYPERRAG_HYPERGRAPH_BACKEND=tugraph` (or adding a new driver) switches the backing store without touching call sites. File existence checks are skipped for TuGraph because it is not file-backed.

This keeps backend-specific code confined to the adapter module and lets the rest of the project use the stable hypergraph API surface.
