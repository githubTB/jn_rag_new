from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import settings
from models.upload import UploadBatchResult, UploadedFileRecord


class UploadRepository:
    """Stores deduplicated file metadata and task bindings in SQLite."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or settings.db_path)

    def initialize(self) -> None:
        """Create tables needed for company registration, file dedup, and task binding."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    task_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    credit_code TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS upload_batches (
                    task_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    company_credit_code TEXT,
                    chapter TEXT NOT NULL,
                    cache_root TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS stored_files (
                    id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    cache_path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    content_type TEXT,
                    bucket TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    object_url TEXT NOT NULL,
                    etag TEXT,
                    version_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS task_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    stored_file_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    cache_path TEXT NOT NULL,
                    reused_existing INTEGER NOT NULL DEFAULT 0,
                    processing_required INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES upload_batches(task_id) ON DELETE CASCADE,
                    FOREIGN KEY(stored_file_id) REFERENCES stored_files(id) ON DELETE CASCADE,
                    UNIQUE(task_id, relative_path)
                );

                CREATE INDEX IF NOT EXISTS idx_stored_files_hash
                ON stored_files(content_hash);

                CREATE INDEX IF NOT EXISTS idx_task_files_task_id
                ON task_files(task_id);
                """
            )

    def register_company(
        self,
        *,
        task_id: str,
        company_name: str,
        company_credit_code: str | None,
    ) -> None:
        """Persist task-to-company binding, updating repeated uploads safely."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO companies (task_id, company_name, credit_code)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    credit_code = COALESCE(excluded.credit_code, companies.credit_code)
                """,
                (task_id, company_name, company_credit_code),
            )

    def get_stored_file_by_hash(self, content_hash: str) -> dict[str, object] | None:
        """Return globally stored file metadata for the given content hash."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, content_hash, filename, cache_path, size, content_type,
                       bucket, object_key, object_url, etag, version_id
                FROM stored_files
                WHERE content_hash = ?
                """,
                (content_hash,),
            ).fetchone()
        return dict(row) if row else None

    def save_stored_file(
        self,
        *,
        stored_file_id: str,
        content_hash: str,
        filename: str,
        cache_path: str,
        size: int,
        content_type: str | None,
        bucket: str,
        object_key: str,
        object_url: str,
        etag: str | None,
        version_id: str | None,
    ) -> None:
        """Persist the canonical single-copy record for a newly stored file."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO stored_files (
                    id, content_hash, filename, cache_path, size, content_type,
                    bucket, object_key, object_url, etag, version_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    filename = excluded.filename,
                    cache_path = excluded.cache_path,
                    size = excluded.size,
                    content_type = excluded.content_type,
                    bucket = excluded.bucket,
                    object_key = excluded.object_key,
                    object_url = excluded.object_url,
                    etag = excluded.etag,
                    version_id = excluded.version_id
                """,
                (
                    stored_file_id,
                    content_hash,
                    filename,
                    cache_path,
                    size,
                    content_type,
                    bucket,
                    object_key,
                    object_url,
                    etag,
                    version_id,
                ),
            )

    def save_batch(self, batch: UploadBatchResult) -> None:
        """Replace one task's upload binding snapshot while preserving global dedup records."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM task_files WHERE task_id = ?", (batch.task_id,))
            conn.execute("DELETE FROM upload_batches WHERE task_id = ?", (batch.task_id,))
            conn.execute(
                """
                INSERT INTO upload_batches (
                    task_id, company_name, company_credit_code, chapter,
                    cache_root, bucket, file_count, total_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.task_id,
                    batch.company_name,
                    batch.company_credit_code,
                    batch.chapter,
                    batch.cache_root,
                    batch.bucket,
                    batch.file_count,
                    batch.total_bytes,
                ),
            )
            conn.executemany(
                """
                INSERT INTO task_files (
                    task_id, stored_file_id, filename, relative_path, cache_path,
                    reused_existing, processing_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch.task_id,
                        file.content_hash,
                        file.filename,
                        file.relative_path,
                        file.cache_path,
                        1 if file.deduplicated else 0,
                        1 if file.processing_required else 0,
                    )
                    for file in batch.files
                ],
            )

    def get_batch(self, task_id: str) -> UploadBatchResult | None:
        """Load one task batch with task-scoped bindings and global file metadata."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            batch_row = conn.execute(
                """
                SELECT task_id, company_name, company_credit_code, chapter,
                       cache_root, bucket, file_count, total_bytes
                FROM upload_batches
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if batch_row is None:
                return None

            file_rows = conn.execute(
                """
                SELECT tf.filename, tf.relative_path, tf.cache_path,
                       sf.size, sf.content_type, sf.content_hash, sf.bucket,
                       sf.object_key, sf.object_url, sf.etag, sf.version_id,
                       tf.reused_existing, tf.processing_required
                FROM task_files tf
                JOIN stored_files sf ON sf.id = tf.stored_file_id
                WHERE tf.task_id = ?
                ORDER BY tf.id ASC
                """,
                (task_id,),
            ).fetchall()

        files = [
            UploadedFileRecord(
                filename=row["filename"],
                relative_path=row["relative_path"],
                cache_path=row["cache_path"],
                size=row["size"],
                content_type=row["content_type"],
                content_hash=row["content_hash"],
                bucket=row["bucket"],
                object_key=row["object_key"],
                object_url=row["object_url"],
                etag=row["etag"],
                version_id=row["version_id"],
                deduplicated=bool(row["reused_existing"]),
                processing_required=bool(row["processing_required"]),
            )
            for row in file_rows
        ]

        return UploadBatchResult(
            task_id=batch_row["task_id"],
            company_name=batch_row["company_name"],
            company_credit_code=batch_row["company_credit_code"],
            chapter=batch_row["chapter"],
            cache_root=batch_row["cache_root"],
            bucket=batch_row["bucket"],
            sqlite_db_path=str(self.db_path),
            file_count=batch_row["file_count"],
            total_bytes=batch_row["total_bytes"],
            files=files,
        )

    def resolve_task_file_path(self, task_id: str, relative_path: str) -> str | None:
        """Resolve a task-visible relative path to the canonical stored cache path."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT cache_path
                FROM task_files
                WHERE task_id = ? AND relative_path = ?
                """,
                (task_id, relative_path),
            ).fetchone()
        return row[0] if row else None

    def reset(self) -> None:
        """Drop upload and dedup tables and recreate them for a clean state."""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                DROP TABLE IF EXISTS task_files;
                DROP TABLE IF EXISTS stored_files;
                DROP TABLE IF EXISTS upload_batches;
                DROP TABLE IF EXISTS companies;
                DROP TABLE IF EXISTS uploaded_files;
                """
            )
        self.initialize()
