# Doc-to-Context

HWP, PPT, Word, Excel 문서를 AI가 읽을 수 있는 구조화된 Markdown으로 자동 변환하는 **Claude Code skill**.

프로젝트 루트에 문서 파일을 넣고 Claude에게 "문서 변환해줘"라고 말하면, 모든 문서가 깔끔한 Markdown으로 변환되어 `AI_Context/` 폴더에 정리됩니다.

## 왜 필요한가?

한국에서 정부기관, 대학, 공공기관과 일하면 **HWP 파일을 강제로 써야** 합니다. 이 파일들은 AI가 직접 읽을 수 없어서 context engineering의 장애물이 됩니다. PPT, Word, Excel도 마찬가지로 AI가 원본 구조를 유지하면서 읽기 어렵습니다.

기존 변환 도구들은 기계적 포맷 변환에 그치지만, **Doc-to-Context는 AI가 의미 구조를 이해하고 재구조화**합니다. 특히 HWP의 복잡한 표(셀 병합, 다단 등)를 **XML 레벨에서 직접 추출**하여 정확한 구조를 보존합니다.

## 지원 포맷

| 포맷 | 확장자 | 변환 방식 |
|------|--------|----------|
| 한글 | `.hwp`, `.hwpx` | HWP → HWPX → XML TextExtractor (표 구조 보존) |
| PowerPoint | `.ppt`, `.pptx` | markitdown 직접 변환 |
| Word | `.doc`, `.docx` | markitdown 직접 변환 |
| Excel | `.xls`, `.xlsx` | markitdown 직접 변환 |

## 설치

### 1. 의존성 설치

```bash
# HWP 변환 (Windows + 한글 설치 필요)
pip install pyhwpx

# HWPX 텍스트 추출 (표 구조 보존의 핵심)
pip install python-hwpx

# PPT/Word/Excel 변환
pip install 'markitdown[all]'
```

> **참고**: HWP 변환은 Windows에서 한글(Hancom Office)이 설치된 환경에서만 동작합니다. PPT/Word/Excel 변환은 OS 무관합니다.

### 2. Skill 설치

```bash
# 리포지토리 클론
git clone https://github.com/hyunsungko/Skill-MD-Converter.git

# Claude Code 전역 skill로 설치
mkdir -p ~/.claude/skills/doc-to-context
cp Skill-MD-Converter/.claude/skills/doc-to-context/SKILL.md ~/.claude/skills/doc-to-context/
cp Skill-MD-Converter/convert_docs.py ~/.claude/skills/doc-to-context/
cp Skill-MD-Converter/hwp_to_pdf_cli.py ~/.claude/skills/doc-to-context/
```

또는 원라이너:

```bash
git clone https://github.com/hyunsungko/Skill-MD-Converter.git /tmp/doc-to-context \
  && mkdir -p ~/.claude/skills/doc-to-context \
  && cp /tmp/doc-to-context/.claude/skills/doc-to-context/SKILL.md ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/convert_docs.py ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/hwp_to_pdf_cli.py ~/.claude/skills/doc-to-context/ \
  && rm -rf /tmp/doc-to-context
```

설치 확인: Claude Code를 실행하면 skill 목록에 `doc-to-context`가 표시됩니다.

## 사용법

### 기본 사용

프로젝트에 문서 파일을 넣고 Claude에게 말하세요:

```
문서 변환해줘
```

또는:

```
HWP 파일 마크다운으로 변환해줘
```

```
새 문서 추가했어, context 업데이트해줘
```

Claude가 자동으로 skill을 인식하고 변환을 시작합니다.

### 수동 실행 (skill 없이)

```bash
# 프로젝트 루트의 모든 문서 변환
python convert_docs.py

# 특정 파일만 변환
python convert_docs.py "강의계획서.hwp" "규정.docx"

# 변환 대상만 확인 (실제 변환 안 함)
python convert_docs.py --scan-only

# 모든 파일 강제 재변환 (캐시 무시)
python convert_docs.py --force
```

## 작동 방식

