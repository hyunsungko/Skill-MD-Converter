"""
Document-to-Context Converter
프로젝트 루트의 문서 파일(HWP, PPTX, DOCX, XLSX)을 Markdown으로 변환하고
AI_Context/ 폴더에 구조화된 결과를 저장하는 파이프라인 오케스트레이터.

Usage:
    python convert_docs.py                    # 프로젝트 루트 스캔 및 변환
    python convert_docs.py --scan-only        # 변환 대상만 확인
    python convert_docs.py --force            # 모든 파일 강제 재변환
    python convert_docs.py <file1> <file2>    # 특정 파일만 변환
"""

import sys
import os
import json
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 설정 ────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {'.hwp', '.hwpx', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'}
HWP_EXTENSIONS = {'.hwp', '.hwpx'}
OUTPUT_DIR = "AI_Context"
INTERMEDIATE_DIR = os.path.join(OUTPUT_DIR, "_intermediate")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "_manifest.json")
HWP_TIMEOUT_SECONDS = 120


# ── 의존성 검사 ─────────────────────────────────────────
def check_dependencies() -> dict:
    """의존성 설치 상태 확인. 포맷별 지원 여부를 반환."""
    status = {"hwp": False, "pptx": False, "docx": False, "xlsx": False, "markitdown": False}
    missing = []

    # pyhwpx (HWP 변환)
    try:
        import pyhwpx  # noqa: F401
        status["hwp"] = True
    except ImportError:
        missing.append("pyhwpx (HWP 변환): pip install pyhwpx")

    # markitdown (PPT/Word/Excel/PDF 변환)
    try:
        import markitdown  # noqa: F401
        status["markitdown"] = True
    except ImportError:
        missing.append("markitdown (문서→MD 변환): pip install 'markitdown[all]'")

    # markitdown extras 개별 확인
    if status["markitdown"]:
        try:
            import pptx  # noqa: F401
            status["pptx"] = True
        except ImportError:
            missing.append("python-pptx (PPT 변환): pip install 'markitdown[all]'")

        try:
            import mammoth  # noqa: F401
            status["docx"] = True
        except ImportError:
            missing.append("mammoth (Word 변환): pip install 'markitdown[all]'")

        try:
            import openpyxl  # noqa: F401
            status["xlsx"] = True
        except ImportError:
            missing.append("openpyxl (Excel 변환): pip install 'markitdown[all]'")

    # python-hwpx (HWPX 텍스트 추출 — HWP 변환의 핵심 의존성)
    try:
        from hwpx.tools.text_extractor import TextExtractor  # noqa: F401
        status["hwpx_extractor"] = True
    except ImportError:
        status["hwpx_extractor"] = False
        missing.append("python-hwpx (HWPX 텍스트 추출): pip install python-hwpx")

    if missing:
        print("⚠ 일부 의존성 미설치 (해당 포맷 변환 불가):")
        for m in missing:
            print(f"  - {m}")
        print()

    return status


# ── SHA256 해시 ──────────────────────────────────────────
def compute_sha256(filepath: str) -> str:
    """파일의 SHA256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ── Manifest 관리 ────────────────────────────────────────
def load_manifest() -> dict:
    """_manifest.json 로드. 없거나 손상 시 빈 manifest 반환."""
    if not os.path.exists(MANIFEST_PATH):
        return {"files": []}
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "files" not in data:
            data["files"] = []
        return data
    except (json.JSONDecodeError, IOError):
        print("⚠ _manifest.json 손상 — 새로 생성합니다.")
        return {"files": []}


def save_manifest(manifest: dict):
    """_manifest.json 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def find_in_manifest(manifest: dict, filename: str) -> dict | None:
    """manifest에서 파일 항목 찾기"""
    for entry in manifest["files"]:
        if entry.get("filename") == filename:
            return entry
    return None


# ── 파일 스캔 ────────────────────────────────────────────
def scan_documents(root_dir: str, specific_files: list = None) -> list:
    """프로젝트 루트에서 지원 포맷 문서 파일 스캔

    Args:
        root_dir: 스캔할 디렉토리
        specific_files: 특정 파일만 처리할 경우 파일 경로 목록

    Returns:
        [{path, filename, extension}] 형태의 목록
    """
    documents = []

    if specific_files:
        for filepath in specific_files:
            p = Path(filepath)
            if p.exists() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                documents.append({
                    "path": str(p.resolve()),
                    "filename": p.name,
                    "extension": p.suffix.lower(),
                })
        return documents

    root = Path(root_dir)
    for item in root.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append({
                "path": str(item.resolve()),
                "filename": item.name,
                "extension": item.suffix.lower(),
            })

    return sorted(documents, key=lambda d: d["filename"])


