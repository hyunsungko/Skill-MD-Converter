"""
HWP to PDF Converter - CLI Version
Agent가 자동으로 실행할 수 있는 커맨드라인 버전

Usage:
    python hwp_to_pdf_cli.py <hwp_file>                          # 단일 파일 변환
    python hwp_to_pdf_cli.py <folder>                            # 폴더 내 모든 HWP 변환
    python hwp_to_pdf_cli.py <file1> <file2> ...                 # 여러 파일 변환
    python hwp_to_pdf_cli.py --output-dir <dir> <hwp_file> ...   # 출력 디렉토리 지정
"""

import sys
import os
import argparse
from pathlib import Path

try:
    from pyhwpx import Hwp
    HAS_PYHWPX = True
except ImportError:
    HAS_PYHWPX = False


def convert_hwp_to_pdf(hwp_filepath: str, pdf_filepath: str = None, hwp_instance=None) -> bool:
    """HWP 파일을 PDF로 변환

    Args:
        hwp_filepath: HWP 파일 경로
        pdf_filepath: PDF 출력 경로 (None이면 같은 위치에 같은 이름으로 생성)
        hwp_instance: 재사용할 Hwp COM 객체 (None이면 새로 생성)

    Returns:
        bool: 변환 성공 여부
    """
    if not HAS_PYHWPX:
        print("오류: pyhwpx 라이브러리가 설치되지 않았습니다.")
        print("설치 방법: pip install pyhwpx")
        return False

    owns_hwp = hwp_instance is None
    hwp = hwp_instance

    if not os.path.exists(hwp_filepath):
        print(f"오류: 파일을 찾을 수 없습니다 - {hwp_filepath}")
        return False

    if pdf_filepath is None:
        pdf_filepath = str(Path(hwp_filepath).with_suffix(".pdf"))

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(os.path.abspath(pdf_filepath)), exist_ok=True)

    try:
        print(f"변환 중: {os.path.basename(hwp_filepath)}")

        if hwp is None:
            hwp = Hwp(visible=False)
            _register_module(hwp)

        # 파일 열기
        if not hwp.Open(hwp_filepath, "HWP", "forceopen:true;suspendpassword:true"):
            print(f"오류: HWP 파일 열기 실패 - {os.path.basename(hwp_filepath)}")
            return False

        # PDF로 저장
        if not hwp.SaveAs(pdf_filepath, "PDF"):
            print(f"오류: PDF 저장 실패 - {os.path.basename(pdf_filepath)}")
            return False

        if os.path.exists(pdf_filepath):
            print(f"완료: {pdf_filepath}")
            return True
        else:
            print("오류: PDF 파일 생성 확인 실패")
            return False

    except Exception as e:
        print(f"오류: {os.path.basename(hwp_filepath)} - {str(e)}")
        return False
    finally:
        if owns_hwp and hwp:
            try:
                hwp.Quit()
            except Exception:
                pass


def _register_module(hwp):
    """보안 승인 모듈 등록 및 메시지박스 모드 설정"""
    try:
        try:
            hwp.RegisterModule("FilePathCheckDLL", "AutomationModule")
        except Exception:
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModuleExample")
            except Exception:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    except Exception:
        pass

    try:
        hwp.SetMessageBoxMode(0x00010000)
    except Exception:
        try:
            hwp.set_message_box_mode(0x00010000)
        except Exception:
            pass


def create_hwp_instance():
    """재사용 가능한 Hwp COM 인스턴스 생성

    Returns:
        Hwp 인스턴스 또는 None (생성 실패 시)
    """
    if not HAS_PYHWPX:
        return None
    try:
        hwp = Hwp(visible=False)
        _register_module(hwp)
        return hwp
    except Exception as e:
        print(f"오류: Hwp COM 인스턴스 생성 실패 - {str(e)}")
        return None


def quit_hwp_instance(hwp):
    """Hwp COM 인스턴스 종료"""
    if hwp:
        try:
            hwp.Quit()
        except Exception:
            pass


def find_hwp_files(path: str) -> list:
    """경로에서 HWP 파일 찾기"""
    path = Path(path)

    if path.is_file():
        if path.suffix.lower() in ['.hwp', '.hwpx']:
            return [str(path)]
        else:
            return []
    elif path.is_dir():
        files = []
        for ext in ['*.hwp', '*.hwpx', '*.HWP', '*.HWPX']:
            files.extend([str(f) for f in path.glob(ext)])
        return sorted(files)
    else:
        return []


def main():
    parser = argparse.ArgumentParser(description="HWP to PDF Converter")
    parser.add_argument("files", nargs="+", help="HWP 파일 또는 폴더 경로")
    parser.add_argument("--output-dir", "-o", help="PDF 출력 디렉토리 (기본: 원본과 같은 위치)")
    args = parser.parse_args()

    if not HAS_PYHWPX:
        print("오류: pyhwpx 라이브러리가 설치되지 않았습니다.")
        print("설치 방법: pip install pyhwpx")
        sys.exit(1)

    # 모든 인자에서 HWP 파일 수집
    hwp_files = []
    for path in args.files:
        found = find_hwp_files(path)
        if found:
            hwp_files.extend(found)
        else:
            print(f"경고: HWP 파일을 찾을 수 없습니다 - {path}")

    if not hwp_files:
        print("변환할 HWP 파일이 없습니다.")
        sys.exit(1)

    # 중복 제거
    hwp_files = list(dict.fromkeys(hwp_files))

    print(f"\n총 {len(hwp_files)}개 파일 변환 시작")
    print("=" * 50)

    # COM 재사용으로 배치 변환
    hwp = create_hwp_instance()
    if hwp is None:
        print("오류: Hwp COM 인스턴스를 생성할 수 없습니다.")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    try:
        for hwp_file in hwp_files:
            if args.output_dir:
                pdf_name = Path(hwp_file).with_suffix(".pdf").name
                pdf_path = str(Path(args.output_dir) / pdf_name)
            else:
                pdf_path = None

            if convert_hwp_to_pdf(hwp_file, pdf_path, hwp_instance=hwp):
                success_count += 1
            else:
                fail_count += 1
    finally:
        quit_hwp_instance(hwp)

    print("=" * 50)
    print(f"변환 완료: 성공 {success_count}개, 실패 {fail_count}개")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
