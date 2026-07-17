---
name: ground-hanmedicine-answers
description: Produce source-grounded Korean medicine answers, classical-text checks, and clinician-facing evidence briefs using this repository's canonical corpus with explicit provenance, uncertainty, and safety controls. Use for Korean medicine or traditional East Asian medicine questions involving classical passages, formula provenance, herbal medicine, acupuncture, treatment evidence, differential considerations, citation verification, RAG-grounded synthesis, or comparison with conventional medicine.
---

# Ground Hanmedicine Answers

Ground material claims in retrievable evidence, preserve provenance, and separate historical doctrine from modern clinical-effect evidence. Never let a response template override the user's requested scope.

## Workflow

1. Read `references/intent-routing.md` and classify the request. Apply exclusions and negation before keyword matches.
2. For classical-text claims, read `references/corpus-contract.md` and search this repository before relying on model knowledge.
3. Read `references/evidence-policy.md` for factual, historical, efficacy, or safety claims.
4. Read `references/safety-rules.md` for patient-specific, treatment, dosing, interaction, pregnancy, pediatric, geriatric, or urgent-symptom questions.
5. For treatment-oriented work, read only the relevant section of `references/treatment-modules.md`.
6. Collect evidence before drafting. Record exact source identity and location during retrieval.
7. Draft using `references/output-contract.md`. Omit irrelevant sections instead of forcing a clinical template.
8. When the answer is saved as Markdown, run `python3 scripts/validate_brief.py <draft.md>` from this skill directory. Resolve errors and review warnings before delivery.

## Corpus Retrieval

From this skill directory, use:

```bash
python3 scripts/search_corpus.py "검색어"
python3 scripts/search_corpus.py "검색어" --source-id donguibogam --context 1
```

The search output is retrieval evidence, not proof that the matched passage has been collated or clinically validated. Open every passage used in the answer and inspect its adjacent context, `metadata.json`, and `collation.md`.

## Non-negotiable Rules

- Never invent a citation, quotation, document identifier, effect size, treatment rate, dosage, or retrieval result.
- Never claim that a database, vector store, or RAG system was searched unless a current tool result proves it.
- Treat `catalog.json` as the corpus registry and `texts/<stable-id>/source.md` as the canonical local text.
- Preserve source ID, title, repository-relative path, and exact line number for local quotations.
- Report `quality_status` and relevant `known_issues`; do not silently repair suspected transcription errors.
- Treat classical texts as evidence of historical doctrine, not proof of modern clinical efficacy.
- Keep study results attached to their population, intervention, comparator, outcome, and follow-up period.
- Prefer “not found in the searched sources” over asserting nonexistence.
- Do not expose private patient information in searches, files, logs, or citations.
- Do not add treatments, formulas, doses, or procedures when the user asked only for history, terminology, translation, literature verification, or architecture analysis.

## Completion Gate

Before answering, verify that:

- every direct quotation was opened and checked against the cited source;
- every local quotation includes a stable source ID, repository path, and line number;
- the source's quality status and relevant collation risk are disclosed;
- every clinical number has an adjacent modern source and outcome definition;
- historical doctrine, modern evidence, guidance, and inference remain distinct;
- missing evidence and unsearched sources are explicit;
- the final scope matches the request classification;
- urgent red flags and major contraindications are surfaced when relevant.

If these conditions cannot be met, provide a bounded evidence summary and state exactly what remains unverified.
