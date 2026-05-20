"""股票数据获取 — akshare 封装 + 重试 + 预取"""
import re
import time
import logging
from datetime import datetime, timedelta

from utils import clear_proxy_env, safe_float, detect_market, build_kline_row, TTLCache

clear_proxy_env()

import akshare as ak
import requests

logger = logging.getLogger("stock_api")

# ── 缓存 ─────────────────────────────────────────────────────────────────────
_quote_cache = TTLCache()
_kline_cache = TTLCache()


# ── 搜索 ─────────────────────────────────────────────────────────────────────

def search_stock(keyword: str) -> list[dict]:
    """按关键词搜索股票（带重试）"""
    results = []
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_spot_em()
            mask = df["名称"].str.contains(keyword) | df["代码"].str.contains(keyword)
            matched = df[mask].head(10)
            for _, row in matched.iterrows():
                results.append({
                    "symbol": row["代码"],
                    "name": row["名称"],
                    "price": safe_float(row.get("最新价", 0)),
                    "change_pct": safe_float(row.get("涨跌幅", 0)),
                    "market": "A股",
                })
            return results
        except Exception as e:
            logger.warning("A股搜索失败(attempt %d): %s", attempt + 1, e)
            time.sleep(1 + attempt)
    return results


def get_stock_quote(symbol: str) -> dict:
    """获取实时行情（带缓存）"""
    def fetch():
        market = detect_market(symbol)
        for attempt in range(3):
            try:
                fetchers = {
                    "A股": _get_a_stock_quote,
                    "港股": _get_hk_stock_quote,
                    "美股": _get_us_stock_quote,
                }
                fn = fetchers.get(market, _get_a_stock_quote)
                result = fn(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning("行情获取失败 %s (attempt %d): %s", symbol, attempt + 1, e)
                time.sleep(1 + attempt)
        raise ValueError(f"获取 {symbol} 行情失败，已重试3次")
    return _quote_cache.get(f"q_{symbol}", fetch, ttl=120)


def get_stock_kline(symbol: str, days: int = 30) -> list[dict]:
    """获取历史K线（带缓存），失败时返回空列表"""
    def fetch():
        market = detect_market(symbol)
        for attempt in range(3):
            try:
                fetchers = {
                    "A股": _get_a_stock_kline,
                    "港股": _get_hk_stock_kline,
                    "美股": _get_us_stock_kline,
                }
                fn = fetchers.get(market, _get_a_stock_kline)
                result = fn(symbol, days)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning("K线获取失败 %s (attempt %d): %s", symbol, attempt + 1, e)
                time.sleep(1 + attempt)
        logger.warning("K线获取最终失败 %s, 返回空列表", symbol)
        return []
    return _kline_cache.get(f"k_{symbol}_{days}", fetch, ttl=120)


# ── A 股 ────────────────────────────────────────────────────────────────────

def _eastmoney_single_quote(symbol: str, timeout: int = 10) -> dict | None:
    """直连 Eastmoney 单股 API — 轻量快速"""
    try:
        prefix = "1" if symbol.startswith("6") else "0"
        secid = f"{prefix}.{symbol}"
        url = (
            "https://push2.eastmoney.com/api/qt/stock/get"
            f"?secid={secid}"
            "&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f116,f117,f162,f167,f168,f169,f170,f171"
        )
        r = requests.get(url, timeout=timeout, proxies={"http": None, "https": None})
        if r.status_code != 200:
            return None
        d = r.json().get("data", {})
        if not d or not d.get("f57"):
            return None
        return {
            "symbol": str(d.get("f57", symbol)),
            "name": str(d.get("f58", "")),
            "price": d.get("f43", 0) / 100.0 if d.get("f43") else 0,
            "change_pct": (d.get("f170", 0) or 0) / 100.0,
            "volume": d.get("f47", 0) or 0,
            "high": (d.get("f44", 0) or 0) / 100.0,
            "low": (d.get("f45", 0) or 0) / 100.0,
            "open": (d.get("f46", 0) or 0) / 100.0,
            "market": "A股",
            "turnover_rate": (d.get("f168", 0) or 0) / 100.0,
            "pe": (d.get("f162", 0) or 0) / 100.0,
        }
    except Exception as e:
        logger.debug("Eastmoney单股API失败 %s: %s", symbol, e)
        return None


def _quick_fetch_quote(symbol: str) -> dict:
    """预取专用：调用 _eastmoney_single_quote 短超时版，失败抛异常"""
    result = _eastmoney_single_quote(symbol, timeout=5)
    if result is None:
        raise ValueError(f"快速行情获取失败: {symbol}")
    return result


def _build_quote(symbol: str, r, market: str) -> dict:
    return {
        "symbol": symbol,
        "name": str(r.get("名称", "")),
        "price": safe_float(r.get("最新价", 0)),
        "change_pct": safe_float(r.get("涨跌幅", 0)),
        "volume": safe_float(r.get("成交量", 0)),
        "high": safe_float(r.get("最高", 0)),
        "low": safe_float(r.get("最低", 0)),
        "open": safe_float(r.get("今开", 0)),
        "market": market,
        "turnover_rate": safe_float(r.get("换手率", 0)),
        "pe": safe_float(r.get("市盈率-动态", 0)),
    }


def _get_a_stock_quote(symbol: str) -> dict:
    """多数据源获取A股行情"""

    # 方案1: 直连 Eastmoney 单股 API
    try:
        result = _eastmoney_single_quote(symbol)
        if result:
            return result
    except Exception as e:
        logger.debug("方案1 Eastmoney直连失败: %s", e)

    # 方案2: akshare 雪球 API
    try:
        time.sleep(0.3)
        df = ak.stock_individual_spot_xq(symbol=symbol, timeout=10)
        if df is not None and not df.empty:
            r = df.iloc[0]
            return {
                "symbol": symbol,
                "name": str(r.get("name", r.get("名称", symbol))),
                "price": safe_float(r.get("current", r.get("最新价", 0))),
                "change_pct": safe_float(r.get("percent", r.get("涨跌幅", 0))),
                "volume": safe_float(r.get("volume", r.get("成交量", 0))),
                "high": safe_float(r.get("high", r.get("最高", 0))),
                "low": safe_float(r.get("low", r.get("最低", 0))),
                "open": safe_float(r.get("open", r.get("今开", 0))),
                "market": "A股",
                "turnover_rate": 0,
                "pe": 0,
            }
    except Exception as e:
        logger.debug("方案2 雪球API失败: %s", e)

    # 方案3: akshare 东方财富全量（慢但全面）
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == symbol]
        if not row.empty:
            return _build_quote(symbol, row.iloc[0], "A股")
    except Exception as e:
        logger.debug("方案3 东财全量失败: %s", e)

    raise ValueError(f"无法获取A股 {symbol} 行情")


