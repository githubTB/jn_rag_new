from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from core.di import get_container

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])

# 获取依赖注入容器
container = get_container()


@router.get("/search")
async def search(
    task_id: str | None = Query(None, description="限定任务范围"),
    query: str | None = Query(None, description="搜索关键词"),
):
    logger.info("[Search] task_id=%s query=%s", task_id, query)
    return JSONResponse(
        {
            "ok": True,
            "message": "搜索功能待接入向量检索流程",
            "task_id": task_id,
            "query": query,
            "results": [],
        }
    )
