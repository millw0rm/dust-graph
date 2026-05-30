"""In-memory graph adapter for tests, fixtures, and early CLI workflows."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dust_graph.models import GraphEdge, GraphFixture, GraphNode, QueryResult


class InMemoryGraphAdapter:
    """Simple dictionary-backed graph adapter.

    The query surface is intentionally tiny and deterministic. It supports a few
    named statements so tests and examples can run before a full query engine or
    Kuzu adapter exists.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}

    def upsert_node(self, node: GraphNode) -> GraphNode:
        self.nodes[node.id] = node
        return node

    def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"edge {edge.stable_id} references unknown node")
        self.edges[edge.stable_id] = edge
        return edge

    def bulk_import(self, fixture: GraphFixture | Iterable[GraphNode | GraphEdge]) -> None:
        if isinstance(fixture, GraphFixture):
            facts: list[GraphNode | GraphEdge] = [*fixture.nodes, *fixture.edges]
        else:
            facts = list(fixture)

        for fact in facts:
            if isinstance(fact, GraphNode):
                self.upsert_node(fact)
        for fact in facts:
            if isinstance(fact, GraphEdge):
                self.upsert_edge(fact)

    def query(self, statement: str, parameters: dict[str, Any] | None = None) -> QueryResult:
        parameters = parameters or {}
        if statement == "nodes":
            node_type = parameters.get("type")
            return [
                {"node": node}
                for node in self.nodes.values()
                if node_type is None or node.type == node_type
            ]
        if statement == "edges":
            edge_type = parameters.get("type")
            return [
                {"edge": edge}
                for edge in self.edges.values()
                if edge_type is None or edge.type == edge_type
            ]
        if statement == "neighbors":
            node_id = parameters["id"]
            return [
                {"edge": edge, "node": self.nodes[edge.target]}
                for edge in self.edges.values()
                if edge.source == node_id
            ]
        raise ValueError(f"unsupported in-memory query statement: {statement}")
