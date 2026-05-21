#!/usr/bin/env python3
"""Batch-ingest HWP/HWPX files from inbox/raw."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox" / "raw"
PROCESSED = ROOT / "inbox" / "processed"
INGEST = ROOT / "scripts" / "ingest_hwp.py"
MANIFEST = INBOX / "manifest.json"


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-ingest files from inbox/raw.")
    parser.add_argument("--commit", action="store_true", help="Create one git commit for all converted files")
    parser.add_argument("--push", action="store_true", help="Push the current branch after committing")
    parser.add_argument("--rhwp-bin", help="Path to rhwp binary")
    args = parser.parse_args()

    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    files = sorted([*INBOX.glob("*.hwp"), *INBOX.glob("*.hwpx")])
    if not files:
        print(f"No HWP/HWPX files found in {INBOX}")
        return 0

    PROCESSED.mkdir(parents=True, exist_ok=True)

    converted: list[Path] = []
    for path in files:
        cmd = [str(INGEST), str(path), "--stage"]
        item = manifest.get(path.name, {})
        option_map = {
            "id": "--id",
            "title_ko": "--title-ko",
            "title_hanja": "--title-hanja",
            "author": "--author",
            "era": "--era",
            "source_note": "--source-note",
            "rights_status": "--rights-status",
            "license": "--license",
            "quality_status": "--quality-status",
        }
        for key, option in option_map.items():
            value = item.get(key)
            if value:
                cmd.extend([option, str(value)])
        if args.rhwp_bin:
            cmd.extend(["--rhwp-bin", args.rhwp_bin])
        print(f"Converting: {path.name}")
        result = run(cmd, check=False)
        if result.returncode != 0:
            print(f"Failed: {path.name}")
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
        run(["git", "commit", "-m", f"Add converted HWP archives: {names}{suffix}"])

    if args.push:
        run(["git", "push", "-u", "origin", current_branch()])

    print(f"Converted {len(converted)} file(s).")
    print("Archive root: texts/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
