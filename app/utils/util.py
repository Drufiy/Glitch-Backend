from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from app.agent.schema import HistoryEntry


# Minimal in-memory history store (simple dict + helpers)
SESSION_HISTORY: Dict[str, List[HistoryEntry]] = {}


def _create_session() -> str:
    session_id = str(uuid4())
    SESSION_HISTORY[session_id] = []
    return session_id


def get_or_create_session(session_id: Optional[str]) -> str:
    if session_id and session_id in SESSION_HISTORY:
        return session_id
    if session_id and session_id not in SESSION_HISTORY:
        SESSION_HISTORY[session_id] = []
        return session_id
    return _create_session()


def append_history(
    session_id: str,
    message: str,
    command: Optional[str] = None,
    command_output: Optional[str] = None,
) -> None:
    history = SESSION_HISTORY.setdefault(session_id, [])
    history.append(
        HistoryEntry(
            timestamp=datetime.utcnow(),
            message=message,
            command=command,
            command_output=command_output,
        )
    )


def get_history(session_id: str) -> List[HistoryEntry]:
    return list(SESSION_HISTORY.get(session_id, []))

