"""
convert_docs.py의 scan_documents, filter_changed, compute_sha256 단위 테스트
"""

import hashlib
import os
import sys
from pathlib import Path

import pytest

# 프로젝트 루트를 sys.path에 추가하여 convert_docs를 임포트할 수 있도록 한다
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convert_docs import compute_sha256, filter_changed, scan_documents


# ═══════════════════════════════════════════════════════════
# compute_sha256 테스트
# ═══════════════════════════════════════════════════════════
class TestComputeSha256:
    """compute_sha256() 해시 계산 정확성 테스트"""

    def test_empty_file(self, tmp_path):
        """빈 파일의 SHA256 해시가 올바르게 계산되는지 확인"""
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert compute_sha256(str(f)) == expected

    def test_known_content(self, tmp_path):
        """알려진 내용의 SHA256 해시가 정확한지 확인"""
        content = b"hello world"
        f = tmp_path / "hello.txt"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(str(f)) == expected

    def test_binary_content(self, tmp_path):
        """바이너리 데이터의 해시가 올바르게 계산되는지 확인"""
        content = bytes(range(256)) * 100  # 25,600 바이트
        f = tmp_path / "binary.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(str(f)) == expected

    def test_large_file_chunked_read(self, tmp_path):
        """8192 바이트를 넘는 파일도 정확하게 해시 계산되는지 확인 (청크 읽기 검증)"""
        content = b"A" * 20000  # 8192 * 2 이상
        f = tmp_path / "large.dat"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(str(f)) == expected

    def test_same_content_same_hash(self, tmp_path):
        """동일한 내용의 두 파일이 같은 해시를 반환하는지 확인"""
        content = b"same content"
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert compute_sha256(str(f1)) == compute_sha256(str(f2))

    def test_different_content_different_hash(self, tmp_path):
        """다른 내용의 두 파일이 다른 해시를 반환하는지 확인"""
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert compute_sha256(str(f1)) != compute_sha256(str(f2))


