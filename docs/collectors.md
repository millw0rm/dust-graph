# Planned Collectors

Dust Graph collectors ingest evidence from repositories, platforms, control planes, and imported scans into the canonical graph vocabulary. Each collector should emit records with provenance, environment, confidence, first-seen, and last-seen metadata so graph consumers can explain where a fact came from and when it was observed.

Collectors must normalize facts into nodes and edges without persisting secrets, packet payloads, credentials, or raw sensitive business data. When a source contains sensitive values, collectors store safe identifiers, names, paths, hashes, redaction flags, and provenance only.

## Repository Collector

The repository collector analyzes source repositories and repository-hosting metadata to discover logical services, code ownership, declared APIs, deployment hints, datastore references, messaging references, and configuration dependencies.

1. **Inputs**
   - Git clone URLs, local checkout paths, repository hosting API metadata, branch or commit refs, CODEOWNERS files, package manifests, service catalog descriptors, CI/CD workflow files, infrastructure-as-code files, deployment manifests, OpenAPI specs, README files, and configuration files.
2. **Output node types**
   - `Repository`, `Service`, `API`, `APIEndpoint`, `User`, `Group`, `ServiceAccount`, `Namespace`, `Database`, `Broker`, `Topic`, `Queue`, and placeholder external `Service` nodes when only a dependency endpoint is known.
3. **Output edge types**
   - `CONTAINS`, `OWNS`, `EXPOSES`, `HAS_ENDPOINT`, `DEPLOYS_TO`, `CALLS`, `CONNECTS_TO`, `PUBLISHES_TO`, `CONSUMES_FROM`, `READS_FROM`, `WRITES_TO`, and `RUNS_AS`.
4. **Required credentials**
   - Read-only repository access token or SSH key for private repositories.
   - Optional read-only repository hosting API token for organization, team, repository visibility, branch, pull request, and ownership metadata.
   - No write access is required.
5. **Sensitive data handling rules**
   - Never persist secret values from `.env`, Terraform state, CI secret stores, Kubernetes Secret manifests, private keys, certificates, cookies, tokens, passwords, or connection strings containing credentials.
   - Store environment variable names and secret reference names only.
   - Store parsed non-sensitive connection metadata only after usernames, passwords, tokens, query-string secrets, and high-entropy values are redacted.
   - Preserve file path, line range, commit SHA, and extraction rule as provenance instead of raw sensitive content.
6. **Initial mock/sample data format**

   ```yaml
   collector: repository
   source:
     repository: github.com/acme/payments
     ref: 4f8c2a1
   nodes:
     - type: Repository
       id: repo:github.com/acme/payments
       name: payments
     - type: Service
       id: service:payments-api
       name: payments-api
     - type: API
       id: api:payments:v1
       name: Payments API
     - type: Database
       id: database:postgres:payments
       engine: postgres
       database_name: payments
   edges:
     - type: CONTAINS
       from: repo:github.com/acme/payments
       to: service:payments-api
     - type: EXPOSES
       from: service:payments-api
       to: api:payments:v1
     - type: CONNECTS_TO
       from: service:payments-api
       to: database:postgres:payments
   redactions:
     - source_ref: config/prod.env:12
       field: DATABASE_URL
       reason: credential-bearing connection string
   ```

## Kubernetes Collector

The Kubernetes collector reads cluster API resources and selected workload metadata to connect deployments, namespaces, services, pods, ingress routes, service accounts, network policies, ports, and observed runtime placement.

1. **Inputs**
   - Kubernetes API resources, kubeconfig contexts, cluster names, namespaces, workloads, pods, services, ingress resources, gateway resources, service accounts, role bindings, config maps, network policies, endpoint slices, labels, annotations, owner references, container image references, and selected event metadata.
2. **Output node types**
   - `K8sCluster`, `Namespace`, `Service`, `K8sService`, `Pod`, `Ingress`, `NetworkPolicy`, `ServiceAccount`, `Role`, `Permission`, `Port`, `IPAddress`, `Host`, `Database`, `Broker`, `Topic`, and `Queue` when safe references are found.
