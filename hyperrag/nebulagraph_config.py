from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any


class HypergraphBackendMode(str, Enum):
    HGDB = "hgdb"
    MIRROR_ONLY = "mirror-only"
    DUAL_READ = "dual-read"
    NEBULAGRAPH_SERVING = "nebulagraph-serving"


def resolve_hypergraph_backend_mode(config: dict[str, Any]) -> HypergraphBackendMode:
    mode = _get_config_value(
        config,
        "hypergraph_backend_mode",
        "HYPERRAG_HYPERGRAPH_BACKEND_MODE",
        HypergraphBackendMode.HGDB.value,
    )
    return _coerce_backend_mode(mode)


@dataclass(frozen=True)
class NebulaGraphSettings:
    mode: HypergraphBackendMode
    host: str
    port: int
    username: str
    password: str
    space: str
    database_name: str
    serving_enabled: bool
    fallback_to_hgdb: bool

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "NebulaGraphSettings":
        mode = resolve_hypergraph_backend_mode(config)
        database_name = str(
            _get_config_value(config, "database_name", "HYPERRAG_DATABASE_NAME", "")
        )
        database_config = _get_database_config(config, database_name)

        serving_enabled = (
            mode == HypergraphBackendMode.NEBULAGRAPH_SERVING
            and _coerce_bool(
                _get_config_value(config, "nebulagraph_validated", "", False)
            )
        )

        return cls(
            mode=mode,
            host=str(
                _get_config_value(
                    database_config,
                    "nebulagraph_host",
                    "",
                    _get_config_value(
                        config,
                        "nebulagraph_host",
                        "HYPERRAG_NEBULAGRAPH_HOST",
                        "127.0.0.1",
                    ),
                )
            ),
            port=_coerce_port(
                _get_config_value(
                    database_config,
                    "nebulagraph_port",
                    "",
                    _get_config_value(
                        config,
                        "nebulagraph_port",
                        "HYPERRAG_NEBULAGRAPH_PORT",
                        9669,
                    ),
                )
            ),
            username=str(
                _get_config_value(
                    database_config,
                    "nebulagraph_username",
                    "",
                    _get_config_value(
                        config,
                        "nebulagraph_username",
                        "HYPERRAG_NEBULAGRAPH_USERNAME",
                        "root",
                    ),
                )
            ),
            password=str(
                _get_config_value(
                    database_config,
                    "nebulagraph_password",
                    "",
                    _get_config_value(
                        config,
                        "nebulagraph_password",
                        "HYPERRAG_NEBULAGRAPH_PASSWORD",
                        "nebula",
                    ),
                )
            ),
            space=str(
                _get_config_value(
                    database_config,
                    "nebulagraph_space",
                    "",
                    _get_config_value(
                        config,
                        "nebulagraph_space",
                        "HYPERRAG_NEBULAGRAPH_SPACE",
                        "hyperrag",
                    ),
                )
            ),
            database_name=database_name,
            serving_enabled=serving_enabled,
            fallback_to_hgdb=_coerce_bool(
                _get_config_value(
                    database_config,
                    "fallback_to_hgdb",
                    "",
                    _get_config_value(
                        config,
                        "fallback_to_hgdb",
                        "HYPERRAG_FALLBACK_TO_HGDB",
                        True,
                    ),
                )
            ),
        )


def _coerce_backend_mode(value: Any) -> HypergraphBackendMode:
    try:
        return HypergraphBackendMode(str(value))
    except ValueError:
        return HypergraphBackendMode.HGDB


def _coerce_port(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 9669


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)


def _get_config_value(
    config: dict[str, Any], key: str, env_key: str, default: Any
) -> Any:
    if key in config and config[key] is not None:
        return config[key]
    if env_key and env_key in os.environ:
        return os.environ[env_key]
    return default


def _get_database_config(config: dict[str, Any], database_name: str) -> dict[str, Any]:
    database_mapping = config.get("nebulagraph_databases", {})
    if not isinstance(database_mapping, dict):
        return {}

    database_config = database_mapping.get(database_name, {})
    if not isinstance(database_config, dict):
        return {}

    return database_config
