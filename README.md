# Doc-to-Context

**PDF, HWP, PPT, Word, Excel 문서를 AI가 읽을 수 있는 구조화된 Markdown으로 자동 변환하는 Claude Code skill.**

Context Engineering의 핵심은 AI에게 정확하고 구조화된 정보를 제공하는 것입니다. 이 skill은 프로젝트에 있는 문서 파일들을 깔끔한 Markdown으로 변환하고, `AI_Context/` 폴더에 통합 정리하여 AI가 바로 활용할 수 있게 만듭니다.

## 지원 포맷

| 포맷 | 확장자 | 변환 백엔드 |
|------|--------|------------|
| PDF | `.pdf` | docling (AI 기반 레이아웃 분석) |
| PowerPoint | `.ppt`, `.pptx` | docling + 이미지 fallback |
| Word | `.doc`, `.docx` | docling |
| Excel | `.xls`, `.xlsx` | docling |
| 한글 | `.hwp`, `.hwpx` | pyhwpx → python-hwpx TextExtractor (표 구조 보존) |

### 변환 백엔드: docling (IBM Research)

v2부터 변환 백엔드를 **markitdown에서 docling으로 교체**했습니다.

- AI 기반 레이아웃 분석으로 테이블 구조 보존율 향상
- 109개 언어 OCR 내장 (스캔 PDF도 처리 가능)
- PDF, PPTX, DOCX, XLSX 등 다양한 포맷 통합 지원
- MIT 라이선스

### 이미지 전용 슬라이드 fallback

PPTX가 이미지로만 구성된 경우 (텍스트 레이어 없음):
1. LibreOffice로 PDF 변환 → pdftoppm으로 페이지별 이미지 생성
2. Claude가 이미지를 직접 읽어 내용을 구조화된 Markdown으로 작성

---

## 설치 가이드

### 방법 1: AI에게 맡기기 (권장)

아래 링크를 복사해서 Claude Code에 "이거 설치해줘"라고 말하면 됩니다:

```
https://github.com/hyunsungko/Skill-MD-Converter
```

### 방법 2: 수동 설치

#### Step 1: 의존성 설치

```bash
# docling (PDF/PPT/Word/Excel 변환) — 필수
pip install docling

# HWP 변환 (Windows + 한글 설치 환경에서만)
pip install pyhwpx
pip install python-hwpx

# 이미지 fallback용 (선택)
sudo apt install poppler-utils    # pdftoppm
sudo apt install libreoffice-impress  # PPTX→PDF 변환
```

> **참고:** docling은 PyTorch 기반이라 설치 용량이 큽니다 (~수GB). GPU가 있으면 OCR 속도가 빨라지지만 CPU에서도 동작합니다.

> **venv 사용 권장:** 시스템 Python과 충돌을 피하려면 가상환경을 만들어 설치하세요.
> ```bash
> python3 -m venv ~/docling-env
> source ~/docling-env/bin/activate
> pip install docling
> ```

#### Step 2: Skill 파일 설치

```bash
git clone https://github.com/hyunsungko/Skill-MD-Converter.git /tmp/doc-to-context \
  && mkdir -p ~/.claude/skills/doc-to-context \
  && cp /tmp/doc-to-context/.claude/skills/doc-to-context/SKILL.md ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/convert_docs.py ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/hwp_to_pdf_cli.py ~/.claude/skills/doc-to-context/ \
  && rm -rf /tmp/doc-to-context \
  && echo "설치 완료!"
```

설치 후 Claude Code에서 `doc-to-context` skill이 자동으로 인식됩니다.

---

## 활용 가이드

### 기본 사용법

Claude Code에서 자연어로 요청하면 자동 트리거됩니다:

```
"문서 변환해줘"
"이 폴더에 있는 PPTX를 마크다운으로 바꿔줘"
"AI가 읽을 수 있게 정리해줘"
"context 만들어"
"새 문서 추가했어"
```

### 변환 과정 (5단계)

