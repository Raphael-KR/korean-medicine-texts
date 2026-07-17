#!/usr/bin/env python3
"""Search canonical classical texts registered in catalog.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def load_catalog(repo_root: Path) -> dict[str, Any]:
    catalog_path = repo_root / "catalog.json"
    if not catalog_path.is_file():
        raise ValueError(f"catalog.json not found under repository root: {repo_root}")
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(data.get("texts"), list):
        raise ValueError("catalog.json does not contain a texts list")
    return data


def search(
    query: str,
    repo_root: Path,
    source_id: str | None = None,
    max_results: int = 20,
    context: int = 0,
) -> dict[str, Any]:
    if not query:
        raise ValueError("query must not be empty")
    if max_results < 1:
        raise ValueError("max_results must be at least 1")
    if context < 0:
        raise ValueError("context must not be negative")

    repo_root = repo_root.resolve()
    catalog = load_catalog(repo_root)
    entries = catalog["texts"]
    if source_id is not None:
        entries = [entry for entry in entries if entry.get("id") == source_id]
        if not entries:
            raise ValueError(f"source ID is not registered in catalog.json: {source_id}")

    matches: list[dict[str, Any]] = []
    searched_sources: list[str] = []
    needle = query.casefold()

    for entry in entries:
        stable_id = str(entry.get("id", ""))
        markdown_path = entry.get("markdown_path")
        if not stable_id or not isinstance(markdown_path, str):
            continue
        source_path = (repo_root / markdown_path).resolve()
        if not inside(source_path, repo_root) or not source_path.is_file():
            raise ValueError(f"invalid or missing canonical text path for {stable_id}: {markdown_path}")

        metadata_path = repo_root / "texts" / stable_id / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        searched_sources.append(stable_id)
        lines = source_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if needle not in line.casefold():
                continue
            start = max(0, index - context)
            end = min(len(lines), index + context + 1)
            matches.append(
                {
                    "source_id": stable_id,
                    "title_ko": entry.get("title_ko", ""),
                    "title_hanja": entry.get("title_hanja", ""),
                    "quality_status": metadata.get("quality_status", entry.get("quality_status", "unknown")),
                    "quality_note": metadata.get("quality_note", ""),
                    "path": markdown_path,
                    "line": index + 1,
                    "excerpt": "\n".join(lines[start:end]),
                }
            )
            if len(matches) > max_results:
                break
        if len(matches) > max_results:
            break

    truncated = len(matches) > max_results
    return {
        "query": query,
        "catalog_schema_version": catalog.get("schema_version"),
        "searched_sources": searched_sources,
        "match_count": min(len(matches), max_results),
        "truncated": truncated,
        "matches": matches[:max_results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Literal text to search for")
    parser.add_argument("--root", type=Path, default=default_repo_root(), help="Repository root")
    parser.add_argument("--source-id", help="Restrict search to one catalog source ID")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--context", type=int, default=0, help="Context lines before and after each match")
    args = parser.parse_args()

    try:
        result = search(args.query, args.root, args.source_id, args.max_results, args.context)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
