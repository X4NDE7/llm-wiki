# Troubleshooting

## Setup cannot find Python

Run `python3 --version`. Install Python 3 and ensure it is on the shell's PATH.
On Windows, use WSL or Git Bash with a working Python interpreter. No pip packages
are required. In PowerShell, the helper also runs as `python scripts/wiki-ingest.py`.

## Codex cannot find the wiki skill

Check `<project>/.agents/skills/wiki/SKILL.md` and start Codex in that project.
The file must have `name: wiki` and a description in YAML frontmatter. Restart Codex
if a newly installed skill has not appeared. Invoke `$wiki ingest ...` inside
Codex, not in your terminal.

Reinstall only the skill, preserving wiki pages:

```bash
python3 scripts/install_skill.py --project /path/to/project --config /path/to/wiki/llm-wiki.yml
```

The installed `config-path.txt` must point to the intended configuration. The skill
bundle contains `references/`, `scripts/wiki-ingest.py`, and `scripts/wiki_ingest/`.

## Existing pages or config are skipped

Setup preserves existing pages. It prompts before replacing the config. Add new
schema guidance deliberately to an existing vault instead of expecting setup to
replace customized pages. Refresh the installed skill with the command above.

## Jev answers are pending or unresolved

Offline is the default. For live calls, set `TYPESAFE_API_KEY` in the environment
without committing it and set `ingest.jev.live: true`. Missing credentials never
produce synthetic successful judgments. Inspect the run audit's request statuses.

`pending` means no response was obtained in offline/replay mode. `oversized` means
source evidence needs subdivision with intact spans. `invalid_response` means the
provider's answer failed the typed contract. `http_401` indicates authentication;
`http_429`/`http_529` indicate rate/overload limits. `budget_exhausted` means the
configured maximum attempts was reached. Choose a new output filename to rerun.

An evaluated answer can still have an `unresolved` label when it falls between the
configured thresholds. Preserve it for review; do not treat it as a negative.

## Output already exists

Artifacts are immutable by filename. Use a new revision name for both output and
its `.run.json` audit. `annotate` preserves old dimension sets and answers in the
new index. A changed source/edition requires preparation again and new block IDs.

## Retrieval misses a concept

Read the source in context and revise the task. Add source block IDs proposed by
Codex to `candidate_ids`, expand the lexical shortlist, or add Noul dimension
matches. Filters add candidates; they never exclude unfamiliar material. An absence
result applies only to evaluated candidates, not the entire book.

## Wiki links or routing look wrong

Check the configured tool. Logseq uses `Wiki___Namespace___Page.md` in `pages/`;
Obsidian uses `Wiki/Namespace/Page.md`. Both link using `[[Wiki/Namespace/Page]]`.
Run `$wiki lint --fix` to repair hub index drift and missing cross-references.
Cold pages remain on disk after `$wiki prune`; look in the hub's archive section
or use the query's full-text fallback.

## A credential warning appears

Review the flagged text without printing secrets. Remove secret values from the
pending article changes and use a credential reference. Never send credentials to
Jev or commit them. Source artifacts and run audits can contain source quotations,
so keep them in the configured private/ignored artifact directory.
