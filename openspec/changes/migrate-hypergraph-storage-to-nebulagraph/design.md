## Context

Hyper-RAG stores extracted graph knowledge through `BaseHypergraphStorage`. The current implementation, `HypergraphStorage`, persists a local `hypergraph_chunk_entity_relation.hgdb` file backed by `HypergraphDB`. Retrieval code does not query the `.hgdb` file directly; it depends on storage methods such as `get_vertex`, `get_hyperedge`, `get_nbr_e_of_vertex`, `get_nbr_v_of_hyperedge`, `vertex_degree`, and `hyperedge_degree`.

The query pipeline also depends on separate storage layers:

- `NanoVectorDBStorage` for semantic retrieval of entities, relationships, and chunks.
- JSON KV files for full documents, text chunks, and LLM cache.
- Hypergraph storage for graph expansion, degree ranking, and source chunk lookup.

NebulaGraph can replace the hypergraph storage backend, but NebulaGraph uses a property graph model with binary edges. Hyper-RAG hyperedges can connect more than two entities, so a direct pairwise edge conversion would lose high-order relationship semantics and risk retrieval quality regressions.

## Goals / Non-Goals

**Goals:**

- Preserve current query behavior and answer quality while moving hypergraph persistence from local `.hgdb` files to NebulaGraph.
- Keep Hyper-RAG hyperedges as first-class retrievable objects with their existing `id_set`, `description`, `keywords`, `weight`, and `source_id` fields.
- Keep semantic vector retrieval and text chunk storage unchanged during the initial migration.
- Keep prompt construction, query routing, and answer generation unchanged during the initial migration.
- Provide migration tooling from existing `.hgdb` datasets into NebulaGraph.
- Provide mirror-only migration and dual-read validation that compares `.hgdb` and NebulaGraph retrieval outputs before enabling NebulaGraph serving.
- Allow rollback to `.hgdb` storage without changing Web UI or query API contracts.

**Non-Goals:**

- Replacing `NanoVectorDBStorage` in the initial migration.
- Changing the public `/hyperrag/query`, `/hyperrag/insert`, file upload, or database selection APIs.
- Rewriting `hyper_query`, `hyper_query_lite`, `graph_query`, or prompt behavior as part of the storage migration.
- Flattening all high-order hyperedges into pairwise graph edges.
- Building a full graph analytics feature set on NebulaGraph before storage parity is proven.
- Adding scoped retrieval, query routing, or graph-native reranking in the initial migration.

## Decisions

### Decision: Model hyperedges as NebulaGraph vertices

Represent each Hyper-RAG hyperedge as a `Hyperedge` vertex and connect entity vertices to it with membership edges.

```text
(:Entity {name: A}) -- MEMBER_OF --> (:Hyperedge {edge_hash: H})
(:Entity {name: B}) -- MEMBER_OF --> (:Hyperedge {edge_hash: H})
(:Entity {name: C}) -- MEMBER_OF --> (:Hyperedge {edge_hash: H})
```

The `Hyperedge` vertex stores the original hyperedge fields:

- `id_set`
- `description`
- `keywords`
- `weight`
- `source_id`
- `arity`
- `edge_hash`

Rationale: this preserves high-order relation identity and keeps `get_hyperedge(id_set)` semantically equivalent to the existing `.hgdb` backend.

Alternative considered: convert each hyperedge into all pairwise entity edges. This was rejected because it loses the fact that multiple entities belong to one shared relationship and can change ranking, context construction, and answer quality.

### Decision: Use canonical IDs and deterministic ordering

Entity and Hyperedge IDs must be stable and repeatable across migration runs. Entity VIDs should be derived from a normalized entity name plus database scope. Hyperedge VIDs should be derived from a canonical representation of the sorted `id_set`, plus database scope.

Adapter outputs must normalize unordered values before returning them to retrieval code:

- Hyperedge `id_set` values are returned as deterministic tuples.
- Neighbor hyperedge lists are sorted by canonical hyperedge ID.
- Neighbor entity lists are sorted by canonical entity ID.

Rationale: the current local backend relies heavily on set and tuple semantics. NebulaGraph result ordering can differ, and order drift can change context strings passed to the LLM. Deterministic normalization reduces accidental quality changes.

### Decision: Implement a storage adapter, not a query rewrite

Add `NebulaHypergraphStorage` implementing `BaseHypergraphStorage`. `HyperRAG` should be able to select either `HypergraphStorage` or `NebulaHypergraphStorage` through configuration.

Rationale: the current retrieval pipeline already isolates graph operations behind `BaseHypergraphStorage`. Keeping that contract stable minimizes changes to query behavior and makes parity testing straightforward.

Alternative considered: modify `hyper_query` and related functions to issue NebulaGraph queries directly. This was rejected because it couples retrieval logic to a specific backend and makes quality regressions harder to isolate.

### Decision: Keep vector retrieval unchanged during initial migration

Continue using `NanoVectorDBStorage` for `entities_vdb`, `relationships_vdb`, and `chunks_vdb` during the first NebulaGraph phase.

Rationale: answer quality is strongly affected by vector recall. Changing graph storage and vector retrieval at the same time would make regressions hard to diagnose.

Alternative considered: move vectors into NebulaGraph at the same time. This is out of scope for the first migration and can be proposed separately after graph storage parity is proven.

