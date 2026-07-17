# Evidence Policy

## Authority Ladder

Choose the nearest authoritative source that satisfies identity, completeness, currency, and scope.

1. Canonical classical text in this repository, trial record, full research paper, regulator notice, or official guideline
2. Systematic review or evidence synthesis with transparent methods
3. Professional society or public research-institute summary linked to primary evidence
4. Secondary educational material
5. Model knowledge, used only to form search terms or explicitly labeled hypotheses

For a repository classical text, record stable ID, title, `source.md` path, line number, quality status, and relevant collation issue. For modern research, record title, year, design, population, intervention, comparator, outcome, follow-up, and DOI/URL when available.

## Evidence Classes

- **Historical doctrine:** what a classical source states.
- **Mechanistic evidence:** laboratory or physiological findings.
- **Clinical evidence:** patient outcomes from observational or interventional research.
- **Guidance:** recommendations from an accountable organization.
- **Inference:** reasoned synthesis not directly stated by a source.

Never present one class as another. A classical passage can establish provenance or historical doctrine; it cannot by itself establish present-day effectiveness or safety.

## Retrieval Record

Maintain these fields while researching:

- query and variants;
- source or database searched;
- search date for external sources;
- document identity;
- exact passage or result used;
- stable locator;
- quality status, relevance, and limitations.

Do not manufacture vector-store metadata. Include document IDs, chunk IDs, or similarity scores only when returned by an actual retrieval system.

## Numerical and Absence Claims

- Keep each result attached to its study and outcome definition.
- Prefer absolute event counts and confidence intervals when available.
- Do not combine unrelated response rates into a broad minimum–maximum range.
- Do not call symptom-score change a cure rate.
- If denominator, comparator, or follow-up is missing, do not repeat the percentage as a clinical claim.
- Use “not found in the sources searched” and disclose the search scope. Claim nonexistence only when an authoritative exhaustive source supports it.
