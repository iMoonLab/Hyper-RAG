import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "hyperrag" / "nebulagraph_config.py"
spec = importlib.util.spec_from_file_location("nebulagraph_config", MODULE_PATH)
nebulagraph_config = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nebulagraph_config
spec.loader.exec_module(nebulagraph_config)

HypergraphBackendMode = nebulagraph_config.HypergraphBackendMode
NebulaGraphSettings = nebulagraph_config.NebulaGraphSettings
resolve_hypergraph_backend_mode = nebulagraph_config.resolve_hypergraph_backend_mode


class NebulaGraphConfigTest(unittest.TestCase):
    def test_default_backend_is_hgdb(self):
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_hypergraph_backend_mode({})

        self.assertEqual(HypergraphBackendMode.HGDB, mode)

    def test_mirror_only_mode_from_global_config(self):
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_hypergraph_backend_mode(
                {"hypergraph_backend_mode": "mirror-only"}
            )

        self.assertEqual(HypergraphBackendMode.MIRROR_ONLY, mode)

    def test_invalid_mode_falls_back_to_hgdb(self):
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_hypergraph_backend_mode(
                {"hypergraph_backend_mode": "not-a-backend"}
            )

        self.assertEqual(HypergraphBackendMode.HGDB, mode)

    def test_mode_is_trimmed_and_case_insensitive(self):
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_hypergraph_backend_mode(
                {"hypergraph_backend_mode": " DUAL-READ "}
            )

        self.assertEqual(HypergraphBackendMode.DUAL_READ, mode)

    def test_settings_default_to_not_serving_and_fallback_to_hgdb(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = NebulaGraphSettings.from_config({})

        self.assertEqual(HypergraphBackendMode.HGDB, settings.mode)
        self.assertFalse(settings.serving_enabled)
        self.assertTrue(settings.fallback_to_hgdb)

    def test_serving_requires_explicit_validated_true(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = NebulaGraphSettings.from_config(
                {
                    "hypergraph_backend_mode": "nebulagraph-serving",
                    "nebulagraph_validated": "true",
                }
            )

        self.assertTrue(settings.serving_enabled)

    def test_serving_rejects_non_true_validation_states(self):
        for validation_state in ("pending", "failed", "invalid", "false", ""):
            with self.subTest(validation_state=validation_state):
                with patch.dict(os.environ, {}, clear=True):
                    settings = NebulaGraphSettings.from_config(
                        {
                            "hypergraph_backend_mode": "nebulagraph-serving",
                            "nebulagraph_validated": validation_state,
                        }
                    )

                self.assertFalse(settings.serving_enabled)


if __name__ == "__main__":
    unittest.main()
