# M2 Cross-Repository Context Inference

## Scope

This M2 task plan defines how Dust Graph will infer relationships between separate repositories when no single repository explicitly declares the full dependency. The goal is to connect independently ingested repository evidence into explainable cross-repository graph relationships that can support impact analysis, ownership discovery, dependency review, and operational troubleshooting.

The plan is intentionally implementation-neutral. Extractors may run against Git repositories, artifact registries, CI/CD metadata, Kubernetes manifests, service catalogs, runtime configuration, and generated code. Every inferred relationship must retain source evidence, confidence, and redaction-safe values so users can inspect why Dust Graph connected two repositories.

## Inference Principles

Cross-repository inference should follow these principles:

- Prefer direct, source-backed relationships over name-only matches.
- Create intermediate domain nodes for shared resources such as API endpoints, broker topics, schemas, Kubernetes services, owner groups, environments, namespaces, and dependencies.
- Attach every inferred edge to one or more evidence records that identify the source repository, file path, parser, matched token, normalized value, and observation time.
- Store raw secrets only outside the graph in approved secret handling systems; graph evidence must contain redacted, hashed, or structurally summarized values.
- Treat confidence as a normalized category and score, for example `high` (`0.85-1.0`), `medium` (`0.55-0.84`), and `low` (`0.20-0.54`).
- Keep inference deterministic and idempotent by deriving node and edge identifiers from normalized resource identity plus repository identity.
- Preserve directionality: producer to consumer, owner to dependent, deployer to referenced runtime object, and spec provider to generated client.

## Common Evidence Fields

Each inferred node or edge should store evidence with these fields where available:

- `source_repository_id`: stable identifier of the repository containing the evidence.
- `source_repository_slug`: human-readable repository owner/name or equivalent.
- `source_file`: relative path to the file that produced the evidence.
- `source_ref`: commit SHA, tag, branch, artifact digest, or ingestion batch identifier.
- `line_start` and `line_end`: source location when line-oriented evidence is available.
- `parser`: extractor or rule name, such as `openapi`, `kubernetes-manifest`, `terraform`, `package-lock`, or `static-http-client`.
- `matched_key`: configuration key, manifest field, annotation, import path, generated package name, route, topic, schema, or dependency coordinate that matched.
- `matched_value_redacted`: safe display value after redaction.
- `matched_value_hash`: keyed hash of the normalized full value when exact matching is required without exposing sensitive text.
- `normalized_identity`: canonical resource identity used for joins, such as `https://api.example.com/users/{id}`, `kafka://prod/orders.created`, `postgres://cluster/app_public`, or `k8s://cluster/ns/service`.
- `environment`: environment inferred from path, labels, workspace, namespace, deployment target, or configuration.
- `confidence_score` and `confidence_level`: numeric and categorical confidence.
- `observed_at`: ingestion timestamp.

## Relationship Rules

### 1. API Endpoint Exposure and Calls

**Rule:** Repository A exposes API endpoint X and Repository B calls endpoint X.

**Source files to inspect:**

- In Repository A: OpenAPI, Swagger, AsyncAPI HTTP sections, route files, controller annotations, server framework declarations, API gateway configuration, ingress rules, service catalog descriptors, and reverse proxy configuration.
- In Repository B: HTTP client code, SDK usage, generated clients, service configuration, environment templates, API base URL settings, tests, contract tests, Postman or Insomnia collections, CI smoke tests, and infrastructure variables.

**Node types created:**

- `Repository` for each repository.
- `Service` for deployable or logical services.
- `API` for the exposed API surface.
- `APIEndpoint` for normalized method and route, including path template.
- Optional `HTTPClient`, `ConfigValue`, `Environment`, and `SecretReference` nodes when the call site is configuration-driven.

**Edge types created:**

- Repository A `CONTAINS` Service A.
- Service A `EXPOSES` API.
- API `HAS_ENDPOINT` APIEndpoint X.
- Repository B `CONTAINS` Service B.
- Service B `CALLS` APIEndpoint X when caller service can be resolved.
- Repository B `DEPENDS_ON` Repository A as an inferred repository-level summary edge.
- Evidence `MENTIONS` or `CONFIGURES` edges from file/config nodes to the matched endpoint when file-level provenance is represented.

**Confidence level:**

- **High:** exact method and normalized route match, or generated client references the spec operation ID for X.
- **Medium:** base URL plus route prefix match, but method or path parameters are partially inferred.
- **Low:** host name, service name, or documentation reference matches but no concrete call site is found.

**Evidence fields to store:**

- HTTP method, normalized route template, operation ID, base URL host, configured path prefix, client library or generated package, source file and line, parser, environment, source commit, and confidence reason.

