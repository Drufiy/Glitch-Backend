#!/usr/bin/env python3
"""
Main application runner
"""
from fastapi import FastAPI
from app.routes.route import router as api_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Diagnostic Bot API", version="1.0.0")


# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # or restrict to ["GET", "POST"]
    allow_headers=["*"],  # or restrict if you know exact headers
)


# Routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)