3. **Output edge types**
   - `CONTAINS`, `DEPLOYS_TO`, `ROUTES_TO`, `EXPOSES`, `RUNS_AS`, `HAS_ROLE`, `GRANTS`, `ALLOWS`, `DENIES`, `CONNECTS_TO`, `PUBLISHES_TO`, `CONSUMES_FROM`, and `OBSERVED_CONNECTS_TO` when endpoint or flow evidence is available.
4. **Required credentials**
   - Read-only Kubernetes credentials scoped to list and watch non-secret workload and networking resources.
   - Optional permission to read Secret names and keys as references only; Secret data access should not be granted for initial collectors.
   - Optional cloud or cluster inventory credentials for node and load balancer enrichment.
5. **Sensitive data handling rules**
   - Do not read or persist Kubernetes Secret data values.
   - Treat ConfigMap values as potentially sensitive; persist only keys and safe, allowlisted routing metadata unless a value passes redaction checks.
   - Redact environment variable values from pod specs and store `valueFrom` references by name/key only.
   - Do not store container command arguments that match password, token, key, or credential patterns.
6. **Initial mock/sample data format**

   ```yaml
   collector: kubernetes
   source:
     cluster: prod-us-east-1
     namespace: payments
   nodes:
     - type: K8sCluster
       id: k8scluster:prod-us-east-1
     - type: Namespace
       id: namespace:prod-us-east-1:payments
       name: payments
     - type: K8sService
       id: k8sservice:prod-us-east-1:payments:payments-api
       name: payments-api
     - type: Pod
       id: pod:prod-us-east-1:payments:payments-api-7d8f
   edges:
     - type: CONTAINS
       from: k8scluster:prod-us-east-1
       to: namespace:prod-us-east-1:payments
     - type: ROUTES_TO
       from: k8sservice:prod-us-east-1:payments:payments-api
       to: pod:prod-us-east-1:payments:payments-api-7d8f
   redactions:
     - source_ref: pod/payments-api-7d8f.env[STRIPE_SECRET_KEY]
       reason: secret-like environment variable name
   ```

## FortiGate Collector

The FortiGate collector imports firewall inventory, address objects, service objects, policies, virtual IPs, VPNs, routes, interfaces, and selected traffic-policy metadata from FortiGate appliances or FortiManager.

1. **Inputs**
   - FortiGate or FortiManager API exports, firewall policies, address and address-group objects, service and service-group objects, interface definitions, zones, VIPs, static routes, policy packages, VPN definitions, NAT rules, tags, comments, and optional summarized traffic counters.
2. **Output node types**
   - `Firewall`, `FirewallPolicy`, `VPN`, `Subnet`, `IPAddress`, `Port`, `Host`, `Service`, `K8sService`, `Namespace`, `Database`, `Broker`, `Topic`, and `Queue` when targets can be reconciled to existing graph nodes.
3. **Output edge types**
   - `CONTAINS`, `ALLOWS`, `DENIES`, `ROUTES_TO`, `EXPOSES`, `CONNECTS_TO`, `CAN_ACCESS`, and `OBSERVED_CONNECTS_TO` for summarized policy hit or flow evidence.
4. **Required credentials**
   - Read-only FortiGate REST API token, FortiManager API token, or sanitized configuration export.
   - Access should be scoped to configuration and policy reads; administrative write permissions are not required.
5. **Sensitive data handling rules**
   - Do not persist pre-shared keys, certificates, local user passwords, administrative session tokens, packet captures, or decrypted payload content.
   - Store VPN and policy names, object names, CIDRs, interface names, ports, protocols, rule IDs, actions, NAT metadata, and comments after redacting secret-like text.
   - Store summarized counters only; avoid raw logs with user identifiers unless explicitly approved and minimized.
6. **Initial mock/sample data format**

   ```yaml
   collector: fortigate
   source:
     firewall: edge-fw-01
     vdom: root
   nodes:
     - type: Firewall
       id: firewall:edge-fw-01
     - type: FirewallPolicy
       id: firewallpolicy:edge-fw-01:100
       policy_id: 100
       action: accept
     - type: Subnet
       id: subnet:10.20.0.0/16
       cidr: 10.20.0.0/16
     - type: Port
       id: port:tcp:443
       protocol: tcp
       number: 443
   edges:
     - type: CONTAINS
       from: firewall:edge-fw-01
       to: firewallpolicy:edge-fw-01:100
     - type: ALLOWS
       from: firewallpolicy:edge-fw-01:100
       to: subnet:10.20.0.0/16
     - type: ALLOWS
       from: firewallpolicy:edge-fw-01:100
       to: port:tcp:443
   redactions: []
   ```

