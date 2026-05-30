# M1 Graph Adapter Contract Task Plan

## Scope

This M1 task plan specifies the backend-neutral graph adapter contract before implementation. The contract should let Dust Graph start with a Kuzu adapter while preserving a clear path to a later Neo4j adapter or another graph backend. The adapter boundary must protect the stable Dust Graph domain model from backend-specific query languages, storage layouts, transactions, and driver APIs.

This plan is documentation-only unless a later session explicitly implements the contract. Implementation work should use this document as the source of truth for the first adapter interface, fixtures, and conformance tests.

## Design Goals

- Keep graph domain objects stable and repository-owned.
- Support Kuzu as the first concrete implementation without leaking Kuzu concepts into callers.
- Allow a Neo4j implementation later without changing application/domain code.
- Make imports idempotent and safe to retry.
- Track source-system provenance and ingestion metadata for every imported batch.
- Provide enough query and traversal capability for early workflows while leaving backend-specific optimizations behind the adapter.
- Keep deletion, expiration, and source refresh behavior explicit so stale data does not silently remain authoritative.

## Non-Goals

- Do not design a complete ORM or expose arbitrary backend drivers to callers.
- Do not require Cypher, Kuzu SQL, or any vendor query language in the domain layer.
- Do not commit to production deployment, clustering, backups, or hosted service operations in M1.
- Do not define every future node and edge type; the adapter should operate on the canonical schema once defined.
- Do not require a full migration framework before the first implementation.

## Stable Domain Model

The adapter should exchange repository-owned data structures, not backend-native records.

### `GraphNode`

A node represents a durable entity in the Dust Graph domain.

Required fields:

- `id`: stable repository-owned identifier, unique within a node kind.
- `kind`: canonical node kind, such as `Project`, `Task`, `Document`, or `Decision`.
- `properties`: JSON-compatible scalar, list, and object values validated by the canonical schema.
- `source`: source reference that identifies where this assertion came from.
- `observed_at`: timestamp when the source data was observed.

Optional fields:

- `labels`: backend-neutral tags or classifications.
- `valid_from`: timestamp for when the assertion becomes valid.
- `valid_until`: timestamp for expiration or historical validity.
- `confidence`: optional normalized confidence value for derived data.

### `GraphEdge`

An edge represents a typed relationship between two nodes.

Required fields:

- `id`: stable repository-owned identifier or deterministic synthetic identifier.
- `kind`: canonical edge kind, such as `DEPENDS_ON`, `DOCUMENTS`, `SUPPORTS`, or `SUPERSEDES`.
- `from`: node reference containing `kind` and `id`.
- `to`: node reference containing `kind` and `id`.
- `properties`: JSON-compatible relationship properties validated by the canonical schema.
- `source`: source reference that identifies where this assertion came from.
- `observed_at`: timestamp when the source relationship was observed.

Optional fields:

- `valid_from`: timestamp for when the relationship becomes valid.
- `valid_until`: timestamp for expiration or historical validity.
- `confidence`: optional normalized confidence value for derived relationships.

### `SourceRef`

A source reference identifies ownership and provenance for imported data.

Required fields:

- `system`: source system name, such as `fixture`, `repository`, `manual`, or `ingestion-job`.
- `external_id`: source-local identifier for the entity, assertion, file, or batch item.

Optional fields:

- `uri`: durable source URI when available.
- `version`: source revision, commit SHA, document version, or export version.
- `checksum`: content checksum used for idempotency and stale-data detection.

### `IngestionMetadata`

Ingestion metadata records what happened during an import or refresh operation.

Required fields:

- `run_id`: unique ingestion run identifier.
- `source`: source reference for the import batch.
- `started_at`: run start timestamp.
- `finished_at`: run completion timestamp.
- `status`: `succeeded`, `failed`, or `partial`.
- `nodes_seen`: count of source nodes processed.
- `edges_seen`: count of source edges processed.
- `nodes_upserted`: count of nodes inserted or updated.
- `edges_upserted`: count of edges inserted or updated.

Optional fields:

- `nodes_deleted`: count of nodes deleted during stale cleanup.
- `edges_deleted`: count of edges deleted during stale cleanup.
- `nodes_expired`: count of nodes marked expired during stale cleanup.
- `edges_expired`: count of edges marked expired during stale cleanup.
- `warnings`: non-fatal validation or import warnings.
- `errors`: fatal or item-level error summaries.
- `parameters`: backend-neutral import parameters, such as dry-run mode or stale-data policy.

## Adapter Contract

The adapter should expose a small interface centered on domain operations. Method names below are descriptive; implementation language may adjust naming while preserving semantics.

### 1. Upsert Nodes

`upsert_nodes(nodes, options) -> UpsertResult`

Semantics:

