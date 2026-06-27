## Why

Hyper-RAG currently persists extracted entities, hyperedges, and adjacency data in local `.hgdb` pickle files. This limits operational visibility, centralized management, and future multi-dataset graph operations as the Web UI moves beyond small local demos.

NebulaGraph can provide a durable graph backend for the Hyper-RAG knowledge graph, but the migration must preserve the current retrieval behavior and answer quality by keeping hyperedge semantics, source chunk links, and vector retrieval unchanged during the first migration phase.

## What Changes

- Add a NebulaGraph-backed hypergraph storage option that implements the existing `BaseHypergraphStorage` contract.
- Represent Hyper-RAG hyperedges as first-class NebulaGraph vertices connected to entity vertices, rather than flattening hyperedges into pairwise edges.
- Preserve existing entity, hyperedge, degree, neighbor, and source lookup behavior expected by `hyper_query`, `hyper_query_lite`, and `graph_query`.
- Keep `NanoVectorDBStorage` and JSON text chunk storage unchanged in the initial migration so semantic retrieval quality can be compared independently from graph storage changes.
- Add an offline migration/export path from existing `hypergraph_chunk_entity_relation.hgdb` files into NebulaGraph.
- Add a dual-read validation mode that compares `.hgdb` and NebulaGraph retrieval outputs before switching query traffic.
- Add configuration to select the hypergraph backend per deployment or database.
- No breaking API changes are intended for Web UI query, insert, file upload, or database selection endpoints.

## Capabilities

### New Capabilities
- `nebulagraph-hypergraph-storage`: Store and retrieve Hyper-RAG entity and hyperedge graph data from NebulaGraph while preserving current retrieval semantics and quality validation.

### Modified Capabilities

None.

## Impact

- Affected storage code:
  - `hyperrag/base.py`
  - `hyperrag/storage.py`
  - HyperRAG initialization paths in `hyperrag/hyperrag.py` and `web-ui/backend/main.py`
- Affected retrieval behavior:
  - `hyperrag/operate.py` depends on exact `BaseHypergraphStorage` semantics for neighbor, degree, entity, hyperedge, and source lookups.
- New dependencies:
  - NebulaGraph Python client or an equivalent supported client package.
  - NebulaGraph connection configuration for host, port, credentials, graph space, and backend selection.
- New operational systems:
  - NebulaGraph graph space/schema management.
  - Migration and validation tooling for existing `.hgdb` datasets.
- Quality risk:
  - Incorrect hyperedge modeling or missing `source_id` preservation can reduce retrieval quality. The migration must include parity checks before enabling NebulaGraph as the serving backend.
