"""
Database configuration and session management
"""
import os
from typing import Optional, Generator
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Session management (for backward compatibility with old code)
class SessionLocal:
    """Compatibility wrapper for old session-based code"""
    def __init__(self):
        self.is_open = True
    
    def close(self):
        """Close session (no-op for Supabase)"""
        self.is_open = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Dependency for FastAPI
def get_db() -> Generator:
    """
    FastAPI dependency to provide database session.
    Maintains backward compatibility with old SQLAlchemy code.
    
    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            # db is a SessionLocal instance for compatibility
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Supabase client initialization
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DATABASE] ✅ Supabase connected successfully")
    else:
        print("[DATABASE] ⚠️  SUPABASE_URL and/or SUPABASE_KEY not set")
        print("[DATABASE] ℹ️  Set these in your .env file to enable persistence")
except Exception as e:
    print(f"[DATABASE] ❌ Failed to initialize Supabase: {e}")
    supabase = None


def is_database_available() -> bool:
    """Check if database (Supabase) is available"""
    return supabase is not None


# Base class compatibility (for old ORM code that referenced Base)
class Base:
    """Placeholder for old declarative_base()"""
    pass


# Database URL (for reference/logging)
SQLALCHEMY_DATABASE_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else "sqlite:///./submissions.db"

# Engine compatibility (for old code that might reference engine)
class Engine:
    """Placeholder for old SQLAlchemy engine"""
    def __init__(self, url: str):
        self.url = url
    
    def __repr__(self):
        return f"<Engine '{self.url}'>"


engine = Engine(SQLALCHEMY_DATABASE_URL)

__all__ = [
    "SessionLocal",
    "get_db",
    "supabase",
    "is_database_available",
    "Base",
    "engine",
    "SQLALCHEMY_DATABASE_URL",
]
