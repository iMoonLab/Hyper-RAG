import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "web-ui"
    / "backend"
    / "settings_helpers.py"
)
spec = importlib.util.spec_from_file_location("settings_helpers", MODULE_PATH)
settings_helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = settings_helpers
spec.loader.exec_module(settings_helpers)

merge_settings_for_save = settings_helpers.merge_settings_for_save


class SettingsHelpersTest(unittest.TestCase):
    def test_preserves_unknown_existing_settings(self):
        merged = merge_settings_for_save(
            {"futureSetting": "keep", "modelName": "old"},
            {"modelName": "new"},
        )

        self.assertEqual("keep", merged["futureSetting"])
        self.assertEqual("new", merged["modelName"])

    def test_preserves_existing_api_key_for_masked_value(self):
        merged = merge_settings_for_save(
            {"apiKey": "secret"},
            {"apiKey": "***", "modelName": "new"},
        )

        self.assertEqual("secret", merged["apiKey"])

    def test_keeps_nebulagraph_settings_from_incoming_payload(self):
        merged = merge_settings_for_save(
            {},
            {
                "hypergraphBackendMode": "dual-read",
                "nebulaGraphValidated": False,
            },
        )

        self.assertEqual("dual-read", merged["hypergraphBackendMode"])
        self.assertFalse(merged["nebulaGraphValidated"])

    def test_preserves_existing_nebulagraph_settings_when_omitted(self):
        merged = merge_settings_for_save(
            {
                "hypergraphBackendMode": "nebulagraph-serving",
                "nebulaGraphValidated": True,
            },
            {"modelName": "gpt-5-mini"},
        )

        self.assertEqual("nebulagraph-serving", merged["hypergraphBackendMode"])
        self.assertTrue(merged["nebulaGraphValidated"])


if __name__ == "__main__":
    unittest.main()