- Insert missing nodes and update existing nodes matched by `(kind, id)`.
- Preserve stable identity across backend implementations.
- Validate node shape before persistence or return structured validation errors.
- Treat repeated calls with the same node payload as idempotent.
- Update provenance and observation timestamps as part of the node assertion.

Required options:

- `run_id`: ingestion run responsible for the operation.

Optional options:

- `dry_run`: validate and plan without persisting.
- `merge_strategy`: `replace_properties` by default; later implementations may add schema-approved merge strategies.

### 2. Upsert Edges

`upsert_edges(edges, options) -> UpsertResult`

Semantics:

- Insert missing edges and update existing edges matched by stable edge `id`.
- Validate that referenced endpoint identities are present or can be created according to explicit options.
- Preserve edge direction and kind exactly as provided by the domain model.
- Treat repeated calls with the same edge payload as idempotent.
- Do not expose backend-specific relationship identifiers to callers.

Required options:

- `run_id`: ingestion run responsible for the operation.

Optional options:

- `dry_run`: validate and plan without persisting.
- `missing_endpoint_policy`: `error` by default; future values may include `create_stub` for schema-approved placeholder nodes.

### 3. Bulk Import

`bulk_import(batch, options) -> ImportResult`

Semantics:

- Accept a batch containing nodes, edges, source information, and ingestion parameters.
- Execute validation before mutation when feasible.
- Import nodes before edges unless the implementation can guarantee equivalent correctness.
- Provide all-or-nothing behavior by default for a single batch when supported by the backend.
- Return counts, warnings, and errors in backend-neutral result objects.
- Record ingestion metadata for every attempted run, including failed and dry-run attempts when practical.

Required options:

- `run_id`: caller-provided or adapter-generated unique run identifier.
- `source`: source reference for the batch.

Optional options:

- `dry_run`: validate and produce a plan without persisting domain graph mutations.
- `transaction_mode`: `atomic` by default; implementations that cannot guarantee atomicity must report that capability.
- `stale_policy`: optional cleanup policy to apply after successful import.

### 4. Run Saved Queries

`run_saved_query(query_id, parameters, options) -> QueryResult`

Semantics:

- Execute only repository-defined saved queries identified by stable `query_id`.
- Accept backend-neutral parameters validated against the saved query definition.
- Return backend-neutral result rows, nodes, edges, paths, or subgraphs as declared by the query definition.
- Keep backend query text in adapter-specific query registries or translation layers.
- Avoid accepting raw backend query strings from application code.

Required inputs:

- `query_id`: stable identifier for a saved query.
- `parameters`: JSON-compatible parameter object.

Optional options:

- `limit`: maximum result count when supported by the saved query.
- `timeout_ms`: execution timeout hint.
- `as_of`: optional timestamp for historical queries when supported.

### 5. Return Subgraphs Around an Entity

`get_subgraph(entity_ref, options) -> SubgraphResult`

Semantics:

- Return nodes and edges around a starting entity reference.
- Support bounded traversal so callers cannot accidentally request unbounded graph expansion.
- Respect canonical edge direction while allowing explicit inbound, outbound, or both-direction traversal options.
- Return only domain model objects and traversal metadata, not backend path objects.

Required inputs:

- `entity_ref`: `{ kind, id }` reference to the starting node.

Required options:

- `depth`: maximum traversal depth, with implementation-defined safe upper bounds.

Optional options:

- `edge_kinds`: allow-list of relationship kinds.
- `node_kinds`: allow-list of node kinds.
- `direction`: `outbound`, `inbound`, or `both`.
- `limit`: maximum number of nodes or paths.
- `as_of`: optional timestamp for historical subgraph views when supported.

### 6. Delete or Expire Stale Source Data

`cleanup_source_data(source, policy, options) -> CleanupResult`

Semantics:

- Identify data previously imported from a source that is no longer present, no longer valid, or explicitly removed.
- Support hard deletion for disposable derived data.
- Support expiration for historical data that should remain queryable with validity windows.
- Never remove data from other sources unless the policy explicitly allows it and the adapter can prove ownership.
- Return affected node and edge identities with counts and warnings.

Required inputs:

- `source`: source reference or source selector.
- `policy`: cleanup behavior.

Policy values:

- `expire_missing`: set `valid_until` or equivalent expiration metadata for missing source assertions.
- `delete_missing`: physically remove missing source assertions when safe.
- `delete_source`: remove all data owned by the selected source when safe.

Optional options:

- `run_id`: ingestion run responsible for the cleanup.
- `observed_before`: timestamp cutoff for stale observations.
- `dry_run`: report what would be affected without mutating the graph.

### 7. Record Ingestion Metadata

`record_ingestion_metadata(metadata) -> MetadataResult`

Semantics:

- Persist ingestion metadata independently from graph entity upserts.
- Record both successful and failed attempts when feasible.
- Make ingestion runs queryable by `run_id`, source, status, and time range.
- Do not require domain entities to be inserted successfully before metadata can be recorded.

Related read methods:

- `get_ingestion_run(run_id) -> IngestionMetadata | None`
- `list_ingestion_runs(filter, pagination) -> IngestionRunPage`

## Result and Error Shape

All adapter methods should return structured, backend-neutral results.

Common result fields:

- `ok`: boolean success indicator.
- `run_id`: ingestion run associated with the operation when applicable.
- `counts`: inserted, updated, skipped, deleted, expired, and failed counts as applicable.
- `warnings`: non-fatal warnings.
- `errors`: structured errors with code, message, and optional item reference.
- `capabilities`: optional capability notes when behavior is degraded or emulated.

Common error codes:

- `validation_failed`
- `node_not_found`
- `edge_endpoint_missing`
- `saved_query_not_found`
- `unsupported_capability`
- `transaction_failed`
- `backend_unavailable`
- `stale_cleanup_unsafe`

## Backend Capability Contract

Each adapter implementation should expose a capability descriptor so callers and tests can understand backend-specific limits without depending on backend APIs.

Suggested fields:

- `backend_name`: for example `kuzu` or `neo4j`.
- `supports_transactions`: whether atomic batch mutation is supported.
- `supports_bulk_import`: whether optimized bulk import is available.
- `supports_expiration`: whether validity-window queries are natively supported or emulated.
- `supports_saved_queries`: whether saved query execution is implemented.
- `max_recommended_subgraph_depth`: safe default traversal depth.
- `property_value_limits`: backend-specific constraints translated into neutral limits.

## Kuzu First Implementation Notes

The first Kuzu implementation should be treated as an adapter behind the contract, not as the contract itself.

Guidelines:

- Keep Kuzu table names, relationship tables, and query syntax inside the Kuzu adapter module.
- Translate `GraphNode`, `GraphEdge`, and metadata objects into Kuzu records at the boundary.
- Store enough source and ingestion fields to support idempotency and stale cleanup.
- Prefer deterministic edge identifiers even if Kuzu can address relationships internally.
- Implement saved queries through repository-defined query definitions mapped to Kuzu query text.
- Report unsupported or emulated capabilities explicitly through the capability descriptor.

## Neo4j Later Implementation Notes

The later Neo4j implementation should be able to satisfy the same contract without changing application callers.

Guidelines:

- Map canonical node `kind` to labels or properties without requiring callers to know label strategy.
- Map canonical edge `kind` to relationship types or properties inside the Neo4j adapter.
- Keep Cypher query text inside the Neo4j adapter or saved-query translation layer.
- Preserve the same idempotency rules for `(kind, id)` nodes and stable edge `id` values.
- Match Kuzu-visible semantics for bulk import results, saved query results, cleanup behavior, and ingestion metadata.

## Conformance Expectations

Every backend adapter should pass the same adapter-level tests once implementation begins.

Minimum conformance scenarios:

- Upserting the same node twice is idempotent.
- Upserting the same edge twice is idempotent.
- Upserting an edge with a missing endpoint fails by default.
- Bulk import inserts nodes before edges and returns accurate counts.
- Saved query execution rejects unknown query identifiers.
- Subgraph retrieval respects depth, direction, node-kind filters, and edge-kind filters.
- Cleanup dry runs report affected data without mutating persisted records.
- Expiration sets validity metadata without deleting historical records.
- Ingestion metadata can be recorded for successful and failed runs.
- Capability descriptors are available for every adapter implementation.

## Deliverables Checklist

- [ ] Define repository-owned domain data structures for nodes, edges, source references, and ingestion metadata.
- [ ] Define the graph adapter interface around the seven required capabilities.
- [ ] Define backend-neutral result and error objects.
- [ ] Add a capability descriptor for adapter implementations.
- [ ] Add a Kuzu adapter placeholder that implements or explicitly stubs the contract.
- [ ] Add saved-query definition structure and validation rules.
- [ ] Add conformance tests that can run against Kuzu and future adapters.
- [ ] Add fixtures covering idempotent upsert, bulk import, subgraph traversal, stale cleanup, and ingestion metadata.

## Acceptance Criteria

The graph adapter contract is ready for implementation when:

- Application code can depend only on repository-owned domain objects and adapter methods.
- Kuzu-specific details are limited to the Kuzu adapter implementation plan.
- Neo4j can be added later by implementing the same contract.
- The seven required capabilities are represented in method semantics and result shapes.
- Stale-data cleanup and ingestion metadata are explicit parts of the adapter boundary.
- Conformance expectations are clear enough to drive shared tests for multiple backends.
