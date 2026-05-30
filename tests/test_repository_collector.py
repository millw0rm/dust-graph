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


def test_repository_collector_extracts_openapi_endpoint_metadata() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "payments-api")
    openapi_path = str((FIXTURE_ROOT / "payments-api" / "openapi.yaml").resolve())

    get_endpoint = next(node for node in fixture.nodes if node.id == "endpoint:payments-api:get:payments")
    post_endpoint = next(node for node in fixture.nodes if node.id == "endpoint:payments-api:post:payments")

    assert get_endpoint.properties["method"] == "GET"
    assert get_endpoint.properties["path"] == "/payments"
    assert get_endpoint.properties["operation_id"] == "listPayments"
    assert get_endpoint.properties["tags"] == ["payments"]
    assert get_endpoint.properties["summary"] == "List payments"
    assert get_endpoint.properties["security_requirements"] == ["OAuth2:payments:read"]
    assert get_endpoint.properties["request_body_content_types"] == []
    assert get_endpoint.properties["response_status_codes"] == ["200", "401"]
    assert get_endpoint.properties["source_path"] == openapi_path
    assert get_endpoint.metadata.source_ref == openapi_path
    assert {evidence.source_id for evidence in get_endpoint.metadata.evidence} == {openapi_path}

    assert post_endpoint.properties["method"] == "POST"
    assert post_endpoint.properties["path"] == "/payments"
    assert post_endpoint.properties["operation_id"] == "createPayment"
    assert post_endpoint.properties["tags"] == ["payments"]
    assert post_endpoint.properties["summary"] == "Create a payment"
    assert post_endpoint.properties["security_requirements"] == ["ApiKeyAuth"]
    assert post_endpoint.properties["request_body_content_types"] == [
        "application/json",
        "application/x-www-form-urlencoded",
    ]
    assert post_endpoint.properties["response_status_codes"] == ["201", "400", "401"]
    assert post_endpoint.metadata.source_ref == openapi_path


def test_repository_collector_creates_openapi_access_metadata_for_secured_endpoints() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "payments-api")
    openapi_path = str((FIXTURE_ROOT / "payments-api" / "openapi.yaml").resolve())
    edge_types = _edge_types(fixture)

    api = next(node for node in fixture.nodes if node.id == "api:payments-api:payments-api:v1")
    get_endpoint = next(node for node in fixture.nodes if node.id == "endpoint:payments-api:get:payments")
    post_endpoint = next(node for node in fixture.nodes if node.id == "endpoint:payments-api:post:payments")
    oauth_permission = next(
        node
        for node in fixture.nodes
        if node.type == "Permission" and node.properties["openapi_security_requirement"] == "OAuth2:payments:read"
    )
    api_key_permission = next(
        node
        for node in fixture.nodes
        if node.type == "Permission" and node.properties["openapi_security_requirement"] == "ApiKeyAuth"
    )

    assert api.properties["security_schemes"] == ["ApiKeyAuth", "OAuth2"]
    assert api.properties["security_scheme_types"] == ["ApiKeyAuth:apiKey", "OAuth2:oauth2"]

    assert get_endpoint.properties["security_schemes"] == ["OAuth2"]
    assert get_endpoint.properties["security_scopes"] == ["payments:read"]
    assert oauth_permission.id in get_endpoint.properties["required_permission_ids"]

    assert post_endpoint.properties["security_schemes"] == ["ApiKeyAuth"]
    assert api_key_permission.id in post_endpoint.properties["required_permission_ids"]

    assert oauth_permission.properties["source_path"] == openapi_path
    assert oauth_permission.properties["openapi_security_scheme"] == "OAuth2"
    assert oauth_permission.properties["openapi_security_scheme_type"] == "oauth2"
    assert oauth_permission.properties["openapi_security_scope"] == "payments:read"
    assert oauth_permission.metadata.source_ref == openapi_path
    assert {evidence.source_id for evidence in oauth_permission.metadata.evidence} == {openapi_path}
    assert (oauth_permission.id, "CAN_CALL", get_endpoint.id) in edge_types
    assert (api_key_permission.id, "CAN_CALL", post_endpoint.id) in edge_types
