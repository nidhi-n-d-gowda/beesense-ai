import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from bedrock_engine import BedrockEngine

load_dotenv()

app = FastAPI(
    title="BeeSense AI - Enterprise Wearable Intelligence",
    description="Amazon Bedrock powered ambient wearable intelligence with Alexa+ cross-ecosystem sync",
    version="2.0.0"
)

bedrock = BedrockEngine()

# In-memory storage for ambient memory stream & synced Alexa actions
MEMORY_STREAM: List[Dict[str, Any]] = []
SYNCED_ACTIONS: List[Dict[str, Any]] = []

class TelemetryData(BaseModel):
    heart_rate: int = 74
    activity: str = "stationary"
    ambient_noise_db: int = 42
    location: str = "Work Desk"

class StreamEventRequest(BaseModel):
    transcription: str
    telemetry: Optional[TelemetryData] = None

class QueryMemoryRequest(BaseModel):
    query: str

class SyncAlexaRequest(BaseModel):
    title: str
    due_time: Optional[str] = "Today, 5:00 PM"
    category: Optional[str] = "task"

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "bedrock_ready": bedrock.client is not None,
        "memory_count": len(MEMORY_STREAM),
        "synced_actions_count": len(SYNCED_ACTIONS),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/stream/process")
def process_stream_event(req: StreamEventRequest):
    """
    Ingests live audio transcription & sensor telemetry from the Bee Wearable.
    """
    telemetry_dict = req.telemetry.model_dump() if req.telemetry else {
        "heart_rate": 72,
        "activity": "stationary",
        "ambient_noise_db": 45,
        "location": "Office"
    }
    
    # Process with Amazon Bedrock
    analysis = bedrock.analyze_ambient_stream(
        transcription=req.transcription,
        telemetry=telemetry_dict,
        recent_context=MEMORY_STREAM
    )
    
    memory_entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "transcription": req.transcription,
        "telemetry": telemetry_dict,
        "analysis": analysis
    }
    
    MEMORY_STREAM.append(memory_entry)
    
    # Auto-sync action items to Alexa+ Task Ecosystem if detected
    if analysis.get("action_items") and len(analysis["action_items"]) > 0:
        for item in analysis["action_items"]:
            SYNCED_ACTIONS.append({
                "id": str(uuid.uuid4())[:6],
                "task": item,
                "origin": "Bee Ambient Wearable",
                "synced_to": "Alexa+ Reminders & AWS Step Functions",
                "status": "Scheduled",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            
    return {
        "success": True,
        "memory_entry": memory_entry,
        "synced_actions": SYNCED_ACTIONS[-3:]
    }

@app.get("/api/memories")
def get_memories():
    """Retrieve full episodic memory stream."""
    return {"memories": list(reversed(MEMORY_STREAM))}

@app.post("/api/memories/query")
def query_second_brain(req: QueryMemoryRequest):
    """Query Second Brain memory using natural language."""
    result = bedrock.query_second_brain(req.query, MEMORY_STREAM)
    return result

@app.get("/api/alexa/synced")
def get_synced_actions():
    """Get list of tasks synced across the Amazon ecosystem."""
    return {"synced_actions": list(reversed(SYNCED_ACTIONS))}

@app.post("/api/alexa/sync-manual")
def manual_sync_alexa(req: SyncAlexaRequest):
    action = {
        "id": str(uuid.uuid4())[:6],
        "task": req.title,
        "origin": "Manual Wearable Nudge",
        "synced_to": "Alexa+ Smart Home & Reminders",
        "status": "Active",
        "timestamp": datetime.now().strftime("%I:%M %p")
    }
    SYNCED_ACTIONS.append(action)
    return {"success": True, "action": action}

@app.get("/api/export/summary")
def export_memory_summary():
    """Exports a structured JSON digest of all daily episodic memories & wellness stats."""
    total_memories = len(MEMORY_STREAM)
    tasks_count = len(SYNCED_ACTIONS)
    avg_hr = sum(m["telemetry"]["heart_rate"] for m in MEMORY_STREAM) / total_memories if total_memories > 0 else 72
    
    summary = {
        "report_title": "BeeSense AI Daily Cognitive & Biometric Digest",
        "generated_at": datetime.now().isoformat(),
        "metrics": {
            "total_ambient_events": total_memories,
            "tasks_extracted": tasks_count,
            "average_heart_rate": round(avg_hr, 1)
        },
        "key_memories": [
            {
                "time": m["timestamp"],
                "summary": m["analysis"].get("summary"),
                "category": m["analysis"].get("category"),
                "sentiment": m["analysis"].get("sentiment")
            }
            for m in MEMORY_STREAM
        ],
        "synced_alexa_tasks": SYNCED_ACTIONS
    }
    return JSONResponse(content=summary)

@app.delete("/api/memories/clear")
def clear_memories():
    global MEMORY_STREAM, SYNCED_ACTIONS
    MEMORY_STREAM.clear()
    SYNCED_ACTIONS.clear()
    return {"message": "Memory stream & synced actions cleared"}

# Static file serving
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>BeeSense AI is loading...</h1>"
