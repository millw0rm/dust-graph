from pathlib import Path

import pytest
from typer.testing import CliRunner

from dust_graph.adapters import InMemoryGraphAdapter
from dust_graph.cli import app
from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode
from dust_graph.queries import SAVED_QUERIES, execute_saved_query

SAMPLE_FIXTURE = Path("fixtures/sample_graph.yaml")


def _node(node_id: str, node_type: str, name: str | None = None) -> GraphNode:
    return GraphNode(
        id=node_id,
        type=node_type,
        labels=[node_type],
        metadata=GraphMetadata(name=name, source_system="test", confidence=1.0),
    )


def _edge(source: str, edge_type: str, target: str) -> GraphEdge:
    return GraphEdge(
        type=edge_type,
        source=source,
        target=target,
        metadata=GraphMetadata(source_system="test", confidence=1.0),
    )


def _adapter() -> InMemoryGraphAdapter:
    fixture = GraphFixture(
        version=1,
        name="saved-query-test",
        nodes=[
            _node("repo:payments", "Repository", "payments"),
            _node("repo:shared", "Repository", "shared"),
            _node("service:payments", "Service", "payments"),
            _node("service:ledger", "Service", "ledger"),
            _node("api:payments", "API", "Payments API"),
            _node("db:payments", "Database", "payments-db"),
            _node("namespace:prod", "Namespace", "prod"),
            _node("user:alice", "User", "Alice"),
            _node("group:finance", "Group", "Finance"),
        ],
        edges=[
            _edge("repo:payments", "CONTAINS", "service:payments"),
            _edge("repo:shared", "CONTAINS", "service:ledger"),
            _edge("service:payments", "EXPOSES", "api:payments"),
            _edge("service:payments", "CONNECTS_TO", "db:payments"),
            _edge("service:payments", "DEPLOYS_TO", "namespace:prod"),
            _edge("service:payments", "CALLS", "service:ledger"),
            _edge("user:alice", "CAN_CALL", "api:payments"),
            _edge("group:finance", "CAN_CALL", "api:payments"),
        ],
    )
    adapter = InMemoryGraphAdapter()
    adapter.bulk_import(fixture)
    return adapter


def test_saved_query_registration() -> None:
    assert set(SAVED_QUERIES) == {
        "repository_apis",
        "api_reachable_databases",
        "api_allowed_principals",
        "repository_deployed_services",
        "runtime_service_contributing_repositories",
    }
    assert SAVED_QUERIES["repository_apis"].description
    assert {parameter.name for parameter in SAVED_QUERIES["repository_apis"].parameters} >= {
        "repository_id",
        "repository_slug",
        "environment",
    }


@pytest.mark.parametrize(
    ("name", "parameters", "expected_key", "expected_id"),
    [
        ("repository_apis", {"repository_id": "repo:payments"}, "api", "api:payments"),
        ("api_reachable_databases", {"api_id": "api:payments"}, "database", "db:payments"),
        ("api_allowed_principals", {"api_id": "api:payments"}, "principal", "group:finance"),
        (
            "repository_deployed_services",
            {"repository_slug": "payments"},
            "deployment_target",
            "namespace:prod",
        ),
        (
            "runtime_service_contributing_repositories",
            {"service_id": "service:payments"},
            "repository",
            "repo:payments",
        ),
    ],
)
def test_saved_query_successful_execution(
    name: str, parameters: dict[str, object], expected_key: str, expected_id: str
) -> None:
    rows = execute_saved_query(_adapter(), name, parameters)

    assert rows
    assert any(row[expected_key]["id"] == expected_id for row in rows)
    assert rows == sorted(rows, key=lambda row: str(row))


def test_saved_query_missing_parameters() -> None:
    with pytest.raises(
        ValueError, match="missing required parameter: repository_id or repository_slug"
    ):
        execute_saved_query(_adapter(), "repository_apis", {})


def test_saved_query_empty_results() -> None:
    rows = execute_saved_query(_adapter(), "repository_apis", {"repository_id": "repo:missing"})

    assert rows == []


def test_saved_query_cli_command_outputs_json() -> None:
    result = CliRunner().invoke(
        app,
        [
            "query",
            str(SAMPLE_FIXTURE),
            "repository_apis",
            "--param",
            "repository_id=repo:dust-api",
        ],
    )

    assert result.exit_code == 0
    assert '"api:dust-api-public"' in result.output
