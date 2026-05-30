# M1 Project Foundation Task Plan

## Scope

Milestone M1 establishes the first runnable project foundation for Dust Graph while staying aligned with `docs/BLUEPRINT.md`. The milestone should create the minimal repository structure, interfaces, and examples needed to begin implementing a backend-neutral graph workspace without committing to production infrastructure.

M1 work is limited to foundational scaffolding and early contracts:

- Create the base package layout for application/library code.
- Define the canonical graph schema shape for initial nodes, edges, and metadata.
- Introduce a graph adapter interface that keeps storage backends replaceable.
- Add a Kuzu adapter placeholder without requiring full backend behavior.
- Add a CLI skeleton for future import, validation, and query commands.
- Establish a sample fixture import path for small graph examples.
- Add a basic saved-query structure for reusable graph questions.

## Deliverables Checklist

- [ ] Create base package layout.
- [ ] Define canonical graph schema.
- [ ] Add graph adapter interface.
- [ ] Add Kuzu adapter placeholder.
- [ ] Add CLI skeleton.
- [ ] Add sample fixture import path.
- [ ] Add basic saved-query structure.

## Out of Scope

The following work should not be included in M1 unless `docs/BLUEPRINT.md` is updated first:

- Production-ready graph database integration.
- Full Kuzu query execution or persistence behavior.
- Comprehensive schema validation and migration tooling.
- CI/CD pipeline setup beyond minimal local checks.
- Runtime services, deployments, or operations modeling.
- Expanded graph domains beyond the initial planning, documentation, and decision foundation.
- Feature-complete CLI workflows or user-facing applications.

## Status Table

| State | Meaning | M1 Usage |
| --- | --- | --- |
| `pending` | Work is planned but has not started. | Default state for deliverables not yet touched. |
| `in_progress` | Work has started and is not complete. | Use for the single active implementation slice whenever possible. |
| `done` | Work is complete and has supporting evidence. | Use only after code, docs, fixtures, and checks for the deliverable are complete. |

## Milestone Boundary Rule

Implementation must not expand beyond the M1 scope without first updating `docs/BLUEPRINT.md`. If a task requires broader domains, deeper backend behavior, production operations, or non-foundational features, pause implementation and update the blueprint before continuing.
