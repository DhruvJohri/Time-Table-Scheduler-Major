"""
run.py - Helper script to run the server
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    env = os.getenv("ENV", "development")
    
    print(f"🚀 Starting AI Timetable Generator Backend")
    print(f"📍 Environment: {env}")
    print(f"🔌 Port: {port}")
    print(f"🌐 URL: http://localhost:{port}")
    print(f"📖 Docs: http://localhost:{port}/docs")
    print()
    
    if env == "development":
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info"
        )
    else:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            workers=4,
            log_level="info"
        )
