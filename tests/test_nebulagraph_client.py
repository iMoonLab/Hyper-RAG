import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "hyperrag" / "nebulagraph_client.py"
spec = importlib.util.spec_from_file_location("nebulagraph_client", MODULE_PATH)
nebulagraph_client = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nebulagraph_client
spec.loader.exec_module(nebulagraph_client)

FakeNebulaGraphClient = nebulagraph_client.FakeNebulaGraphClient


class FakeNebulaGraphClientTest(unittest.TestCase):
    def test_execute_records_statement(self):
        client = FakeNebulaGraphClient()

        result = client.execute("CREATE TAG Entity()")

        self.assertEqual(["CREATE TAG Entity()"], client.statements)
        self.assertEqual([], result)

    def test_is_available_defaults_true(self):
        client = FakeNebulaGraphClient()

        self.assertTrue(client.is_available())

    def test_execute_many_runs_statements_in_order(self):
        client = FakeNebulaGraphClient()

        results = client.execute_many(
            [
                "CREATE TAG Entity()",
                "CREATE EDGE MEMBER_OF()",
            ]
        )

        self.assertEqual(
            [
                "CREATE TAG Entity()",
                "CREATE EDGE MEMBER_OF()",
            ],
            client.statements,
        )
        self.assertEqual([[], []], results)

    def test_unavailable_fake_returns_false(self):
        client = FakeNebulaGraphClient(available=False)

        self.assertFalse(client.is_available())


if __name__ == "__main__":
    unittest.main()
