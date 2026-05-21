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


def collect_markdown_pages(raw_dir: Path) -> list[tuple[str, str]]:
    pages = []
    for page in sorted(raw_dir.glob("*.md")):
        text = page.read_text(encoding="utf-8", errors="replace").strip()
        pages.append((page.name, text))
    return pages


def move_assets(raw_dir: Path, text_dir: Path) -> list[str]:
    moved = []
    for asset_dir in sorted(raw_dir.glob("*_assets")):
        target = text_dir / asset_dir.name
        shutil.move(str(asset_dir), str(target))
        moved.append(target.name)
    return moved


def source_markdown(title: str, source_rel: str, metadata: dict, pages: list[tuple[str, str]]) -> str:
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

    for idx, (filename, body) in enumerate(pages, start=1):
        lines.append(f"<!-- rhwp-page: {idx}; original-file: {filename} -->")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def readme_markdown(title: str, source_rel: str, metadata: dict) -> str:
    source_path = metadata["source_path"]
    page_count = metadata["page_count"]
    return f"""# {title}

- Canonical Markdown: [source.md](source.md)
- Original HWP/HWPX: [{Path(source_rel).name}]({source_rel})
- Source archive path: `{source_path}`
- Source SHA-256: `{metadata["source_sha256"]}`
- Converted at: `{metadata["converted_at"]}`
- Converter: `{metadata["converter"]}`
- rhwp page markers: {page_count}
"""


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
    title = unicodedata.normalize("NFC", args.title or input_path.stem)

    source_dir = ROOT / "sources" / slug
    text_dir = ROOT / "texts" / slug
    raw_dir = text_dir / ".rhwp-raw"
    source_dir.mkdir(parents=True, exist_ok=True)
    clean_dir(text_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_name = unicodedata.normalize("NFC", input_path.name)
    source_target = source_dir / source_name
    if input_path != source_target:
        shutil.copy2(input_path, source_target)

    info = run([str(rhwp), "info", str(source_target)], check=False)
    export = run([str(rhwp), "export-markdown", str(source_target), "-o", str(raw_dir)], check=False)
    if export.returncode != 0:
        sys.stderr.write(export.stdout)
        sys.stderr.write(export.stderr)
        return export.returncode

    pages = collect_markdown_pages(raw_dir)
    asset_dirs = move_assets(raw_dir, text_dir)
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
        "page_count": len(pages),
        "asset_dirs": asset_dirs,
        "rhwp_info_stdout": info.stdout.strip(),
        "rhwp_info_stderr": info.stderr.strip(),
    }

    metadata_path = text_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_rel = os.path.relpath(source_target, text_dir).replace(os.sep, "/")
    source_md_path = text_dir / "source.md"
    source_md_path.write_text(
        source_markdown(title, source_rel, metadata, pages),
        encoding="utf-8",
    )

    readme_path = text_dir / "README.md"
    readme_path.write_text(
        readme_markdown(title, source_rel, metadata),
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

    print(f"Markdown archive: {source_md_path.relative_to(ROOT)}")
    url = github_blob_url(source_md_path)
    if url:
        print(f"GitHub URL: {url}")
    else:
        print("GitHub URL: unavailable until origin remote is configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
