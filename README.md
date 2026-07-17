# 한의학 고전 원문 AI Markdown 아카이브

저작권이 소실된 한의학 고전 원문을 AI가 읽기 좋은 Markdown 형태로 공개 배포하는 학술 아카이브입니다.

이 저장소는 특정 개인의 작업 폴더가 아니라, 불특정다수의 한의학자, 연구자, 개발자, AI 도구가 함께 참조할 수 있는 공개 원문 데이터셋을 목표로 합니다.

## 수록 원칙

이 저장소에는 **저작권이 소실된 고전 원문**만 수록합니다.

다음 자료는 이 저장소의 대상이 아닙니다.

- 저작권이 살아 있는 책의 입력본
- 역주본, 번역본, 해설본
- 현대 논문, 교재, 강의자료

원본 파일도 공개 배포합니다. 따라서 기여자는 원본 파일 자체도 공개 배포 가능한 자료인지 확인해야 합니다.

현재 운영 스크립트가 지원하는 원본 형식은 `.hwp`, `.hwpx`, `.doc`, `.docx`, `.txt`, `.md`입니다. 다른 형식도 공개 배포 가능한 고전 원문이라면 수록 대상이 될 수 있으나, 변환 방식은 별도로 정해야 합니다.

## 수록 문헌

전체 목록은 [CATALOG.md](CATALOG.md)와 [catalog.json](catalog.json)을 봐 주세요.

현재 수록:

- [동의보감](texts/donguibogam/source.md)
- [동의수세보원](texts/donguisusebowon/source.md)
- [경악전서](texts/gyeongakjeonseo/source.md)
- [황제내경소문](texts/huangdineijingsuwen/source.md)
- [황제내경영추](texts/huangdineijinglingshu/source.md)

## 데이터 구조

```text
texts/
  <stable-id>/
    README.md       # 문헌별 안내
    source.md       # AI와 사람이 참조할 canonical Markdown 원문
    metadata.json   # 서지, 권리, 변환, 품질 메타데이터
    collation.md    # 원문대조가 필요한 의심 지점과 처리 기록

sources/
  <stable-id>/
    <original>.*    # 공개 배포 가능한 원본 파일

catalog.json        # 기계가 읽기 좋은 전체 목록
CATALOG.md          # 사람이 읽기 좋은 전체 목록
```

폴더명은 한글 책 제목이 아니라 안정적인 ASCII ID를 사용합니다. 예: `donguibogam`, `donguisusebowon`.

## AI 활용 방식

각 문헌의 기본 참조 파일은 `texts/<stable-id>/source.md`입니다.

`source.md`는 원본 파일에서 추출한 텍스트를 하나의 원문 Markdown으로 정리한 파일입니다. HWP/HWPX의 경우 조판 페이지를 별도 파일로 보존하지 않습니다. 조판 페이지는 의미 단위가 아니므로 기본 분할 기준으로 쓰지 않습니다.

향후에는 `chunks/`를 추가해 권, 편, 장, 조문, 처방명 같은 의미 단위 분할을 제공할 예정입니다.

### Codex 스킬

- [`skills/ground-hanmedicine-answers`](skills/ground-hanmedicine-answers/SKILL.md): `catalog.json`, 문헌별 `metadata.json`, canonical `source.md`, `collation.md`를 근거 사슬로 사용해 고전 원문을 검색·검증하고, 역사적 문헌 근거와 현대 임상 근거를 분리해 답변합니다.
- [`skills/hwp-github-ingest`](skills/hwp-github-ingest/SKILL.md): 공개 가능한 고전 원본을 이 저장소의 Markdown 아카이브 구조로 변환합니다.

현대 논문·가이드라인은 이 공개 고전 원문 코퍼스에 포함하지 않습니다. 임상 효과와 안전성에 관한 답변에는 별도의 최신 외부 근거가 필요합니다.

#### `ground-hanmedicine-answers` 설치

이 스킬은 Codex용입니다. 원문 전체를 스킬 폴더에 복제하지 않으므로, **저장소와 스킬을 모두 설치**해야 합니다. Python 3 표준 라이브러리 외에 별도 검색 의존성은 없습니다.

1. 원문 저장소를 클론합니다.

   ```bash
   git clone https://github.com/Raphael-KR/korean-medicine-texts.git
   cd korean-medicine-texts
   ```

2. Codex에 다음과 같이 요청하는 방법을 권장합니다.

   ```text
   Raphael-KR/korean-medicine-texts 저장소의
   skills/ground-hanmedicine-answers 스킬을 전역 설치해줘.
   ```

   또는 macOS/Linux에서 Codex의 기본 스킬 설치기를 직접 실행할 수 있습니다.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
     --repo Raphael-KR/korean-medicine-texts \
     --path skills/ground-hanmedicine-answers
   ```

3. 설치가 끝난 다음 대화부터 스킬을 사용할 수 있습니다. 저장소 밖의 작업공간에서 사용할 경우에는 원문 저장소의 절대경로를 지정합니다.

   ```bash
   export KOREAN_MEDICINE_TEXTS_ROOT="/absolute/path/to/korean-medicine-texts"
   ```

   이 저장소 자체를 Codex 작업공간으로 열었다면 환경변수 없이 현재 작업공간에서 코퍼스를 자동 발견합니다.

4. 설치와 코퍼스 연결을 확인합니다.

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/ground-hanmedicine-answers/scripts/search_corpus.py" \
     "桂枝湯" --root "$PWD" --source-id donguibogam --max-results 1
   ```

#### 사용 예시

명시적으로 호출하려면 프롬프트에 `$ground-hanmedicine-answers`를 포함합니다.

```text
$ground-hanmedicine-answers 동의보감에서 桂枝湯 관련 구절을 찾아
원문 경로와 행 번호, 텍스트 품질 상태를 함께 알려줘.
```

