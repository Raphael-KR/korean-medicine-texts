# 기여 안내

이 프로젝트는 한의학 고전 원문을 AI가 읽기 좋은 공개 Markdown 아카이브로 만드는 작업입니다.

## 기여 가능한 자료

다음 조건을 모두 만족해야 합니다.

- 한의학 고전 원문
- 저작권이 소실된 자료
- 원본 파일도 공개 배포 가능한 자료
- 현대 출판사의 교정, 입력, 역주, 번역, 해설 권리가 붙어 있지 않은 자료

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
- [ ] `source.md`가 AI가 읽을 canonical 원문으로 제공된다.
- [ ] `catalog.json`과 `CATALOG.md`가 갱신되어 있다.
