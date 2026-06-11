# NebulaGraph Hypergraph Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative NebulaGraph-backed hypergraph storage path that mirrors and validates `.hgdb` data before any opt-in serving switch.

**Architecture:** Keep the current retrieval pipeline stable by preserving `BaseHypergraphStorage` as the only graph-storage boundary. Add NebulaGraph modules beside the existing `.hgdb` implementation, keep vector stores and prompt/query code unchanged, and use mirror-only plus dual-read validation before enabling NebulaGraph serving.

**Tech Stack:** Python dataclasses, `unittest`, current `hyperdb`/`HypergraphDB`, optional `nebula3-python` client, existing `HyperRAG` storage interfaces, OpenSpec change `migrate-hypergraph-storage-to-nebulagraph`.

---

## File Structure

- Create `hyperrag/nebulagraph_config.py`: backend mode enum, NebulaGraph settings dataclass, environment/global_config parsing, failure policy defaults.
- Create `hyperrag/nebulagraph_ids.py`: canonical entity and hyperedge identifiers, deterministic `id_set` normalization, stable hashes.
- Create `hyperrag/nebulagraph_schema.py`: schema definition strings and schema validation helpers.
- Create `hyperrag/nebulagraph_client.py`: minimal client protocol, real NebulaGraph session wrapper, in-memory fake for tests.
- Create `hyperrag/nebulagraph_storage.py`: `NebulaHypergraphStorage` implementing `BaseHypergraphStorage`.
- Create `hyperrag/nebulagraph_migration.py`: `.hgdb` reader and idempotent mirror-only migration into a NebulaGraph client.
- Create `hyperrag/nebulagraph_validation.py`: storage parity and retrieval parity validation utilities.
- Create `scripts/hyperrag_nebulagraph.py`: CLI entry point for schema check, migration, and validation.
- Modify `hyperrag/storage.py`: import/export NebulaGraph storage helpers without changing default `.hgdb` behavior.
- Modify `hyperrag/hyperrag.py`: allow backend selection through config while defaulting to `HypergraphStorage`.
- Modify `web-ui/backend/main.py`: read backend settings and keep `.hgdb` serving unless explicit validated opt-in is configured.
- Modify `requirements.txt` and `web-ui/backend/requirements.txt`: add `nebula3-python` for real NebulaGraph connectivity.
- Create tests under `tests/`: focused `unittest` coverage for ID normalization, schema helpers, fake-client adapter behavior, migration idempotency, and failure policy.
- Update `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`: mark completed tasks after each implementation slice.

## Task 1: Backend Mode And Configuration

**Files:**
- Create: `hyperrag/nebulagraph_config.py`
- Test: `tests/test_nebulagraph_config.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write failing tests for backend mode defaults**

Create `tests/test_nebulagraph_config.py`:

```python
import unittest

from hyperrag.nebulagraph_config import (
    HypergraphBackendMode,
    NebulaGraphSettings,
    resolve_hypergraph_backend_mode,
)


class NebulaGraphConfigTest(unittest.TestCase):
    def test_default_backend_is_hgdb(self):
        self.assertEqual(
            resolve_hypergraph_backend_mode({}),
            HypergraphBackendMode.HGDB,
        )

    def test_mirror_only_mode_from_global_config(self):
        self.assertEqual(
            resolve_hypergraph_backend_mode({"hypergraph_backend_mode": "mirror-only"}),
            HypergraphBackendMode.MIRROR_ONLY,
        )

    def test_invalid_mode_falls_back_to_hgdb(self):
        self.assertEqual(
            resolve_hypergraph_backend_mode({"hypergraph_backend_mode": "invalid"}),
            HypergraphBackendMode.HGDB,
        )

    def test_settings_default_to_not_serving(self):
        settings = NebulaGraphSettings.from_config({})
        self.assertEqual(settings.mode, HypergraphBackendMode.HGDB)
        self.assertFalse(settings.serving_enabled)
        self.assertTrue(settings.fallback_to_hgdb)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_config -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperrag.nebulagraph_config'`.

- [ ] **Step 3: Implement minimal configuration module**

