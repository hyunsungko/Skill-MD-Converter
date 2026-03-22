"""
convert_docs.py 에러 핸들링 단위 테스트

테스트 대상:
    1. _run_with_timeout() - 정상 완료, 타임아웃 발생, 예외 발생
    2. convert_with_markitdown() - markitdown 미설치 시 처리, 빈 출력 처리, 타임아웃
    3. check_dependencies() - 의존성 있을 때/없을 때 상태 딕셔너리 확인
"""

import os
import sys
import time
import subprocess
from unittest import mock

import pytest

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convert_docs import _run_with_timeout, convert_with_markitdown, check_dependencies


# ════════════════════════════════════════════════════════════
# 1. _run_with_timeout 테스트
# ════════════════════════════════════════════════════════════

class TestRunWithTimeout:
    """_run_with_timeout 함수에 대한 테스트"""

    def test_normal_completion(self):
        """정상적으로 완료되는 함수는 True를 반환해야 한다."""
        def success_func():
            return True

        result = _run_with_timeout(success_func, timeout=5)
        assert result is True

    def test_normal_completion_returns_false(self):
        """함수가 False를 반환하면 _run_with_timeout도 False를 반환해야 한다."""
        def fail_func():
            return False

        result = _run_with_timeout(fail_func, timeout=5)
        assert result is False

    def test_timeout_occurs(self):
        """함수가 타임아웃 시간을 초과하면 False를 반환해야 한다."""
        def slow_func():
            time.sleep(3)
            return True

        result = _run_with_timeout(slow_func, timeout=1)
        assert result is False

    def test_exception_in_function(self):
        """함수 내부에서 예외가 발생하면 False를 반환해야 한다."""
        def error_func():
            raise ValueError("테스트 예외")

        result = _run_with_timeout(error_func, timeout=5)
        assert result is False

    def test_exception_message_printed(self, capsys):
        """함수 내부에서 예외 발생 시 오류 메시지가 출력되어야 한다."""
        def error_func():
            raise RuntimeError("심각한 오류")

        _run_with_timeout(error_func, timeout=5)
        captured = capsys.readouterr()
        assert "심각한 오류" in captured.out

    def test_timeout_message_printed(self, capsys):
        """타임아웃 발생 시 타임아웃 메시지가 출력되어야 한다."""
        def slow_func():
            time.sleep(3)
            return True

        _run_with_timeout(slow_func, timeout=1)
        captured = capsys.readouterr()
        assert "타임아웃" in captured.out


# ════════════════════════════════════════════════════════════
# 2. convert_with_markitdown 테스트
# ════════════════════════════════════════════════════════════

class TestConvertWithMarkitdown:
    """convert_with_markitdown 함수에 대한 테스트"""

    def test_markitdown_not_installed(self, tmp_path):
        """markitdown이 설치되지 않았을 때(subprocess 실패) None을 반환해야 한다."""
        # 더미 파일 생성
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=1,
                stderr=b"No module named markitdown",
                stdout=b"",
            )
            result = convert_with_markitdown(str(test_file))

        assert result is None

    def test_markitdown_not_installed_message(self, tmp_path, capsys):
        """markitdown 실패 시 오류 메시지가 출력되어야 한다."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=1,
                stderr=b"No module named markitdown",
                stdout=b"",
            )
            convert_with_markitdown(str(test_file))

        captured = capsys.readouterr()
        assert "markitdown 실패" in captured.out

    def test_empty_output(self, tmp_path):
        """markitdown 출력이 비어 있으면 None을 반환해야 한다."""
        test_file = tmp_path / "test.pptx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stderr=b"",
                stdout=b"",
            )
            result = convert_with_markitdown(str(test_file))

        assert result is None

    def test_empty_output_message(self, tmp_path, capsys):
        """비어 있는 출력 시 적절한 오류 메시지가 출력되어야 한다."""
        test_file = tmp_path / "test.pptx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stderr=b"",
                stdout=b"",
            )
            convert_with_markitdown(str(test_file))

        captured = capsys.readouterr()
        assert "비어있습니다" in captured.out

    def test_whitespace_only_output(self, tmp_path):
        """공백만 있는 출력도 비어 있는 것으로 처리해야 한다."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stderr=b"",
                stdout=b"   \n  \n  ",
            )
            result = convert_with_markitdown(str(test_file))

        assert result is None

    def test_timeout(self, tmp_path):
        """markitdown 실행이 타임아웃되면 None을 반환해야 한다."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="markitdown", timeout=120
            )
            result = convert_with_markitdown(str(test_file))

        assert result is None

    def test_timeout_message(self, tmp_path, capsys):
        """타임아웃 발생 시 적절한 오류 메시지가 출력되어야 한다."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="markitdown", timeout=120
            )
            convert_with_markitdown(str(test_file))

        captured = capsys.readouterr()
        assert "타임아웃" in captured.out

    def test_successful_conversion(self, tmp_path):
        """정상 변환 시 raw MD 파일 경로를 반환해야 한다."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        md_content = "# 제목\n\n본문 내용입니다."

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stderr=b"",
                stdout=md_content.encode("utf-8"),
            )
            # INTERMEDIATE_DIR을 tmp_path 하위로 패치
            with mock.patch("convert_docs.INTERMEDIATE_DIR", str(tmp_path / "_intermediate")):
                result = convert_with_markitdown(str(test_file))

        assert result is not None
        assert result.endswith(".raw.md")
        assert os.path.exists(result)

    def test_generic_exception(self, tmp_path):
        """예상치 못한 예외 발생 시 None을 반환해야 한다."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("파일 시스템 오류")
            result = convert_with_markitdown(str(test_file))

        assert result is None


