# M2 Schema Validation Task Plan

## Goal

Add a reusable schema validation path for `GraphFixture` data so fixtures and collector-produced graph output can be checked against `schemas/graph.schema.yaml` before import or downstream processing.

## Scope

- Load the canonical schema from `schemas/graph.schema.yaml` by default.
- Validate every fixture node type against `node_types` in the schema.
- Validate every fixture edge type against `edge_types` in the schema.
- Validate common metadata fields defined by the schema, including required fields and supported scalar formats/ranges.
- Expose validation through fixture helpers and a `dust-graph validate-schema <path>` CLI command.
- Cover the repository collector path by validating its generated `GraphFixture` output with the same validator.

## Implementation Steps

1. Add `src/dust_graph/schema.py` with schema loading, validation error types, and a `validate_graph_fixture_schema` function.
2. Update fixture loading helpers so callers can opt into schema validation without duplicating YAML parsing.
3. Add a Typer CLI command named `validate-schema` that loads a fixture and reports schema validation success.
4. Adjust the graph schema only where needed to align common metadata definitions with the current graph model.
5. Add tests for valid fixtures, unknown node types, unknown edge types, missing required common fields, and repository collector output.
6. Run the focused test suite and commit the completed changes.

## Validation Notes

- The validator should accept an already constructed `GraphFixture` to keep collector output and loaded fixtures on the same path.
- Validation errors should be deterministic and human-readable for CLI use.
- Required common metadata fields should be enforced where a schema entry declares `required: true`.
