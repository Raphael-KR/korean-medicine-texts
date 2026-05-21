#!/usr/bin/env python3
"""Ingest a public-domain source text file into the archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RHWP = ROOT / "vendor" / "rhwp" / "target" / "release" / "rhwp"
SUPPORTED_SOURCE_EXTENSIONS = {".hwp", ".hwpx", ".doc", ".docx", ".txt", ".md"}


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def make_id(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip()).lower()
    text_id = re.sub(r"[\s/\\:]+", "-", normalized)
    text_id = re.sub(r"[^0-9a-z._-]+", "", text_id)
    text_id = text_id.strip(".-_")
    return text_id


def default_text_id(path: Path) -> str:
    text_id = make_id(path.stem)
    if text_id:
        return text_id
    raise SystemExit(
        "A stable ASCII id is required for non-ASCII filenames. "
        "Example: --id donguibogam --title-ko 동의보감"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_log(text: str) -> str:
    return text.replace(str(ROOT), ".")


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


def read_text_source(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def convert_with_rhwp(source_target: Path, raw_dir: Path, rhwp: Path) -> tuple[list[tuple[str, str]], list[str], str, str, str]:
    info = run([str(rhwp), "info", str(source_target)], check=False)
    export = run([str(rhwp), "export-markdown", str(source_target), "-o", str(raw_dir)], check=False)
    if export.returncode != 0:
        sys.stderr.write(export.stdout)
        sys.stderr.write(export.stderr)
        raise SystemExit(export.returncode)

    pages = collect_markdown_pages(raw_dir)
    asset_dirs = move_assets(raw_dir, raw_dir.parent)
    if not pages:
        raise SystemExit("rhwp did not produce Markdown pages")
    return pages, asset_dirs, rhwp_version(rhwp), public_log(info.stdout.strip()), public_log(info.stderr.strip())


def convert_plain_text(source_target: Path) -> tuple[list[tuple[str, str]], list[str], str, str, str]:
    body = read_text_source(source_target).strip()
    return [(source_target.name, body)], [], "plain text passthrough", "", ""


def convert_markdown(source_target: Path) -> tuple[list[tuple[str, str]], list[str], str, str, str]:
    body = read_text_source(source_target).strip()
    return [(source_target.name, body)], [], "markdown passthrough", "", ""


def convert_with_textutil(source_target: Path) -> tuple[list[tuple[str, str]], list[str], str, str, str]:
    if not shutil.which("textutil"):
        raise SystemExit("textutil not found. .doc/.docx conversion is currently supported on macOS with textutil.")

    with tempfile.TemporaryDirectory(prefix="source-ingest-") as tmp:
        output = Path(tmp) / "source.txt"
        result = run(
            ["textutil", "-convert", "txt", "-encoding", "UTF-8", "-output", str(output), str(source_target)],
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(result.returncode)
        body = read_text_source(output).strip()
    return [(source_target.name, body)], [], "textutil txt conversion", "", ""


def convert_source(source_target: Path, raw_dir: Path, rhwp: Path | None) -> tuple[list[tuple[str, str]], list[str], str, str, str]:
    suffix = source_target.suffix.lower()
    if suffix in {".hwp", ".hwpx"}:
        if rhwp is None:
            raise SystemExit("rhwp is required for .hwp/.hwpx files")
        return convert_with_rhwp(source_target, raw_dir, rhwp)
    if suffix == ".txt":
        return convert_plain_text(source_target)
    if suffix == ".md":
        return convert_markdown(source_target)
    if suffix in {".doc", ".docx"}:
        return convert_with_textutil(source_target)
    raise SystemExit(f"unsupported source format: {suffix}")


def move_assets(raw_dir: Path, text_dir: Path) -> list[str]:
    moved = []
    for asset_dir in sorted(raw_dir.glob("*_assets")):
        target = text_dir / asset_dir.name
        shutil.move(str(asset_dir), str(target))
        moved.append(target.name)
    return moved


def source_markdown(title: str, source_rel: str, metadata: dict, pages: list[tuple[str, str]]) -> str:
    front_matter = {
        "id": metadata["id"],
        "title": title,
        "title_hanja": metadata["title_hanja"],
        "source": source_rel,
        "source_format": metadata["source_format"],
        "source_sha256": metadata["source_sha256"],
        "converted_at": metadata["converted_at"],
        "conversion_tool": metadata["conversion_tool"],
        "license": metadata["license"],
        "segment_count": len(pages),
    }
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", "", f"# {title}", ""])
    lines.append(f"- Source: [{Path(source_rel).name}]({source_rel})")
    lines.append(f"- License: `{metadata['license']}`")
    lines.append(f"- Conversion tool: `{metadata['conversion_tool']}`")
    lines.append("")

    for idx, (filename, body) in enumerate(pages, start=1):
        if metadata["source_format"] in {"hwp", "hwpx"}:
            lines.append(f"<!-- rhwp-page: {idx}; original-file: {filename} -->")
        else:
            lines.append(f"<!-- source-segment: {idx}; original-file: {filename} -->")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def readme_markdown(title: str, source_rel: str, metadata: dict) -> str:
    source_path = metadata["source_path"]
    segment_count = metadata["segment_count"]
    return f"""# {title}

