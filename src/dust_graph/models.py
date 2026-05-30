"""Core graph model definitions for Dust Graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ScalarValue = str | int | float | bool | None
PropertyValue = ScalarValue | list[ScalarValue] | dict[str, ScalarValue]


class SourceEvidence(BaseModel):
    """A source record that supports a node or edge fact."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., min_length=1, description="System, file, log, or collector name.")
    source_id: str | None = Field(default=None, description="Upstream identifier or URI.")
    observed_at: datetime | None = Field(default=None, description="When this evidence was observed.")
    confidence: float | None = Field(default=None, ge=0, le=1)
    detail: str | None = Field(default=None, description="Short human-readable evidence detail.")


class GraphMetadata(BaseModel):
    """Common metadata carried by graph facts."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    owner: str | None = None
    environment: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_seen_window(self) -> GraphMetadata:
        if self.first_seen and self.last_seen and self.first_seen > self.last_seen:
            raise ValueError("first_seen must be before or equal to last_seen")
        return self


class GraphNode(BaseModel):
    """Backend-neutral graph node."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, PropertyValue] = Field(default_factory=dict)
    metadata: GraphMetadata = Field(default_factory=GraphMetadata)

    @field_validator("labels")
    @classmethod
    def labels_must_be_non_empty(cls, labels: list[str]) -> list[str]:
        if any(not label for label in labels):
            raise ValueError("labels must not contain empty values")
        return labels


class GraphEdge(BaseModel):
    """Backend-neutral graph edge from one node to another."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, min_length=1)
    type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    directed: bool = True
    properties: dict[str, PropertyValue] = Field(default_factory=dict)
    metadata: GraphMetadata = Field(default_factory=GraphMetadata)

    @property
    def stable_id(self) -> str:
        """Return a deterministic identifier when a fixture omits an explicit edge ID."""

        return self.id or f"{self.source}:{self.type}:{self.target}"


class GraphFixture(BaseModel):
    """Importable collection of graph nodes and edges."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    name: str = Field(..., min_length=1)
    description: str | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_edge_endpoints(self) -> GraphFixture:
        node_ids = {node.id for node in self.nodes}
        missing = sorted(
            endpoint
            for edge in self.edges
            for endpoint in (edge.source, edge.target)
            if endpoint not in node_ids
        )
        if missing:
            raise ValueError(f"edges reference unknown node IDs: {', '.join(missing)}")
        return self


QueryResult = list[dict[str, Any]]
