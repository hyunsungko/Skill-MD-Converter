"""convert_docs.py의 manifest 관련 함수 단위 테스트"""

import json
import os

import pytest

import convert_docs


# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """모든 테스트에서 OUTPUT_DIR / MANIFEST_PATH를 임시 경로로 격리."""
    output_dir = str(tmp_path / "AI_Context")
    manifest_path = os.path.join(output_dir, "_manifest.json")
    monkeypatch.setattr(convert_docs, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(convert_docs, "MANIFEST_PATH", manifest_path)


# ── load_manifest() ───────────────────────────────────────


class TestLoadManifest:
    """load_manifest() 테스트"""

    def test_file_not_exists(self):
        """manifest 파일이 없으면 빈 manifest 반환"""
        result = convert_docs.load_manifest()
        assert result == {"files": []}

    def test_valid_json(self, tmp_path):
        """정상 JSON 로드"""
        manifest_data = {
            "files": [
                {"filename": "test.hwp", "sha256": "abc123", "status": "converted"}
            ]
        }
        os.makedirs(os.path.dirname(convert_docs.MANIFEST_PATH), exist_ok=True)
        with open(convert_docs.MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        result = convert_docs.load_manifest()
        assert result == manifest_data
        assert len(result["files"]) == 1
        assert result["files"][0]["filename"] == "test.hwp"

    def test_corrupted_json(self, tmp_path, capsys):
        """손상된 JSON이면 빈 manifest 반환 + 경고 출력"""
        os.makedirs(os.path.dirname(convert_docs.MANIFEST_PATH), exist_ok=True)
        with open(convert_docs.MANIFEST_PATH, "w", encoding="utf-8") as f:
            f.write("{invalid json!!")

        result = convert_docs.load_manifest()
        assert result == {"files": []}

        captured = capsys.readouterr()
        assert "손상" in captured.out

    def test_missing_files_key(self, tmp_path):
        """'files' 키가 없는 JSON이면 빈 files 리스트 추가"""
        data_without_files = {"version": 1, "meta": "something"}
        os.makedirs(os.path.dirname(convert_docs.MANIFEST_PATH), exist_ok=True)
        with open(convert_docs.MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(data_without_files, f)

        result = convert_docs.load_manifest()
        assert "files" in result
        assert result["files"] == []
        # 기존 키는 보존
        assert result["version"] == 1


# ── save_manifest() ───────────────────────────────────────


class TestSaveManifest:
    """save_manifest() 테스트"""

    def test_save_normal(self):
        """정상 저장 및 내용 검증"""
        manifest = {
            "files": [
                {"filename": "a.docx", "status": "converted"}
            ]
        }
        convert_docs.save_manifest(manifest)

        assert os.path.exists(convert_docs.MANIFEST_PATH)
        with open(convert_docs.MANIFEST_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == manifest

    def test_creates_directory(self):
        """OUTPUT_DIR이 없으면 자동 생성"""
        assert not os.path.exists(convert_docs.OUTPUT_DIR)

        manifest = {"files": []}
        convert_docs.save_manifest(manifest)

        assert os.path.isdir(convert_docs.OUTPUT_DIR)
        assert os.path.exists(convert_docs.MANIFEST_PATH)


# ── find_in_manifest() ───────────────────────────────────


class TestFindInManifest:
    """find_in_manifest() 테스트"""

    def test_found(self):
        """존재하는 항목 검색"""
        manifest = {
            "files": [
                {"filename": "alpha.hwp", "sha256": "aaa"},
                {"filename": "beta.docx", "sha256": "bbb"},
            ]
        }
        result = convert_docs.find_in_manifest(manifest, "beta.docx")
        assert result is not None
        assert result["sha256"] == "bbb"

    def test_not_found(self):
        """없는 항목 검색 시 None 반환"""
        manifest = {
            "files": [
                {"filename": "alpha.hwp", "sha256": "aaa"},
            ]
        }
        result = convert_docs.find_in_manifest(manifest, "nonexistent.xlsx")
        assert result is None


# ── _update_manifest_entry() ──────────────────────────────


class TestUpdateManifestEntry:
    """_update_manifest_entry() 테스트"""

    def test_add_new_entry(self):
        """신규 항목 추가"""
        manifest = {"files": []}
        convert_docs._update_manifest_entry(
            manifest, "new.pptx", "/path/to/new.pptx",
            sha256="hash123", status="converted",
        )

        assert len(manifest["files"]) == 1
        entry = manifest["files"][0]
        assert entry["filename"] == "new.pptx"
        assert entry["path"] == "/path/to/new.pptx"
        assert entry["sha256"] == "hash123"
        assert entry["status"] == "converted"
        assert "converted_at" in entry

    def test_update_existing_entry(self):
        """기존 항목 업데이트 — 값이 덮어써지고, 배열 길이는 유지"""
        manifest = {
            "files": [
                {"filename": "exist.docx", "path": "/old/path", "status": "failed",
                 "error": "변환 실패"}
            ]
        }
        convert_docs._update_manifest_entry(
            manifest, "exist.docx", "/new/path",
            sha256="newhash", status="converted",
        )

        assert len(manifest["files"]) == 1
        entry = manifest["files"][0]
        assert entry["path"] == "/new/path"
        assert entry["status"] == "converted"
        assert entry["sha256"] == "newhash"
        # error는 명시적으로 삭제하지 않았으므로 남아있음
        assert entry["error"] == "변환 실패"

    def test_remove_key_with_none(self):
        """error=None을 전달하면 entry에서 error 키 삭제"""
        manifest = {
            "files": [
                {"filename": "doc.xlsx", "path": "/p", "status": "failed",
                 "error": "some error"}
            ]
        }
        convert_docs._update_manifest_entry(
            manifest, "doc.xlsx", "/p",
            status="converted", error=None,
        )

        entry = manifest["files"][0]
        assert entry["status"] == "converted"
        assert "error" not in entry

    def test_none_for_nonexistent_key_is_noop(self):
        """존재하지 않는 키에 None을 전달해도 오류 없이 무시"""
        manifest = {
            "files": [
                {"filename": "doc.xlsx", "path": "/p", "status": "converted"}
            ]
        }
        # error 키가 없는 상태에서 error=None 전달
        convert_docs._update_manifest_entry(
            manifest, "doc.xlsx", "/p",
            error=None,
        )

        entry = manifest["files"][0]
        assert "error" not in entry
