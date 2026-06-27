import importlib
import subprocess
import sys
import unittest


class ReproduceImportTests(unittest.TestCase):
    def test_reproduce_modules_import_as_package(self):
        for module_name in (
            "reproduce.Step_0",
            "reproduce.Step_1",
            "reproduce.Step_2_extract_question",
            "reproduce.Step_3_response_question",
        ):
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)

    def test_service_api_imports_reproduce_helpers(self):
        importlib.import_module("service_api")

    def test_reproduce_step_1_runs_as_module(self):
        result = subprocess.run(
            [sys.executable, "-m", "reproduce.Step_1", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--data-name", result.stdout)


if __name__ == "__main__":
    unittest.main()
