# Dust Graph Blueprint

## 1. Project Goal

Dust Graph is an infrastructure, API, repository, access, and runtime relationship graph for understanding how software systems are defined, connected, secured, and used. It should make it easy to ingest structured facts from repositories, network and perimeter systems, Kubernetes, API gateways, data platforms, identity providers, and runtime evidence, then connect those facts into an inspectable graph that answers ownership, dependency, exposure, access, and traffic questions.

The primary product goal is to provide a reliable graph foundation that links intended configuration with observed runtime behavior: what repositories and manifests define a system, what network paths and API routes expose it, what identities can access it, what data systems it uses, and what evidence confirms those relationships. The initial implementation should stay small and reviewable while preserving a path to production-scale import, query, and validation workflows.

## 2. Major Modeling Domains

The graph model should begin with infrastructure and runtime domains that expose concrete relationships between source-defined intent, deployed resources, access boundaries, and observed behavior. Expand the model only when concrete workflows require it.

### Repository Context

- Repositories, services, packages, owners, teams, and ownership metadata.
- OpenAPI specifications, Helm charts, Kubernetes manifests, Terraform modules, CI/CD files, and other deployable artifacts.
- Relationships from source artifacts to the systems, infrastructure, APIs, and access rules they define or influence.

### Network and Perimeter

- Fortinet and FortiGate assets, VPNs, firewall policies, routes, NAT rules, subnets, IPs, ports, and VMs.
- Allowed, denied, translated, and routed paths between users, workloads, services, data systems, and external networks.
- Perimeter exposure and reachability relationships that connect network intent with runtime observations.

### Kubernetes

- Clusters, namespaces, workloads, pods, services, ingresses, network policies, and service accounts.
- Ownership, deployment, routing, identity, and policy relationships across Kubernetes resources.
- Links from Kubernetes resources back to repository artifacts such as manifests, Helm charts, and CI/CD deployment pipelines.

### API Layer

- APIs, endpoints, methods, OpenAPI specs, gateway routes, consumers, producers, and runtime API calls.
- Relationships between API definitions, gateway configuration, deployed services, identities, and observed calls.
- Versioning, ownership, exposure, and dependency links that help answer who calls what and through which route.

### Data Systems

- Databases, schemas, tables, brokers, topics, queues, and related platform resources.
- Application, service, user, and service-account access to databases, schemas, tables, brokers, topics, and queues.
- Data dependency relationships that connect repository definitions, runtime services, and audit or metadata evidence.

### Identity and Access

- Users, groups, roles, permissions, service accounts, API credentials, and workload identities.
- API access, database access, broker access, Kubernetes RBAC, and infrastructure permissions.
- Effective-access relationships that explain who or what can reach a resource and through which grants, policies, or inherited memberships.

### Runtime Evidence

- Observed connections from Hubble, API gateways, FortiGate logs, database audit logs, and broker metadata.
- Evidence records that confirm, contradict, or enrich source-defined relationships.
- Temporal observations for traffic, access, dependency, and exposure so the graph can distinguish intended configuration from observed behavior.

## 3. Recommended Graph Backend Strategy

Use a staged backend strategy so the repository can move quickly while preserving a path to a production graph database.

### Stage 1: File-Backed Graph Seed

- Start with repository-local, human-readable files for schemas, fixtures, examples, and planning artifacts.
- Prefer formats that are easy to diff and review, such as Markdown for plans and JSON or YAML for graph fixtures.
- Keep the initial data model explicit and small so the shape of nodes, edges, and metadata can stabilize before adding infrastructure.

### Stage 2: Embedded or Lightweight Query Layer

- Add an application-level graph abstraction once the first workflows need validation, traversal, or querying.
- Keep storage concerns behind interfaces so fixtures, tests, and future databases can share the same domain model.
- Use this stage to define invariants, migrations, import/export paths, and test data.

### Stage 3: Production Graph Backend

- Introduce a dedicated graph backend only after the access patterns justify it.
- Evaluate candidates against query expressiveness, local development ergonomics, migration support, hosted options, operational complexity, and integration with the repository's primary language stack.
- Keep file-based import/export as a durable escape hatch even after adopting a database.

### Strategy Principles

