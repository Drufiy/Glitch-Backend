#!/usr/bin/env python3
"""
Main application runner for Glitch Backend
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes.route import router as api_router
from app.routes.auth import router as auth_router
from app.routes.threads import router as threads_router
from os import environ

app = FastAPI(title="Glitch API", version="1.0.0")

# Server switch state (ON by default)
app.state.server_enabled = True


# ============================================================
# CORS CONFIGURATION FOR CLOUD RUN
# ============================================================

DEPLOYED_URL = environ.get("GCP_BACKEND_URL", "")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "tauri://localhost",
]

if DEPLOYED_URL:
    ALLOWED_ORIGINS.append(DEPLOYED_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# SERVER SWITCH MIDDLEWARE (with correct preflight behavior)
# ============================================================

@app.middleware("http")
async def switch_middleware(request: Request, call_next):
    # Handle preflight immediately
    if request.method == "OPTIONS":
        response = JSONResponse(status_code=200, content={"detail": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    # Handle switch control
    switch_param = request.query_params.get("switch")
    if switch_param is not None:
        value = switch_param.strip().lower()

        if value in {"true", "false"}:
            request.app.state.server_enabled = (value == "true")
            return JSONResponse({
                "message": "server switch updated",
                "server_enabled": request.app.state.server_enabled
            })

        return JSONResponse(
            {"error": "invalid switch value; use true or false"},
            status_code=400
        )

    # If server disabled → block all endpoints
    if not request.app.state.server_enabled:
        return JSONResponse(
            {"error": "server is currently disabled"},
            status_code=503
        )

    # Process request normally
    return await call_next(request)


# ============================================================
# ROUTES
# ============================================================

app.include_router(api_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(threads_router, tags=["threads"])


# ============================================================
# UVICORN ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