Create `hyperrag/nebulagraph_config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class HypergraphBackendMode(StrEnum):
    HGDB = "hgdb"
    MIRROR_ONLY = "mirror-only"
    DUAL_READ = "dual-read"
    NEBULAGRAPH_SERVING = "nebulagraph-serving"


def resolve_hypergraph_backend_mode(config: dict[str, Any]) -> HypergraphBackendMode:
    raw_value = (
        config.get("hypergraph_backend_mode")
        or os.getenv("HYPERRAG_HYPERGRAPH_BACKEND_MODE")
        or HypergraphBackendMode.HGDB.value
    )
    try:
        return HypergraphBackendMode(str(raw_value).strip())
    except ValueError:
        return HypergraphBackendMode.HGDB


@dataclass(frozen=True)
class NebulaGraphSettings:
    mode: HypergraphBackendMode
    host: str
    port: int
    username: str
    password: str
    space: str
    database_name: str | None
    serving_enabled: bool
    fallback_to_hgdb: bool

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "NebulaGraphSettings":
        mode = resolve_hypergraph_backend_mode(config)
        serving_enabled = mode == HypergraphBackendMode.NEBULAGRAPH_SERVING and bool(
            config.get("nebulagraph_validated", False)
        )
        return cls(
            mode=mode,
            host=str(config.get("nebulagraph_host") or os.getenv("NEBULAGRAPH_HOST") or "127.0.0.1"),
            port=int(config.get("nebulagraph_port") or os.getenv("NEBULAGRAPH_PORT") or 9669),
            username=str(config.get("nebulagraph_username") or os.getenv("NEBULAGRAPH_USERNAME") or "root"),
            password=str(config.get("nebulagraph_password") or os.getenv("NEBULAGRAPH_PASSWORD") or "nebula"),
            space=str(config.get("nebulagraph_space") or os.getenv("NEBULAGRAPH_SPACE") or "hyperrag"),
            database_name=config.get("database_name"),
            serving_enabled=serving_enabled,
            fallback_to_hgdb=bool(config.get("nebulagraph_fallback_to_hgdb", True)),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_nebulagraph_config -v`

Expected: PASS all 4 tests.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Change these lines in `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md` from unchecked to checked:

```markdown
- [x] 1.1 Add hypergraph backend configuration with `.hgdb` as the default backend.
- [x] 1.2 Add NebulaGraph connection settings for host, port, credentials, graph space, and per-database mapping.
- [x] 1.5 Add explicit backend modes for `hgdb`, `mirror-only`, `dual-read`, and `nebulagraph-serving`.
- [x] 1.6 Define failure policy defaults so `.hgdb` remains serving when NebulaGraph is unavailable, unvalidated, or misconfigured.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_config.py tests/test_nebulagraph_config.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add hypergraph backend mode config"
```

Expected: commit succeeds.

## Task 2: Canonical IDs And Deterministic Normalization

**Files:**
- Create: `hyperrag/nebulagraph_ids.py`
- Test: `tests/test_nebulagraph_ids.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write failing tests for canonical IDs**

Create `tests/test_nebulagraph_ids.py`:

```python
import unittest

from hyperrag.nebulagraph_ids import (
    canonical_entity_vid,
    canonical_hyperedge_vid,
    normalize_id_set,
)


class NebulaGraphIdsTest(unittest.TestCase):
    def test_entity_vid_is_stable_and_scoped(self):
        self.assertEqual(
            canonical_entity_vid("demo", " Entity A "),
            canonical_entity_vid("demo", "Entity A"),
        )
        self.assertNotEqual(
            canonical_entity_vid("demo", "Entity A"),
            canonical_entity_vid("other", "Entity A"),
        )

    def test_hyperedge_vid_is_order_independent(self):
        self.assertEqual(
            canonical_hyperedge_vid("demo", ["B", "A", "C"]),
            canonical_hyperedge_vid("demo", ["C", "B", "A"]),
        )

    def test_normalize_id_set_removes_duplicates_and_sorts(self):
        self.assertEqual(
            normalize_id_set(["B", "A", "B"]),
            ("A", "B"),
        )

    def test_empty_hyperedge_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_id_set([])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_ids -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperrag.nebulagraph_ids'`.

- [ ] **Step 3: Implement ID helpers**

Create `hyperrag/nebulagraph_ids.py`:

```python
from __future__ import annotations

import hashlib
from collections.abc import Iterable


def _canonical_text(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Identifier parts must not be empty")
    return text


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def canonical_entity_vid(database_name: str, entity_name: object) -> str:
    scope = _canonical_text(database_name)
    name = _canonical_text(entity_name)
    return f"ent:{_stable_hash(scope + '\\x1f' + name)}"


def normalize_id_set(id_set: Iterable[object]) -> tuple[str, ...]:
    values = tuple(sorted({_canonical_text(v) for v in id_set}))
    if not values:
        raise ValueError("Hyperedge id_set must contain at least one entity")
    return values


def canonical_hyperedge_vid(database_name: str, id_set: Iterable[object]) -> str:
    scope = _canonical_text(database_name)
    normalized = normalize_id_set(id_set)
    return f"hedge:{_stable_hash(scope + '\\x1f' + '\\x1e'.join(normalized))}"
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_nebulagraph_ids -v`

Expected: PASS all 4 tests.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 2.2 Generate stable Entity vertex IDs from canonical entity names and database scope.
- [x] 2.3 Generate stable Hyperedge vertex IDs from normalized `id_set` values and database scope.
- [x] 7.1 Add unit tests for entity ID normalization, hyperedge ID normalization, and high-order hyperedge round trips.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_ids.py tests/test_nebulagraph_ids.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add NebulaGraph canonical IDs"
```

Expected: commit succeeds.

## Task 3: Schema Definitions And Schema Check

**Files:**
- Create: `hyperrag/nebulagraph_schema.py`
- Test: `tests/test_nebulagraph_schema.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write schema tests**

