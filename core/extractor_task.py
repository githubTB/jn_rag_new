"""
core/extractor_task.py — 完整入库流水线。

串联：文件上传 -> Hash去重 → 存入 MinIO → 解析 → 切片 → Chunk 去重 → 向量化 → 落库Milvus → 元数据写入SQLite → 标记完成

使用示例
--------
    from core.tasks import IngestTask

    # 单文件，带企业和类型
    result = IngestTask.run(
        "uploads/营业执照.jpg",
        task_id="task_001",
        doc_type="license",
    )

    # 同步调用（适合调试）
    result = IngestTask.run("uploads/合同.pdf", task_id="task_001", sync=True)

    # 异步（FastAPI BackgroundTasks）
    background_tasks.add_task(IngestTask.run, file_path, task_id=task_id, doc_type=doc_type)
"""