# ═══════════════════════════════════════════════════════════
# scan_documents 테스트
# ═══════════════════════════════════════════════════════════
class TestScanDocuments:
    """scan_documents() 파일 스캔 및 필터링 테스트"""

    def test_supported_extensions_only(self, tmp_path):
        """지원되는 확장자만 스캔 결과에 포함되는지 확인"""
        # 지원 포맷 파일 생성
        (tmp_path / "doc.hwp").write_bytes(b"")
        (tmp_path / "doc.hwpx").write_bytes(b"")
        (tmp_path / "doc.pptx").write_bytes(b"")
        (tmp_path / "doc.docx").write_bytes(b"")
        (tmp_path / "doc.xlsx").write_bytes(b"")
        (tmp_path / "doc.ppt").write_bytes(b"")
        (tmp_path / "doc.doc").write_bytes(b"")
        (tmp_path / "doc.xls").write_bytes(b"")
        # 비지원 포맷
        (tmp_path / "readme.md").write_bytes(b"")
        (tmp_path / "script.py").write_bytes(b"")
        (tmp_path / "image.png").write_bytes(b"")
        (tmp_path / "data.json").write_bytes(b"")
        (tmp_path / "notes.txt").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        filenames = {d["filename"] for d in results}

        # 지원 포맷은 모두 포함
        assert "doc.hwp" in filenames
        assert "doc.hwpx" in filenames
        assert "doc.pptx" in filenames
        assert "doc.docx" in filenames
        assert "doc.xlsx" in filenames
        assert "doc.ppt" in filenames
        assert "doc.doc" in filenames
        assert "doc.xls" in filenames

        # 비지원 포맷은 제외
        assert "readme.md" not in filenames
        assert "script.py" not in filenames
        assert "image.png" not in filenames
        assert "data.json" not in filenames
        assert "notes.txt" not in filenames

    def test_result_structure(self, tmp_path):
        """반환 결과의 구조(path, filename, extension)가 올바른지 확인"""
        (tmp_path / "report.docx").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        assert len(results) == 1
        doc = results[0]
        assert "path" in doc
        assert "filename" in doc
        assert "extension" in doc
        assert doc["filename"] == "report.docx"
        assert doc["extension"] == ".docx"
        assert os.path.isabs(doc["path"])

    def test_case_insensitive_extension(self, tmp_path):
        """대소문자가 섞인 확장자도 올바르게 스캔되는지 확인"""
        (tmp_path / "DOC.HWP").write_bytes(b"")
        (tmp_path / "Doc.Pptx").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        filenames = {d["filename"] for d in results}
        assert "DOC.HWP" in filenames
        assert "Doc.Pptx" in filenames
        # extension은 소문자로 정규화
        extensions = {d["extension"] for d in results}
        assert ".hwp" in extensions
        assert ".pptx" in extensions

    def test_empty_directory(self, tmp_path):
        """빈 디렉토리를 스캔하면 빈 목록이 반환되는지 확인"""
        results = scan_documents(str(tmp_path))
        assert results == []

    def test_no_supported_files(self, tmp_path):
        """지원 포맷이 없는 디렉토리를 스캔하면 빈 목록이 반환되는지 확인"""
        (tmp_path / "readme.md").write_bytes(b"")
        (tmp_path / "script.py").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        assert results == []

    def test_sorted_by_filename(self, tmp_path):
        """결과가 파일명 기준으로 정렬되는지 확인"""
        (tmp_path / "zebra.docx").write_bytes(b"")
        (tmp_path / "alpha.hwp").write_bytes(b"")
        (tmp_path / "middle.pptx").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        filenames = [d["filename"] for d in results]
        assert filenames == sorted(filenames)

    def test_does_not_recurse_subdirectories(self, tmp_path):
        """하위 디렉토리는 스캔하지 않는지 확인 (root.iterdir는 재귀하지 않음)"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.docx").write_bytes(b"")
        (tmp_path / "top.docx").write_bytes(b"")

        results = scan_documents(str(tmp_path))
        filenames = {d["filename"] for d in results}
        assert "top.docx" in filenames
        assert "nested.docx" not in filenames

    # ── specific_files 모드 ───────────────────────────────

    def test_specific_files_existing(self, tmp_path):
        """specific_files로 존재하는 특정 파일만 스캔되는지 확인"""
        f1 = tmp_path / "target.hwp"
        f2 = tmp_path / "ignore_me.docx"
        f1.write_bytes(b"")
        f2.write_bytes(b"")

        results = scan_documents(str(tmp_path), specific_files=[str(f1)])
        assert len(results) == 1
        assert results[0]["filename"] == "target.hwp"

    def test_specific_files_nonexistent(self, tmp_path):
        """specific_files에 존재하지 않는 파일 경로가 포함되면 무시되는지 확인"""
        fake_path = str(tmp_path / "nonexistent.docx")

        results = scan_documents(str(tmp_path), specific_files=[fake_path])
        assert results == []

    def test_specific_files_unsupported_extension(self, tmp_path):
        """specific_files에 비지원 확장자가 포함되면 무시되는지 확인"""
        f = tmp_path / "data.csv"
        f.write_bytes(b"")

        results = scan_documents(str(tmp_path), specific_files=[str(f)])
        assert results == []

    def test_specific_files_mixed(self, tmp_path):
        """specific_files에 지원/비지원/존재하지 않는 파일이 섞여 있을 때 올바르게 필터링"""
        valid = tmp_path / "report.xlsx"
        invalid_ext = tmp_path / "notes.txt"
        valid.write_bytes(b"")
        invalid_ext.write_bytes(b"")
        nonexistent = str(tmp_path / "ghost.docx")

        results = scan_documents(
            str(tmp_path),
            specific_files=[str(valid), str(invalid_ext), nonexistent],
        )
        assert len(results) == 1
        assert results[0]["filename"] == "report.xlsx"


# ═══════════════════════════════════════════════════════════
# filter_changed 테스트
# ═══════════════════════════════════════════════════════════
class TestFilterChanged:
    """filter_changed() 증분 감지 테스트"""

    def _make_doc_entry(self, tmp_path, name, content=b""):
        """테스트용 문서 딕셔너리와 파일을 생성하는 헬퍼"""
        f = tmp_path / name
        f.write_bytes(content)
        ext = Path(name).suffix.lower()
        return {
            "path": str(f.resolve()),
            "filename": name,
            "extension": ext,
        }

    def test_new_file_detected(self, tmp_path):
        """manifest에 없는 신규 파일이 변경 대상으로 감지되는지 확인"""
        doc = self._make_doc_entry(tmp_path, "new_report.docx", b"new content")
        manifest = {"files": []}

        result = filter_changed([doc], manifest)
        assert len(result) == 1
        assert result[0]["filename"] == "new_report.docx"

    def test_unchanged_file_excluded(self, tmp_path):
        """manifest의 해시와 동일한 파일은 결과에서 제외되는지 확인"""
        content = b"unchanged content"
        doc = self._make_doc_entry(tmp_path, "stable.hwp", content)
        file_hash = hashlib.sha256(content).hexdigest()
        manifest = {
            "files": [
                {"filename": "stable.hwp", "sha256": file_hash}
            ]
        }

        result = filter_changed([doc], manifest)
        assert len(result) == 0

    def test_changed_file_detected(self, tmp_path):
        """파일 내용이 변경되면 (해시 불일치) 변경 대상으로 감지되는지 확인"""
        doc = self._make_doc_entry(tmp_path, "updated.pptx", b"new version")
        old_hash = hashlib.sha256(b"old version").hexdigest()
        manifest = {
            "files": [
                {"filename": "updated.pptx", "sha256": old_hash}
            ]
        }

        result = filter_changed([doc], manifest)
        assert len(result) == 1
        assert result[0]["filename"] == "updated.pptx"

    def test_force_mode_returns_all(self, tmp_path):
        """force=True일 때 모든 문서가 반환되는지 확인"""
        content = b"some content"
        doc = self._make_doc_entry(tmp_path, "forced.docx", content)
        file_hash = hashlib.sha256(content).hexdigest()
        manifest = {
            "files": [
                {"filename": "forced.docx", "sha256": file_hash}
            ]
        }

        # 해시가 같아도 force=True면 반환
        result = filter_changed([doc], manifest, force=True)
        assert len(result) == 1
        assert result[0]["filename"] == "forced.docx"

    def test_force_mode_with_empty_manifest(self, tmp_path):
        """force=True + 빈 manifest에서도 모든 문서가 반환되는지 확인"""
        doc = self._make_doc_entry(tmp_path, "doc.xlsx", b"data")
        manifest = {"files": []}

        result = filter_changed([doc], manifest, force=True)
        assert len(result) == 1

    def test_no_changes(self, tmp_path):
        """모든 파일이 변경되지 않았을 때 빈 목록이 반환되는지 확인"""
        content1 = b"content one"
        content2 = b"content two"
        doc1 = self._make_doc_entry(tmp_path, "file1.docx", content1)
        doc2 = self._make_doc_entry(tmp_path, "file2.hwp", content2)
        manifest = {
            "files": [
                {"filename": "file1.docx", "sha256": hashlib.sha256(content1).hexdigest()},
                {"filename": "file2.hwp", "sha256": hashlib.sha256(content2).hexdigest()},
            ]
        }

        result = filter_changed([doc1, doc2], manifest)
        assert len(result) == 0

    def test_mixed_new_and_unchanged(self, tmp_path):
        """신규 파일과 변경 없는 파일이 섞여 있을 때 신규 파일만 반환되는지 확인"""
        existing_content = b"existing"
        doc_existing = self._make_doc_entry(tmp_path, "old.docx", existing_content)
        doc_new = self._make_doc_entry(tmp_path, "brand_new.pptx", b"new stuff")
        manifest = {
            "files": [
                {
                    "filename": "old.docx",
                    "sha256": hashlib.sha256(existing_content).hexdigest(),
                }
            ]
        }

        result = filter_changed([doc_existing, doc_new], manifest)
        assert len(result) == 1
        assert result[0]["filename"] == "brand_new.pptx"

    def test_empty_documents_list(self, tmp_path):
        """빈 문서 목록이 입력되면 빈 결과가 반환되는지 확인"""
        manifest = {"files": [{"filename": "something.hwp", "sha256": "abc123"}]}

        result = filter_changed([], manifest)
        assert result == []

    def test_manifest_entry_missing_sha256(self, tmp_path):
        """manifest 항목에 sha256 키가 없으면 변경으로 감지되는지 확인"""
        doc = self._make_doc_entry(tmp_path, "no_hash.docx", b"content")
        manifest = {
            "files": [
                {"filename": "no_hash.docx"}  # sha256 키 없음
            ]
        }

        result = filter_changed([doc], manifest)
        assert len(result) == 1
        assert result[0]["filename"] == "no_hash.docx"
