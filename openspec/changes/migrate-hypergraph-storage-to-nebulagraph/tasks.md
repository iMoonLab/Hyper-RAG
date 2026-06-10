## 1. Configuration And Schema

- [x] 1.1 Add hypergraph backend configuration with `.hgdb` as the default backend.
- [x] 1.2 Add NebulaGraph connection settings for host, port, credentials, graph space, and per-database mapping.
- [x] 1.3 Define NebulaGraph schema for Entity vertices, Hyperedge vertices, membership edges, and optional reverse membership edges.
- [x] 1.4 Add a schema initialization/check command that verifies required tags, edge types, and indexes exist before migration.
- [x] 1.5 Add explicit backend modes for `hgdb`, `mirror-only`, `dual-read`, and `nebulagraph-serving`.
- [x] 1.6 Define failure policy defaults so `.hgdb` remains serving when NebulaGraph is unavailable, unvalidated, or misconfigured.

## 2. Migration Tooling

- [x] 2.1 Implement a reader that loads existing `hypergraph_chunk_entity_relation.hgdb` data through the current HypergraphDB format.
- [x] 2.2 Generate stable Entity vertex IDs from canonical entity names and database scope.
- [x] 2.3 Generate stable Hyperedge vertex IDs from normalized `id_set` values and database scope.
- [x] 2.4 Upsert Entity vertices while preserving `entity_type`, `description`, `source_id`, and `additional_properties`.
- [x] 2.5 Upsert Hyperedge vertices while preserving `id_set`, `description`, `keywords`, `weight`, `source_id`, and arity.
- [x] 2.6 Upsert membership relationships between each Entity vertex and its Hyperedge vertex.
- [x] 2.7 Make migration repeatable without creating duplicate logical entities or hyperedges.
- [x] 2.8 Add mirror-only migration execution that writes NebulaGraph data while leaving `.hgdb` as the serving backend.

## 3. NebulaGraph Storage Adapter

- [x] 3.1 Add `NebulaHypergraphStorage` implementing the full `BaseHypergraphStorage` interface.
- [x] 3.2 Implement vertex existence, lookup, upsert, removal, count, and listing behavior.
- [x] 3.3 Implement hyperedge existence, lookup, upsert, removal, count, and listing behavior using Hyperedge vertices.
- [x] 3.4 Implement `get_nbr_e_of_vertex`, `get_nbr_v_of_hyperedge`, and `get_nbr_v_of_vertex` with outputs normalized to match `.hgdb` semantics.
- [x] 3.5 Implement `vertex_degree` and `hyperedge_degree` with parity against the current backend.
- [ ] 3.6 Add batching for hot retrieval paths used by `hyper_query`, `hyper_query_lite`, and `graph_query`.
- [x] 3.7 Normalize returned hyperedge tuples, neighbor lists, and entity lists into deterministic ordering before returning to retrieval code.
- [x] 3.8 Ensure degree calculations do not double-count reverse or auxiliary membership edges.

## 4. Integration

- [ ] 4.1 Wire backend selection into `HyperRAG` initialization without changing public query or insert APIs.
- [ ] 4.2 Wire Web UI backend initialization to select `.hgdb` or NebulaGraph per configured database.
- [ ] 4.3 Keep `NanoVectorDBStorage` and text chunk JSON storage unchanged for the initial migration.
- [ ] 4.4 Add diagnostics that expose selected hypergraph backend and NebulaGraph connection status.
- [ ] 4.5 Ensure mirror-only and dual-read modes never serve user-facing query responses from NebulaGraph.
- [ ] 4.6 Verify prompt construction, query routing, vector recall, text chunk lookup, and answer generation remain unchanged.

## 5. Dual-Read Validation

- [ ] 5.1 Add storage parity checks for vertex count, hyperedge count, sampled entity records, sampled hyperedge records, neighbor lookups, and degree values.
- [ ] 5.2 Add retrieval parity checks for fixed question sets across `hyper`, `hyper-lite`, and `graph` modes.
- [ ] 5.3 Compare retrieved entities, hyperedges, and source text units while keeping vector stores unchanged.
- [ ] 5.4 Report failed parity checks with enough detail to identify missing records, changed source IDs, or changed neighbor sets.
- [ ] 5.5 Add context string diff reporting after deterministic normalization.
- [ ] 5.6 Add optional final answer regression scoring when an evaluator is configured.
- [ ] 5.7 Add validation checks for NebulaGraph schema completeness and migration completeness.

## 6. Quality Gate And Rollback

- [ ] 6.1 Define configurable acceptance thresholds for storage parity and retrieval parity.
- [ ] 6.2 Block NebulaGraph serving when parity checks fail.
- [ ] 6.3 Add an opt-in switch to enable NebulaGraph serving only after validation passes.
- [ ] 6.4 Verify rollback by switching configuration back to `.hgdb` without changing Web UI or API request/response contracts.
- [ ] 6.5 Verify `.hgdb` remains serving when NebulaGraph connection, schema validation, or migration validation fails.

## 7. Tests And Documentation

- [x] 7.1 Add unit tests for entity ID normalization, hyperedge ID normalization, and high-order hyperedge round trips.
- [x] 7.2 Add adapter tests covering every `BaseHypergraphStorage` method used by retrieval.
- [x] 7.3 Add migration tests using a small `.hgdb` fixture with both pairwise and high-order hyperedges.
- [ ] 7.4 Add integration tests comparing `.hgdb` and NebulaGraph retrieval outputs for a fixed fixture dataset.
- [ ] 7.5 Add tests that prove mirror-only and dual-read modes keep `.hgdb` as the serving backend.
- [x] 7.6 Add tests for deterministic output ordering and degree semantics.
- [ ] 7.7 Document NebulaGraph setup, schema initialization, mirror-only migration, validation, enablement, failure policy, and rollback steps.
