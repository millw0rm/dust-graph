from pydantic import ValidationError

from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode, SourceEvidence


def test_graph_fixture_validates_edge_endpoints() -> None:
    fixture = GraphFixture(
        name="valid",
        nodes=[
            GraphNode(id="service:a", type="Service"),
            GraphNode(id="api:a", type="API"),
        ],
        edges=[GraphEdge(type="EXPOSES", source="service:a", target="api:a")],
    )

    assert fixture.edges[0].stable_id == "service:a:EXPOSES:api:a"


def test_graph_fixture_rejects_missing_edge_endpoint() -> None:
    try:
        GraphFixture(
            name="invalid",
            nodes=[GraphNode(id="service:a", type="Service")],
            edges=[GraphEdge(type="EXPOSES", source="service:a", target="api:missing")],
        )
    except ValidationError as error:
        assert "unknown node IDs" in str(error)
    else:
        raise AssertionError("fixture should reject missing edge endpoints")


def test_source_evidence_confidence_is_bounded() -> None:
    try:
        SourceEvidence(source="fixture", confidence=1.5)
    except ValidationError as error:
        assert "less than or equal to 1" in str(error)
    else:
        raise AssertionError("confidence should be bounded")


def test_metadata_seen_window_must_be_ordered() -> None:
    try:
        GraphMetadata(first_seen="2026-01-02T00:00:00Z", last_seen="2026-01-01T00:00:00Z")
    except ValidationError as error:
        assert "first_seen must be before" in str(error)
    else:
        raise AssertionError("metadata should reject an inverted seen window")
