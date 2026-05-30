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
    assert "k8sdeployment:commerce:payments-api" in node_ids
    assert "k8sservice:commerce:payments-api" in node_ids
    assert "ingress:commerce:payments-api" in node_ids
    assert "serviceaccount:commerce:payments-api" in node_ids
    assert "networkpolicy:commerce:payments-api-ingress" in node_ids
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
    assert ("k8sdeployment:commerce:payments-api", "RUNS_AS", "serviceaccount:commerce:payments-api") in edge_types
    assert ("ingress:commerce:payments-api", "ROUTES_TO", "k8sservice:commerce:payments-api") in edge_types
    assert ("k8sservice:commerce:payments-api", "ROUTES_TO", "k8sdeployment:commerce:payments-api") in edge_types
    assert ("networkpolicy:commerce:payments-api-ingress", "ALLOWS", "k8sdeployment:commerce:payments-api") in edge_types


def test_repository_collector_matches_k8s_service_selectors_to_deployment_labels() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "payments-api")
    edge_types = _edge_types(fixture)

    deployment = next(node for node in fixture.nodes if node.id == "k8sdeployment:commerce:payments-api")
    service = next(node for node in fixture.nodes if node.id == "k8sservice:commerce:payments-api")

    assert deployment.properties["labels"] == {"app": "payments-api", "tier": "backend"}
    assert service.properties["selector"] == {"app": "payments-api"}
    assert ("k8sservice:commerce:payments-api", "ROUTES_TO", "k8sdeployment:commerce:payments-api") in edge_types


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


def test_repository_collector_redacts_sensitive_config_values_from_serialized_output() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "sensitive-config")
    serialized = fixture.model_dump_json()

    forbidden_values = [
        "FakePassword123!",
        "AnotherFakePassword456!",
        "YetAnotherFakePassword789!",
        "apiuser",
        "dbuser",
        "brokeruser",
        "fake-query-token",
        "Bearer fake-bearer-token-1234567890abcdef",
        "fake-api-key-1234567890abcdef",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "fakeSignatureValue1234567890",
        "-----BEGIN PRIVATE KEY-----",
        "fake-private-key-material",
        "topic-secret-looking-1234567890abcdef",
        "queue-secret-looking-abcdef1234567890",
        "QWxhZGRpbjpPcGVuU2VzYW1lVG9rZW4xMjM0NTY3ODkw",
        "postgres://dbuser:FakePassword123!@db.safe.internal:5432/customerdb",
        "amqp://brokeruser:AnotherFakePassword456!@rabbit.safe.internal:5672/vhost",
        "https://apiuser:YetAnotherFakePassword789!@payments.safe.internal:8443/v1/payments",
    ]
    for forbidden in forbidden_values:
        assert forbidden not in serialized


def test_repository_collector_preserves_safe_redacted_config_metadata() -> None:
    fixture = collect_repository(FIXTURE_ROOT / "sensitive-config")

    database = next(node for node in fixture.nodes if node.type == "Database")
    assert database.properties["engine"] == "postgres"
    assert database.properties["config_key"] == "DATABASE_URL"
    assert database.properties["host"] == "db.safe.internal"
    assert database.properties["port"] == 5432
    assert database.properties["database_name"] == "customerdb"
    assert database.properties["scheme"] == "postgres"
    assert database.properties["value_redacted"] is True
    assert database.properties["redaction_reason"] == "sensitive_config_value"

    broker = next(node for node in fixture.nodes if node.type == "Broker")
    assert broker.properties["broker_type"] == "amqp"
    assert broker.properties["config_key"] == "BROKER_URL"
    assert broker.properties["host"] == "rabbit.safe.internal"
    assert broker.properties["port"] == 5672
    assert broker.properties["resource_name"] == "vhost"
    assert broker.properties["value_redacted"] is True

    endpoint = next(node for node in fixture.nodes if node.id == "endpointref:sensitive-config:payments_api_url")
    assert endpoint.properties["config_key"] == "PAYMENTS_API_URL"
    assert endpoint.properties["scheme"] == "https"
    assert endpoint.properties["host"] == "payments.safe.internal"
    assert endpoint.properties["port"] == 8443
    assert endpoint.properties["resource_name"] == "payments"
    assert endpoint.properties["value_redacted"] is True
    assert endpoint.properties["redaction_reason"] == "sensitive_config_value"

    safe_topic = next(node for node in fixture.nodes if node.id == "topic:safe_topic")
    assert safe_topic.properties["topic_name"] == "public.events"
    assert safe_topic.properties["value_redacted"] is True

    secret_topic = next(node for node in fixture.nodes if node.id == "topic:secret_topic")
    assert "topic_name" not in secret_topic.properties
