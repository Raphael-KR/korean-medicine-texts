# 구조 기반 검색 청킹

`source.md`가 정본이며 `chunks.jsonl`은 재현 가능한 파생 산출물이다. 청크는 페이지가 아니라 문헌의 확인 가능한 구조 경계로 만든다.

## 스키마

각 JSONL 행은 하나의 검색 단위다.

```json
{
  "schema_version": 1,
  "chunk_id": "huangdineijingsuwen:00001",
  "source_id": "huangdineijingsuwen",
  "source_sha256": "…",
  "chunking_profile": "neijing-pian-zhang-v1",
  "headings": ["上古天眞論篇 第一", "第一章"],
  "line_start": 17,
  "line_end": 72,
  "text": "…",
  "content_sha256": "…"
}
```

`line_start`와 `line_end`는 `source.md`의 1-based 행 번호다. 청크 안의 `text`는 해당 범위의 정본 문장을 그대로 가져오며, 검색 결과는 항상 이 위치를 표시해야 한다.

## 프로필

| 문헌 | 상위 경계 | 하위 경계 |
|---|---|---|
| 황제내경소문·영추 | `…篇 第…` | `第…章` |
| 동의보감 | 편·권 | `{주제}` → `【항목】` |
| 동의수세보원 | 7편 | 체질별 병론·범론·처방 |
| 경악전서 | 집·권 | 논·편·변·기·음 |

긴 단위는 1,200자에서 나누며, 매우 짧은 같은 구조의 연속 단위는 합친다. HWP 변환의 반복 머리말과 `경악전서`의 선행 목차는 본문 경계로 취급하지 않는다.

## 운영

`python3 scripts/chunk_corpus.py`로 전 문헌을, `--source-id`로 하나의 문헌을 재생성한다. 새 원본은 AI-readable 품질 게이트와 구조 청크 QC를 통과한 뒤에만 발행한다.

이 저장소는 임베딩이나 벡터 인덱스를 포함하지 않는다. 별도 검색 시스템이 `chunks.jsonl`을 읽어 인덱싱할 수 있지만, 그 시스템은 모델·인덱스 버전·검색 점수를 자신의 실행 결과로 남겨야 한다.
