#!/usr/bin/env python3
import argparse
import importlib.util
from pathlib import Path
import sys
from typing import Callable


def _load_schema_statements_for_space() -> Callable[[str], list[str]]:
    try:
        from hyperrag.nebulagraph_schema import schema_statements_for_space

        return schema_statements_for_space
    except ModuleNotFoundError:
        pass

    module_path = (
        Path(__file__).resolve().parents[1] / "hyperrag" / "nebulagraph_schema.py"
    )
    spec = importlib.util.spec_from_file_location(
        "hyperrag.nebulagraph_schema",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.schema_statements_for_space


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyperrag-nebulagraph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    schema_check_parser = subparsers.add_parser(
        "schema-check",
        help="Print NebulaGraph schema check statements for a graph space.",
    )
    schema_check_parser.add_argument("--space", required=True)

    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Placeholder for future .hgdb to NebulaGraph migration wiring.",
    )
    migrate_parser.add_argument("--hgdb", required=True)
    migrate_parser.add_argument("--database", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Placeholder for future NebulaGraph validation wiring.",
    )
    validate_parser.add_argument("--hgdb", required=True)
    validate_parser.add_argument("--database", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schema-check":
        schema_statements_for_space = _load_schema_statements_for_space()
        try:
            statements = schema_statements_for_space(args.space)
        except ValueError as exc:
            parser.error(str(exc))
        for statement in statements:
            print(statement)
        return 0

    if args.command in {"migrate", "validate"}:
        parser.error(f"Command {args.command!r} requires implementation wiring")

    parser.error(f"Unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
