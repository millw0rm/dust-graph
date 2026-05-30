# M1 Kuzu Adapter Implementation Task Plan

## Source Alignment

This task plan is derived from `docs/BLUEPRINT.md` and `docs/task-plans/M1-project-foundation.md`.
It follows the blueprint's staged backend strategy by keeping Kuzu behind the stable
`GraphAdapter` protocol and limiting this slice to a skeleton adapter rather than a
production graph backend.

## Scope

Implement the first Kuzu adapter seam for M1 without making Kuzu part of the default
runtime or test dependency set.

In scope:

- Add a `KuzuGraphAdapter` class that implements the existing graph adapter contract.
- Keep `kuzu` optional and report a clear installation message when it is missing.
- Reuse the same public adapter methods as the in-memory adapter: `upsert_node`,
  `upsert_edge`, `bulk_import`, and `query`.
- Add default-suite tests for importability and missing optional-dependency behavior.
- Add a Kuzu smoke test that only runs when `kuzu` is installed.
- Update the M1 project-foundation task plan when complete.

Out of scope:

- Production-ready Kuzu schema design.
- Comprehensive Kuzu migrations or domain-specific labels.
- Replacing the in-memory adapter in CLI or default workflows.

## Task Breakdown

| # | Task | Status | Acceptance Notes |
| --- | --- | --- | --- |
| 1 | Create this implementation task plan. | `done` | Plan is recorded before implementation under `docs/task-plans/`. |
| 2 | Add Kuzu adapter skeleton. | `done` | `KuzuGraphAdapter` implements the current `GraphAdapter` protocol methods in `src/dust_graph/adapters/kuzu.py`. |
| 3 | Preserve optional dependency behavior. | `done` | Importing the adapter module does not require `kuzu`; instantiation raises a clear `KuzuOptionalDependencyError` if the package is missing. |
| 4 | Add Kuzu adapter tests. | `done` | Tests cover importability, missing dependency messaging, and a skipped-unless-installed smoke path. |
| 5 | Update M1 foundation status. | `done` | The Kuzu adapter task in `M1-project-foundation.md` is marked complete with evidence notes. |
