"""
Main FastAPI application
AI Timetable Generator Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from app.routes import timetables
from app.models.database import init_db

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="AI Timetable Generator",
    description="Production-grade constraint-based scheduler for college timetables",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(timetables.router)


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
        "description": "Production-grade constraint-based scheduler for college timetables",
        "endpoints": {
            "health": "/health",
            "generate_timetable": "POST /api/timetable/generate",
            "get_timetable": "GET /api/timetable",
            "get_branch_timetable": "GET /api/timetable/{branch_code}/{year}/{section}",
            "validate": "POST /api/timetable/validate",
            "statistics": "GET /api/timetable/statistics",
            "clear": "DELETE /api/timetable/clear",
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
