"""Run from the repository or from an installed Codex wiki skill."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wiki_ingest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
