# Repository Digestion

## Purpose

Dust Graph should ingest external repositories by extracting stable, reviewable facts about source ownership, service boundaries, deployment configuration, APIs, runtime dependencies, and integration points. The ingestion process should favor explicit evidence from repository files, attach provenance to every graph record, and avoid storing secrets or sensitive values.

## Ingestion Principles

- **Evidence first:** create nodes and edges only when there is a file, manifest, workflow, spec, or code reference that supports the claim.
- **Provenance on every fact:** include source repository, file path, line range when available, commit SHA, default branch, extractor name, extraction timestamp, and confidence.
- **Incremental updates:** re-ingest repositories by commit or branch snapshot so stale facts can be marked as no longer observed without deleting historical context immediately.
- **Secret safety:** detect likely secrets, redact values, and store only safe metadata such as variable names, dependency names, provider types, and reference categories.
- **Human reviewability:** prefer normalized graph records with short evidence snippets or file pointers over opaque blobs.
- **Conservative inference:** when a service, database, broker, topic, or queue name is inferred from configuration or code, record the inference rule and a confidence score.

## Repository Discovery and Metadata

For each repository, Dust Graph should first create or update the `Repository` node using version-control and hosting metadata.

Extraction targets:

- Repository name, slug, clone URL, web URL, host provider, organization or namespace, visibility, archived status, and service metadata from the hosting platform.
- Default branch, latest observed commit SHA, tags or release branches when available, and repository topics or labels.
- Owners from platform teams, CODEOWNERS files, repository permissions, package metadata, maintainers files, or configured ownership catalogs.
- Primary and secondary languages from platform language statistics, build files, lockfiles, package manifests, and source file distribution.
- Repository-level service hints from files such as `README`, `catalog-info.yaml`, `service.yaml`, `package.json`, `go.mod`, `pom.xml`, `pyproject.toml`, `Cargo.toml`, and deployment descriptors.

## Extraction Targets

### 1. Repository and Service Identity

Dust Graph should identify deployable or logical services before mapping deeper resources.

Look for:

- Service names in Backstage descriptors, deployment manifests, Helm chart metadata, Docker Compose files, CI/CD deployment jobs, package manifests, README badges, and application config files.
- Monorepo service boundaries from workspace manifests, directory conventions, build targets, chart directories, or per-service deployment folders.
- Runtime entry points such as application modules, process managers, server bootstrap files, and container commands.

Store candidate service identities with evidence paths and confidence. Multiple services may belong to one repository.

### 2. OpenAPI Specs

Discover OpenAPI definitions in common locations and generated artifacts.

Look for:

- Files named `openapi.yaml`, `openapi.yml`, `openapi.json`, `swagger.yaml`, `swagger.yml`, or `swagger.json`.
- OpenAPI documents embedded in documentation, API gateway config, service descriptors, or generated client/server folders.
- Version, title, servers, tags, paths, operations, methods, parameters, request schemas, response schemas, authentication schemes, and deprecation markers.

Map each spec to an `API` node and each path/method operation to an `APIEndpoint` node. Preserve operation IDs when available.

### 3. Kubernetes Manifests

Discover Kubernetes YAML and JSON manifests from raw manifest folders, overlays, generated output, and deployment directories.

Look for:

- Workloads: `Deployment`, `StatefulSet`, `DaemonSet`, `Job`, `CronJob`, and custom workload resources.
- Routing and exposure: `Service`, `Ingress`, gateway resources, ports, protocols, hosts, paths, and selectors.
- Placement: namespaces, labels, annotations, service accounts, environment references, config maps, secrets references, volumes, and image references.
- Runtime dependencies in environment variables, config maps, annotations, sidecars, init containers, and command arguments.

Use namespace declarations and manifest metadata to map services to `Namespace` nodes. Do not store Kubernetes Secret values; store only secret names, keys, and reference paths when needed for provenance.

### 4. Helm Charts

Discover Helm charts and rendered values.

Look for:

- `Chart.yaml`, `values.yaml`, `values.schema.json`, templates, dependency charts, aliases, app versions, and chart annotations.
- Service names, image repositories, image tags, container names, namespace templates, ingress hosts, service ports, environment variable names, config keys, and external dependency settings.
- References introduced by templating helpers, subcharts, global values, and environment-specific values files.

Where possible, parse both chart metadata and values files. Rendering templates can improve accuracy, but extracted graph facts should retain the original chart and values evidence.

### 5. Terraform Files

