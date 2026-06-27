## ADDED Requirements

### Requirement: NebulaGraph backend selection
The system SHALL support selecting NebulaGraph as an alternative hypergraph storage backend while preserving `.hgdb` storage as the default serving backend until NebulaGraph parity is validated and explicitly enabled.

#### Scenario: Default backend remains local hgdb
- **WHEN** no NebulaGraph backend configuration is provided
- **THEN** the system SHALL continue using the existing `.hgdb` hypergraph storage implementation

#### Scenario: NebulaGraph backend is configured
- **WHEN** deployment configuration enables NebulaGraph for a database without serving opt-in
- **THEN** the system SHALL use NebulaGraph only for migration, mirror, or validation workflows while `.hgdb` remains the serving backend

#### Scenario: NebulaGraph serving is explicitly enabled
- **WHEN** deployment configuration selects NebulaGraph serving for a database after quality validation passes
- **THEN** HyperRAG SHALL initialize a NebulaGraph-backed implementation of `BaseHypergraphStorage` for serving that database

### Requirement: Mirror-only migration mode
The system SHALL provide a mirror-only NebulaGraph mode that stores migrated or mirrored graph data without serving user queries from NebulaGraph.

#### Scenario: Mirror-only mode receives graph data
- **WHEN** mirror-only mode is active for a database
- **THEN** NebulaGraph SHALL receive migrated or mirrored Entity and Hyperedge records for that database

#### Scenario: Mirror-only mode preserves serving backend
- **WHEN** mirror-only mode is active for a database
- **THEN** user query execution SHALL continue reading hypergraph data from the `.hgdb` backend

### Requirement: Hyperedge-preserving graph model
The system SHALL model each Hyper-RAG hyperedge as a first-class NebulaGraph vertex rather than flattening high-order hyperedges into pairwise entity edges.

#### Scenario: Migrating a high-order hyperedge
- **WHEN** a source hyperedge contains more than two entity IDs
- **THEN** the migration SHALL create one Hyperedge vertex preserving the original `id_set`, `description`, `keywords`, `weight`, and `source_id`

#### Scenario: Connecting entities to a hyperedge
- **WHEN** a Hyperedge vertex is created
- **THEN** the migration SHALL connect every member entity vertex to the Hyperedge vertex with membership relationships

### Requirement: Canonical graph identifiers
The system SHALL use stable, deterministic identifiers for NebulaGraph Entity and Hyperedge vertices so repeated migrations and validations address the same logical records.

#### Scenario: Entity identifier generation
- **WHEN** an entity is written to NebulaGraph
- **THEN** its vertex identifier SHALL be derived from a canonical entity name and database scope

#### Scenario: Hyperedge identifier generation
- **WHEN** a hyperedge is written to NebulaGraph
- **THEN** its vertex identifier SHALL be derived from a canonical sorted representation of `id_set` and database scope

#### Scenario: Hyperedge identifier round trip
- **WHEN** retrieval calls `get_hyperedge` with an unordered `id_set`
- **THEN** the NebulaGraph backend SHALL resolve the same Hyperedge vertex as the `.hgdb` backend would resolve after normalizing the `id_set`

### Requirement: Storage contract parity
The NebulaGraph backend SHALL implement the same externally observable behavior as `BaseHypergraphStorage` for all methods used by Hyper-RAG retrieval.

#### Scenario: Entity lookup parity
- **WHEN** retrieval calls `get_vertex` for an entity that exists in the migrated dataset
- **THEN** the NebulaGraph backend SHALL return the same entity fields as the `.hgdb` backend, including `entity_type`, `description`, `source_id`, and `additional_properties`

#### Scenario: Hyperedge lookup parity
- **WHEN** retrieval calls `get_hyperedge` with an `id_set` that exists in the migrated dataset
- **THEN** the NebulaGraph backend SHALL return the same hyperedge fields as the `.hgdb` backend, including `description`, `keywords`, `source_id`, and `weight`

#### Scenario: Neighbor lookup parity
- **WHEN** retrieval calls `get_nbr_e_of_vertex` or `get_nbr_v_of_hyperedge`
- **THEN** the NebulaGraph backend SHALL return neighbor relationships equivalent to the `.hgdb` backend after normalizing unordered hyperedge ID sets

#### Scenario: Degree parity
- **WHEN** retrieval calls `vertex_degree` or `hyperedge_degree`
- **THEN** the NebulaGraph backend SHALL return the same degree values as the `.hgdb` backend for the migrated dataset

#### Scenario: Deterministic output ordering
- **WHEN** the NebulaGraph backend returns entities, hyperedges, or neighbor lists to retrieval code
- **THEN** it SHALL return deterministic normalized ordering so equivalent data produces stable context construction

#### Scenario: Membership edges do not affect degree semantics
- **WHEN** the NebulaGraph schema uses membership edges to model hyperedges
- **THEN** `vertex_degree` and `hyperedge_degree` SHALL be computed from Hyper-RAG membership semantics and SHALL NOT double-count reverse or auxiliary membership edges

