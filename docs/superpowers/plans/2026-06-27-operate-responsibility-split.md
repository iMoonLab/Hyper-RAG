# Operate Responsibility Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `hyperrag/operate.py` into focused modules while preserving the existing public import surface and query/indexing behavior.

**Architecture:** Keep `hyperrag/operate.py` as a compatibility facade that re-exports the existing public functions. Move implementation into focused modules for chunking, extraction parsing, graph upsert, indexing, query keyword parsing, query context construction, non-streaming query modes, and streaming query modes. Update internal imports to target the new modules directly while keeping external `hyperrag.operate` imports working.

**Tech Stack:** Python async code, HyperRAG storage abstractions from `hyperrag.base`, prompt constants from `hyperrag.prompt`, utility helpers from `hyperrag.utils`.

---

## File Structure

- Create: `hyperrag/chunking.py`
  - Responsibility: token-window text chunking only.
- Create: `hyperrag/extraction.py`
  - Responsibility: convert LLM extraction records into entity and hyperedge dictionaries.
- Create: `hyperrag/graph_upsert.py`
  - Responsibility: summarize long entity/relation fields, merge duplicate nodes/edges, and write them to the hypergraph storage.
- Create: `hyperrag/indexing.py`
  - Responsibility: orchestrate entity/hyperedge extraction from chunks and update vector stores.
- Create: `hyperrag/query_keywords.py`
  - Responsibility: parse low-level and high-level keyword JSON returned by the LLM.
- Create: `hyperrag/query_context.py`
  - Responsibility: build entity-line, relation-line, and combined context payloads.
- Create: `hyperrag/query_modes.py`
  - Responsibility: non-streaming query entry points.
- Create: `hyperrag/query_stream.py`
  - Responsibility: streaming query entry points.
- Modify: `hyperrag/operate.py`
  - Responsibility after refactor: compatibility facade only.
- Modify: `hyperrag/hyperrag.py`
  - Responsibility after refactor: import operation functions from focused modules instead of `operate.py`.
- Modify: `web-ui/backend/main.py`
  - Responsibility after refactor: include new HyperRAG modules in logging configuration.

---

## Phase 1: Plan Persistence and Compatibility Skeleton

**Files:**
- Create: `docs/superpowers/plans/2026-06-27-operate-responsibility-split.md`
- Modify later: `hyperrag/operate.py`

- [x] **Step 1: Save this implementation plan**

Write this plan under `docs/superpowers/plans/2026-06-27-operate-responsibility-split.md`.

- [ ] **Step 2: Preserve compatibility expectations**

Before changing imports, record that these import paths must keep working:

```python
from hyperrag.operate import chunking_by_token_size
from hyperrag.operate import extract_entities
from hyperrag.operate import hyper_query, hyper_query_lite, graph_query
from hyperrag.operate import naive_query, llm_query
from hyperrag.operate import hyper_query_stream, hyper_query_lite_stream
from hyperrag.operate import naive_query_stream, llm_query_stream
from hyperrag.operate import combine_contexts, remove_after_sources
```

Expected acceptance: after all implementation phases, the import smoke test succeeds.

---

## Phase 2: Split Indexing-Side Responsibilities

**Files:**
- Create: `hyperrag/chunking.py`
- Create: `hyperrag/extraction.py`
- Create: `hyperrag/graph_upsert.py`
- Create: `hyperrag/indexing.py`
- Modify: `hyperrag/operate.py`

- [ ] **Step 1: Move chunking**

Move `chunking_by_token_size` from `operate.py` into `chunking.py`.

`chunking.py` imports:

```python
from .utils import decode_tokens_by_tiktoken, encode_string_by_tiktoken
```

- [ ] **Step 2: Move extraction record parsers**

Move these functions into `extraction.py`:

```python
_handle_single_entity_extraction
_handle_single_relationship_extraction_low
_handle_single_relationship_extraction_high
```

`extraction.py` imports:

```python
from .utils import clean_str, is_float_regex
```

- [ ] **Step 3: Move summary and graph upsert helpers**

Move these functions into `graph_upsert.py`:

```python
_handle_entity_summary
_handle_entity_additional_properties
_handle_relation_summary
_handle_relation_keywords_summary
_merge_nodes_then_upsert
_merge_edges_then_upsert
```

Keep the existing field names and fallback behavior exactly as-is.

- [ ] **Step 4: Move indexing orchestration**

Move `extract_entities` into `indexing.py`.

`indexing.py` should import parsers from `extraction.py` and graph write helpers from `graph_upsert.py`. It must preserve existing progress output, entity/vector upsert payloads, and return semantics.

- [ ] **Step 5: Re-export indexing-side functions from `operate.py`**

Update `operate.py` so legacy imports still work for the moved indexing-side functions.

- [ ] **Step 6: Verify phase 2**

Run:

```powershell
python -m compileall hyperrag
python -c "from hyperrag.operate import chunking_by_token_size, extract_entities; print('indexing imports ok')"
```

Expected: both commands exit with code 0.

---

## Phase 3: Split Query Context and Query Modes

**Files:**
- Create: `hyperrag/query_keywords.py`
- Create: `hyperrag/query_context.py`
- Create: `hyperrag/query_modes.py`
- Create: `hyperrag/query_stream.py`
- Modify: `hyperrag/operate.py`

