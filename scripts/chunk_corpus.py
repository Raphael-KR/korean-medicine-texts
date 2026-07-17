#!/usr/bin/env python3
"""Create reproducible, structure-aware retrieval chunks from canonical source Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_MAX_CHARS = 1_200
DEFAULT_MIN_CHARS = 280


@dataclass(frozen=True)
class Boundary:
    level: int
    title: str


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def source_body_start(lines: list[str]) -> int:
    if lines and lines[0] == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line == "---":
                return index + 1
    return 0


def boundary_for(source_id: str, line: str) -> Boundary | None:
    stripped = line.strip()
    if not stripped:
        return None

    if source_id in {"huangdineijingsuwen", "huangdineijinglingshu"}:
        if re.fullmatch(r".+?(?:篇\s*)?第[一二三四五六七八九十百六]+(?:\([^)]*\))?", stripped):
            return Boundary(1, stripped)
        if re.fullmatch(r"第[一二三四五六七八九十百六]+章", stripped):
            return Boundary(2, stripped)
        return None

    if source_id == "donguibogam":
        if re.fullmatch(r"東醫寶鑑.+篇[卷券]之[一二三四五六七八九十]+", stripped):
            return Boundary(1, stripped)
        if re.fullmatch(r"\{[^{}]+\}", stripped):
            return Boundary(2, stripped[1:-1])
        if re.fullmatch(r"【[^【】]+】", stripped):
            return Boundary(3, stripped[1:-1])
        return None

    if source_id == "donguisusebowon":
        if re.fullmatch(r"(?:性命論|四端論|擴充論|臟腑論|醫源論|廣濟說|四象人辨證論)", stripped):
            return Boundary(1, stripped)
        if re.fullmatch(r"(?:[少太][陰陽]人.*(?:病論|泛論|處方)|張仲景.*方|(?:宋元明|元明|唐宋明).*方|新定.*方)", stripped):
            return Boundary(2, stripped)
        return None

    if source_id == "gyeongakjeonseo":
        if re.fullmatch(r"卷之[一二三四五六七八九十百]+\s+.+", stripped):
            return Boundary(1, stripped)
        if re.fullmatch(r".{2,30}(?:論|篇|辨|記|吟)(?:\s+[一二三四五六七八九十百六]+.*)?", stripped):
            return Boundary(2, stripped)
    return None


def profile_name(source_id: str) -> str:
    return {
        "huangdineijingsuwen": "neijing-pian-zhang-v1",
        "huangdineijinglingshu": "neijing-pian-zhang-v1",
        "donguibogam": "donguibogam-pyeon-gwon-hangmok-v1",
        "donguisusebowon": "donguisusebowon-pyeon-byeongjeung-v1",
        "gyeongakjeonseo": "gyeongakjeonseo-jip-gwon-hangmok-v1",
    }.get(source_id, "paragraph-fallback-v1")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_chunks(
    source_id: str,
    source_path: Path,
    source_sha256: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> list[dict]:
    """Split a canonical text on its documented structural markers, then size-bound it."""
    lines = source_path.read_text(encoding="utf-8").splitlines()
    start = source_body_start(lines)
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start < len(lines) and lines[start].startswith("# "):
        start += 1
        while start < len(lines) and not lines[start].strip():
            start += 1
    if source_id == "gyeongakjeonseo":
        first_volume_positions = [
            index
            for index, line in enumerate(lines[start:], start=start)
            if re.fullmatch(r"卷之一\s+.+", line.strip())
        ]
        if len(first_volume_positions) > 1:
            start = first_volume_positions[1]
    headings: list[str] = []
    sections: list[tuple[list[str], int, int, list[str]]] = []
    buffer: list[str] = []
    buffer_start = start + 1
    seen_body_boundary = False

    def flush() -> None:
        nonlocal buffer, buffer_start
        text = "\n".join(buffer).strip()
        if text:
            first = next((idx for idx, value in enumerate(buffer) if value.strip()), 0)
            last = len(buffer) - 1 - next((idx for idx, value in enumerate(reversed(buffer)) if value.strip()), 0)
            sections.append((headings.copy(), buffer_start + first, buffer_start + last, buffer[first : last + 1]))
        buffer = []

    for zero_index in range(start, len(lines)):
        line = lines[zero_index]
        boundary = boundary_for(source_id, line)
        if boundary:
            # Some HWP conversions repeat running headers on each page. Repeated current
            # headings are content noise, not new semantic sections.
            if boundary.title in headings and headings[-1] == boundary.title:
                buffer.append(line)
                continue
            flush()
            headings = headings[: boundary.level - 1]
            headings.append(boundary.title)
            buffer_start = zero_index + 2
            seen_body_boundary = True
            continue
        buffer.append(line)
    flush()

    chunks: list[dict] = []
    for section_headings, line_start, line_end, section_lines in sections:
        current: list[str] = []
        current_start = line_start
        for offset, line in enumerate(section_lines):
            candidate = "\n".join([*current, line]).strip()
            if current and len(candidate) > max_chars:
                chunks.append(_chunk(source_id, source_sha256, section_headings, current_start, line_start + offset - 1, current))
                current = []
                current_start = line_start + offset
            current.append(line)
        if current:
            if chunks and len("\n".join(current).strip()) < min_chars and chunks[-1]["headings"] == section_headings:
                previous = chunks.pop()
                merged_start = previous["line_start"]
                merged = lines[merged_start - 1 : line_end]
                chunks.append(_chunk(source_id, source_sha256, section_headings, merged_start, line_end, merged))
            else:
                chunks.append(_chunk(source_id, source_sha256, section_headings, current_start, line_end, current))

    for number, chunk in enumerate(chunks, start=1):
        chunk["chunk_id"] = f"{source_id}:{number:05d}"
    return chunks


def _chunk(source_id: str, source_sha256: str, headings: list[str], line_start: int, line_end: int, lines: list[str]) -> dict:
    chunk_lines = list(lines)
    while chunk_lines and not chunk_lines[0].strip():
        chunk_lines.pop(0)
        line_start += 1
    while chunk_lines and not chunk_lines[-1].strip():
        chunk_lines.pop()
        line_end -= 1
    if not chunk_lines:
        raise ValueError("cannot create an empty retrieval chunk")
    text = "\n".join(chunk_lines)
    return {
        "schema_version": SCHEMA_VERSION,
        "chunk_id": "",
        "source_id": source_id,
        "source_sha256": source_sha256,
        "chunking_profile": profile_name(source_id),
        "headings": headings,
        "line_start": line_start,
        "line_end": line_end,
        "text": text,
        "content_sha256": content_hash(text),
    }


def write_chunks(text_dir: Path, metadata: dict) -> Path:
    source_path = text_dir / "source.md"
    chunks = make_chunks(metadata["id"], source_path, metadata["source_sha256"])
    if not chunks:
        raise ValueError(f"no retrieval chunks created for {source_path}")
    output = text_dir / "chunks.jsonl"
    output.write_text("".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-id", action="append", help="Rebuild only one source ID; repeatable")
    args = parser.parse_args()
    root = args.root.resolve()
    requested = set(args.source_id or [])
    for metadata_path in sorted((root / "texts").glob("*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if requested and metadata["id"] not in requested:
            continue
        output = write_chunks(metadata_path.parent, metadata)
        print(output.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