## OpenAPI Collector

The OpenAPI collector ingests OpenAPI 2.0 and 3.x specifications from repositories, registries, service catalogs, gateway exports, or explicit uploads to model API surfaces and operations.

1. **Inputs**
   - OpenAPI JSON or YAML documents, service catalog links, API registry exports, gateway-provided specs, source repository paths, base URLs, server objects, tags, paths, operations, security schemes, schemas, and ownership annotations.
2. **Output node types**
   - `API`, `APIEndpoint`, `Service`, `Repository`, `Group`, `User`, `ServiceAccount`, `Role`, `Permission`, and `Port` when server details include protocol and port.
3. **Output edge types**
   - `EXPOSES`, `HAS_ENDPOINT`, `OWNS`, `CONTAINS`, `CAN_CALL`, `CAN_ACCESS`, and `GRANTS` for documented security schemes or explicit authorization annotations.
4. **Required credentials**
   - Read-only access to the source repository, API registry, artifact store, or gateway export endpoint.
   - No production API invocation credentials are required because the collector reads specifications rather than calling business endpoints.
5. **Sensitive data handling rules**
   - Do not store example request or response bodies that contain credentials, tokens, personal data, payment data, or other sensitive domain data.
   - Persist path templates, methods, operation IDs, tags, server hostnames, documented auth scheme names, and schema names.
   - Redact examples, default values, enum values, descriptions, and extensions when they match sensitive-name or high-entropy patterns.
6. **Initial mock/sample data format**

   ```yaml
   collector: openapi
   source:
     spec_uri: repo://github.com/acme/payments/openapi.yaml
     spec_version: 3.1.0
   nodes:
     - type: API
       id: api:payments:v1
       name: Payments API
       version: v1
     - type: APIEndpoint
       id: apiendpoint:payments:v1:get:/payments/{id}
       method: GET
       path: /payments/{id}
       operation_id: getPayment
   edges:
     - type: HAS_ENDPOINT
       from: api:payments:v1
       to: apiendpoint:payments:v1:get:/payments/{id}
   redactions:
     - source_ref: components.examples.CreatePayment.value.card_number
       reason: sample payment data
   ```

## API Gateway Collector

The API gateway collector ingests configured routes, listeners, virtual hosts, upstreams, policies, plugins, certificates by reference, and ownership tags from gateway products such as Kong, Envoy, NGINX, Apigee, AWS API Gateway, Azure API Management, and similar systems.

1. **Inputs**
   - Gateway control-plane APIs, declarative config files, route tables, hostnames, base paths, methods, upstream targets, listeners, stages, deployments, plugins, authentication and authorization policy names, rate-limit policies, mTLS settings, tags, and optional OpenAPI exports.
2. **Output node types**
   - `API`, `APIEndpoint`, `Service`, `K8sService`, `Ingress`, `Port`, `IPAddress`, `Host`, `Role`, `Permission`, `ServiceAccount`, `Group`, `User`, and `FirewallPolicy` or `NetworkPolicy` when gateway policy maps to access rules.
3. **Output edge types**
   - `EXPOSES`, `HAS_ENDPOINT`, `ROUTES_TO`, `CAN_CALL`, `CAN_ACCESS`, `GRANTS`, `OWNS`, `ALLOWS`, `DENIES`, and `OBSERVED_CONNECTS_TO` for summarized gateway metrics or access logs.
4. **Required credentials**
   - Read-only gateway control-plane token, cloud IAM role, configuration export, or access to versioned declarative gateway config.
   - Optional metrics-read permission for route-level aggregate traffic counts.
5. **Sensitive data handling rules**
   - Do not persist API keys, client secrets, JWT signing keys, mTLS private keys, certificate private material, session cookies, raw authorization headers, request bodies, response bodies, or full access logs.
   - Store certificate names/fingerprints, auth policy names, route IDs, hostnames, paths, methods, upstream references, and aggregate counters.
   - Hash or redact consumer identifiers unless they map to approved graph principals.