- Canonical Markdown: [source.md](source.md)
- Original source file: [{Path(source_rel).name}]({source_rel})
- Stable ID: `{metadata["id"]}`
- Title in Hanja: {metadata["title_hanja"] or "미상"}
- Author: {metadata["author"] or "미상"}
- Era: {metadata["era"] or "미상"}
- Source archive path: `{source_path}`
- Source format: `{metadata["source_format"]}`
- Source SHA-256: `{metadata["source_sha256"]}`
- Rights status: `{metadata["rights_status"]}`
- License: `{metadata["license"]}`
- Quality status: `{metadata["quality_status"]}`
- Converted at: `{metadata["converted_at"]}`
- Conversion tool: `{metadata["conversion_tool"]}`
- Source segments: {segment_count}
"""


def catalog_entry(metadata: dict) -> dict:
    source_path = metadata["source_path"]
    return {
        "id": metadata["id"],
        "title_ko": metadata["title_ko"],
        "title_hanja": metadata["title_hanja"],
        "author": metadata["author"],
        "era": metadata["era"],
        "source_path": source_path,
        "source_format": metadata.get("source_format", Path(source_path).suffix.lower().lstrip(".")),
        "markdown_path": f"texts/{metadata['id']}/source.md",
        "rights_status": metadata["rights_status"],
        "license": metadata["license"],
        "quality_status": metadata["quality_status"],
        "segment_count": metadata.get("segment_count", metadata.get("page_count")),
    }


def update_catalog() -> None:
    entries = []
    for metadata_path in sorted((ROOT / "texts").glob("*/metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "id" in metadata:
            entries.append(catalog_entry(metadata))
    entries.sort(key=lambda item: item["id"])

    catalog = {
        "schema_version": 1,
        "description": "Public-domain Korean medicine source texts converted to AI-readable Markdown.",
        "texts": entries,
    }
    (ROOT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# 수록 문헌 목록",
        "",
        "| ID | 서명 | 한자 | 저자 | 시대 | 원본 형식 | 품질 | 구간 | 원문 | Markdown |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in entries:
        lines.append(
            "| {id} | {title_ko} | {title_hanja} | {author} | {era} | {source_format} | {quality_status} | {segment_count} | [{source_name}]({source_path}) | [source.md]({markdown_path}) |".format(
                id=item["id"],
                title_ko=item["title_ko"] or "",
                title_hanja=item["title_hanja"] or "",
                author=item["author"] or "",
                era=item["era"] or "",
                source_format=item["source_format"],
                segment_count=item["segment_count"],
                quality_status=item["quality_status"],
                source_name=Path(item["source_path"]).name,
                source_path=item["source_path"],
                markdown_path=item["markdown_path"],
            )
        )
    (ROOT / "CATALOG.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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


def rhwp_version(rhwp: Path) -> str:
    result = run([str(rhwp), "--version"], check=False)
    version = result.stdout.strip() or result.stderr.strip()
    return version or "rhwp unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a public-domain source text to a Markdown archive entry.")
    parser.add_argument("input", help="Input source file: .hwp, .hwpx, .doc, .docx, .txt, or .md")
    parser.add_argument("--id", help="Stable ASCII text id, e.g. donguibogam")
    parser.add_argument("--title", help="Document title. Defaults to input filename stem.")
    parser.add_argument("--title-ko", help="Korean title. Defaults to --title or input filename stem.")
    parser.add_argument("--title-hanja", default="", help="Hanja title, if known")
    parser.add_argument("--author", default="", help="Author/compiler, if known")
    parser.add_argument("--era", default="", help="Historical era or publication period, if known")
    parser.add_argument("--source-note", default="", help="Short provenance note for the source file")
    parser.add_argument(
        "--rights-status",
        default="public_domain_classical_text",
        help="Rights status. This archive accepts only public-domain classical source texts.",
    )
    parser.add_argument("--license", default="Public Domain Mark 1.0", help="Data license/mark")
    parser.add_argument("--quality-status", default="raw_converted", help="raw_converted, reviewed, corrected, etc.")
    parser.add_argument("--rhwp-bin", help="Path to rhwp binary")
    parser.add_argument("--stage", action="store_true", help="Stage the ingested files with git add")
    parser.add_argument("--commit", action="store_true", help="Create a git commit for the ingested document")
    parser.add_argument("--push", action="store_true", help="Push the current branch after committing/staging")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"input file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_EXTENSIONS))
        raise SystemExit(f"input must be one of: {supported}")

    rhwp = resolve_rhwp(args.rhwp_bin) if input_path.suffix.lower() in {".hwp", ".hwpx"} else None
    text_id = args.id or default_text_id(input_path)
    text_id = make_id(text_id)
    if not text_id:
        raise SystemExit("--id must contain at least one ASCII letter or digit")
    title = unicodedata.normalize("NFC", args.title_ko or args.title or input_path.stem)

    source_dir = ROOT / "sources" / text_id
    text_dir = ROOT / "texts" / text_id
    raw_dir = text_dir / ".rhwp-raw"
    source_dir.mkdir(parents=True, exist_ok=True)
    clean_dir(text_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_name = unicodedata.normalize("NFC", input_path.name)
    source_target = source_dir / source_name
    if input_path != source_target:
        shutil.copy2(input_path, source_target)

    pages, asset_dirs, conversion_tool, info_stdout, info_stderr = convert_source(source_target, raw_dir, rhwp)
    shutil.rmtree(raw_dir, ignore_errors=True)
    if not pages:
        raise SystemExit("conversion did not produce Markdown content")

    metadata = {
        "id": text_id,
        "title": title,
        "title_ko": title,
        "title_hanja": unicodedata.normalize("NFC", args.title_hanja),
        "author": unicodedata.normalize("NFC", args.author),
        "era": unicodedata.normalize("NFC", args.era),
        "source_path": source_target.relative_to(ROOT).as_posix(),
        "source_format": input_path.suffix.lower().lstrip("."),
        "source_sha256": sha256_file(source_target),
        "source_note": unicodedata.normalize("NFC", args.source_note),
        "rights_status": args.rights_status,
        "license": args.license,
        "quality_status": args.quality_status,
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "conversion_tool": conversion_tool,
        "segment_count": len(pages),
        "page_count": len(pages) if source_target.suffix.lower() in {".hwp", ".hwpx"} else None,
        "asset_dirs": asset_dirs,
        "conversion_info_stdout": info_stdout,
        "conversion_info_stderr": info_stderr,
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
    update_catalog()

    changed_paths = [
        source_target.relative_to(ROOT).as_posix(),
        text_dir.relative_to(ROOT).as_posix(),
        "CATALOG.md",
        "catalog.json",
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