### Requirement: Source chunk linkage preservation
The migration SHALL preserve source chunk linkage so graph retrieval can resolve entities and hyperedges back to the existing text chunk store.

#### Scenario: Entity source IDs are migrated
- **WHEN** an entity vertex is migrated to NebulaGraph
- **THEN** its `source_id` value SHALL be preserved exactly as represented in the `.hgdb` backend

#### Scenario: Hyperedge source IDs are migrated
- **WHEN** a hyperedge is migrated to NebulaGraph
- **THEN** its `source_id` value SHALL be preserved exactly as represented in the `.hgdb` backend

### Requirement: Vector retrieval remains unchanged
The initial NebulaGraph migration SHALL NOT replace the existing vector storage used for entity, relationship, or chunk semantic retrieval, and SHALL NOT alter prompt construction, query routing, or answer generation.

#### Scenario: Querying with NebulaGraph backend
- **WHEN** a query runs with NebulaGraph selected as the hypergraph backend
- **THEN** the system SHALL continue using the configured vector stores for `entities_vdb`, `relationships_vdb`, and `chunks_vdb`

#### Scenario: Query behavior remains storage-semantics preserving
- **WHEN** NebulaGraph is used as the hypergraph backend
- **THEN** the query pipeline SHALL preserve existing vector recall, text chunk lookup, context format, prompt templates, and answer generation behavior

### Requirement: Offline migration from hgdb
The system SHALL provide a migration path from existing `hypergraph_chunk_entity_relation.hgdb` files into NebulaGraph.

#### Scenario: Migrating an existing database
- **WHEN** an operator runs the migration for a Hyper-RAG database directory
- **THEN** the system SHALL read the source `.hgdb` file and create equivalent Entity and Hyperedge records in the configured NebulaGraph graph space

#### Scenario: Migration is repeatable
- **WHEN** an operator reruns migration for the same source `.hgdb` file
- **THEN** the system SHALL upsert existing Entity and Hyperedge records without creating duplicate logical graph records

### Requirement: Dual-read validation
The system SHALL provide validation that compares `.hgdb` and NebulaGraph outputs before NebulaGraph is used as the serving graph backend.

#### Scenario: Storage parity validation
- **WHEN** validation runs against a migrated dataset
- **THEN** it SHALL compare vertex counts, hyperedge counts, sampled entity records, sampled hyperedge records, neighbor lookups, and degree values between both backends

#### Scenario: Retrieval parity validation
- **WHEN** validation runs against a fixed question set
- **THEN** it SHALL compare retrieved entities, hyperedges, and source text units for `hyper`, `hyper-lite`, and `graph` query modes while keeping vector stores unchanged

#### Scenario: Context parity validation
- **WHEN** validation runs against a fixed question set
- **THEN** it SHALL report context string differences between `.hgdb` and NebulaGraph retrieval outputs after deterministic normalization

#### Scenario: Answer regression validation
- **WHEN** an answer evaluator is configured for a fixed question set
- **THEN** validation SHALL report final answer regression scores for `.hgdb` and NebulaGraph-backed retrieval

### Requirement: Quality gate before serving
The system SHALL require an explicit quality gate before NebulaGraph can be enabled as the serving backend for a dataset.

#### Scenario: Validation passes
- **WHEN** storage parity and retrieval parity meet configured acceptance thresholds
- **THEN** the operator SHALL be able to enable NebulaGraph as the serving hypergraph backend for that dataset

#### Scenario: Validation fails
- **WHEN** storage parity or retrieval parity fails configured acceptance thresholds
- **THEN** the system SHALL keep the `.hgdb` backend active for serving and report the failed checks

### Requirement: Failure policy preserves serving quality
The system SHALL avoid silently serving from NebulaGraph when NebulaGraph is unavailable, misconfigured, or not validated.

#### Scenario: NebulaGraph connection fails before serving opt-in
- **WHEN** NebulaGraph is configured for mirror or validation and the connection fails
- **THEN** the system SHALL keep `.hgdb` as the serving backend and report the NebulaGraph failure

#### Scenario: NebulaGraph schema is incomplete
- **WHEN** required NebulaGraph tags, edge types, or indexes are missing
- **THEN** migration or validation SHALL fail with a diagnostic message and SHALL NOT enable NebulaGraph serving

#### Scenario: Partial migration is detected
- **WHEN** validation detects missing or mismatched entities, hyperedges, source IDs, neighbors, or degrees
- **THEN** NebulaGraph serving SHALL remain disabled for that dataset

### Requirement: Rollback without API changes
The system SHALL allow rollback from NebulaGraph to `.hgdb` storage without changing public query, insert, upload, or database selection APIs.

#### Scenario: Backend rollback
- **WHEN** an operator switches backend configuration from NebulaGraph to `.hgdb`
- **THEN** existing Web UI and API clients SHALL continue using the same request and response contracts
