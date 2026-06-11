# NebulaGraph Hypergraph Storage Rollout

## Default Behavior

HyperRAG continues to use the local `.hgdb` hypergraph store by default. Public query and upload APIs are unchanged during the NebulaGraph rollout.

NebulaGraph support is intentionally conservative. The current migration path is additive, and `.hgdb` remains the serving backend unless NebulaGraph serving is explicitly enabled and validated.

## Backend Modes

- `hgdb`: Use the existing `.hgdb` hypergraph store for reads and writes. This remains the default mode.
- `mirror-only`: Keep `.hgdb` serving user queries while mirroring hypergraph writes or migration output into NebulaGraph.
- `dual-read`: Keep `.hgdb` serving user queries while comparing NebulaGraph reads for parity checks and diagnostics.
- `nebulagraph-serving`: Serve hypergraph reads from NebulaGraph only after explicit enablement and validation.

## Conservative Enablement Policy

`mirror-only` and `dual-read` must not serve user-facing query responses from NebulaGraph. They are for migration, diagnostics, and parity validation while `.hgdb` remains the source used for user-visible retrieval.

`nebulagraph-serving` requires both:

- Backend mode set to `nebulagraph-serving`.
- The validation flag configured to allow NebulaGraph serving.

Do not enable `nebulagraph-serving` until storage parity and retrieval parity are implemented and passing. If NebulaGraph is unavailable, unvalidated, or misconfigured, use `hgdb` so `.hgdb` remains the serving backend.

## Current Commands

The implemented schema inspection command prints the local NebulaGraph schema DDL statements for the configured graph space:

```bash
./scripts/hyperrag_nebulagraph.py schema-check --space hyperrag
```

At this stage, the command prints the local schema statements only. It does not verify a remote NebulaGraph cluster.

## Current Limitations

The NebulaGraph rollout is not complete yet:

- CLI `migrate` and `validate` are parser placeholders and intentionally return an implementation-wiring error.
- Real NebulaGraph client writes are not complete.
- Remote schema verification is not complete.
- Retrieval parity checks for fixed question sets are not complete.
- Serving cutover to NebulaGraph is not complete.

These limitations mean NebulaGraph should be treated as migration groundwork only, not as a serving-ready replacement for `.hgdb`.

## Setup And Schema Initialization

Before attempting migration or validation work, prepare a NebulaGraph space such as `hyperrag` in the target NebulaGraph environment. Use the schema check command above to print the schema DDL statements expected by HyperRAG, then apply the statements through the NebulaGraph tooling used by your deployment.

Because remote schema verification is not implemented yet, manually confirm that the required tags, edge types, and indexes exist before relying on mirror or validation output.

## Mirror-Only Migration

Use `mirror-only` when wiring migration execution so `.hgdb` remains the serving backend while NebulaGraph receives mirrored data. This mode is intended to make migration repeatable and observable without changing user-facing retrieval behavior.

Do not use mirror-only results as proof that NebulaGraph serving is ready. Mirror-only mode must be followed by storage parity and retrieval parity validation.

## Validation

Use `dual-read` for parity validation work once the validation implementation is wired. In this mode, `.hgdb` remains the serving backend and NebulaGraph reads are compared for diagnostics only.

The quality gate for serving is:

- Storage parity implemented and passing.
- Retrieval parity implemented and passing for fixed question sets.
- Schema and migration completeness validation implemented and passing.
- Validation flag explicitly allows NebulaGraph serving.

Until those checks exist and pass, keep serving mode on `hgdb`.

## Failure Policy

If NebulaGraph connection, schema validation, migration validation, or parity validation fails, keep `.hgdb` as the serving backend. Mirror-only and dual-read failures should be treated as migration or validation failures, not as user-facing query failures.

## Rollback

Rollback is configuration-only for the public API surface:

- Set `hypergraphBackendMode` or `hypergraph_backend_mode` back to `hgdb`.
- Keep public query and upload API request and response contracts unchanged.

After rollback, HyperRAG should continue serving from the existing `.hgdb` hypergraph data.
