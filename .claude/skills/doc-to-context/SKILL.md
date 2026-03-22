---
name: doc-to-context
description: |
  프로젝트 루트의 문서 파일(HWP, HWPX, PPT, PPTX, DOC, DOCX, XLS, XLSX)을
  AI가 읽기 쉬운 구조화된 Markdown으로 변환하고 AI_Context/ 폴더에 정리하는 skill.
  Use when: 사용자가 "문서 변환", "context 정리", "MD 변환", "HWP 변환",
  "문서를 마크다운으로", "AI가 읽을 수 있게", "context 만들어",
  "새 문서 추가했어", "문서 파일 넣었어" 등을 언급할 때 사용.
  Also use when: 프로젝트에 .hwp, .pptx, .docx, .xlsx 파일이 있고
  사용자가 해당 파일의 내용을 파악하거나 활용하려 할 때.
---

# Document-to-Context Converter

프로젝트 루트에 있는 문서 파일들을 AI가 읽기 쉬운 구조화된 Markdown으로 변환합니다.

## 사전 요구사항

이 skill을 사용하려면 다음 패키지가 설치되어 있어야 합니다:

```bash
pip install pyhwpx          # HWP 변환 (Windows + 한글 설치 필요)
pip install python-hwpx     # HWPX 텍스트 추출 (표 구조 보존)
pip install 'markitdown[all]' # PPT/Word/Excel/PDF → MD 변환
```

## 실행 순서

이 skill이 트리거되면 다음 단계를 순서대로 수행합니다.

### Step 1: convert_docs.py 실행

프로젝트 루트에서 문서 파일을 스캔하고 raw Markdown으로 변환합니다.

```bash
python convert_docs.py
```

- 지원 포맷: HWP, HWPX, PPT, PPTX, DOC, DOCX, XLS, XLSX
- HWP/HWPX → HWPX → TextExtractor (pyhwpx + python-hwpx, 표 구조 보존)
  - HWPX 변환 실패 시 PDF 경유 fallback (pyhwpx + markitdown)
- PPT/Word/Excel → MD (markitdown 직접)
- 증분 처리: _manifest.json으로 SHA256 비교, 변경된 파일만 변환
- 결과: `AI_Context/_intermediate/` 에 raw MD 파일 저장

특정 파일만 변환하려면:
```bash
python convert_docs.py "파일명.hwp" "파일명.pptx"
```

강제 재변환:
```bash
python convert_docs.py --force
```

### Step 2: AI 구조화

convert_docs.py 실행 후, `AI_Context/_intermediate/` 에 생성된 각 raw MD 파일을
읽고 구조화된 깔끔한 Markdown으로 재작성합니다.

**각 raw MD 파일에 대해:**

1. Read tool로 `AI_Context/_intermediate/{파일명}.raw.md` 읽기
2. 아래 **구조화 원칙**에 따라 깔끔한 Markdown으로 재작성
   - HWP 파일의 raw MD는 `[셀]` 태그로 표 셀이 구분되어 있음
   - `[셀]` 태그들을 분석하여 원본 표의 행/열 구조를 복원해서 Markdown 테이블로 재구성
3. Write tool로 `AI_Context/{파일명}.md` 로 저장

**raw MD가 2000행 초과 시:**
- H1/H2 섹션 단위로 분할하여 순차적으로 읽고 처리
- 각 섹션을 구조화한 뒤 하나의 파일로 합쳐서 저장

### 구조화 원칙

변환 시 반드시 지켜야 할 규칙들:

1. **원본 무손실**: 원본의 모든 텍스트 내용을 빠짐없이 포함하는 것이 목표.
   HWP→PDF 경로에서 발생하는 구조적 손실은 best-effort로 복원.
2. **표 변환**: 표는 Markdown 테이블(`| ... | ... |`)로 정확히 변환
3. **제목 계층**: 원본의 제목 계층 구조 유지 (H1 → H2 → H3)
4. **리스트 보존**: 번호 매기기, 불릿 포인트 등 리스트 구조 보존
5. **내용 추가 금지**: 원본에 없는 내용을 추가하지 않음
6. **불필요한 요소 제거**: markitdown이 생성한 불필요한 메타데이터, 깨진 문자, 의미 없는 기호 등은 정리

### Step 3: 정량적 검증

각 파일의 구조화 완료 후, 원본 대비 누락 여부를 검증합니다.

1. **글자 수 비교**: 구조화 MD의 글자 수가 raw MD 대비 85% 미만이면 누락 경고 출력
2. **핵심 키워드 확인**: 원본의 고유명사, 숫자 데이터, 표 제목 등이 구조화 MD에 존재하는지 확인
3. **누락 발견 시**: 해당 부분을 보충하여 재작성

검증 방법:
```bash
# raw MD 글자 수
python -c "print(len(open('AI_Context/_intermediate/파일명.raw.md', encoding='utf-8').read()))"
# 구조화 MD 글자 수
python -c "print(len(open('AI_Context/파일명.md', encoding='utf-8').read()))"
```

### Step 4: _SUMMARY.md 생성

모든 개별 파일의 구조화가 완료되면, AI_Context/ 폴더에 통합 요약 파일을 생성합니다.

`AI_Context/_SUMMARY.md` 를 다음 형식으로 작성:

```markdown
# 프로젝트 문서 통합 요약

> 자동 생성: {현재 날짜 YYYY-MM-DD HH:MM}
> 원본 문서 {N}개 기반

## 문서 목록
- [문서1.md](./문서1.md) — 한줄 요약
- [문서2.md](./문서2.md) — 한줄 요약

## 핵심 정보 요약
(각 문서의 주요 내용을 문서 유형에 맞게 자유롭게 정리.
 고정 카테고리를 강제하지 않고 문서 내용에 따라 적절한 구조로 통합.)
```

이미 _SUMMARY.md가 존재하는 경우:
- 신규 문서를 문서 목록에 추가
- 핵심 정보 요약에 새 내용 반영
- 기존 내용은 유지

### Step 5: 완료 보고

변환 완료 후 사용자에게 결과를 보고합니다:

- 성공/실패/건너뜀 파일 수
- 실패한 파일이 있으면 사유와 함께 목록 표시
- `AI_Context/` 폴더에 생성된 파일 목록
- 누락 검증 결과 (경고가 있었다면)

## 증분 업데이트

사용자가 새 문서 파일을 추가하고 다시 요청하면:

1. `python convert_docs.py` 재실행 → 변경/신규 파일만 변환
2. 신규 raw MD만 구조화 (기존 구조화 MD는 유지)
3. _SUMMARY.md 업데이트 (기존 내용 유지 + 신규 추가)

## 폴더 구조

```
프로젝트 루트/
├── .claude/skills/doc-to-context/
│   └── SKILL.md                      ← 이 파일
├── convert_docs.py                    ← 변환 파이프라인 스크립트
├── hwp_to_pdf_cli.py                  ← HWP→PDF 변환 유틸리티
├── AI_Context/                        ← 자동 생성
│   ├── 문서1.md                       ← 구조화된 최종 MD
│   ├── 문서2.md
│   ├── _SUMMARY.md                    ← 전체 통합 요약
│   ├── _manifest.json                 ← 증분 추적 메타데이터
│   └── _intermediate/                 ← 중간 파일 (raw MD, HWPX)
│       ├── 문서1.raw.md
│       ├── 문서1.hwpx                  ← HWP→HWPX 중간산물
│       └── 문서2.raw.md
├── 원본문서1.hwp
├── 원본문서2.pptx
└── ...
```
