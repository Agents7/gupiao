import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import os

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import ACCESS_TOKEN_EXPIRE_MINUTES
from database import init_db, get_user_by_username, create_user
from models import (
    LoginRequest, RegisterRequest, TokenResponse, ErrorResponse,
    ChatRequest, ChatResponse, ProfileUpdateRequest,
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from services.agent import run_agent, run_agent_stream
from services.stock_api import get_stock_quote as stock_get_quote
from services.market_data import get_dashboard_data
from exceptions import (
    ErrorCode, AppException, ValidationException,
    DataSourceException, NotFoundException, AIServiceException,
    wrong_credentials, password_mismatch, username_taken,
)
import memory

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


# ── Lifetime ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    try:
        init_db()
    except Exception as e:
        logger.critical("数据库初始化失败: %s", e)
        raise
    yield
    logger.info("Shutting down...")


# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="股小助手 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ──────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一处理自定义应用异常"""
    log_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
    }.get(exc.log_level, logger.error)
    log_fn("[%s] %s %s: %s", exc.error_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=exc.error_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理 Pydantic 请求验证异常，转换为统一格式"""
    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in errors[:3]  # 只显示前3个错误
    )
    logger.warning("[%s] %s %s: %s", ErrorCode.VALIDATION_ERROR, request.method, request.url.path, detail)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            detail=detail,
            error_code=ErrorCode.VALIDATION_ERROR,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 FastAPI 原生 HTTPException，转换为统一格式"""
    logger.warning("[HTTP_%s] %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：捕获所有未处理的异常"""
    logger.exception("[%s] %s %s: %s", ErrorCode.INTERNAL_ERROR, request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="服务器内部错误，请稍后重试",
            error_code=ErrorCode.INTERNAL_ERROR,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump(),
    )


# ── Routes ──────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    logger.info("注册请求: %s", req.username)

    if req.password != req.confirm_password:
        raise password_mismatch()

    existing = get_user_by_username(req.username)
    if existing is not None:
        raise username_taken()

    try:
        pw_hash = hash_password(req.password)
        user = create_user(req.username, pw_hash)
    except ValidationException:
        raise
    except Exception as e:
        logger.exception("用户创建失败")
        raise AppException(
            detail="注册失败，请稍后重试",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )

    token, expire = create_access_token(req.username)
    logger.info("注册成功: %s (id=%s)", user["username"], user["id"])
    return TokenResponse(
        access_token=token,
        username=user["username"],
        expires_at=expire.isoformat(),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    logger.info("登录请求: %s", req.username)

    user = get_user_by_username(req.username)
    if user is None:
        raise wrong_credentials()

    if not verify_password(req.password, user["password_hash"]):
        raise wrong_credentials()

    token, expire = create_access_token(req.username)
    logger.info("登录成功: %s (id=%s)", user["username"], user["id"])
    return TokenResponse(
        access_token=token,
        username=user["username"],
        expires_at=expire.isoformat(),
    )


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    logger.debug("获取个人信息: %s", user["username"])
    return {
        "id": user["id"],
        "username": user["username"],
        "created_at": user["created_at"],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── 看板路由 ─────────────────────────────────────────────────────────────────

@app.get("/api/market/dashboard")
async def market_dashboard(user: dict = Depends(get_current_user)):
    """市场看板数据聚合接口"""
    try:
        data = get_dashboard_data()
        return data
    except Exception as e:
        logger.exception("看板数据获取异常")
        raise DataSourceException(
            detail="市场数据获取失败，请稍后重试",
            error_code=ErrorCode.DATA_SOURCE_ERROR,
        )


# ── Agent 路由 ─────────────────────────────────────────────────────────────────

@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Agent 对话核心接口"""
    user_id = str(user["id"])
    try:
        result = run_agent(user_id, req.conversation_id, req.message)
        return result
    except AIServiceException:
        raise
    except Exception as e:
        logger.exception("Agent 对话异常")
        raise AIServiceException(
            detail=f"分析服务异常: {e}",
            error_code=ErrorCode.AI_SERVICE_ERROR,
        )


@app.post("/api/agent/chat/stream")
async def agent_chat_stream(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Agent 对话流式接口 — SSE 实时推送分析结果"""
    user_id = str(user["id"])
    return StreamingResponse(
        run_agent_stream(user_id, req.conversation_id, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    """获取用户的对话列表"""
    try:
        convs = memory.get_user_conversations(str(user["id"]))
        return convs if convs is not None else []
    except Exception as e:
        logger.exception("获取对话列表异常")
        raise AppException(
            detail="获取对话列表失败",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )


@app.post("/api/agent/conversations")
async def new_conversation(user: dict = Depends(get_current_user)):
    """创建新对话"""
    try:
        conv = memory.create_conversation(str(user["id"]))
    except Exception as e:
        logger.exception("创建对话异常")
        raise AppException(
            detail="创建对话失败",
            error_code=ErrorCode.CREATE_FAILED,
            status_code=500,
        )
    if conv is None:
        raise AppException(
            detail="创建对话失败",
            error_code=ErrorCode.CREATE_FAILED,
            status_code=500,
        )
    return conv


@app.get("/api/agent/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, user: dict = Depends(get_current_user)):
    """获取对话消息历史"""
    try:
        msgs = memory.get_conversation_messages(conv_id, limit=50)
        return msgs if msgs is not None else []
    except Exception as e:
        logger.exception("获取消息异常")
        raise AppException(
            detail="获取消息失败",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )


@app.delete("/api/agent/conversations/{conv_id}")
async def remove_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    """删除对话"""
    try:
        deleted = memory.delete_conversation(conv_id)
        if not deleted:
            raise NotFoundException(
                detail="对话不存在或已删除",
                error_code=ErrorCode.NOT_FOUND,
            )
        return {"ok": True}
    except NotFoundException:
        raise
    except Exception as e:
        logger.exception("删除对话异常")
        raise AppException(
            detail="删除对话失败",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )


@app.get("/api/agent/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """获取用户画像"""
    try:
        profile = memory.load_user_profile(str(user["id"]))
        return profile if profile is not None else {}
    except Exception as e:
        logger.exception("获取画像异常")
        return {}  # 画像失败不阻塞，返回空


@app.patch("/api/agent/profile")
async def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """手动更新用户画像"""
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if updates:
            memory.update_user_profile(str(user["id"]), updates)
        profile = memory.load_user_profile(str(user["id"]))
        return profile if profile is not None else {}
    except Exception as e:
        logger.exception("更新画像异常")
        raise AppException(
            detail="更新用户画像失败",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )


@app.get("/api/agent/skills")
async def list_skills(user: dict = Depends(get_current_user)):
    """获取用户的分析技能列表"""
    try:
        skills = memory.get_user_skills(str(user["id"]))
        return skills if skills is not None else []
    except Exception as e:
        logger.exception("获取技能列表异常")
        return []


# ── 股票数据路由 ──────────────────────────────────────────────────────────────

@app.get("/api/stock/quote")
async def stock_quote(symbol: str, user: dict = Depends(get_current_user)):
    """快速查询股票行情"""
    if not symbol or not symbol.strip():
        raise ValidationException(
            detail="股票代码不能为空",
            error_code=ErrorCode.MISSING_FIELD,
        )
    try:
        return stock_get_quote(symbol.strip())
    except ValueError as e:
        raise NotFoundException(
            detail=str(e),
            error_code=ErrorCode.INVALID_SYMBOL,
        )
    except Exception as e:
        logger.exception("查询行情异常: %s", symbol)
        raise DataSourceException(
            detail=f"查询行情失败: {e}",
            error_code=ErrorCode.DATA_SOURCE_ERROR,
        )


@app.get("/api/stock/analyses")
async def list_analyses(user: dict = Depends(get_current_user)):
    """获取用户的历史分析记录"""
    try:
        analyses = memory.get_user_analyses(str(user["id"]), limit=20)
        return analyses if analyses is not None else []
    except Exception as e:
        logger.exception("获取分析记录异常")
        return []


# ── 生产模式：静态文件托管 ──────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
SPA_INDEX = os.path.join(STATIC_DIR, "index.html")

if os.path.isdir(STATIC_DIR):
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        """SPA fallback — 非 /api/ 路径返回前端入口"""
        path = os.path.join(STATIC_DIR, catchall)
        if os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(SPA_INDEX)
