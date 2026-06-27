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


def _load_module(module_name, relative_path):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_load_module("hyperrag.nebulagraph_ids", "nebulagraph_ids.py")
nebulagraph_validation = importlib.import_module("hyperrag.nebulagraph_validation")

RetrievalParityResult = nebulagraph_validation.RetrievalParityResult


class RetrievalParityResultTest(unittest.TestCase):
    def test_perfect_overlaps_pass_threshold(self):
        result = RetrievalParityResult(
            mode="hyper",
            entity_overlap=1.0,
            hyperedge_overlap=1.0,
            text_unit_overlap=1.0,
            context_diff="",
            answer_score=1.0,
        )

        self.assertTrue(result.passed(0.95))

    def test_missing_answer_score_does_not_block_when_base_overlaps_pass(self):
        result = RetrievalParityResult(
            mode="hyper-lite",
            entity_overlap=0.96,
            hyperedge_overlap=0.97,
            text_unit_overlap=0.98,
            context_diff="answer scoring disabled",
            answer_score=None,
        )

        self.assertTrue(result.passed(0.95))

    def test_low_entity_hyperedge_or_text_overlap_fails(self):
        cases = [
            RetrievalParityResult("hyper", 0.94, 1.0, 1.0, "", None),
            RetrievalParityResult("hyper", 1.0, 0.94, 1.0, "", None),
            RetrievalParityResult("hyper", 1.0, 1.0, 0.94, "", None),
        ]

        for result in cases:
            with self.subTest(result=result):
                self.assertFalse(result.passed(0.95))

    def test_low_answer_score_fails_when_provided(self):
        result = RetrievalParityResult(
            mode="graph",
            entity_overlap=1.0,
            hyperedge_overlap=1.0,
            text_unit_overlap=1.0,
            context_diff="",
            answer_score=0.94,
        )

        self.assertFalse(result.passed(0.95))


if __name__ == "__main__":
    unittest.main()
