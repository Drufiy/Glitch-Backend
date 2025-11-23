from dotenv import load_dotenv
import os

# Load variables from .env file (for local development)
load_dotenv()

# --- Configuration variables loaded from the environment ---
# API Key for the LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# The secret key for signing JWT tokens (CRITICAL for security)
JWT_SECRET = os.getenv("JWT_SECRET") 

# Supabase configuration (loaded in supabase_client.py, but good to ensure consistency)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Check if the critical secret is present
if not JWT_SECRET:
    print("[CRITICAL WARNING] JWT_SECRET environment variable is missing. Authentication will fail.")
