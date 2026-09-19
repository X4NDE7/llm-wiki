"""Assemble the self-contained Codex skill into a project's .agents/skills."""

import argparse
import shutil
from pathlib import Path


def install(project, config, source_root=None):
    root = Path(source_root) if source_root else Path(__file__).resolve().parents[1]
    project = Path(project).expanduser().resolve()
    config = Path(config).expanduser().resolve()
    target = project / ".agents" / "skills" / "wiki"
    target.mkdir(parents=True, exist_ok=True)
    references, scripts = target / "references", target / "scripts"
    references.mkdir(exist_ok=True)
    scripts.mkdir(exist_ok=True)
    skill = (root / "skills/wiki/SKILL.md").read_text(encoding="utf-8")
    for old, new in (("../../wiki.md", "references/workflows.md"),
                     ("../../docs/jev-ingestion.md", "references/jev-ingestion.md"),
                     ("../../scripts/wiki-ingest.py", "scripts/wiki-ingest.py")):
        skill = skill.replace(old, new)
    (target / "SKILL.md").write_text(skill, encoding="utf-8", newline="\n")
    (target / "config-path.txt").write_text(str(config) + "\n", encoding="utf-8")
    shutil.copyfile(root / "wiki.md", references / "workflows.md")
    shutil.copyfile(root / "docs/jev-ingestion.md", references / "jev-ingestion.md")
    shutil.copyfile(root / "scripts/wiki-ingest.py", scripts / "wiki-ingest.py")
    package = scripts / "wiki_ingest"
    package.mkdir(exist_ok=True)
    for module in (root / "wiki_ingest").glob("*.py"):
        shutil.copyfile(module, package / module.name)
    example_dir = target / "examples" / "jev"
    example_dir.mkdir(parents=True, exist_ok=True)
    for example in (root / "examples/jev").glob("*.json"):
        shutil.copyfile(example, example_dir / example.name)
    # Preserve existing project guidance. This block only locates the wiki skill.
    agents = project / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    marker = "<!-- llm-wiki skill -->"
    if marker not in text:
        with agents.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n\n" + marker + "\nFor wiki tasks, use the `wiki` skill in "
                         "`.agents/skills/wiki/SKILL.md`. Its `config-path.txt` identifies the wiki. "
                         "Read optional L1 rule notes explicitly; never put secrets in instructions.\n")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print("Installed Codex wiki skill:", install(args.project, args.config))