Discover infrastructure definitions from Terraform and compatible HCL files.

Look for:

- Files ending in `.tf`, `.tfvars`, `.tf.json`, and module directories.
- Providers, modules, workspaces, backends, variables, outputs, data sources, resources, tags, and dependency expressions.
- Infrastructure that identifies namespaces, clusters, databases, brokers, topics, queues, container registries, service accounts, IAM bindings, DNS records, and load balancers.

Store variable and output names, resource addresses, provider types, and dependency relationships. Do not store secret variable values from tfvars, environment files, state files, or backend configuration.

### 6. Dockerfiles and Container Names

Discover container build and runtime configuration.

Look for:

- `Dockerfile`, `*.Dockerfile`, Docker Compose files, build bake files, Kubernetes image fields, Helm image values, and CI build steps.
- Image repository names, image aliases, container names, stages, exposed ports, entrypoints, commands, labels, health checks, and build arguments.
- Compose services, networks, volumes, environment variable names, dependency declarations, and container-to-container references.

Use image names, compose service names, Kubernetes container names, and Helm image values as service identity hints. Redact build argument or environment values that appear sensitive.

### 7. CI/CD Workflows

Discover workflow automation and deployment paths.

Look for:

- GitHub Actions, GitLab CI, CircleCI, Buildkite, Jenkins, Azure Pipelines, Tekton, Argo CD, Flux, Drone, and similar workflow definitions.
- Build, test, package, scan, publish, deploy, release, rollback, and migration jobs.
- Workflow environment names, deployment targets, registry names, chart publishing steps, Terraform plans/applies, kubectl commands, Helm commands, service names, and notification targets.
- Secrets and variables by name only, such as `${{ secrets.PROD_TOKEN }}` or masked CI variable references.

Use deployment jobs to strengthen `Service -> DEPLOYS_TO -> Namespace` mappings and to associate repositories with runtime services.

### 8. Environment Variables and Dependency Hints

Extract environment variable names and dependency hints without storing secrets.

Look for:

- Environment variable names in code, manifests, Compose files, Helm values, Terraform variables, CI workflows, dotenv examples, and documentation.
- Safe dependency hints from variable names and non-secret values, such as hostnames, port names, protocol names, feature flags, queue names, topic names, and database adapter names.
- Common dependency patterns such as `DATABASE_URL`, `REDIS_URL`, `KAFKA_BROKERS`, `RABBITMQ_URL`, `SQS_QUEUE`, `SNS_TOPIC`, `SERVICE_URL`, and `*_HOST`.

Never store raw values that match secret patterns, tokens, passwords, private keys, session cookies, authorization headers, connection strings with credentials, or high-entropy strings. For connection strings, store parsed non-sensitive components only when credentials are absent or safely redacted.

### 9. Service-to-Service References in Config Files

Discover service references from configuration and deployment files.

Look for:

- URLs, hosts, DNS names, Kubernetes service names, service discovery names, RPC targets, gRPC authorities, HTTP client base URLs, and API gateway upstreams.
- Config files including YAML, JSON, TOML, INI, properties files, XML, Helm values, Compose files, Kubernetes ConfigMaps, and framework-specific config.
- References in retries, circuit breakers, client configs, authorization audiences, OIDC resource indicators, CORS origins, and webhook targets.

When a referenced service is known, map the source service to the target service using a runtime dependency edge such as `CALLS` or a more specific edge if available. When only a host or URL is known, create a placeholder service or external endpoint node with low confidence and clear provenance.

### 10. Database and Broker References in Code and Config

Discover datastore and messaging dependencies from both code and configuration.

Look for:

- Database adapters, ORM config, migration folders, schema files, connection factories, JDBC/ODBC strings, DSNs, and known client libraries.
- Database engines and services such as PostgreSQL, MySQL, MariaDB, SQL Server, Oracle, SQLite, MongoDB, DynamoDB, Cassandra, Elasticsearch/OpenSearch, Redis, and cloud-managed database resources.
- Broker and messaging clients such as Kafka, RabbitMQ, ActiveMQ, NATS, SQS, SNS, Pub/Sub, EventBridge, Kinesis, Redis streams, and cloud event hubs.
- Topic, queue, stream, exchange, consumer group, routing key, subscription, and channel names in code constants, config files, Terraform resources, Helm values, and Kubernetes manifests.

Map services to databases, topics, and queues only when evidence identifies the dependency. Store broker nodes when broker identity is known; otherwise map directly to topics or queues with provider metadata.

