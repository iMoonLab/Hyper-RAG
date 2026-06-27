import os
import unittest
from unittest.mock import patch


class ProxyEnvironmentTests(unittest.TestCase):
    def test_normalizes_multiline_proxy_environment_value(self):
        from hyperrag.env import normalize_proxy_env

        environ = {
            "HTTP_PROXY": "http://127.0.0.1:7897\r\nHTTPS_PROXY=http://127.0.0.1:7897"
        }

        normalize_proxy_env(environ)

        self.assertEqual(environ["HTTP_PROXY"], "http://127.0.0.1:7897")
        self.assertEqual(environ["HTTPS_PROXY"], "http://127.0.0.1:7897")

    def test_openai_client_accepts_normalized_proxy_environment(self):
        broken_proxy = "http://127.0.0.1:7897\r\nHTTPS_PROXY=http://127.0.0.1:7897"

        with patch.dict(os.environ, {"HTTP_PROXY": broken_proxy}, clear=False):
            from hyperrag.env import normalize_proxy_env

            normalize_proxy_env()

            from openai import AsyncOpenAI

            AsyncOpenAI(base_url="https://api.example.com/v1", api_key="test-key")


if __name__ == "__main__":
    unittest.main()
