# Corpus Contract

## Authority Chain

Use the repository in this order:

1. `catalog.json` — canonical registry of available works and stable IDs
2. `texts/<stable-id>/metadata.json` — rights, conversion, quality, and known-issue metadata
3. `texts/<stable-id>/source.md` — canonical AI-readable classical text
4. `texts/<stable-id>/collation.md` — suspected defects and source-collation history
5. `sources/<stable-id>/` — original conversion input when source comparison is required

Do not treat a title recalled from model knowledge as present in the corpus. Confirm it in `catalog.json`.

## Search Procedure

1. Search exact Korean, Hanja, and common variant forms separately.
2. Use `scripts/search_corpus.py` for structured matches or `rg -n` for exploratory search.
3. Open the matched lines with surrounding context. A keyword hit alone is not a verified quotation.
4. Read the work's `metadata.json`. Record `quality_status`, `quality_note`, and relevant `known_issues`.
5. Check `collation.md` for the matched area or expression.
6. Cite the stable ID, title, repository-relative `source.md` path, and 1-based line number.

If no match is found, list the query variants and source IDs searched. Say “not found in the searched corpus,” not “does not exist.”

## Quality Interpretation

- `raw_converted`: usable for discovery, but quotations require explicit conversion-status disclosure and source comparison when a character-level reading matters.
- `needs_ocr`: do not use as reliable quotation evidence without checking a better witness.
- `reviewed`: some or all source comparison has occurred; inspect its scope.
- `corrected`: corrections were applied; still preserve edition and locator context.

A passed readability gate means the text is machine-readable. It does not establish textual accuracy.

## Boundaries

- This repository contains public-domain classical source texts, not modern clinical papers or guidelines.
- Do not add copyrighted modern books, translations, papers, or private clinical material to this repository.
- Do not describe the corpus as a vector database or claim semantic retrieval unless an actual index and retrieval result exist.
- If a future `chunks/` directory exists, inspect its schema before citing chunk IDs. Do not infer them from headings or line ranges.
