"""
College Timetable Generator — FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from app.routes import auth, profiles, timetables, export
from app.routes import upload_master, upload_assignment

load_dotenv()

app = FastAPI(
    title="College Timetable Generator",
    description="Smart Dynamic Timetable Generator powered by OR-Tools CP-SAT",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(timetables.router)
app.include_router(export.router)
app.include_router(upload_master.router)
app.include_router(upload_assignment.router)


@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "College Timetable Generator is running"}


@app.get("/")
async def root():
    return {
        "name": "College Timetable Generator",
        "version": "2.0.0",
        "endpoints": {
            "health":            "/health",
            "auth":              "/api/auth/login",
            "profiles":          "/api/profiles",
            "upload_master":     "/api/upload/master",
            "upload_assignment": "/api/upload/assignment",
            "timetables":        "/api/timetables",
            "export":            "/api/export",
            "docs":              "/docs",
        }
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
