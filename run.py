#!/usr/bin/env python3
"""
Main application runner
"""
from fastapi import FastAPI
from app.config.setting import settings
from app.routes import health, bot, session

# Create FastAPI app
app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# Include routers
app.include_router(session.router)
app.include_router(health.router)
app.include_router(bot.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)