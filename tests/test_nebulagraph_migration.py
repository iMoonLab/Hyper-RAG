import importlib.util
import asyncio
from pathlib import Path
import pickle
import sys
import tempfile
import types
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "hyperrag"

if "hyperrag" not in sys.modules:
    package = types.ModuleType("hyperrag")
    package.__path__ = [str(PACKAGE_ROOT)]
    sys.modules["hyperrag"] = package

if "hyperrag.utils" not in sys.modules:
    utils = types.ModuleType("hyperrag.utils")
    utils.EmbeddingFunc = object
    sys.modules["hyperrag.utils"] = utils


def _load_module(module_name, relative_path):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


nebulagraph_migration = _load_module(
    "hyperrag.nebulagraph_migration", "nebulagraph_migration.py"
)
nebulagraph_storage = _load_module(
    "hyperrag.nebulagraph_storage", "nebulagraph_storage.py"
)

load_hgdb_snapshot = nebulagraph_migration.load_hgdb_snapshot
migrate_snapshot_to_storage = nebulagraph_migration.migrate_snapshot_to_storage
migrate_snapshot_to_storage_async = (
    nebulagraph_migration.migrate_snapshot_to_storage_async
)
NebulaHypergraphStorage = nebulagraph_storage.NebulaHypergraphStorage


class PickledHypergraphObject:
    def __init__(self, vertices, hyperedges):
        self._v_data = vertices
        self._e_data = hyperedges
        self._v_inci = {}


class MutatingStorage:
    async def upsert_vertex(self, vertex_id, vertex_data):
        vertex_data["description"] = "mutated by storage"

    async def upsert_hyperedge(self, id_set, hyperedge_data):
        hyperedge_data["weight"] = 999


