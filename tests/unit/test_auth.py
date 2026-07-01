import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")

from auth.database import Base
from auth.hashing import hash_password, verify_password
from auth.jwt import create_access_token, decode_access_token
from auth.crud import authenticate_user, create_user, get_user_by_username
from fastapi import HTTPException


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# --- hashing ---

def test_hash_and_verify_roundtrip():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)


def test_wrong_password_fails_verification():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


# --- jwt ---

def test_token_roundtrip():
    token = create_access_token({"sub": "alice"})
    token_data = decode_access_token(token)
    assert token_data.username == "alice"


def test_tampered_token_raises_401():
    token = create_access_token({"sub": "alice"})
    tampered = token[:-4] + "XXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_missing_sub_raises_401():
    token = create_access_token({"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


# --- crud ---

def test_create_and_retrieve_user(db):
    user = create_user(db, "bob", "password123")
    assert user.id is not None
    assert user.username == "bob"
    assert user.is_active is True

    fetched = get_user_by_username(db, "bob")
    assert fetched is not None
    assert fetched.id == user.id


def test_get_nonexistent_user_returns_none(db):
    assert get_user_by_username(db, "nobody") is None


def test_authenticate_user_success(db):
    create_user(db, "carol", "secret")
    result = authenticate_user(db, "carol", "secret")
    assert result is not False
    assert result.username == "carol"


def test_authenticate_user_wrong_password(db):
    create_user(db, "dave", "correct")
    assert authenticate_user(db, "dave", "wrong") is False


def test_authenticate_user_unknown_username(db):
    assert authenticate_user(db, "ghost", "pass") is False
