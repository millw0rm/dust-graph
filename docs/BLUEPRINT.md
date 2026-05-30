# Dust Graph Blueprint

## 1. Project Goal

Dust Graph is a durable, graph-centered knowledge and modeling workspace for representing projects, systems, plans, decisions, artifacts, and their relationships over time. The project should make it easy to capture structured facts, connect them into an inspectable graph, query those relationships, and evolve the model without losing historical context.

The initial goal is to establish a small, reliable foundation that can support iterative development: define the core domains, choose a graph backend strategy that can start simple and scale later, and keep each implementation step aligned with this blueprint.

## 2. Major Modeling Domains

The graph model should begin with a small set of high-value domains and expand only when concrete workflows require it.

### Planning and Execution

- Projects, goals, milestones, tasks, and sessions.
- Dependencies between tasks, blockers, and prerequisites.
- Status transitions, ownership, and completion evidence.

### Knowledge and Documentation

- Documents, notes, references, summaries, and source material.
- Links between claims, supporting evidence, and derived conclusions.
- Versioned documentation artifacts and the decisions that changed them.

### Code and Repository Structure

- Repositories, packages, modules, files, symbols, and build targets.
- Relationships between code entities, tests, documentation, and generated artifacts.
- Change sets, pull requests, reviews, and release notes.

### Decisions and Rationale

- Architecture decisions, alternatives, tradeoffs, constraints, and outcomes.
- Links from decisions to the tasks, files, issues, and milestones they affect.
- Supersession relationships when a decision is revised or replaced.

### People, Roles, and Collaboration

- Contributors, maintainers, reviewers, stakeholders, and agents.
- Responsibility relationships such as ownership, review assignment, and approval.
- Collaboration events that provide context for why work changed direction.

### Runtime and Operations

- Services, environments, deployments, incidents, checks, and observability signals.
- Relationships between runtime behavior, code changes, and operational decisions.
- Health, reliability, and support workflows once the project has runnable systems.

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

### M2: Initial Graph Vocabulary

- Define the first node and edge vocabulary for the core planning, documentation, and decision domains.
- Add minimal examples that show how projects, tasks, documents, and decisions connect.
- Document naming, identity, metadata, and relationship conventions.

### M3: Schema and Fixture Validation

- Add machine-checkable schemas for the initial graph vocabulary.
- Add fixtures that exercise expected graph shapes and invalid cases.
- Provide a validation command that can run locally and in CI.

### M4: Query and Traversal Prototype

- Implement a small query or traversal layer over the file-backed fixtures.
- Support essential questions such as dependency lookup, related decisions, and milestone progress.
- Keep the implementation backend-neutral.

### M5: Repository and Code Modeling

- Extend the model to represent repositories, files, modules, tests, and change sets.
- Connect code artifacts to tasks, decisions, documentation, and milestones.
- Add examples that demonstrate traceability from goal to implementation evidence.

### M6: Session Workflow Integration

- Add a repeatable workflow for turning blueprint milestones into session plans, task slices, and completion notes.
- Capture session outputs as graph-compatible artifacts.
- Ensure the workflow can identify when the blueprint itself needs to change.

### M7: Backend Evaluation and Adapter Boundary

- Evaluate whether the file-backed approach is still sufficient for current workloads.
- Define the adapter boundary for any embedded, service-backed, or hosted graph database.
- Prototype at least one backend adapter if justified by the milestone evidence.

### M8: Production Readiness and Operations

- Add operational modeling for services, environments, checks, releases, and incidents if the project has runnable systems.
- Harden validation, migration, import/export, and backup workflows.
- Document production readiness criteria and long-term maintenance expectations.

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
