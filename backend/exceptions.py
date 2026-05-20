"""自定义异常与错误码体系"""

# ── 错误码常量 ─────────────────────────────────────────────────────────────────
class ErrorCode:
    # 参数验证 (10xxx)
    VALIDATION_ERROR = "10001"
    MISSING_FIELD = "10002"
    INVALID_FORMAT = "10003"

    # 认证授权 (20xxx)
    WRONG_CREDENTIALS = "20001"
    TOKEN_EXPIRED = "20002"
    TOKEN_MISSING = "20003"
    USER_NOT_FOUND = "20004"
    USERNAME_TAKEN = "20005"
    PASSWORD_MISMATCH = "20006"

    # 数据源 (30xxx)
    DATA_SOURCE_ERROR = "30001"
    DATA_TIMEOUT = "30002"
    INVALID_SYMBOL = "30003"

    # 资源 (40xxx)
    NOT_FOUND = "40001"
    CREATE_FAILED = "40002"

    # 内部服务 (50xxx)
    AI_SERVICE_ERROR = "50001"
    DB_ERROR = "50002"
    INTERNAL_ERROR = "50003"


# ── 自定义异常基类 ────────────────────────────────────────────────────────────


class AppException(Exception):
    """应用统一异常基类"""
    def __init__(self, detail: str, error_code: str = ErrorCode.INTERNAL_ERROR,
                 status_code: int = 500, log_level: str = "error"):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.log_level = log_level
        super().__init__(detail)


# ── 认证异常 ──────────────────────────────────────────────────────────────────


class AuthException(AppException):
    """认证相关异常"""
    def __init__(self, detail: str, error_code: str = ErrorCode.WRONG_CREDENTIALS):
        super().__init__(detail=detail, error_code=error_code, status_code=401,
                         log_level="warning")


def wrong_credentials(msg: str = "用户名或密码错误") -> AuthException:
    return AuthException(msg, ErrorCode.WRONG_CREDENTIALS)


def token_missing() -> AuthException:
    return AuthException("未提供认证令牌", ErrorCode.TOKEN_MISSING)


def token_expired(msg: str = "令牌无效或已过期") -> AuthException:
    return AuthException(msg, ErrorCode.TOKEN_EXPIRED)


def user_not_found() -> AuthException:
    return AuthException("用户不存在", ErrorCode.USER_NOT_FOUND)


# ── 验证异常 ──────────────────────────────────────────────────────────────────


class ValidationException(AppException):
    """参数验证异常"""
    def __init__(self, detail: str, error_code: str = ErrorCode.VALIDATION_ERROR):
        super().__init__(detail=detail, error_code=error_code, status_code=422,
                         log_level="warning")


def username_taken() -> ValidationException:
    return ValidationException("用户名已被注册", ErrorCode.USERNAME_TAKEN)


def password_mismatch() -> ValidationException:
    return ValidationException("两次输入的密码不一致", ErrorCode.PASSWORD_MISMATCH)


# ── 数据源异常 ────────────────────────────────────────────────────────────────


class DataSourceException(AppException):
    """数据源异常"""
    def __init__(self, detail: str, error_code: str = ErrorCode.DATA_SOURCE_ERROR):
        super().__init__(detail=detail, error_code=error_code, status_code=502,
                         log_level="error")


# ── 资源异常 ──────────────────────────────────────────────────────────────────


class NotFoundException(AppException):
    """资源不存在"""
    def __init__(self, detail: str, error_code: str = ErrorCode.NOT_FOUND):
        super().__init__(detail=detail, error_code=error_code, status_code=404,
                         log_level="warning")


# ── AI 服务异常 ───────────────────────────────────────────────────────────────


class AIServiceException(AppException):
    """AI 服务调用异常"""
    def __init__(self, detail: str, error_code: str = ErrorCode.AI_SERVICE_ERROR):
        super().__init__(detail=detail, error_code=error_code, status_code=500,
                         log_level="error")
