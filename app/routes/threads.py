"""
Thread management routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from app.database.thread_service import ThreadService
from app.agent.schema import HistoryEntry
from app.routes.auth import get_current_user

router = APIRouter()


class ThreadCreate(BaseModel):
    title: Optional[str] = None


class ThreadResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    created_at: str
    updated_at: str


class ThreadListResponse(BaseModel):
    threads: List[ThreadResponse]


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    command: Optional[str] = None
    command_output: Optional[str] = None
    created_at: str


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(thread_data: ThreadCreate, current_user: Dict = Depends(get_current_user)) -> ThreadResponse:
    """Create a new thread for the authenticated user"""
    try:
        user_id = current_user.get("id")
        thread_id = ThreadService.create_thread(
            user_id=user_id,
            title=thread_data.title,
        )
        
        thread = ThreadService.get_thread(thread_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create thread"
            )
        
        return ThreadResponse(
            id=thread["id"],
            user_id=thread.get("user_id"),
            title=thread.get("title", "New Chat"),
            created_at=thread["created_at"],
            updated_at=thread["updated_at"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create thread: {str(e)}"
        )


@router.get("/threads", response_model=ThreadListResponse)
def list_threads(current_user: Dict = Depends(get_current_user), limit: int = 50) -> ThreadListResponse:
    """List threads for the authenticated user"""
    try:
        user_id = current_user.get("id")
        threads = ThreadService.list_threads(user_id=user_id, limit=limit)
        return ThreadListResponse(
            threads=[
                ThreadResponse(
                    id=t["id"],
                    user_id=t.get("user_id"),
                    title=t.get("title", "New Chat"),
                    created_at=t["created_at"],
                    updated_at=t["updated_at"],
                )
                for t in threads
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}"
        )


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(thread_id: str, current_user: Dict = Depends(get_current_user)) -> ThreadResponse:
    """Get a specific thread owned by the authenticated user"""
    thread = ThreadService.get_thread(thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    # Enforce ownership
    if thread.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this thread")

    return ThreadResponse(
        id=thread["id"],
        user_id=thread.get("user_id"),
        title=thread.get("title", "New Chat"),
        created_at=thread["created_at"],
        updated_at=thread["updated_at"],
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: str, current_user: Dict = Depends(get_current_user)):
    """Delete a thread and all its messages if owned by the authenticated user"""
    thread = ThreadService.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this thread")

    success = ThreadService.delete_thread(thread_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete thread"
        )


@router.get("/threads/{thread_id}/messages", response_model=List[HistoryEntry])
def get_thread_messages(thread_id: str, current_user: Dict = Depends(get_current_user), limit: int = 100) -> List[HistoryEntry]:
    """Get all messages for a thread (only if owned by authenticated user)"""
    thread = ThreadService.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view messages for this thread")

    messages = ThreadService.get_messages(thread_id, limit=limit)
    return messages

