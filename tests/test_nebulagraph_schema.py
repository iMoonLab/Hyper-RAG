import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "hyperrag" / "nebulagraph_schema.py"
spec = importlib.util.spec_from_file_location("nebulagraph_schema", MODULE_PATH)
nebulagraph_schema = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nebulagraph_schema
spec.loader.exec_module(nebulagraph_schema)

REQUIRED_SCHEMA_STATEMENTS = nebulagraph_schema.REQUIRED_SCHEMA_STATEMENTS
schema_statements_for_space = nebulagraph_schema.schema_statements_for_space


class NebulaGraphSchemaTest(unittest.TestCase):
    def _statement_containing(self, text):
        for statement in REQUIRED_SCHEMA_STATEMENTS:
            if text in statement:
                return statement
        self.fail(f"Missing schema statement containing {text!r}")

    def test_required_schema_contains_entity_tag(self):
        self.assertTrue(
            any(
                "CREATE TAG IF NOT EXISTS Entity" in statement
                for statement in REQUIRED_SCHEMA_STATEMENTS
            )
        )

    def test_required_schema_contains_hyperedge_tag(self):
        self.assertTrue(
            any(
                "CREATE TAG IF NOT EXISTS Hyperedge" in statement
                for statement in REQUIRED_SCHEMA_STATEMENTS
            )
        )

    def test_required_schema_contains_member_of_edge(self):
        self.assertTrue(
            any(
                "CREATE EDGE IF NOT EXISTS MEMBER_OF" in statement
                for statement in REQUIRED_SCHEMA_STATEMENTS
            )
        )

    def test_required_schema_contains_has_member_edge(self):
        self.assertTrue(
            any(
                "CREATE EDGE IF NOT EXISTS HAS_MEMBER" in statement
                for statement in REQUIRED_SCHEMA_STATEMENTS
            )
        )

    def test_entity_tag_contains_required_fields(self):
        entity_statement = self._statement_containing("CREATE TAG IF NOT EXISTS Entity")

        for field_fragment in (
            "name string",
            "entity_type string",
            "description string",
            "source_id string",
            "additional_properties string",
            "database_name string",
        ):
            with self.subTest(field_fragment=field_fragment):
                self.assertIn(field_fragment, entity_statement)

    def test_hyperedge_tag_contains_required_fields(self):
        hyperedge_statement = self._statement_containing(
            "CREATE TAG IF NOT EXISTS Hyperedge"
        )

        for field_fragment in (
            "edge_hash string",
            "id_set string",
            "description string",
            "keywords string",
            "weight double",
            "source_id string",
            "arity int",
            "database_name string",
        ):
            with self.subTest(field_fragment=field_fragment):
                self.assertIn(field_fragment, hyperedge_statement)

    def test_membership_edges_include_database_scope(self):
        for edge_name in ("MEMBER_OF", "HAS_MEMBER"):
            with self.subTest(edge_name=edge_name):
                edge_statement = self._statement_containing(
                    f"CREATE EDGE IF NOT EXISTS {edge_name}"
                )
                self.assertIn("database_name string", edge_statement)

    def test_schema_statements_for_space_starts_with_use_statement(self):
        statements = schema_statements_for_space(" hyperrag ")

        self.assertEqual("USE `hyperrag`", statements[0])
        self.assertEqual(REQUIRED_SCHEMA_STATEMENTS, statements[1:])

    def test_schema_statements_for_space_rejects_blank_space_name(self):
        for space_name in ("", "   "):
            with self.subTest(space_name=space_name):
                with self.assertRaises(ValueError):
                    schema_statements_for_space(space_name)

    def test_schema_statements_for_space_rejects_backticks(self):
        with self.assertRaises(ValueError):
            schema_statements_for_space("bad`space")


if __name__ == "__main__":
    unittest.main()
