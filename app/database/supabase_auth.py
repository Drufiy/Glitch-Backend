from typing import Optional, Dict
from werkzeug.security import generate_password_hash, check_password_hash

from app.database.supabase_client import supabase, is_supabase_available


def get_user_by_email(email: str) -> Optional[Dict]:
    """Return a user row from Supabase by email or None."""
    if not is_supabase_available():
        return None

    try:
        result = supabase.table("users").select("*").eq("email", email).limit(1).execute()
        data = result.data or []
        if len(data) == 0:
            return None
        return data[0]
    except Exception as e:
        print(f"[SUPABASE_AUTH] Failed to get user: {e}")
        return None


def create_user(email: str, password: str, name: Optional[str] = None) -> Optional[Dict]:
    """Create a user in Supabase `users` table with a hashed password."""
    if not is_supabase_available():
        return None

    try:
        password_hash = generate_password_hash(password)
        user_data = {"email": email, "password_hash": password_hash, "name": name}
        result = supabase.table("users").insert(user_data).execute()
        inserted = result.data or []
        if len(inserted) == 0:
            return None
        return inserted[0]
    except Exception as e:
        print(f"[SUPABASE_AUTH] Failed to create user: {e}")
        return None


def verify_user_credentials(email: str, password: str) -> bool:
    """Verify email/password against the hash stored in Supabase."""
    user = get_user_by_email(email)
    if not user:
        return False
    stored_hash = user.get("password_hash")
    if not stored_hash:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except Exception:
        return False