```text
$ground-hanmedicine-answers 소갈의 고전 문헌상 설명과 현대 당뇨병 임상 근거를
서로 섞지 말고 구분해서 정리해줘.
```

스킬은 고전 원문의 존재·출전·문맥을 이 저장소에서 확인합니다. 현대 치료 효과, 안전성, 상호작용, 가이드라인은 최신 외부 근거를 별도로 검색해야 하며, 고전 원문만으로 현대 임상 효과를 주장하지 않습니다.

업데이트할 때는 GitHub 저장소를 정본으로 삼고, 전역 설치본을 직접 편집하지 마세요. Codex에 같은 GitHub 경로의 스킬을 최신 버전으로 다시 설치해 달라고 요청하면 됩니다.

## 품질 상태

각 문헌의 `metadata.json`에는 `quality_status`가 있습니다.

- `raw_converted`: 원본 파일에서 Markdown으로 자동 변환한 원문
- `needs_ocr`: 자동 변환 결과가 AI가 읽기 좋은 텍스트 기준을 통과하지 못해 OCR 또는 다른 원본 확보가 필요한 상태
- `reviewed`: 사람이 원문 대조를 일부 또는 전체 수행
- `corrected`: 오류 교정이 반영된 상태

자동 변환 스크립트는 변환 직후 `source.md` 후보에 대해 품질 게이트를 실행합니다. 본문 글자 수, `￼` 같은 객체/치환 문자 비율, 실제 문자 비율을 검사하며, 통과하지 못한 자료는 기본적으로 `texts/` 갱신, git stage, commit, push를 진행하지 않습니다.

현재 자료는 기본적으로 `raw_converted`입니다. 연구나 임상 판단에 사용할 때는 반드시 원문 대조가 필요합니다.

일부 파일에는 고전 원문 외에 현대 입력자가 남긴 "일러두기", 입력 방식 설명, 기호 설명 등이 포함될 수 있습니다. 이런 경우 `metadata.json`의 `has_modern_input_notes`와 `modern_input_note`에 별도 표시합니다.

canonical `source.md`는 AI 참조용 원문 코퍼스이므로, 원본 파일에 현대 서두, 교정주, 음훈 각주, 미주가 포함되어 있더라도 필요하면 변환 과정에서 제거합니다. 제거 여부와 적용된 정제 규칙은 `metadata.json`의 `cleanup_applied`와 `cleanup`에 기록합니다.

## 원문대조

이 저장소의 원문대조는 전체 본문을 모두 대조하는 방식이 아니라, 우선 **한자 본문 중간에 현대 한글 음절이 섞인 의심 지점**을 중심으로 진행합니다.

자동 변환과 QC/Lint 단계에서 의심 지점이 발견되면 `metadata.json`의 `known_issues`에 기록하고, 문헌별 `collation.md`에서 사람이 읽기 좋은 작업표로 관리합니다.

원문대조 없이 추정으로 본문을 교정하지 않습니다. 탕액편의 한글 약재명, 물명, 우리말 이명처럼 원문 자체에 포함된 한글 표기는 보존합니다.

자세한 기준은 [docs/COLLATION.md](docs/COLLATION.md)를 참고해 주세요.

## 변환 Manifest

운영자는 `inbox/raw/manifest.json`으로 변환 규칙을 지정할 수 있습니다. 한 원본 파일이 여러 문헌을 포함하면 `splits`로 나누고, 현대 주석층 제거는 `cleanup`에서 명시합니다.

```json
{
  "황제내경소문.hwpx": {
    "source_id": "huangdineijing",
    "source_note": "원본 HWPX에는 黃帝內經素問과 黃帝內經靈樞가 함께 포함됨",
    "has_modern_input_notes": true,
    "modern_input_note": "원본의 현대 서두와 교정주/음훈 각주는 canonical source.md에서 제거함",
    "cleanup": {
      "remove_editorial_notes": true,
      "remove_inline_note_refs": true,
      "remove_korean_labels": true,
      "reject_korean_body_text": true
    },
    "splits": [
      {
        "id": "huangdineijingsuwen",
        "title_ko": "황제내경소문",
        "title_hanja": "黃帝內經素問",
        "body_start": "^上古天眞論篇 第一$",
        "body_end_before": "^九鍼十二原 第一\\(法天\\)$"
      },
      {
        "id": "huangdineijinglingshu",
        "title_ko": "황제내경영추",
        "title_hanja": "黃帝內經靈樞",
        "body_start": "^九鍼十二原 第一\\(法天\\)$"
      }
    ]
  }
}
```

## 기여 방법

기여 방법은 두 가지입니다.

1. 비개발자: 공개 배포 가능한 원문 파일과 서지 정보를 운영자에게 전달합니다.
2. GitHub 사용자: 직접 변환 결과를 추가하고 Pull Request를 보냅니다.

자세한 절차는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요.

## 권리와 라이선스

이 저장소는 저작권이 소실된 고전 원문만 수록합니다. 자세한 기준은 [DATA_LICENSE.md](DATA_LICENSE.md)를 참고해 주세요.

## 변환 도구

HWP/HWPX 변환에는 [edwardkim/rhwp](https://github.com/edwardkim/rhwp)의 `export-markdown` 기능을 사용합니다. 운영 환경에서는 필요에 따라 fork를 사용할 수 있으나, 이 프로젝트 문서에서는 원본 프로젝트를 기준으로 표시합니다. DOC/DOCX는 운영 환경의 `textutil`을 통해 텍스트로 추출하고, TXT/MD는 그대로 수집합니다.

운영용 스크립트는 [scripts](scripts) 아래에 있습니다. 공개 사용자는 보통 이 스크립트를 직접 사용할 필요가 없습니다.
