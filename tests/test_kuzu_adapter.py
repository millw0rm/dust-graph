from __future__ import annotations

import importlib.util

import pytest

from dust_graph.adapter import GraphAdapter
from dust_graph.adapters.kuzu import KuzuGraphAdapter, KuzuOptionalDependencyError
from dust_graph.models import GraphEdge, GraphFixture, GraphNode


def test_kuzu_adapter_class_is_importable_without_kuzu_dependency() -> None:
    assert KuzuGraphAdapter.__name__ == "KuzuGraphAdapter"
    assert {"upsert_node", "upsert_edge", "bulk_import", "query"}.issubset(
        set(KuzuGraphAdapter.__dict__)
    )


def test_kuzu_adapter_missing_dependency_has_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    real_find_spec = importlib.util.find_spec

    def find_spec_without_kuzu(name: str, *args: object, **kwargs: object):
        if name == "kuzu":
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec_without_kuzu)

    with pytest.raises(KuzuOptionalDependencyError) as error:
        KuzuGraphAdapter()

    message = str(error.value)
    assert "optional dependency 'kuzu'" in message
    assert "dust-graph[kuzu]" in message


def test_kuzu_adapter_conforms_to_graph_adapter_when_dependency_is_available(tmp_path) -> None:
    pytest.importorskip("kuzu")

    adapter = KuzuGraphAdapter(tmp_path / "kuzu-db")
    fixture = GraphFixture(
        name="kuzu-smoke",
        nodes=[
            GraphNode(id="service:api", type="Service"),
            GraphNode(id="api:public", type="API"),
        ],
        edges=[GraphEdge(type="EXPOSES", source="service:api", target="api:public")],
    )

    adapter.bulk_import(fixture)

    assert isinstance(adapter, GraphAdapter)
    assert adapter.query("MATCH (n:GraphNode) RETURN n.id AS id ORDER BY id") == [
        {"id": "api:public"},
        {"id": "service:api"},
    ]
