# Intent Routing

Apply the first matching route. Evaluate negation before all keywords.

## 1. Meta or Architecture

Examples: RAG design, prompt analysis, database coverage, model comparison, product evaluation.

- Answer only the system or product question.
- Do not append diagnosis, treatment, or prescription material.

## 2. Classical Text, History, Terminology, or Translation

Examples: passage verification, formula provenance, author or edition questions, term comparison.

- Search the local corpus and follow `corpus-contract.md`.
- Separate transcription, translation, interpretation, and clinical extrapolation.
- Do not expand into clinical recommendations unless explicitly requested.

## 3. Modern Evidence Review

Examples: efficacy, safety, adverse events, interaction evidence, guideline comparison.

- Define PICO or the closest usable question.
- Search current primary or authoritative external sources when available.
- Report study-specific outcomes and limitations.
- Do not use the classical corpus as clinical-effect evidence.

## 4. Clinician-facing Treatment Brief

Use only when treatment planning is explicitly requested and the context indicates professional review.

- State missing assessment data before candidate options.
- Present options and evidence, not an autonomous final diagnosis or prescription.
- Read the matching treatment module and safety rules.

## 5. Public or Patient-facing Health Question

- Provide education, red flags, and questions to discuss with a licensed professional.
- Avoid individualized dosing, invasive procedure instructions, or claims that substitute for examination.

## Negation and Ambiguity

- “처방은 제시하지 마세요” → no formula, herb list, dose, or treatment table.
- “침 치료는 제외하고” → exclude acupuncture even if acupuncture terms appear elsewhere.
- “문헌만 확인해줘” → classical-text route, not treatment route.
- “이 처방이 실제 존재하는지만” → provenance verification only.

Choose the least interventionist route consistent with the request. Ask one concise question only when audience or clinical specificity materially changes the safe result.
