# M1 Project Foundation Task Plan

## Scope

Milestone M1 establishes the first runnable project foundation for Dust Graph while staying aligned with `docs/BLUEPRINT.md`. The milestone should create the minimal repository structure, interfaces, and examples needed to begin implementing a backend-neutral graph workspace without committing to production infrastructure.

M1 work is limited to foundational scaffolding and early contracts:

- Select the initial language/runtime and record the rationale.
- Create package and tooling files that make the repository runnable for future tasks.
- Define graph-core model types for nodes, edges, identifiers, metadata, and validation boundaries.
- Introduce a graph adapter interface that keeps storage backends replaceable.
- Keep Kuzu as the next adapter after the in-memory adapter contract works.
- Add a CLI skeleton for future import, validation, and query commands.
- Establish a sample fixture format for small graph examples.
- Design one sample import command and one sample query.
- Document how future tasks should keep task-plan files current.

## Task Breakdown

| # | Task | Status | Acceptance Notes |
| --- | --- | --- | --- |
| 1 | Choose language/runtime. | `done` | Python 3.11+ selected in `pyproject.toml` and `README.md`; Typer, Pydantic, YAML fixtures, and an adapter-first storage path are documented. |
| 2 | Add package/tooling files. | `done` | Added `pyproject.toml` with package metadata, console script, runtime dependencies, pytest configuration, and dev test dependency. |
| 3 | Create graph-core model definitions. | `done` | Added Pydantic models for source evidence, graph metadata, nodes, edges, and importable graph fixtures in `src/dust_graph/models.py`. |
| 4 | Create graph adapter interface. | `done` | Added `GraphAdapter` protocol with `upsert_node`, `upsert_edge`, `bulk_import`, and `query` in `src/dust_graph/adapter.py`. |
| 5 | Create Kuzu adapter skeleton. | `pending` | Deferred intentionally: the current runnable foundation stabilizes the in-memory adapter first; Kuzu remains the next adapter after this contract is exercised. |
| 6 | Create CLI skeleton. | `done` | Added the `dust-graph` Typer entry point with `validate-fixture` and `import-fixture` commands in `src/dust_graph/cli.py`. |
| 7 | Add sample fixture format. | `done` | Added `fixtures/sample_graph.yaml`, a YAML fixture with graph metadata, nodes, edges, properties, and evidence. |
| 8 | Add one sample import command design. | `done` | Implemented `dust-graph import-fixture fixtures/sample_graph.yaml`, which loads a fixture into the in-memory adapter and reports imported counts. |
| 9 | Add one sample query design. | `done` | Added deterministic in-memory named queries: `nodes`, `edges`, and `neighbors`; tests cover the `nodes` query result shape. |
| 10 | Add documentation for how future tasks should update task-plan files. | `done` | This plan keeps the task-plan update guidance below and now includes concrete evidence notes when tasks are marked `done`. |

## Status Table

| State | Meaning | M1 Usage |
| --- | --- | --- |
| `pending` | Work is planned but has not started. | Use for planned work that has not started, including intentionally deferred follow-up tasks. |
| `in_progress` | Work has started and is not complete. | Use for the single active implementation slice whenever possible. |
| `done` | Work is complete and has supporting evidence. | Use only after code, docs, fixtures, and checks for the task are complete. |

## Future Task-Plan Update Guidance

Future tasks should update task-plan files as part of the same change that performs the work:

- Move a task from `pending` to `in_progress` when implementation starts.
- Move a task to `done` only when the implementation, documentation, fixtures, and relevant checks for that task are complete.
- Add short evidence notes or links to changed files when marking a task `done`.
- Add newly discovered work as a new `pending` task instead of silently expanding an existing task.
- Keep milestone boundaries aligned with `docs/BLUEPRINT.md`; update the blueprint first if the work expands beyond the milestone scope.

## Next Adapter Note

Kuzu should be introduced after the in-memory adapter has enough exercised behavior to define a stable persistence contract. The first Kuzu task should implement the existing `GraphAdapter` protocol rather than changing callers to depend on Kuzu-specific APIs.

## Out of Scope

The following work should not be included in M1 unless `docs/BLUEPRINT.md` is updated first:

- Production-ready graph database integration.
- Full Kuzu query execution or persistence behavior.
- Comprehensive schema validation and migration tooling.
- CI/CD pipeline setup beyond minimal local checks.
- Runtime services, deployments, or operations modeling.
- Expanded graph domains beyond the initial planning, documentation, and decision foundation.
- Feature-complete CLI workflows or user-facing applications.

## Milestone Boundary Rule

Implementation must not expand beyond the M1 scope without first updating `docs/BLUEPRINT.md`. If a task requires broader domains, deeper backend behavior, production operations, or non-foundational features, pause implementation and update the blueprint before continuing.
