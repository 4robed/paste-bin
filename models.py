from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Column
from database import Base


class Paste(Base):
    __tablename__ = "pastes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    short_code = Column(String(16), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    language = Column(String(50), default="plaintext", nullable=False)
    password_hash = Column(String(200), nullable=True)
    views = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
