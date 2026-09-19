"""Install into isolated wikis and execute the bundled helper without the checkout."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = (Path("C:/Program Files/Git/bin/bash.exe") if os.name == "nt"
        else Path(shutil.which("bash") or "/missing-bash"))


@unittest.skipUnless(BASH.exists(), "bash is needed for installer integration tests")
class SetupTests(unittest.TestCase):
    def test_both_wiki_formats_and_installed_pipeline(self):
        for mode, name in (("1", "logseq"), ("2", "obsidian")):
            with self.subTest(tool=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                wiki, project = root / "Wiki's space", root / "Codex project"
                wiki.mkdir()
                project.mkdir()
                (project / "AGENTS.md").write_text("Keep existing project guidance.\n", encoding="utf-8")
                env = {**os.environ, "GIT_AUTHOR_NAME": "Wiki Test", "GIT_AUTHOR_EMAIL": "wiki@example.test",
                       "GIT_COMMITTER_NAME": "Wiki Test", "GIT_COMMITTER_EMAIL": "wiki@example.test"}
                subprocess.run(["git", "init", str(wiki)], check=True, capture_output=True, env=env)
                answers = f"{mode}\n{wiki.as_posix()}\n\nskip\n{project.as_posix()}\n"
                run = subprocess.run([str(BASH), str(ROOT / "setup.sh")], input=answers.encode(),
                                     capture_output=True, env=env, timeout=45)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                config = (wiki / "llm-wiki.yml").read_text(encoding="utf-8")
                self.assertIn('memory_path: ""', config)
                self.assertIn("live: false", config)
                skill = project / ".agents/skills/wiki"
                self.assertTrue((skill / "SKILL.md").exists())
                self.assertEqual(Path((skill / "config-path.txt").read_text().strip()), wiki / "llm-wiki.yml")
                self.assertIn("Keep existing project guidance.", (project / "AGENTS.md").read_text())
                schema = wiki / ("pages/Wiki___Schema.md" if name == "logseq" else "Wiki/Schema.md")
                schema_text = schema.read_text(encoding="utf-8")
                self.assertTrue(schema_text.startswith("- wiki-version::" if name == "logseq" else "---\n"))
                self.assertIn("Source Provenance", schema_text)
                if name == "logseq":
                    self.assertTrue(all(line.lstrip().startswith("- ") for line in schema_text.splitlines() if line.strip()))
                subprocess.run(["git", "check-ignore", ".wiki-ingest/private.txt"], cwd=wiki,
                               capture_output=True, check=True)
                # Run the copied script with an unrelated working directory and no PYTHONPATH.
                helper = skill / "scripts/wiki-ingest.py"
                clean_env = {k: v for k, v in env.items() if k not in ("PYTHONPATH", "TYPESAFE_API_KEY")}
                prepared, annotated, packet_path = root / "prepared.json", root / "annotated.json", root / "packet.json"
                commands = [
                    ["prepare", str(skill / "examples/jev/source.json"), "--output", str(prepared)],
                    ["annotate", "--index", str(prepared), "--dimensions", str(skill / "examples/jev/dimensions.json"), "--output", str(annotated)],
                    ["packet", "--index", str(annotated), "--task", str(skill / "examples/jev/task.json"), "--output", str(packet_path)],
                ]
                for command in commands:
                    result = subprocess.run([sys.executable, str(helper), *command], cwd=root,
                                            capture_output=True, text=True, env=clean_env, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                packet_data = json.loads(packet_path.read_text(encoding="utf-8"))
                self.assertEqual(packet_data["answer_status"], "unresolved")
                self.assertTrue(packet_data["candidates"])
                # Rerun: refuse config replacement and preserve customized pages/instructions.
                schema.write_text(schema_text + "\n" + ("- " if name == "logseq" else "") + "Custom schema note\n", encoding="utf-8")
                original = schema.read_bytes()
                rerun_answers = f"{mode}\n{wiki.as_posix()}\n\nskip\nn\n{project.as_posix()}\n"
                rerun = subprocess.run([str(BASH), str(ROOT / "setup.sh")], input=rerun_answers.encode(),
                                       capture_output=True, env=env, timeout=45)
                self.assertEqual(rerun.returncode, 0, rerun.stdout + rerun.stderr)
                self.assertEqual(schema.read_bytes(), original)
                self.assertEqual((project / "AGENTS.md").read_text().count("<!-- llm-wiki skill -->"), 1)


if __name__ == "__main__":
    unittest.main()
