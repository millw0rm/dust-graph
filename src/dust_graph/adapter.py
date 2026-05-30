"""Graph adapter contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from dust_graph.models import GraphEdge, GraphFixture, GraphNode, QueryResult


@runtime_checkable
class GraphAdapter(Protocol):
    """Backend-neutral graph storage interface.

    Kuzu and other persistent backends should implement this protocol after the
    in-memory contract has stabilized.
    """

    def upsert_node(self, node: GraphNode) -> GraphNode:
        """Create or replace a node by ID."""
        ...

    def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create or replace an edge by stable ID."""
        ...

    def bulk_import(self, fixture: GraphFixture | Iterable[GraphNode | GraphEdge]) -> None:
        """Import a fixture or iterable of graph facts."""
        ...

    def query(self, statement: str, parameters: dict[str, Any] | None = None) -> QueryResult:
        """Run a backend-specific query and return row dictionaries."""
        ...