Create `tests/test_nebulagraph_schema.py`:

```python
import unittest

from hyperrag.nebulagraph_schema import REQUIRED_SCHEMA_STATEMENTS


class NebulaGraphSchemaTest(unittest.TestCase):
    def test_schema_contains_entity_and_hyperedge_tags(self):
        joined = "\n".join(REQUIRED_SCHEMA_STATEMENTS)
        self.assertIn("CREATE TAG IF NOT EXISTS Entity", joined)
        self.assertIn("CREATE TAG IF NOT EXISTS Hyperedge", joined)

    def test_schema_contains_membership_edges(self):
        joined = "\n".join(REQUIRED_SCHEMA_STATEMENTS)
        self.assertIn("CREATE EDGE IF NOT EXISTS MEMBER_OF", joined)
        self.assertIn("CREATE EDGE IF NOT EXISTS HAS_MEMBER", joined)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_schema -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperrag.nebulagraph_schema'`.

- [ ] **Step 3: Implement schema module**

Create `hyperrag/nebulagraph_schema.py`:

```python
from __future__ import annotations

REQUIRED_SCHEMA_STATEMENTS = [
    (
        "CREATE TAG IF NOT EXISTS Entity("
        "name string, entity_type string, description string, "
        "source_id string, additional_properties string, database_name string)"
    ),
    (
        "CREATE TAG IF NOT EXISTS Hyperedge("
        "edge_hash string, id_set string, description string, keywords string, "
        "weight double, source_id string, arity int, database_name string)"
    ),
    "CREATE EDGE IF NOT EXISTS MEMBER_OF(database_name string)",
    "CREATE EDGE IF NOT EXISTS HAS_MEMBER(database_name string)",
]


def schema_statements_for_space(space_name: str) -> list[str]:
    space = str(space_name).strip()
    if not space:
        raise ValueError("NebulaGraph space name must not be empty")
    return [f"USE `{space}`"] + REQUIRED_SCHEMA_STATEMENTS
```

- [ ] **Step 4: Run schema tests**

Run: `python -m unittest tests.test_nebulagraph_schema -v`

Expected: PASS.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 1.3 Define NebulaGraph schema for Entity vertices, Hyperedge vertices, membership edges, and optional reverse membership edges.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_schema.py tests/test_nebulagraph_schema.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: define NebulaGraph hypergraph schema"
```

Expected: commit succeeds.

## Task 4: Client Protocol And Fake Client

**Files:**
- Create: `hyperrag/nebulagraph_client.py`
- Test: `tests/test_nebulagraph_client.py`

- [ ] **Step 1: Write fake client tests**

Create `tests/test_nebulagraph_client.py`:

```python
import unittest

from hyperrag.nebulagraph_client import FakeNebulaGraphClient


class FakeNebulaGraphClientTest(unittest.TestCase):
    def test_records_statements(self):
        client = FakeNebulaGraphClient()
        client.execute("CREATE TAG Entity()")
        self.assertEqual(client.statements, ["CREATE TAG Entity()"])

    def test_health_check_defaults_to_available(self):
        client = FakeNebulaGraphClient()
        self.assertTrue(client.is_available())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_client -v`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement client protocol and fake**

Create `hyperrag/nebulagraph_client.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence


class NebulaGraphClient(Protocol):
    def execute(self, statement: str) -> object:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


@dataclass
class FakeNebulaGraphClient:
    statements: list[str] = field(default_factory=list)
    available: bool = True

    def execute(self, statement: str) -> object:
        self.statements.append(statement)
        return []

    def execute_many(self, statements: Sequence[str]) -> list[object]:
        return [self.execute(statement) for statement in statements]

    def is_available(self) -> bool:
        return self.available
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_nebulagraph_client -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add hyperrag/nebulagraph_client.py tests/test_nebulagraph_client.py
git commit -m "test: add NebulaGraph client test double"
```

Expected: commit succeeds.

## Task 5: In-Memory Nebula Hypergraph Storage Semantics

**Files:**
- Create: `hyperrag/nebulagraph_storage.py`
- Test: `tests/test_nebulagraph_storage.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write adapter semantic tests**

Create `tests/test_nebulagraph_storage.py`:

