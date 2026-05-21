#!/usr/bin/env python3
"""Ingest an HWP/HWPX file into a GitHub-friendly Markdown archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RHWP = ROOT / "vendor" / "rhwp" / "target" / "release" / "rhwp"


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def slugify(path: Path) -> str:
    stem = unicodedata.normalize("NFC", path.stem.strip())
    slug = re.sub(r"[\s/\\:]+", "-", stem)
    slug = re.sub(r"[^0-9A-Za-z가-힣._-]+", "", slug)
    slug = slug.strip(".-_")
    return slug or "untitled"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_rhwp(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("RHWP_BIN"):
        candidates.append(Path(os.environ["RHWP_BIN"]))
    candidates.append(DEFAULT_RHWP)
    found = shutil.which("rhwp")
    if found:
        candidates.append(Path(found))

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate.resolve()

    raise SystemExit(
        "rhwp binary not found. Run ./scripts/bootstrap_rhwp.sh or set RHWP_BIN=/path/to/rhwp"
    )


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def move_markdown_output(raw_dir: Path, pages_dir: Path) -> list[Path]:
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_files = sorted(raw_dir.glob("*.md"))
    moved = []
    for page in page_files:
        target = pages_dir / page.name
        shutil.move(str(page), str(target))
        text = target.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\]\(([^)]+_assets/[^)]+)\)", r"](../\1)", text)
        target.write_text(text, encoding="utf-8")
        moved.append(target)
    for asset_dir in sorted(raw_dir.glob("*_assets")):
        shutil.move(str(asset_dir), str(pages_dir.parent / asset_dir.name))
    return moved


def combined_markdown(title: str, source_rel: str, metadata: dict, pages: list[Path], base: Path) -> str:
    front_matter = {
        "title": title,
        "source": source_rel,
        "source_sha256": metadata["source_sha256"],
        "converted_at": metadata["converted_at"],
        "converter": metadata["converter"],
        "page_count": len(pages),
    }
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", "", f"# {title}", ""])
    lines.append(f"- Source: [{Path(source_rel).name}]({source_rel})")
    lines.append(f"- Converter: `{metadata['converter']}`")
    lines.append("")

    for idx, page in enumerate(pages, start=1):
        rel_page = page.relative_to(base).as_posix()
        body = page.read_text(encoding="utf-8", errors="replace").strip()
        body = body.replace("](../", "](")
        lines.append(f"## Page {idx}")
        lines.append("")
        lines.append(f"Source page file: [{page.name}]({rel_page})")
        lines.append("")
        if body:
            lines.append(body)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def github_base_url() -> str | None:
    result = run(["git", "remote", "get-url", "origin"], check=False)
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        repo = remote.removeprefix("git@github.com:").removesuffix(".git")
    elif remote.startswith("https://github.com/"):
        repo = remote.removeprefix("https://github.com/").removesuffix(".git")
    else:
        return None
    return f"https://github.com/{repo}"


def current_branch() -> str:
    result = run(["git", "branch", "--show-current"])
    return result.stdout.strip() or "master"


def github_blob_url(path: Path) -> str | None:
    base = github_base_url()
    if not base:
        return None
    rel = path.relative_to(ROOT).as_posix()
    return f"{base}/blob/{quote(current_branch(), safe='')}/{quote(rel, safe='/')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert HWP/HWPX to Markdown archive entries.")
    parser.add_argument("input", help="Input .hwp or .hwpx file")
    parser.add_argument("--title", help="Document title. Defaults to input filename stem.")
    parser.add_argument("--slug", help="Output slug. Defaults to a sanitized filename stem.")
    parser.add_argument("--rhwp-bin", help="Path to rhwp binary")
    parser.add_argument("--stage", action="store_true", help="Stage the ingested files with git add")
    parser.add_argument("--commit", action="store_true", help="Create a git commit for the ingested document")
    parser.add_argument("--push", action="store_true", help="Push the current branch after committing/staging")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"input file not found: {input_path}")
    if input_path.suffix.lower() not in {".hwp", ".hwpx"}:
        raise SystemExit("input must be a .hwp or .hwpx file")

    rhwp = resolve_rhwp(args.rhwp_bin)
    slug = args.slug or slugify(input_path)
    title = args.title or input_path.stem

    source_dir = ROOT / "sources" / slug
    text_dir = ROOT / "texts" / slug
    raw_dir = text_dir / ".rhwp-raw"
    pages_dir = text_dir / "pages"
    source_dir.mkdir(parents=True, exist_ok=True)
    clean_dir(text_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_target = source_dir / input_path.name
    shutil.copy2(input_path, source_target)

    info = run([str(rhwp), "info", str(source_target)], check=False)
    export = run([str(rhwp), "export-markdown", str(source_target), "-o", str(raw_dir)], check=False)
    if export.returncode != 0:
        sys.stderr.write(export.stdout)
        sys.stderr.write(export.stderr)
        return export.returncode

    pages = move_markdown_output(raw_dir, pages_dir)
    shutil.rmtree(raw_dir, ignore_errors=True)
    if not pages:
        raise SystemExit("rhwp did not produce Markdown pages")

    metadata = {
        "title": title,
        "slug": slug,
        "source_path": source_target.relative_to(ROOT).as_posix(),
        "source_sha256": sha256_file(source_target),
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "converter": f"rhwp ({rhwp})",
        "rhwp_info_stdout": info.stdout.strip(),
        "rhwp_info_stderr": info.stderr.strip(),
    }

    metadata_path = text_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_path = text_dir / "README.md"
    source_rel = os.path.relpath(source_target, text_dir).replace(os.sep, "/")
    readme_path.write_text(
        combined_markdown(title, source_rel, metadata, pages, text_dir),
        encoding="utf-8",
    )

    changed_paths = [
        source_target.relative_to(ROOT).as_posix(),
        text_dir.relative_to(ROOT).as_posix(),
    ]
    if args.stage or args.commit:
        run(["git", "add", *changed_paths])

    if args.commit:
        run(["git", "commit", "-m", f"Add {title} markdown archive"])
    if args.push:
        run(["git", "push", "-u", "origin", current_branch()])

    print(f"Markdown archive: {readme_path.relative_to(ROOT)}")
    url = github_blob_url(readme_path)
    if url:
        print(f"GitHub URL: {url}")
    else:
        print("GitHub URL: unavailable until origin remote is configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