def filter_changed(documents: list, manifest: dict, force: bool = False) -> list:
    """manifest와 비교하여 신규/변경된 파일만 필터링"""
    if force:
        return documents

    changed = []
    for doc in documents:
        entry = find_in_manifest(manifest, doc["filename"])
        if entry is None:
            changed.append(doc)
            continue

        current_hash = compute_sha256(doc["path"])
        if current_hash != entry.get("sha256"):
            changed.append(doc)

    return changed


# ── 변환 함수들 ──────────────────────────────────────────
def convert_hwp_to_md(hwp_path: str, hwp_instance=None) -> str | None:
    """HWP → HWPX → TextExtractor → raw MD 변환. 성공 시 raw MD 경로 반환.

    hwpxskill의 접근 방식을 차용: pyhwpx로 HWP→HWPX 변환 후,
    python-hwpx의 TextExtractor로 셀 단위 텍스트 추출.
    PDF 경유 대비 표 구조 보존률이 훨씬 높음.
    """
    from hwp_to_pdf_cli import convert_hwp_to_pdf

    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    hwpx_name = Path(hwp_path).with_suffix(".hwpx").name
    hwpx_path = os.path.join(INTERMEDIATE_DIR, hwpx_name)

    # HWP → HWPX 변환
    success = _run_with_timeout(
        lambda: _convert_hwp_to_hwpx(hwp_path, hwpx_path, hwp_instance),
        timeout=HWP_TIMEOUT_SECONDS,
    )

    if not success or not os.path.exists(hwpx_path):
        # HWPX 실패 시 PDF 경유 fallback
        print("  HWPX 변환 실패 — PDF 경유 fallback 시도...")
        pdf_name = Path(hwp_path).with_suffix(".pdf").name
        pdf_path = os.path.join(INTERMEDIATE_DIR, pdf_name)
        fb_success = _run_with_timeout(
            lambda: convert_hwp_to_pdf(hwp_path, pdf_path, hwp_instance=hwp_instance),
            timeout=HWP_TIMEOUT_SECONDS,
        )
        if fb_success and os.path.exists(pdf_path):
            return convert_with_markitdown(pdf_path)
        return None

    # HWPX → raw MD (TextExtractor)
    return _extract_hwpx_to_md(hwpx_path)


def _convert_hwp_to_hwpx(hwp_path: str, hwpx_path: str, hwp_instance=None) -> bool:
    """pyhwpx COM으로 HWP를 HWPX로 저장"""
    owns_hwp = hwp_instance is None
    hwp = hwp_instance

    try:
        if hwp is None:
            from pyhwpx import Hwp
            hwp = Hwp(visible=False)
            from hwp_to_pdf_cli import _register_module
            _register_module(hwp)

        if not hwp.Open(hwp_path, "HWP", "forceopen:true;suspendpassword:true"):
            print(f"  오류: HWP 파일 열기 실패")
            return False

        os.makedirs(os.path.dirname(os.path.abspath(hwpx_path)), exist_ok=True)
        if not hwp.SaveAs(hwpx_path, "HWPX"):
            print(f"  오류: HWPX 저장 실패")
            return False

        return os.path.exists(hwpx_path)

    except Exception as e:
        print(f"  오류: HWP→HWPX 변환 실패 - {str(e)}")
        return False
    finally:
        if owns_hwp and hwp:
            try:
                hwp.Quit()
            except Exception:
                pass


