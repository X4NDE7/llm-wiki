---
name: wiki
description: Maintain a personal Logseq or Obsidian wiki with source-linked ingestion, Jev evidence selection, queries, lint, status, import, and pruning. Use when the user asks to work on their configured llm-wiki knowledge base.
---

# Wiki for Codex

Read the configured `llm-wiki.yml` first. The installed copy's config location is in
`config-path.txt` beside this file. In a source checkout, find the user's existing
config or run `setup.sh`; this repository is the toolkit, not their personal wiki.

Invoke as `$wiki ingest <source>`, `$wiki query <question>`, `$wiki lint [--fix]`,
`$wiki status`, `$wiki import`, or `$wiki prune [--l1]`. These are requests to this
skill, not shell commands. Codex performs discovery, reasoning, and article writing.

Read [the workflows](../../wiki.md) for the requested operation and the configured
wiki's Schema for formatting. Preserve hub routing, access logs, L1 verification,
and append-only article content. Load at most three full wiki pages at a time.
Existing user authorization applies; do not ask again for actions already authorized.

## Ingest with Jev

Read [the ingestion guide](../../docs/jev-ingestion.md) for artifact shapes, command
examples, evidence policy, and validation. The helper is
[wiki-ingest.py](../../scripts/wiki-ingest.py); run it with Python 3. It makes typed
Jev calls and deterministic transformations, and never writes wiki articles.

1. Extract source text with edition, page/line locations, layout boundaries, and
   figure references. Inspect images with available vision/document tools. Jev is
   text-only. Preserve extracted sources under the configured artifact directory.
2. Run `prepare` to recover ambiguous structure while retaining exact spans.
3. Read every source section in coherent units. Record a discovery/coverage note,
   including unfamiliar concepts and argument dependencies. Propose versioned
   semantic questions and internal vertical/horizontal reading tasks.
4. Run `annotate` with those dimensions. Run `packet` across relevant indexes for
   each article task. Expand retrieval when candidate coverage is insufficient.
   Use `align` for proposed entity/concept links and `navigate` when several facet
   paths need exploration. Neither operation authorizes merging articles.
5. Read packet quotations in context, including conflicts, low-relevance results,
   uncertain results, and figure references. Explain differences between authors;
   distinguish source statements from your interpretation. Add source title,
   edition, page/span references, and inspected illustrations to the articles.
6. Run the existing quality gate plus provenance checks. Log unresolved questions,
   extraction gaps, rubric revisions, and actual live/offline execution status.
   Commit and push only within the user's authorized repository and scope.

For short notes or `ingest.mode: llm`, use the standard ingest workflow directly.
With `ingest.mode: jev`, pass configured model, request budget, and thresholds to
the helper. Pass `--live` only when `ingest.jev.live` is true and
`TYPESAFE_API_KEY` is available; otherwise run offline and state that Jev judgments
are pending. Never fabricate annotation results to keep the pipeline moving.

## Codex L1

Codex reads applicable `AGENTS.md` instructions at startup. An optional `memory_path`
is this toolkit's directory of non-secret rule notes; it is not automatically loaded
by Codex. Read its `INDEX.md` (or legacy `MEMORY.md`) and relevant notes explicitly
when working on the wiki. Keep essential always-needed rules in `AGENTS.md`.

Store actual credentials in environment variables or a secret manager, never in
`AGENTS.md`, source artifacts, article content, or committed configuration. L1 may
hold credential *references*, not secret values. Do not send L1 notes to Jev.
