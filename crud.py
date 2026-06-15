from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models import Paste
from utils import make_short_code, hash_password, expiry_from_option


def create_paste(
    db: Session,
    content: str,
    language: str,
    title: Optional[str] = None,
    password: Optional[str] = None,
    expiry: str = "never",
) -> Paste:
    for _ in range(5):
        code = make_short_code()
        if not db.query(Paste).filter(Paste.short_code == code).first():
            break

    paste = Paste(
        short_code=code,
        title=title or None,
        content=content,
        language=language,
        password_hash=hash_password(password) if password else None,
        expires_at=expiry_from_option(expiry),
    )
    db.add(paste)
    db.commit()
    db.refresh(paste)
    return paste


def get_paste(db: Session, short_code: str) -> Optional[Paste]:
    paste = db.query(Paste).filter(Paste.short_code == short_code).first()
    if paste is None:
        return None
    if paste.expires_at and paste.expires_at < datetime.utcnow():
        db.delete(paste)
        db.commit()
        return None
    return paste


def increment_views(db: Session, paste: Paste) -> None:
    paste.views += 1
    db.commit()
