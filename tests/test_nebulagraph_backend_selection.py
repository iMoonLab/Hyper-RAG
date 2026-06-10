import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "hyperrag"


def _install_stub_modules():
    package = types.ModuleType("hyperrag")
    package.__path__ = [str(PACKAGE_ROOT)]
    sys.modules["hyperrag"] = package

    utils = types.ModuleType("hyperrag.utils")

    class EmbeddingFunc:
        pass

    utils.EmbeddingFunc = EmbeddingFunc
    utils.compute_mdhash_id = lambda content, prefix="": prefix + content
    utils.limit_async_func_call = lambda _max_async: lambda func: func
    utils.limit_async_gen_call = lambda _max_async: lambda func: func
    utils.convert_response_to_json = lambda response: response
    utils.set_logger = lambda _log_file: None

    class Logger:
        level = "INFO"

        def info(self, *_args, **_kwargs):
            pass

        def debug(self, *_args, **_kwargs):
            pass

        def warning(self, *_args, **_kwargs):
            pass

        def setLevel(self, level):
            self.level = level

    utils.logger = Logger()
    sys.modules["hyperrag.utils"] = utils

    operate = types.ModuleType("hyperrag.operate")
    for name in (
        "chunking_by_token_size",
        "extract_entities",
        "hyper_query_lite",
        "hyper_query",
        "naive_query",
        "graph_query",
        "llm_query",
        "hyper_query_stream",
        "hyper_query_lite_stream",
        "naive_query_stream",
        "llm_query_stream",
    ):
        setattr(operate, name, lambda *args, **kwargs: None)
    sys.modules["hyperrag.operate"] = operate

    llm = types.ModuleType("hyperrag.llm")
    llm.gpt_4o_mini_complete = lambda *args, **kwargs: None
    llm.openai_embedding = lambda *args, **kwargs: None
    sys.modules["hyperrag.llm"] = llm

    storage = types.ModuleType("hyperrag.storage")

    class JsonKVStorage:
        pass

    class NanoVectorDBStorage:
        pass

    class HypergraphStorage:
        pass

    storage.JsonKVStorage = JsonKVStorage
    storage.NanoVectorDBStorage = NanoVectorDBStorage
    storage.HypergraphStorage = HypergraphStorage
    sys.modules["hyperrag.storage"] = storage

    return HypergraphStorage


def _load_module(module_name, relative_path):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HypergraphStorage = _install_stub_modules()
_load_module("hyperrag.base", "base.py")
_load_module("hyperrag.nebulagraph_ids", "nebulagraph_ids.py")
nebulagraph_config = _load_module(
    "hyperrag.nebulagraph_config", "nebulagraph_config.py"
)
nebulagraph_storage = _load_module(
    "hyperrag.nebulagraph_storage", "nebulagraph_storage.py"
)
hyperrag_module = _load_module("hyperrag.hyperrag", "hyperrag.py")

HypergraphBackendMode = nebulagraph_config.HypergraphBackendMode
NebulaGraphSettings = nebulagraph_config.NebulaGraphSettings
NebulaHypergraphStorage = nebulagraph_storage.NebulaHypergraphStorage
resolve_hypergraph_storage_cls = hyperrag_module.resolve_hypergraph_storage_cls


class DefaultStorage:
    pass


class NebulaGraphBackendSelectionTest(unittest.TestCase):
    def test_nebulagraph_serving_without_validation_is_not_serving(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = NebulaGraphSettings.from_config(
                {
                    "hypergraph_backend_mode": "nebulagraph-serving",
                    "nebulagraph_validated": False,
                }
            )

        self.assertEqual(HypergraphBackendMode.NEBULAGRAPH_SERVING, settings.mode)
        self.assertFalse(settings.serving_enabled)

    def test_nebulagraph_serving_with_validation_is_serving(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = NebulaGraphSettings.from_config(
                {
                    "hypergraph_backend_mode": "nebulagraph-serving",
                    "nebulagraph_validated": True,
                }
            )

        self.assertEqual(HypergraphBackendMode.NEBULAGRAPH_SERVING, settings.mode)
        self.assertTrue(settings.serving_enabled)

    def test_mirror_only_resolves_to_default_storage(self):
        with patch.dict(os.environ, {}, clear=True):
            storage_cls = resolve_hypergraph_storage_cls(
                {"hypergraph_backend_mode": "mirror-only"}, HypergraphStorage
            )

        self.assertIs(HypergraphStorage, storage_cls)

    def test_dual_read_resolves_to_default_storage(self):
        with patch.dict(os.environ, {}, clear=True):
            storage_cls = resolve_hypergraph_storage_cls(
                {"hypergraph_backend_mode": "dual-read"}, DefaultStorage
            )

        self.assertIs(DefaultStorage, storage_cls)

    def test_validated_nebulagraph_serving_resolves_to_nebula_storage(self):
        with patch.dict(os.environ, {}, clear=True):
            storage_cls = resolve_hypergraph_storage_cls(
                {
                    "hypergraph_backend_mode": "nebulagraph-serving",
                    "nebulagraph_validated": True,
                },
                DefaultStorage,
            )

        self.assertIs(NebulaHypergraphStorage, storage_cls)

    def test_addon_params_override_base_config_to_enable_serving(self):
        with patch.dict(os.environ, {}, clear=True):
            storage_cls = resolve_hypergraph_storage_cls(
                {
                    "hypergraph_backend_mode": "mirror-only",
                    "nebulagraph_validated": False,
                    "addon_params": {
                        "hypergraph_backend_mode": "nebulagraph-serving",
                        "nebulagraph_validated": True,
                    },
                },
                DefaultStorage,
            )

        self.assertIs(NebulaHypergraphStorage, storage_cls)


if __name__ == "__main__":
    unittest.main()
