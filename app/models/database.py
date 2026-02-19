"""
Database connection and models
"""

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ai-timetable")

# MongoDB connection
client = MongoClient(MONGODB_URI)
db: Database = client[DATABASE_NAME]

# Collections
users_collection: Collection = db["users"]
timetables_collection: Collection = db["timetables"]

# Create indexes
users_collection.create_index("email", unique=True)
timetables_collection.create_index("user_id")
timetables_collection.create_index("created_at")


def get_db():
    """Get database instance"""
    return db


def close_db():
    """Close database connection"""
    client.close()
