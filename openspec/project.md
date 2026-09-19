# Project: llm-wiki

## Context

llm-wiki implements Andrej Karpathy's "LLM Wiki" concept — a persistent, structured
knowledge base maintained by an LLM (Codex) using a dual-layer cache architecture
inspired by CPU memory hierarchies.

- **Owner:** X4NDE7 (Codex/Jev adaptation); upstream by Mehmet Goekce / MEMOTECH
- **License:** MIT (open-source)
- **Repository:** github.com/X4NDE7/llm-wiki
- **Status:** Codex/Jev adaptation of upstream v1.4.0

## Architecture

- **L1:** Applicable AGENTS.md startup instructions plus optional explicitly read rule notes. Rules, gotchas, identity and credential references only.
- **L2 (On-demand):** Logseq or Obsidian wiki (~50-200 pages). Projects, workflows,
  research, deep knowledge. Queried via `$wiki` commands. Git-tracked.

## Tech Stack

- **Runtime:** Codex (CLI)
- **Dependencies:** bash, python3, git (no npm, no pip)
- **Wiki tools:** Logseq (outliner) or Obsidian (flat markdown)
- **Config:** `llm-wiki.yml` (YAML)
- **Format:** Markdown with tool-specific conventions

## Stakeholders

| Role | Who | Responsibility |
|------|-----|---------------|
| Maintainer | Mehmet Goekce | Architecture, releases, specs |
| Contributors | Open-source community | Features, bug fixes, templates |
| Users | Codex users | Install, configure, use $wiki commands |

## Constraints

- Zero external dependencies beyond bash, python3, git
- Must work on macOS, Linux, WSL
- Must support both Logseq and Obsidian (identical capabilities, different format)
- Config always reads from `llm-wiki.yml`
- Max 3 wiki pages loaded simultaneously (LLM context budget)
- Actual credentials MUST stay in environment variables or a secret manager, never L1 instructions or L2 articles
- Append-only updates (never overwrite existing wiki content)

## Specs

| Spec | Covers | Requirements | Scenarios |
|------|--------|-------------|-----------|
| specs/ingest.md | $wiki ingest — 5-phase source processing pipeline | 34 | 10 |
| specs/query.md | $wiki query — two-stage routing, synthesis, access log | 26 | 13 |
| specs/lint.md | $wiki lint — 12 automated health checks with auto-fix | 53 | 14 |
| specs/prune.md | $wiki prune — L2 index eviction, `--l1` verification | 39 | 15 |
| specs/schema.md | Page types, properties, validation, format rules | 49 | 10 |
| specs/config.md | llm-wiki.yml loading, validation, error handling | 20 | 9 |
| specs/setup.md | setup.sh interactive installer (11 steps) | 47 | 10 |
| specs/l1-l2-routing.md | L1/L2 boundary decision logic, L1 staleness | 40 | 11 |
| **Total** | **Complete system coverage** | **308** | **92** |
