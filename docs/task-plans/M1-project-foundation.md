# M1 Project Foundation Task Plan

## Scope

Milestone M1 establishes the first runnable project foundation for Dust Graph while staying aligned with `docs/BLUEPRINT.md`. The milestone should create the minimal repository structure, interfaces, and examples needed to begin implementing a backend-neutral graph workspace without committing to production infrastructure.

M1 work is limited to foundational scaffolding and early contracts:

- Select the initial language/runtime and record the rationale.
- Create package and tooling files that make the repository runnable for future tasks.
- Define graph-core model types for nodes, edges, identifiers, metadata, and validation boundaries.
- Introduce a graph adapter interface that keeps storage backends replaceable.
- Add a Kuzu adapter skeleton without requiring full backend behavior.
- Add a CLI skeleton for future import, validation, and query commands.
- Establish a sample fixture format for small graph examples.
- Design one sample import command and one sample query.
- Document how future tasks should keep task-plan files current.

## Task Breakdown

| # | Task | Status | Acceptance Notes |
| --- | --- | --- | --- |
| 1 | Choose language/runtime. | `pending` | Record the selected language/runtime, version expectations, and rationale in the repository docs or package metadata. |
| 2 | Add package/tooling files. | `pending` | Add the minimal package manager, formatter/linter/test, and local run scripts needed for later M1 implementation tasks. |
| 3 | Create graph-core model definitions. | `pending` | Define foundational graph model shapes for nodes, edges, IDs, labels/types, properties, and metadata without binding them to a storage backend. |
| 4 | Create graph adapter interface. | `pending` | Define the backend-neutral interface for importing, querying, and basic lifecycle interactions with a graph store. |
| 5 | Create Kuzu adapter skeleton. | `pending` | Add a Kuzu-specific adapter placeholder that implements or conforms to the graph adapter interface without requiring complete persistence behavior. |
| 6 | Create CLI skeleton. | `pending` | Add a minimal command-line entry point and command grouping for future import, validation, and query workflows. |
| 7 | Add sample fixture format. | `pending` | Document and add a small sample fixture structure that can represent graph nodes and edges for local examples. |
| 8 | Add one sample import command design. | `pending` | Specify one import command shape, expected arguments, and intended behavior for loading a sample fixture. |
| 9 | Add one sample query design. | `pending` | Specify one saved or example query, including the graph question it answers and the expected result shape. |
| 10 | Add documentation for how future tasks should update task-plan files. | `pending` | Document when task statuses should change, where evidence should be noted, and how newly discovered work should be added to milestone task plans. |

## Status Table

| State | Meaning | M1 Usage |
| --- | --- | --- |
| `pending` | Work is planned but has not started. | Initial state for every M1 task in this plan. |
| `in_progress` | Work has started and is not complete. | Use for the single active implementation slice whenever possible. |
| `done` | Work is complete and has supporting evidence. | Use only after code, docs, fixtures, and checks for the task are complete. |

## Future Task-Plan Update Guidance

Future tasks should update task-plan files as part of the same change that performs the work:

- Move a task from `pending` to `in_progress` when implementation starts.
- Move a task to `done` only when the implementation, documentation, fixtures, and relevant checks for that task are complete.
- Add short evidence notes or links to changed files when marking a task `done`.
- Add newly discovered work as a new `pending` task instead of silently expanding an existing task.
- Keep milestone boundaries aligned with `docs/BLUEPRINT.md`; update the blueprint first if the work expands beyond the milestone scope.

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