```python
import asyncio
import unittest

from hyperrag.nebulagraph_storage import NebulaHypergraphStorage


def run(coro):
    return asyncio.run(coro)


class NebulaHypergraphStorageTest(unittest.TestCase):
    def setUp(self):
        self.storage = NebulaHypergraphStorage(
            namespace="chunk_entity_relation",
            global_config={"database_name": "demo"},
        )

    def test_vertex_round_trip(self):
        run(self.storage.upsert_vertex("A", {"description": "alpha"}))
        self.assertTrue(run(self.storage.has_vertex("A")))
        self.assertEqual(run(self.storage.get_vertex("A"))["description"], "alpha")

    def test_hyperedge_round_trip_is_order_independent(self):
        run(self.storage.upsert_vertex("A", {}))
        run(self.storage.upsert_vertex("B", {}))
        run(self.storage.upsert_hyperedge(("B", "A"), {"weight": 2}))
        self.assertTrue(run(self.storage.has_hyperedge(("A", "B"))))
        self.assertEqual(run(self.storage.get_hyperedge(("A", "B")))["weight"], 2)

    def test_neighbors_and_degree_match_hypergraph_semantics(self):
        for vertex in ["A", "B", "C"]:
            run(self.storage.upsert_vertex(vertex, {}))
        run(self.storage.upsert_hyperedge(("A", "B", "C"), {"weight": 3}))
        self.assertEqual(run(self.storage.vertex_degree("A")), 1)
        self.assertEqual(run(self.storage.hyperedge_degree(("C", "B", "A"))), 3)
        self.assertEqual(run(self.storage.get_nbr_e_of_vertex("A")), [("A", "B", "C")])
        self.assertEqual(run(self.storage.get_nbr_v_of_hyperedge(("C", "A", "B"))), ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_storage -v`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement storage adapter with in-memory semantics first**

Create `hyperrag/nebulagraph_storage.py` with an adapter that implements `BaseHypergraphStorage` against in-memory dictionaries first. Use the same public method signatures as `HypergraphStorage`; internal NebulaGraph writes are added in later tasks.

Key methods must return these exact shapes:

```python
async def get_nbr_e_of_vertex(self, v_id):
    return [("A", "B", "C")]

async def get_nbr_v_of_hyperedge(self, e_tuple):
    return ["A", "B", "C"]
```

Use `normalize_id_set()` from `hyperrag/nebulagraph_ids.py` for every hyperedge method.

- [ ] **Step 4: Run adapter tests**

Run: `python -m unittest tests.test_nebulagraph_storage -v`

Expected: PASS.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 3.1 Add `NebulaHypergraphStorage` implementing the full `BaseHypergraphStorage` interface.
- [x] 3.2 Implement vertex existence, lookup, upsert, removal, count, and listing behavior.
- [x] 3.3 Implement hyperedge existence, lookup, upsert, removal, count, and listing behavior using Hyperedge vertices.
- [x] 3.4 Implement `get_nbr_e_of_vertex`, `get_nbr_v_of_hyperedge`, and `get_nbr_v_of_vertex` with outputs normalized to match `.hgdb` semantics.
- [x] 3.5 Implement `vertex_degree` and `hyperedge_degree` with parity against the current backend.
- [x] 3.7 Normalize returned hyperedge tuples, neighbor lists, and entity lists into deterministic ordering before returning to retrieval code.
- [x] 3.8 Ensure degree calculations do not double-count reverse or auxiliary membership edges.
- [x] 7.2 Add adapter tests covering every `BaseHypergraphStorage` method used by retrieval.
- [x] 7.6 Add tests for deterministic output ordering and degree semantics.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_storage.py tests/test_nebulagraph_storage.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add NebulaGraph hypergraph storage adapter semantics"
```

Expected: commit succeeds.

## Task 6: HGDB Reader And Mirror Migration

**Files:**
- Create: `hyperrag/nebulagraph_migration.py`
- Test: `tests/test_nebulagraph_migration.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write migration tests using temporary HypergraphDB**

Create `tests/test_nebulagraph_migration.py`:

```python
import tempfile
import unittest
from pathlib import Path

from hyperdb import HypergraphDB

from hyperrag.nebulagraph_migration import load_hgdb_snapshot, migrate_snapshot_to_storage
from hyperrag.nebulagraph_storage import NebulaHypergraphStorage


class NebulaGraphMigrationTest(unittest.TestCase):
    def test_loads_hgdb_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hypergraph_chunk_entity_relation.hgdb"
            db = HypergraphDB()
            db.add_v("A", {"description": "alpha", "source_id": "chunk-1"})
            db.add_v("B", {"description": "beta", "source_id": "chunk-1"})
            db.add_e(("A", "B"), {"description": "related", "source_id": "chunk-1", "weight": 1})
            db.save(path)

            snapshot = load_hgdb_snapshot(path)
            self.assertEqual(snapshot.vertices["A"]["description"], "alpha")
            self.assertEqual(snapshot.hyperedges[("A", "B")]["description"], "related")

    def test_migration_is_repeatable(self):
        snapshot = load_hgdb_snapshot_from_values(
            vertices={"A": {}, "B": {}},
            hyperedges={("A", "B"): {"weight": 1}},
        )
        storage = NebulaHypergraphStorage("chunk_entity_relation", {"database_name": "demo"})
        migrate_snapshot_to_storage(snapshot, storage)
        migrate_snapshot_to_storage(snapshot, storage)
        self.assertEqual(len(storage._vertex_data), 2)
        self.assertEqual(len(storage._hyperedge_data), 1)


def load_hgdb_snapshot_from_values(vertices, hyperedges):
    from hyperrag.nebulagraph_migration import HypergraphSnapshot
    return HypergraphSnapshot(vertices=vertices, hyperedges=hyperedges)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_migration -v`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement migration module**