- [ ] **Step 1: Extract keyword parsing**

Create `query_keywords.py` with:

```python
def parse_query_keywords(result: str, kw_prompt: str) -> tuple[str, str]:
    ...

def parse_low_level_keywords(result: str, kw_prompt: str) -> str:
    ...
```

The parser must preserve the existing fallback behavior:

1. Try `json.loads(result)`.
2. If that fails, strip prompt/user/model markers.
3. Extract the first JSON object between `{` and `}`.
4. Return comma-joined keyword strings.
5. Let `json.JSONDecodeError` propagate to callers so they can return or yield `PROMPTS["fail_response"]`.

- [ ] **Step 2: Move query context builders**

Move these functions into `query_context.py`:

```python
_build_entity_query_context
_find_most_related_text_unit_from_entities
_find_most_related_edges_from_entities
_build_relation_query_context
_find_most_related_entities_from_relationships
_find_related_text_unit_from_relationships
combine_contexts
remove_after_sources
```

Preserve the existing dictionary shape:

```python
{
    "context": str,
    "entities": list[dict],
    "hyperedges": list[dict],
    "text_units": list[dict],
}
```

- [ ] **Step 3: Move non-streaming query modes**

Move these functions into `query_modes.py`:

```python
hyper_query
hyper_query_lite
graph_query
naive_query
llm_query
```

Use `query_keywords.py` for keyword parsing and `query_context.py` for context building. Keep output behavior unchanged for `return_type == "json"` and `only_need_context`.

- [ ] **Step 4: Move streaming query modes**

Move these functions into `query_stream.py`:

```python
hyper_query_stream
hyper_query_lite_stream
naive_query_stream
llm_query_stream
```

Use the same keyword/context helpers as non-streaming code. Preserve current `ValueError` behavior for `return_type == "json"`.

- [ ] **Step 5: Re-export query-side functions from `operate.py`**

Update the compatibility facade so all old `hyperrag.operate` query imports still work.

- [ ] **Step 6: Verify phase 3**

Run:

```powershell
python -m compileall hyperrag
python -c "from hyperrag.operate import hyper_query, hyper_query_lite, graph_query, naive_query, llm_query, hyper_query_stream, hyper_query_lite_stream, naive_query_stream, llm_query_stream, combine_contexts, remove_after_sources; print('query imports ok')"
```

Expected: both commands exit with code 0.

---

## Phase 4: Update Internal Callers and Logging

**Files:**
- Modify: `hyperrag/hyperrag.py`
- Modify: `web-ui/backend/main.py`

- [ ] **Step 1: Update `hyperrag/hyperrag.py` imports**

Replace imports from `.operate` with focused imports:

```python
from .chunking import chunking_by_token_size
from .indexing import extract_entities
from .query_modes import graph_query, hyper_query, hyper_query_lite, llm_query, naive_query
from .query_stream import hyper_query_lite_stream, hyper_query_stream, llm_query_stream, naive_query_stream
```

Do not change `ainsert`, `aquery`, or `astream_query` behavior.

- [ ] **Step 2: Update backend logging module list**

In `web-ui/backend/main.py`, add these module names to `hyperrag_modules`:

```python
hyperrag.chunking
hyperrag.extraction
hyperrag.graph_upsert
hyperrag.indexing
hyperrag.query_keywords
hyperrag.query_context
hyperrag.query_modes
hyperrag.query_stream
```

Keep `hyperrag.operate` in the list.

- [ ] **Step 3: Verify phase 4**

Run:

```powershell
python -m compileall hyperrag
python -c "from hyperrag.hyperrag import HyperRAG; print('HyperRAG import ok')"
rg -n "from \\.operate|from hyperrag\\.operate|hyperrag\\.operate|operate import" .
```

Expected:

- Compile exits with code 0.
- `HyperRAG` import exits with code 0.
- Remaining `operate` references are either the compatibility facade, acceptable external compatibility references, or documented logging references.

---

## Phase 5: Final Verification and Review

**Files:**
- All files touched by previous phases.

- [ ] **Step 1: Run full import/compile verification**

Run:

```powershell
python -m compileall hyperrag
python -c "from hyperrag.operate import chunking_by_token_size, extract_entities, hyper_query, hyper_query_stream, naive_query, llm_query; print('operate compatibility ok')"
python -c "from hyperrag.hyperrag import HyperRAG; print('HyperRAG import ok')"
```

- [ ] **Step 2: Run available tests if environment permits**

Try:

```powershell
python web-ui/backend/test_hyperrag_api.py
python web-ui/backend/test_file_api.py
```

If these tests require a running service, API key, or unavailable dependency, record the exact failure and rely on compile/import verification for this refactor.

- [ ] **Step 3: Inspect diff**

Run:

```powershell
git diff -- hyperrag web-ui/backend/main.py docs/superpowers/plans/2026-06-27-operate-responsibility-split.md
```

Check that:

- `operate.py` is a facade.
- Focused modules own their stated responsibilities.
- No prompt, ranking, truncation, storage field, or return shape was intentionally changed.

- [ ] **Step 4: Final code review**

Request a final code review for the complete split before reporting completion.

