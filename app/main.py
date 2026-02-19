"""
Main FastAPI application
AI Timetable Generator Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from app.routes import profiles, timetables, export

load_dotenv()

app = FastAPI(
    title="AI Timetable Generator",
    description="Intelligent scheduling engine for generating optimized timetables",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(profiles.router)
app.include_router(timetables.router)
app.include_router(export.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "message": "AI Timetable Generator Backend is running"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "AI Timetable Generator",
        "version": "1.0.0",
        "description": "Intelligent scheduling engine for generating optimized timetables",
        "endpoints": {
            "health": "/health",
            "profiles": "/api/profiles",
            "timetables": "/api/timetables",
            "export": "/api/export",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


# 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
