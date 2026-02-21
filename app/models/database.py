"""
College Timetable System — Database Collections
Indexes are created lazily (on first connection) so the app boots even
when MongoDB is temporarily unreachable.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MONGODB_URI   = os.getenv("MONGODB_URI",   "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ai-timetable")

# Connection (lazy — no ping at module load time)
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db: Database = client[DATABASE_NAME]

# ── Collections ───────────────────────────────────────────────────────────────
users_collection:           Collection = db["users"]
timetables_collection:      Collection = db["timetables"]
master_data_collection:     Collection = db["master_data"]
assignment_data_collection: Collection = db["assignment_data"]


def _create_indexes():
    """Create indexes. Called once on first real DB operation, not at import time."""
    try:
        users_collection.create_index("email", unique=True)
        timetables_collection.create_index("admin_id")
        timetables_collection.create_index([
            ("admin_id", ASCENDING),
            ("branch",   ASCENDING),
            ("year",     ASCENDING),
            ("version",  DESCENDING),
        ])
        timetables_collection.create_index("created_at")
        uploads_collection.create_index("admin_email")
        master_data_collection.create_index("admin_email")
        assignment_data_collection.create_index("admin_email")
        assignment_data_collection.create_index([
            ("admin_email", ASCENDING),
            ("branch",      ASCENDING),
            ("year",        ASCENDING),
        ])
        logger.info("MongoDB indexes created.")
    except Exception as exc:
        logger.warning(f"Could not create indexes (MongoDB may be unavailable): {exc}")


# Run index creation in a background thread so startup is never blocked
import threading
threading.Thread(target=_create_indexes, daemon=True).start()


def get_db() -> Database:
    return db


def close_db():
    client.close()
