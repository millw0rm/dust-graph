# M2 Initial Saved Query Catalog

## Scope

This M2 task plan defines the first repository-owned saved queries for Dust Graph. The catalog is intentionally backend-neutral: each entry describes the product question, required inputs, and graph vocabulary it should traverse, but does not prescribe Cypher, Kuzu SQL, or any other query language.

These saved queries are the initial contract between ingestion, graph storage, and user-facing workflows. Later implementation work should assign stable `query_id` values, add executable query definitions, validate parameters, and provide fixtures that prove each query shape.

## Catalog Conventions

Each saved query should:

- Accept stable Dust Graph identifiers where possible, with optional human-friendly lookup fields such as repository slug or service name.
- Return matched nodes, traversed relationship evidence, source metadata, confidence, and environment context.
- Prefer explicit edges from the canonical vocabulary over inferred joins.
- Preserve directionality in results so users can distinguish ownership, deployment, reachability, and observed traffic evidence.
- Include stale or low-confidence records only when the caller opts in.

Common optional parameters for every query:

- `environment`: limit results to a deployment context such as `dev`, `staging`, or `prod`.
- `source_system`: limit results to records from a specific integration or extractor.
- `min_confidence`: omit records below the requested confidence threshold.
- `as_of`: evaluate records whose validity or observation window overlaps a timestamp.
- `include_stale`: include records not observed in the latest ingestion window.

## Saved Queries

### 1. `repository_owned_apis`

- **User question:** Which APIs are owned by this repository?
- **Expected input parameters:**
  - `repository_id` or `repository_slug`.
  - Optional common parameters: `environment`, `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `Repository`
  - `Service`
  - `API`
  - `APIEndpoint` when endpoint-level detail is requested.
- **Expected edge types used:**
  - `Repository` `CONTAINS` `Service`
  - `Service` `EXPOSES` `API`
  - `API` `HAS_ENDPOINT` `APIEndpoint` once endpoint ingestion is executable.
  - Optional `User` or `Group` `OWNS` `Repository` for ownership evidence in expanded results.

### 2. `api_reachable_databases`

- **User question:** Which databases are reachable from this API?
- **Expected input parameters:**
  - `api_id` or API lookup fields such as `api_name` plus `environment`.
  - Optional `max_depth` for service-to-service hops before reaching a database.
  - Optional `include_observed_connections` to include observed runtime traffic in addition to configured dependencies.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `API`
  - `Service`
  - `Database`
  - Optional `K8sService`, `Ingress`, `Pod`, `ServiceAccount`, and `Port` for runtime path evidence.
- **Expected edge types used:**
  - `Service` `EXPOSES` `API`
  - `Service` `CONNECTS_TO` `Database`
  - Optional `Service` `CALLS` `Service` for transitive service dependencies.
  - Optional `Service`, `Pod`, `K8sService`, or `IPAddress` `OBSERVED_CONNECTS_TO` `Database`.
  - Optional `Ingress` or `K8sService` `ROUTES_TO` `Service` or `Pod` for Kubernetes path evidence.

### 3. `api_callable_principals`

- **User question:** Which users and groups can call this API?
- **Expected input parameters:**
  - `api_id` or API lookup fields such as `api_name` plus `environment`.
  - Optional `include_indirect_members` to expand nested groups and role grants.
  - Optional `include_service_accounts` to include non-human callers.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `API`
  - `APIEndpoint` when endpoint-level authorization is modeled.
  - `User`
  - `Group`
  - `Role`
  - `Permission`
  - Optional `ServiceAccount`.
- **Expected edge types used:**
  - `User` or `Group` `CAN_CALL` `API`
  - Optional `User` `MEMBER_OF` `Group`
  - Optional `User`, `Group`, or `ServiceAccount` `HAS_ROLE` `Role`
  - Optional `Role` `GRANTS` `Permission`
  - Optional `Permission` `CAN_CALL` or `CAN_ACCESS` `API` / `APIEndpoint`, if authorization is normalized through permissions.

### 4. `repository_deployed_services`

- **User question:** Which services are deployed from this repository?
- **Expected input parameters:**
  - `repository_id` or `repository_slug`.
  - Optional `deployment_target_type` such as `Namespace`, `K8sCluster`, `VM`, or `Host`.
  - Optional common parameters: `environment`, `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `Repository`
  - `Service`
  - `Namespace`
  - `K8sCluster`
  - Optional `K8sService`, `Pod`, `VM`, and `Host`.
