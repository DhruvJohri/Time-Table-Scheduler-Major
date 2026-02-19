"""
Export Routes - JSON, CSV, PDF, Share
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from bson.objectid import ObjectId
from io import StringIO, BytesIO
import csv
import json
from datetime import datetime
from app.models.database import timetables_collection
import os

router = APIRouter(prefix="/api/export", tags=["export"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/{timetable_id}/json")
async def export_json(timetable_id: str):
    """Export timetable as JSON"""
    try:
        timetable = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        timetable["_id"] = str(timetable.get("_id"))
        
        # Convert datetime objects to strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        json_content = json.dumps(timetable, default=convert_datetime, indent=2)
        
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.json"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{timetable_id}/csv")
async def export_csv(timetable_id: str):
    """Export timetable as CSV"""
    try:
        timetable = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Start Time", "End Time", "Activity Type", "Subject/Title", "Description"])

        # Get blocks
        timetable_data = timetable.get("timetable", {})
        if isinstance(timetable_data, dict) and "days" in timetable_data:
            blocks = []
            for day in timetable_data.get("days", []):
                blocks.extend(day.get("blocks", []))
        else:
            blocks = timetable_data.get("blocks", [])

        # Write blocks
        for block in blocks:
            writer.writerow([
                block.get("start", ""),
                block.get("end", ""),
                block.get("type", ""),
                block.get("subject", block.get("title", "")),
                block.get("description", "")
            ])

        csv_content = output.getvalue()
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.csv"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{timetable_id}/pdf")
async def export_pdf(timetable_id: str):
    """Export timetable as HTML (for PDF conversion on client)"""
    try:
        timetable = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        html = _generate_html_timetable(timetable)
        
        return StreamingResponse(
            iter([html]),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.html"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{timetable_id}/share")
async def get_share_link(timetable_id: str):
    """Generate shareable link"""
    try:
        timetable = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        share_url = f"{FRONTEND_URL}/share/{timetable_id}"

        return {
            "shareUrl": share_url,
            "timetableId": timetable_id,
            "type": timetable.get("type"),
            "date": timetable.get("date"),
            "createdAt": timetable.get("created_at").isoformat() if timetable.get("created_at") else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def _generate_html_timetable(timetable: dict) -> str:
    """Generate HTML representation of timetable"""
    
    timetable_data = timetable.get("timetable", {})
    
    if isinstance(timetable_data, dict) and "days" in timetable_data:
        blocks = []
        for day in timetable_data.get("days", []):
            blocks.extend(day.get("blocks", []))
    else:
        blocks = timetable_data.get("blocks", []) if isinstance(timetable_data, dict) else []

    blocks_html = ""
    for block in blocks:
        blocks_html += f"""
        <tr>
            <td>{block.get('start', '')}</td>
            <td>{block.get('end', '')}</td>
            <td>{block.get('type', '')}</td>
            <td>{block.get('subject', block.get('title', ''))}</td>
            <td>{block.get('description', '')}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI-Generated Timetable</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
                color: #333;
            }}
            .info {{
                color: #666;
                margin-bottom: 20px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }}
            th {{
                background-color: #3B82F6;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 12px;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            tr:hover {{
                background-color: #f0f0f0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">Your AI-Generated Timetable</div>
            <div class="info">
                <p><strong>Type:</strong> {timetable.get('type')}</p>
                <p><strong>Date:</strong> {timetable.get('date')}</p>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Start Time</th>
                        <th>End Time</th>
                        <th>Activity Type</th>
                        <th>Subject/Title</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {blocks_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    return html
