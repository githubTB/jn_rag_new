from __future__ import annotations

from enum import Enum


class DocType(str, Enum):
    """文档类型枚举"""
    UNKNOWN = "unknown"
    DOCUMENT = "document"
    TABLE = "table"
    LICENSE = "license"
    INVOICE = "invoice"
    NAMEPLATE = "nameplate"