```
원본 문서 → [Step 1] raw MD 변환 → [Step 2] AI 구조화 → [Step 3] 검증 → [Step 4] 요약 → [Step 5] 보고
```

| 단계 | 수행 주체 | 내용 |
|------|-----------|------|
| **Step 1** | `convert_docs.py` | 문서를 raw Markdown으로 변환 (docling) |
| **Step 2** | Claude AI | raw MD를 읽고 깔끔한 구조화 Markdown으로 재작성 |
| **Step 3** | Claude AI | 글자 수 비교(85% 기준) + 핵심 키워드 검증 |
| **Step 4** | Claude AI | `_SUMMARY.md` 통합 요약 생성 |
| **Step 5** | Claude AI | 성공/실패 보고 |

### CLI 직접 사용 (skill 없이)

```bash
# 프로젝트 루트의 모든 문서 변환
python convert_docs.py

# 변환 대상만 확인 (dry run)
python convert_docs.py --scan-only

# 모든 파일 강제 재변환
python convert_docs.py --force

# 특정 파일만 변환
python convert_docs.py file1.hwp file2.docx report.pdf
```

### 증분 업데이트

`_manifest.json`으로 SHA256 해시를 추적하여, 변경된 파일만 재변환합니다. 새 문서를 추가하고 다시 요청하면 신규 파일만 처리합니다.

### 출력 폴더 구조

```
프로젝트 루트/
├── AI_Context/                        ← 자동 생성
│   ├── 문서1.md                       ← 구조화된 최종 Markdown
│   ├── 문서2.md
│   ├── _SUMMARY.md                    ← 전체 문서 통합 요약
│   ├── _manifest.json                 ← 증분 추적 메타데이터
│   └── _intermediate/                 ← 중간 파일
│       ├── 문서1.raw.md               ← docling 변환 원본
│       └── 문서2.raw.md
├── 원본문서1.pptx
├── 원본문서2.docx
└── ...
```

---

## 변환 품질 비교

### docling vs markitdown (실제 테스트 결과)

같은 PDF(견적서)로 테스트한 결과:

| 항목 | markitdown (v1) | docling (v2) |
|------|-----------------|--------------|
| **테이블 구조** | 단순 텍스트 추출 | 행/열 구조 보존 |
| **제목 계층** | 플랫 출력 | H1/H2/H3 계층 인식 |
| **한국어 OCR** | 미지원 (텍스트 레이어 의존) | 내장 OCR 109개 언어 |
| **PPTX** | 텍스트만 추출 | 테이블/리스트 구조 보존 |
| **속도** | 즉시 | 수초~수십초 (AI 모델 추론) |

---

## 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| **OS** | Linux, macOS, Windows (WSL) | Ubuntu 24.04 (WSL 2) |
| **Python** | 3.10+ | 3.12 |
| **RAM** | 4GB | 8GB+ |
| **GPU** | 불필요 (CPU 동작) | NVIDIA GPU (OCR 가속) |
| **디스크** | 3GB (docling + 모델) | 5GB+ |
| **HWP 변환** | Windows + 한글 설치 필요 | - |

---

## 테스트

```bash
python -m pytest tests/ -v
```

---

## 변경 이력

### v2.0 (2026-03-29)
- 변환 백엔드를 markitdown에서 **docling (IBM Research)** 으로 교체
- PDF 포맷 지원 추가
- 이미지 전용 PPTX 슬라이드 fallback 기능 추가 (LibreOffice → pdftoppm → AI 비전)
- 테이블 구조 보존율 대폭 향상
- 한국어 OCR 지원 (스캔 PDF)

### v1.0 (2026-03-22)
- 최초 릴리스
- markitdown 기반 변환
- HWP → HWPX → TextExtractor 경로 구현
- 증분 처리 (SHA256 해시 기반)

---

## 라이선스

[MIT](LICENSE)

---

## 기여

이슈나 PR은 언제든 환영합니다.