## Secret and Sensitive Data Handling

Dust Graph must not store secrets from ingested repositories.

Required behavior:

- Classify values as sensitive when names or content suggest passwords, tokens, keys, certificates, cookies, credentials, secrets, private keys, or high-entropy material.
- Redact sensitive values before persistence and logs.
- Store safe metadata only: variable name, reference type, provider category, file path, line range, and whether the value was redacted.
- Avoid ingesting Terraform state, encrypted secret payloads, `.env` files with real values, CI secret stores, Kubernetes Secret data, or generated credential files unless a dedicated safe extractor is approved.
- Prefer example files such as `.env.example` and documentation tables for variable names, while still redacting suspicious example values.

## Graph Mappings

The repository ingestion pipeline should emit graph records that conform to the core vocabulary. The required mappings are:

| Source | Edge | Target | Extraction evidence |
| --- | --- | --- | --- |
| `Repository` | `CONTAINS` | `Service` | Service descriptor, monorepo boundary, package metadata, deployment artifact, or runtime entry point. |
| `Service` | `EXPOSES` | `API` | OpenAPI spec, gateway config, server route registration, ingress, service manifest, or documented API surface. |
| `API` | `HAS_ENDPOINT` | `APIEndpoint` | OpenAPI path/method operation or route extraction result. |
| `Service` | `DEPLOYS_TO` | `Namespace` | Kubernetes manifest, Helm values, CI deployment target, GitOps app, or Terraform-managed namespace. |
| `Service` | `CONNECTS_TO` | `Database` | ORM config, database client config, environment reference, Terraform resource, Helm value, or manifest config. |
| `Service` | `PUBLISHES_TO` | `Topic` | Producer code, broker config, topic resource, workflow, or environment reference. |
| `Service` | `CONSUMES_FROM` | `Queue` | Consumer code, worker config, queue resource, workflow, or environment reference. |
| `User` / `Group` | `OWNS` | `Repository` | Repository permissions, hosting teams, CODEOWNERS, catalog ownership, maintainers files, or metadata. |

`HAS_ENDPOINT` is required for API modeling even if the edge type is not yet present in the base schema; it should be added to the schema before endpoint ingestion becomes executable.

## Suggested Node Properties

### Repository

- `name`, `slug`, `provider`, `web_url`, `clone_url`, `default_branch`, `visibility`, `archived`, `primary_language`, `topics`, `latest_commit_sha`.

### Service

- `name`, `service_type`, `source_path`, `runtime`, `language`, `framework`, `container_image`, `container_names`, `deployment_system`, `confidence`.

### API

- `name`, `api_type`, `spec_path`, `spec_format`, `version`, `servers`, `auth_schemes`, `owner_service`.

### APIEndpoint

- `path`, `method`, `operation_id`, `summary`, `tags`, `deprecated`, `auth_required`, `request_schema_ref`, `response_schema_refs`.

### Namespace

- `name`, `cluster`, `environment`, `provider`, `source_path`.

### Database

- `name`, `engine`, `provider`, `host_redacted`, `port`, `database_name`, `resource_address`, `environment`.

### Topic and Queue

- `name`, `broker_type`, `provider`, `resource_address`, `environment`, `source_path`.

## Extraction Output Requirements

Each extracted node or edge should include common metadata compatible with the graph schema:

- `source`: extractor or source system name.
- `source_ref`: repository URL, file path, resource address, or provider identifier.
- `environment`: deployment environment when known.
- `first_seen` and `last_seen`: observation timestamps.
- `confidence`: score from `0` to `1` based on evidence quality.

Edges should also include the evidence file path and extraction rule when available so reviewers can trace why the relationship exists.

## Implementation Notes

A practical ingestion run can be staged as follows:

1. Clone or fetch the repository at a pinned commit from the default branch.
2. Read host metadata, ownership metadata, and language statistics.
3. Scan file names and manifests to select specialized extractors.
4. Run targeted extractors for OpenAPI, Kubernetes, Helm, Terraform, Docker, CI/CD, package manifests, and configuration files.
5. Run code/config reference detection for service, database, broker, topic, and queue references.
6. Redact sensitive values before writing intermediate or final results.
7. Normalize extracted facts into graph nodes and edges with provenance.
8. Validate records against the graph schema and quarantine unsupported or low-confidence records for review.
9. Mark previously observed facts as stale when they are absent from the new commit snapshot.
