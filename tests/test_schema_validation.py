from pathlib import Path

import pytest
from typer.testing import CliRunner

from dust_graph.cli import app
from dust_graph.collectors.repositories import collect_repository
from dust_graph.fixtures import load_fixture
from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode
from dust_graph.schema import GraphSchemaError, validate_graph_fixture_schema

SAMPLE_FIXTURE = Path("fixtures/sample_graph.yaml")
REPOSITORY_FIXTURE_ROOT = Path("tests/fixtures/repositories/payments-api")


def _metadata(source_ref: str = "test://fixture") -> GraphMetadata:
    return GraphMetadata(source_system="unit_test", source_ref=source_ref, confidence=1.0)


def _fixture(
    *,
    node_type: str = "Service",
    edge_type: str = "CALLS",
    metadata: GraphMetadata | None = None,
) -> GraphFixture:
    return GraphFixture(
        name="schema-test",
        nodes=[
            GraphNode(
                id="service:source",
                type=node_type,
                labels=[node_type],
                metadata=metadata or _metadata("test://source"),
            ),
            GraphNode(
                id="service:target",
                type="Service",
                labels=["Service"],
                metadata=_metadata("test://target"),
            ),
        ],
        edges=[
            GraphEdge(
                type=edge_type,
                source="service:source",
                target="service:target",
                metadata=_metadata("test://edge"),
            )
        ],
    )


def test_valid_fixture_passes_schema_validation() -> None:
    fixture = load_fixture(SAMPLE_FIXTURE, validate_schema=True)

    assert validate_graph_fixture_schema(fixture) is fixture


def test_unknown_node_type_fails_schema_validation() -> None:
    fixture = _fixture(node_type="MysteryService")

    with pytest.raises(GraphSchemaError, match="unknown node type 'MysteryService'"):
        validate_graph_fixture_schema(fixture)


def test_unknown_edge_type_fails_schema_validation() -> None:
    fixture = _fixture(edge_type="TELEPORTS_TO")

    with pytest.raises(GraphSchemaError, match="unknown edge type 'TELEPORTS_TO'"):
        validate_graph_fixture_schema(fixture)


def test_missing_required_common_metadata_fails_schema_validation() -> None:
    fixture = _fixture(metadata=GraphMetadata(source_ref="test://source", confidence=1.0))

    with pytest.raises(GraphSchemaError, match="missing required metadata field 'source_system'"):
        validate_graph_fixture_schema(fixture)


def test_repository_collector_output_passes_schema_validation() -> None:
    fixture = collect_repository(REPOSITORY_FIXTURE_ROOT)

    assert validate_graph_fixture_schema(fixture) is fixture


def test_validate_schema_cli_command() -> None:
    result = CliRunner().invoke(app, ["validate-schema", str(SAMPLE_FIXTURE)])

    assert result.exit_code == 0
    assert "valid schema" in result.output
