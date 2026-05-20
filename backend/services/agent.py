"""Agent 核心循环 — 上下文加载 → 工具调用 → LLM 分析 → 后处理"""
import json
import logging
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from services.agent_prompt import build_system_prompt, TOOLS
from services.stock_api import get_stock_quote, get_stock_kline, search_stock, prefetch_stock_data
from utils import parse_llm_json
import memory

logger = logging.getLogger("agent")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def run_agent(user_id: str, conversation_id: str | None, message: str) -> dict:
    """
    Agent 主循环，返回结构化的分析结果。
    如果没有 conversation_id，自动创建新对话。
    """
    profile = memory.load_user_profile(user_id)
    skills = memory.load_relevant_skills(user_id, message, limit=5)

    if not conversation_id:
        conv = memory.create_conversation(user_id)
        if conv is None:
            raise RuntimeError("无法创建对话（Supabase 未配置）")
        conversation_id = conv["id"]

    recent_msgs = memory.get_conversation_messages(conversation_id, limit=20)
    memory.save_message(conversation_id, "user", message)

    system_prompt = build_system_prompt(profile, skills, has_tools=True)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in recent_msgs:
        content = msg.get("content", "")
        role = msg.get("role", "user")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        return _error_response(conversation_id, f"AI 服务暂时不可用: {e}")

    choice = response.choices[0]
    msg = choice.message

    tool_results_store = {}
    skill_used = None

    if msg.tool_calls:
        tool_calls_data = [
            {"id": tc.id, "function": tc.function.name, "arguments": tc.function.arguments}
            for tc in msg.tool_calls
        ]
        memory.save_message(conversation_id, "assistant", json.dumps(tool_calls_data, ensure_ascii=False),
                            tool_calls=tool_calls_data)

        assistant_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }}
                for tc in msg.tool_calls
            ]
        }
        messages.append(assistant_msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            try:
                func_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            logger.info("执行工具: %s(%s)", func_name, func_args)

            try:
                result = _dispatch_tool(func_name, func_args)
            except Exception as e:
                result = {"error": str(e)}
                logger.warning("工具执行失败 %s: %s", func_name, e)

            tool_results_store[func_name] = result
            result_json = json.dumps(result, ensure_ascii=False, default=str)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_json})
            memory.save_message(conversation_id, "tool", result_json[:500],
                                tool_results={"function": func_name, "result": result})

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error("第二轮 LLM 调用失败: %s", e)
            return _error_response(conversation_id, f"AI 分析失败: {e}")

        final_content = response.choices[0].message.content
    else:
        final_content = msg.content

    if not msg.tool_calls:
        try:
            result = json.loads(final_content.strip())
        except json.JSONDecodeError:
            memory.save_message(conversation_id, "assistant", final_content)
            return {
                "conversation_id": conversation_id,
                "reply": final_content,
                "sentiment": None, "risk_level": None, "risk_factors": [],
                "kline_patterns": "", "key_data_points": {},
                "quote_data": None, "kline_data": None,
                "skill_saved": False, "skill_patched": False,
            }
    else:
        try:
            result = parse_llm_json(final_content)
        except ValueError:
            logger.error("无法解析 LLM 回复为 JSON: %s", final_content[:200])
            return _error_response(conversation_id, "AI 返回格式异常，请重试")

    return _finalize_response(result, tool_results_store, conversation_id, user_id, skill_used)


# ── 流式输出 ────────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_agent_stream(user_id: str, conversation_id: str | None, message: str):
    """Agent 流式版本 — 边生成边返回 SSE 事件"""
    profile = memory.load_user_profile(user_id)
    skills = memory.load_relevant_skills(user_id, message, limit=5)

    if not conversation_id:
        conv = memory.create_conversation(user_id)
        if conv is None:
            yield _sse({"type": "error", "content": "无法创建对话（Supabase 未配置）"})
            return
        conversation_id = conv["id"]

    recent_msgs = memory.get_conversation_messages(conversation_id, limit=20)
    memory.save_message(conversation_id, "user", message)

    system_prompt = build_system_prompt(profile, skills, has_tools=True)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in recent_msgs:
        content = msg.get("content", "")
        role = msg.get("role", "user")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    prefetched = prefetch_stock_data(message)
    tool_results_store: dict = {}
    skill_used = None

    if prefetched:
        for event in _stream_with_prefetch(messages, prefetched, tool_results_store,
                                           conversation_id, user_id):
            yield event
    else:
        for event in _stream_with_tools(messages, tool_results_store,
                                        conversation_id, user_id):
            yield event


