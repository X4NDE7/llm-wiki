"""CLI used by Codex after it reads the wiki's YAML configuration."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .evidence import align, navigate, packet
from .jev import Jev
from .source import annotate, prepare, text_source


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value):
    """Publish a complete artifact without overwriting any existing version."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ingest-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        # Hard-link publication fails if destination exists, unlike os.replace.
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Source-linked Jev evidence tools for Codex. Offline by default.")
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "annotate", "packet", "align", "navigate"):
        command = subs.add_parser(name)
        command.add_argument("--output", required=True)
        command.add_argument("--audit", help="Defaults to OUTPUT.run.json")
        mode = command.add_mutually_exclusive_group()
        mode.add_argument("--live", action="store_true", help="Send evidence to TypeSafe using TYPESAFE_API_KEY")
        mode.add_argument("--replay", help="Reuse validated responses with identical request hashes")
        command.add_argument("--model", default="jev-1.13.0")
        command.add_argument("--max-requests", type=int, default=1000)
        command.add_argument("--yes", type=float, default=0.8)
        command.add_argument("--no", type=float, default=0.2)
        command.add_argument("--confidence", type=float, default=0.8)
        if name in ("annotate", "packet", "align"):
            command.add_argument("--index", action="append", required=True)
        if name == "prepare":
            command.add_argument("source")
            command.add_argument("--source-id")
            command.add_argument("--title")
            command.add_argument("--edition", default="unspecified")
        elif name == "annotate":
            command.add_argument("--dimensions", required=True)
        elif name == "packet":
            command.add_argument("--task", required=True)
            command.add_argument("--limit", type=int, default=30)
        elif name == "align":
            command.add_argument("--pair", required=True)
        else:
            command.add_argument("--state", required=True, help="JSON evidence or article description")
            command.add_argument("--facets", required=True)
            command.add_argument("--width", type=int, default=3)
            command.add_argument("--depth", type=int, default=6)
    args = parser.parse_args(argv)
    try:
        output = Path(args.output).expanduser().resolve()
        audit = Path(args.audit).expanduser().resolve() if args.audit else Path(str(output) + ".run.json")
        if output == audit or output.exists() or audit.exists():
            raise ValueError("output/audit already exists or paths overlap; choose a new run filename")
        jev = Jev(live=args.live, model=args.model,
                  replay=read_json(args.replay) if args.replay else None,
                  max_requests=args.max_requests, yes=args.yes, no=args.no, confidence=args.confidence)
        if args.command == "prepare":
            if Path(args.source).suffix.lower() == ".json":
                source = read_json(args.source)
            else:
                if not args.source_id:
                    raise ValueError("plain text preparation requires --source-id")
                source = text_source(args.source, args.source_id, args.title, args.edition)
            result = prepare(source, jev)
        elif args.command == "annotate":
            if len(args.index) != 1:
                raise ValueError("annotate takes exactly one index")
            result = annotate(read_json(args.index[0]), read_json(args.dimensions), jev)
        elif args.command == "packet":
            result = packet([read_json(p) for p in args.index], read_json(args.task), jev, args.limit)
        elif args.command == "align":
            result = align([read_json(p) for p in args.index], read_json(args.pair), jev)
        else:
            result = navigate(read_json(args.state), read_json(args.facets), jev, args.width, args.depth)
        write_new(audit, jev.audit())
        write_new(output, result)
        unresolved = sum(r["status"] != "evaluated" for r in jev.records)
        print(f"Wrote {output}\nAudit: {audit}\nRequests without evaluated answers: {unresolved}")
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        # Do not echo arbitrary source or HTTP contents on the error path.
        if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError):
            print(f"Error: {error}", file=sys.stderr)
        else:
            print(f"Error: invalid or inaccessible input/output ({type(error).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