# ════════════════════════════════════════════════════════════
# 3. check_dependencies 테스트
# ════════════════════════════════════════════════════════════

class TestCheckDependencies:
    """check_dependencies 함수에 대한 테스트"""

    def test_all_dependencies_missing(self):
        """모든 의존성이 없을 때 상태 딕셔너리가 올바르게 반환되어야 한다."""
        with mock.patch.dict("sys.modules", {
            "pyhwpx": None,
            "markitdown": None,
            "pptx": None,
            "mammoth": None,
            "openpyxl": None,
            "hwpx": None,
            "hwpx.tools": None,
            "hwpx.tools.text_extractor": None,
        }):
            # None은 이미 import 시도되었지만 실패한 것을 시뮬레이션
            # import 시 ImportError를 발생시키도록 builtins.__import__를 패치
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            blocked_modules = {"pyhwpx", "markitdown", "pptx", "mammoth", "openpyxl",
                               "hwpx", "hwpx.tools", "hwpx.tools.text_extractor"}

            def mock_import(name, *args, **kwargs):
                if name in blocked_modules:
                    raise ImportError(f"Mocked: No module named '{name}'")
                return original_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=mock_import):
                status = check_dependencies()

        assert status["hwp"] is False
        assert status["markitdown"] is False
        # markitdown이 없으면 pptx/docx/xlsx 검사는 스킵되므로 기본값 False
        assert status["pptx"] is False
        assert status["docx"] is False
        assert status["xlsx"] is False

    def test_all_dependencies_present(self):
        """모든 의존성이 있을 때 상태 딕셔너리가 올바르게 반환되어야 한다."""
        # 가짜 모듈 객체 생성
        fake_pyhwpx = mock.MagicMock()
        fake_markitdown = mock.MagicMock()
        fake_pptx = mock.MagicMock()
        fake_mammoth = mock.MagicMock()
        fake_openpyxl = mock.MagicMock()
        fake_hwpx = mock.MagicMock()
        fake_hwpx_tools = mock.MagicMock()
        fake_hwpx_text_extractor = mock.MagicMock()
        fake_hwpx_text_extractor.TextExtractor = mock.MagicMock()

        modules_dict = {
            "pyhwpx": fake_pyhwpx,
            "markitdown": fake_markitdown,
            "pptx": fake_pptx,
            "mammoth": fake_mammoth,
            "openpyxl": fake_openpyxl,
            "hwpx": fake_hwpx,
            "hwpx.tools": fake_hwpx_tools,
            "hwpx.tools.text_extractor": fake_hwpx_text_extractor,
        }

        with mock.patch.dict("sys.modules", modules_dict):
            status = check_dependencies()

        assert status["hwp"] is True
        assert status["markitdown"] is True
        assert status["pptx"] is True
        assert status["docx"] is True
        assert status["xlsx"] is True
        assert status["hwpx_extractor"] is True

    def test_only_markitdown_present(self):
        """markitdown만 있고 extras가 없을 때 상태를 올바르게 반환해야 한다."""
        fake_markitdown = mock.MagicMock()

        original_import = __import__

        blocked_extras = {"pyhwpx", "pptx", "mammoth", "openpyxl",
                          "hwpx", "hwpx.tools", "hwpx.tools.text_extractor"}

        def mock_import(name, *args, **kwargs):
            if name == "markitdown":
                return fake_markitdown
            if name in blocked_extras:
                raise ImportError(f"Mocked: No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            status = check_dependencies()

        assert status["hwp"] is False
        assert status["markitdown"] is True
        assert status["pptx"] is False
        assert status["docx"] is False
        assert status["xlsx"] is False

    def test_returns_dict_type(self):
        """check_dependencies는 항상 dict를 반환해야 한다."""
        # import를 모킹하지 않고 실제 환경에서 실행
        status = check_dependencies()
        assert isinstance(status, dict)
        # 필수 키들이 존재하는지 확인
        assert "hwp" in status
        assert "markitdown" in status
        assert "pptx" in status
        assert "docx" in status
        assert "xlsx" in status

    def test_missing_message_printed_when_deps_missing(self, capsys):
        """의존성이 없을 때 경고 메시지가 출력되어야 한다."""
        original_import = __import__
        blocked_modules = {"pyhwpx", "markitdown", "pptx", "mammoth", "openpyxl",
                           "hwpx", "hwpx.tools", "hwpx.tools.text_extractor"}

        def mock_import(name, *args, **kwargs):
            if name in blocked_modules:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            check_dependencies()

        captured = capsys.readouterr()
        assert "의존성 미설치" in captured.out
