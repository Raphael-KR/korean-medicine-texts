# Structure-Aware Source Text Ingest

Use this skill to convert a public-domain classical source into the repository's canonical Markdown and reproducible retrieval chunks. It does **not** create embeddings, a vector database, or a claim of semantic search by itself.

## Output Contract

For each accepted source ID, create and keep together:

- `sources/<source-id>/<original>.*` — immutable public source input
- `texts/<id>/source.md` — canonical text; never replace it with normalized or inferred text
- `texts/<id>/metadata.json` — provenance, rights, quality gate, and known issues
- `texts/<id>/chunks.jsonl` — derived retrieval units with a stable ID, source digest, heading path, exact source line range, text, and content digest

`chunks.jsonl` is Git-tracked and rebuilt whenever `source.md` changes. Vector indexes are environment-specific derived artifacts and must not be committed.

## Workflow

1. Confirm the archive workspace, public-domain status, and clean separation from unrelated user changes.
2. Prefer HWPX over HWP. Use `RHWP_BIN` or `vendor/rhwp/target/release/rhwp` for HWP/HWPX; use macOS `textutil` for DOC/DOCX.
3. Ingest locally without staging or publishing:

```bash
./scripts/ingest_source.py "/absolute/path/to/file.hwpx" --id stable-id
```

4. Require the AI-readable gate to pass. It checks readable text volume, replacement/object placeholders, and readable-character ratio. On failure, stop and request OCR or a better source.
5. Build and inspect structure-aware chunks:

```bash
python3 scripts/chunk_corpus.py --source-id stable-id
```

   - Prefer documented work structure: e.g. 篇→章 for 《內經》, 篇→卷→항목 for 《東醫寶鑑》, and 集→卷→항목 for 《景岳全書》.
   - Treat page boundaries and page count as conversion provenance only, never semantic segment boundaries.
   - If a structure marker cannot be matched or conflicts with the converted text, record it as `needs_structure_review`; do not invent a heading.
6. Report the local `source.md`, `chunks.jsonl`, quality-gate result, chunk count/profile, and conversion warnings. **Stop for explicit user QC.**
7. Only after the user says QC passed: stage, commit, push, and then confirm processed-original handling under the repository rules.

## Rules

- Every retrieval result must retain its `chunk_id`, `source_id`, `source_sha256`, `line_start`, and `line_end`; a chunk is a locator, not proof of textual accuracy.
- Keep source collation separate from ingestion. Record uncertain conversion text in `known_issues`/`collation.md`; never guess-correct canonical text.
- Do not claim a vector store, semantic retrieval, or embedding search unless a separate, actual index and query result exist.
- Do not stage, commit, push, or move the inbox original before the required user QC passes.
