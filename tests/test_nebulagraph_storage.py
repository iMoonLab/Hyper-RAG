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

MODULE_PATH = PACKAGE_ROOT / "nebulagraph_storage.py"
spec = importlib.util.spec_from_file_location("hyperrag.nebulagraph_storage", MODULE_PATH)
nebulagraph_storage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nebulagraph_storage
spec.loader.exec_module(nebulagraph_storage)

NebulaHypergraphStorage = nebulagraph_storage.NebulaHypergraphStorage


class NebulaHypergraphStorageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.storage = NebulaHypergraphStorage(
            namespace="test",
            global_config={"working_dir": "/tmp"},
        )

    async def test_vertex_round_trip_copies_data(self):
        data = {"entity_type": "Person", "description": "alpha"}

        await self.storage.upsert_vertex("A", data)
        data["description"] = "mutated"

        self.assertTrue(await self.storage.has_vertex("A"))
        self.assertEqual(
            {"entity_type": "Person", "description": "alpha"},
            await self.storage.get_vertex("A"),
        )

        returned = await self.storage.get_vertex("A")
        returned["description"] = "leaked"
        self.assertEqual("alpha", (await self.storage.get_vertex("A"))["description"])
        self.assertEqual("missing", await self.storage.get_vertex("missing", "missing"))

    async def test_hyperedge_round_trip_is_order_independent_and_copies_data(self):
        data = {"weight": 2}

        await self.storage.upsert_hyperedge(("B", "A"), data)
        data["weight"] = 7

        self.assertTrue(await self.storage.has_hyperedge(("A", "B")))
        self.assertEqual({"weight": 2}, await self.storage.get_hyperedge(("A", "B")))

        returned = await self.storage.get_hyperedge(("B", "A"))
        returned["weight"] = 9
        self.assertEqual(2, (await self.storage.get_hyperedge(("A", "B")))["weight"])
        self.assertEqual("missing", await self.storage.get_hyperedge(("X", "Y"), "missing"))

    async def test_neighbors_and_degree_use_normalized_order(self):
        for vertex_id in ("A", "B", "C"):
            await self.storage.upsert_vertex(vertex_id, {"id": vertex_id})
        await self.storage.upsert_hyperedge(("A", "B", "C"), {"weight": 1})

        self.assertEqual(1, await self.storage.vertex_degree("A"))
        self.assertEqual(3, await self.storage.hyperedge_degree(("C", "B", "A")))
        self.assertEqual([("A", "B", "C")], await self.storage.get_nbr_e_of_vertex("A"))
        self.assertEqual(
            ["A", "B", "C"],
            await self.storage.get_nbr_v_of_hyperedge(("C", "A", "B")),
        )

    async def test_counts_and_all_lists_are_deterministic(self):
        for vertex_id in ("C", "A", "B"):
            await self.storage.upsert_vertex(vertex_id, {"id": vertex_id})
        await self.storage.upsert_hyperedge(("C", "A"), {"weight": 1})
        await self.storage.upsert_hyperedge(("B", "A", "C"), {"weight": 2})

        self.assertEqual(3, await self.storage.get_num_of_vertices())
        self.assertEqual(2, await self.storage.get_num_of_hyperedges())
        self.assertEqual(["A", "B", "C"], await self.storage.get_all_vertices())
        self.assertEqual(
            [("A", "B", "C"), ("A", "C")],
            await self.storage.get_all_hyperedges(),
        )

    async def test_remove_hyperedge_updates_neighbors_and_degrees(self):
        await self.storage.upsert_hyperedge(("B", "A"), {"weight": 1})
        await self.storage.upsert_hyperedge(("A", "C"), {"weight": 2})

        await self.storage.remove_hyperedge(("A", "B"))

        self.assertFalse(await self.storage.has_hyperedge(("B", "A")))
        self.assertEqual([("A", "C")], await self.storage.get_nbr_e_of_vertex("A"))
        self.assertEqual(1, await self.storage.vertex_degree("A"))
        self.assertEqual(0, await self.storage.hyperedge_degree(("A", "B")))

    async def test_remove_vertex_removes_incident_hyperedges_for_consistency(self):
        await self.storage.upsert_hyperedge(("A", "B"), {"weight": 1})
        await self.storage.upsert_hyperedge(("B", "C"), {"weight": 2})
        await self.storage.upsert_hyperedge(("C", "D"), {"weight": 3})

        await self.storage.remove_vertex("B")

        self.assertFalse(await self.storage.has_vertex("B"))
        self.assertFalse(await self.storage.has_hyperedge(("A", "B")))
        self.assertFalse(await self.storage.has_hyperedge(("B", "C")))
        self.assertTrue(await self.storage.has_hyperedge(("C", "D")))
        self.assertEqual(0, await self.storage.vertex_degree("A"))
        self.assertEqual([("C", "D")], await self.storage.get_all_hyperedges())

    async def test_vertex_neighbors_are_deterministic_with_optional_self(self):
        await self.storage.upsert_hyperedge(("C", "A", "B"), {"weight": 1})
        await self.storage.upsert_hyperedge(("D", "A"), {"weight": 2})

        self.assertEqual(
            ["B", "C", "D"],
            await self.storage.get_nbr_v_of_vertex("A", exclude_self=True),
        )
        self.assertEqual(
            ["A", "B", "C", "D"],
            await self.storage.get_nbr_v_of_vertex("A", exclude_self=False),
        )
        self.assertEqual([], await self.storage.get_nbr_v_of_vertex("missing"))


if __name__ == "__main__":
    unittest.main()
