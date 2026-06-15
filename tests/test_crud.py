import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from crud import create_paste, get_paste, increment_views
from models import Paste

TEST_DB = "sqlite:///./test_crud.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    s = Session()
    yield s
    s.query(Paste).delete()
    s.commit()
    s.close()


class TestCreatePaste:
    def test_basic_creation(self, db):
        p = create_paste(db, content="x = 1", language="python")
        assert p.id is not None
        assert len(p.short_code) == 8
        assert p.content == "x = 1"
        assert p.language == "python"
        assert p.password_hash is None
        assert p.expires_at is None
        assert p.views == 0

    def test_with_title(self, db):
        p = create_paste(db, content="hello", language="plaintext", title="My Title")
        assert p.title == "My Title"

    def test_without_title(self, db):
        p = create_paste(db, content="hello", language="plaintext")
        assert p.title is None

    def test_with_password(self, db):
        p = create_paste(db, content="secret", language="plaintext", password="pw123")
        assert p.password_hash is not None
        assert p.password_hash != "pw123"

    def test_expiry_never(self, db):
        p = create_paste(db, content="x", language="plaintext", expiry="never")
        assert p.expires_at is None

    def test_expiry_1h(self, db):
        before = datetime.utcnow()
        p = create_paste(db, content="x", language="plaintext", expiry="1h")
        assert p.expires_at is not None
        assert p.expires_at > before + timedelta(minutes=59)
        assert p.expires_at < before + timedelta(hours=1, minutes=1)

    def test_expiry_1d(self, db):
        p = create_paste(db, content="x", language="plaintext", expiry="1d")
        assert p.expires_at is not None
        assert p.expires_at > datetime.utcnow() + timedelta(hours=23)

    def test_expiry_7d(self, db):
        p = create_paste(db, content="x", language="plaintext", expiry="7d")
        assert p.expires_at is not None
        assert p.expires_at > datetime.utcnow() + timedelta(days=6)

    def test_expiry_30d(self, db):
        p = create_paste(db, content="x", language="plaintext", expiry="30d")
        assert p.expires_at is not None
        assert p.expires_at > datetime.utcnow() + timedelta(days=29)

    def test_unknown_expiry_defaults_to_never(self, db):
        p = create_paste(db, content="x", language="plaintext", expiry="bogus")
        assert p.expires_at is None

    def test_short_codes_are_unique(self, db):
        codes = {create_paste(db, content="x", language="plaintext").short_code for _ in range(20)}
        assert len(codes) == 20

    def test_created_at_is_set(self, db):
        before = datetime.utcnow()
        p = create_paste(db, content="x", language="plaintext")
        assert p.created_at >= before


class TestGetPaste:
    def test_returns_existing_paste(self, db):
        p = create_paste(db, content="hello", language="python")
        fetched = get_paste(db, p.short_code)
        assert fetched is not None
        assert fetched.short_code == p.short_code
        assert fetched.content == "hello"

    def test_returns_none_for_unknown_code(self, db):
        assert get_paste(db, "XXXXXXXX") is None

    def test_returns_none_for_expired_paste(self, db):
        p = create_paste(db, content="gone", language="plaintext")
        p.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        result = get_paste(db, p.short_code)
        assert result is None

    def test_deletes_expired_paste_from_db(self, db):
        p = create_paste(db, content="gone", language="plaintext")
        code = p.short_code
        p.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        get_paste(db, code)
        assert db.query(Paste).filter(Paste.short_code == code).first() is None

    def test_non_expired_paste_returned(self, db):
        p = create_paste(db, content="still here", language="plaintext", expiry="1d")
        fetched = get_paste(db, p.short_code)
        assert fetched is not None


class TestIncrementViews:
    def test_increments_by_one(self, db):
        p = create_paste(db, content="x", language="plaintext")
        assert p.views == 0
        increment_views(db, p)
        assert p.views == 1

    def test_multiple_increments(self, db):
        p = create_paste(db, content="x", language="plaintext")
        for _ in range(5):
            increment_views(db, p)
        assert p.views == 5

    def test_persisted_to_db(self, db):
        p = create_paste(db, content="x", language="plaintext")
        increment_views(db, p)
        fresh = db.query(Paste).filter(Paste.short_code == p.short_code).first()
        assert fresh.views == 1
