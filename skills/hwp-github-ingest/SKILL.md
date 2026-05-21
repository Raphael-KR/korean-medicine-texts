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

5. Return:
   - the generated `texts/<id>/source.md` path
   - the GitHub URL printed by the script
   - any warnings from `rhwp`

## Rules

- Preserve the original file under `sources/<id>/`.
- Do not edit normalized text in the same commit as ingestion unless the user explicitly asks.
- If conversion fails, report the error and keep the repository unchanged except for any files the script staged; inspect `git status` before deciding whether cleanup is needed.
- If the repository has no `origin` remote, stop after local conversion and tell the user that GitHub upload needs a remote.
- If the user only asks for conversion, omit `--commit --push`.
