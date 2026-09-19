# L1/L2 architecture in Codex

L1 contains the short instructions that should influence work immediately. L2 is
an on-demand wiki of projects, research, workflows, and source interpretations.

## What Codex loads

Codex discovers applicable `AGENTS.md` instructions at startup, combining global
and project guidance. Put essential non-secret rules there. See the official
[AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The optional `memory_path` in `llm-wiki.yml` is a toolkit convention, not a Codex
autoload feature. The wiki skill explicitly reads `INDEX.md` (or a legacy
`MEMORY.md`) and relevant notes there. Use it for dated operational rules,
preferences, and credential references. Actual tokens and passwords belong in
environment variables or a secret manager, not an instruction file.

The repository skill is installed at `.agents/skills/wiki/SKILL.md`. Codex loads its
instructions when invoked as `$wiki` or when the task matches the skill. It loads
workflow references only as needed. See [skills](https://learn.chatgpt.com/docs/build-skills).

## Routing knowledge

Ask whether a fact is needed before taking routine action. A naming preference or
operational gotcha belongs in L1. A project's history or a book's full argument
belongs in L2. L1 can point to deeper wiki pages without duplicating them.

Article updates preserve existing content and append corrections with context.
Hub descriptions, metadata, and live/archive routing entries can be refreshed.
Keep at most three full wiki pages in context at once.

## Hub routing and LRU demotion

Each namespace hub has an `### Index` of `[[page]] -- description #tags` lines.
`$wiki query` reads these compact indexes, then opens the best matching pages.
Full-text search is a fallback when routing finds no useful page. Each full-page
read is appended to `Wiki/Reference/Access-Log`, including the matched routing
reason. The log feeds `$wiki prune` and the activity dashboard.

Pruning moves cold pages from the live index to `### Archive` and records their
archived status. Files and incoming links remain intact. Querying an archived
page can promote it back into the live index. Index membership concerns navigation,
not whether its evidence or claims are valid.

## L1 verification

Access frequency does not establish whether an operational instruction is still
correct. Rule-note metadata can mark `asserts-current-behavior: true` and a
`verified: YYYY-MM-DD` date. Decisions and preferences use `false`. Unclassified
notes remain visible for review.

`$wiki lint` reports due behavior claims using `l1_verify_days` (default 90) without
printing private note bodies or changing L1. `$wiki prune --l1` checks individual
claims against read-only local evidence and proposes re-verification, correction,
demotion into wiki history, or deletion. Preserve unrelated notes and any existing
user authorization. This is a review workflow, not an automatic runtime gate.

## Jev's input-stage role

Source preparation and semantic indexing support L2 ingestion without replacing
L1 instructions. Codex discovers concepts and reading tasks. Jev evaluates atomic
questions about local source evidence. Code copies exact spans into packets; Codex
reads the surrounding context and reconciles sources. No L1 notes are sent to Jev.

See [Jev ingestion](jev-ingestion.md) for the extraction contract, multidimensional
annotations, vertical/horizontal packets, alignment, and evaluation process.