def _extract_hwpx_to_md(hwpx_path: str) -> str | None:
    """python-hwpx TextExtractor로 HWPX에서 텍스트 추출 → raw MD 생성"""
    try:
        from hwpx.tools.text_extractor import TextExtractor
    except ImportError:
        print("  오류: python-hwpx가 설치되지 않았습니다. pip install python-hwpx")
        return None

    md_name = Path(hwpx_path).stem + ".raw.md"
    md_path = os.path.join(INTERMEDIATE_DIR, md_name)

    try:
        lines = []
        with TextExtractor(hwpx_path) as ext:
            for section in ext.iter_sections():
                for para in ext.iter_paragraphs(section, include_nested=True):
                    text = para.text(object_behavior="skip")
                    if text.strip():
                        if para.is_nested:
                            lines.append(f"[셀] {text}")
                        else:
                            lines.append(text)

        if not lines:
            print("  오류: HWPX에서 텍스트를 추출할 수 없습니다.")
            return None

        content = "\n".join(lines)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

        return md_path

    except Exception as e:
        print(f"  오류: HWPX 텍스트 추출 실패 - {str(e)}")
        return None


def convert_with_markitdown(filepath: str) -> str | None:
    """markitdown CLI로 파일을 raw MD로 변환. 성공 시 raw MD 경로 반환."""
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    md_name = Path(filepath).stem + ".raw.md"
    md_path = os.path.join(INTERMEDIATE_DIR, md_name)

    try:
        # markitdown CLI 또는 python -m markitdown 으로 실행
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-m", "markitdown", filepath],
            capture_output=True,
            timeout=120,
            env=env,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
            print(f"  오류: markitdown 실패 - {stderr_text}")
            return None

        # 출력 디코딩 (UTF-8 우선, 실패 시 cp949)
        try:
            content = result.stdout.decode("utf-8")
        except UnicodeDecodeError:
            content = result.stdout.decode("cp949", errors="replace")

        if not content or not content.strip():
            print(f"  오류: markitdown 출력이 비어있습니다 - {filepath}")
            return None

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

        return md_path

    except subprocess.TimeoutExpired:
        print(f"  오류: markitdown 타임아웃 (120초) - {filepath}")
        return None
    except Exception as e:
        print(f"  오류: markitdown 실행 실패 - {str(e)}")
        return None


def _run_with_timeout(func, timeout: int) -> bool:
    """함수를 타임아웃과 함께 실행. 별도 스레드에서 실행하여 타임아웃 적용."""
    import threading

    result = [False]
    error = [None]

    def target():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        print(f"  오류: 타임아웃 ({timeout}초) — 변환이 응답하지 않습니다.")
        return False

    if error[0]:
        print(f"  오류: 변환 실패 - {str(error[0])}")
        return False

    return result[0]


