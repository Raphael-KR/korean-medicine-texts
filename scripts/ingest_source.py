#!/usr/bin/env python3
"""Ingest a public-domain source text file into the archive."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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

from chunk_corpus import write_chunks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RHWP = ROOT / "vendor" / "rhwp" / "target" / "release" / "rhwp"
SUPPORTED_SOURCE_EXTENSIONS = {".hwp", ".hwpx", ".doc", ".docx", ".txt", ".md"}
OBJECT_PLACEHOLDERS = {"\ufffc", "\ufffd"}
CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x30000, 0x3134F),
)


@dataclass(frozen=True)
class QualityReport:
    status: str
    passed: bool
    reasons: list[str]
    metrics: dict[str, int | float]


@dataclass(frozen=True)
class CleanupReport:
    body_start_pattern: str
    body_end_before_pattern: str
    removed_preface_lines: int
    removed_trailing_lines: int
    removed_editorial_note_lines: int
    removed_inline_note_refs: int
    korean_body_chars: int


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


def is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in CJK_RANGES)


def is_readable_text_char(char: str) -> bool:
    category = unicodedata.category(char)
    return category[0] in {"L", "N"} or is_cjk(char)


def evaluate_ai_readability(
    pages: list[tuple[str, str]],
    min_text_chars: int,
    max_placeholder_ratio: float,
    min_readable_ratio: float,
) -> QualityReport:
    body = "\n".join(text for _, text in pages)
    nonspace_chars = [char for char in body if not char.isspace()]
    nonspace_count = len(nonspace_chars)
    placeholder_count = sum(1 for char in nonspace_chars if char in OBJECT_PLACEHOLDERS)
    readable_count = sum(1 for char in nonspace_chars if is_readable_text_char(char))
    cjk_count = sum(1 for char in nonspace_chars if is_cjk(char) or "\uac00" <= char <= "\ud7a3")
    replacement_ratio = placeholder_count / nonspace_count if nonspace_count else 1.0
    readable_ratio = readable_count / nonspace_count if nonspace_count else 0.0

    reasons = []
    if readable_count < min_text_chars:
        reasons.append(f"readable text chars {readable_count} < minimum {min_text_chars}")
    if replacement_ratio > max_placeholder_ratio:
        reasons.append(
            f"object/replacement placeholder ratio {replacement_ratio:.3f} > maximum {max_placeholder_ratio:.3f}"
        )
    if readable_ratio < min_readable_ratio:
        reasons.append(f"readable character ratio {readable_ratio:.3f} < minimum {min_readable_ratio:.3f}")

    passed = not reasons
    status = "raw_converted" if passed else "needs_ocr"
    return QualityReport(
        status=status,
        passed=passed,
        reasons=reasons,
        metrics={
            "converted_page_count": len(pages),
            "nonspace_chars": nonspace_count,
            "readable_text_chars": readable_count,
            "cjk_or_hangul_chars": cjk_count,
            "object_placeholder_chars": placeholder_count,
            "object_placeholder_ratio": round(replacement_ratio, 6),
            "readable_char_ratio": round(readable_ratio, 6),
        },
    )


def fail_quality_gate(report: QualityReport) -> None:
    lines = [
        "Converted Markdown did not pass the AI-readable text quality gate.",
        "This file was not staged, committed, or pushed.",
        "",
        "Reasons:",
    ]
    lines.extend(f"- {reason}" for reason in report.reasons)
    lines.extend(
        [
            "",
            "Metrics:",
            json.dumps(report.metrics, ensure_ascii=False, indent=2),
            "",
            "Next step: use an OCR/text-source workflow, then ingest the corrected text.",
        ]
    )
    raise SystemExit("\n".join(lines))


def fail_cleanup_gate(report: CleanupReport) -> None:
    raise SystemExit(
        "\n".join(
            [
                "Cleaned Markdown did not pass the canonical source cleanup gate.",
                "This file was not staged, committed, or pushed.",
                "",
                f"Korean body chars remaining: {report.korean_body_chars}",
                "",
                "If this is expected, rerun without --reject-korean-body-text.",
            ]
        )
    )


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


def collapse_blank_lines(lines: list[str], max_blank_run: int = 2) -> list[str]:
    compacted = []
    blank_run = 0
    for line in lines:
        if not line:
            blank_run += 1
            if blank_run > max_blank_run:
                continue
        else:
            blank_run = 0
        compacted.append(line)
    return compacted


def clean_extracted_body(text: str) -> str:
    raw_lines = text.splitlines()
    lines = []
    idx = 0
    while idx < len(raw_lines):
        line = raw_lines[idx].rstrip()
        next_line = raw_lines[idx + 1].rstrip() if idx + 1 < len(raw_lines) else ""
        if re.fullmatch(r"\s*-\d{1,5}-\s*", line):
            idx += 1
            continue
        if re.fullmatch(r"\|\s*\|", line) and re.fullmatch(r"\|\s*-{3,}\s*\|", next_line):
            idx += 2
            continue
        lines.append(line)
        idx += 1

    return "\n".join(collapse_blank_lines(lines)).strip()


def find_pattern_line(lines: list[str], pattern: str, start: int = 0) -> int:
    regex = re.compile(pattern)
    for idx in range(start, len(lines)):
        if regex.search(lines[idx]):
            return idx
    raise SystemExit(f"pattern not found in converted Markdown: {pattern}")


def apply_body_range(text: str, body_start: str, body_end_before: str) -> tuple[str, int, int]:
    lines = text.splitlines()
    start_idx = 0
    if body_start:
        start_idx = find_pattern_line(lines, body_start)
    end_idx = len(lines)
    if body_end_before:
        end_idx = find_pattern_line(lines, body_end_before, start=start_idx)
    if start_idx >= end_idx:
        raise SystemExit("body range is empty after applying --body-start/--body-end-before")
    return "\n".join(lines[start_idx:end_idx]).strip(), start_idx, len(lines) - end_idx


def remove_editorial_notes(
    text: str,
    remove_note_lines: bool,
    remove_inline_note_refs: bool,
) -> tuple[str, int, int]:
    cleaned = []
    removed_note_lines = 0
    removed_inline_refs = 0
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if remove_note_lines and re.match(r"^\s*\d{1,4}\)\s+", line):
            removed_note_lines += 1
            continue
        if remove_inline_note_refs:
            line, count = re.subn(r"(?<![A-Za-z0-9])\d{1,4}\)", "", line)
            removed_inline_refs += count
            line = re.sub(r"[ \t]+([,.;:，。；：])", r"\1", line)
            line = re.sub(r"[ \t]{2,}", " ", line).rstrip()
        cleaned.append(line)
    return "\n".join(collapse_blank_lines(cleaned)).strip(), removed_note_lines, removed_inline_refs


def remove_korean_parenthetical_labels(text: str) -> str:
    return re.sub(r"(?m) \([가-힣]+[\s)]*$", "", text)


def count_hangul(text: str) -> int:
    return sum(1 for char in text if "\uac00" <= char <= "\ud7a3")


def cleanup_pages(
    pages: list[tuple[str, str]],
    body_start: str,
    body_end_before: str,
    remove_editorial_note_lines: bool,
    remove_inline_note_refs: bool,
    remove_korean_labels: bool,
) -> tuple[list[tuple[str, str]], CleanupReport]:
    cleaned_pages = []
    for _, text in pages:
        cleaned_body = clean_extracted_body(text)
        if cleaned_body:
            cleaned_pages.append(cleaned_body)
    body = "\n\n".join(cleaned_pages)
    body, removed_preface_lines, removed_trailing_lines = apply_body_range(body, body_start, body_end_before)
    removed_note_lines = 0
    removed_inline_refs = 0
    if remove_editorial_note_lines or remove_inline_note_refs:
        body, removed_note_lines, removed_inline_refs = remove_editorial_notes(
            body,
            remove_note_lines=remove_editorial_note_lines,
            remove_inline_note_refs=remove_inline_note_refs,
        )
    if remove_korean_labels:
        body = remove_korean_parenthetical_labels(body)
    body = "\n".join(collapse_blank_lines([line.rstrip() for line in body.splitlines()])).strip()
    report = CleanupReport(
        body_start_pattern=body_start,
        body_end_before_pattern=body_end_before,
        removed_preface_lines=removed_preface_lines,
        removed_trailing_lines=removed_trailing_lines,
        removed_editorial_note_lines=removed_note_lines,
        removed_inline_note_refs=removed_inline_refs,
        korean_body_chars=count_hangul(body),
    )
    return [("source.md", body)], report


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
    }
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", "", f"# {title}", ""])

    for _, body in pages:
        cleaned_body = clean_extracted_body(body)
        if not cleaned_body:
            continue
        lines.append(cleaned_body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def readme_markdown(title: str, source_rel: str, metadata: dict) -> str:
    source_path = metadata["source_path"]
    modern_note = metadata.get("modern_input_note") or "없음"
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
- Contains modern input notes: `{metadata.get("has_modern_input_notes", False)}`
- Modern input note: {modern_note}
- Quality status: `{metadata["quality_status"]}`
- Converted at: `{metadata["converted_at"]}`
- Conversion tool: `{metadata["conversion_tool"]}`
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
        "has_modern_input_notes": metadata.get("has_modern_input_notes", False),
        "modern_input_note": metadata.get("modern_input_note", ""),
        "quality_status": metadata["quality_status"],
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
        "| ID | 서명 | 한자 | 저자 | 시대 | 원본 형식 | 품질 | 원문 | Markdown |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in entries:
        lines.append(
            "| {id} | {title_ko} | {title_hanja} | {author} | {era} | {source_format} | {quality_status} | [{source_name}]({source_path}) | [source.md]({markdown_path}) |".format(
                id=item["id"],
                title_ko=item["title_ko"] or "",
                title_hanja=item["title_hanja"] or "",
                author=item["author"] or "",
                era=item["era"] or "",
                source_format=item["source_format"],
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
    parser.add_argument("--source-id", help="Stable source archive id. Defaults to --id.")
    parser.add_argument("--title", help="Document title. Defaults to input filename stem.")
    parser.add_argument("--title-ko", help="Korean title. Defaults to --title or input filename stem.")
    parser.add_argument("--title-hanja", default="", help="Hanja title, if known")
    parser.add_argument("--author", default="", help="Author/compiler, if known")
    parser.add_argument("--era", default="", help="Historical era or publication period, if known")
    parser.add_argument("--source-note", default="", help="Short provenance note for the source file")
    parser.add_argument(
        "--has-modern-input-notes",
        action="store_true",
        help="Mark that source.md includes modern input/editorial guide notes in addition to the classical text",
    )
    parser.add_argument(
        "--modern-input-note",
        default="",
        help="Short description of modern input/editorial guide notes included in the converted source",
    )
    parser.add_argument(
        "--rights-status",
        default="public_domain_classical_text",
        help="Rights status. This archive accepts only public-domain classical source texts.",
    )
    parser.add_argument("--license", default="Public Domain Mark 1.0", help="Data license/mark")
    parser.add_argument("--quality-status", default="raw_converted", help="raw_converted, reviewed, corrected, etc.")
    parser.add_argument("--body-start", default="", help="Regex for the first body line to keep")
    parser.add_argument("--body-end-before", default="", help="Regex for the first body line to exclude")
    parser.add_argument(
        "--remove-editorial-notes",
        action="store_true",
        help="Remove editorial note lines that start with numeric note markers, e.g. '1) 校釋作 ...'",
    )
    parser.add_argument(
        "--remove-inline-note-refs",
        action="store_true",
        help="Remove inline numeric note markers such as '1)' and '5)6)' from the body",
    )
    parser.add_argument(
        "--remove-korean-labels",
        action="store_true",
        help="Remove trailing Korean parenthetical labels in headings, e.g. '(질병'",
    )
    parser.add_argument(
        "--reject-korean-body-text",
        action="store_true",
        help="Fail if Hangul remains in the cleaned body text",
    )
    parser.add_argument("--skip-quality-gate", action="store_true", help="Allow ingest even when the AI-readability gate fails")
    parser.add_argument("--min-text-chars", type=int, default=500, help="Minimum readable letter/number/CJK chars")
    parser.add_argument(
        "--max-placeholder-ratio",
        type=float,
        default=0.02,
        help="Maximum ratio of object/replacement placeholder chars among non-space chars",
    )
    parser.add_argument(
        "--min-readable-ratio",
        type=float,
        default=0.25,
        help="Minimum ratio of readable letter/number/CJK chars among non-space chars",
    )
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
    source_id = make_id(args.source_id or text_id)
    if not source_id:
        raise SystemExit("--source-id must contain at least one ASCII letter or digit")
    title = unicodedata.normalize("NFC", args.title_ko or args.title or input_path.stem)

    source_name = unicodedata.normalize("NFC", input_path.name)
    source_dir = ROOT / "sources" / source_id
    text_dir = ROOT / "texts" / text_id
    source_target = source_dir / source_name

    cleanup_applied = any(
        [
            args.body_start,
            args.body_end_before,
            args.remove_editorial_notes,
            args.remove_inline_note_refs,
            args.remove_korean_labels,
            args.reject_korean_body_text,
        ]
    )
    cleanup_report = CleanupReport(
        body_start_pattern="",
        body_end_before_pattern="",
        removed_preface_lines=0,
        removed_trailing_lines=0,
        removed_editorial_note_lines=0,
        removed_inline_note_refs=0,
        korean_body_chars=0,
    )

    with tempfile.TemporaryDirectory(prefix="archive-ingest-") as tmp:
        tmp_text_dir = Path(tmp) / "text"
        raw_dir = tmp_text_dir / ".rhwp-raw"
        tmp_text_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        pages, asset_dirs, conversion_tool, info_stdout, info_stderr = convert_source(input_path, raw_dir, rhwp)
        if cleanup_applied:
            pages, cleanup_report = cleanup_pages(
                pages,
                body_start=args.body_start,
                body_end_before=args.body_end_before,
                remove_editorial_note_lines=args.remove_editorial_notes,
                remove_inline_note_refs=args.remove_inline_note_refs,
                remove_korean_labels=args.remove_korean_labels,
            )
            if args.reject_korean_body_text and cleanup_report.korean_body_chars:
                fail_cleanup_gate(cleanup_report)

        quality_report = evaluate_ai_readability(
            pages,
            min_text_chars=args.min_text_chars,
            max_placeholder_ratio=args.max_placeholder_ratio,
            min_readable_ratio=args.min_readable_ratio,
        )
        if not quality_report.passed and not args.skip_quality_gate:
            fail_quality_gate(quality_report)

        source_dir.mkdir(parents=True, exist_ok=True)
        clean_dir(text_dir)
        if input_path != source_target:
            shutil.copy2(input_path, source_target)
        body_text = "\n".join(text for _, text in pages)
        kept_asset_dirs = []
        for asset_dir in asset_dirs:
            if asset_dir not in body_text:
                continue
            shutil.move(str(tmp_text_dir / asset_dir), str(text_dir / asset_dir))
            kept_asset_dirs.append(asset_dir)
        asset_dirs = kept_asset_dirs

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
        "has_modern_input_notes": args.has_modern_input_notes,
        "modern_input_note": unicodedata.normalize("NFC", args.modern_input_note),
        "cleanup_applied": cleanup_applied,
        "cleanup": {
            "body_start_pattern": cleanup_report.body_start_pattern,
            "body_end_before_pattern": cleanup_report.body_end_before_pattern,
            "removed_preface_lines": cleanup_report.removed_preface_lines,
            "removed_trailing_lines": cleanup_report.removed_trailing_lines,
            "removed_editorial_note_lines": cleanup_report.removed_editorial_note_lines,
            "removed_inline_note_refs": cleanup_report.removed_inline_note_refs,
            "korean_body_chars": cleanup_report.korean_body_chars,
        },
        "rights_status": args.rights_status,
        "license": args.license,
        "quality_status": args.quality_status if quality_report.passed else quality_report.status,
        "quality_gate": {
            "passed": quality_report.passed,
            "status": quality_report.status,
            "reasons": quality_report.reasons,
            "metrics": quality_report.metrics,
            "thresholds": {
                "min_text_chars": args.min_text_chars,
                "max_placeholder_ratio": args.max_placeholder_ratio,
                "min_readable_ratio": args.min_readable_ratio,
            },
        },
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "conversion_tool": conversion_tool,
        "converted_page_count": len(pages) if input_path.suffix.lower() in {".hwp", ".hwpx"} else None,
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
    chunks_path = write_chunks(text_dir, metadata)

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
