"""Kuzu graph adapter skeleton.

The adapter keeps Kuzu behind the repository-owned ``GraphAdapter``
protocol while Kuzu remains an optional dependency.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from dust_graph.models import GraphEdge, GraphFixture, GraphNode, QueryResult

KUZU_EXTRA_MESSAGE = (
    "Kuzu support requires the optional dependency 'kuzu'. "
    "Install it with `pip install 'dust-graph[kuzu]'` or `pip install kuzu`."
)


class KuzuOptionalDependencyError(ImportError):
    """Raised when the optional Kuzu dependency is not installed."""


class KuzuGraphAdapter:
    """Kuzu-backed graph adapter implementing the GraphAdapter protocol.

    The first Kuzu implementation intentionally stores the backend-neutral
    Pydantic node and edge payloads as JSON strings on generic Kuzu tables.
    This gives Dust Graph an executable persistence seam without committing the
    domain model to Kuzu-specific labels or property schemas too early.
    """

    def __init__(self, database_path: str | Path = ":memory:", *, initialize_schema: bool = True) -> None:
        self.database_path = str(database_path)
        kuzu = self._load_kuzu_module()
        self.database = kuzu.Database(self.database_path)
        self.connection = kuzu.Connection(self.database)
        if initialize_schema:
            self._initialize_schema()

    def upsert_node(self, node: GraphNode) -> GraphNode:
        """Create or replace a generic graph node by stable ID."""

        self.connection.execute(
            "MERGE (n:GraphNode {id: $id}) "
            "SET n.type = $type, n.labels_json = $labels_json, n.payload = $payload",
            {
                "id": node.id,
                "type": node.type,
                "labels_json": json.dumps(node.labels),
                "payload": node.model_dump_json(),
            },
        )
        return node

    def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create or replace a generic graph edge by stable ID."""

        self.connection.execute(
            "MATCH (:GraphNode)-[e:GraphEdge]->(:GraphNode) "
            "WHERE e.stable_id = $stable_id DELETE e",
            {"stable_id": edge.stable_id},
        )
        self.connection.execute(
            "MATCH (source:GraphNode {id: $source}), (target:GraphNode {id: $target}) "
            "CREATE (source)-[:GraphEdge {stable_id: $stable_id, type: $type, "
            "directed: $directed, payload: $payload}]->(target)",
            {
                "source": edge.source,
                "target": edge.target,
                "stable_id": edge.stable_id,
                "type": edge.type,
                "directed": edge.directed,
                "payload": edge.model_dump_json(),
            },
        )
        return edge

    def bulk_import(self, fixture: GraphFixture | Iterable[GraphNode | GraphEdge]) -> None:
        """Import a fixture or iterable of graph facts."""

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
        """Run a Kuzu Cypher statement and return rows as dictionaries."""

        result = self.connection.execute(statement, parameters or {})
        if isinstance(result, list):
            if not result:
                return []
            result = result[-1]
        return result.rows_as_dict().get_all()

    @staticmethod
    def _load_kuzu_module() -> Any:
        if importlib.util.find_spec("kuzu") is None:
            raise KuzuOptionalDependencyError(KUZU_EXTRA_MESSAGE)
        return importlib.import_module("kuzu")

    def _initialize_schema(self) -> None:
        self.connection.execute(
            "CREATE NODE TABLE IF NOT EXISTS GraphNode("
            "id STRING, type STRING, labels_json STRING, payload STRING, PRIMARY KEY (id))"
        )
        self.connection.execute(
            "CREATE REL TABLE IF NOT EXISTS GraphEdge("
            "FROM GraphNode TO GraphNode, stable_id STRING, type STRING, "
            "directed BOOL, payload STRING)"
        )