def _stream_with_prefetch(messages, prefetched, tool_results_store,
                           conversation_id, user_id):
    """预取命中：数据已就绪，单轮 streaming 调用直达分析"""
    ctx_parts = ["<prefetched_data>\n以下股票数据已预先获取，请直接使用进行分析，无需重复调用工具："]
    for sym, d in prefetched.items():
        quote = d.get("quote", {})
        kline = d.get("kline", [])
        kline_brief = kline[-15:] if isinstance(kline, list) and len(kline) > 15 else kline
        ctx_parts.append(f"\n【{sym}】")
        ctx_parts.append(f"行情: {json.dumps(quote, ensure_ascii=False, default=str)}")
        ctx_parts.append(f"K线(最近{len(kline_brief)}日): {json.dumps(kline_brief, ensure_ascii=False, default=str)}")
    ctx_parts.append("\n重要：以上数据已就绪，请直接输出分析 JSON，不要再调用 get_stock_quote 或 get_stock_kline。")
    ctx_parts.append("</prefetched_data>")

    messages.insert(-1, {"role": "system", "content": "\n".join(ctx_parts)})

    for sym, d in prefetched.items():
        tool_results_store["get_stock_quote"] = d.get("quote", {})
        tool_results_store["get_stock_kline"] = d.get("kline", [])

    yield _sse({"type": "status", "content": "已预取行情数据，直接生成分析..."})

    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("预取路径 LLM 调用失败: %s", e)
        yield _sse({"type": "error", "content": f"AI 服务暂时不可用: {e}"})
        return

    full_content = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_content += delta
            yield _sse({"type": "delta", "content": delta})

    try:
        result = parse_llm_json(full_content)
    except ValueError:
        logger.error("无法解析 LLM 回复为 JSON: %s", full_content[:200])
        yield _sse({"type": "error", "content": "AI 返回格式异常，请重试"})
        return

    for event in _post_process(result, tool_results_store, conversation_id, user_id):
        yield event


def _stream_with_tools(messages, tool_results_store, conversation_id, user_id):
    """未命中预取：走传统 function calling 流程"""
    yield _sse({"type": "status", "content": "正在分析您的问题..."})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        yield _sse({"type": "error", "content": f"AI 服务暂时不可用: {e}"})
        return

    choice = response.choices[0]
    msg = choice.message

    if msg.tool_calls:
        tool_calls_data = [
            {"id": tc.id, "function": tc.function.name, "arguments": tc.function.arguments}
            for tc in msg.tool_calls
        ]
        memory.save_message(conversation_id, "assistant",
                            json.dumps(tool_calls_data, ensure_ascii=False),
                            tool_calls=tool_calls_data)

        assistant_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }}
                for tc in msg.tool_calls
            ]
        }
        messages.append(assistant_msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            try:
                func_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            yield _sse({"type": "status", "content": f"正在获取 {func_name} 数据..."})

            try:
                result = _dispatch_tool(func_name, func_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_results_store[func_name] = result
            result_json = json.dumps(result, ensure_ascii=False, default=str)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_json})
            memory.save_message(conversation_id, "tool", result_json[:500],
                                tool_results={"function": func_name, "result": result})

        yield _sse({"type": "status", "content": "正在生成分析报告..."})

        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error("流式 LLM 调用失败: %s", e)
            yield _sse({"type": "error", "content": f"AI 分析失败: {e}"})
            return

        full_content = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_content += delta
                yield _sse({"type": "delta", "content": delta})

    else:
        full_content = msg.content or ""

    if not msg.tool_calls:
        try:
            result = json.loads(full_content.strip())
        except json.JSONDecodeError:
            memory.save_message(conversation_id, "assistant", full_content)
            yield _sse({"type": "done", "result": {
                "conversation_id": conversation_id,
                "reply": full_content,
                "sentiment": None, "risk_level": None, "risk_factors": [],
                "kline_patterns": "", "key_data_points": {},
                "quote_data": None, "kline_data": None,
                "skill_saved": False, "skill_patched": False,
            }})
            return
    else:
        try:
            result = parse_llm_json(full_content)
        except ValueError:
            logger.error("无法解析 LLM 回复为 JSON: %s", full_content[:200])
            yield _sse({"type": "error", "content": "AI 返回格式异常，请重试"})
            return

    for event in _post_process(result, tool_results_store, conversation_id, user_id):
        yield event


# ── 共享工具 ────────────────────────────────────────────────────────────────────

def _dispatch_tool(func_name: str, func_args: dict) -> dict:
    """统一工具调度"""
    if func_name == "get_stock_quote":
        return get_stock_quote(func_args.get("symbol", ""))
    elif func_name == "get_stock_kline":
        return get_stock_kline(func_args.get("symbol", ""), func_args.get("days", 30))
    elif func_name == "search_stock":
        return search_stock(func_args.get("keyword", ""))
    else:
        return {"error": f"未知工具: {func_name}"}


