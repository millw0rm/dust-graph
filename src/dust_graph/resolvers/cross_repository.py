"""Cross-repository relationship resolver."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from urllib.parse import urlparse

from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode, SourceEvidence


CONFIDENCE_LEVELS = ((0.85, "high"), (0.55, "medium"), (0.0, "low"))


@dataclass(frozen=True)
class RepositoryContext:
    fixture: GraphFixture
    repository: GraphNode
    services: tuple[GraphNode, ...]
    service_by_id: dict[str, GraphNode]
    api_by_id: dict[str, GraphNode]
    endpoint_by_id: dict[str, GraphNode]
    edge_by_stable_id: dict[str, GraphEdge]
    service_sources: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ApiProvider:
    context: RepositoryContext
    service: GraphNode
    api: GraphNode
    endpoint: GraphNode


@dataclass(frozen=True)
class ApiConsumerHint:
    context: RepositoryContext
    service: GraphNode
    endpoint: GraphNode


@dataclass(frozen=True)
class ResourceLink:
    context: RepositoryContext
    service: GraphNode
    resource: GraphNode
    edge: GraphEdge


def resolve_cross_repository_context(*fixtures: GraphFixture | Iterable[GraphFixture]) -> GraphFixture:
    """Infer cross-repository relationships from two or more repository fixtures."""

    normalized = _normalize_fixtures(fixtures)
    if len(normalized) < 2:
        raise ValueError("cross-repository resolution requires at least two GraphFixture objects")

    contexts = [_context_for(fixture) for fixture in normalized]
    nodes = _merge_nodes(normalized)
    edges = _merge_edges(normalized)
    for context in contexts:
        nodes.setdefault(context.repository.id, context.repository)

    for edge in _resolve_api_calls(contexts):
        edges.setdefault(edge.stable_id, edge)
    for edge in _resolve_broker_links(contexts):
        edges.setdefault(edge.stable_id, edge)
    for edge in _resolve_database_links(contexts):
        edges.setdefault(edge.stable_id, edge)

    return GraphFixture(
        name="cross-repository-context",
        description="Combined repository fixtures with inferred cross-repository relationships.",
        nodes=sorted(nodes.values(), key=lambda node: node.id),
        edges=sorted(edges.values(), key=lambda edge: edge.stable_id),
    )


def _normalize_fixtures(args: Sequence[GraphFixture | Iterable[GraphFixture]]) -> list[GraphFixture]:
    if len(args) == 1 and not isinstance(args[0], GraphFixture):
        fixtures = list(args[0])
    else:
        fixtures = list(args)  # type: ignore[list-item]
    if not all(isinstance(fixture, GraphFixture) for fixture in fixtures):
        raise TypeError("resolve_cross_repository_context accepts only GraphFixture objects")
    return fixtures


def _context_for(fixture: GraphFixture) -> RepositoryContext:
    repositories = [node for node in fixture.nodes if node.type == "Repository"]
    repository = repositories[0] if repositories else GraphNode(
        id=f"repo:{_slug(fixture.name)}",
        type="Repository",
        labels=["Repository"],
        metadata=_metadata("resolver", fixture.name, 0.4, [], "fixture without repository node"),
    )
    services = tuple(node for node in fixture.nodes if node.type == "Service")
    service_by_id = {node.id: node for node in services}
    edges = {edge.stable_id: edge for edge in fixture.edges}
    service_sources: dict[str, str] = {}
    for edge in fixture.edges:
        if edge.type == "CONTAINS" and edge.source == repository.id and edge.target in service_by_id:
            service_sources[edge.target] = edge.source
    return RepositoryContext(
        fixture=fixture,
        repository=repository,
        services=services,
        service_by_id=service_by_id,
        api_by_id={node.id: node for node in fixture.nodes if node.type == "API"},
        endpoint_by_id={node.id: node for node in fixture.nodes if node.type == "APIEndpoint"},
        edge_by_stable_id=edges,
        service_sources=service_sources,
    )


def _merge_nodes(fixtures: Sequence[GraphFixture]) -> dict[str, GraphNode]:
    nodes: dict[str, GraphNode] = {}
    for fixture in fixtures:
        for node in fixture.nodes:
            if node.id not in nodes:
                nodes[node.id] = node.model_copy(deep=True)
            else:
                existing = nodes[node.id]
                existing.properties.update({key: value for key, value in node.properties.items() if value is not None})
                existing.metadata.evidence.extend(node.metadata.evidence)
    return nodes


def _merge_edges(fixtures: Sequence[GraphFixture]) -> dict[str, GraphEdge]:
    edges: dict[str, GraphEdge] = {}
    for fixture in fixtures:
        for edge in fixture.edges:
            if edge.stable_id not in edges:
                edges[edge.stable_id] = edge.model_copy(deep=True)
            else:
                existing = edges[edge.stable_id]
                existing.properties.update({key: value for key, value in edge.properties.items() if value is not None})
                existing.metadata.evidence.extend(edge.metadata.evidence)
    return edges


def _resolve_api_calls(contexts: Sequence[RepositoryContext]) -> Iterable[GraphEdge]:
    providers = list(_api_providers(contexts))
    consumers = list(_api_consumer_hints(contexts))
    for consumer in consumers:
        for provider in providers:
            if consumer.context.repository.id == provider.context.repository.id:
                continue
            match = _api_match(consumer.endpoint, provider)
            if match is None:
                continue
            score, reason, matched_value = match
            yield _inferred_edge(
                "CALLS",
                consumer.service.id,
                provider.endpoint.id,
                score,
                reason,
                [consumer.endpoint, provider.endpoint, provider.api, consumer.service, provider.service],
                {
                    "relationship_scope": "cross_repository",
                    "matched_on": reason,
                    "matched_value_redacted": matched_value,
                    "provider_repository_id": provider.context.repository.id,
                    "consumer_repository_id": consumer.context.repository.id,
                },
            )
            yield _inferred_edge(
                "CALLS",
                consumer.context.repository.id,
                provider.context.repository.id,
                max(score - 0.1, 0.2),
                f"repository summary for {reason}",
                [consumer.endpoint, provider.endpoint, provider.api],
                {
                    "relationship_scope": "cross_repository_summary",
                    "matched_on": reason,
                    "matched_value_redacted": matched_value,
                },
            )


def _api_providers(contexts: Sequence[RepositoryContext]) -> Iterable[ApiProvider]:
    for context in contexts:
        exposed_api_by_service: dict[str, list[GraphNode]] = {}
        endpoints_by_api: dict[str, list[GraphNode]] = {}
        for edge in context.fixture.edges:
            if edge.type == "EXPOSES" and edge.source in context.service_by_id and edge.target in context.api_by_id:
                exposed_api_by_service.setdefault(edge.source, []).append(context.api_by_id[edge.target])
            if edge.type == "HAS_ENDPOINT" and edge.source in context.api_by_id and edge.target in context.endpoint_by_id:
                endpoints_by_api.setdefault(edge.source, []).append(context.endpoint_by_id[edge.target])
        for service_id, apis in exposed_api_by_service.items():
            for api in apis:
                for endpoint in endpoints_by_api.get(api.id, ()):
                    yield ApiProvider(context, context.service_by_id[service_id], api, endpoint)


def _api_consumer_hints(contexts: Sequence[RepositoryContext]) -> Iterable[ApiConsumerHint]:
    provider_endpoint_ids = {
        edge.target
        for context in contexts
        for edge in context.fixture.edges
        if edge.type == "HAS_ENDPOINT"
    }
    for context in contexts:
        for edge in context.fixture.edges:
            if edge.type in {"CALLS", "CONNECTS_TO"} and edge.source in context.service_by_id and edge.target in context.endpoint_by_id:
                endpoint = context.endpoint_by_id[edge.target]
                if endpoint.id not in provider_endpoint_ids or endpoint.properties.get("consumer_hint"):
                    yield ApiConsumerHint(context, context.service_by_id[edge.source], endpoint)


def _api_match(consumer_endpoint: GraphNode, provider: ApiProvider) -> tuple[float, str, str] | None:
    consumer_props = consumer_endpoint.properties
    provider_endpoint_props = provider.endpoint.properties
    provider_names = {_norm_name(provider.service.properties.get("name")), _norm_name(provider.api.metadata.name)}
    provider_names |= {_norm_name(provider.api.id), _norm_name(provider.service.id)}
    provider_names.discard("")

    consumer_path = _normalize_path(_str_prop(consumer_props.get("path")))
    provider_path = _normalize_path(_str_prop(provider_endpoint_props.get("path")))
    consumer_method = _str_prop(consumer_props.get("method")).upper()
    provider_method = _str_prop(provider_endpoint_props.get("method")).upper()
    consumer_host = _normalize_host(_str_prop(consumer_props.get("host")))
    consumer_base = _str_prop(consumer_props.get("base_url"))
    service_hint = _norm_name(consumer_props.get("service_name_hint"))
    api_title_hint = _norm_name(consumer_props.get("api_title_hint"))

    if consumer_path and provider_path and consumer_path == provider_path and (not consumer_method or consumer_method == provider_method):
        if service_hint in provider_names or api_title_hint in provider_names or _host_matches_name(consumer_host, provider_names):
            return 0.95, "service/url plus endpoint path", f"{consumer_method or provider_method} {consumer_path}".strip()
        return 0.88, "endpoint path", f"{consumer_method or provider_method} {consumer_path}".strip()
    if consumer_path and provider_path and (consumer_path.startswith(provider_path) or provider_path.startswith(consumer_path)):
        if service_hint in provider_names or _host_matches_name(consumer_host, provider_names):
            return 0.78, "base URL plus route prefix", consumer_path
    if service_hint and service_hint in provider_names:
        return 0.62, "configured service name", _str_prop(consumer_props.get("service_name_hint"))
    if api_title_hint and api_title_hint in provider_names:
        return 0.62, "OpenAPI title", _str_prop(consumer_props.get("api_title_hint"))
    if consumer_base and _host_matches_name(consumer_host, provider_names):
        return 0.58, "configured service URL", _redact_url(consumer_base)
    return None


def _resolve_broker_links(contexts: Sequence[RepositoryContext]) -> Iterable[GraphEdge]:
    links = _resource_links(contexts, {"Topic", "Queue"}, {"PUBLISHES_TO", "CONSUMES_FROM", "READS_FROM", "WRITES_TO"})
    by_identity: dict[tuple[str, str], list[ResourceLink]] = {}
    for link in links:
        identity = _resource_identity(link.resource)
        if identity:
            by_identity.setdefault((link.resource.type, identity), []).append(link)
    for (_resource_type, identity), group in by_identity.items():
        producers = [link for link in group if link.edge.type in {"PUBLISHES_TO", "WRITES_TO"}]
        consumers = [link for link in group if link.edge.type in {"CONSUMES_FROM", "READS_FROM"}]
        for producer in producers:
            for consumer in consumers:
                if producer.context.repository.id == consumer.context.repository.id:
                    continue
                yield _inferred_edge(
                    "PUBLISHES_TO",
                    producer.service.id,
                    producer.resource.id,
                    0.9,
                    "shared topic or queue name",
                    [producer.resource, producer.service, consumer.service],
                    {"relationship_scope": "cross_repository", "matched_value_redacted": identity},
                )
                yield _inferred_edge(
                    "CONSUMES_FROM",
                    consumer.service.id,
                    consumer.resource.id,
                    0.9,
                    "shared topic or queue name",
                    [consumer.resource, producer.service, consumer.service],
                    {"relationship_scope": "cross_repository", "matched_value_redacted": identity},
                )


def _resolve_database_links(contexts: Sequence[RepositoryContext]) -> Iterable[GraphEdge]:
    links = _resource_links(contexts, {"Database"}, {"CONNECTS_TO", "READS_FROM", "WRITES_TO"})
    by_identity: dict[str, list[ResourceLink]] = {}
    for link in links:
        identity = _resource_identity(link.resource)
        if identity:
            by_identity.setdefault(identity, []).append(link)
    for identity, group in by_identity.items():
        if len({link.context.repository.id for link in group}) < 2:
            continue
        for link in group:
            score = 0.82 if _str_prop(link.resource.properties.get("database_name")) else 0.68
            for edge_type in _database_edge_types(link.edge):
                yield _inferred_edge(
                    edge_type,
                    link.service.id,
                    link.resource.id,
                    score,
                    "shared database identifier",
                    [link.resource, link.service],
                    {"relationship_scope": "cross_repository", "matched_value_redacted": identity},
                )


def _resource_links(
    contexts: Sequence[RepositoryContext], resource_types: set[str], edge_types: set[str]
) -> list[ResourceLink]:
    result: list[ResourceLink] = []
    for context in contexts:
        resources = {node.id: node for node in context.fixture.nodes if node.type in resource_types}
        for edge in context.fixture.edges:
            if edge.type in edge_types and edge.source in context.service_by_id and edge.target in resources:
                result.append(ResourceLink(context, context.service_by_id[edge.source], resources[edge.target], edge))
    return result


def _database_edge_types(edge: GraphEdge) -> tuple[str, ...]:
    if edge.type in {"READS_FROM", "WRITES_TO"}:
        return (edge.type,)
    access = _str_prop(edge.properties.get("access")).lower()
    if access == "read":
        return ("READS_FROM",)
    if access == "write":
        return ("WRITES_TO",)
    return ("CONNECTS_TO", "READS_FROM", "WRITES_TO")


def _inferred_edge(
    edge_type: str,
    source: str,
    target: str,
    confidence: float,
    reason: str,
    evidence_nodes: Sequence[GraphNode],
    properties: dict[str, str],
) -> GraphEdge:
    level = _confidence_level(confidence)
    safe_properties = dict(properties)
    safe_properties.update({"confidence_level": level, "confidence_reason": reason})
    return GraphEdge(
        id=f"inferred:{edge_type.lower()}:{source}:{target}:{_slug(reason)}",
        type=edge_type,
        source=source,
        target=target,
        properties=safe_properties,
        metadata=_metadata("cross_repository_resolver", reason, confidence, evidence_nodes, reason),
    )


def _metadata(
    source_system: str,
    source_ref: str,
    confidence: float,
    evidence_nodes: Sequence[GraphNode],
    detail: str,
) -> GraphMetadata:
    evidence = [
        SourceEvidence(
            source=node.metadata.source_system or "repository_fixture",
            source_id=node.metadata.source_ref or node.id,
            confidence=node.metadata.confidence,
            detail=f"{node.type}:{node.id}",
        )
        for node in evidence_nodes
    ]
    if not evidence:
        evidence = [SourceEvidence(source=source_system, source_id=source_ref, confidence=confidence, detail=detail)]
    return GraphMetadata(
        source_system=source_system,
        source_ref=source_ref,
        confidence=confidence,
        tags=["inferred", f"confidence:{_confidence_level(confidence)}"],
        evidence=evidence,
    )


def _confidence_level(score: float) -> str:
    for minimum, level in CONFIDENCE_LEVELS:
        if score >= minimum:
            return level
    return "low"


def _resource_identity(node: GraphNode) -> str:
    for key in ("normalized_identity", "topic_name", "queue_name", "database_name", "schema", "config_key"):
        value = _str_prop(node.properties.get(key))
        if value:
            return _normalize_identity(value)
    name = node.metadata.name or ""
    if name:
        return _normalize_identity(name)
    return _normalize_identity(node.id)


def _normalize_identity(value: str) -> str:
    return value.strip().lower().replace("_", ".")


def _str_prop(value: object) -> str:
    return value if isinstance(value, str) else ""


def _normalize_path(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme else value
    if not path.startswith("/"):
        path = f"/{path}"
    return re.sub(r"/+$", "", path) or "/"


def _normalize_host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"//{value}")
    return (parsed.hostname or value).lower()


def _host_matches_name(host: str, names: set[str]) -> bool:
    if not host:
        return False
    host_parts = {_norm_name(part) for part in host.split(".")}
    return bool(host_parts & names)


def _norm_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.lower().removeprefix("service:").removeprefix("api:")
    value = value.replace("@", "").replace("/", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def _redact_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc, query="", fragment="").geturl()


def _slug(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"
