from pathlib import Path

import pytest

from dust_graph.collectors.repositories import collect_repository
from dust_graph.models import GraphFixture
from dust_graph.resolvers.cross_repository import resolve_cross_repository_context
from dust_graph.schema import validate_graph_fixture_schema

FIXTURE_ROOT = Path("tests/fixtures/repositories")


def _edge_types(fixture: GraphFixture) -> set[tuple[str, str, str]]:
    return {(edge.source, edge.type, edge.target) for edge in fixture.edges}


def _edges_of_type(fixture: GraphFixture, edge_type: str):
    return [edge for edge in fixture.edges if edge.type == edge_type]


def test_cross_repository_resolver_requires_multiple_fixtures() -> None:
    payments = collect_repository(FIXTURE_ROOT / "payments-api")

    with pytest.raises(ValueError, match="at least two GraphFixture"):
        resolve_cross_repository_context(payments)


def test_cross_repository_resolver_infers_api_and_shared_messaging_relationships() -> None:
    payments = collect_repository(FIXTURE_ROOT / "payments-api")
    orders = collect_repository(FIXTURE_ROOT / "orders-worker")

    resolved = resolve_cross_repository_context(payments, orders)
    edge_types = _edge_types(resolved)

    assert validate_graph_fixture_schema(resolved) is resolved
    assert ("service:orders-worker", "CALLS", "endpoint:payments-api:get:payments") in edge_types
    assert ("repo:orders-worker", "CALLS", "repo:payments-api") in edge_types
    assert any(
        source == "service:payments-api" and edge_type == "PUBLISHES_TO" and target.startswith("topic:")
        for source, edge_type, target in edge_types
    )
    assert any(
        source == "service:orders-worker" and edge_type == "CONSUMES_FROM" and target.startswith("topic:")
        for source, edge_type, target in edge_types
    )

    api_edge = next(
        edge
        for edge in _edges_of_type(resolved, "CALLS")
        if edge.source == "service:orders-worker" and edge.target == "endpoint:payments-api:get:payments"
    )
    assert api_edge.properties["confidence_level"] == "high"
    assert api_edge.properties["matched_on"] == "service/url plus endpoint path"
    assert api_edge.metadata.source_system == "cross_repository_resolver"
    evidence_files = {Path(evidence.source_id or "").name for evidence in api_edge.metadata.evidence}
    assert evidence_files >= {"config.yaml", "openapi.yaml"}


def test_cross_repository_resolver_infers_shared_database_access_from_database_names() -> None:
    payments = collect_repository(FIXTURE_ROOT / "payments-api")
    reporting = collect_repository(FIXTURE_ROOT / "reporting-job")

    resolved = resolve_cross_repository_context(payments, reporting)
    edge_types = _edge_types(resolved)

    assert any(
        source == "service:reporting-job" and edge_type == "READS_FROM" and target.startswith("database:")
        for source, edge_type, target in edge_types
    )
    assert any(
        source == "service:payments-api" and edge_type == "WRITES_TO" and target.startswith("database:")
        for source, edge_type, target in edge_types
    )
    database_edges = [
        edge
        for edge in resolved.edges
        if edge.type in {"READS_FROM", "WRITES_TO"} and edge.target.startswith("database:")
    ]
    assert any(edge.properties.get("matched_value_redacted") == "payments" for edge in database_edges)
