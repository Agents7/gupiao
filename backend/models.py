import re
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator

from exceptions import ErrorCode, ValidationException

logger = logging.getLogger("models")

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValidationException("用户名不能为空", ErrorCode.MISSING_FIELD)
        v = v.strip()
        if not USERNAME_PATTERN.match(v):
            raise ValidationException(
                "用户名格式不合法：仅允许字母、数字、下划线，3-32位",
                ErrorCode.INVALID_FORMAT,
            )
        logger.debug("Username validation passed: %s", v)
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValidationException("密码不能为空", ErrorCode.MISSING_FIELD)
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValidationException(
                f"密码长度不能少于 {PASSWORD_MIN_LENGTH} 位",
                ErrorCode.INVALID_FORMAT,
            )
        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValidationException(
                f"密码长度不能超过 {PASSWORD_MAX_LENGTH} 位",
                ErrorCode.INVALID_FORMAT,
            )
        logger.debug("Password validation passed (len=%d)", len(v))
        return v


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValidationException("用户名不能为空", ErrorCode.MISSING_FIELD)
        v = v.strip()
        if not USERNAME_PATTERN.match(v):
            raise ValidationException(
                "用户名格式不合法：仅允许字母、数字、下划线，3-32位",
                ErrorCode.INVALID_FORMAT,
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValidationException("密码不能为空", ErrorCode.MISSING_FIELD)
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValidationException(
                f"密码长度不能少于 {PASSWORD_MIN_LENGTH} 位",
                ErrorCode.INVALID_FORMAT,
            )
        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValidationException(
                f"密码长度不能超过 {PASSWORD_MAX_LENGTH} 位",
                ErrorCode.INVALID_FORMAT,
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm(cls, v: str) -> str:
        if not v:
            raise ValidationException("确认密码不能为空", ErrorCode.MISSING_FIELD)
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    expires_at: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: str = ""

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v: str) -> str:
        return v or datetime.now(timezone.utc).isoformat()


# ── Agent 相关模型 ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    sentiment: str | None = None
    risk_level: str | None = None
    risk_factors: list = []
    kline_patterns: str = ""
    key_data_points: dict = {}
    quote_data: dict | None = None
    kline_data: list | None = None
    skill_saved: bool = False
    skill_patched: bool = False


class ProfileUpdateRequest(BaseModel):
    risk_tolerance: str | None = None
    investment_style: str | None = None
    preferred_markets: str | None = None
    focus_sectors: str | None = None
    focus_stocks: str | None = None
    experience_level: str | None = None