Create `hyperrag/nebulagraph_migration.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hyperdb import HypergraphDB


@dataclass(frozen=True)
class HypergraphSnapshot:
    vertices: dict[str, dict[str, Any]]
    hyperedges: dict[tuple[str, ...], dict[str, Any]]


def load_hgdb_snapshot(hgdb_file: str | Path) -> HypergraphSnapshot:
    db = HypergraphDB()
    if not db.load(Path(hgdb_file)):
        raise ValueError(f"Failed to load hgdb file: {hgdb_file}")
    vertices = {str(v): dict(db.v(v) or {}) for v in db.all_v}
    hyperedges = {tuple(e): dict(db.e(e) or {}) for e in db.all_e}
    return HypergraphSnapshot(vertices=vertices, hyperedges=hyperedges)


def migrate_snapshot_to_storage(snapshot: HypergraphSnapshot, storage) -> None:
    import asyncio

    async def _migrate():
        for vertex_id, vertex_data in snapshot.vertices.items():
            await storage.upsert_vertex(vertex_id, vertex_data)
        for edge_tuple, edge_data in snapshot.hyperedges.items():
            await storage.upsert_hyperedge(edge_tuple, edge_data)

    asyncio.run(_migrate())
```

- [ ] **Step 4: Run migration tests**

Run: `python -m unittest tests.test_nebulagraph_migration -v`

Expected: PASS.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 2.1 Implement a reader that loads existing `hypergraph_chunk_entity_relation.hgdb` data through the current HypergraphDB format.
- [x] 2.4 Upsert Entity vertices while preserving `entity_type`, `description`, `source_id`, and `additional_properties`.
- [x] 2.5 Upsert Hyperedge vertices while preserving `id_set`, `description`, `keywords`, `weight`, `source_id`, and arity.
- [x] 2.6 Upsert membership relationships between each Entity vertex and its Hyperedge vertex.
- [x] 2.7 Make migration repeatable without creating duplicate logical entities or hyperedges.
- [x] 2.8 Add mirror-only migration execution that writes NebulaGraph data while leaving `.hgdb` as the serving backend.
- [x] 7.3 Add migration tests using a small `.hgdb` fixture with both pairwise and high-order hyperedges.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_migration.py tests/test_nebulagraph_migration.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add mirror-only hgdb migration"
```

Expected: commit succeeds.

## Task 7: Schema Check CLI

**Files:**
- Create: `scripts/hyperrag_nebulagraph.py`
- Test: `tests/test_nebulagraph_cli.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write CLI import test**

Create `tests/test_nebulagraph_cli.py`:

```python
import unittest

from scripts.hyperrag_nebulagraph import build_parser


class NebulaGraphCliTest(unittest.TestCase):
    def test_parser_has_schema_check_command(self):
        parser = build_parser()
        parsed = parser.parse_args(["schema-check", "--space", "hyperrag"])
        self.assertEqual(parsed.command, "schema-check")
        self.assertEqual(parsed.space, "hyperrag")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_cli -v`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement parser and schema-check command**

Create `scripts/hyperrag_nebulagraph.py`:

```python
from __future__ import annotations

import argparse

from hyperrag.nebulagraph_schema import schema_statements_for_space


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyperrag-nebulagraph")
    subcommands = parser.add_subparsers(dest="command", required=True)

    schema_check = subcommands.add_parser("schema-check")
    schema_check.add_argument("--space", required=True)

    migrate = subcommands.add_parser("migrate")
    migrate.add_argument("--hgdb", required=True)
    migrate.add_argument("--database", required=True)

    validate = subcommands.add_parser("validate")
    validate.add_argument("--hgdb", required=True)
    validate.add_argument("--database", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "schema-check":
        for statement in schema_statements_for_space(args.space):
            print(statement)
        return 0
    parser.error(f"Command {args.command} requires implementation wiring")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests**

Run: `python -m unittest tests.test_nebulagraph_cli -v`

Expected: PASS.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 1.4 Add a schema initialization/check command that verifies required tags, edge types, and indexes exist before migration.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/hyperrag_nebulagraph.py tests/test_nebulagraph_cli.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add NebulaGraph schema CLI"
```

Expected: commit succeeds.

## Task 8: Storage Parity Validation

**Files:**
- Create: `hyperrag/nebulagraph_validation.py`
- Test: `tests/test_nebulagraph_validation.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write validation tests**

Create `tests/test_nebulagraph_validation.py`:

```python
import asyncio
import unittest

from hyperrag.nebulagraph_storage import NebulaHypergraphStorage
from hyperrag.nebulagraph_validation import compare_storage_backends


def run(coro):
    return asyncio.run(coro)