**Safe redaction examples:**

- `https://api.example.com/v1/users/123?token=abc` -> `https://api.example.com/v1/users/{id}?token=<redacted>`.
- `Authorization: Bearer eyJ...` -> `Authorization: Bearer <redacted>` with only header presence stored.
- `https://user:pass@api.example.com` -> `https://<redacted>@api.example.com`.

### 2. Broker Topic Publication and Consumption

**Rule:** Repository A publishes to broker topic T and Repository B consumes topic T.

**Source files to inspect:**

- Messaging configuration, producer and consumer code, Kafka Connect configuration, schema registry subjects, AsyncAPI documents, queue declarations, Helm values, Terraform broker resources, dead-letter queue settings, CI integration tests, and runtime environment templates.

**Node types created:**

- `Repository` for each repository.
- `Service` for producer and consumer services.
- `Broker` for Kafka, RabbitMQ, SNS/SQS, Pub/Sub, NATS, or equivalent broker clusters.
- `BrokerTopic` for topic, queue, exchange, stream, or subject T.
- Optional `MessageSchema`, `ConsumerGroup`, `Environment`, and `ConfigValue` nodes.

**Edge types created:**

- Repository A `CONTAINS` Service A.
- Service A `PUBLISHES_TO` BrokerTopic T.
- Repository B `CONTAINS` Service B.
- Service B `CONSUMES_FROM` BrokerTopic T.
- Broker `HOSTS` BrokerTopic T.
- BrokerTopic T `USES_SCHEMA` MessageSchema when schema evidence exists.
- Repository B `DEPENDS_ON` Repository A as an inferred summary edge when producer ownership is unique or strongest.

**Confidence level:**

- **High:** identical normalized topic and environment plus explicit producer/consumer roles.
- **Medium:** identical topic name with compatible broker type but environment or cluster is inferred.
- **Low:** shared string constant or documentation reference resembles a topic but role is ambiguous.

**Evidence fields to store:**

- Topic name, broker type, cluster or bootstrap alias, producer/consumer role, consumer group, schema subject, partition or routing key pattern when relevant, environment, source files and lines, parser, and confidence reason.

**Safe redaction examples:**

- `prod.payments.card-authorized` -> `prod.payments.card-authorized` if topic names are approved non-secret metadata.
- `tenant-9f81-private-events` -> `tenant-<hash8>-private-events` when tenant identifiers are sensitive.
- `sasl.jaas.config=... password="secret"` -> `sasl.jaas.config=<redacted>` while retaining broker type and topic.

### 3. Database Schema Ownership and Cross-Repository Access

**Rule:** Repository A owns a database schema and Repository B reads or writes that schema.

**Source files to inspect:**

- In Repository A: database migrations, ORM models, schema definition files, Liquibase/Flyway changelogs, Prisma schema, Rails migrations, SQL DDL, Terraform database resources, data catalog descriptors, and ownership metadata.
- In Repository B: SQL queries, ORM models, ETL jobs, dbt models, BI extracts, connection configuration, stored procedure calls, migration references, and integration tests.

**Node types created:**

- `Repository` for each repository.
- `Service`, `Job`, or `DataPipeline` for runtime actors.
- `Database` for database instances or logical databases.
- `DatabaseSchema` for schema ownership.
- `DatabaseTable` and optional `DatabaseColumn` for table-level evidence.
- Optional `DBRole`, `ConnectionString`, `Environment`, and `Migration` nodes.

**Edge types created:**

- Repository A `OWNS` DatabaseSchema.
- Database `CONTAINS` DatabaseSchema.
- DatabaseSchema `CONTAINS` DatabaseTable.
- Repository B `CONTAINS` Service/Job/DataPipeline B.
- Service/Job/DataPipeline B `READS_FROM` DatabaseSchema or DatabaseTable.
- Service/Job/DataPipeline B `WRITES_TO` DatabaseSchema or DatabaseTable.
- Repository B `DEPENDS_ON` Repository A as an inferred summary edge.

**Confidence level:**

- **High:** Repository A migration creates schema/table and Repository B has parsed SQL or ORM access to the same normalized database/schema/table in the same environment.
- **Medium:** schema/table names match and connection alias or database name is inferred from configuration.
- **Low:** query text mentions table names without resolvable database, schema, or environment.

**Evidence fields to store:**

- Database engine, database alias, schema name, table name, operation type (`read`, `write`, `ddl`, `unknown`), migration ID, ORM entity, connection variable name, environment, source files and lines, parser, and confidence reason.

**Safe redaction examples:**