- **Expected edge types used:**
  - `Repository` `CONTAINS` `Service`
  - `Service` `DEPLOYS_TO` `Namespace`, `K8sCluster`, `VM`, or `Host`
  - Optional `Namespace` `CONTAINS` `K8sService` / `Pod`
  - Optional `K8sService` `ROUTES_TO` `Pod` or `Service`.

### 5. `runtime_service_contributing_repositories`

- **User question:** Which repositories contribute to this runtime service?
- **Expected input parameters:**
  - `service_id` or service lookup fields such as `service_name` plus `environment`.
  - Optional `include_transitive_dependencies` to include repositories for called services or shared artifacts.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `Service`
  - `Repository`
  - Optional `Namespace`, `K8sService`, `Pod`, and `ServiceAccount` for runtime identity confirmation.
- **Expected edge types used:**
  - `Repository` `CONTAINS` `Service`
  - Optional `Service` `CALLS` `Service` for transitive runtime dependency contributors.
  - Optional `Service` `DEPLOYS_TO` deployment target nodes for matching logical and runtime service identities.
  - Optional `Pod` or workload node `RUNS_AS` `ServiceAccount` when runtime service ownership is inferred from workload identity.

### 6. `vpn_users_reaching_k8s_service`

- **User question:** Which VPN users can reach this Kubernetes service?
- **Expected input parameters:**
  - `k8s_service_id` or Kubernetes lookup fields such as `cluster`, `namespace`, and `service_name`.
  - Optional `vpn_id` to limit to one VPN gateway or tunnel.
  - Optional `port` and `protocol` to constrain network reachability.
  - Optional common parameters: `environment`, `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `User`
  - `Group`
  - `VPN`
  - `K8sService`
  - `Namespace`
  - `K8sCluster`
  - `NetworkPolicy`
  - `FirewallPolicy`
  - `Subnet`
  - `IPAddress`
  - `Port`
- **Expected edge types used:**
  - `User` `MEMBER_OF` `Group`
  - `User` or `Group` `CAN_ACCESS` `VPN`
  - `VPN` `ROUTES_TO` `Subnet`, `IPAddress`, `Namespace`, or `K8sService`
  - `FirewallPolicy` or `NetworkPolicy` `ALLOWS` `K8sService`, `IPAddress`, `Port`, or related target nodes
  - Optional `K8sService` `ROUTES_TO` `Pod` for backend workload evidence.

### 7. `database_allowing_firewall_policies`

- **User question:** Which firewall policies allow traffic to this database?
- **Expected input parameters:**
  - `database_id` or database lookup fields such as `database_name`, `engine`, and `environment`.
  - Optional `source_node_id` or `source_cidr` to limit policies by traffic source.
  - Optional `port` and `protocol`.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `Database`
  - `Firewall`
  - `FirewallPolicy`
  - `Subnet`
  - `IPAddress`
  - `Port`
  - Optional `Service`, `K8sService`, `Pod`, `VM`, `Host`, `VPN`, `User`, and `Group` for source context.
- **Expected edge types used:**
  - `Firewall` `CONTAINS` `FirewallPolicy`
  - `FirewallPolicy` `ALLOWS` `Database`, `IPAddress`, `Subnet`, or `Port`
  - Optional source-side `ALLOWS` or `ROUTES_TO` edges from policy to allowed source nodes.
  - Optional `Service`, `Pod`, `VM`, or `Host` `CONNECTS_TO` / `OBSERVED_CONNECTS_TO` `Database` to show traffic using the policy.

### 8. `observed_connections_without_policy`

- **User question:** Which observed connections do not have a matching policy?
- **Expected input parameters:**
  - Optional `source_node_id` and `target_node_id` to scope the check.
  - Optional `target_type` such as `Database`, `API`, `K8sService`, `Port`, or `IPAddress`.
  - Optional `port`, `protocol`, and `environment`.
  - Optional `observed_since` to focus on recent traffic.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - Source-side nodes: `Service`, `Pod`, `VM`, `Host`, `User`, `ServiceAccount`, `VPN`, `IPAddress`.
  - Target-side nodes: `Database`, `API`, `K8sService`, `Service`, `IPAddress`, `Port`, `Topic`, `Queue`, or `Broker`.
  - Policy nodes: `FirewallPolicy`, `NetworkPolicy`, `Role`, and `Permission` where applicable.
- **Expected edge types used:**
  - `OBSERVED_CONNECTS_TO`
  - Policy or entitlement edges that could justify the observation: `ALLOWS`, `CAN_ACCESS`, `CAN_CALL`, `GRANTS`, `HAS_ROLE`, `MEMBER_OF`, and `ROUTES_TO`.
  - Optional `DENIES` edges to flag explicitly denied observed traffic separately from traffic with no policy.

### 9. `exposed_apis_missing_ownership`

- **User question:** Which exposed APIs are missing ownership metadata?
- **Expected input parameters:**
  - Optional `repository_id`, `service_id`, or `environment` to scope results.
  - Optional `public_only` to focus on internet-facing APIs.
  - Optional `include_endpoint_details` to show affected `APIEndpoint` records.
  - Optional common parameters: `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - `API`
  - `APIEndpoint`
  - `Service`
  - `Repository`
  - Ownership candidates: `User`, `Group`, `ServiceAccount`, or `Role`.
  - Optional exposure path nodes: `Ingress`, `K8sService`, `Port`, `IPAddress`, `Subnet`, and `FirewallPolicy`.
