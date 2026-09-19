# FAQ

## What runs the wiki?

Codex runs the installed `wiki` skill. Python handles deterministic source artifacts
and optional Jev calls. Logseq or Obsidian displays the Markdown articles. There is
no separate server or vector-database requirement.

## Do I need API keys?

Use your normal Codex account/setup. This toolkit does not call the OpenAI API or
require a separate OpenAI API key. Live Jev judgments require `TYPESAFE_API_KEY` and
`ingest.jev.live: true`. Offline mode records pending questions without API calls.

## Can I keep my existing wiki?

Yes. Run the skill installer with the existing `llm-wiki.yml`. The schema, hub
routing, access log, and L1 verification conventions remain supported. Setup skips
existing wiki pages and asks before replacing an existing config.

## Does Codex read a memory directory automatically?

No. Applicable `AGENTS.md` instructions are startup guidance. The wiki skill reads
optional `memory_path` notes explicitly. Put only non-secret references there;
store credentials in the environment or a secret manager.

## Can I ingest PDFs and scanned books?

Codex first uses available extraction/OCR and image tools. The helper accepts
extracted JSON with pages, lines, coordinates, regions and figures, or plain text.
It does not bundle OCR or claim reliable automatic textbook layout recovery.

## Can I use the original Claude Code command?

This fork targets Codex through `$wiki` and `.agents/skills/wiki/SKILL.md`. Older
Claude slash-command installations are separate and are not needed by Codex.

## Does a high Jev score prove a claim?

No. Scores reflect a supplied rubric; confidence is derived from its answer
distribution. Review evidence in context. Conflicts and uncertain candidates stay
available. No automatic page merge follows from an alignment score.

## Can this repository stay public?

The toolkit and synthetic examples can be public. Keep your actual source files,
indexes, run audits, API keys, and personal wiki in an appropriately private
location. `.wiki-ingest/` and `.env*` are ignored by default. Review staged files
before pushing; ignore rules do not untrack files already committed.