- `postgres://app:secret@db.prod.internal:5432/orders` -> `postgres://<redacted>@db.prod.internal:5432/orders`.
- `SELECT * FROM customers WHERE ssn='123-45-6789'` -> store operation `read`, table `customers`, predicate shape `ssn=<redacted>`, and query hash.
- Column `password_hash` may be stored as `password_hash` if classified metadata is allowed; example values must be `<redacted>`.

### 4. Kubernetes Service Deployment and DNS References

**Rule:** Repository A deploys Kubernetes service S and Repository B references S by DNS name.

**Source files to inspect:**

- In Repository A: Kubernetes `Service`, `Deployment`, `StatefulSet`, `Ingress`, `Gateway`, Helm charts, Kustomize overlays, Terraform Kubernetes provider resources, Argo CD applications, Flux resources, and service mesh virtual services.
- In Repository B: Kubernetes manifests, Helm values, application configuration, environment variables, service discovery configuration, DNS references in code, egress policies, service mesh routes, tests, and deployment templates.

**Node types created:**

- `Repository` for each repository.
- `Service` for logical application services.
- `K8sCluster`, `Namespace`, `K8sService`, `K8sWorkload`, `PodTemplate`, and optional `Ingress`, `Gateway`, `VirtualService`, `NetworkPolicy`, and `Environment` nodes.
- Optional `DNSName` or `ConfigValue` nodes for DNS references.

**Edge types created:**

- Repository A `DEPLOYS` K8sService S.
- Namespace `CONTAINS` K8sService S.
- K8sService S `ROUTES_TO` K8sWorkload or Service A.
- Repository B `REFERENCES` DNSName for S.
- Service B `CALLS` K8sService S when application ownership is resolved.
- Repository B `DEPENDS_ON` Repository A as an inferred summary edge.

**Confidence level:**

- **High:** full Kubernetes DNS name matches `service.namespace.svc.cluster.local`, or same cluster and namespace are explicit.
- **Medium:** short service name matches with namespace inferred from deployment context.
- **Low:** unqualified host name matches a service name but namespace, cluster, or environment is unknown.

**Evidence fields to store:**

- Service name, namespace, cluster, port name/number, protocol, DNS form, manifest kind, workload selector labels, environment, source files and lines, parser, and confidence reason.

**Safe redaction examples:**

- `payments-api.payments.svc.cluster.local` -> unchanged if service DNS is approved metadata.
- `customer-123-api.private.svc.cluster.local` -> `customer-<hash8>-api.private.svc.cluster.local` when tenant identifiers are sensitive.
- `API_URL=https://token@payments-api.payments.svc` -> `API_URL=https://<redacted>@payments-api.payments.svc`.

### 5. OpenAPI Spec Providers and Generated or Configured Clients

**Rule:** Repository A defines an OpenAPI spec and Repository B has generated clients or configured base URLs for that API.

**Source files to inspect:**

- In Repository A: `openapi.yaml`, `openapi.json`, Swagger files, generated API documentation, operation annotations, API gateway spec imports, service catalog API descriptors, and published client package metadata.
- In Repository B: generated client source directories, OpenAPI generator metadata, package lockfiles, dependency manifests, client configuration, API base URL settings, import paths, codegen config files, and CI steps that download or generate clients.

**Node types created:**

- `Repository` for each repository.
- `API` and `APIEndpoint` for spec-defined APIs and operations.
- `OpenAPISpec` for the specification artifact.
- `GeneratedClient` for generated SDKs or typed clients.
- Optional `Package`, `ConfigValue`, `Environment`, and `BuildStep` nodes.

**Edge types created:**

- Repository A `DEFINES` OpenAPISpec.
- OpenAPISpec `DESCRIBES` API.
- API `HAS_ENDPOINT` APIEndpoint.
- Repository B `CONTAINS` GeneratedClient.
- GeneratedClient `GENERATED_FROM` OpenAPISpec when generator metadata or checksum matches.
- Service B `CALLS` API when runtime configuration or client usage is detected.
- Repository B `DEPENDS_ON` Repository A as an inferred summary edge.

**Confidence level:**

- **High:** generated metadata, spec checksum, package coordinate, or operation IDs match Repository A's spec.
- **Medium:** configured base URL matches spec servers and generated client class/package names match API name.
- **Low:** dependency or import name resembles the API but no spec identity, checksum, or server URL matches.

**Evidence fields to store:**

- Spec path, spec version, title, server URLs after redaction, operation IDs, generator name and version, generated package/module name, package coordinate, spec checksum, source files and lines, parser, and confidence reason.

**Safe redaction examples:**

- `servers: [{ url: "https://api.example.com/{tenant}" }]` -> store template and mark `{tenant}` as variable.
- `x-api-key: abc123` in an example -> `x-api-key: <redacted>`.
- Generated config `basePath=https://api.example.com?key=secret` -> `basePath=https://api.example.com?key=<redacted>`.

