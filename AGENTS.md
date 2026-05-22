# Repository Instructions

## graphify

- `graphify` (`~/.Codex/skills/graphify/SKILL.md`) - any input to knowledge graph.
- Trigger: `/graphify`
- When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

## 원문 변환/커밋/푸시 운영 원칙

1. `inbox/raw`의 `.hwp`, `.hwpx`, `.doc`, `.docx`, `.txt`, `.md` 파일을 확인한다.
2. 가능하면 `.hwp`보다 한컴오피스에서 변환한 `.hwpx`를 우선 사용한다.
3. `inbox/raw/manifest.json`이 있으면 그 메타데이터를 사용한다.
4. 변환은 저장소의 `scripts/ingest_folder.py` 또는 `scripts/ingest_source.py`를 사용한다.
5. 변환 결과를 변환 자료의 로컬 위치와 함께 답변하고, 사용자가 변환 품질을 QC할 수 있도록 이후 진행을 멈춘다.
6. 사용자가 QC 통과를 명시한 뒤에만 이후 stage, commit, push 절차를 진행한다.
7. 변환 직후 AI-readable 품질 게이트를 반드시 확인한다.
8. 품질 게이트 실패 자료는 커밋/푸시하지 말고, 실패 이유와 필요한 후속 조치를 알려준다.
9. AI-readable 품질 게이트와 사용자 QC를 모두 통과한 자료만 stage, commit, push 한다.
10. 처리 완료된 원본은 `inbox/processed`로 이동되었는지 확인한다.
11. 작업 후 `git status`가 깨끗한지 확인한다.
12. 최종 답변에는 변환된 문헌, 품질 게이트 결과, 변환 자료의 로컬 위치, GitHub 링크, 커밋 해시를 알려준다.
