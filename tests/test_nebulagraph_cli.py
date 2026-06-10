import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hyperrag_nebulagraph.py"
spec = importlib.util.spec_from_file_location("hyperrag_nebulagraph", MODULE_PATH)
hyperrag_nebulagraph = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hyperrag_nebulagraph
spec.loader.exec_module(hyperrag_nebulagraph)


class NebulaGraphCliTest(unittest.TestCase):
    def test_build_parser_parses_schema_check_space(self):
        parser = hyperrag_nebulagraph.build_parser()

        args = parser.parse_args(["schema-check", "--space", "hyperrag"])

        self.assertEqual("schema-check", args.command)
        self.assertEqual("hyperrag", args.space)

    def test_main_schema_check_prints_schema_statements(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = hyperrag_nebulagraph.main(["schema-check", "--space", "hyperrag"])

        self.assertEqual(0, result)
        lines = output.getvalue().splitlines()
        self.assertEqual("USE `hyperrag`", lines[0])
        self.assertTrue(
            any("CREATE TAG IF NOT EXISTS Entity" in line for line in lines)
        )
        self.assertTrue(
            any("CREATE TAG IF NOT EXISTS Hyperedge" in line for line in lines)
        )
        self.assertTrue(
            any("CREATE EDGE IF NOT EXISTS MEMBER_OF" in line for line in lines)
        )

    def test_script_is_directly_executable(self):
        self.assertTrue(os.access(MODULE_PATH, os.X_OK))

    def test_main_schema_check_reports_invalid_space_as_parser_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as captured:
                hyperrag_nebulagraph.main(["schema-check", "--space", "bad`space"])

        self.assertEqual(2, captured.exception.code)

    def test_parser_exposes_migrate_arguments(self):
        parser = hyperrag_nebulagraph.build_parser()

        args = parser.parse_args(
            ["migrate", "--hgdb", "graph.hgdb", "--database", "default"]
        )

        self.assertEqual("migrate", args.command)
        self.assertEqual("graph.hgdb", args.hgdb)
        self.assertEqual("default", args.database)

    def test_parser_exposes_validate_arguments(self):
        parser = hyperrag_nebulagraph.build_parser()

        args = parser.parse_args(
            ["validate", "--hgdb", "graph.hgdb", "--database", "default"]
        )

        self.assertEqual("validate", args.command)
        self.assertEqual("graph.hgdb", args.hgdb)
        self.assertEqual("default", args.database)

    def test_main_migrate_requires_implementation_wiring(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as captured:
                hyperrag_nebulagraph.main(
                    ["migrate", "--hgdb", "graph.hgdb", "--database", "default"]
                )

        self.assertEqual(2, captured.exception.code)

    def test_main_validate_requires_implementation_wiring(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as captured:
                hyperrag_nebulagraph.main(
                    ["validate", "--hgdb", "graph.hgdb", "--database", "default"]
                )

        self.assertEqual(2, captured.exception.code)


if __name__ == "__main__":
    unittest.main()