### Decision: Default to mirror-only until parity is proven

The initial NebulaGraph mode is mirror-only: data is migrated or mirrored into NebulaGraph, but `.hgdb` remains the serving backend. NebulaGraph becomes serving only through explicit per-database opt-in after validation passes.

Write behavior is explicit:

- `hgdb`: existing serving and write behavior.
- `mirror-only`: NebulaGraph receives migrated or mirrored data, while `.hgdb` serves queries.
- `dual-read`: queries compare `.hgdb` and NebulaGraph outputs, while `.hgdb` serves responses.
- `nebulagraph-serving`: NebulaGraph serves graph storage calls after quality gates pass.

Rationale: the safest way to avoid retrieval regression is to prove storage parity before serving queries from NebulaGraph.

### Decision: Use dual-read validation before serving from NebulaGraph

Provide a validation mode that loads the same dataset through both backends and compares storage-level outputs for representative entities, hyperedges, and query expansions.

The minimum parity checks are:

- Vertex count and hyperedge count.
- Sampled `get_vertex` and `get_hyperedge` equality.
- `get_nbr_e_of_vertex` equality after normalizing hyperedge IDs.
- `get_nbr_v_of_hyperedge` equality.
- `vertex_degree` and `hyperedge_degree` equality.
- Retrieved entity overlap for fixed question sets.
- Retrieved hyperedge overlap for fixed question sets.
- Retrieved source text unit overlap for fixed question sets.
- Context string diff for fixed question sets.
- Final answer regression score for fixed question sets when an evaluator is configured.

Rationale: the requirement is to avoid degrading retrieval quality. Dual-read validation gives a concrete gate before changing serving behavior.

### Decision: Preserve `.hgdb` degree semantics

`vertex_degree` and `hyperedge_degree` must match the local backend, independent of how many NebulaGraph edges are used internally to model membership. If both `MEMBER_OF` and reverse membership edges exist, degree calculations must avoid double-counting.

Rationale: degree values are used as `rank` signals in context construction. Any semantic drift changes retrieval ordering and can change answer quality.

### Decision: Preserve source linkage and dataset metadata

NebulaGraph records MUST preserve `source_id` exactly as the current backend does. New optional metadata fields such as `database_name`, `collection`, `source_file`, and `doc_id` should be available for future scoped retrieval.

Rationale: `source_id` is used to return from graph entities/hyperedges to text chunks. Missing or changed `source_id` breaks evidence retrieval. Metadata does not need to affect existing query behavior initially, but it enables safe multi-dataset storage later.

## Risks / Trade-offs

- Hyperedge semantics could be lost if modeled as pairwise edges -> Model hyperedges as first-class vertices and validate `id_set` round trips.
- NebulaGraph query latency could exceed local `.hgdb` latency -> Batch vertex/edge reads where possible and benchmark storage calls used by query paths.
- Storage output ordering could differ from `.hgdb` -> Normalize ordering in the adapter for tuple-like return values and validate context overlap rather than raw unordered set order.
- Canonical ID drift could create duplicate logical hyperedges -> Define stable ID generation before migration and make migration idempotent.
- Degree calculations could double-count membership edges -> Implement degree methods from hyperedge membership semantics, not raw graph edge counts.
- Missing `source_id` could reduce answer grounding -> Treat `source_id` preservation as a migration gate.
- Backend configuration mistakes could point different databases at the same graph space -> Require explicit graph space/database mapping and expose backend status in diagnostics.
- NebulaGraph connection, schema, or migration failures could silently degrade results -> Keep `.hgdb` as the active serving backend unless validation explicitly passes and configuration opts in to NebulaGraph serving.
- Dual writes during insertion could create partial writes -> Start with offline migration and mirror-only validation before enabling NebulaGraph serving.

## Migration Plan

1. Add configuration for hypergraph backend selection with `.hgdb` as the default and mirror-only NebulaGraph support as non-serving.
2. Define NebulaGraph schema for `Entity`, `Hyperedge`, `MEMBER_OF`, and optional reverse membership edges.
3. Implement offline migration from `hypergraph_chunk_entity_relation.hgdb` to NebulaGraph.
4. Implement `NebulaHypergraphStorage` behind `BaseHypergraphStorage` with canonical IDs, deterministic ordering, and `.hgdb` degree semantics.
5. Add parity tooling that compares `.hgdb` and NebulaGraph outputs for storage operations.
6. Add fixed-question retrieval comparisons for `hyper`, `hyper-lite`, and `graph` modes while keeping vector stores unchanged.
7. Run NebulaGraph in dual-read validation mode while `.hgdb` continues serving.
8. Enable NebulaGraph as an opt-in serving backend for selected datasets only after validation passes.
9. Roll back by switching the backend configuration to `.hgdb`; no data deletion is required.

## Open Questions

- Which NebulaGraph deployment target should be supported first: local Docker Compose, external cluster, or both?
- Should the adapter use one graph space per Hyper-RAG database or one shared graph space with a `database_name` property?
- What threshold defines acceptable retrieval parity: exact context match, entity/hyperedge overlap, answer score, or a combination?
- After validation, should insertion use dual-write for rollback safety or NebulaGraph-only writes for operational simplicity?