- Do not couple domain modeling to a single vendor too early.
- Treat the graph backend as replaceable behind a stable repository-owned interface.
- Optimize first for correctness, inspectability, tests, and easy review.
- Add operational complexity only when milestones require it.

## 4. Initial Repository Layout

The repository should evolve toward the following layout as features are introduced. Directories should be created only when they are needed by a milestone.

```text
.
├── docs/
│   ├── BLUEPRINT.md          # Durable project plan and source for session plans.
│   ├── decisions/            # Architecture decision records and rationale.
│   └── milestones/           # Milestone-specific plans derived from the blueprint.
├── schemas/                  # Graph node, edge, and metadata schemas.
├── fixtures/                 # Small example graphs and test datasets.
├── src/                      # Application or library implementation.
├── tests/                    # Automated tests and validation scenarios.
├── scripts/                  # Developer tooling, import/export, and validation scripts.
└── README.md                 # Repository overview and quickstart.
```

## 5. Milestones

### M1: Durable Planning Foundation

- Create and maintain this blueprint as the canonical planning artifact.
- Define the workflow rule that every coding session derives its smaller plan from this file.
- Establish the first documentation conventions for goals, domains, milestones, and decisions.

### M2: Initial Infrastructure Graph Vocabulary

- Define the first node and edge vocabulary for repositories, services, owners, network resources, Kubernetes resources, APIs, data systems, identities, access grants, and runtime evidence.
- Add minimal examples that show how repository artifacts, deployed resources, access relationships, and observed runtime connections link together.
- Document naming, identity, metadata, provenance, and relationship conventions for infrastructure and access graph data.

### M3: Schema and Fixture Validation

- Add machine-checkable schemas for the initial infrastructure, API, access, and runtime evidence vocabulary.
- Add fixtures that exercise expected graph shapes and invalid cases across repository, network, Kubernetes, API, data, identity, and evidence domains.
- Provide a validation command that can run locally and in CI.

### M4: Query and Traversal Prototype

- Implement a small query or traversal layer over the file-backed fixtures.
- Support essential questions such as service ownership, API exposure, network reachability, effective access, data dependencies, and observed runtime paths.
- Keep the implementation backend-neutral.

### M5: Repository and Configuration Ingestion

- Extend the model and examples to represent repositories, OpenAPI specs, Helm charts, Kubernetes manifests, Terraform, and CI/CD files.
- Connect source-defined configuration to services, APIs, network paths, Kubernetes resources, data systems, and access relationships.
- Add examples that demonstrate traceability from repository artifacts to deployed or intended infrastructure relationships.

### M6: Session Workflow Integration

- Add a repeatable workflow for turning blueprint milestones into session plans, task slices, and completion notes.
- Capture session outputs as graph-compatible artifacts.
- Ensure the workflow can identify when the blueprint itself needs to change.

### M7: Runtime Evidence and Access Correlation

- Add import and fixture patterns for observed connections from Hubble, API gateways, FortiGate logs, database audit logs, and broker metadata.
- Correlate runtime evidence with repository-defined intent, network policy, API routes, data access, and identity grants.
- Identify contradictions, stale definitions, missing owners, unexpected access, and unobserved intended paths.

### M8: Backend Evaluation and Production Readiness

- Evaluate whether the file-backed approach is still sufficient for current infrastructure graph workloads.
- Define the adapter boundary for any embedded, service-backed, or hosted graph database.
- Harden validation, migration, import/export, backup, and operational workflows for production-scale infrastructure, API, access, and runtime evidence data.

## 6. Workflow Rule for Coding Sessions

Every coding session must begin by deriving a smaller, concrete plan from `docs/BLUEPRINT.md` before implementation starts.

The derived plan should:

1. Identify the relevant blueprint milestone or milestones.
2. State the narrow objective for the session.
3. List the smallest useful implementation or documentation steps.
4. Call out files or directories expected to change.
5. Define the checks that will prove the session is complete.
6. Note any blueprint updates discovered during the work.

If a requested change does not fit the current blueprint, the session should update `docs/BLUEPRINT.md` or create a follow-up planning task before adding implementation code. This rule keeps day-to-day work aligned with the durable project plan and prevents ad hoc repository growth.
