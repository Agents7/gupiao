import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_user_by_username
from exceptions import token_missing, token_expired, user_not_found

logger = logging.getLogger("auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    logger.debug("Hashing password")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    result = pwd_context.verify(plain, hashed)
    logger.debug("Password verification: %s", "passed" if result else "failed")
    return result


def create_access_token(username: str) -> tuple[str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    logger.debug("Creating token for user: %s, expires: %s", username, expire.isoformat())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), expire


def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            logger.warning("Token missing 'sub' claim")
            return None
        logger.debug("Token verified for user: %s", username)
        return username
    except JWTError as e:
        logger.warning("Token verification failed: %s", e)
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None:
        raise token_missing()

    username = verify_token(credentials.credentials)
    if username is None:
        raise token_expired()

    user = get_user_by_username(username)
    if user is None:
        logger.warning("Token valid but user not found: %s", username)
        raise user_not_found()

    return user
