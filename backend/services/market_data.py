"""市场看板数据聚合 — 多数据源 + 缓存 + 并行获取"""
import re
import time
import logging
import concurrent.futures

from utils import clear_proxy_env, safe_float, TTLCache

clear_proxy_env()

import requests
import akshare as ak

logger = logging.getLogger("market_data")

_cache = TTLCache()
CACHE_TTL = 60


# ── 指数行情（Sina 源）───────────────────────────────────────────────────────

def get_index_overview() -> list[dict]:
    """获取主要指数实时行情"""
    def fetch():
        df = ak.stock_zh_index_spot_sina()
        focus_codes = {"sh000001", "sz399001", "sz399006", "sh000688", "sh000300"}
        focus_names = {"上证指数", "深证成指", "创业板指", "科创50", "沪深300"}
        results = []
        for _, r in df.iterrows():
            code = str(r["代码"])
            name = str(r["名称"])
            if code in focus_codes or name in focus_names:
                results.append({
                    "name": name,
                    "code": code,
                    "price": safe_float(r.get("最新价", 0)),
                    "change_pct": safe_float(r.get("涨跌幅", 0)),
                    "change_amt": safe_float(r.get("涨跌额", 0)),
                    "volume": safe_float(r.get("成交量", 0)),
                    "amount": safe_float(r.get("成交额", 0)),
                })
        seen = set()
        deduped = []
        for item in results:
            key = item["name"]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped
    return _cache.get("index_overview", fetch, ttl=CACHE_TTL)


# ── 涨跌幅排行（直连 Sina API，服务端排序）────────────────────────────────────

SINA_API = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
SINA_TIMEOUT = 15
SINA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _sina_spot_page(page=1, num=80, sort="changepercent", asc=0):
    """直连 Sina API 获取单页 A 股行情"""
    params = {
        "page": page, "num": num, "sort": sort, "asc": asc,
        "node": "hs_a", "symbol": "", "_s_r_a": "page",
    }
    resp = requests.get(SINA_API, params=params, headers=SINA_HEADERS, timeout=SINA_TIMEOUT)
    resp.encoding = "gb2312"
    return resp.json()


def _parse_sina_row(r: dict) -> dict:
    return {
        "symbol": str(r.get("code", "")),
        "name": str(r.get("name", "")),
        "price": safe_float(r.get("trade", 0)),
        "change_pct": safe_float(r.get("changepercent", 0)),
        "change_amt": safe_float(r.get("pricechange", 0)),
        "volume": safe_float(r.get("volume", 0)),
        "amount": safe_float(r.get("amount", 0)),
    }


def _is_junk_stock(name: str) -> bool:
    return bool(re.search(r"ST|退|N\b", str(name)))


def _sina_sorted_top(n: int, asc: int = 0) -> list[dict]:
    """从 Sina 获取涨跌幅前 N，分页获取直到凑够"""
    results = []
    seen = set()
    for page in range(1, 6):
        try:
            rows = _sina_spot_page(page=page, num=80, sort="changepercent", asc=asc)
        except Exception as e:
            logger.warning("Sina sorted page %d failed: %s", page, e)
            break
        if not rows:
            break
        for r in rows:
            name = str(r.get("name", ""))
            if _is_junk_stock(name):
                continue
            symbol = str(r.get("code", ""))
            if symbol in seen:
                continue
            seen.add(symbol)
            price = safe_float(r.get("trade", 0))
            if price <= 0:
                continue
            pct = safe_float(r.get("changepercent", 0))
            if abs(pct) > 19.5:
                continue
            results.append(_parse_sina_row(r))
            if len(results) >= n:
                return results[:n]
    return results[:n]


def get_top_gainers(n: int = 10) -> list[dict]:
    return _cache.get(f"gainers_{n}", lambda: _sina_sorted_top(n, asc=0), ttl=120)


def get_top_losers(n: int = 10) -> list[dict]:
    return _cache.get(f"losers_{n}", lambda: _sina_sorted_top(n, asc=1), ttl=120)


# ── 板块 ───────────────────────────────────────────────────────────────────────

def get_hot_sectors(n: int = 10) -> list[dict]:
    def fetch():
        try:
            df = ak.stock_board_industry_name_em()
            df_sorted = df.nlargest(n, "涨跌幅")
            return [
                {
                    "name": str(r["板块名称"]),
                    "code": str(r.get("板块代码", "")),
                    "change_pct": safe_float(r.get("涨跌幅", 0)),
                    "up_count": int(r.get("上涨家数", 0) or 0),
                    "down_count": int(r.get("下跌家数", 0) or 0),
                    "leader": str(r.get("领涨股票", "")),
                    "leader_change": safe_float(r.get("领涨股票-涨跌幅", 0)),
                }
                for _, r in df_sorted.iterrows()
            ]
        except Exception as e:
            logger.info("东方财富行业板块获取失败，使用降级方案: %s", e)
            return _get_sectors_fallback(n)
    return _cache.get(f"sectors_{n}", fetch, ttl=CACHE_TTL)


