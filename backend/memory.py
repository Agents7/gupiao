"""记忆管理 — 用户画像 / 技能库 / 学习日志 / 对话消息"""
import logging

from supabase_client import get_supabase

logger = logging.getLogger("memory")

# ── 用户画像 ──────────────────────────────────────────────────────────────────

DEFAULT_PROFILE = {
    "risk_tolerance": "moderate",
    "investment_style": "swing",
    "preferred_markets": "A股",
    "focus_sectors": "[]",
    "focus_stocks": "[]",
    "experience_level": "beginner",
    "total_analyses": 0,
    "favorite_sectors": "",
    "avg_holding_period": "",
}


def load_user_profile(user_id: str) -> dict:
    try:
        supabase = get_supabase()
        if supabase is None:
            return DEFAULT_PROFILE
        res = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]
        # 不存在则创建默认画像
        supabase.table("user_profiles").insert({"user_id": user_id, **DEFAULT_PROFILE}).execute()
        return {**DEFAULT_PROFILE, "user_id": user_id}
    except Exception as e:
        logger.warning("加载用户画像失败，使用默认画像: %s", e)
        return DEFAULT_PROFILE


def update_user_profile(user_id: str, updates: dict) -> None:
    if not updates:
        return
    try:
        supabase = get_supabase()
        if supabase is None:
            return
        allowed = {"risk_tolerance", "investment_style", "preferred_markets",
                    "focus_sectors", "focus_stocks", "experience_level",
                    "favorite_sectors", "avg_holding_period", "total_analyses"}
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return
        # 确保 profile 存在
        existing = supabase.table("user_profiles").select("user_id").eq("user_id", user_id).execute()
        if not existing.data:
            supabase.table("user_profiles").insert({"user_id": user_id, **DEFAULT_PROFILE}).execute()
        supabase.table("user_profiles").update(filtered).eq("user_id", user_id).execute()
        logger.info("用户画像已更新: %s -> %s", user_id, list(filtered.keys()))
    except Exception as e:
        logger.warning("更新用户画像失败: %s", e)


# ── 技能库 ────────────────────────────────────────────────────────────────────

def load_relevant_skills(user_id: str, message: str = "", limit: int = 5) -> list[dict]:
    try:
        supabase = get_supabase()
        if supabase is None:
            return []
        # 按最近使用排序加载
        res = supabase.table("agent_skills").select("*")\
            .eq("user_id", user_id)\
            .order("last_used_at", desc=True)\
            .limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.warning("加载技能失败: %s", e)
        return []


def save_skill(user_id: str, skill_data: dict) -> dict | None:
    try:
        supabase = get_supabase()
        if supabase is None:
            return None
        res = supabase.table("agent_skills").insert({
            "user_id": user_id,
            "skill_name": skill_data.get("skill_name", ""),
            "skill_content": skill_data.get("skill_content", ""),
            "triggers": skill_data.get("triggers", ""),
            "last_used_at": "now()",
        }).execute()
        logger.info("新技能已沉淀: %s", skill_data.get("skill_name"))
        return res.data[0] if res.data else None
    except Exception as e:
        logger.warning("保存技能失败: %s", e)
        return None


def patch_skill(user_id: str, patch_data: dict) -> bool:
    try:
        supabase = get_supabase()
        if supabase is None:
            return False
        skill_name = patch_data.get("skill_name", "")
        # 按名称查找并更新
        existing = supabase.table("agent_skills").select("id")\
            .eq("user_id", user_id).eq("skill_name", skill_name).execute()
        if existing.data:
            supabase.table("agent_skills").update({
                "skill_content": supabase.table("agent_skills").select("skill_content").eq("id", existing.data[0]["id"]).execute().data[0].get("skill_content", "") + "\n\n## 修正\n" + patch_data.get("patch_description", ""),
                "last_used_at": "now()",
            }).eq("id", existing.data[0]["id"]).execute()
            logger.info("技能已修正: %s", skill_name)
        return True
    except Exception as e:
        logger.warning("修正技能失败: %s", e)
        return False


