"""
Seed test users from `test_users.py`.

Usage:
  1. Edit `scripts/test_users.py` and fill the "password" fields for the users you want to create.
  2. Run: python scripts/seed_test_users.py

Notes:
  - Users with empty password field will be skipped and reported.
  - This script uses the project's `create_user` helper which hashes passwords correctly.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_auth import create_user, get_user_by_email
from scripts.test_users import TEST_USERS


def main():
    print("Starting test user seeding...\n")
    created = 0
    skipped = 0
    exists = 0

    for u in TEST_USERS:
        email = u.get("email")
        password = u.get("password")
        name = u.get("name") or ""

        if not password:
            print(f"SKIP (no password set): {email}")
            skipped += 1
            continue

        try:
            existing = get_user_by_email(email)
            if existing:
                print(f"EXISTS: {email}")
                exists += 1
                continue

            ok = create_user(email, password, name)
            if ok:
                print(f"CREATED: {email} (name: {name})")
                created += 1
            else:
                print(f"FAILED: {email}")
        except Exception as e:
            print(f"ERROR: {email} -> {e}")

    print("\nSummary:")
    print(f"  Created: {created}")
    print(f"  Skipped (no password): {skipped}")
    print(f"  Already existed: {exists}")


if __name__ == '__main__':
    main()
