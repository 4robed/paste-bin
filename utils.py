from datetime import datetime, timedelta
from typing import Optional, Dict
from nanoid import generate
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = URLSafeTimedSerializer(SECRET_KEY)

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

EXPIRY_OPTIONS: Dict[str, Optional[timedelta]] = {
    "never": None,
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

EXPIRY_LABELS = {
    "never": "Never",
    "1h": "1 Hour",
    "1d": "1 Day",
    "7d": "7 Days",
    "30d": "30 Days",
}


def make_short_code() -> str:
    return generate(ALPHABET, 8)


def expiry_from_option(option: str) -> Optional[datetime]:
    delta = EXPIRY_OPTIONS.get(option)
    if delta is None:
        return None
    return datetime.utcnow() + delta


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def make_unlock_cookie(short_code: str) -> str:
    return _signer.dumps(short_code, salt="unlock")


def verify_unlock_cookie(token: str, short_code: str, max_age: int = 86400) -> bool:
    try:
        value = _signer.loads(token, salt="unlock", max_age=max_age)
        return value == short_code
    except Exception:
        return False
