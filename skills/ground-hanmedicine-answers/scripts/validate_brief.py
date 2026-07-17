#!/usr/bin/env python3
"""Validate a Markdown Korean medicine evidence brief for grounding failures."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


URL_RE = re.compile(r"https?://[^\s)>]+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
LOCAL_CITATION_RE = re.compile(r"texts/[a-z0-9_-]+/source\.md:\d+")
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
DOSE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|㎎|그램)\b", re.IGNORECASE)
UNSUPPORTED_RANGE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*[~～-]\s*\d+(?:\.\d+)?\s*%")


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def validate(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    has_modern_source = bool(URL_RE.search(text) or DOI_RE.search(text))

    if PERCENT_RE.search(text) and not has_modern_source:
        errors.append("Clinical percentage appears without any URL or DOI in the brief.")
    if DOSE_RE.search(text) and not has_modern_source:
        errors.append("Dose-like content appears without any URL or DOI in the brief.")

    for paragraph in paragraphs(text):
        if PERCENT_RE.search(paragraph) and not (URL_RE.search(paragraph) or DOI_RE.search(paragraph)):
            warnings.append("A percentage is not adjacent to a URL or DOI: " + paragraph[:120])
        if UNSUPPORTED_RANGE_RE.search(paragraph) and not any(
            term in paragraph for term in ("각 연구", "연구별", "이질성", "범위로 합산하지")
        ):
            warnings.append("A treatment-rate range may combine unlike outcomes: " + paragraph[:120])

    if re.search(r"(?:원문|고전|source\.md).*(?:인용|기재|말한다|기록)", text, re.IGNORECASE) and not LOCAL_CITATION_RE.search(text):
        warnings.append("A classical-text claim lacks a repository source.md line citation.")

    if LOCAL_CITATION_RE.search(text) and "quality" not in text.casefold() and "품질" not in text:
        warnings.append("A local corpus citation lacks an explicit quality-status disclosure.")

    if re.search(r"(?:반드시|확실히|완전히)\s*(?:치료|완치|예방)", text):
        warnings.append("Overconfident treatment language detected.")

    if re.search(r"(?:내부|자체)\s*(?:RAG|지식베이스|데이터베이스).*(?:검색|확인)", text, re.IGNORECASE) and not re.search(
        r"(?:문서|chunk|청크)\s*(?:ID|아이디)|유사도\s*점수|검색\s*기록", text, re.IGNORECASE
    ):
        warnings.append("A retrieval claim lacks document/chunk/search metadata.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="Markdown brief to validate")
    args = parser.parse_args()
    if not args.markdown.is_file():
        print(f"ERROR: file not found: {args.markdown}", file=sys.stderr)
        return 2

    errors, warnings = validate(args.markdown.read_text(encoding="utf-8"))
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARNING: {item}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASSED: 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
