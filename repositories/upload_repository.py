from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import settings
from core.base import BaseRepository
from models.upload import UploadBatchResult, UploadedFileRecord


class UploadRepository(BaseRepository):
    """Stores deduplicated file metadata and task bindings in SQLite."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        super().__init__()
        self.db_path = Path(db_path or settings.db_path)

    def initialize(self) -> None:
        """Create tables needed for company registration, file dedup, and task binding."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    credit_code TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS upload_batches (
                    task_id TEXT PRIMARY KEY,
                    company_credit_code TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    cache_root TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(company_credit_code) REFERENCES companies(credit_code) ON DELETE CASCADE
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

                CREATE INDEX IF NOT EXISTS idx_upload_batches_company
                ON upload_batches(company_credit_code);
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
            # 注册企业信息（以credit_code为准）
            if batch.company_credit_code:
                conn.execute(
                    """
                    INSERT INTO companies (credit_code, company_name)
                    VALUES (?, ?)
                    ON CONFLICT(credit_code) DO UPDATE SET
                        company_name = excluded.company_name
                    """,
                    (batch.company_credit_code, batch.company_name),
                )
            # 清理旧数据
            conn.execute("DELETE FROM task_files WHERE task_id = ?", (batch.task_id,))
            conn.execute("DELETE FROM upload_batches WHERE task_id = ?", (batch.task_id,))
            # 保存批次信息
            conn.execute(
                """
                INSERT INTO upload_batches (
                    task_id, company_credit_code, company_name, chapter,
                    cache_root, bucket, file_count, total_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.task_id,
                    batch.company_credit_code,
                    batch.company_name,
                    batch.chapter,
                    batch.cache_root,
                    batch.bucket,
                    batch.file_count,
                    batch.total_bytes,
                ),
            )
            
            # 先插入stored_files表
            for file in batch.files:
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
                        file.content_hash,
                        file.content_hash,
                        file.filename,
                        file.cache_path,
                        file.size,
                        file.content_type,
                        file.bucket,
                        file.object_key,
                        file.object_url,
                        file.etag,
                        file.version_id,
                    ),
                )
            
            # 再插入task_files表
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
                SELECT tf.id as file_id, tf.filename, tf.relative_path, tf.cache_path,
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
                file_id=str(row["file_id"]),
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

    def get_companies(self) -> list[dict[str, str | None | int]]:
        """获取企业列表"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT c.credit_code, c.company_name, c.created_at,
                       COUNT(DISTINCT ub.task_id) as task_count,
                       SUM(ub.file_count) as file_count,
                       0 as done_count,
                       0 as confirmed_count
                FROM companies c
                LEFT JOIN upload_batches ub ON c.credit_code = ub.company_credit_code
                GROUP BY c.credit_code
                ORDER BY c.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_company_by_task_id(self, task_id: str) -> dict[str, str | None] | None:
        """根据task_id获取企业详情"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT c.credit_code, c.company_name, c.created_at, ub.task_id
                FROM companies c
                JOIN upload_batches ub ON c.credit_code = ub.company_credit_code
                WHERE ub.task_id = ?
                """,
                (task_id,),
            ).fetchone()
        return dict(row) if row else None
        
    def get_company_by_credit_code(self, credit_code: str) -> dict[str, any] | None:
        """根据信用代码获取企业详细信息"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 获取企业基本信息
            company_row = conn.execute(
                """
                SELECT credit_code, company_name, created_at
                FROM companies
                WHERE credit_code = ?
                """,
                (credit_code,)
            ).fetchone()
            
            if not company_row:
                return None
            
            # 获取企业的任务批次
            batches_rows = conn.execute(
                """
                SELECT task_id, company_credit_code, company_name, chapter, 
                       cache_root, bucket, file_count, total_bytes, created_at
                FROM upload_batches
                WHERE company_credit_code = ?
                ORDER BY created_at DESC
                """,
                (credit_code,)
            ).fetchall()
            
            batches = [
                {
                    "task_id": row["task_id"],
                    "company_credit_code": row["company_credit_code"],
                    "company_name": row["company_name"],
                    "chapter": row["chapter"],
                    "cache_root": row["cache_root"],
                    "bucket": row["bucket"],
                    "file_count": row["file_count"],
                    "total_bytes": row["total_bytes"],
                    "created_at": row["created_at"]
                }
                for row in batches_rows
            ]
            
            # 获取企业的所有文件
            files_rows = conn.execute(
                """
                SELECT sf.id, sf.filename, tf.relative_path, sf.cache_path, 
                       sf.size, sf.content_type, sf.content_hash, sf.bucket, 
                       sf.object_key, sf.object_url, sf.etag, sf.version_id,
                       tf.reused_existing, tf.processing_required
                FROM stored_files sf
                JOIN task_files tf ON sf.id = tf.stored_file_id
                JOIN upload_batches ub ON tf.task_id = ub.task_id
                WHERE ub.company_credit_code = ?
                """,
                (credit_code,)
            ).fetchall()
            
            files = [
                {
                    "file_id": row["id"],
                    "filename": row["filename"],
                    "relative_path": row["relative_path"],
                    "cache_path": row["cache_path"],
                    "size": row["size"],
                    "content_type": row["content_type"],
                    "content_hash": row["content_hash"],
                    "bucket": row["bucket"],
                    "object_key": row["object_key"],
                    "object_url": row["object_url"],
                    "etag": row["etag"],
                    "version_id": row["version_id"],
                    "deduplicated": bool(row["reused_existing"]),
                    "processing_required": bool(row["processing_required"])
                }
                for row in files_rows
            ]
            
            # 获取最新的上传批次信息
            latest_batch = batches[0] if batches else None
            upload_batch = {
                "chapter": latest_batch["chapter"] if latest_batch else "",
                "file_count": latest_batch["file_count"] if latest_batch else 0,
                "total_bytes": latest_batch["total_bytes"] if latest_batch else 0
            }
            
            return {
                "credit_code": company_row["credit_code"],
                "company_name": company_row["company_name"],
                "created_at": company_row["created_at"],
                "batches": batches,
                "files": files,
                "upload_batch": upload_batch
            }
            
    def get_task_id_by_file_id(self, file_id: str) -> str | None:
        """根据文件ID获取任务ID"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT task_id
                FROM task_files
                WHERE stored_file_id = ?
                """,
                (file_id,)
            ).fetchone()
        
        return row["task_id"] if row else None
        
    def get_file_info(self, file_id: str) -> dict[str, any] | None:
        """根据文件ID获取文件信息"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT tf.task_id, tf.filename, tf.relative_path, tf.stored_file_id,
                       sf.cache_path, sf.bucket, sf.object_key
                FROM task_files tf
                JOIN stored_files sf ON tf.stored_file_id = sf.id
                WHERE tf.id = ? OR tf.stored_file_id = ?
                """,
                (file_id, file_id),
            ).fetchone()
        
        return dict(row) if row else None
        
    def replace_file(self, file_id: str, new_file: UploadedFileRecord) -> None:
        """替换文件并更新数据库记录"""
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            
            # 检查文件是否已经存在（去重逻辑）
            existing_file = conn.execute(
                "SELECT id FROM stored_files WHERE content_hash = ?",
                (new_file.content_hash,),
            ).fetchone()
            
            is_deduplicated = False
            if existing_file:
                # 如果文件已经存在，直接使用 existing_file_id
                stored_file_id = existing_file["id"]
                is_deduplicated = True
            else:
                # 使用content_hash作为file_id，与save_batch方法保持一致
                stored_file_id = new_file.content_hash
                # 插入新的stored_files记录
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stored_files (
                        id, content_hash, filename, cache_path, size, content_type,
                        bucket, object_key, object_url, etag, version_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stored_file_id,
                        new_file.content_hash,
                        new_file.filename,
                        new_file.cache_path,
                        new_file.size,
                        new_file.content_type,
                        new_file.bucket,
                        new_file.object_key,
                        new_file.object_url,
                        new_file.etag,
                        new_file.version_id,
                    ),
                )
            
            # 从task_files中获取任务ID和相对路径
            row = conn.execute(
                "SELECT task_id, relative_path FROM task_files WHERE stored_file_id = ?",
                (file_id,)
            ).fetchone()
            
            if not row:
                raise ValueError("文件不存在")
            
            task_id = row["task_id"]
            relative_path = row["relative_path"]
            
            # 更新task_files记录，只更新当前任务的文件关系
            conn.execute(
                """
                UPDATE task_files
                SET stored_file_id = ?, filename = ?, cache_path = ?, 
                    reused_existing = ?, processing_required = 1
                WHERE task_id = ? AND relative_path = ?
                """,
                (
                    stored_file_id,
                    new_file.filename,
                    new_file.cache_path,
                    1 if is_deduplicated else 0,
                    task_id,
                    relative_path,
                ),
            )
            
            # 更新upload_batches的file_count和total_bytes
            conn.execute(
                """
                UPDATE upload_batches
                SET file_count = (SELECT COUNT(*) FROM task_files WHERE task_id = ?),
                    total_bytes = COALESCE((SELECT SUM(sf.size) FROM task_files tf JOIN stored_files sf ON tf.stored_file_id = sf.id WHERE tf.task_id = ?), 0)
                WHERE task_id = ?
                """,
                (task_id, task_id, task_id),
            )

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

    def close(self) -> None:
        """关闭仓储连接"""
        # SQLite连接是自动管理的，这里不需要特殊处理
        self.logger.info("关闭UploadRepository连接")
