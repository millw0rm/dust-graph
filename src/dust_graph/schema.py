"""Schema vocabulary validation for Dust Graph fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "graph.schema.yaml"


class GraphSchemaError(ValueError):
    """Raised when a graph fixture does not match the canonical schema."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class GraphSchema:
    """Loaded graph schema vocabulary."""

    path: Path
    common_metadata: dict[str, dict[str, Any]]
    node_types: frozenset[str]
    edge_types: frozenset[str]


@lru_cache(maxsize=8)
def load_graph_schema(path: Path | str = DEFAULT_SCHEMA_PATH) -> GraphSchema:
    """Load the Dust Graph schema vocabulary from YAML."""

    schema_path = Path(path)
    raw = yaml.safe_load(schema_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"schema root must be a mapping: {schema_path}")

    common_metadata = raw.get("common_metadata")
    node_types = raw.get("node_types")
    edge_types = raw.get("edge_types")
    if not isinstance(common_metadata, dict):
        raise ValueError("schema common_metadata must be a mapping")
    if not isinstance(node_types, dict):
        raise ValueError("schema node_types must be a mapping")
    if not isinstance(edge_types, dict):
        raise ValueError("schema edge_types must be a mapping")

    normalized_metadata: dict[str, dict[str, Any]] = {}
    for field_name, definition in common_metadata.items():
        if not isinstance(field_name, str) or not isinstance(definition, dict):
            raise ValueError("schema common_metadata entries must be mappings keyed by strings")
        normalized_metadata[field_name] = definition

    return GraphSchema(
        path=schema_path,
        common_metadata=normalized_metadata,
        node_types=frozenset(str(node_type) for node_type in node_types),
        edge_types=frozenset(str(edge_type) for edge_type in edge_types),
    )


def validate_graph_fixture_schema(
    fixture: GraphFixture,
    schema: GraphSchema | None = None,
) -> GraphFixture:
    """Validate a graph fixture against the configured Dust Graph schema."""

    graph_schema = schema or load_graph_schema()
    errors: list[str] = []

    for index, node in enumerate(fixture.nodes):
        location = f"nodes[{index}] ({node.id})"
        if node.type not in graph_schema.node_types:
            errors.append(f"{location}: unknown node type '{node.type}'")
        errors.extend(_validate_common_metadata(location, node, graph_schema.common_metadata))

    for index, edge in enumerate(fixture.edges):
        location = f"edges[{index}] ({edge.stable_id})"
        if edge.type not in graph_schema.edge_types:
            errors.append(f"{location}: unknown edge type '{edge.type}'")
        errors.extend(_validate_common_metadata(location, edge, graph_schema.common_metadata))

    if errors:
        raise GraphSchemaError(errors)
    return fixture


def _validate_common_metadata(
    location: str,
    record: GraphNode | GraphEdge,
    common_metadata: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    metadata = record.metadata
    for field_name, definition in common_metadata.items():
        value = _metadata_value(record, metadata, field_name)
        if definition.get("required") is True and _is_missing(value):
            errors.append(f"{location}: missing required metadata field '{field_name}'")
            continue
        if _is_missing(value):
            continue
        errors.extend(_validate_metadata_value(location, field_name, value, definition))
    return errors


def _metadata_value(record: GraphNode | GraphEdge, metadata: GraphMetadata, field_name: str) -> Any:
    if field_name == "id":
        return record.id if isinstance(record, GraphNode) else record.stable_id
    return getattr(metadata, field_name, None)


def _validate_metadata_value(
    location: str,
    field_name: str,
    value: Any,
    definition: dict[str, Any],
) -> list[str]:
    expected_type = definition.get("type")
    errors: list[str] = []

    if expected_type == "string" and not isinstance(value, str):
        errors.append(f"{location}: metadata field '{field_name}' must be a string")
    elif expected_type == "number" and (isinstance(value, bool) or not isinstance(value, int | float)):
        errors.append(f"{location}: metadata field '{field_name}' must be a number")
    elif expected_type == "datetime" and not isinstance(value, datetime):
        errors.append(f"{location}: metadata field '{field_name}' must be a datetime")

    if isinstance(value, int | float):
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        if isinstance(minimum, int | float) and value < minimum:
            errors.append(f"{location}: metadata field '{field_name}' must be >= {minimum}")
        if isinstance(maximum, int | float) and value > maximum:
            errors.append(f"{location}: metadata field '{field_name}' must be <= {maximum}")

    return errors


def _is_missing(value: Any) -> bool:
    return value is None or value == ""
