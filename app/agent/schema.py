from pydantic import BaseModel
from typing import Optional, Literal, List
from datetime import datetime


# =============================================
# HISTORY ENTRY (stored in Supabase)
# =============================================
class HistoryEntry(BaseModel):
    timestamp: datetime
    message: str
    command: Optional[str] = None
    command_output: Optional[str] = None


# =============================================
# REQUEST: FIRST DIAGNOSE CALL
# =============================================
class DiagnoseRequest(BaseModel):
    problem: str
    command_output: Optional[str] = None

    # Deprecated, kept for compatibility
    session_id: Optional[str] = None

    # THREAD ID for the conversation
    thread_id: Optional[str] = None


# =============================================
# REQUEST: CONTINUE AFTER COMMAND EXECUTION
# =============================================
class DiagnoseContinueRequest(BaseModel):
    thread_id: str
    command: str
    command_output: str


# =============================================
# RESPONSE BACK TO FRONTEND
# =============================================
class DiagnoseResponse(BaseModel):
    message: str
    command: Optional[str] = None
    next_step: Literal["command", "message"]

    # Compatibility — session_id == thread_id
    session_id: str
    thread_id: Optional[str] = None

    history: List[HistoryEntry]


# =============================================
# AI STRUCTURED OUTPUT SCHEMA (Gemini)
# =============================================
class DiagnosisOutput(BaseModel):
    """
    Structured response from the AI model.
    next_step = "command" → AI wants user machine to run a command
    next_step = "message" → AI is done and returns explanation
    """
    message: str
    command: str = ""         # Command to run (optional)
    next_step: Literal["command", "message"]