6. **Initial mock/sample data format**

   ```yaml
   collector: api_gateway
   source:
     gateway: kong-prod
     workspace: default
   nodes:
     - type: API
       id: api:payments:gateway
       hostname: api.example.com
     - type: APIEndpoint
       id: apiendpoint:payments:gateway:post:/payments
       method: POST
       path: /payments
     - type: Service
       id: service:payments-api
   edges:
     - type: HAS_ENDPOINT
       from: api:payments:gateway
       to: apiendpoint:payments:gateway:post:/payments
     - type: ROUTES_TO
       from: apiendpoint:payments:gateway:post:/payments
       to: service:payments-api
   redactions:
     - source_ref: plugin/key-auth/config/key_names
       reason: credential material excluded
   ```

## Hubble/Cilium Collector

The Hubble/Cilium collector ingests Kubernetes network flow metadata and Cilium policy state to model observed workload connectivity and compare it with expected network policy.

1. **Inputs**
   - Hubble flow exports, Cilium API state, CiliumNetworkPolicy and CiliumClusterwideNetworkPolicy resources, endpoint identities, labels, DNS metadata, verdicts, L4/L7 protocol summaries, namespaces, services, pods, IPs, ports, and time-windowed aggregate flow samples.
2. **Output node types**
   - `K8sCluster`, `Namespace`, `Pod`, `K8sService`, `Service`, `NetworkPolicy`, `IPAddress`, `Port`, `Database`, `Broker`, `Topic`, `Queue`, and external `Host` or `Service` nodes for unresolved destinations.
3. **Output edge types**
   - `OBSERVED_CONNECTS_TO`, `ALLOWS`, `DENIES`, `ROUTES_TO`, `CONTAINS`, `CONNECTS_TO`, `PUBLISHES_TO`, and `CONSUMES_FROM` when protocol metadata identifies datastore or messaging use.
4. **Required credentials**
   - Read-only access to Hubble Relay, exported Hubble logs, or Cilium observability APIs.
   - Read-only Kubernetes access to reconcile pods, namespaces, services, labels, and policy resources.
5. **Sensitive data handling rules**
   - Do not persist packet payloads, HTTP bodies, request headers, cookies, authorization headers, query strings with secrets, DNS payloads beyond queried names, or full raw flow logs by default.
   - Store minimized flow metadata: source, destination, namespace, labels, DNS name, port, protocol, verdict, policy reference, timestamps, and aggregate counts.
   - Hash or truncate high-cardinality external IP evidence when full retention is not needed.
6. **Initial mock/sample data format**

   ```yaml
   collector: hubble_cilium
   source:
     cluster: prod-us-east-1
     window: 2026-05-30T00:00:00Z/2026-05-30T01:00:00Z
   nodes:
     - type: Pod
       id: pod:prod-us-east-1:payments:payments-api-7d8f
     - type: IPAddress
       id: ip:10.44.2.18
       address: 10.44.2.18
     - type: Port
       id: port:tcp:5432
       protocol: tcp
       number: 5432
   edges:
     - type: OBSERVED_CONNECTS_TO
       from: pod:prod-us-east-1:payments:payments-api-7d8f
       to: ip:10.44.2.18
       port_id: port:tcp:5432
       verdict: forwarded
       count: 42
   redactions: []
   ```

## Authz/OpenFGA Collector

The Authz/OpenFGA collector imports authorization models, relationship tuples, usersets, permissions, object namespaces, and application principal mappings from OpenFGA or compatible authorization systems.

1. **Inputs**
   - OpenFGA store IDs, authorization model versions, type definitions, relations, tuples, usersets, object identifiers, application-to-object mappings, user and group identity mappings, service account mappings, and optional evaluation traces from approved test scenarios.
2. **Output node types**
   - `User`, `Group`, `ServiceAccount`, `Role`, `Permission`, `Repository`, `Service`, `API`, `APIEndpoint`, `Database`, `Broker`, `Topic`, `Queue`, and synthetic object nodes mapped to canonical types when available.
3. **Output edge types**
   - `MEMBER_OF`, `HAS_ROLE`, `GRANTS`, `CAN_ACCESS`, `CAN_CALL`, `OWNS`, `CONTAINS`, and `RUNS_AS`.
