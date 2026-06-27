import os
from collections.abc import MutableMapping


_PROXY_ENV_NAMES = {
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
}


def normalize_proxy_env(environ: MutableMapping[str, str] | None = None) -> None:
    """Split malformed multiline proxy environment values back into variables."""
    environ = os.environ if environ is None else environ

    for name in tuple(_PROXY_ENV_NAMES):
        raw_value = environ.get(name)
        if not raw_value or ("\n" not in raw_value and "\r" not in raw_value):
            continue

        lines = [line.strip() for line in raw_value.splitlines() if line.strip()]
        if not lines:
            continue

        first_line = lines[0]
        if "=" in first_line:
            key, value = first_line.split("=", 1)
            if key in _PROXY_ENV_NAMES and value:
                environ[key] = value
            else:
                environ[name] = first_line
        else:
            environ[name] = first_line

        for line in lines[1:]:
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in _PROXY_ENV_NAMES and value:
                environ[key] = value
