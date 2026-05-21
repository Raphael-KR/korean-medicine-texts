# HWP GitHub Ingest

Use this skill when the user gives an HWP/HWPX file and wants it converted into the repository's Markdown archive, committed, pushed to GitHub, and returned as a link.

## Workflow

1. Confirm the workspace is the archive repository.
2. Ensure `rhwp` is available:
   - Prefer `RHWP_BIN` if set.
   - Otherwise use `vendor/rhwp/target/release/rhwp`.
   - If missing, run `./scripts/bootstrap_rhwp.sh`.
3. Run ingestion:

```bash
./scripts/ingest_hwp.py "/absolute/path/to/file.hwp" --commit --push
```

4. Return:
   - the generated `texts/<slug>/README.md` path
   - the GitHub URL printed by the script
   - any warnings from `rhwp`

## Rules

- Preserve the original file under `sources/<slug>/`.
- Do not edit normalized text in the same commit as ingestion unless the user explicitly asks.
- If `rhwp export-markdown` fails, report the error and keep the repository unchanged except for any files the script staged; inspect `git status` before deciding whether cleanup is needed.
- If the repository has no `origin` remote, stop after local conversion and tell the user that GitHub upload needs a remote.
- If the user only asks for conversion, omit `--commit --push`.
