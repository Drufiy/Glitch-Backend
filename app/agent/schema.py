from pydantic import BaseModel
from typing import Optional, Literal, List
from datetime import datetime

class HistoryEntry(BaseModel):
    timestamp: datetime
    message: str
    command: Optional[str] = None
    command_output: Optional[str] = None

class DiagnoseRequest(BaseModel):
    problem: str
    command_output: Optional[str] = None
    session_id: Optional[str] = None  # Deprecated: use thread_id instead
    thread_id: Optional[str] = None  # Thread ID for conversation continuity

class DiagnoseResponse(BaseModel):
    message: str
    command: Optional[str] = None
    next_step: Literal["command", "message"]
    session_id: str  # Deprecated: kept for backward compatibility
    thread_id: Optional[str] = None  # Thread ID
    history: List[HistoryEntry]

# Schema for structured generation
class DiagnosisOutput(BaseModel):
    """Structured output schema for AI diagnosis"""
    message: str
    command: str = ""
    next_step: Literal["command", "message"]
