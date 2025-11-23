#!/usr/bin/env python3
"""
Main application runner
"""
from fastapi import FastAPI
from app.routes.route import router as api_router
from app.routes.auth import router as auth_router
from app.routes.threads import router as threads_router
from fastapi.middleware.cors import CORSMiddleware
# Migration note: SQLAlchemy/SQLite removed in favor of Supabase.
from fastapi import Request
from fastapi.responses import JSONResponse
from os import environ 

# Database table creation is now handled in Supabase via SQL schema.

app = FastAPI(title="Glitch API", version="1.0.0")

# Initialize on/off switch state (True = ON, False = OFF)
app.state.server_enabled = True

# --- BEGIN MODIFICATION FOR GCP DEPLOYMENT ---

# 1. Fetch the deployed HTTPS URL from a GCP-injected environment variable.
DEPLOYED_URL = environ.get("GCP_BACKEND_URL", "")

# 2. Define the list of allowed origins.
ALLOWED_ORIGINS = [
    # Kept: Local development origin (e.g., Next.js dev server)
    "http://localhost:3000",
    # Kept: Tauri internal webview origin (essential for local testing/packaged app)
    "tauri://localhost",
]

# 3. Add the deployed HTTPS URL only if it exists (i.e., only when running on GCP)
if DEPLOYED_URL:
    ALLOWED_ORIGINS.append(DEPLOYED_URL)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- END MODIFICATION ---

# Toggle middleware
@app.middleware("http")
async def switch_middleware(request: Request, call_next):
    
    # --- CRITICAL FIX: Allow OPTIONS (CORS pre-flight) requests to proceed ---
    # This prevents the "failed to fetch" error caused by the middleware blocking the pre-flight check.
    if request.method == "OPTIONS":
        return await call_next(request)
    # -----------------------------------------------------------------------
    
    switch_param = request.query_params.get("switch")

    if switch_param is not None:
        value = switch_param.strip().lower()
        if value in {"true", "false"}:
            app.state.server_enabled = (value == "true")
            return JSONResponse({"message": "server switch updated", "server_enabled": app.state.server_enabled})
        return JSONResponse({"error": "invalid switch value; use true or false"}, status_code=400)

    if not app.state.server_enabled:
        return JSONResponse({"error": "server is currently disabled"}, status_code=503)

    response = await call_next(request)
    return response

# Routes
app.include_router(api_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(threads_router, tags=["threads"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