4. **Required credentials**
   - Read-only OpenFGA API token or exported model and tuple files.
   - Optional identity provider read token for resolving user, group, and service account names to approved graph principal IDs.
5. **Sensitive data handling rules**
   - Do not persist authentication tokens, session identifiers, passwords, raw JWTs, or sensitive user profile attributes.
   - Store principal IDs, display names only when approved, group names, relation names, object IDs, model IDs, and tuple provenance.
   - Minimize personal data; hash or pseudonymize user IDs when the graph does not require direct identity display.
6. **Initial mock/sample data format**

   ```yaml
   collector: authz_openfga
   source:
     store_id: 01HRPAYMENTS
     model_id: 01HRMODEL
   nodes:
     - type: User
       id: user:alice
       display_name: Alice
     - type: Group
       id: group:payments-admins
     - type: Permission
       id: permission:payments-api:write
       action: write
   edges:
     - type: MEMBER_OF
       from: user:alice
       to: group:payments-admins
     - type: GRANTS
       from: group:payments-admins
       to: permission:payments-api:write
   redactions:
     - source_ref: users/alice.email
       reason: personal attribute not needed for graph traversal
   ```

## Database Metadata Collector

The database metadata collector reads database inventory and schema metadata to model datastore assets, schemas, tables or collections at the chosen granularity, roles, service connectivity, and safe ownership hints.

1. **Inputs**
   - Cloud database inventory APIs, database information schemas, system catalogs, sanitized schema dumps, migration metadata, database roles, grants, extensions, endpoints, ports, engine versions, tags, owners, and optional aggregate usage statistics.
2. **Output node types**
   - `Database`, `Service`, `ServiceAccount`, `Role`, `Permission`, `User`, `Group`, `Port`, `IPAddress`, `Host`, and optional `Repository` nodes when migration provenance maps back to code.
3. **Output edge types**
   - `CONTAINS`, `CONNECTS_TO`, `CAN_ACCESS`, `HAS_ROLE`, `GRANTS`, `OWNS`, `DEPLOYS_TO`, `READS_FROM`, `WRITES_TO`, and `OBSERVED_CONNECTS_TO` for approved aggregate connection evidence.
4. **Required credentials**
   - Read-only metadata account with access to system catalogs or information schema only.
   - Optional cloud inventory read role for managed database resources, tags, endpoints, and network placement.
   - No permission to read application table data is required.
5. **Sensitive data handling rules**
   - Do not persist row data, query result data, backups, dumps containing data, passwords, connection strings with credentials, secrets, or full SQL text containing literals.
   - Store schema names, table or collection names, column names only after sensitive-name review, engine, version, endpoint host, port, role names, grant names, and aggregate counts.
   - Redact or classify column names that imply personal, payment, health, authentication, or regulated data.
6. **Initial mock/sample data format**

   ```yaml
   collector: database_metadata
   source:
     provider: aws-rds
     instance: payments-prod
   nodes:
     - type: Database
       id: database:postgres:payments-prod:payments
       engine: postgres
       database_name: payments
     - type: Role
       id: role:database:payments-prod:payments_rw
       name: payments_rw
     - type: Port
       id: port:tcp:5432
       protocol: tcp
       number: 5432
   edges:
     - type: HAS_ROLE
       from: serviceaccount:payments-api
       to: role:database:payments-prod:payments_rw
     - type: GRANTS
       from: role:database:payments-prod:payments_rw
       to: database:postgres:payments-prod:payments
   redactions:
     - source_ref: information_schema.columns.payments.customer_email
       reason: sensitive column classification stored without sample values
   ```

## Broker Metadata Collector

The broker metadata collector reads messaging platform metadata to model brokers, topics, queues, exchanges, subscriptions, consumer groups, producers, consumers, and access policy relationships.

1. **Inputs**
   - Kafka, RabbitMQ, NATS, ActiveMQ, SQS, SNS, Pub/Sub, EventBridge, Kinesis, Redis streams, or cloud event hub metadata; broker clusters; topics; queues; exchanges; routing keys; subscriptions; consumer groups; ACLs; IAM policies; tags; partitions; retention settings; and aggregate throughput or lag metrics.
2. **Output node types**
   - `Broker`, `Topic`, `Queue`, `Service`, `ServiceAccount`, `Role`, `Permission`, `User`, `Group`, `Port`, `IPAddress`, and `Host`.
