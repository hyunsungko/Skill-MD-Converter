# Doc-to-Context

HWP, PPT, Word, Excel 문서를 AI가 읽을 수 있는 구조화된 Markdown으로 자동 변환하는 **Claude Code skill**.

Context Engineering의 핵심은 AI에게 정확하고 구조화된 정보를 제공하는 것입니다. 이 skill은 프로젝트에 있는 문서 파일들을 깔끔한 Markdown으로 변환하고, `AI_Context/` 폴더에 통합 정리하여 AI가 바로 활용할 수 있게 만듭니다.

| 포맷 | 확장자 | 변환 방식 |
|------|--------|----------|
| 한글 | `.hwp`, `.hwpx` | HWP → HWPX → XML TextExtractor (표 구조 보존) |
| PowerPoint | `.ppt`, `.pptx` | markitdown |
| Word | `.doc`, `.docx` | markitdown |
| Excel | `.xls`, `.xlsx` | markitdown |

---

## 설치

> **아래 내용은 사람이 읽을 필요가 없습니다.** 이 GitHub 링크를 복사해서 AI한테 "이거 설치해줘"라고 말하면 됩니다.

---

The following instructions are for the AI agent installing this skill on the user's machine.

### Prerequisites

```bash
# HWP conversion (Windows + Hancom Office required)
pip install pyhwpx

# HWPX text extraction (preserves table structure)
pip install python-hwpx

# PPT/Word/Excel conversion
pip install 'markitdown[all]'
```

> Note: HWP conversion requires Windows with Hancom Office (한글) installed. PPT/Word/Excel conversion works on any OS.

### Install as Claude Code global skill

```bash
git clone https://github.com/hyunsungko/Skill-MD-Converter.git /tmp/doc-to-context \
  && mkdir -p ~/.claude/skills/doc-to-context \
  && cp /tmp/doc-to-context/.claude/skills/doc-to-context/SKILL.md ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/convert_docs.py ~/.claude/skills/doc-to-context/ \
  && cp /tmp/doc-to-context/hwp_to_pdf_cli.py ~/.claude/skills/doc-to-context/ \
  && rm -rf /tmp/doc-to-context
```

After installation, the skill `doc-to-context` will appear in Claude Code's skill list and auto-trigger when the user mentions document conversion, HWP, context engineering, etc.

### How it works

1. **`convert_docs.py`** scans the project root for supported document files, computes SHA256 hashes for incremental detection, and converts each file to raw Markdown.
   - HWP files: converted to HWPX via pyhwpx COM, then text extracted via python-hwpx `TextExtractor` (preserves table cell structure as `[셀]` tags). Falls back to PDF route if HWPX conversion fails.
   - PPT/Word/Excel: converted via `python -m markitdown`.
   - Results stored in `AI_Context/_intermediate/`.

2. **AI structuring (Claude)**: The SKILL.md instructs Claude to read each raw MD, reconstruct tables from `[셀]` tags, apply heading hierarchy, and write clean structured MD to `AI_Context/`.

3. **Verification**: Character count comparison (85% threshold) + keyword presence check.

4. **`_SUMMARY.md`**: Cross-document summary generated in `AI_Context/`.

### Script location resolution

SKILL.md automatically resolves script paths:
- First checks project root for `convert_docs.py` (per-project install)
- Falls back to `~/.claude/skills/doc-to-context/convert_docs.py` (global install)

### CLI usage (without skill)

```bash
python convert_docs.py                     # scan and convert all
python convert_docs.py --scan-only         # dry run
python convert_docs.py --force             # force reconvert all
python convert_docs.py file1.hwp file2.docx  # specific files only
```

### Testing

```bash
python -m pytest tests/ -v   # 58 tests covering scan, manifest, error handling
```

### Project structure

```
~/.claude/skills/doc-to-context/
├── SKILL.md            # Claude Code skill definition
├── convert_docs.py     # Pipeline orchestrator
└── hwp_to_pdf_cli.py   # HWP → PDF/HWPX conversion utility
```

### License

[MIT](LICENSE)
