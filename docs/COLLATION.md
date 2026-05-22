# 원문대조 작업 지침

이 저장소의 원문대조는 전체 본문을 처음부터 끝까지 대조하는 방식이 아니라, 자동 변환과 QC/Lint 과정에서 발견된 의심 지점을 우선 확인하는 방식으로 진행합니다.

## 기본 범위

우선 대조 대상은 다음과 같습니다.

- 한자 본문 중간에 현대 한글 음절이 섞인 경우
- 깨진 문자, 치환 문자, 객체 자리표시자 주변 문장
- 자동 변환 과정에서 누락 또는 오인식 가능성이 높은 표, 그림, 특수문자 주변
- `metadata.json`의 `known_issues`에 `status: "needs_collation"`으로 기록된 항목

탕액편의 한글 약재명, 물명, 우리말 이명처럼 원문 자체에 포함된 한글 표기는 제거하거나 교정하지 않습니다.

## 작업 단위

각 문헌의 원문대조 작업은 문헌 폴더의 `collation.md`에서 관리합니다.

```text
texts/
  <stable-id>/
    source.md
    metadata.json
    collation.md
```

`collation.md`는 사람이 읽고 검토하기 위한 작업표입니다. 기계 판별에는 `metadata.json`의 `known_issues`를 사용합니다.

## known_issues 필드

원문대조 대상은 다음 형식을 권장합니다.

```json
{
  "line": 5634,
  "text": "葉수擣",
  "type": "suspected_hangul_conversion_error",
  "status": "needs_collation",
  "note": "한글 '수'가 섞여 있어 원문 대조 필요"
}
```

대조가 끝난 항목은 다음처럼 갱신합니다.

```json
{
  "line": 5634,
  "text": "葉수擣",
  "type": "suspected_hangul_conversion_error",
  "status": "resolved",
  "resolution": "corrected",
  "corrected_text": "葉搗",
  "evidence": "원본 HWPX 본문 대조"
}
```

확실히 원문 표기가 맞는 경우에는 `resolution: "kept"`로 표시합니다.

## 원칙

- 원문 대조 없이 추정으로 교정하지 않습니다.
- 확실한 변환 잔여물은 QC/Lint 단계에서 제거할 수 있습니다.
- 의미 판단이 필요한 본문 교정은 원문대조 단계에서만 합니다.
- 교정할 때는 `source.md`, `metadata.json`, `collation.md`를 함께 갱신합니다.
- 줄 번호는 변경될 수 있으므로, `text` 필드의 주변 문자열도 함께 확인합니다.
