from __future__ import annotations

import mimetypes
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import app
from api.routes import ingest as ingest_route
from repositories.upload_repository import UploadRepository
from services.storage import UploadedObject
from services.upload_service import UploadService


class FakeMinioStorageService:
    """Keeps unit tests deterministic without depending on real object storage."""

    def __init__(self) -> None:
        self.bucket = "test-rag-documents"

    def upload_file(self, *, source_path: Path, object_key: str, content_type: str | None = None):
        assert source_path.exists()
        return UploadedObject(
            bucket=self.bucket,
            object_key=object_key,
            etag="fake-etag",
            version_id="fake-version",
        )

    def presigned_get_url(self, *, object_key: str, expires=None) -> str:
        return f"http://minio.test/{self.bucket}/{object_key}"


def _sample_files_from_project_root() -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    sample_files = [
        path
        for path in project_root.iterdir()
        if path.is_file() and path.suffix.lower() in {".doc", ".docx", ".pdf", ".txt", ".md"}
    ]
    assert sample_files, f"{project_root} 根目录下至少需要一个可上传样例文件"
    preferred_suffixes = [".docx", ".pdf", ".doc", ".md", ".txt"]
    for suffix in preferred_suffixes:
        preferred = [path for path in sample_files if path.suffix.lower() == suffix]
        if preferred:
            return [preferred[0]]
    return [sample_files[0]]


def _build_test_client() -> TestClient:
    return TestClient(app)


def _real_local_url_from_response(cache_url: str) -> str:
    base_url = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return base_url + urlsplit(cache_url).path


def _build_client_request(sample_files: list[Path]):
    multipart_files = []
    opened_files = []
    try:
        for file_path in sample_files:
            mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            file_obj = file_path.open("rb")
            opened_files.append(file_obj)
            multipart_files.append(("files", (file_path.name, file_obj, mime_type)))

        client = _build_test_client()
        response = client.post(
            "/api/upload/folder",
            data={
                "task_id": "test-task-001",
                "company_name": "测试企业",
                "company_credit_code": "91500000TEST000001",
                "chapter": "基础资料",
                "relative_paths": [file_path.name for file_path in sample_files],
            },
            files=multipart_files,
        )
        return response
    finally:
        for file_obj in opened_files:
            file_obj.close()


def test_upload_folder_simulates_frontend_request(tmp_path, monkeypatch) -> None:
    sample_files = _sample_files_from_project_root()
    upload_root = tmp_path / "uploads"
    db_path = tmp_path / "rag_meta.db"

    def _service_factory() -> UploadService:
        return UploadService(
            upload_root=upload_root,
            storage=FakeMinioStorageService(),
            repository=UploadRepository(db_path),
        )

    monkeypatch.setattr(ingest_route, "UploadService", _service_factory)
    monkeypatch.setattr(ingest_route, "UploadRepository", lambda: UploadRepository(db_path))
    response = _build_client_request(sample_files)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert payload["task_id"] == "test-task-001"
    assert payload["company_name"] == "测试企业"
    assert payload["file_count"] == len(sample_files)
    assert payload["sqlite_db_path"] == str(db_path)

    uploaded = payload["files"][0]
    assert uploaded["bucket"] == "test-rag-documents"
    assert uploaded["object_key"].startswith("test-task-001/")
    assert Path(uploaded["cache_path"]).exists()
    assert "/api/files/test-task-001/" in uploaded["cache_url"]
    assert uploaded["object_url"].startswith("http://minio.test/test-rag-documents/")

    with sqlite3.connect(db_path) as conn:
        batch_row = conn.execute(
            "SELECT company_name, chapter, file_count FROM upload_batches WHERE task_id = ?",
            ("test-task-001",),
        ).fetchone()
        file_row = conn.execute(
            "SELECT bucket, object_key FROM uploaded_files WHERE task_id = ? LIMIT 1",
            ("test-task-001",),
        ).fetchone()

    assert batch_row == ("测试企业", "基础资料", len(sample_files))
    assert file_row is not None
    assert file_row[0] == "test-rag-documents"
    assert file_row[1].startswith("test-task-001/")

    query_response = _build_test_client().get("/api/upload/test-task-001")
    assert query_response.status_code == 200, query_response.text
    query_payload = query_response.json()
    assert query_payload["task_id"] == "test-task-001"
    assert query_payload["company_name"] == "测试企业"
    assert query_payload["file_count"] == len(sample_files)
    assert query_payload["sqlite_db_path"] == str(db_path)
    assert query_payload["files"][0]["object_key"].startswith("test-task-001/")


@pytest.mark.integration
def test_upload_folder_with_real_minio() -> None:
    run_flag = os.environ.get("RUN_MINIO_UPLOAD_TEST", "").lower()
    if run_flag not in {"1", "true", "yes"}:
        pytest.skip("设置 RUN_MINIO_UPLOAD_TEST=1 后执行真实 MinIO 集成测试")

    sample_files = _sample_files_from_project_root()
    response = _build_client_request(sample_files)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert payload["bucket"] == "rag-documents"

    first_file = payload["files"][0]
    assert first_file["object_url"].startswith("http")
    assert Path(first_file["cache_path"]).exists()
    assert "/uploads/test-task-001/" in first_file["cache_path"]
    print(f"Local file URL: {_real_local_url_from_response(first_file['cache_url'])}")
    print(f"MinIO file URL: {first_file['object_url']}")


# 运行测试
# 上传存储 MinIO 配置
# venv/bin/python -m pytest tests/test_upload.py -s
# APP_BASE_URL=http://127.0.0.1:8000 RUN_MINIO_UPLOAD_TEST=1 venv/bin/python -m pytest tests/test_upload.py -s -k real_minio
