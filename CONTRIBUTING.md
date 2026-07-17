# 기여 안내

이 프로젝트는 한의학 고전 원문을 AI가 읽기 좋은 공개 Markdown 아카이브로 만드는 작업입니다.

## 프로젝트 범위

이 저장소는 외부 AI/RAG 시스템이 소비할 수 있는 원문·메타데이터·구조 청크 지식베이스까지만 제공합니다. 검색 API/UI, 임베딩, 벡터 데이터베이스, 모델 서빙, reranker 또는 운영형 RAG 애플리케이션 구현은 기여 범위에 포함하지 않습니다. 관련 제안은 이 저장소 변경이 아니라 별도 소비 시스템의 과제로 분리해 주세요.

## 기여 가능한 자료

다음 조건을 모두 만족해야 합니다.

- 한의학 고전 원문
- 저작권이 소실된 자료
- 원본 파일도 공개 배포 가능한 자료
- 저작권이 살아 있는 책의 입력본, 역주본, 번역본, 해설본이 아닌 자료

## 비개발자 기여

GitHub 사용이 익숙하지 않다면 운영자에게 다음 정보를 전달해 주세요.

- 원본 파일
- 서명
- 한자 서명
- 저자 또는 편자
- 시대
- 출처 또는 파일 제공 경위
- 저작권 소실/공개 배포 가능 판단 근거

운영자가 변환, 검수, 업로드를 진행할 수 있습니다.

## GitHub Pull Request 기여

1. 저장소를 fork합니다.
2. 안정적인 ASCII ID를 정합니다. 예: `donguibogam`.
3. 원본 파일을 `sources/<id>/`에 추가합니다.
4. Markdown 원문을 `texts/<id>/source.md`에 추가합니다.
5. `texts/<id>/metadata.json`을 작성합니다.
6. `catalog.json`과 `CATALOG.md`를 갱신합니다.
7. Pull Request를 보냅니다.

## 원문대조 기여

원문대조 기여는 전체 본문을 모두 확인하는 작업이 아니라, 우선 `metadata.json`의 `known_issues`와 `texts/<id>/collation.md`에 기록된 의심 지점을 확인하는 방식으로 받습니다.

특히 한자 본문 중간에 현대 한글 음절이 섞인 경우를 우선 대조합니다. 예를 들어 `葉수擣`, `最凶흉之候`처럼 한글 한 글자가 본문 사이에 들어간 항목입니다.

원문대조 PR에는 다음을 포함해 주세요.

- 대조한 원본 또는 판본
- 수정한 `source.md` 위치
- 갱신한 `metadata.json`의 `known_issues` 상태
- 갱신한 `collation.md` 기록

원문 확인 없이 추정으로 고치지 말아 주세요. 탕액편의 한글 약재명, 물명, 우리말 이명처럼 원문 자체에 포함된 한글 표기는 보존합니다.

## 자동 변환 사용

로컬에서 변환하려면:

```bash
./scripts/ingest_source.py /path/to/file.hwp \
  --id donguibogam \
  --title-ko 동의보감 \
  --title-hanja 東醫寶鑑 \
  --author 허준 \
  --era 조선 \
  --source-note "저작권이 소실된 고전 원문 파일" \
  --stage
```

현재 지원 형식은 `.hwp`, `.hwpx`, `.doc`, `.docx`, `.txt`, `.md`입니다.

변환 직후에는 자동 품질 게이트가 실행됩니다. `source.md` 후보가 충분한 실제 한글/한자/문자 텍스트를 포함하지 않거나, `￼` 같은 객체/치환 문자가 과도하면 변환은 실패로 처리되고 git stage, commit, push가 진행되지 않습니다. 이런 파일은 OCR 또는 더 나은 텍스트 원본 확보가 필요합니다.

여러 파일을 한 번에 처리할 때는 `inbox/raw/manifest.example.json`을 참고해 `inbox/raw/manifest.json`을 작성한 뒤:

```bash
./scripts/ingest_folder.py --commit --push
```

## Pull Request 체크리스트

- [ ] 저작권이 소실된 고전 원문이다.
- [ ] 원본 파일도 공개 배포 가능하다.
- [ ] 현대 출판사 교정본, 역주본, 번역본, 해설본이 아니다.
- [ ] 폴더명은 stable ASCII ID를 사용했다.
- [ ] `metadata.json`의 서지/권리/품질 정보가 채워져 있다.
- [ ] `source.md`가 자동 품질 게이트를 통과한 AI-readable canonical 원문이다.
- [ ] 변환 오류 의심 지점은 `known_issues`와 `collation.md`에 기록했거나, 원문대조 근거와 함께 처리했다.
- [ ] `catalog.json`과 `CATALOG.md`가 갱신되어 있다.
