from fastapi import APIRouter, HTTPException, Depends
from fastapi import status
from typing import Optional, Dict, List
from datetime import datetime

from app.agent.prompts import sys_info_prompt
from app.agent.schema import DiagnoseRequest, DiagnoseContinueRequest, DiagnoseResponse, DiagnosisOutput
from app.agent.agents import custom_agent
from app.database.thread_service import ThreadService
from app.routes.auth import get_current_user


router = APIRouter()


# -----------------------------
# HEALTH CHECK
# -----------------------------
@router.get("/health")
def health() -> dict:
    return {"status": "healthy"}


# -----------------------------
# HISTORY HELPERS
# -----------------------------
def _render_history_section(thread_id: Optional[str] = None) -> str:
    """Format the last 5 messages of the thread for use in prompts."""
    history = ThreadService.get_messages(thread_id, limit=10) if thread_id else []

    if not history:
        return "No previous steps."

    lines = []
    for entry in history[-5:]:
        line = f"[{entry.timestamp.isoformat()}] message: {entry.message}"
        if entry.command:
            line += f" | command: {entry.command}"
        if entry.command_output:
            line += f" | output: {entry.command_output}"
        lines.append(line)

    return "\n".join(lines)


def _previous_commands(thread_id: Optional[str] = None) -> List[str]:
    """Get previous commands sent by the AI."""
    history = ThreadService.get_messages(thread_id, limit=20) if thread_id else []
    cmds = [msg.command for msg in history if msg.command]
    return cmds[-10:]


def _last_command(thread_id: Optional[str] = None) -> Optional[str]:
    """Get the last command that was stored in the thread."""
    history = ThreadService.get_messages(thread_id, limit=20) if thread_id else []
    for entry in reversed(history):
        if entry.command:
            return entry.command
    return None


# ============================================================
# ROUTE 1 — FIRST DIAGNOSE (NO EXECUTION)
# ============================================================
@router.post("/diagnose", response_model=DiagnoseResponse, status_code=status.HTTP_200_OK)
def diagnose(payload: DiagnoseRequest, current_user: Dict = Depends(get_current_user)) -> DiagnoseResponse:

    user_id = current_user.get("id")
    thread_id = payload.thread_id

    # -------------------------
    # THREAD RESOLUTION
    # -------------------------
    if thread_id:
        thread = ThreadService.get_thread(thread_id)
        if not thread:
            thread_id = ThreadService.create_thread(
                user_id=user_id,
                title=payload.problem[:50]
            )
        else:
            if thread.get("user_id") != user_id:
                raise HTTPException(403, "Not authorized to access this thread")
    else:
        thread_id = ThreadService.create_thread(
            user_id=user_id,
            title=payload.problem[:50]
        )

    # -------------------------
    # STORE USER MESSAGE
    # -------------------------
    ThreadService.add_message(
        thread_id=thread_id,
        role="user",
        message=payload.problem,
        user_id=user_id,
    )

    # -------------------------
    # PREPARE SYSTEM PROMPT
    # -------------------------
    history_section = _render_history_section(thread_id)
    command_output_section = "No command executed yet."

    system_prompt = sys_info_prompt.format(
        problem=payload.problem,
        history_section=history_section,
        command_output_section=command_output_section,
    )

    prev_cmds = _previous_commands(thread_id)

    # -------------------------
    # CALL AI
    # -------------------------
    try:
        ai_output: DiagnosisOutput = custom_agent(
            system_prompt=system_prompt,
            user_query=payload.problem,
            response_model=DiagnosisOutput,
        )
    except Exception as e:
        ai_output = DiagnosisOutput(
            message=f"Internal error while processing your request: {str(e)}",
            command="",
            next_step="message",
        )

    # -------------------------
    # STORE AI RESPONSE (NO EXECUTION)
    # -------------------------
    ThreadService.add_message(
        thread_id=thread_id,
        role="assistant",
        message=ai_output.message,
        command=ai_output.command,
        command_output=None,
        user_id=user_id,
    )

    history = ThreadService.get_messages(thread_id)

    return DiagnoseResponse(
        message=ai_output.message,
        command=ai_output.command or None,
        next_step=ai_output.next_step,
        session_id=thread_id,
        thread_id=thread_id,
        history=history,
    )


# ============================================================
# ROUTE 2 — CONTINUE AFTER COMMAND EXECUTION
# ============================================================
@router.post("/diagnose/continue", response_model=DiagnoseResponse)
def diagnose_continue(payload: DiagnoseContinueRequest, current_user: Dict = Depends(get_current_user)):

    user_id = current_user.get("id")
    thread_id = payload.thread_id

    if not thread_id:
        raise HTTPException(400, "Missing thread_id for continuation")

    thread = ThreadService.get_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")

    if thread.get("user_id") != user_id:
        raise HTTPException(403, "Not authorized for this thread")

    # -------------------------
    # STORE USER'S COMMAND OUTPUT
    # -------------------------
    ThreadService.add_message(
        thread_id=thread_id,
        role="user",
        message=f"Command output for: {payload.command}",
        command=payload.command,
        command_output=payload.command_output,
        user_id=user_id,
    )

    # -------------------------
    # PREPARE RE-PROMPT FOR GEMINI
    # -------------------------
    history_section = _render_history_section(thread_id)
    command_output_section = payload.command_output or "No output"

    system_prompt = sys_info_prompt.format(
        problem="Continuing troubleshooting...",
        history_section=history_section,
        command_output_section=command_output_section,
    )

    # -------------------------
    # CALL AI AGAIN
    # -------------------------
    try:
        ai_output: DiagnosisOutput = custom_agent(
            system_prompt=system_prompt,
            user_query=f"Command output:\n{payload.command_output}",
            response_model=DiagnosisOutput,
        )
    except Exception as e:
        ai_output = DiagnosisOutput(
            message=f"Error interpreting command output: {str(e)}",
            command="",
            next_step="message",
        )

    # -------------------------
    # STORE AI RESPONSE
    # -------------------------
    ThreadService.add_message(
        thread_id=thread_id,
        role="assistant",
        message=ai_output.message,
        command=ai_output.command,
        command_output=None,
        user_id=user_id,
    )

    history = ThreadService.get_messages(thread_id)

    return DiagnoseResponse(
        message=ai_output.message,
        command=ai_output.command or None,
        next_step=ai_output.next_step,
        session_id=thread_id,
        thread_id=thread_id,
        history=history,
    )
