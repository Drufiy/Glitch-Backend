"""
Supabase client configuration
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Optional[object] = None

try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[SUPABASE] Connected successfully")
    else:
        print("[WARNING] SUPABASE_URL and/or SUPABASE_KEY not set. Thread persistence disabled.")
        print("[INFO] To enable threads, set SUPABASE_URL and SUPABASE_KEY in .env file")
except Exception as e:
    print(f"[WARNING] Failed to initialize Supabase: {e}")
    print("[INFO] App will continue with in-memory storage only")
    supabase = None

def is_supabase_available() -> bool:
    """Check if Supabase is available"""
    return supabase is not None

