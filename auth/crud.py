from sqlalchemy.orm import Session

from .hashing import hash_password, verify_password
from .models import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, plain_password: str) -> User:
    user = User(username=username, hashed_password=hash_password(plain_password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | bool:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user
