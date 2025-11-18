"""
Database package initializer.

This file exposes common database-level symbols for backward compatibility
so other modules can `from app.database import supabase, is_supabase_available`
or still import submodules like `from app.database.thread_service import ThreadService`.
"""
from .supabase_client import supabase, is_supabase_available  # type: ignore
from .supabase_auth import get_user_by_email, create_user, verify_user_credentials  # type: ignore
from .thread_service import ThreadService  # type: ignore

__all__ = [
	"supabase",
	"is_supabase_available",
	"get_user_by_email",
	"create_user",
	"verify_user_credentials",
	"ThreadService",
]