### 6. Shared Owner, Environment, Namespace, or Runtime Dependency

**Rule:** Repository A and Repository B share an owner group, environment, namespace, or runtime dependency.

**Source files to inspect:**

- CODEOWNERS files, service catalog descriptors, repository metadata, team manifests, Terraform workspaces, Helm values, Kubernetes namespaces, Argo CD/Flux applications, CI/CD pipeline definitions, dependency manifests and lockfiles, container image references, runtime environment manifests, and infrastructure modules.

**Node types created:**

- `Repository` for each repository.
- `Group`, `User`, or `Team` for ownership.
- `Environment` for deployment stage or runtime context.
- `Namespace` for Kubernetes or cloud namespaces.
- `RuntimeDependency`, `Package`, `ContainerImage`, `InfrastructureModule`, or `PlatformService` for shared dependencies.
- Optional `Service`, `BuildPipeline`, and `DeploymentTarget` nodes.

**Edge types created:**

- Group/Team `OWNS` Repository A and Repository B.
- Repository A/B `DEPLOYS_TO` Environment or Namespace.
- Repository A/B `USES` RuntimeDependency, Package, ContainerImage, InfrastructureModule, or PlatformService.
- Repository A `RELATED_TO` Repository B with relationship reason `shared_owner`, `shared_environment`, `shared_namespace`, or `shared_runtime_dependency`.
- Repository A `MAY_IMPACT` Repository B only when the shared dependency is operationally meaningful, such as the same mutable infrastructure module or shared runtime service.

**Confidence level:**

- **High:** exact stable owner group ID, namespace UID, environment identifier, or dependency coordinate and version match.
- **Medium:** normalized names match across repositories but stable IDs are unavailable.
- **Low:** fuzzy team names, path conventions, or broad dependency families match without a stable shared identifier.

**Evidence fields to store:**

- Owner group ID or slug, environment name and source, namespace name and cluster, dependency coordinate and version, image digest, module source and version, source files and lines, parser, relationship reason, and confidence reason.

**Safe redaction examples:**

- `@company/payments-platform` -> unchanged if group slugs are approved metadata.
- `namespace: tenant-42-prod` -> `namespace: tenant-<hash8>-prod` when tenant identifiers are sensitive.
- `registry.example.com/private/app:sha256-deadbeef...` -> store registry host, image path policy label, and digest prefix only if allowed; otherwise store keyed hash.

## Redaction and Matching Guidance

Inference needs enough normalized information to join evidence across repositories without exposing sensitive values. Implementations should:

- Strip credentials, tokens, query secret parameters, and inline keys before storing display values.
- Store keyed hashes for full values that are sensitive but need exact equality matching.
- Preserve non-sensitive structure such as protocol, host, route template, topic shape, schema name, namespace, dependency coordinate, and version when allowed by policy.
- Classify evidence values before persistence using field context, secret scanners, and allow/deny lists.
- Keep raw source snippets out of graph properties unless they have passed redaction and size limits.
- Record `redaction_applied: true` and `redaction_strategy`, such as `credential-strip`, `query-param-redact`, `tenant-hash`, `secret-placeholder`, or `value-hash-only`.

## Repository-Level Summary Edges

Rules may create resource-level edges first and repository-level summary edges second. A summary edge such as Repository B `DEPENDS_ON` Repository A should include:

- `derived_from_edge_ids`: resource-level edge identifiers used to derive the summary.
- `relationship_rules`: rule identifiers that contributed evidence.
- `highest_confidence_level` and `aggregate_confidence_score`.
- `evidence_count`: number of independent source observations.
- `environments`: environments where the relationship appears.
- `last_observed_at`: latest observation time.

Repository-level summary edges should be recomputed when source evidence expires or when a higher-confidence owner for a resource is discovered.

## Implementation Status

- Added an initial deterministic resolver in `dust_graph.resolvers.cross_repository` that accepts two or more repository collector fixtures and returns a combined fixture with inferred cross-repository edges.
- Implemented API call inference from consumer URL/config hints to provider OpenAPI endpoints, with resource-level `CALLS` edges and repository-level summary `CALLS` edges.
- Implemented shared topic/queue inference between cross-repository broker producers and consumers using normalized topic or queue names.
- Implemented shared database inference using redacted-safe database identifiers, parsed database names, and schema/config hints to create `CONNECTS_TO`, `READS_FROM`, and `WRITES_TO` edges.
- Added confidence levels, confidence reasons, matched values, and source evidence metadata to inferred edges.
- Expanded repository collector config hints so fixture repositories can expose redaction-safe API URL, topic/queue name, and database-name hints for cross-repository resolution.
