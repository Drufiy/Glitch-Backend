from fastapi import APIRouter, HTTPException
from fastapi import status
from typing import Optional

from app.agent.prompts import intent_prompt
from app.agent.schema import DiagnoseRequest, DiagnoseResponse, DiagnosisOutput
from app.agent.agents import custom_agent
from app.utils import util as session


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "healthy"}


def _render_history_section(session_id: str) -> str:
    history = session.get_history(session_id)
    if not history:
        return "No previous steps."
    lines = []
    for entry in history[-5:]:
        line = f"[{entry.timestamp.isoformat()}] message: {entry.message}"
        if entry.command:
            line += f" | command: {entry.command}"
        if entry.command_output:
            trimmed = entry.command_output
            if len(trimmed) > 500:
                trimmed = trimmed[:500] + "... (truncated)"
            line += f" | output: {trimmed}"
        lines.append(line)
    return "\n".join(lines)


def _shorten_text(text: str, max_chars: int = 1000) -> str:
    if not text or len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return text[:head] + f"\n... (truncated {len(text) - max_chars} chars) ...\n" + text[-tail:]


def _previous_commands(session_id: str) -> list[str]:
    cmds: list[str] = []
    for entry in session.get_history(session_id):
        if entry.command:
            cmds.append(entry.command)
    return cmds[-10:]


@router.post("/diagnose", response_model=DiagnoseResponse, status_code=status.HTTP_200_OK)
def diagnose(payload: DiagnoseRequest) -> DiagnoseResponse:
    # Resolve session
    session_id = session.get_or_create_session(payload.session_id)

    # Prepare sections
    history_section = _render_history_section(session_id)
    short_co = _shorten_text(payload.command_output, 1000) if payload.command_output else None
    command_output_section = (
        f"Latest command output provided by user (may be empty):\n{short_co}"
        if short_co
        else "No command output provided yet."
    )

    # Build system prompt
    system_prompt = intent_prompt.format(
        problem=payload.problem,
        history_section=history_section,
        command_output_section=command_output_section,
    )
    prev_cmds = _previous_commands(session_id)
    if prev_cmds:
        system_prompt += "\n\nPreviously suggested commands (do not repeat unless new output requires it):\n- " + "\n- ".join(prev_cmds)

    # Call the agent with structured output
    try:
        ai_output: DiagnosisOutput = custom_agent(
            system_prompt=system_prompt,
            user_query=payload.problem,
            response_model=DiagnosisOutput,
        )
    except Exception as e:
        # Graceful fallback
        ai_output = DiagnosisOutput(
            message=(
                "I couldn't generate a structured response right now. "
                "Please try again or provide recent command output (e.g., 'top -l 1 && df -h')."
            ),
            command="",
            next_step="message",
        )

    # If model repeats a previous command without new output, stop the loop and ask user to run it
    if ai_output.next_step == "command" and ai_output.command and ai_output.command in prev_cmds and not payload.command_output:
        ai_output = DiagnosisOutput(
            message=(
                f"You still need to run the previously suggested command and share its output: {prev_cmds[-1]}"
            ),
            command="",
            next_step="message",
        )

    # Persist interaction
    # 1) User problem
    session.append_history(
        session_id=session_id,
        message=f"User: {payload.problem}",
        command=None,
        command_output=short_co,
    )
    # 2) AI response
    session.append_history(
        session_id=session_id,
        message=f"Assistant: {ai_output.message}",
        command=ai_output.command,
        command_output=None,
    )

    return DiagnoseResponse(
        message=ai_output.message,
        command=ai_output.command or None,
        next_step=ai_output.next_step,
        session_id=session_id,
        history=session.get_history(session_id),
    )

