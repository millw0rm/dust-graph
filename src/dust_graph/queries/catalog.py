"""Saved query catalog for backend-neutral Dust Graph lookups."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dust_graph.adapters.memory import InMemoryGraphAdapter
from dust_graph.models import GraphEdge, GraphNode, QueryResult


COMMON_PARAMETER_NAMES = (
    "environment",
    "source_system",
    "min_confidence",
    "as_of",
    "include_stale",
)


@dataclass(frozen=True)
class QueryParameter:
    """Describe an accepted saved-query parameter."""

    name: str
    description: str
    required: bool = False


@dataclass(frozen=True)
class SavedQuery:
    """Executable saved-query definition."""

    name: str
    description: str
    parameters: tuple[QueryParameter, ...]
    handler: Callable[[InMemoryGraphAdapter, dict[str, Any]], QueryResult]

    @property
    def required_parameter_names(self) -> tuple[str, ...]:
        """Return parameter names that are unconditionally required."""

        return tuple(parameter.name for parameter in self.parameters if parameter.required)


def execute_saved_query(
    adapter: InMemoryGraphAdapter, name: str, parameters: dict[str, Any] | None = None
) -> QueryResult:
    """Execute a registered saved query."""

    try:
        query = SAVED_QUERIES[name]
    except KeyError as exc:
        raise ValueError(f"unknown saved query: {name}") from exc
    return query.handler(adapter, parameters or {})


def _parameter(name: str, description: str, *, required: bool = False) -> QueryParameter:
    return QueryParameter(name=name, description=description, required=required)


def _common_parameters() -> tuple[QueryParameter, ...]:
    return (
        _parameter("environment", "Limit results to a deployment environment."),
        _parameter("source_system", "Limit results to facts from this source system."),
        _parameter("min_confidence", "Omit facts below this confidence threshold."),
        _parameter("as_of", "Reserved timestamp for validity-window evaluation."),
        _parameter("include_stale", "Reserved flag for including stale facts."),
    )


def _require_any(parameters: dict[str, Any], *names: str) -> None:
    if not any(parameters.get(name) not in (None, "") for name in names):
        joined = " or ".join(names)
        raise ValueError(f"missing required parameter: {joined}")


def _node_matches_lookup(node: GraphNode, *, node_id: str | None, lookup: str | None) -> bool:
    if node_id is not None:
        return node.id == node_id
    if lookup is None:
        return False
    return lookup in {
        node.metadata.name,
        node.properties.get("name"),
        node.properties.get("slug"),
        node.properties.get("url"),
    }


def _repository(adapter: InMemoryGraphAdapter, parameters: dict[str, Any]) -> GraphNode | None:
    _require_any(parameters, "repository_id", "repository_slug")
    repository_id = parameters.get("repository_id")
    repository_slug = parameters.get("repository_slug")
    return next(
        (
            node
            for node in _nodes(adapter, "Repository")
            if _node_matches_lookup(node, node_id=repository_id, lookup=repository_slug)
        ),
        None,
    )


def _api(adapter: InMemoryGraphAdapter, parameters: dict[str, Any]) -> GraphNode | None:
    _require_any(parameters, "api_id", "api_name")
    api_id = parameters.get("api_id")
    api_name = parameters.get("api_name")
    return next(
        (
            node
            for node in _nodes(adapter, "API")
            if _node_matches_lookup(node, node_id=api_id, lookup=api_name)
        ),
        None,
    )


def _service(adapter: InMemoryGraphAdapter, parameters: dict[str, Any]) -> GraphNode | None:
    _require_any(parameters, "service_id", "service_name")
    service_id = parameters.get("service_id")
    service_name = parameters.get("service_name")
    return next(
        (
            node
            for node in _nodes(adapter, "Service")
            if _node_matches_lookup(node, node_id=service_id, lookup=service_name)
        ),
        None,
    )


def _nodes(adapter: InMemoryGraphAdapter, node_type: str) -> list[GraphNode]:
    return sorted(
        (node for node in adapter.nodes.values() if node.type == node_type),
        key=lambda node: node.id,
    )


def _passes_common_filters(item: GraphNode | GraphEdge, parameters: dict[str, Any]) -> bool:
    environment = parameters.get("environment")
    if environment is not None and item.metadata.environment not in (None, environment):
        return False

    source_system = parameters.get("source_system")
    if source_system is not None and item.metadata.source_system != source_system:
        return False

    min_confidence = parameters.get("min_confidence")
    if min_confidence is not None:
        confidence = item.metadata.confidence
        if confidence is not None and confidence < float(min_confidence):
            return False

    return True


def _filtered_edges(
    adapter: InMemoryGraphAdapter,
    parameters: dict[str, Any],
    *,
    source: str | None = None,
    target: str | None = None,
    edge_type: str | None = None,
) -> list[GraphEdge]:
    return [
        edge
        for edge in adapter.edges_sorted()
        if (source is None or edge.source == source)
        and (target is None or edge.target == target)
        and (edge_type is None or edge.type == edge_type)
        and _passes_common_filters(edge, parameters)
    ]


def _node_document(node: GraphNode) -> dict[str, Any]:
    return node.model_dump(mode="json")


def _edge_document(edge: GraphEdge) -> dict[str, Any]:
    document = edge.model_dump(mode="json")
    document["id"] = edge.stable_id
    return document


def _path_document(edges: list[GraphEdge]) -> list[dict[str, Any]]:
    return [_edge_document(edge) for edge in edges]


def _repository_services(
    adapter: InMemoryGraphAdapter, repository: GraphNode, parameters: dict[str, Any]
) -> list[tuple[GraphNode, GraphEdge]]:
    services: list[tuple[GraphNode, GraphEdge]] = []
    for edge in _filtered_edges(adapter, parameters, source=repository.id):
        if edge.type not in {"CONTAINS", "DEPLOYS_TO"}:
            continue
        service = adapter.nodes.get(edge.target)
        if service is None or service.type != "Service":
            continue
        if not _passes_common_filters(service, parameters):
            continue
        services.append((service, edge))
    return sorted(services, key=lambda item: (item[0].id, item[1].stable_id))


def repository_apis(adapter: InMemoryGraphAdapter, parameters: dict[str, Any]) -> QueryResult:
    """Return APIs exposed by services associated with a repository."""

    repository = _repository(adapter, parameters)
    if repository is None or not _passes_common_filters(repository, parameters):
        return []

    rows: list[dict[str, Any]] = []
    for service, repository_edge in _repository_services(adapter, repository, parameters):
        for exposes_edge in _filtered_edges(
            adapter, parameters, source=service.id, edge_type="EXPOSES"
        ):
            api = adapter.nodes.get(exposes_edge.target)
            if api is None or api.type != "API" or not _passes_common_filters(api, parameters):
                continue
            rows.append(
                {
                    "repository": _node_document(repository),
                    "service": _node_document(service),
                    "api": _node_document(api),
                    "path": _path_document([repository_edge, exposes_edge]),
                }
            )
    return sorted(rows, key=lambda row: (row["api"]["id"], row["service"]["id"]))


def api_reachable_databases(
    adapter: InMemoryGraphAdapter, parameters: dict[str, Any]
) -> QueryResult:
    """Return databases reachable from the service that exposes an API."""

    api = _api(adapter, parameters)
    if api is None or not _passes_common_filters(api, parameters):
        return []

    max_depth = int(parameters.get("max_depth", 1))
    exposing_edges = _filtered_edges(adapter, parameters, target=api.id, edge_type="EXPOSES")
    include_observed = bool(parameters.get("include_observed_connections", False))
    database_edge_types = {"CONNECTS_TO"}
    if include_observed:
        database_edge_types.add("OBSERVED_CONNECTS_TO")

    rows: list[dict[str, Any]] = []
    for exposes_edge in exposing_edges:
        service = adapter.nodes.get(exposes_edge.source)
        if (
            service is None
            or service.type != "Service"
            or not _passes_common_filters(service, parameters)
        ):
            continue
        traversals = adapter.traverse_bounded(
            service.id,
            edge_types={"CALLS"},
            max_depth=max_depth,
            direction="out",
            include_start=True,
        )
        for reached_service, call_path in traversals:
            if reached_service.type != "Service" or not _passes_common_filters(
                reached_service, parameters
            ):
                continue
            for database_edge in _filtered_edges(adapter, parameters, source=reached_service.id):
                if database_edge.type not in database_edge_types:
                    continue
                database = adapter.nodes.get(database_edge.target)
                if database is None or database.type != "Database":
                    continue
                if not _passes_common_filters(database, parameters):
                    continue
                rows.append(
                    {
                        "api": _node_document(api),
                        "service": _node_document(service),
                        "reachable_service": _node_document(reached_service),
                        "database": _node_document(database),
                        "path": _path_document([exposes_edge, *call_path, database_edge]),
                    }
                )
    return sorted(rows, key=lambda row: (row["database"]["id"], row["reachable_service"]["id"]))


def api_allowed_principals(
    adapter: InMemoryGraphAdapter, parameters: dict[str, Any]
) -> QueryResult:
    """Return principals with CAN_CALL access to an API."""

    api = _api(adapter, parameters)
    if api is None or not _passes_common_filters(api, parameters):
        return []

    include_service_accounts = bool(parameters.get("include_service_accounts", False))
    allowed_types = {"User", "Group"}
    if include_service_accounts:
        allowed_types.add("ServiceAccount")

    rows: list[dict[str, Any]] = []
    for edge in _filtered_edges(adapter, parameters, target=api.id, edge_type="CAN_CALL"):
        principal = adapter.nodes.get(edge.source)
        if principal is None or principal.type not in allowed_types:
            continue
        if not _passes_common_filters(principal, parameters):
            continue
        rows.append(
            {
                "api": _node_document(api),
                "principal": _node_document(principal),
                "path": _path_document([edge]),
            }
        )
    return sorted(rows, key=lambda row: (row["principal"]["type"], row["principal"]["id"]))


def repository_deployed_services(
    adapter: InMemoryGraphAdapter, parameters: dict[str, Any]
) -> QueryResult:
    """Return services from a repository and their deployment targets."""

    repository = _repository(adapter, parameters)
    if repository is None or not _passes_common_filters(repository, parameters):
        return []

    target_type = parameters.get("deployment_target_type")
    rows: list[dict[str, Any]] = []
    for service, repository_edge in _repository_services(adapter, repository, parameters):
        for deploy_edge in _filtered_edges(
            adapter, parameters, source=service.id, edge_type="DEPLOYS_TO"
        ):
            target = adapter.nodes.get(deploy_edge.target)
            if target is None or not _passes_common_filters(target, parameters):
                continue
            if target_type is not None and target.type != target_type:
                continue
            rows.append(
                {
                    "repository": _node_document(repository),
                    "service": _node_document(service),
                    "deployment_target": _node_document(target),
                    "path": _path_document([repository_edge, deploy_edge]),
                }
            )
    return sorted(rows, key=lambda row: (row["service"]["id"], row["deployment_target"]["id"]))


def runtime_service_contributing_repositories(
    adapter: InMemoryGraphAdapter, parameters: dict[str, Any]
) -> QueryResult:
    """Return repositories that contribute to a runtime service."""

    service = _service(adapter, parameters)
    if service is None or not _passes_common_filters(service, parameters):
        return []

    include_transitive = bool(parameters.get("include_transitive_dependencies", False))
    max_depth = int(parameters.get("max_depth", 1 if include_transitive else 0))
    traversals = adapter.traverse_bounded(
        service.id,
        edge_types={"CALLS"},
        max_depth=max_depth,
        direction="out",
        include_start=True,
    )

    rows: list[dict[str, Any]] = []
    for contributed_service, service_path in traversals:
        if contributed_service.type != "Service" or not _passes_common_filters(
            contributed_service, parameters
        ):
            continue
        for edge in adapter.incoming_edges(
            contributed_service.id, edge_types={"CONTAINS", "DEPLOYS_TO"}
        ):
            if not _passes_common_filters(edge, parameters):
                continue
            repository = adapter.nodes.get(edge.source)
            if repository is None or repository.type != "Repository":
                continue
            if not _passes_common_filters(repository, parameters):
                continue
            rows.append(
                {
                    "service": _node_document(service),
                    "contributed_service": _node_document(contributed_service),
                    "repository": _node_document(repository),
                    "path": _path_document([*service_path, edge]),
                }
            )
    return sorted(rows, key=lambda row: (row["repository"]["id"], row["contributed_service"]["id"]))


SAVED_QUERIES: dict[str, SavedQuery] = {
    "repository_apis": SavedQuery(
        name="repository_apis",
        description="Which APIs are owned by this repository?",
        parameters=(
            _parameter("repository_id", "Stable repository node identifier."),
            _parameter("repository_slug", "Human-friendly repository slug."),
            *_common_parameters(),
        ),
        handler=repository_apis,
    ),
    "api_reachable_databases": SavedQuery(
        name="api_reachable_databases",
        description="Which databases are reachable from this API?",
        parameters=(
            _parameter("api_id", "Stable API node identifier."),
            _parameter("api_name", "Human-friendly API name."),
            _parameter(
                "max_depth",
                "Maximum service-to-service CALLS hops before reaching a database.",
            ),
            _parameter(
                "include_observed_connections",
                "Include OBSERVED_CONNECTS_TO edges in addition to configured CONNECTS_TO edges.",
            ),
            *_common_parameters(),
        ),
        handler=api_reachable_databases,
    ),
    "api_allowed_principals": SavedQuery(
        name="api_allowed_principals",
        description="Which users and groups can call this API?",
        parameters=(
            _parameter("api_id", "Stable API node identifier."),
            _parameter("api_name", "Human-friendly API name."),
            _parameter(
                "include_indirect_members",
                "Reserved flag for nested group/role expansion.",
            ),
            _parameter(
                "include_service_accounts",
                "Include service accounts as callable principals.",
            ),
            *_common_parameters(),
        ),
        handler=api_allowed_principals,
    ),
    "repository_deployed_services": SavedQuery(
        name="repository_deployed_services",
        description="Which services are deployed from this repository?",
        parameters=(
            _parameter("repository_id", "Stable repository node identifier."),
            _parameter("repository_slug", "Human-friendly repository slug."),
            _parameter("deployment_target_type", "Limit deployment targets to a node type."),
            *_common_parameters(),
        ),
        handler=repository_deployed_services,
    ),
    "runtime_service_contributing_repositories": SavedQuery(
        name="runtime_service_contributing_repositories",
        description="Which repositories contribute to this runtime service?",
        parameters=(
            _parameter("service_id", "Stable service node identifier."),
            _parameter("service_name", "Human-friendly service name."),
            _parameter(
                "include_transitive_dependencies",
                "Include repositories for services reached through CALLS edges.",
            ),
            *_common_parameters(),
        ),
        handler=runtime_service_contributing_repositories,
    ),
}
