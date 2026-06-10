import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "hyperrag" / "nebulagraph_ids.py"
spec = importlib.util.spec_from_file_location("nebulagraph_ids", MODULE_PATH)
nebulagraph_ids = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nebulagraph_ids
spec.loader.exec_module(nebulagraph_ids)

canonical_entity_vid = nebulagraph_ids.canonical_entity_vid
canonical_hyperedge_vid = nebulagraph_ids.canonical_hyperedge_vid
normalize_id_set = nebulagraph_ids.normalize_id_set


class NebulaGraphIdsTest(unittest.TestCase):
    def test_entity_vid_trims_entity_name(self):
        self.assertEqual(
            canonical_entity_vid("demo", " Entity A "),
            canonical_entity_vid("demo", "Entity A"),
        )

    def test_entity_vid_is_scoped_by_database_name(self):
        self.assertNotEqual(
            canonical_entity_vid("demo-a", "Entity A"),
            canonical_entity_vid("demo-b", "Entity A"),
        )

    def test_hyperedge_vid_is_order_independent(self):
        self.assertEqual(
            canonical_hyperedge_vid("demo", ["B", "A", "C"]),
            canonical_hyperedge_vid("demo", ["C", "B", "A"]),
        )

    def test_normalize_id_set_deduplicates_and_sorts(self):
        self.assertEqual(("A", "B"), normalize_id_set(["B", "A", "B"]))

    def test_normalize_id_set_rejects_empty_id_set(self):
        with self.assertRaises(ValueError):
            normalize_id_set([])

    def test_high_order_hyperedge_vid_is_deterministic(self):
        first_vid = canonical_hyperedge_vid("demo", ["D", "B", "A", "C"])
        second_vid = canonical_hyperedge_vid("demo", ["C", "A", "D", "B"])

        self.assertEqual(first_vid, second_vid)
        self.assertTrue(first_vid.startswith("hedge:"))

    def test_entity_vid_payload_serialization_is_unambiguous(self):
        self.assertNotEqual(
            canonical_entity_vid("a", "b\x1fc"),
            canonical_entity_vid("a\x1fb", "c"),
        )

    def test_hyperedge_vid_payload_serialization_is_unambiguous(self):
        self.assertNotEqual(
            canonical_hyperedge_vid("demo", ["A\x1eB"]),
            canonical_hyperedge_vid("demo", ["A", "B"]),
        )

    def test_none_identifier_parts_are_rejected(self):
        with self.assertRaises(ValueError):
            canonical_entity_vid("demo", None)

        with self.assertRaises(ValueError):
            normalize_id_set(["A", None])


if __name__ == "__main__":
    unittest.main()