def get_user_skills(user_id: str) -> list[dict]:
    try:
        supabase = get_supabase()
        if supabase is None:
            return []
        res = supabase.table("agent_skills").select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.warning("获取技能列表失败: %s", e)
        return []


# ── 学习日志 ──────────────────────────────────────────────────────────────────

def log_learning_event(user_id: str, event_type: str, description: str, details: dict | None = None) -> None:
    try:
        supabase = get_supabase()
        if supabase is None:
            return
        supabase.table("agent_learning_log").insert({
            "user_id": user_id,
            "event_type": event_type,
            "description": description,
            "details": details or {},
        }).execute()
        logger.info("学习事件记录: %s - %s", event_type, description)
    except Exception as e:
        logger.warning("记录学习事件失败: %s", e)


# ── 对话管理 ──────────────────────────────────────────────────────────────────

def create_conversation(user_id: str, title: str = "新对话") -> dict | None:
    try:
        supabase = get_supabase()
        if supabase is None:
            return None
        res = supabase.table("conversations").insert({
            "user_id": user_id,
            "title": title,
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.warning("创建对话失败: %s", e)
        return None


def get_user_conversations(user_id: str) -> list[dict]:
    try:
        supabase = get_supabase()
        if supabase is None:
            return []
        res = supabase.table("conversations").select("*")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .limit(50).execute()
        return res.data or []
    except Exception as e:
        logger.warning("获取对话列表失败: %s", e)
        return []


def get_conversation_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    try:
        supabase = get_supabase()
        if supabase is None:
            return []
        res = supabase.table("conversation_messages").select("*")\
            .eq("conversation_id", conversation_id)\
            .order("created_at")\
            .limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.warning("获取消息失败: %s", e)
        return []


def save_message(conversation_id: str, role: str, content: str,
                 tool_calls: dict | None = None, tool_results: dict | None = None,
                 skill_used: str | None = None) -> dict | None:
    try:
        supabase = get_supabase()
        if supabase is None:
            return None
        res = supabase.table("conversation_messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "skill_used": skill_used,
        }).execute()
        # 更新对话的 updated_at
        supabase.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.warning("保存消息失败: %s", e)
        return None


def delete_conversation(conversation_id: str) -> bool:
    try:
        supabase = get_supabase()
        if supabase is None:
            return False
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        return True
    except Exception as e:
        logger.warning("删除对话失败: %s", e)
        return False


# ── 分析记录 ──────────────────────────────────────────────────────────────────

def save_analysis(user_id: str, conversation_id: str, symbol: str,
                  stock_name: str, market: str, quote_data: dict,
                  kline_data: list, analysis: dict) -> dict | None:
    try:
        supabase = get_supabase()
        if supabase is None:
            return None
        res = supabase.table("stock_analyses").insert({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "symbol": symbol,
            "stock_name": stock_name,
            "market": market,
            "quote_data": quote_data,
            "kline_data": kline_data,
            "summary": analysis.get("summary", analysis.get("reply", "")),
            "sentiment": analysis.get("sentiment", ""),
            "risk_level": analysis.get("risk_level", ""),
            "kline_patterns": analysis.get("kline_patterns", ""),
            "key_points": analysis.get("risk_factors", []),
        }).execute()
        # 更新画像中的分析计数
        update_user_profile(user_id, {"total_analyses": _inc_analysis_count(user_id)})
        return res.data[0] if res.data else None
    except Exception as e:
        logger.warning("保存分析记录失败: %s", e)
        return None


def get_user_analyses(user_id: str, limit: int = 20) -> list[dict]:
    try:
        supabase = get_supabase()
        if supabase is None:
            return []
        res = supabase.table("stock_analyses").select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.warning("获取分析记录失败: %s", e)
        return []


def _inc_analysis_count(user_id: str) -> int:
    try:
        supabase = get_supabase()
        if supabase is None:
            return 0
        res = supabase.table("user_profiles").select("total_analyses").eq("user_id", user_id).execute()
        current = res.data[0].get("total_analyses", 0) if res.data else 0
        return current + 1
    except Exception:
        return 0
