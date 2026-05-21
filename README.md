# 한의학 고전 원문 AI Markdown 아카이브

저작권이 소실된 한의학 고전 원문을 AI가 읽기 좋은 Markdown 형태로 공개 배포하는 학술 아카이브입니다.

이 저장소는 특정 개인의 작업 폴더가 아니라, 불특정다수의 한의학자, 연구자, 개발자, AI 도구가 함께 참조할 수 있는 공개 원문 데이터셋을 목표로 합니다.

## 수록 원칙

이 저장소에는 **저작권이 소실된 고전 원문**만 수록합니다.

다음 자료는 이 저장소의 대상이 아닙니다.

- 현대 출판사의 교정본
- 현대인이 입력/편집한 저작권 보호 입력본
- 역주본, 번역본, 해설본
- 현대 논문, 교재, 강의자료
- 배포 권한이 불명확한 HWP/HWPX 파일

HWP/HWPX 원본도 공개 배포합니다. 따라서 기여자는 원본 파일 자체도 공개 배포 가능한 자료인지 확인해야 합니다.

## 수록 문헌

전체 목록은 [CATALOG.md](CATALOG.md)와 [catalog.json](catalog.json)을 봐 주세요.

현재 수록:

- [동의보감](texts/donguibogam/source.md)
- [동의수세보원](texts/donguisusebowon/source.md)

## 데이터 구조

```text
texts/
  <stable-id>/
    README.md       # 문헌별 안내
    source.md       # AI와 사람이 참조할 canonical Markdown 원문
    metadata.json   # 서지, 권리, 변환, 품질 메타데이터

sources/
  <stable-id>/
    <original>.hwp  # 공개 배포 가능한 원본 HWP/HWPX

catalog.json        # 기계가 읽기 좋은 전체 목록
CATALOG.md          # 사람이 읽기 좋은 전체 목록
```

폴더명은 한글 책 제목이 아니라 안정적인 ASCII ID를 사용합니다. 예: `donguibogam`, `donguisusebowon`.

## AI 활용 방식

각 문헌의 기본 참조 파일은 `texts/<stable-id>/source.md`입니다.

`source.md`는 HWP 페이지별 파일을 따로 보존하지 않고 하나의 원문 Markdown으로 합친 파일입니다. HWP 조판 페이지는 의미 단위가 아니므로 기본 분할 기준으로 쓰지 않습니다. 다만 변환 추적을 위해 `<!-- rhwp-page: N -->` 주석은 남깁니다.

향후에는 `chunks/`를 추가해 권, 편, 장, 조문, 처방명 같은 의미 단위 분할을 제공할 예정입니다.

## 품질 상태

각 문헌의 `metadata.json`에는 `quality_status`가 있습니다.

- `raw_converted`: HWP에서 Markdown으로 자동 변환한 원문
- `reviewed`: 사람이 원문 대조를 일부 또는 전체 수행
- `corrected`: 오류 교정이 반영된 상태

현재 자료는 기본적으로 `raw_converted`입니다. 연구나 임상 판단에 사용할 때는 반드시 원문 대조가 필요합니다.

## 기여 방법

기여 방법은 두 가지입니다.

1. 비개발자: 공개 배포 가능한 HWP/HWPX 원문 파일과 서지 정보를 운영자에게 전달합니다.
2. GitHub 사용자: 직접 변환 결과를 추가하고 Pull Request를 보냅니다.

자세한 절차는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요.

## 권리와 라이선스

이 저장소는 저작권이 소실된 고전 원문만 수록합니다. 자세한 기준은 [DATA_LICENSE.md](DATA_LICENSE.md)를 참고해 주세요.

## 변환 도구

HWP/HWPX 변환에는 [Raphael-KR/rhwp](https://github.com/Raphael-KR/rhwp)의 `export-markdown` 기능을 사용합니다.

운영용 스크립트는 [scripts](scripts) 아래에 있습니다. 공개 사용자는 보통 이 스크립트를 직접 사용할 필요가 없습니다.
