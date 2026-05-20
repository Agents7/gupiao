"""Supabase 客户端 — 单例 + 表 CRUD"""
import logging
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger("supabase_client")

_supabase: Client | None = None


def get_supabase() -> Client | None:
    global _supabase
    if _supabase is not None:
        return _supabase
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("Supabase 未配置，跳过数据库操作")
        return None
    try:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase 客户端已初始化")
        return _supabase
    except Exception as e:
        logger.error("Supabase 初始化失败: %s", e)
        return None