_SINA_KL_COL_MAP = {
    "date": "date", "open": "open", "close": "close",
    "high": "high", "low": "low", "volume": "volume", "change_pct": "",
}
_EM_KL_COL_MAP = {
    "date": "日期", "open": "开盘", "close": "收盘",
    "high": "最高", "low": "最低", "volume": "成交量", "change_pct": "涨跌幅",
}


def _get_a_stock_kline(symbol: str, days: int) -> list[dict]:
    """获取A股K线，优先用 Sina 源（更可靠）"""

    # 方案1: Sina 日线数据
    try:
        prefix = "sh" if symbol.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{symbol}", adjust="qfq")
        if df is not None and not df.empty:
            return [build_kline_row(r, _SINA_KL_COL_MAP)
                    for _, r in df.tail(days).iterrows()]
    except Exception as e:
        logger.debug("方案1 Sina K线失败: %s", e)

    # 方案2: Eastmoney K线（备用）
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days * 4)).strftime("%Y%m%d")
        time.sleep(0.3)
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq")
        if df is not None and not df.empty:
            return [build_kline_row(r, _EM_KL_COL_MAP)
                    for _, r in df.tail(days).iterrows()]
    except Exception as e:
        logger.debug("方案2 东财K线失败: %s", e)

    return []


def _quick_fetch_kline(symbol: str) -> list[dict]:
    """预取专用：单次尝试 Sina K线，不重试"""
    try:
        prefix = "sh" if symbol.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{symbol}", adjust="qfq")
        if df is not None and not df.empty:
            return [build_kline_row(r, _SINA_KL_COL_MAP)
                    for _, r in df.tail(60).iterrows()]
        return []
    except Exception as e:
        logger.debug("K线快速预取失败 %s: %s", symbol, e)
        return []