- **Expected edge types used:**
  - `Service` `EXPOSES` `API`
  - Optional `API` `HAS_ENDPOINT` `APIEndpoint`
  - Missing or absent ownership path checks over `OWNS` edges from `User`, `Group`, `ServiceAccount`, or `Role` to `API`, `Service`, or `Repository`.
  - Optional `Ingress`, `K8sService`, `FirewallPolicy`, or `Service` `EXPOSES` / `ROUTES_TO` exposure edges.

### 10. `principal_compromise_blast_radius`

- **User question:** What is the blast radius from a compromised user, service account, or VM?
- **Expected input parameters:**
  - Exactly one starting identity or compute parameter: `user_id`, `service_account_id`, or `vm_id`.
  - Optional `max_depth` for traversals.
  - Optional `impact_types` such as `apis`, `databases`, `repositories`, `services`, `kubernetes`, `network`, or `messages`.
  - Optional `include_observed_connections` to add runtime traffic beyond declared permissions.
  - Optional common parameters: `environment`, `source_system`, `min_confidence`, `as_of`, `include_stale`.
- **Expected node types used:**
  - Start nodes: `User`, `ServiceAccount`, or `VM`.
  - Identity and entitlement nodes: `Group`, `Role`, `Permission`, and `VPN`.
  - Application nodes: `Repository`, `Service`, `API`, and `APIEndpoint`.
  - Runtime and network nodes: `K8sCluster`, `Namespace`, `K8sService`, `Pod`, `Host`, `Subnet`, `IPAddress`, `Port`, `Firewall`, `FirewallPolicy`, and `NetworkPolicy`.
  - Data and messaging nodes: `Database`, `Broker`, `Topic`, and `Queue`.
- **Expected edge types used:**
  - Identity expansion: `MEMBER_OF`, `HAS_ROLE`, `GRANTS`, `RUNS_AS`.
  - Access and callability: `CAN_ACCESS`, `CAN_CALL`, `ALLOWS`, `ROUTES_TO`.
  - Ownership and code impact: `OWNS`, `CONTAINS`, `DEPLOYS_TO`, `EXPOSES`.
  - Runtime and data impact: `CALLS`, `CONNECTS_TO`, `OBSERVED_CONNECTS_TO`, `READS_FROM`, `WRITES_TO`, `PUBLISHES_TO`, and `CONSUMES_FROM`.
  - Optional `DENIES` edges to stop or annotate traversal paths blocked by explicit policy.

## Implementation Follow-Ups

- Assign immutable `query_id` values and version each saved query definition.
- Add executable backend-specific query mappings behind the graph adapter rather than exposing backend query languages to callers.
- Add fixtures for at least one positive and one negative case for every saved query.
- Extend the canonical schema with any edge types used by repository ingestion but not yet defined in the base schema, especially `HAS_ENDPOINT`.
- Define result schemas for path evidence, matched node summaries, missing-policy diagnostics, and blast-radius traversal explanations.
