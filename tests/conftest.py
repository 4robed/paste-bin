import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite:///./test_pastebin.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def plain_paste(client):
    resp = client.post("/", data={"content": "hello world", "language": "plaintext", "expiry": "never"}, follow_redirects=False)
    assert resp.status_code == 303
    code = resp.headers["location"].lstrip("/")
    return code


@pytest.fixture()
def python_paste(client):
    resp = client.post(
        "/",
        data={"title": "My Script", "content": "print('hello')\nx = 1 + 2\nprint(x)", "language": "python", "expiry": "never"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    code = resp.headers["location"].lstrip("/")
    return code


@pytest.fixture()
def protected_paste(client):
    resp = client.post(
        "/",
        data={"content": "secret code", "language": "plaintext", "password": "hunter2", "expiry": "never"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    code = resp.headers["location"].lstrip("/")
    return code
