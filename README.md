"""
README - AI Timetable Generator Backend (Python)

Production-ready Python backend for AI-powered intelligent timetable generation.

## About

This is the core backend service for the AI Timetable Generator system. It provides:

- **Intelligent Scheduling Engine**: Advanced algorithm for generating optimized timetables
- **REST API**: FastAPI-based REST endpoints for profile and timetable management
- **MongoDB Integration**: Persistent data storage
- **AI Optimizations**: Multiple optimization modes (reduce stress, focus, add revision, etc.)
- **Export Functionality**: JSON, CSV, PDF, and shareable links

## Tech Stack

- **Framework**: FastAPI (async Python web framework)
- **Database**: MongoDB
- **Language**: Python 3.8+
- **Key Dependencies**: 
  - fastapi
  - uvicorn
  - pydantic
  - pymongo
  - python-dotenv

## Project Structure

```
ai-timetable-backend/
├── app/
│   ├── models/
│   │   └── database.py          # MongoDB connection & collections
│   ├── routes/
│   │   ├── profiles.py          # User profile endpoints
│   │   ├── timetables.py        # Timetable generation endpoints
│   │   └── export.py            # Export functionality endpoints
│   ├── services/
│   │   └── scheduling_engine.py # Core scheduling logic
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── main.py                  # FastAPI app setup
│   └── __init__.py
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB running locally or remote connection

### Setup

1. **Clone or navigate to the project:**
```bash
cd ai-timetable-backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your MongoDB connection string
```

5. **Ensure MongoDB is running:**
```bash
# Local MongoDB should be running on mongodb://localhost:27017
# Or update MONGODB_URI in .env
```

## Running the Server

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: http://localhost:8000

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Python directly

```bash
python -m uvicorn app.main:app --reload
```

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Profile Management

```
POST   /api/profiles              - Create user profile
GET    /api/profiles/{email}      - Get profile by email
PUT    /api/profiles/{email}      - Update profile
DELETE /api/profiles/{email}      - Delete profile
```

### Timetable Generation

```
POST   /api/timetables/generate   - Generate new timetable
GET    /api/timetables/{id}       - Get timetable by ID
GET    /api/timetables/user/{id}  - Get all user timetables
PUT    /api/timetables/{id}       - Edit timetable
POST   /api/timetables/{id}/regenerate - Regenerate with optimization
DELETE /api/timetables/{id}       - Delete timetable
```

### Export

```
GET    /api/export/{id}/json      - Export as JSON
GET    /api/export/{id}/csv       - Export as CSV
GET    /api/export/{id}/pdf       - Export as HTML/PDF
GET    /api/export/{id}/share     - Get shareable link
```

## Core Features

### 1. Scheduling Engine

The `SchedulingEngine` class implements intelligent timetable generation:

- **Time-aware distribution**: Distributes study subjects across available time
- **Energy curves**: Respects productivity patterns (morning person, night owl, balanced)
- **Smart breaks**: Inserts breaks strategically between study blocks
- **Fixed activities**: Accommodates work, meals, exercise schedules
- **Free time**: Allocates requested free time
- **Weekend optimization**: Different schedules for weekends

### 2. AI Optimizations

Modify generated timetables with:

- **reduce_stress**: Shorter study blocks, more breaks
- **more_focus**: Longer study blocks, minimal breaks
- **add_revision**: Include revision slots for studied subjects
- **weekend_relax**: Lighter workload overall

### 3. Timetable Types

Generate different timetable formats:

- **daily**: Single day timetable
- **weekly**: 7-day timetable with weekends
- **exam_mode**: Intensive study schedule
- **workday**: Work-focused schedule
- **weekend**: Relaxed schedule

## Request Examples

### Create User Profile

```bash
curl -X POST http://localhost:8000/api/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Doe",
    "is_student": true,
    "wake_up_time": "06:00",
    "sleep_time": "23:00",
    "work_start_time": "09:00",
    "work_end_time": "17:00",
    "subjects": [
      {"name": "DSA", "priority": 1, "daily_hours": 3},
      {"name": "Web Dev", "priority": 2, "daily_hours": 2}
    ],
    "productivity_type": "morning_person",
    "goal_type": "exam_prep",
    "break_frequency": 30,
    "lunch_time_preference": "12:30",
    "tea_time_preference": "15:00",
    "exercise_time": "07:00",
    "exercise_duration": 45,
    "free_time_required": 2,
    "preferred_timetable_type": "daily"
  }'
```

### Generate Timetable

```bash
curl -X POST http://localhost:8000/api/timetables/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_ObjectId_here",
    "timetable_type": "daily",
    "start_date": "2024-01-20",
    "optimization": null
  }'
```

### Regenerate with Optimization

```bash
curl -X POST http://localhost:8000/api/timetables/{timetable_id}/regenerate \
  -H "Content-Type: application/json" \
  -d '{
    "optimization": "reduce_stress"
  }'
```

## Database Schema

### Users Collection

```json
{
  "_id": ObjectId,
  "email": "string (unique)",
  "name": "string",
  "wake_up_time": "HH:MM",
  "sleep_time": "HH:MM",
  "work_start_time": "HH:MM",
  "work_end_time": "HH:MM",
  "is_student": boolean,
  "subjects": [
    {
      "name": "string",
      "priority": 1-5,
      "daily_hours": float,
      "topics": ["string"]
    }
  ],
  "productivity_type": "morning_person|night_owl|balanced",
  "goal_type": "exam_prep|work_productivity|balanced_life|fitness_focus",
  "break_frequency": integer,
  "lunch_time_preference": "HH:MM",
  "tea_time_preference": "HH:MM",
  "exercise_time": "HH:MM",
  "exercise_duration": integer,
  "free_time_required": float,
  "preferred_timetable_type": "daily|weekly|exam_mode|workday|weekend"
}
```

### Timetables Collection

```json
{
  "_id": ObjectId,
  "user_id": "string",
  "type": "daily|weekly|exam_mode|workday|weekend",
  "date": "YYYY-MM-DD",
  "timetable": {
    "day": "string",
    "blocks": [
      {
        "start": "HH:MM",
        "end": "HH:MM",
        "type": "study|work|meal|exercise|break|sleep|free_time|revision",
        "subject": "string (optional)",
        "title": "string (optional)",
        "priority": integer,
        "energy_level": "high|medium|low"
      }
    ]
  },
  "modifications": [
    {
      "type": "optimization_type",
      "timestamp": "ISO date",
      "previous_timetable": [],
      "new_timetable": []
    }
  ],
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

## Configuration

Environment variables in `.env`:

```env
# Database
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=ai-timetable

# Server
PORT=8000
ENV=development
```

## Error Handling

API returns standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **404**: Not Found
- **500**: Internal Server Error

Error response format:

```json
{
  "detail": "Error message describing the issue"
}
```

## Performance Considerations

- **Scheduling Engine**: Generates timetables in < 100ms
- **MongoDB Indexing**: Automatic indexes on user_id and created_at
- **Async/Await**: All I/O operations are non-blocking
- **CORS**: Enabled for frontend integration

## Security Notes

For production:

1. Remove CORS allow_origins=["*"], restrict to specific domains
2. Add authentication (JWT, OAuth2)
3. Validate all inputs rigorously
4. Use environment variables for sensitive data
5. Run MongoDB with authentication enabled
6. Rate limiting on API endpoints

## Testing

Create test profiles and generate timetables:

```bash
# Use the API documentation UI at http://localhost:8000/docs
# Or use the curl examples provided above
```

## Troubleshooting

### MongoDB Connection Error

```
Error: Failed to connect to MongoDB
```

Solution:
- Ensure MongoDB is running
- Check MONGODB_URI in .env
- Verify network connectivity

### Port Already in Use

```
ERROR: Address already in use
```

Solution:
```bash
# Use different port
uvicorn app.main:app --port 8001
```

## Future Enhancements

- OpenAI integration for smart optimizations
- caching for frequently accessed timetables
- batch timetable generation
- Real-time WebSocket updates
- Mobile app support
- Calendar integration (Google Calendar, Outlook)
- AI-powered schedule conflict resolution

## License

MIT License

## Support

For issues or questions, please refer to the project documentation or contact the development team.
