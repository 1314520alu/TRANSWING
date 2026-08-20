#!/usr/bin/env python3
"""Search Transwing knowledge-base files (md, csv, params, lua)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "knowledge-base" / "index.yaml"
SEARCH_EXTENSIONS = {".md", ".csv", ".params", ".lua", ".mjs"}
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "agent-tools",
    "mcps",
    "outputs",
    "patches",
}


def load_index() -> dict | None:
    if not INDEX_PATH.exists() or yaml is None:
        return None
    with INDEX_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def paths_for_category(category: str | None) -> set[Path] | None:
    if not category:
        return None
    index = load_index()
    if not index:
        return None
    cat = category.lower()
    paths: set[Path] = set()
    for block in index.get("categories", []):
        if block.get("id", "").lower() == cat:
            for item in block.get("items", []):
                paths.add(REPO_ROOT / item["path"])
    return paths if paths else None


def iter_files(category_paths: set[Path] | None) -> list[Path]:
    if category_paths is not None:
        return sorted(p for p in category_paths if p.is_file())

    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SEARCH_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def search_file(path: Path, pattern: re.Pattern[str], max_snippets: int = 3) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    hits: list[dict] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not pattern.search(line):
            continue
        hits.append(
            {
                "file": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "line": i,
                "text": line.strip()[:240],
            }
        )
        if len(hits) >= max_snippets:
            break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Transwing knowledge base")
    parser.add_argument("query", help="Search keyword or regex")
    parser.add_argument(
        "--category",
        "-c",
        choices=["airframe", "firmware", "sitl_lua", "guard", "design"],
        help="Limit to index.yaml category",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--ignore-case", "-i", action="store_true", default=True)
    args = parser.parse_args()

    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        pattern = re.compile(args.query, flags)
    except re.error:
        pattern = re.compile(re.escape(args.query), flags)

    category_paths = paths_for_category(args.category)
    if args.category and category_paths is not None and not category_paths:
        print(f"Unknown category: {args.category}", file=sys.stderr)
        return 1

    results: list[dict] = []
    for path in iter_files(category_paths):
        for hit in search_file(path, pattern):
            results.append(hit)

    if args.json:
        print(json.dumps({"query": args.query, "count": len(results), "hits": results}, ensure_ascii=False, indent=2))
    else:
        if not results:
            print(f"No matches for: {args.query}")
            return 0
        for hit in results:
            print(f"{hit['file']}:{hit['line']}: {hit['text']}")
        print(f"\n{len(results)} match(es)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