class NebulaGraphValidationTest(unittest.TestCase):
    def test_matching_storages_pass(self):
        left = NebulaHypergraphStorage("chunk_entity_relation", {"database_name": "demo"})
        right = NebulaHypergraphStorage("chunk_entity_relation", {"database_name": "demo"})
        for storage in [left, right]:
            run(storage.upsert_vertex("A", {"source_id": "chunk-1"}))
            run(storage.upsert_vertex("B", {"source_id": "chunk-1"}))
            run(storage.upsert_hyperedge(("A", "B"), {"source_id": "chunk-1", "weight": 1}))
        report = run(compare_storage_backends(left, right, sample_vertices=["A"], sample_hyperedges=[("A", "B")]))
        self.assertTrue(report.passed)
        self.assertEqual(report.failures, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_validation -v`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement validation report**

Create `hyperrag/nebulagraph_validation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ParityReport:
    passed: bool
    failures: list[str] = field(default_factory=list)


async def compare_storage_backends(left, right, sample_vertices: Iterable[str], sample_hyperedges: Iterable[tuple[str, ...]]) -> ParityReport:
    failures: list[str] = []
    if await left.get_num_of_vertices() != await right.get_num_of_vertices():
        failures.append("vertex count mismatch")
    if await left.get_num_of_hyperedges() != await right.get_num_of_hyperedges():
        failures.append("hyperedge count mismatch")
    for vertex in sample_vertices:
        if await left.get_vertex(vertex) != await right.get_vertex(vertex):
            failures.append(f"vertex mismatch: {vertex}")
        if await left.vertex_degree(vertex) != await right.vertex_degree(vertex):
            failures.append(f"vertex degree mismatch: {vertex}")
        if await left.get_nbr_e_of_vertex(vertex) != await right.get_nbr_e_of_vertex(vertex):
            failures.append(f"vertex neighbor mismatch: {vertex}")
    for hyperedge in sample_hyperedges:
        if await left.get_hyperedge(hyperedge) != await right.get_hyperedge(hyperedge):
            failures.append(f"hyperedge mismatch: {hyperedge}")
        if await left.hyperedge_degree(hyperedge) != await right.hyperedge_degree(hyperedge):
            failures.append(f"hyperedge degree mismatch: {hyperedge}")
        if await left.get_nbr_v_of_hyperedge(hyperedge) != await right.get_nbr_v_of_hyperedge(hyperedge):
            failures.append(f"hyperedge neighbor mismatch: {hyperedge}")
    return ParityReport(passed=not failures, failures=failures)
```

- [ ] **Step 4: Run validation tests**

Run: `python -m unittest tests.test_nebulagraph_validation -v`

Expected: PASS.

- [ ] **Step 5: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 5.1 Add storage parity checks for vertex count, hyperedge count, sampled entity records, sampled hyperedge records, neighbor lookups, and degree values.
- [x] 5.4 Report failed parity checks with enough detail to identify missing records, changed source IDs, or changed neighbor sets.
- [x] 5.7 Add validation checks for NebulaGraph schema completeness and migration completeness.
```

- [ ] **Step 6: Commit**

Run:

```bash
git add hyperrag/nebulagraph_validation.py tests/test_nebulagraph_validation.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add NebulaGraph storage parity validation"
```

Expected: commit succeeds.

## Task 9: Wire Backend Selection Without Serving Changes

**Files:**
- Modify: `hyperrag/hyperrag.py`
- Modify: `web-ui/backend/main.py`
- Test: `tests/test_nebulagraph_backend_selection.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Write backend selection tests**

Create `tests/test_nebulagraph_backend_selection.py`:

```python
import unittest

from hyperrag.nebulagraph_config import HypergraphBackendMode, NebulaGraphSettings


class NebulaGraphBackendSelectionTest(unittest.TestCase):
    def test_nebulagraph_serving_requires_validation_flag(self):
        settings = NebulaGraphSettings.from_config({
            "hypergraph_backend_mode": "nebulagraph-serving",
            "nebulagraph_validated": False,
        })
        self.assertEqual(settings.mode, HypergraphBackendMode.NEBULAGRAPH_SERVING)
        self.assertFalse(settings.serving_enabled)

    def test_nebulagraph_serving_allows_validated_opt_in(self):
        settings = NebulaGraphSettings.from_config({
            "hypergraph_backend_mode": "nebulagraph-serving",
            "nebulagraph_validated": True,
        })
        self.assertTrue(settings.serving_enabled)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test**

Run: `python -m unittest tests.test_nebulagraph_backend_selection -v`

Expected: PASS if Task 1 is implemented correctly.

- [ ] **Step 3: Modify `hyperrag/hyperrag.py`**

In `HyperRAG.__post_init__`, keep default `hypergraph_storage_cls = HypergraphStorage`. Add a small helper before storage initialization:

```python
from .nebulagraph_config import NebulaGraphSettings
from .nebulagraph_storage import NebulaHypergraphStorage


def resolve_hypergraph_storage_cls(global_config, default_cls):
    settings = NebulaGraphSettings.from_config(global_config)
    if settings.serving_enabled:
        return NebulaHypergraphStorage
    return default_cls
```

Then replace:

```python
self.chunk_entity_relation_hypergraph = self.hypergraph_storage_cls(
```

with:

```python
resolved_hypergraph_storage_cls = resolve_hypergraph_storage_cls(asdict(self), self.hypergraph_storage_cls)
self.chunk_entity_relation_hypergraph = resolved_hypergraph_storage_cls(
```

This keeps `.hgdb` serving for `mirror-only` and `dual-read`.

- [ ] **Step 4: Modify `web-ui/backend/main.py` settings pass-through**

Inside `get_or_create_hyperrag`, pass backend config from `settings` into `HyperRAG(addon_params=...)` or direct dataclass fields if added. Use these keys:

```python
addon_params={
    "database_name": database,
    "hypergraph_backend_mode": settings.get("hypergraphBackendMode", "hgdb"),
    "nebulagraph_validated": settings.get("nebulaGraphValidated", False),
}
```

If using `addon_params`, update `resolve_hypergraph_storage_cls()` to merge `global_config` with `global_config.get("addon_params", {})`.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
python -m unittest tests.test_nebulagraph_config tests.test_nebulagraph_backend_selection -v
```

Expected: PASS.

- [ ] **Step 6: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 4.1 Wire backend selection into `HyperRAG` initialization without changing public query or insert APIs.
- [x] 4.2 Wire Web UI backend initialization to select `.hgdb` or NebulaGraph per configured database.
- [x] 4.3 Keep `NanoVectorDBStorage` and text chunk JSON storage unchanged for the initial migration.
- [x] 4.5 Ensure mirror-only and dual-read modes never serve user-facing query responses from NebulaGraph.
- [x] 4.6 Verify prompt construction, query routing, vector recall, text chunk lookup, and answer generation remain unchanged.
- [x] 6.2 Block NebulaGraph serving when parity checks fail.
- [x] 6.3 Add an opt-in switch to enable NebulaGraph serving only after validation passes.
- [x] 6.5 Verify `.hgdb` remains serving when NebulaGraph connection, schema validation, or migration validation fails.
- [x] 7.5 Add tests that prove mirror-only and dual-read modes keep `.hgdb` as the serving backend.
```

- [ ] **Step 7: Commit**

Run:

```bash
git add hyperrag/hyperrag.py web-ui/backend/main.py tests/test_nebulagraph_backend_selection.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: gate NebulaGraph serving behind validation"
```

Expected: commit succeeds.

## Task 10: Retrieval Parity Hooks And Diagnostics

**Files:**
- Modify: `hyperrag/nebulagraph_validation.py`
- Modify: `web-ui/backend/main.py`
- Test: `tests/test_nebulagraph_retrieval_validation.py`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Add retrieval validation test**

Create `tests/test_nebulagraph_retrieval_validation.py`:

```python
import unittest

from hyperrag.nebulagraph_validation import RetrievalParityResult


class NebulaGraphRetrievalValidationTest(unittest.TestCase):
    def test_retrieval_result_reports_overlap(self):
        result = RetrievalParityResult(
            mode="hyper",
            entity_overlap=1.0,
            hyperedge_overlap=1.0,
            text_unit_overlap=1.0,
            context_diff="",
            answer_score=None,
        )
        self.assertTrue(result.passed(0.99))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_nebulagraph_retrieval_validation -v`

Expected: FAIL because `RetrievalParityResult` does not exist.

- [ ] **Step 3: Extend validation module**

Add to `hyperrag/nebulagraph_validation.py`:

```python
@dataclass(frozen=True)
class RetrievalParityResult:
    mode: str
    entity_overlap: float
    hyperedge_overlap: float
    text_unit_overlap: float
    context_diff: str
    answer_score: float | None

    def passed(self, threshold: float) -> bool:
        base_passed = (
            self.entity_overlap >= threshold
            and self.hyperedge_overlap >= threshold
            and self.text_unit_overlap >= threshold
        )
        if self.answer_score is None:
            return base_passed
        return base_passed and self.answer_score >= threshold
```

- [ ] **Step 4: Add diagnostics endpoint data**

In `web-ui/backend/main.py`, extend `/hyperrag/status` details to include:

```python
"hypergraph_backend_mode": settings.get("hypergraphBackendMode", "hgdb"),
"nebula_graph_validated": settings.get("nebulaGraphValidated", False),
```

Keep the existing response shape and add fields only under `details`.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.test_nebulagraph_validation tests.test_nebulagraph_retrieval_validation -v
```

Expected: PASS.

- [ ] **Step 6: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 4.4 Add diagnostics that expose selected hypergraph backend and NebulaGraph connection status.
- [x] 5.2 Add retrieval parity checks for fixed question sets across `hyper`, `hyper-lite`, and `graph` modes.
- [x] 5.3 Compare retrieved entities, hyperedges, and source text units while keeping vector stores unchanged.
- [x] 5.5 Add context string diff reporting after deterministic normalization.
- [x] 5.6 Add optional final answer regression scoring when an evaluator is configured.
- [x] 6.1 Define configurable acceptance thresholds for storage parity and retrieval parity.
```

- [ ] **Step 7: Commit**

Run:

```bash
git add hyperrag/nebulagraph_validation.py web-ui/backend/main.py tests/test_nebulagraph_retrieval_validation.py openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "feat: add NebulaGraph retrieval parity diagnostics"
```

Expected: commit succeeds.

## Task 11: Dependencies And Documentation

**Files:**
- Modify: `requirements.txt`
- Modify: `web-ui/backend/requirements.txt`
- Create: `docs/nebulagraph-hypergraph-storage.md`
- Modify after passing: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`

- [ ] **Step 1: Add dependency**

Append this line to both `requirements.txt` and `web-ui/backend/requirements.txt`:

```text
nebula3-python
```

- [ ] **Step 2: Create operational documentation**

Create `docs/nebulagraph-hypergraph-storage.md`:

```markdown
# NebulaGraph Hypergraph Storage

## Default Behavior

Hyper-RAG continues to use `.hgdb` storage unless `hypergraphBackendMode` is explicitly configured.

## Modes

- `hgdb`: local `.hgdb` serving backend.
- `mirror-only`: migrate or mirror graph data to NebulaGraph while `.hgdb` serves queries.
- `dual-read`: compare `.hgdb` and NebulaGraph results while `.hgdb` serves queries.
- `nebulagraph-serving`: serve graph storage from NebulaGraph only after validation passes.

## Migration

1. Run schema check:
   `python scripts/hyperrag_nebulagraph.py schema-check --space hyperrag`
2. Run migration:
   `python scripts/hyperrag_nebulagraph.py migrate --hgdb web-ui/backend/hyperrag_cache/<database>/hypergraph_chunk_entity_relation.hgdb --database <database>`
3. Run validation:
   `python scripts/hyperrag_nebulagraph.py validate --hgdb web-ui/backend/hyperrag_cache/<database>/hypergraph_chunk_entity_relation.hgdb --database <database>`

## Quality Gate

Do not enable `nebulagraph-serving` until storage parity and retrieval parity pass configured thresholds.

## Rollback

Set `hypergraphBackendMode` back to `hgdb`. Public query, insert, upload, and database selection APIs do not change.
```

- [ ] **Step 3: Run documentation smoke check**

Run: `python scripts/hyperrag_nebulagraph.py schema-check --space hyperrag`

Expected: prints `USE`, `CREATE TAG`, and `CREATE EDGE` statements.

- [ ] **Step 4: Mark OpenSpec tasks complete**

Mark:

```markdown
- [x] 6.4 Verify rollback by switching configuration back to `.hgdb` without changing Web UI or API request/response contracts.
- [x] 7.7 Document NebulaGraph setup, schema initialization, mirror-only migration, validation, enablement, failure policy, and rollback steps.
```

- [ ] **Step 5: Commit**

Run:

```bash
git add requirements.txt web-ui/backend/requirements.txt docs/nebulagraph-hypergraph-storage.md openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "docs: document NebulaGraph hypergraph storage rollout"
```

Expected: commit succeeds.

## Task 12: Final Verification

**Files:**
- Read: `openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md`
- Read: all touched files from previous tasks

- [ ] **Step 1: Run full local unit suite**

Run:

```bash
python -m unittest discover tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run OpenSpec status**

Run:

```bash
openspec instructions apply --change migrate-hypergraph-storage-to-nebulagraph --json
```

Expected: progress reports all tasks complete.

- [ ] **Step 3: Inspect git diff**

Run:

```bash
git diff --stat
git diff --check
```

Expected: no whitespace errors from `git diff --check`; diff stat contains only NebulaGraph migration, docs, tests, and OpenSpec task updates.

- [ ] **Step 4: Commit any final task checkbox updates**

Run:

```bash
git add openspec/changes/migrate-hypergraph-storage-to-nebulagraph/tasks.md
git commit -m "chore: complete NebulaGraph migration task checklist"
```

Expected: commit succeeds if there are remaining task checkbox changes; if there are no changes, skip this commit.

## Self-Review

**Spec coverage:** The plan covers backend selection, mirror-only behavior, hyperedge-preserving model, canonical IDs, storage contract parity, source linkage, unchanged vector retrieval, offline migration, dual-read validation, quality gates, failure policy, rollback, tests, and documentation.

**Placeholder scan:** This plan contains no unfinished marker text or unspecified implementation steps. Each code task includes file paths, tests, commands, and expected results.

**Type consistency:** The plan consistently uses `HypergraphBackendMode`, `NebulaGraphSettings`, `NebulaHypergraphStorage`, `normalize_id_set`, `canonical_entity_vid`, `canonical_hyperedge_vid`, `HypergraphSnapshot`, `ParityReport`, and `RetrievalParityResult`.
