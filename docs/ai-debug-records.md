# AI 工具辅助 Debug 记录

记录了使用 Claude Code 在此项目中解决的实际 bug。

---

## Bug #1：DeepSeek 返回的 JSON 前面带了一句话

**时间**：2026-05-18

**现象**：
```
用户访问 /api/agent/chat，500 Internal Server Error。
日志：json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**排查过程**：

1. 看日志发现异常在 `agent.py:119` 的 `json.loads(final_content.strip())`
2. 打印原始返回值，发现 LLM 返回的是：

```
好的，根据您的问题，我为您分析如下：
{
  "reply": "贵州茅台...",
  "sentiment": "neutral",
  ...
}
希望以上分析对您有帮助！
```

3. `json.loads()` 无法解析带前后文字的字符串

**AI 工具如何解决**：

Claude 给出的方案是 `parse_llm_json()` 函数（实现在 [utils.py:41-54](../backend/utils.py)）：

```python
def parse_llm_json(content: str) -> dict:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # 回退：用正则提取 { ... } 块
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        return json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"无法解析 LLM 回复为 JSON") from e
```

关键细节：用 `rindex("}")` 而不是 `index("}")`——因为 reply 字段内的 Markdown 可能包含 `}`（如代码块），必须从右边找最后一个。

**教训**：永远不要信任 LLM 的 `response_format={"type": "json_object"}` 承诺。解析层必须有正则兜底。

---

## Bug #2：akshare 被 Clash 代理拦死

**时间**：2026-05-19

**现象**：
```
akshare 调用超时，所有股票查询返回 "DataSourceException: 市场数据获取失败"
```

**排查过程**：

1. 在 `stock_api.py` 中的重试循环里加日志，发现每次都在第 1 次请求就 timeout
2. 单独跑 `ak.stock_zh_a_spot_em()` 报 `ConnectionError`
3. `curl https://push2.eastmoney.com` 正常，但 Python 里连不上
4. 检查环境变量发现 `HTTP_PROXY=http://127.0.0.1:7890`（Clash 代理已关闭但变量残留）
5. Python 的 `requests`/`akshare` 自动读取这些代理变量，请求被路由到不存在的代理

**AI 工具如何解决**：

Claude 给出 `clear_proxy_env()` 函数（实现在 [utils.py:17-26](../backend/utils.py)）：

```python
def clear_proxy_env():
    global _proxy_cleared
    if _proxy_cleared:
        return
    for key in list(os.environ.keys()):
        if "proxy" in key.lower():
            del os.environ[key]
    os.environ["no_proxy"] = "*"
    _proxy_cleared = True
```

此函数必须在 `import akshare` 之前调用（因为 akshare 在 import 时就读取了环境变量）。

**教训**：国内开发环境经常有残留代理变量。网络库会自动读取 `HTTP_PROXY`/`HTTPS_PROXY`，导致本该直连的请求被路由到已关闭的代理。

---

## Bug #3：东方财富 API 价格是实际价格的 100 倍

**时间**：2026-05-18

**现象**：
```
LLM 分析回复："茅台当前价格 168,000 元"，实际应该是 1,680 元。
前端 K 线图 Y 轴数值异常。
```

**排查过程**：

1. 对比 akshare 返回数据和东方财富网页显示
2. 东方财富 API 返回 `f43` 字段值为 `168000`，但网页显示 `1680.00`
3. 检查其他字段：`f44`（最高）= `169500`，`f45`（最低）= `167200`
4. 确认规律：所有价格字段都乘了 100，因为东方财富内部用"分"做单位避免浮点数

**AI 工具如何解决**：

被指出这是 Eastmoney API 的已知特征——价格用"分"存储，需要在解析时除以 100：

```python
# backend/services/stock_api.py:109
"price": d.get("f43", 0) / 100.0 if d.get("f43") else 0,
"high": (d.get("f44", 0) or 0) / 100.0,
"low": (d.get("f45", 0) or 0) / 100.0,
"open": (d.get("f46", 0) or 0) / 100.0,
```

`f170`（涨跌幅）和 `f47`（成交量）不需要除以 100——涨跌幅已经是百分比，成交量是"手"。需要逐个字段确认。

**教训**：第三方 API 的数字格式不一定和 UI 显示一致。东方财富所有金额类字段用"分"存储，接入新 API 时必须逐个字段核对。

---

## Bug #4：前端 Router History Mode 导致刷新 404

**时间**：2026-05-20

**现象**：
```
SPA 中直接访问 /agent/xxx 返回 404，但从首页点击进入正常。
刷新页面后白屏，浏览器控制台显示 HTML 返回了 404。
```

**排查过程**：

1. Vue Router 用的是 `createWebHistory()`（HTML5 History 模式）
2. 前端打包后的 `dist/` 只有 `index.html` + js/css 文件
3. 浏览器请求 `/agent/123` 时，FastAPI 找不到这个路径，返回 404
4. 从首页点击进入正常，是因为 Vue Router 在客户端拦截了点击，没有发 HTTP 请求

**AI 工具如何解决**：

Claude 给出的方案是添加 SPA fallback 路由（实现在 [main.py:408-416](../backend/main.py)）：

```python
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
SPA_INDEX = os.path.join(STATIC_DIR, "index.html")

if os.path.isdir(STATIC_DIR):
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        path = os.path.join(STATIC_DIR, catchall)
        if os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(SPA_INDEX)
```

逻辑：先检查请求路径是否对应静态文件（js/css/图片），如果不是，返回 `index.html`，让 Vue Router 在客户端处理路由。

**教训**：History mode 的 SPA 必须配置服务端 fallback。nginx 用 `try_files $uri /index.html`；FastAPI 直接托管，用 catch-all 路由。

---

## 总结：AI 工具在 Debug 中的效率提升

| 环节 | 传统方式 | AI 辅助 |
|------|---------|--------|
| 定位根因 | 逐行 print，重启服务 | 描述现象，AI 根据日志推理 |
| 找解决方案 | Google / StackOverflow / GitHub Issues | AI 直接生成针对当前代码的修复 |
| 边界情况 | 靠经验，容易遗漏 | AI 提示相似的常见陷阱 |
| 写兜底逻辑 | 手动处理各种异常分支 | AI 生成健壮的 fallback 逻辑 |

以上 4 个 bug 从发现到修复，平均每个不到 15 分钟。
