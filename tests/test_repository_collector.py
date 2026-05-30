from pathlib import Path

from dust_graph.collectors.repositories import collect_repository

FIXTURE_ROOT = Path("tests/fixtures/repositories")


def _node_ids(fixture):
    return {node.id for node in fixture.nodes}


def _edge_types(fixture):
    return {(edge.source, edge.type, edge.target) for edge in fixture.edges}


def test_repository_collector_extracts_safe_service_api_k8s_and_runtime_metadata() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "payments-api")
    node_ids = _node_ids(fixture)
    edge_types = _edge_types(fixture)
    repo = next(node for node in fixture.nodes if node.id == "repo:payments-api")

    assert repo.properties["name"] == "payments-api"
    assert "JavaScript" in repo.properties["languages"]
    assert "Python" in repo.properties["languages"]
    assert "payments-api" in repo.properties["candidate_services"]
    assert repo.properties["ci_workflows"] == ["Payments CI"]

    assert "service:payments-api" in node_ids
    assert "api:payments-api:payments-api:v1" in node_ids
    assert "endpoint:payments-api:get:payments" in node_ids
    assert "namespace:commerce" in node_ids
    assert "k8sservice:commerce:payments-api" in node_ids
    assert "serviceaccount:commerce:payments-api" in node_ids
    assert "port:8080:tcp" in node_ids
    assert "port:80:tcp" in node_ids
    assert any(node.type == "Database" and node.properties["value_redacted"] for node in fixture.nodes)
    assert any(node.type == "Broker" and node.properties["value_redacted"] for node in fixture.nodes)
    assert any(node.type == "Topic" and node.properties["config_key"] == "PAYMENTS_TOPIC" for node in fixture.nodes)

    all_properties = repr([node.properties for node in fixture.nodes])
    assert "super-secret" not in all_properties
    assert "do-not-store-me" not in all_properties
    assert ("service:payments-api", "EXPOSES", "api:payments-api:payments-api:v1") in edge_types
    assert ("api:payments-api:payments-api:v1", "HAS_ENDPOINT", "endpoint:payments-api:get:payments") in edge_types
    assert ("service:payments-api", "RUNS_AS", "serviceaccount:commerce:payments-api") in edge_types


def test_repository_collector_supports_second_repository_for_cross_repo_relationships() -> None:
    payments = collect_repository(FIXTURE_ROOT / "payments-api")
    orders = collect_repository(FIXTURE_ROOT / "orders-worker")

    payments_topics = {node.id for node in payments.nodes if node.type == "Topic"}
    orders_topics = {node.id for node in orders.nodes if node.type == "Topic"}
    orders_repo = next(node for node in orders.nodes if node.id == "repo:orders-worker")

    assert "Python" in orders_repo.properties["languages"]
    assert orders_repo.properties["ci_workflows"] == ["unit-test"]
    assert "service:orders-worker" in _node_ids(orders)
    assert "port:9090:tcp" in _node_ids(orders)
    assert payments_topics & orders_topics == {"topic:payments_topic"}
    assert any(node.type == "Queue" and node.properties["config_key"] == "RABBITMQ_QUEUE" for node in orders.nodes)
