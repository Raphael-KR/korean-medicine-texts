# 한의학 원서 Markdown 아카이브

HWP/HWPX로 된 한의학 원서를 AI가 읽기 좋은 Markdown 형태로 변환해 GitHub에 보관하는 프로젝트입니다.

## 목표

- 원본 HWP/HWPX 파일을 온프레미스 환경에서 변환합니다.
- 변환기는 [Raphael-KR/rhwp](https://github.com/Raphael-KR/rhwp)의 `export-markdown` CLI를 사용합니다.
- Markdown, 이미지 asset, 원본 파일, 변환 메타데이터를 한 묶음으로 저장합니다.
- Codex 스킬을 통해 “파일 전달 → 변환 → GitHub 업로드 → 링크 반환” 흐름을 자동화합니다.

## 저장 구조

```text
.
├── sources/                 # 원본 HWP/HWPX 보관
├── inbox/
│   └── raw/                  # 사용자가 변환 전 파일을 복사해두는 작업 폴더
├── texts/                   # AI가 읽을 Markdown 결과물
│   └── <slug>/
│       ├── README.md        # 병합본 + 메타데이터
│       ├── pages/           # rhwp가 만든 페이지별 Markdown
│       └── *_assets/        # 추출 이미지
├── scripts/
│   ├── bootstrap_rhwp.sh    # rhwp 클론/빌드
│   └── ingest_hwp.py        # 변환/정리/Git 작업
└── skills/
    └── hwp-github-ingest/   # Codex용 스킬 초안
```

## 1. rhwp 온프레미스 구축

Rust toolchain이 설치된 머신에서:

```bash
./scripts/bootstrap_rhwp.sh
```

기본값은 `vendor/rhwp`에 `Raphael-KR/rhwp`를 클론하고 release 바이너리를 빌드합니다. 빌드 결과는 `vendor/rhwp/target/release/rhwp`입니다.

이미 빌드된 `rhwp`가 있다면 환경변수로 지정할 수 있습니다.

```bash
export RHWP_BIN=/path/to/rhwp
```

## 2. HWP/HWPX 변환

사용자는 변환할 파일을 먼저 여기에 복사합니다.

```text
inbox/raw/
```

단일 파일 변환:

```bash
./scripts/ingest_hwp.py /path/to/원서.hwp
```

명령은 다음 작업을 수행합니다.

1. 원본을 `sources/<slug>/`에 복사
2. `rhwp export-markdown` 실행
3. 페이지별 Markdown을 `texts/<slug>/pages/`에 저장
4. 전체 병합본을 `texts/<slug>/README.md`에 생성
5. 변환 메타데이터를 front matter와 `metadata.json`으로 기록

GitHub까지 올리려면:

```bash
./scripts/ingest_hwp.py /path/to/원서.hwp --commit --push
```

`--push`는 현재 브랜치를 origin으로 push하고, origin URL을 기준으로 GitHub blob 링크를 출력합니다.

`inbox/raw/`에 들어 있는 모든 파일을 한 번에 처리하려면:

```bash
./scripts/ingest_folder.py --commit --push
```

처리된 파일은 `inbox/processed/`로 이동합니다. 변환 실패 파일은 원래 위치에 남습니다.

## 3. Codex 스킬 설치

스킬 초안은 `skills/hwp-github-ingest/SKILL.md`에 있습니다. Codex에서 이 저장소 작업을 반복할 때 해당 스킬을 `$CODEX_HOME/skills`로 복사해 사용할 수 있습니다.

```bash
mkdir -p "$CODEX_HOME/skills/hwp-github-ingest"
cp skills/hwp-github-ingest/SKILL.md "$CODEX_HOME/skills/hwp-github-ingest/SKILL.md"
```

## Markdown 원칙

- 원문을 먼저 보존하고, 정규화/교정은 별도 커밋으로 진행합니다.
- 페이지 경계는 병합본에 `## Page N`으로 남깁니다.
- 표, 이미지, 주석처럼 변환 손실 위험이 있는 요소는 원본과 페이지별 파일을 함께 추적합니다.
- AI 후처리는 원문 Markdown 위에 덮어쓰기보다 별도 파일 또는 별도 브랜치에서 수행합니다.