class NebulaGraphMigrationTest(unittest.TestCase):
    def _write_hgdb_fixture(self, payload):
        temp_dir = tempfile.TemporaryDirectory()
        hgdb_file = Path(temp_dir.name) / "hypergraph_chunk_entity_relation.hgdb"
        with hgdb_file.open("wb") as file:
            pickle.dump(payload, file)
        self.addCleanup(temp_dir.cleanup)
        return hgdb_file

    def test_load_hgdb_snapshot_preserves_pairwise_payloads(self):
        hgdb_file = self._write_hgdb_fixture(
            {
                "v_data": {
                    "A": {
                        "entity_type": "Person",
                        "description": "Alice",
                        "source_id": "chunk-a",
                    },
                    "B": {
                        "entity_type": "Place",
                        "description": "Berlin",
                        "source_id": "chunk-b",
                    },
                },
                "e_data": {
                    ("B", "A"): {
                        "description": "Alice visited Berlin",
                        "source_id": "chunk-ab",
                        "weight": 0.75,
                    }
                },
                "v_inci": {},
            }
        )

        snapshot = load_hgdb_snapshot(hgdb_file)

        self.assertEqual({"A", "B"}, set(snapshot.vertices))
        self.assertEqual("Alice", snapshot.vertices["A"]["description"])
        self.assertEqual("chunk-b", snapshot.vertices["B"]["source_id"])
        self.assertEqual({("A", "B")}, set(snapshot.hyperedges))
        self.assertEqual(
            "Alice visited Berlin",
            snapshot.hyperedges[("A", "B")]["description"],
        )
        self.assertEqual("chunk-ab", snapshot.hyperedges[("A", "B")]["source_id"])
        self.assertEqual(0.75, snapshot.hyperedges[("A", "B")]["weight"])

    def test_load_hgdb_snapshot_supports_pickled_hypergraph_object(self):
        hgdb_file = self._write_hgdb_fixture(
            PickledHypergraphObject(
                vertices={"A": {"description": "Alice"}},
                hyperedges={("A", "B"): {"weight": 1.0}},
            )
        )

        snapshot = load_hgdb_snapshot(hgdb_file)

        self.assertEqual("Alice", snapshot.vertices["A"]["description"])
        self.assertEqual(1.0, snapshot.hyperedges[("A", "B")]["weight"])

    def test_migration_is_repeatable_without_duplicate_logical_records(self):
        hgdb_file = self._write_hgdb_fixture(
            {
                "v_data": {
                    "A": {"description": "Alice"},
                    "B": {"description": "Berlin"},
                },
                "e_data": {("A", "B"): {"weight": 1.0}},
                "v_inci": {},
            }
        )
        snapshot = load_hgdb_snapshot(hgdb_file)
        storage = NebulaHypergraphStorage(
            namespace="test",
            global_config={"working_dir": str(hgdb_file.parent)},
        )

        migrate_snapshot_to_storage(snapshot, storage)
        migrate_snapshot_to_storage(snapshot, storage)

        self.assertEqual(2, len(storage._vertex_data))
        self.assertEqual(1, len(storage._hyperedge_data))

    def test_migration_preserves_high_order_hyperedge_id_set_and_arity(self):
        hgdb_file = self._write_hgdb_fixture(
            {
                "v_data": {
                    "A": {"description": "Alice"},
                    "B": {"description": "Berlin"},
                    "C": {"description": "Conference"},
                },
                "e_data": {
                    ("C", "A", "B"): {
                        "description": "Alice attended a Berlin conference",
                        "keywords": "travel,event",
                        "source_id": "chunk-abc",
                        "weight": 2.5,
                    }
                },
                "v_inci": {},
            }
        )
        snapshot = load_hgdb_snapshot(hgdb_file)
        storage = NebulaHypergraphStorage(
            namespace="test",
            global_config={"working_dir": str(hgdb_file.parent)},
        )

        migrate_snapshot_to_storage(snapshot, storage)

        self.assertEqual({("A", "B", "C")}, set(snapshot.hyperedges))
        self.assertEqual(3, len(storage._vertex_data))
        self.assertEqual(1, len(storage._hyperedge_data))
        edge_data = storage._hyperedge_data[("A", "B", "C")]
        self.assertEqual(("A", "B", "C"), tuple(edge_data["id_set"]))
        self.assertEqual(3, edge_data["arity"])
        self.assertEqual("Alice attended a Berlin conference", edge_data["description"])
        self.assertEqual("travel,event", edge_data["keywords"])
        self.assertEqual("chunk-abc", edge_data["source_id"])
        self.assertEqual(2.5, edge_data["weight"])

    def test_migration_passes_payload_copies_to_storage(self):
        snapshot = nebulagraph_migration.HypergraphSnapshot(
            vertices={"A": {"description": "Alice"}},
            hyperedges={("A",): {"weight": 1}},
        )

        migrate_snapshot_to_storage(snapshot, MutatingStorage())

        self.assertEqual("Alice", snapshot.vertices["A"]["description"])
        self.assertEqual(1, snapshot.hyperedges[("A",)]["weight"])

    def test_async_migration_entrypoint_runs_inside_event_loop(self):
        async def run_migration():
            snapshot = nebulagraph_migration.HypergraphSnapshot(
                vertices={"A": {"description": "Alice"}},
                hyperedges={("A",): {"weight": 1}},
            )
            storage = NebulaHypergraphStorage(
                namespace="test",
                global_config={"working_dir": "/tmp"},
            )
            await migrate_snapshot_to_storage_async(snapshot, storage)
            return storage

        storage = asyncio.run(run_migration())

        self.assertEqual("Alice", storage._vertex_data["A"]["description"])
        self.assertEqual(["A"], storage._hyperedge_data[("A",)]["id_set"])

    def test_sync_migration_rejects_running_event_loop(self):
        async def run_migration():
            snapshot = nebulagraph_migration.HypergraphSnapshot(
                vertices={"A": {}},
                hyperedges={},
            )
            storage = NebulaHypergraphStorage(
                namespace="test",
                global_config={"working_dir": "/tmp"},
            )
            migrate_snapshot_to_storage(snapshot, storage)

        with self.assertRaisesRegex(RuntimeError, "active event loop"):
            asyncio.run(run_migration())


if __name__ == "__main__":
    unittest.main()
