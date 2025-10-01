#!/usr/bin/env python3
"""Script to grant all screen access permissions to all roles"""

import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = "sqlite:///./backend/db/dev.db"

# All screen permissions that should be granted to all roles
ALL_SCREEN_PERMISSIONS = [
    # Dashboard
    "dashboard:read",

    # Users management
    "read:users",
    "create:users",
    "update:users",
    "delete:users",
    "users:write",

    # Roles management
    "read:roles",
    "create:roles",
    "update:roles",
    "delete:roles",

    # Audit logs
    "read:audit_logs",

    # Keep existing permissions
    "read:protected",
    "users:create",
    "roles:manage",
    "*"
]

def grant_all_screen_access():
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get all roles
        result = db.execute(text("SELECT id, name, permissions FROM roles"))
        roles = result.fetchall()

        print(f'Found {len(roles)} roles to update with full screen access:')

        # Update each role with all permissions
        for role in roles:
            role_id, role_name, current_permissions_json = role

            # Parse current permissions
            try:
                current_permissions = json.loads(current_permissions_json) if current_permissions_json else []
            except (json.JSONDecodeError, TypeError):
                current_permissions = []

            # Combine current permissions with all screen permissions (avoid duplicates)
            updated_permissions = list(set(current_permissions + ALL_SCREEN_PERMISSIONS))

            # Convert back to JSON
            updated_permissions_json = json.dumps(updated_permissions)

            print(f'- {role_name}: {current_permissions} -> {updated_permissions}')

            # Update the role in database
            update_query = text("UPDATE roles SET permissions = :permissions WHERE id = :role_id")
            db.execute(update_query, {
                "permissions": updated_permissions_json,
                "role_id": role_id
            })

        # Commit changes
        db.commit()

        print(f'\nSuccessfully granted all screen access permissions to {len(roles)} roles')
        print('All roles now have access to:')
        for perm in ALL_SCREEN_PERMISSIONS:
            print(f'  - {perm}')

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    grant_all_screen_access()