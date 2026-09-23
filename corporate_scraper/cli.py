"""Headless study creation and export commands for future Task Scheduler use."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .exports import export_study
from .models import FilterSpec, RunSpec, TargetMode
from .paths import default_export_path, study_database
from .reprocess import reprocess_study
from .references import TECHNOLOGY_REFERENCES
from .runner import CollectionRunner
from .sources import IndeedAdapter, LinkedInAdapter
from .store import StudyStore
from .transport import HttpTransport

def _spec(payload: dict) -> RunSpec:
    filters = payload.get("filters", {})
    return RunSpec(name=payload["name"], queries=tuple(payload["queries"]), cities=tuple(payload["cities"]),
                   sources=tuple(str(source).casefold() for source in payload["sources"]), target=int(payload.get("target", 200)),
                   target_mode=TargetMode(payload.get("target_mode", "descriptions")),
                   max_pages=int(payload.get("max_pages", 20)), max_attempts=int(payload.get("max_attempts", 1000)),
                   max_duration_minutes=int(payload.get("max_duration_minutes", 120)),
                   filters=FilterSpec(**filters))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="corporate-scraper")
    parser.add_argument("--database", type=Path, default=study_database())
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-study", help="Create a persisted study from a JSON preset.")
    create.add_argument("--preset", type=Path, required=True)
    export = commands.add_parser("export", help="Export an existing study without opening the desktop UI.")
    export.add_argument("--run-id", required=True); export.add_argument("--output", type=Path)
    export.add_argument("--include-descriptions", action="store_true")
    run = commands.add_parser("run", help="Run a persisted study using the verified HTTP collection path.")
    run.add_argument("--run-id", required=True)
    resume = commands.add_parser("resume", help="Resume unfinished detail and search tasks from a persisted study.")
    resume.add_argument("--run-id", required=True)
    reprocess = commands.add_parser("reprocess", help="Re-extract stored descriptions without network requests.")
    reprocess.add_argument("--run-id", required=True)
    args = parser.parse_args(argv); store = StudyStore(args.database)
    if args.command == "create-study":
        try:
            payload = json.loads(args.preset.read_text(encoding="utf-8"))
            run_id = store.create_run(_spec(payload))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            print(f"Preset error: {error}", file=sys.stderr)
            return 2
        print(run_id)
        return 0
    if args.command == "reprocess":
        print(f"Reprocessed {reprocess_study(store, args.run_id)} descriptions")
        return 0
    if args.command in {"run", "resume"}:
        try:
            stored = store.run(args.run_id)
            spec = RunSpec.from_dict(json.loads(stored["spec_json"]))
            adapters = {"linkedin": LinkedInAdapter(), "indeed": IndeedAdapter()}
            transports = {source: HttpTransport("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
                          for source in spec.sources if source in adapters}
            result = CollectionRunner(store, adapters, transports, TECHNOLOGY_REFERENCES,
                                      min_request_interval_seconds=1.0).run(args.run_id, spec)
        except (KeyError, ValueError, json.JSONDecodeError, OSError) as error:
            print(f"{args.command.title()} error: {error}", file=sys.stderr)
            return 4
        for message in result.messages:
            print(message)
        print(f"state={result.state}; attempts={result.attempts}")
        return 0 if result.state not in {"run_locked"} else 4
    try:
        output = export_study(store, args.run_id, args.output or default_export_path(args.run_id), args.include_descriptions)
        print(output)
    except (OSError, KeyError, ValueError) as error:
        print(f"Export error: {error}", file=sys.stderr)
        return 3
    return 0