3. **Output edge types**
   - `CONTAINS`, `PUBLISHES_TO`, `CONSUMES_FROM`, `READS_FROM`, `WRITES_TO`, `CAN_ACCESS`, `HAS_ROLE`, `GRANTS`, `CONNECTS_TO`, and `OBSERVED_CONNECTS_TO` for approved aggregate producer or consumer evidence.
4. **Required credentials**
   - Read-only broker metadata credentials, cloud inventory role, or exported broker configuration.
   - Optional read-only metrics credentials for aggregate consumer lag and throughput.
   - No permission to consume message payloads is required.
5. **Sensitive data handling rules**
   - Do not persist message payloads, headers containing secrets, credentials, SASL passwords, API keys, private certificates, or per-message user data.
   - Store broker names, topic and queue names, subscription names, consumer group IDs, ACL principal names, retention settings, partition counts, routing metadata, and aggregate metrics.
   - Redact topic, queue, or consumer group names if they include sensitive tenant, personal, or regulated identifiers.
6. **Initial mock/sample data format**

   ```yaml
   collector: broker_metadata
   source:
     provider: kafka
     cluster: kafka-prod
   nodes:
     - type: Broker
       id: broker:kafka-prod
       provider: kafka
     - type: Topic
       id: topic:kafka-prod:payments.events
       name: payments.events
     - type: Service
       id: service:payments-api
   edges:
     - type: CONTAINS
       from: broker:kafka-prod
       to: topic:kafka-prod:payments.events
     - type: PUBLISHES_TO
       from: service:payments-api
       to: topic:kafka-prod:payments.events
   redactions: []
   ```

## Nmap/Imported Scan Collector

The Nmap/imported scan collector imports approved network scan outputs and third-party discovery results to model hosts, IP addresses, subnets, open ports, exposed services, and coarse network reachability evidence.

1. **Inputs**
   - Nmap XML or JSON exports, Masscan or other sanctioned scanner exports, CMDB network inventory, asset discovery CSV files, scan scope metadata, scan timestamps, hostnames, IP addresses, CIDRs, protocols, open ports, service banners after redaction, OS guesses, tags, and scan confidence.
2. **Output node types**
   - `Host`, `IPAddress`, `Subnet`, `Port`, `Service`, `API`, `Database`, `Broker`, `Firewall`, `FirewallPolicy`, and `K8sService` when scan targets reconcile to known graph entities.
3. **Output edge types**
   - `CONTAINS`, `EXPOSES`, `ROUTES_TO`, `CONNECTS_TO`, `OBSERVED_CONNECTS_TO`, `ALLOWS`, and `DEPLOYS_TO` when scan evidence maps to deployed services or network policy.
4. **Required credentials**
   - No live credentials are required for file import.
   - If the collector orchestrates scans later, it requires explicit scan authorization metadata and scanner execution credentials, but the initial collector should accept imported files only.
5. **Sensitive data handling rules**
   - Import only scans that are explicitly authorized for the environment and scope.
   - Do not store raw service banners if they contain host keys, certificates with sensitive subject data, internal usernames, tokens, or application-specific secrets.
   - Store normalized protocol, port, service name, product family, coarse version when safe, scan timestamp, scope, and confidence.
   - Keep raw scan files outside graph storage unless they have been sanitized and approved.
6. **Initial mock/sample data format**

   ```yaml
   collector: nmap_imported_scan
   source:
     scan_id: scan-2026-05-30-prod-edge
     format: nmap-xml
     scope: 10.20.0.0/24
   nodes:
     - type: Host
       id: host:10.20.0.15
       hostname: api-01.internal
     - type: IPAddress
       id: ip:10.20.0.15
       address: 10.20.0.15
     - type: Port
       id: port:tcp:443
       protocol: tcp
       number: 443
     - type: API
       id: api:unknown:10.20.0.15:443
       scheme: https
   edges:
     - type: EXPOSES
       from: host:10.20.0.15
       to: port:tcp:443
     - type: EXPOSES
       from: host:10.20.0.15
       to: api:unknown:10.20.0.15:443
   redactions:
     - source_ref: ports/443/servicefp
       reason: raw banner omitted until sanitized
   ```
