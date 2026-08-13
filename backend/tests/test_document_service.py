"""
Tests for upload validation added to document_service.py:
- filename sanitization (path traversal protection)
- extension allowlist
- size limit
No database needed — validate_upload() and _sanitize_file_name() are pure.
"""
import pytest

from app.document_service import (
    validate_upload,
    _sanitize_file_name,
    UploadValidationError,
    MAX_UPLOAD_BYTES,
)


def test_sanitize_strips_directory_traversal():
    assert _sanitize_file_name("../../etc/passwd") == "passwd"
    assert _sanitize_file_name("../../../secrets.txt") == "secrets.txt"


def test_sanitize_strips_windows_path():
    assert _sanitize_file_name("C:\\Windows\\win.ini") == "C__Windows_win.ini"


def test_sanitize_replaces_unsafe_characters():
    result = _sanitize_file_name("weird<>name?.pdf")
    assert "<" not in result and ">" not in result and "?" not in result
    assert result.endswith(".pdf")


def test_sanitize_rejects_empty_name():
    with pytest.raises(UploadValidationError):
        _sanitize_file_name("")


def test_validate_upload_accepts_known_extensions():
    for ext in ["pdf", "docx", "txt", "csv", "xlsx"]:
        name = validate_upload(b"some content", f"contract.{ext}")
        assert name == f"contract.{ext}"


def test_validate_upload_rejects_unknown_extension():
    with pytest.raises(UploadValidationError):
        validate_upload(b"malicious", "script.exe")


def test_validate_upload_rejects_empty_file():
    with pytest.raises(UploadValidationError):
        validate_upload(b"", "empty.pdf")


def test_validate_upload_rejects_oversized_file():
    too_big = b"x" * (MAX_UPLOAD_BYTES + 1)
    with pytest.raises(UploadValidationError):
        validate_upload(too_big, "huge.pdf")


def test_validate_upload_sanitizes_traversal_before_type_check():
    # even a well-disguised traversal attempt should end up safe on disk
    name = validate_upload(b"data", "../../evil.pdf")
    assert "/" not in name and "\\" not in name
