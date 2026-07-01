"""
CLI utility to create users in the auth database.

Usage:
    python scripts/create_user.py --username alice --password secret
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth.crud import create_user, get_user_by_username
from auth.database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)


def main():
    parser = argparse.ArgumentParser(description="Create a user in the auth database")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Plain-text password (will be hashed)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if get_user_by_username(db, args.username):
            print(f"Error: username '{args.username}' already exists.")
            sys.exit(1)
        user = create_user(db, args.username, args.password)
        print(f"Created user: id={user.id}, username={user.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
