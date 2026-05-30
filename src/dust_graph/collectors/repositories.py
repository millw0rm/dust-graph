"""Local repository collector.

The collector intentionally uses targeted file-name extraction instead of broad
source parsing so early ingestion is deterministic and avoids retaining secrets.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from dust_graph.models import GraphEdge, GraphFixture, GraphMetadata, GraphNode, SourceEvidence

OPENAPI_FILE_NAMES = {"openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.json"}
K8S_KINDS = {"Deployment", "Service", "Ingress", "Namespace", "ServiceAccount", "ConfigMap"}
CONFIG_FILE_NAMES = {
    ".env",
    "app.env",
    "application.properties",
    "application.yml",
    "application.yaml",
    "config.yml",
    "config.yaml",
    "settings.yml",
    "settings.yaml",
}
DOCKERFILE_RE = re.compile(r"(^|/)Dockerfile([.\w-]*)?$", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(secret|password|passwd|token|api[_-]?key|credential|private[_-]?key)", re.I)
DB_KEY_RE = re.compile(r"(database|datasource|db_|_db|postgres|postgresql|mysql|mariadb|mongodb|mongo|redis|sqlite|jdbc)", re.I)
BROKER_KEY_RE = re.compile(r"(broker|kafka|rabbitmq|amqp|sqs|sns|pubsub|nats|mqtt|activemq)", re.I)
TOPIC_KEY_RE = re.compile(r"topic", re.I)
QUEUE_KEY_RE = re.compile(r"queue", re.I)
API_URL_KEY_RE = re.compile(r"(api|endpoint|base[_-]?url|service[_-]?url|url)$", re.I)
SERVICE_KEY_RE = re.compile(r"(^|[._-])(service|app|application)[._-]?(name)?$", re.I)

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".sql": "SQL",
}
PACKAGE_LANGUAGE_HINTS = {
    "package.json": "JavaScript",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "go.mod": "Go",
    "pom.xml": "Java",
    "build.gradle": "Java",
    "Cargo.toml": "Rust",
    "Gemfile": "Ruby",
}
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__"}


@dataclass
class CollectorState:
    root: Path
    repo_name: str
    repo_id: str
    languages: set[str] = field(default_factory=set)
    service_names: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, GraphEdge] = field(default_factory=dict)
    ci_workflows: set[str] = field(default_factory=set)


def collect_repository(path: str | Path) -> GraphFixture:
    """Collect safe metadata from a local repository into a graph fixture."""

    root = Path(path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"repository path must be an existing directory: {path}")

    repo_name = root.name
    state = CollectorState(root=root, repo_name=repo_name, repo_id=f"repo:{_slug(repo_name)}")
    _add_node(
        state,
        GraphNode(
            id=state.repo_id,
            type="Repository",
            labels=["Repository"],
            properties={"name": repo_name, "path": str(root)},
            metadata=_metadata(repo_name, "repository path", 1.0),
        ),
    )

    files = list(_iter_files(root))
    for file_path in files:
        _detect_language(state, file_path)
        _extract_package_file(state, file_path)
        _extract_docker(state, file_path)
        _extract_compose(state, file_path)
        _extract_openapi(state, file_path)
        _extract_kubernetes(state, file_path)
        _extract_config_hints(state, file_path)
        _extract_ci_workflows(state, file_path)

    if not state.service_names:
        _add_service(state, repo_name, "repository name", 0.4)

    repo = state.nodes[state.repo_id]
    repo.properties["languages"] = sorted(state.languages)
    repo.properties["candidate_services"] = sorted(state.service_names)
    repo.properties["ci_workflows"] = sorted(state.ci_workflows)

    for service_name, reasons in sorted(state.service_names.items()):
        service = _add_service(state, service_name, ", ".join(sorted(reasons)), 0.8)
        _add_edge(state, "CONTAINS", state.repo_id, service.id, "candidate service belongs to repository", 0.8)

    return GraphFixture(
        name=f"repository-collector:{repo_name}",
        description=f"Safe repository metadata collected from {root}",
        nodes=sorted(state.nodes.values(), key=lambda node: node.id),
        edges=sorted(state.edges.values(), key=lambda edge: edge.stable_id),
    )


def _iter_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _detect_language(state: CollectorState, path: Path) -> None:
    if path.suffix in LANGUAGE_EXTENSIONS:
        state.languages.add(LANGUAGE_EXTENSIONS[path.suffix])
    if path.name in PACKAGE_LANGUAGE_HINTS:
        state.languages.add(PACKAGE_LANGUAGE_HINTS[path.name])


def _extract_package_file(state: CollectorState, path: Path) -> None:
    try:
        if path.name == "package.json":
            data = json.loads(path.read_text())
            name = data.get("name") if isinstance(data, dict) else None
            if isinstance(name, str):
                _remember_service(state, name, _source(path))
        elif path.name == "pyproject.toml":
            data = tomllib.loads(path.read_text())
            name = data.get("project", {}).get("name")
            if isinstance(name, str):
                _remember_service(state, name, _source(path))
        elif path.name == "Cargo.toml":
            data = tomllib.loads(path.read_text())
            name = data.get("package", {}).get("name")
            if isinstance(name, str):
                _remember_service(state, name, _source(path))
        elif path.name == "Chart.yaml":
            data = _load_single_yaml(path)
            name = data.get("name") if isinstance(data, dict) else None
            if isinstance(name, str):
                _remember_service(state, name, _source(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError):
        return


def _extract_docker(state: CollectorState, path: Path) -> None:
    relative = _source(path)
    if not DOCKERFILE_RE.search(str(path.relative_to(state.root))):
        return
    exposed_ports: list[str] = []
    base_images: list[str] = []
    for raw_line in _safe_lines(path):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("FROM "):
            image = line.split()[1]
            if image and image != "--platform":
                base_images.append(image)
        elif line.upper().startswith("EXPOSE "):
            exposed_ports.extend(line.split()[1:])
    service = _add_service(state, state.repo_name, relative, 0.6)
    _remember_service(state, service.metadata.name or state.repo_name, relative)
    if base_images:
        service.properties["container_images"] = sorted(set(base_images))
    for port in exposed_ports:
        _add_port(state, service.id, port, relative)


def _extract_compose(state: CollectorState, path: Path) -> None:
    if path.name not in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
        return
    data = _load_single_yaml(path)
    services = data.get("services") if isinstance(data, dict) else None
    if not isinstance(services, dict):
        return
    for name, config in services.items():
        if not isinstance(name, str):
            continue
        service = _add_service(state, name, _source(path), 0.9)
        _remember_service(state, name, _source(path))
        if isinstance(config, dict):
            image = config.get("image")
            if isinstance(image, str):
                service.properties["container_image"] = image
            ports = config.get("ports")
            if isinstance(ports, list):
                for port in ports:
                    _add_port(state, service.id, str(port), _source(path))


def _extract_openapi(state: CollectorState, path: Path) -> None:
    if path.name not in OPENAPI_FILE_NAMES:
        return
    data = _load_yaml_or_json(path)
    if not isinstance(data, dict) or "openapi" not in data and "swagger" not in data:
        return
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    title = str(info.get("title") or path.stem)
    version = str(info.get("version") or "unknown")
    api_id = f"api:{_slug(state.repo_name)}:{_slug(title)}:{_slug(version)}"
    _add_node(
        state,
        GraphNode(
            id=api_id,
            type="API",
            labels=["API"],
            properties={"spec_path": _source(path), "spec_format": path.suffix.lstrip("."), "version": version},
            metadata=_metadata(title, _source(path), 0.95),
        ),
    )
    service = _add_service(state, _best_service_name(state), _source(path), 0.7)
    _add_edge(state, "EXPOSES", service.id, api_id, _source(path), 0.95)

    paths = data.get("paths")
    if isinstance(paths, dict):
        for route, route_config in paths.items():
            if not isinstance(route, str) or not isinstance(route_config, dict):
                continue
            for method, operation in route_config.items():
                if method.lower() not in HTTP_METHODS:
                    continue
                operation_id = operation.get("operationId") if isinstance(operation, dict) else None
                endpoint_id = f"endpoint:{_slug(state.repo_name)}:{_slug(method)}:{_slug(route)}"
                _add_node(
                    state,
                    GraphNode(
                        id=endpoint_id,
                        type="APIEndpoint",
                        labels=["APIEndpoint"],
                        properties={"path": route, "method": method.upper(), "operation_id": operation_id},
                        metadata=_metadata(f"{method.upper()} {route}", _source(path), 0.95),
                    ),
                )
                _add_edge(state, "HAS_ENDPOINT", api_id, endpoint_id, _source(path), 0.95)


def _extract_kubernetes(state: CollectorState, path: Path) -> None:
    if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
        return
    for document in _load_yaml_documents(path):
        if not isinstance(document, dict) or document.get("kind") not in K8S_KINDS:
            continue
        kind = str(document["kind"])
        metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        name = metadata.get("name")
        if not isinstance(name, str):
            continue
        namespace = metadata.get("namespace") if isinstance(metadata.get("namespace"), str) else None
        namespace_id = None
        if namespace or kind == "Namespace":
            namespace_name = namespace or name
            namespace_id = f"namespace:{_slug(namespace_name)}"
            _add_node(
                state,
                GraphNode(
                    id=namespace_id,
                    type="Namespace",
                    labels=["Namespace"],
                    properties={"name": namespace_name, "source_path": _source(path)},
                    metadata=_metadata(namespace_name, _source(path), 0.95),
                ),
            )
        if kind == "Service":
            node_id = f"k8sservice:{_slug(namespace or 'default')}:{_slug(name)}"
            _add_node(state, GraphNode(id=node_id, type="K8sService", labels=["K8sService"], properties={"name": name, "namespace": namespace}, metadata=_metadata(name, _source(path), 0.95)))
            service = _add_service(state, name, _source(path), 0.85)
            _remember_service(state, name, _source(path))
            _add_edge(state, "DEPLOYS_TO", service.id, node_id, _source(path), 0.8)
            if namespace_id:
                _add_edge(state, "DEPLOYS_TO", node_id, namespace_id, _source(path), 0.9)
            spec = document.get("spec") if isinstance(document.get("spec"), dict) else {}
            ports = spec.get("ports") if isinstance(spec.get("ports"), list) else []
            for port_obj in ports:
                if isinstance(port_obj, dict) and port_obj.get("port") is not None:
                    _add_port(state, node_id, str(port_obj["port"]), _source(path), protocol=str(port_obj.get("protocol", "TCP")))
        elif kind == "Deployment":
            service = _add_service(state, name, _source(path), 0.9)
            _remember_service(state, name, _source(path))
            if namespace_id:
                _add_edge(state, "DEPLOYS_TO", service.id, namespace_id, _source(path), 0.9)
            sa_name = _nested_get(document, ["spec", "template", "spec", "serviceAccountName"])
            if isinstance(sa_name, str):
                sa_id = f"serviceaccount:{_slug(namespace or 'default')}:{_slug(sa_name)}"
                _add_node(state, GraphNode(id=sa_id, type="ServiceAccount", labels=["ServiceAccount"], properties={"name": sa_name, "namespace": namespace}, metadata=_metadata(sa_name, _source(path), 0.9)))
                _add_edge(state, "RUNS_AS", service.id, sa_id, _source(path), 0.9)
            for image in _deployment_images(document):
                images = service.properties.setdefault("container_images", [])
                if isinstance(images, list) and image not in images:
                    images.append(image)
        else:
            node_type = "ServiceAccount" if kind == "ServiceAccount" else kind
            node_id = f"{_slug(node_type)}:{_slug(namespace or 'default')}:{_slug(name)}"
            _add_node(state, GraphNode(id=node_id, type=node_type, labels=[node_type], properties={"name": name, "namespace": namespace, "source_path": _source(path)}, metadata=_metadata(name, _source(path), 0.9)))
            if namespace_id and node_id != namespace_id:
                _add_edge(state, "DEPLOYS_TO", node_id, namespace_id, _source(path), 0.8)


def _extract_config_hints(state: CollectorState, path: Path) -> None:
    if path.name not in CONFIG_FILE_NAMES and path.suffix.lower() not in {".env", ".properties"}:
        return
    for key, value in _config_pairs(path):
        service = _add_service(state, _best_service_name(state), _source(path), 0.55)
        redacted_key = key.upper()
        if SERVICE_KEY_RE.search(key) and value and not SECRET_KEY_RE.search(key):
            _remember_service(state, _safe_name(value), _source(path))
        if DB_KEY_RE.search(key):
            engine = _database_engine(key, value)
            database_id = f"database:{_slug(engine)}:{_slug(redacted_key)}"
            database_name = _database_name(value)
            properties = {"engine": engine, "config_key": redacted_key, "value_redacted": True}
            if database_name:
                properties["database_name"] = database_name
            _add_node(state, GraphNode(id=database_id, type="Database", labels=["Database"], properties=properties, metadata=_metadata(redacted_key, _source(path), 0.65)))
            _add_edge(state, "CONNECTS_TO", service.id, database_id, _source(path), 0.65)
        if BROKER_KEY_RE.search(key):
            broker_type = _broker_type(key, value)
            broker_id = f"broker:{_slug(broker_type)}:{_slug(redacted_key)}"
            _add_node(state, GraphNode(id=broker_id, type="Broker", labels=["Broker"], properties={"broker_type": broker_type, "config_key": redacted_key, "value_redacted": True}, metadata=_metadata(redacted_key, _source(path), 0.65)))
            _add_edge(state, "CONNECTS_TO", service.id, broker_id, _source(path), 0.65)
        if TOPIC_KEY_RE.search(key):
            topic_id = f"topic:{_slug(redacted_key)}"
            properties = {"config_key": redacted_key, "value_redacted": True}
            if value and not SECRET_KEY_RE.search(key):
                properties["topic_name"] = _safe_resource_name(value)
            _add_node(state, GraphNode(id=topic_id, type="Topic", labels=["Topic"], properties=properties, metadata=_metadata(redacted_key, _source(path), 0.6)))
            edge_type = "CONSUMES_FROM" if _is_consumer_key(key) else "PUBLISHES_TO"
            _add_edge(state, edge_type, service.id, topic_id, _source(path), 0.6)
        if QUEUE_KEY_RE.search(key):
            queue_id = f"queue:{_slug(redacted_key)}"
            properties = {"config_key": redacted_key, "value_redacted": True}
            if value and not SECRET_KEY_RE.search(key):
                properties["queue_name"] = _safe_resource_name(value)
            _add_node(state, GraphNode(id=queue_id, type="Queue", labels=["Queue"], properties=properties, metadata=_metadata(redacted_key, _source(path), 0.6)))
            edge_type = "PUBLISHES_TO" if _is_producer_key(key) else "CONSUMES_FROM"
            _add_edge(state, edge_type, service.id, queue_id, _source(path), 0.6)
        if _looks_like_api_url(key, value):
            endpoint_id = f"endpointref:{_slug(state.repo_name)}:{_slug(redacted_key)}"
            url_parts = _url_parts(value or "")
            properties = {
                "consumer_hint": True,
                "config_key": redacted_key,
                "value_redacted": True,
                "base_url": url_parts["base_url"],
                "host": url_parts["host"],
                "path": url_parts["path"],
                "service_name_hint": _service_hint_from_key_or_url(key, value),
            }
            _add_node(state, GraphNode(id=endpoint_id, type="APIEndpoint", labels=["APIEndpoint"], properties=properties, metadata=_metadata(redacted_key, _source(path), 0.7)))
            _add_edge(state, "CALLS", service.id, endpoint_id, _source(path), 0.7)


def _extract_ci_workflows(state: CollectorState, path: Path) -> None:
    rel = path.relative_to(state.root)
    if len(rel.parts) >= 3 and rel.parts[0] == ".github" and rel.parts[1] == "workflows" and path.suffix.lower() in {".yml", ".yaml"}:
        data = _load_single_yaml(path)
        name = data.get("name") if isinstance(data, dict) else None
        state.ci_workflows.add(str(name or path.stem))
    elif path.name == ".gitlab-ci.yml":
        data = _load_single_yaml(path)
        if isinstance(data, dict):
            for name, value in data.items():
                if not str(name).startswith(".") and isinstance(value, dict) and "script" in value:
                    state.ci_workflows.add(str(name))


def _config_pairs(path: Path) -> Iterator[tuple[str, str | None]]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = _load_single_yaml(path)
        yield from _flatten_mapping(data)
        return
    if path.suffix.lower() == ".json":
        data = _load_yaml_or_json(path)
        yield from _flatten_mapping(data)
        return
    for line in _safe_lines(path):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        separator = "=" if "=" in stripped else ":" if ":" in stripped else None
        if separator:
            key, value = stripped.split(separator, 1)
            yield key.strip(), value.strip().strip('"\'') or None


def _flatten_mapping(data: Any, prefix: str = "") -> Iterator[tuple[str, str | None]]:
    if isinstance(data, dict):
        for key, value in data.items():
            compound = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_mapping(value, compound)
    elif isinstance(data, (str, int, float, bool)):
        yield prefix, str(data)
    elif data is None and prefix:
        yield prefix, None


def _load_yaml_or_json(path: Path) -> Any:
    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text())
        return _load_single_yaml(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return None


def _load_single_yaml(path: Path) -> Any:
    docs = _load_yaml_documents(path)
    return docs[0] if docs else {}


def _load_yaml_documents(path: Path) -> list[Any]:
    try:
        if path.suffix.lower() == ".json":
            return [json.loads(path.read_text())]
        return list(yaml.safe_load_all(path.read_text()))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return []


def _deployment_images(document: dict[str, Any]) -> Iterator[str]:
    containers = _nested_get(document, ["spec", "template", "spec", "containers"])
    if isinstance(containers, list):
        for container in containers:
            if isinstance(container, dict) and isinstance(container.get("image"), str):
                yield container["image"]


def _nested_get(data: dict[str, Any], keys: list[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_lines(path: Path) -> list[str]:
    try:
        return path.read_text(errors="ignore").splitlines()
    except OSError:
        return []


def _database_engine(key: str, value: str | None) -> str:
    text = f"{key} {value or ''}".lower()
    for engine in ("postgres", "postgresql", "mysql", "mariadb", "mongodb", "mongo", "redis", "sqlite"):
        if engine in text:
            return "postgres" if engine == "postgresql" else "mongodb" if engine == "mongo" else engine
    parsed = urlparse(value or "")
    return parsed.scheme or "unknown"


def _broker_type(key: str, value: str | None) -> str:
    text = f"{key} {value or ''}".lower()
    for broker in ("kafka", "rabbitmq", "amqp", "sqs", "sns", "pubsub", "nats", "mqtt", "activemq"):
        if broker in text:
            return broker
    return "unknown"



def _database_name(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.path and parsed.path != "/":
        return _safe_resource_name(parsed.path.rsplit("/", 1)[-1])
    if "://" not in value and re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return _safe_resource_name(value)
    return None


def _safe_resource_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "-", value.strip()).strip("-.")


def _is_consumer_key(key: str) -> bool:
    return bool(re.search(r"(consume|consumer|subscribe|input|source|read)", key, re.I))


def _is_producer_key(key: str) -> bool:
    return bool(re.search(r"(produce|producer|publish|output|sink|write)", key, re.I))


def _looks_like_api_url(key: str, value: str | None) -> bool:
    if not value or SECRET_KEY_RE.search(key):
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return bool(API_URL_KEY_RE.search(key) or "/" in parsed.path.strip("/"))


def _url_parts(value: str) -> dict[str, str]:
    parsed = urlparse(value)
    host = parsed.hostname or ""
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    base_url = parsed._replace(netloc=netloc, path="", params="", query="", fragment="").geturl()
    return {"base_url": base_url, "host": host, "path": parsed.path or "/"}


def _service_hint_from_key_or_url(key: str, value: str | None) -> str:
    parsed = urlparse(value or "")
    candidates = [key]
    if parsed.hostname:
        candidates.extend(parsed.hostname.split("."))
    for candidate in candidates:
        candidate = re.sub(r"(api|endpoint|base|url|service|http|https)", " ", candidate, flags=re.I)
        safe = _safe_name(candidate)
        if safe:
            return safe
    return ""

def _add_port(state: CollectorState, source_id: str, raw_port: str, source: str, protocol: str | None = None) -> None:
    match = re.search(r"(?P<port>\d{2,5})(?:/(?P<protocol>tcp|udp))?", raw_port, re.I)
    if not match:
        return
    port = int(match.group("port"))
    detected_protocol = (protocol or match.group("protocol") or "tcp").upper()
    port_id = f"port:{port}:{detected_protocol.lower()}"
    _add_node(state, GraphNode(id=port_id, type="Port", labels=["Port"], properties={"port": port, "protocol": detected_protocol}, metadata=_metadata(f"{port}/{detected_protocol}", source, 0.85)))
    _add_edge(state, "EXPOSES", source_id, port_id, source, 0.85)


def _add_service(state: CollectorState, name: str, source: str, confidence: float) -> GraphNode:
    safe = _safe_name(name) or state.repo_name
    service_id = f"service:{_slug(safe)}"
    node = state.nodes.get(service_id)
    if node is None:
        node = GraphNode(id=service_id, type="Service", labels=["Service"], properties={"name": safe}, metadata=_metadata(safe, source, confidence))
        _add_node(state, node)
    _remember_service(state, safe, source)
    return node


def _remember_service(state: CollectorState, name: str, reason: str) -> None:
    safe = _safe_name(name)
    if safe:
        state.service_names[safe].add(reason)


def _add_node(state: CollectorState, node: GraphNode) -> None:
    if node.id in state.nodes:
        existing = state.nodes[node.id]
        existing.properties.update({k: v for k, v in node.properties.items() if v is not None})
        existing.metadata.evidence.extend(node.metadata.evidence)
    else:
        state.nodes[node.id] = node


def _add_edge(state: CollectorState, edge_type: str, source: str, target: str, detail: str, confidence: float) -> None:
    edge = GraphEdge(type=edge_type, source=source, target=target, metadata=_metadata(None, detail, confidence))
    state.edges[edge.stable_id] = edge


def _metadata(name: str | None, source_id: str, confidence: float) -> GraphMetadata:
    return GraphMetadata(
        name=name,
        source_system="repository_collector",
        source_ref=source_id,
        confidence=confidence,
        evidence=[SourceEvidence(source="repository_collector", source_id=source_id, confidence=confidence)],
    )


def _source(path: Path) -> str:
    # Resolved in call sites through paths owned by the active state; this helper
    # is intentionally path-only to keep evidence values portable in fixtures.
    return str(path)


def _best_service_name(state: CollectorState) -> str:
    return sorted(state.service_names)[0] if state.service_names else state.repo_name


def _safe_name(name: str) -> str:
    value = name.strip().strip('"\'')
    if "/" in value and not value.startswith("/"):
        value = value.rsplit("/", 1)[-1]
    return value[:100]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-.")
    return slug or "unknown"
