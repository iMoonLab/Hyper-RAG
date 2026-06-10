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

    def test_schema_statements_for_space_starts_with_use_statement(self):
        statements = schema_statements_for_space(" hyperrag ")

        self.assertEqual("USE `hyperrag`", statements[0])
        self.assertEqual(REQUIRED_SCHEMA_STATEMENTS, statements[1:])

    def test_schema_statements_for_space_rejects_blank_space_name(self):
        for space_name in ("", "   "):
            with self.subTest(space_name=space_name):
                with self.assertRaises(ValueError):
                    schema_statements_for_space(space_name)


if __name__ == "__main__":
    unittest.main()
