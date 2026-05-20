import sqlite3
import logging
from contextlib import contextmanager

from config import DB_PATH
from exceptions import username_taken, AppException, ErrorCode

logger = logging.getLogger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db() -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(SCHEMA)
            conn.commit()
        logger.info("Database initialized at %s", DB_PATH)
    except sqlite3.Error as e:
        logger.critical("Failed to initialize database: %s", e)
        raise AppException(
            detail="数据库初始化失败",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error("Database error: %s", e)
        raise AppException(
            detail="数据库操作异常",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
        )
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        if row is None:
            logger.debug("User not found: %s", username)
            return None
        logger.debug("User found: %s (id=%s)", username, row["id"])
        return dict(row)


def create_user(username: str, password_hash: str) -> dict:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()
            row_id = cur.lastrowid
            logger.info("User created: %s (id=%s)", username, row_id)
            return {"id": row_id, "username": username}
        except sqlite3.IntegrityError:
            logger.warning("Duplicate username attempt: %s", username)
            raise username_taken()
