"""共享工具：代理清理、数值转换、JSON 解析、缓存、K线构建"""
import os
import re
import json
import time
import logging
import threading

logger = logging.getLogger("utils")


# ── 代理清理 ─────────────────────────────────────────────────────────────────

_proxy_cleared = False


def clear_proxy_env():
    """清除环境中可能残留的不可用代理（如 Clash 127.0.0.1:7890）"""
    global _proxy_cleared
    if _proxy_cleared:
        return
    for key in list(os.environ.keys()):
        if "proxy" in key.lower():
            del os.environ[key]
    os.environ["no_proxy"] = "*"
    _proxy_cleared = True


# ── 数值转换 ─────────────────────────────────────────────────────────────────

def safe_float(val) -> float:
    """安全转换为 float，处理 None、空字符串、'-'、'nan'"""
    try:
        return float(val) if val is not None and str(val) not in ("", "-", "nan") else 0.0
    except (ValueError, TypeError):
        return 0.0


# ── JSON 解析 ────────────────────────────────────────────────────────────────

def parse_llm_json(content: str) -> dict:
    """解析 LLM 返回的 JSON，带花括号提取回退"""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # 回退：提取第一个 { ... } 块
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        return json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"无法解析 LLM 回复为 JSON") from e


# ── K线构建 ──────────────────────────────────────────────────────────────────

def build_kline_row(r, col_map: dict) -> dict:
    """根据列名映射构建统一的 K 线条目"""
    return {
        "date": str(r[col_map["date"]]),
        "open": safe_float(r.get(col_map.get("open", ""), 0)),
        "close": safe_float(r.get(col_map.get("close", ""), 0)),
        "high": safe_float(r.get(col_map.get("high", ""), 0)),
        "low": safe_float(r.get(col_map.get("low", ""), 0)),
        "volume": safe_float(r.get(col_map.get("volume", ""), 0)),
        "change_pct": safe_float(r.get(col_map.get("change_pct", ""), 0)),
    }


# ── 线程安全缓存 ─────────────────────────────────────────────────────────────

class TTLCache:
    """线程安全的 TTL 缓存"""

    def __init__(self):
        self._cache: dict = {}
        self._locks: dict = {}
        self._lock_lock = threading.Lock()

    def _get_lock(self, key: str) -> threading.Lock:
        with self._lock_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get(self, key: str, fetcher, ttl: int = 60):
        now = time.time()
        if key in self._cache:
            data, ts = self._cache[key]
            if now - ts < ttl:
                return data

        lock = self._get_lock(key)
        with lock:
            # 双重检查
            if key in self._cache:
                data, ts = self._cache[key]
                if time.time() - ts < ttl:
                    return data
            try:
                data = fetcher()
                self._cache[key] = (data, time.time())
                return data
            except Exception as e:
                logger.warning("缓存获取失败 %s: %s", key, e)
                if key in self._cache:
                    return self._cache[key][0]
                raise

    def clear(self, key: str = None):
        """清除指定 key 或全部缓存"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


# ── 股票代码检测 ─────────────────────────────────────────────────────────────

def detect_market(symbol: str) -> str:
    """识别股票代码所属市场"""
    s = str(symbol).upper().strip()
    if s.isdigit() and len(s) == 6:
        return "A股"
    if s.isdigit() and len(s) == 5:
        return "港股"
    if s.isalpha() and 1 <= len(s) <= 5:
        return "美股"
    return "unknown"