# ── 港股 ────────────────────────────────────────────────────────────────────

def _get_hk_stock_quote(symbol: str) -> dict:
    try:
        df = ak.stock_hk_spot_em()
        row = df[df["代码"] == symbol]
        if not row.empty:
            return _build_quote(symbol, row.iloc[0], "港股")
    except Exception as e:
        logger.debug("港股行情获取失败 %s: %s", symbol, e)
    raise ValueError(f"无法获取港股 {symbol} 行情")


def _get_hk_stock_kline(symbol: str, days: int) -> list[dict]:
    try:
        df = ak.stock_hk_hist(symbol=symbol, period="daily", adjust="qfq")
        if df is not None and not df.empty:
            return [build_kline_row(r, _EM_KL_COL_MAP)
                    for _, r in df.tail(days).iterrows()]
    except Exception as e:
        logger.debug("港股K线获取失败 %s: %s", symbol, e)
    return []


# ── 美股 ────────────────────────────────────────────────────────────────────

def _get_us_stock_quote(symbol: str) -> dict:
    try:
        df = ak.stock_us_spot_em()
        row = df[df["代码"] == symbol.upper()]
        if not row.empty:
            return _build_quote(symbol.upper(), row.iloc[0], "美股")
    except Exception as e:
        logger.debug("美股行情获取失败 %s: %s", symbol, e)
    raise ValueError(f"无法获取美股 {symbol} 行情")


def _get_us_stock_kline(symbol: str, days: int) -> list[dict]:
    try:
        df = ak.stock_us_hist(symbol=symbol.upper(), period="daily", adjust="qfq")
        if df is not None and not df.empty:
            return [build_kline_row(r, _EM_KL_COL_MAP)
                    for _, r in df.tail(days).iterrows()]
    except Exception as e:
        logger.debug("美股K线获取失败 %s: %s", symbol, e)
    return []


# ── 预取 ────────────────────────────────────────────────────────────────────

_STOCK_CODE_RE = re.compile(r'(?<!\d)(\d{6})(?!\d)')
_HK_CODE_RE = re.compile(r'(?<!\d)(\d{5})(?!\d)')
_US_TICKER_RE = re.compile(r'(?<![A-Za-z])([A-Za-z]{2,5})(?![A-Za-z])')

_NON_STOCK_WORDS = {
    'api', 'ai', 'etf', 'ipo', 'http', 'https', 'macd', 'rsi', 'kdj',
    'the', 'and', 'for', 'are', 'not', 'you', 'all', 'can', 'was',
    'jpg', 'png', 'pdf', 'xml', 'css', 'sql', 'ssh', 'cpu', 'gpu',
    'ceo', 'cfo', 'cto', 'usa', 'nyc', 'llc', 'irs', 'sec', 'fed',
    'iso', 'sms', 'ltd', 'inc', 'cor', 'com', 'net', 'org', 'gov',
}


def extract_stock_symbols(message: str) -> list[str]:
    """从用户消息中提取潜在的股票代码"""
    symbols = []
    for m in _STOCK_CODE_RE.findall(message):
        symbols.append(m)
    for m in _HK_CODE_RE.findall(message):
        symbols.append(m)
    for m in _US_TICKER_RE.findall(message):
        if m.lower() not in _NON_STOCK_WORDS:
            symbols.append(m.upper())
    return list(dict.fromkeys(symbols))[:3]


def prefetch_stock_data(message: str) -> dict[str, dict] | None:
    """预取股票数据。在 LLM 调用前并行拉取行情+K线，命中则跳过 function calling 回合"""
    import concurrent.futures

    symbols = extract_stock_symbols(message)
    if not symbols:
        return None

    data: dict = {}
    for sym in symbols[:2]:
        entry: dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            fut_quote = pool.submit(_quick_fetch_quote, sym)
            fut_kline = pool.submit(_quick_fetch_kline, sym)
            try:
                entry["quote"] = fut_quote.result(timeout=8)
            except Exception:
                entry["quote"] = {"error": "行情预取超时", "symbol": sym}
            try:
                entry["kline"] = fut_kline.result(timeout=12)
            except Exception:
                entry["kline"] = []

        if entry["kline"] or ("error" not in str(entry.get("quote", {}))):
            data[sym] = entry
        else:
            logger.warning("预取完全失败 %s", sym)

    return data if data else None
