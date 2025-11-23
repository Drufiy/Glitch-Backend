#!/usr/bin/env python3
"""
Main application runner
"""
from fastapi import FastAPI
from app.routes.route import router as api_router
from app.routes.auth import router as auth_router
from app.routes.threads import router as threads_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from os import environ

app = FastAPI(title="Glitch API", version="1.0.0")

# Initialize on/off switch state (True = ON, False = OFF)
app.state.server_enabled = True

# --- BEGIN MODIFICATION FOR GCP DEPLOYMENT ---

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

# --- END MODIFICATION ---


# Toggle middleware
@app.middleware("http")
async def switch_middleware(request: Request, call_next):

    # FIX: Handle OPTIONS manually, return 200
    if request.method == "OPTIONS":
        return JSONResponse(status_code=200, content={"detail": "OK"})

    switch_param = request.query_params.get("switch")

    if switch_param is not None:
        value = switch_param.strip().lower()
        if value in {"true", "false"}:
            request.app.state.server_enabled = (value == "true")
            return JSONResponse(
                {"message": "server switch updated", "server_enabled": request.app.state.server_enabled}
            )
        return JSONResponse({"error": "invalid switch value; use true or false"}, status_code=400)

    if not request.app.state.server_enabled:
        return JSONResponse({"error": "server is currently disabled"}, status_code=503)

    return await call_next(request)


# Routes
app.include_router(api_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(threads_router, tags=["threads"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
