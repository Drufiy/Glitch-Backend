from fastapi import APIRouter, HTTPException, Depends
from fastapi import status
from typing import Optional, Dict
import subprocess
import os

from app.agent.prompts import sys_info_prompt
from app.agent.schema import DiagnoseRequest, DiagnoseResponse, DiagnosisOutput
from app.agent.agents import custom_agent
from app.database.thread_service import ThreadService
from app.routes.auth import get_current_user


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "healthy"}


def _render_history_section(thread_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
    """Get history from thread or fallback to session"""
    history = []
    if thread_id:
        history = ThreadService.get_messages(thread_id, limit=5)
    elif session_id:
        history = session.get_history(session_id)
    
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


def _previous_commands(thread_id: Optional[str] = None, session_id: Optional[str] = None) -> list[str]:
    """Get previous commands from thread or fallback to session"""
    history = []
    if thread_id:
        history = ThreadService.get_messages(thread_id, limit=10)
    elif session_id:
        history = session.get_history(session_id)
    
    cmds: list[str] = []
    for entry in history:
        if entry.command:
            cmds.append(entry.command)
    return cmds[-10:]


def _last_command(thread_id: Optional[str] = None, session_id: Optional[str] = None) -> Optional[str]:
    """Get last command from thread or fallback to session"""
    history = []
    if thread_id:
        history = ThreadService.get_messages(thread_id, limit=10)
    elif session_id:
        history = session.get_history(session_id)
    
    for entry in reversed(history):
        if entry.command:
            return entry.command
    return None


def _execute_powershell_command(command: str) -> dict:
    """
    Execute a PowerShell command safely and return the result.
    
    Args:
        command: PowerShell command to execute
        
    Returns:
        dict with 'success', 'output', and 'error' keys
    """
    try:
        # Sanitize command - only allow PowerShell commands
        if not command.strip():
            return {"success": False, "output": "", "error": "Empty command"}
        
        # Use PowerShell to execute the command
        # -NoProfile: Skip profile loading for faster startup
        # -Command: Execute the command
        # -ErrorAction Stop: Make errors catchable
        ps_command = f'powershell.exe -NoProfile -Command "{command}"'
        
        print(f"[EXEC] PowerShell command: {command}")
        result = subprocess.run(
            ps_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""
        
        if result.returncode == 0:
            print(f"[SUCCESS] Command executed successfully")
            return {"success": True, "output": output, "error": error}
        else:
            print(f"[ERROR] Command failed (exit code: {result.returncode})")
            # Combine stdout and stderr for failed commands
            combined_output = f"{output}\n{error}".strip() if error else output
            return {"success": False, "output": combined_output, "error": error or "Command failed"}
            
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Command timed out after 30 seconds")
        return {"success": False, "output": "", "error": "Command timed out after 30 seconds"}
    except Exception as e:
        print(f"[ERROR] Failed to execute command: {e}")
        return {"success": False, "output": "", "error": str(e)}


@router.post("/diagnose", response_model=DiagnoseResponse, status_code=status.HTTP_200_OK)
def diagnose(payload: DiagnoseRequest, current_user: Dict = Depends(get_current_user)) -> DiagnoseResponse:
    # Resolve thread for authenticated user
    thread_id = payload.thread_id
    user_id = current_user.get("id")

    # If thread_id is provided, verify ownership or create if missing
    if thread_id:
        thread = ThreadService.get_thread(thread_id)
        if not thread:
            # Create a new thread owned by the user if it doesn't exist
            thread_id = ThreadService.create_thread(user_id=user_id, title=payload.problem[:50])
            print(f"[THREAD] Created new thread: {thread_id}")
        else:
            # Enforce ownership
            if thread.get("user_id") != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this thread")
        print(f"[THREAD] Using thread: {thread_id}")
    else:
        # Create a new thread for this user
        thread_id = ThreadService.create_thread(user_id=user_id, title=payload.problem[:50])
        print(f"[THREAD] Created new thread: {thread_id}")

    # Persist the current user input BEFORE building the prompt so the agent sees it in history
    if payload.command_output:
        last_cmd = _last_command(thread_id=thread_id)
        ThreadService.add_message(
            thread_id=thread_id,
            role="user",
            message=f"User: output for '{last_cmd}'" if last_cmd else "User: command output",
            command_output=payload.command_output,
            user_id=user_id,
        )
    else:
        ThreadService.add_message(
            thread_id=thread_id,
            role="user",
            message=payload.problem,
            user_id=user_id,
        )

    # Prepare sections
    history_section = _render_history_section(thread_id=thread_id)
    command_output_section = (
        f"Latest command output provided by user (may be empty):\n{payload.command_output}"
        if payload.command_output
        else "No command output provided yet."
    )

    # Build system prompt
    system_prompt = sys_info_prompt.format(
        problem=payload.problem,
        history_section=history_section,
        command_output_section=command_output_section,
    )
    # with open("system_prompt.txt", "w",encoding="utf-8") as f:
    #     f.write(system_prompt)
    prev_cmds = _previous_commands(thread_id=thread_id)
    # if prev_cmds:
    #     system_prompt += "\n\nPreviously suggested commands (do not repeat unless new output requires it):\n- " + "\n- ".join(prev_cmds)

    # Call the agent with structured output
    try:
        ai_output: DiagnosisOutput = custom_agent(
            system_prompt=system_prompt,
            user_query=payload.problem,
            response_model=DiagnosisOutput,
        )
        print(f"[AI] Output: {ai_output}")
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] custom_agent error: {e}")
        print(f"[TRACEBACK]\n{error_details}")
        # Graceful fallback with better error message
        ai_output = DiagnosisOutput(
            message=(
                f"I encountered an error processing your request: {str(e)[:200]}. "
                "Please try again or rephrase your request."
            ),
            command="",
            next_step="message",
        )
        

    # # If model repeats a previous command without new output, stop the loop and ask user to run it
    # if ai_output.next_step == "command" and ai_output.command and ai_output.command in prev_cmds and not payload.command_output:
    #     ai_output = DiagnosisOutput(
    #         message=(
    #             f"You still need to run the previously suggested command and share its output: {prev_cmds[-1]}"
    #         ),
    #         command="",
    #         next_step="message",
    #     )
    # Auto-execute command if AI suggests one and no command_output was provided
    command_output = None
    if ai_output.next_step == "command" and ai_output.command and not payload.command_output:
        print(f"[AUTO-EXEC] Command: {ai_output.command}")
        exec_result = _execute_powershell_command(ai_output.command)
        command_output = exec_result.get("output", "")
        if exec_result.get("error"):
            command_output += f"\n[Error]: {exec_result['error']}"
        
        # Store the command execution result
        ThreadService.add_message(
            thread_id=thread_id,
            role="assistant",
            message=ai_output.message,
            command=ai_output.command,
            command_output=command_output,
            user_id=user_id,
        )
        
        # If command executed, update the message to include results
        if exec_result.get("success"):
            ai_output.message += f"\n\n[SUCCESS] Command executed. Output:\n{command_output[:500]}"  # Limit output length
        else:
            ai_output.message += f"\n\n[ERROR] Command failed. Error: {exec_result.get('error', 'Unknown error')}"
    else:
        # Persist AI response without execution
        ThreadService.add_message(
            thread_id=thread_id,
            role="assistant",
            message=ai_output.message,
            command=ai_output.command,
            command_output=command_output,
            user_id=user_id,
        )

    # Get history for response
    history = ThreadService.get_messages(thread_id, limit=100)
    response_session_id = thread_id

    return DiagnoseResponse(
        message=ai_output.message,
        command=ai_output.command or None,
        next_step=ai_output.next_step,
        session_id=response_session_id,  # For backward compatibility
        thread_id=thread_id,
        history=history,
    )