def get_hot_concepts(n: int = 10) -> list[dict]:
    def fetch():
        try:
            df = ak.stock_board_concept_name_em()
            df_sorted = df.nlargest(n, "涨跌幅")
            return [
                {
                    "name": str(r["板块名称"]),
                    "code": str(r.get("板块代码", "")),
                    "change_pct": safe_float(r.get("涨跌幅", 0)),
                    "up_count": int(r.get("上涨家数", 0) or 0),
                    "down_count": int(r.get("下跌家数", 0) or 0),
                    "leader": str(r.get("领涨股票", "")),
                    "leader_change": safe_float(r.get("领涨股票-涨跌幅", 0)),
                }
                for _, r in df_sorted.iterrows()
            ]
        except Exception as e:
            logger.info("东方财富概念板块获取失败，使用降级方案: %s", e)
            return _get_sectors_fallback(n)
    return _cache.get(f"concepts_{n}", fetch, ttl=CACHE_TTL)


def _get_sectors_fallback(n: int) -> list[dict]:
    try:
        all_rows = _sina_sorted_top(200, asc=0)
        if not all_rows:
            return []
        results = []
        for stock in all_rows[:n * 2]:
            results.append({
                "name": stock["name"],
                "code": stock["symbol"],
                "change_pct": stock["change_pct"],
                "up_count": 0,
                "down_count": 0,
                "leader": stock["name"],
                "leader_change": stock["change_pct"],
            })
        return results[:n]
    except Exception as e:
        logger.warning("板块降级数据获取失败: %s", e)
        return []


# ── 热门推荐 ──────────────────────────────────────────────────────────────────

def get_hot_stocks(n: int = 8) -> list[dict]:
    def fetch():
        try:
            df = ak.stock_hot_rank_em().head(n * 2)
            results = []
            for _, r in df.iterrows():
                raw_code = str(r["代码"])
                symbol = re.sub(r'^(SH|SZ|BJ)', '', raw_code)
                results.append({
                    "symbol": symbol,
                    "name": str(r["股票名称"]),
                    "price": safe_float(r.get("最新价", 0)),
                    "change_pct": safe_float(r.get("涨跌幅", 0)),
                    "rank": int(r.get("当前排名", 999)),
                    "source": "hot_rank",
                })
            return sorted(results, key=lambda x: x["rank"])[:n]
        except Exception as e:
            logger.info("东方财富热榜获取失败，使用成交量降级方案: %s", e)

        try:
            rows = _sina_sorted_top(100, asc=0)
            filtered = [r for r in rows if r["price"] > 5 and 0 < r["change_pct"] < 19.5]
            filtered.sort(key=lambda x: x["volume"], reverse=True)
            results = []
            for i, r in enumerate(filtered[:n]):
                results.append({
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "price": r["price"],
                    "change_pct": r["change_pct"],
                    "rank": i + 1,
                    "source": "active",
                })
            return results
        except Exception as e:
            logger.warning("热门推荐降级方案失败: %s", e)
            return []
    return _cache.get(f"hot_stocks_{n}", fetch, ttl=300)


# ── 市场广度（乐股乐股源）────────────────────────────────────────────────────

def get_market_breadth() -> dict:
    def fetch():
        try:
            df = ak.stock_market_activity_legu()
            if df is not None and not df.empty:
                mapping = {}
                for _, r in df.iterrows():
                    mapping[str(r["item"])] = str(r["value"])

                def _int(key):
                    try:
                        return int(float(mapping.get(key, "0")))
                    except (ValueError, KeyError):
                        return 0

                return {
                    "up": _int("上涨"),
                    "down": _int("下跌"),
                    "flat": _int("平盘"),
                    "suspended": _int("停牌"),
                    "limit_up": _int("涨停"),
                    "limit_down": _int("跌停"),
                    "real_limit_up": _int("真实涨停"),
                    "real_limit_down": _int("真实跌停"),
                    "activity": safe_float(mapping.get("活跃度", "0").replace("%", "")),
                }
        except Exception as e:
            logger.warning("市场广度获取失败: %s", e)
        return {"up": 0, "down": 0, "flat": 0, "suspended": 0, "limit_up": 0, "limit_down": 0, "real_limit_up": 0, "real_limit_down": 0, "activity": 0}
    return _cache.get("market_breadth", fetch, ttl=CACHE_TTL)


# ── 看板聚合 ──────────────────────────────────────────────────────────────────

def get_dashboard_data() -> dict:
    """并行获取所有看板数据"""
    result = {}
    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            "indices": pool.submit(_safe_fetch, get_index_overview),
            "top_gainers": pool.submit(_safe_fetch, get_top_gainers, 10),
            "top_losers": pool.submit(_safe_fetch, get_top_losers, 10),
            "hot_sectors": pool.submit(_safe_fetch, get_hot_sectors, 10),
            "hot_concepts": pool.submit(_safe_fetch, get_hot_concepts, 10),
            "hot_stocks": pool.submit(_safe_fetch, get_hot_stocks, 8),
            "market_breadth": pool.submit(_safe_fetch, get_market_breadth),
        }

        for key, fut in futures.items():
            try:
                result[key] = fut.result(timeout=60)
            except Exception as e:
                logger.error("看板数据获取失败 %s: %s", key, e)
                result[key] = [] if key != "market_breadth" else {}
                errors.append(key)

    result["errors"] = errors
    result["timestamp"] = time.time()
    return result


def _safe_fetch(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        logger.debug("看板子项获取失败 %s: %s", getattr(fn, '__name__', fn), e)
        if fn is get_market_breadth:
            return {"up": 0, "down": 0, "flat": 0, "suspended": 0,
                    "limit_up": 0, "limit_down": 0, "real_limit_up": 0,
                    "real_limit_down": 0, "activity": 0}
        return []
