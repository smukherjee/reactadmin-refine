#!/usr/bin/env python3
"""Script to reset all user passwords to 'pass1234'"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Database URL
DATABASE_URL = "sqlite:///./backend/db/dev.db"

# Password hashing context (same as in the app)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def reset_passwords():
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Hash the new password
        new_password = "pass1234"
        hashed_password = pwd_context.hash(new_password)

        # Get all users before update
        result = db.execute(text("SELECT id, email, password_hash FROM users"))
        users = result.fetchall()

        print(f'Found {len(users)} users to reset passwords:')
        for user in users:
            print(f'- {user.email}: {user.password_hash[:20]}...')

        # Update all user passwords
        update_query = text("UPDATE users SET password_hash = :hashed_password")
        db.execute(update_query, {"hashed_password": hashed_password})

        # Commit changes
        db.commit()

        print(f'\nSuccessfully reset passwords for {len(users)} users to "pass1234"')
        print(f'New hash: {hashed_password[:20]}...')

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_passwords()