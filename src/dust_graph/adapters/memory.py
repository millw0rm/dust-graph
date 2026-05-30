"""In-memory graph adapter for tests, fixtures, and early CLI workflows."""

from __future__ import annotations

from collections import deque
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

    def edges_sorted(self) -> list[GraphEdge]:
        """Return all edges in deterministic stable-ID order."""

        return [self.edges[edge_id] for edge_id in sorted(self.edges)]

    def outgoing_edges(
        self, node_id: str, edge_types: set[str] | None = None
    ) -> list[GraphEdge]:
        """Return deterministic one-hop outgoing edges from a node."""

        return [
            edge
            for edge in self.edges_sorted()
            if edge.source == node_id and (edge_types is None or edge.type in edge_types)
        ]

    def incoming_edges(
        self, node_id: str, edge_types: set[str] | None = None
    ) -> list[GraphEdge]:
        """Return deterministic one-hop incoming edges to a node."""

        return [
            edge
            for edge in self.edges_sorted()
            if edge.target == node_id and (edge_types is None or edge.type in edge_types)
        ]

    def neighbors(
        self, node_id: str, *, edge_types: set[str] | None = None, direction: str = "out"
    ) -> list[tuple[GraphEdge, GraphNode]]:
        """Return deterministic one-hop neighbors for a node.

        Direction may be ``out``, ``in``, or ``both``. For inbound edges, the
        returned neighbor is the edge source; for outbound edges, it is the edge
        target.
        """

        if direction not in {"out", "in", "both"}:
            raise ValueError("direction must be 'out', 'in', or 'both'")

        pairs: list[tuple[GraphEdge, GraphNode]] = []
        if direction in {"out", "both"}:
            pairs.extend(
                (edge, self.nodes[edge.target])
                for edge in self.outgoing_edges(node_id, edge_types)
            )
        if direction in {"in", "both"}:
            pairs.extend(
                (edge, self.nodes[edge.source])
                for edge in self.incoming_edges(node_id, edge_types)
            )
        return sorted(pairs, key=lambda pair: (pair[1].id, pair[0].stable_id))

    def traverse_bounded(
        self,
        start_id: str,
        *,
        edge_types: set[str] | None = None,
        max_depth: int = 1,
        direction: str = "out",
        include_start: bool = False,
    ) -> list[tuple[GraphNode, list[GraphEdge]]]:
        """Return nodes reached within a bounded depth and their edge paths.

        Results are breadth-first and deterministic. Cycles are suppressed by
        retaining the shortest path discovered for each node.
        """

        if start_id not in self.nodes:
            return []
        if max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to 0")

        results: list[tuple[GraphNode, list[GraphEdge]]] = []
        visited = {start_id}
        queue: deque[tuple[str, list[GraphEdge]]] = deque([(start_id, [])])
        if include_start:
            results.append((self.nodes[start_id], []))

        while queue:
            node_id, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for edge, neighbor in self.neighbors(
                node_id, edge_types=edge_types, direction=direction
            ):
                if neighbor.id in visited:
                    continue
                next_path = [*path, edge]
                visited.add(neighbor.id)
                results.append((neighbor, next_path))
                queue.append((neighbor.id, next_path))

        return results

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
