#!/usr/bin/env python3
"""Batch-ingest public-domain source files from inbox/raw."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox" / "raw"
PROCESSED = ROOT / "inbox" / "processed"
INGEST = ROOT / "scripts" / "ingest_source.py"
MANIFEST = INBOX / "manifest.json"
SUPPORTED_SOURCE_EXTENSIONS = {".hwp", ".hwpx", ".doc", ".docx", ".txt", ".md"}


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True)


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip() or "master"


def add_ingest_options(cmd: list[str], item: dict, rhwp_bin: str | None) -> None:
    option_map = {
        "id": "--id",
        "source_id": "--source-id",
        "title_ko": "--title-ko",
        "title_hanja": "--title-hanja",
        "author": "--author",
        "era": "--era",
        "source_note": "--source-note",
        "modern_input_note": "--modern-input-note",
        "rights_status": "--rights-status",
        "license": "--license",
        "quality_status": "--quality-status",
        "body_start": "--body-start",
        "body_end_before": "--body-end-before",
    }
    for key, option in option_map.items():
        value = item.get(key)
        if value not in (None, ""):
            cmd.extend([option, str(value)])

    cleanup = item.get("cleanup", {})
    cleanup_option_map = {
        "body_start": "--body-start",
        "body_end_before": "--body-end-before",
    }
    for key, option in cleanup_option_map.items():
        value = cleanup.get(key)
        if value not in (None, "") and option not in cmd:
            cmd.extend([option, str(value)])

    if item.get("has_modern_input_notes"):
        cmd.append("--has-modern-input-notes")
    if cleanup.get("remove_preface"):
        if "body_start" not in item and cleanup.get("body_start") is None:
            raise SystemExit("cleanup.remove_preface requires body_start or cleanup.body_start")
    if cleanup.get("remove_editorial_notes"):
        cmd.append("--remove-editorial-notes")
    if cleanup.get("remove_inline_note_refs"):
        cmd.append("--remove-inline-note-refs")
    if cleanup.get("remove_korean_labels"):
        cmd.append("--remove-korean-labels")
    if cleanup.get("reject_korean_body_text"):
        cmd.append("--reject-korean-body-text")
    if rhwp_bin:
        cmd.extend(["--rhwp-bin", rhwp_bin])


def merged_item(parent: dict, split: dict) -> dict:
    merged = {key: value for key, value in parent.items() if key != "splits"}
    cleanup = {}
    if isinstance(parent.get("cleanup"), dict):
        cleanup.update(parent["cleanup"])
    if isinstance(split.get("cleanup"), dict):
        cleanup.update(split["cleanup"])
    merged.update(split)
    if cleanup:
        merged["cleanup"] = cleanup
    if parent.get("source_id") and "source_id" not in merged:
        merged["source_id"] = parent["source_id"]
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-ingest supported public-domain source files from inbox/raw.")
    parser.add_argument("--commit", action="store_true", help="Create one git commit for all converted files")
    parser.add_argument("--push", action="store_true", help="Push the current branch after committing")
    parser.add_argument("--rhwp-bin", help="Path to rhwp binary")
    args = parser.parse_args()

    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    files = sorted(path for path in INBOX.iterdir() if path.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS)
    if not files:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_EXTENSIONS))
        print(f"No supported source files found in {INBOX} ({supported})")
        return 0

    PROCESSED.mkdir(parents=True, exist_ok=True)

    converted: list[Path] = []
    for path in files:
        item = manifest.get(path.name, {})
        splits = item.get("splits") or [None]
        for split in splits:
            ingest_item = merged_item(item, split) if split else item
            cmd = [str(INGEST), str(path), "--stage"]
            add_ingest_options(cmd, ingest_item, args.rhwp_bin)
            label = ingest_item.get("id") or path.stem
            print(f"Converting: {path.name} -> {label}")
            result = run(cmd, check=False)
            if result.returncode != 0:
                print(f"Failed: {path.name} -> {label}")
                return result.returncode
        converted.append(path)

    for path in converted:
        target = PROCESSED / path.name
        if target.exists():
            target = PROCESSED / f"{path.stem}-{len(list(PROCESSED.glob(path.stem + '*')))}{path.suffix}"
        shutil.move(str(path), str(target))

    if args.commit:
        run(["git", "add", "inbox/processed"])
        names = ", ".join(path.stem for path in converted[:3])
        suffix = "" if len(converted) <= 3 else f" and {len(converted) - 3} more"
        run(["git", "commit", "-m", f"Add converted source archives: {names}{suffix}"])

    if args.push:
        run(["git", "push", "-u", "origin", current_branch()])

    print(f"Converted {len(converted)} file(s).")
    print("Archive root: texts/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