# ── 메인 파이프라인 ──────────────────────────────────────
def run_pipeline(root_dir: str, scan_only: bool = False, force: bool = False,
                 specific_files: list = None) -> dict:
    """변환 파이프라인 실행

    Returns:
        {"success": [...], "failed": [...], "skipped": [...]}
    """
    results = {"success": [], "failed": [], "skipped": []}

    # 1. 의존성 검사
    dep_status = check_dependencies()

    # 2. 파일 스캔
    all_docs = scan_documents(root_dir, specific_files)
    if not all_docs:
        print("변환 대상 문서가 없습니다.")
        return results

    print(f"발견된 문서: {len(all_docs)}개")
    for doc in all_docs:
        print(f"  - {doc['filename']} ({doc['extension']})")

    # 3. 증분 감지
    manifest = load_manifest()
    changed_docs = filter_changed(all_docs, manifest, force=force)

    if not changed_docs:
        print("\n모든 파일이 이미 변환되어 있습니다. (변경 없음)")
        return results

    print(f"\n변환 대상: {len(changed_docs)}개 (신규/변경)")

    if scan_only:
        for doc in changed_docs:
            print(f"  [대상] {doc['filename']}")
        return results

    # 4. 출력 디렉토리 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    # 5. HWP COM 인스턴스 준비 (재사용)
    hwp_instance = None
    hwp_docs = [d for d in changed_docs if d["extension"] in HWP_EXTENSIONS]
    if hwp_docs and dep_status["hwp"]:
        from hwp_to_pdf_cli import create_hwp_instance
        hwp_instance = create_hwp_instance()
        if hwp_instance is None:
            print("⚠ Hwp COM 인스턴스 생성 실패 — HWP 파일은 건너뜁니다.")

    # 6. 파일별 변환
    print("\n" + "=" * 50)
    print("변환 시작")
    print("=" * 50)

    try:
        for doc in changed_docs:
            filename = doc["filename"]
            ext = doc["extension"]
            filepath = doc["path"]

            print(f"\n[{filename}]")

            # 포맷별 지원 여부 확인
            if ext in HWP_EXTENSIONS and not dep_status["hwp"]:
                print("  건너뜀: pyhwpx 미설치")
                _update_manifest_entry(manifest, filename, filepath, status="skipped",
                                       error="pyhwpx 미설치")
                results["skipped"].append(filename)
                continue

            if ext in {'.pptx', '.ppt'} and not dep_status["pptx"]:
                print("  건너뜀: python-pptx 미설치")
                _update_manifest_entry(manifest, filename, filepath, status="skipped",
                                       error="python-pptx 미설치")
                results["skipped"].append(filename)
                continue

            if ext in {'.docx', '.doc'} and not dep_status["docx"]:
                print("  건너뜀: mammoth 미설치")
                _update_manifest_entry(manifest, filename, filepath, status="skipped",
                                       error="mammoth 미설치")
                results["skipped"].append(filename)
                continue

            if ext in {'.xlsx', '.xls'} and not dep_status["xlsx"]:
                print("  건너뜀: openpyxl 미설치")
                _update_manifest_entry(manifest, filename, filepath, status="skipped",
                                       error="openpyxl 미설치")
                results["skipped"].append(filename)
                continue

            # 변환 실행
            raw_md_path = None
            if ext in HWP_EXTENSIONS:
                raw_md_path = convert_hwp_to_md(filepath, hwp_instance=hwp_instance)
            else:
                raw_md_path = convert_with_markitdown(filepath)

            if raw_md_path and os.path.exists(raw_md_path):
                file_hash = compute_sha256(filepath)
                _update_manifest_entry(manifest, filename, filepath,
                                       sha256=file_hash,
                                       output=Path(filename).stem + ".md",
                                       raw_md=raw_md_path,
                                       status="converted",
                                       error=None)
                results["success"].append(filename)
                print(f"  ✓ raw MD 생성: {raw_md_path}")
            else:
                _update_manifest_entry(manifest, filename, filepath,
                                       status="failed", error="변환 실패")
                results["failed"].append(filename)
                print(f"  ✗ 변환 실패")

    finally:
        # COM 인스턴스 정리
        if hwp_instance:
            from hwp_to_pdf_cli import quit_hwp_instance
            quit_hwp_instance(hwp_instance)

    # 7. Manifest 저장
    save_manifest(manifest)

    # 8. 결과 보고
    print("\n" + "=" * 50)
    print("변환 결과")
    print("=" * 50)
    print(f"  성공: {len(results['success'])}개")
    if results["success"]:
        for f in results["success"]:
            print(f"    ✓ {f}")
    print(f"  실패: {len(results['failed'])}개")
    if results["failed"]:
        for f in results["failed"]:
            print(f"    ✗ {f}")
    print(f"  건너뜀: {len(results['skipped'])}개")
    if results["skipped"]:
        for f in results["skipped"]:
            print(f"    - {f}")

    return results


def _update_manifest_entry(manifest: dict, filename: str, filepath: str, **kwargs):
    """manifest 항목 업데이트 또는 추가"""
    now = datetime.now(timezone.utc).isoformat()

    entry = find_in_manifest(manifest, filename)
    if entry is None:
        entry = {"filename": filename}
        manifest["files"].append(entry)

    entry["path"] = filepath
    entry["converted_at"] = now
    for k, v in kwargs.items():
        if v is None and k in entry:
            del entry[k]
        elif v is not None:
            entry[k] = v


# ── CLI ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Document-to-Context Converter: 문서 파일을 AI가 읽을 수 있는 Markdown으로 변환"
    )
    parser.add_argument("files", nargs="*", help="변환할 특정 파일들 (생략 시 프로젝트 루트 스캔)")
    parser.add_argument("--scan-only", action="store_true", help="변환 대상만 확인하고 실제 변환은 하지 않음")
    parser.add_argument("--force", action="store_true", help="모든 파일 강제 재변환 (캐시 무시)")
    parser.add_argument("--root", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 디렉토리)")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    specific_files = args.files if args.files else None

    results = run_pipeline(
        root_dir=root_dir,
        scan_only=args.scan_only,
        force=args.force,
        specific_files=specific_files,
    )

    # 실패가 있으면 exit code 1
    if results["failed"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
