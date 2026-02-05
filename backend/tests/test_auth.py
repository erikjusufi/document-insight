import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import get_engine, get_session
from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    get_settings.cache_clear()
    settings = get_settings()
    settings.sample_docs_dir = str(sample_dir)
    settings.qa_load_on_startup = False
    get_engine.cache_clear()

    app = create_app()

    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app.state.sessionmaker = SessionLocal

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_register_login_me(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "user@example.com"

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"


def test_login_invalid_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user2@example.com", "password": "secret123"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "user2@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_register_rejects_long_password(client: TestClient) -> None:
    long_password = "a" * 73
    response = client.post(
        "/auth/register",
        json={"email": "long@example.com", "password": long_password},
    )
    assert response.status_code == 422


def test_login_upgrades_legacy_hash(client: TestClient) -> None:
    from passlib.context import CryptContext

    legacy_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    legacy_hash = legacy_context.hash("secret123")

    register_response = client.post(
        "/auth/register",
        json={"email": "legacy@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201

    SessionLocal = client.app.state.sessionmaker
    with SessionLocal() as session:
        session.execute(
            text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
            {"hash": legacy_hash, "email": "legacy@example.com"},
        )
        session.commit()

    login_response = client.post(
        "/auth/login",
        json={"email": "legacy@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT hashed_password FROM users WHERE email = :email"),
            {"email": "legacy@example.com"},
        ).one()
    assert row[0].startswith("$2")
