REQUIRED_SCHEMA_STATEMENTS = [
    (
        "CREATE TAG IF NOT EXISTS Entity("
        "name string, "
        "entity_type string, "
        "description string, "
        "source_id string, "
        "additional_properties string, "
        "database_name string"
        ")"
    ),
    (
        "CREATE TAG IF NOT EXISTS Hyperedge("
        "edge_hash string, "
        "id_set string, "
        "description string, "
        "keywords string, "
        "weight double, "
        "source_id string, "
        "arity int, "
        "database_name string"
        ")"
    ),
    "CREATE EDGE IF NOT EXISTS MEMBER_OF(database_name string)",
    "CREATE EDGE IF NOT EXISTS HAS_MEMBER(database_name string)",
]


def schema_statements_for_space(space_name: str) -> list[str]:
    trimmed_space_name = str(space_name).strip()
    if not trimmed_space_name:
        raise ValueError("NebulaGraph space name must not be empty")
    if "`" in trimmed_space_name:
        raise ValueError("NebulaGraph space name must not contain backticks")

    return [f"USE `{trimmed_space_name}`", *REQUIRED_SCHEMA_STATEMENTS]