```
문서 파일 (HWP/PPT/Word/Excel)
         │
         ▼
┌─────────────────────────────────┐
│     Step 1: convert_docs.py     │
│  파일 스캔 → 증분 감지(SHA256)   │
│  → 포맷별 변환 → raw MD 생성    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│     Step 2: AI 구조화 (Claude)   │
│  raw MD → 표/제목/리스트 복원    │
│  → 깔끔한 구조화 MD 생성        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│     Step 3: 정량적 검증          │
│  글자 수 85% 임계값 비교         │
│  핵심 키워드 존재 확인           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│     AI_Context/ 폴더            │
│  ├── 문서1.md (구조화 결과)      │
│  ├── 문서2.md                   │
│  ├── _SUMMARY.md (통합 요약)    │
│  ├── _manifest.json (증분 추적) │
│  └── _intermediate/ (중간 파일) │
└─────────────────────────────────┘
```

### HWP 변환 파이프라인

기존 도구들은 HWP → PDF → 텍스트 추출 방식을 사용하는데, 이 과정에서 **표 구조가 완전히 깨집니다** (셀 순서 뒤섞임, 경계 손실).

Doc-to-Context는 다른 접근을 사용합니다:

```
HWP → HWPX (pyhwpx COM) → XML 파싱 (python-hwpx TextExtractor)
```

HWPX는 ZIP 기반 XML 포맷이므로, XML에서 직접 표의 셀/행/열 구조를 추출할 수 있습니다. 이 방식은 [hwpxskill](https://github.com/anthropics/skills)의 접근 방식을 차용한 것입니다.

HWPX 변환이 실패하면 PDF 경유로 자동 fallback 합니다.

## 주요 기능

- **증분 변환**: SHA256 해시 기반으로 변경된 파일만 재변환. `_manifest.json`으로 상태 추적.
- **표 구조 보존**: HWP의 복잡한 표를 XML 레벨에서 추출하여 Markdown 테이블로 정확히 복원.
- **AI 구조화**: 기계적 변환 결과를 Claude가 의미 구조를 분석하여 깔끔하게 재구조화.
- **정량적 검증**: 변환 후 글자 수 비교 + 핵심 키워드 존재 확인으로 누락 방지.
- **통합 요약**: 여러 문서의 핵심 정보를 `_SUMMARY.md`로 통합 정리.
- **의존성 검사**: 누락된 패키지가 있으면 안내하고 해당 포맷만 건너뜀 (전체 중단 없음).
- **타임아웃 보호**: HWP COM 객체 행(hang) 시 타임아웃으로 파이프라인 보호.
- **에러 복구**: 개별 파일 변환 실패 시 건너뛰고 나머지 계속 진행.

## 시스템 요구사항

| 요구사항 | HWP 변환 | PPT/Word/Excel 변환 |
|---------|---------|-------------------|
| OS | Windows | Windows / macOS / Linux |
| Python | 3.10+ | 3.10+ |
| 한글(Hancom) | 필수 | 불필요 |

## 테스트

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 개별 테스트
python -m pytest tests/test_scan_filter.py -v      # 파일 스캔, SHA256, 증분 감지
python -m pytest tests/test_manifest.py -v          # manifest 관리
python -m pytest tests/test_error_handling.py -v    # 타임아웃, 에러 핸들링
```

## 프로젝트 구조

```
Skill-MD-Converter/
├── .claude/skills/doc-to-context/
│   └── SKILL.md                  # Claude Code skill 정의
├── convert_docs.py                # 파이프라인 오케스트레이터
├── hwp_to_pdf_cli.py              # HWP → PDF/HWPX 변환 유틸리티
├── tests/
│   ├── test_scan_filter.py        # 파일 스캔/필터 테스트 (26개)
│   ├── test_manifest.py           # manifest 관리 테스트 (12개)
│   └── test_error_handling.py     # 에러 핸들링 테스트 (20개)
├── TODOS.md                       # v2 로드맵
├── LICENSE                        # MIT License
└── README.md                      # 이 파일
```

## 로드맵 (v2)

- 이미지/차트 인식 및 별도 정리
- 문서 간 관계 자동 매핑
- pyhwpx 직접 텍스트 추출 경로 (PDF/HWPX 경유 없이)

## 기여

이슈와 PR을 환영합니다. 특히 다음 영역에서 기여를 기다립니다:

- 새로운 문서 포맷 지원 (PDF, HWP 직접 추출 등)
- macOS/Linux에서의 HWP 변환 방안
- AI 구조화 품질 개선

## License

[MIT](LICENSE)
