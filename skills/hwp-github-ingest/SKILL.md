# Source Text GitHub Ingest

Use this skill when the user gives a public-domain classical source text file and wants it converted into the repository's Markdown archive, committed, pushed to GitHub, and returned as a link.

## Workflow

1. Confirm the workspace is the archive repository.
2. Ensure required converters are available:
   - Prefer `RHWP_BIN` if set.
   - For HWP/HWPX, otherwise use `vendor/rhwp/target/release/rhwp`.
   - If HWP/HWPX support is missing, run `./scripts/bootstrap_rhwp.sh`, which defaults to the upstream `edwardkim/rhwp` repository.
   - For DOC/DOCX, use macOS `textutil`.
3. Run ingestion:

```bash
./scripts/ingest_source.py "/absolute/path/to/file.hwp" --id stable-id --commit --push
```

4. The ingester runs an AI-readability quality gate before writing archive files or publishing:
   - enough readable Korean/Hanja/letter/number text must be present
   - object/replacement placeholders such as `￼` must remain below the threshold
   - if the gate fails, do not commit or push; report that OCR or a better text source is needed

5. After ingestion, run QC/Lint before publishing when requested:
   - remove clear conversion residue such as page comments, standalone page numbers, and image placeholder labels
   - record uncertain text problems in `metadata.json` as `known_issues`
   - do not guess-correct the canonical text

6. Keep source collation as a separate workflow:
   - prioritize suspected Hangul conversion errors embedded in Hanja body text
   - track these items in `texts/<id>/collation.md`
   - only update `source.md` after checking the original source or another reliable witness

7. Return:
   - the generated `texts/<id>/source.md` path
   - the GitHub URL printed by the script
   - any warnings from `rhwp`

## Rules

- Preserve the original file under `sources/<id>/`.
- Do not edit normalized text in the same commit as ingestion unless the user explicitly asks.
- Do not perform source collation in the ingestion commit. Use a separate commit for collation fixes and update `known_issues` plus `collation.md`.
- If conversion fails, report the error and keep the repository unchanged except for any files the script staged; inspect `git status` before deciding whether cleanup is needed.
- If the repository has no `origin` remote, stop after local conversion and tell the user that GitHub upload needs a remote.
- If the user only asks for conversion, omit `--commit --push`.