def _finalize_response(result: dict, tool_results_store: dict,
                       conversation_id: str, user_id: str, skill_used=None) -> dict:
    """后处理：校验字段、存储信息、组装返回"""
    sentiment = result.get("sentiment")
    risk_level = result.get("risk_level")

    if sentiment and sentiment not in ("bullish", "neutral", "bearish"):
        sentiment = "neutral"
    if risk_level and risk_level not in ("low", "medium", "high"):
        risk_level = "medium"

    memory.save_message(conversation_id, "assistant", json.dumps(result, ensure_ascii=False),
                        skill_used=skill_used)

    profile_updates = result.get("profile_updates", {})
    if profile_updates and isinstance(profile_updates, dict):
        memory.update_user_profile(user_id, profile_updates)

    skill_to_save = result.get("skill_to_save")
    if skill_to_save and isinstance(skill_to_save, dict):
        saved = memory.save_skill(user_id, skill_to_save)
        if saved:
            memory.log_learning_event(user_id, "skill_created",
                                       f"新技能: {skill_to_save.get('skill_name', '')}",
                                       skill_to_save)

    skill_to_patch = result.get("skill_to_patch")
    if skill_to_patch and isinstance(skill_to_patch, dict):
        memory.patch_skill(user_id, skill_to_patch)
        memory.log_learning_event(user_id, "skill_patched",
                                   f"修正技能: {skill_to_patch.get('skill_name', '')}",
                                   skill_to_patch)

    if sentiment is not None and tool_results_store.get("get_stock_quote"):
        quote = tool_results_store["get_stock_quote"]
        kline = tool_results_store.get("get_stock_kline", [])
        symbol = quote.get("symbol", "")
        if symbol:
            memory.save_analysis(
                user_id=user_id,
                conversation_id=conversation_id,
                symbol=symbol,
                stock_name=quote.get("name", ""),
                market=quote.get("market", ""),
                quote_data=quote,
                kline_data=kline if isinstance(kline, list) else [],
                analysis=result,
            )

    return {
        "conversation_id": conversation_id,
        "reply": result.get("reply", ""),
        "sentiment": sentiment,
        "risk_level": risk_level,
        "risk_factors": result.get("risk_factors", []),
        "kline_patterns": result.get("kline_patterns", ""),
        "key_data_points": result.get("key_data_points", {}),
        "quote_data": tool_results_store.get("get_stock_quote"),
        "kline_data": tool_results_store.get("get_stock_kline"),
        "skill_saved": skill_to_save is not None,
        "skill_patched": skill_to_patch is not None,
    }


def _post_process(result, tool_results_store, conversation_id, user_id):
    """流式后处理：校验、存储、返回 done 事件"""
    sentiment = result.get("sentiment")
    risk_level = result.get("risk_level")

    memory.save_message(conversation_id, "assistant", json.dumps(result, ensure_ascii=False),
                        skill_used=None)

    profile_updates = result.get("profile_updates", {})
    if profile_updates and isinstance(profile_updates, dict):
        memory.update_user_profile(user_id, profile_updates)

    skill_to_save = result.get("skill_to_save")
    if skill_to_save and isinstance(skill_to_save, dict):
        saved = memory.save_skill(user_id, skill_to_save)
        if saved:
            memory.log_learning_event(user_id, "skill_created",
                                       f"新技能: {skill_to_save.get('skill_name', '')}",
                                       skill_to_save)

    skill_to_patch = result.get("skill_to_patch")
    if skill_to_patch and isinstance(skill_to_patch, dict):
        memory.patch_skill(user_id, skill_to_patch)
        memory.log_learning_event(user_id, "skill_patched",
                                   f"修正技能: {skill_to_patch.get('skill_name', '')}",
                                   skill_to_patch)

    if sentiment is not None and tool_results_store.get("get_stock_quote"):
        quote = tool_results_store["get_stock_quote"]
        kline = tool_results_store.get("get_stock_kline", [])
        symbol = quote.get("symbol", "")
        if symbol:
            memory.save_analysis(
                user_id=user_id,
                conversation_id=conversation_id,
                symbol=symbol,
                stock_name=quote.get("name", ""),
                market=quote.get("market", ""),
                quote_data=quote,
                kline_data=kline if isinstance(kline, list) else [],
                analysis=result,
            )

    yield _sse({"type": "done", "result": {
        "conversation_id": conversation_id,
        "reply": result.get("reply", ""),
        "sentiment": sentiment,
        "risk_level": risk_level,
        "risk_factors": result.get("risk_factors", []),
        "kline_patterns": result.get("kline_patterns", ""),
        "key_data_points": result.get("key_data_points", {}),
        "quote_data": tool_results_store.get("get_stock_quote"),
        "kline_data": tool_results_store.get("get_stock_kline"),
        "skill_saved": skill_to_save is not None,
        "skill_patched": skill_to_patch is not None,
    }})


def _error_response(conversation_id: str, message: str) -> dict:
    return {
        "conversation_id": conversation_id,
        "reply": message,
        "sentiment": None,
        "risk_level": None,
        "risk_factors": [],
        "kline_patterns": "",
        "key_data_points": {},
        "quote_data": None,
        "kline_data": None,
        "skill_saved": False,
        "skill_patched": False,
    }
