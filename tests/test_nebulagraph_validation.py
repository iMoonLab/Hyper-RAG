import importlib
import importlib.util
from pathlib import Path
import sys
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


nebulagraph_storage = _load_module(
    "hyperrag.nebulagraph_storage", "nebulagraph_storage.py"
)
nebulagraph_validation = importlib.import_module("hyperrag.nebulagraph_validation")

NebulaHypergraphStorage = nebulagraph_storage.NebulaHypergraphStorage
compare_storage_backends = nebulagraph_validation.compare_storage_backends


class NeighborMismatchStorage:
    def __init__(self, storage):
        self.storage = storage

    async def get_num_of_vertices(self):
        return await self.storage.get_num_of_vertices()

    async def get_num_of_hyperedges(self):
        return await self.storage.get_num_of_hyperedges()

    async def get_vertex(self, vertex_id):
        return await self.storage.get_vertex(vertex_id)

    async def vertex_degree(self, vertex_id):
        return await self.storage.vertex_degree(vertex_id)

    async def get_nbr_e_of_vertex(self, vertex_id):
        return await self.storage.get_nbr_e_of_vertex(vertex_id)

    async def get_hyperedge(self, id_set):
        return await self.storage.get_hyperedge(id_set)

    async def hyperedge_degree(self, id_set):
        return await self.storage.hyperedge_degree(id_set)

    async def get_nbr_v_of_hyperedge(self, id_set):
        return ["A", "C"]


class NebulaGraphValidationTest(unittest.IsolatedAsyncioTestCase):
    def _storage(self):
        return NebulaHypergraphStorage(
            namespace="test",
            global_config={"working_dir": "/tmp"},
        )

    async def _matching_pair(self):
        left = self._storage()
        right = self._storage()
        for storage in (left, right):
            await storage.upsert_vertex(
                "A",
                {
                    "entity_type": "Person",
                    "description": "Alice",
                    "source_id": "chunk-a",
                },
            )
            await storage.upsert_vertex(
                "B",
                {
                    "entity_type": "Place",
                    "description": "Berlin",
                    "source_id": "chunk-b",
                },
            )
            await storage.upsert_hyperedge(
                ("A", "B"),
                {
                    "description": "Alice visited Berlin",
                    "source_id": "chunk-ab",
                    "weight": 1.0,
                },
            )
        return left, right

    async def test_matching_storages_pass(self):
        left, right = await self._matching_pair()

        report = await compare_storage_backends(
            left,
            right,
            sample_vertices=["A"],
            sample_hyperedges=[("A", "B")],
        )

        self.assertTrue(report.passed)
        self.assertEqual([], report.failures)

    async def test_count_mismatch_reports_clear_failure(self):
        left, right = await self._matching_pair()
        await right.upsert_vertex("C", {"description": "Conference"})

        report = await compare_storage_backends(
            left,
            right,
            sample_vertices=["A"],
            sample_hyperedges=[("A", "B")],
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any(
                "vertex count mismatch" in failure
                and "left=2" in failure
                and "right=3" in failure
                for failure in report.failures
            ),
            report.failures,
        )

    async def test_vertex_payload_mismatch_reports_vertex_id(self):
        left, right = await self._matching_pair()
        await right.upsert_vertex(
            "A",
            {
                "entity_type": "Person",
                "description": "Alicia",
                "source_id": "chunk-a",
            },
        )

        report = await compare_storage_backends(
            left,
            right,
            sample_vertices=["A"],
            sample_hyperedges=[("A", "B")],
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("vertex payload mismatch" in failure and "A" in failure for failure in report.failures),
            report.failures,
        )

    async def test_hyperedge_neighbor_mismatch_reports_normalized_id_set(self):
        left, right = await self._matching_pair()
        right_with_bad_neighbors = NeighborMismatchStorage(right)

        report = await compare_storage_backends(
            left,
            right_with_bad_neighbors,
            sample_vertices=["A"],
            sample_hyperedges=[("B", "A")],
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any(
                "hyperedge neighbors mismatch" in failure
                and "('A', 'B')" in failure
                for failure in report.failures
            ),
            report.failures,
        )


if __name__ == "__main__":
    unittest.main()
