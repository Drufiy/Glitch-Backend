"""
Thread and message management service using Supabase
"""
from typing import List, Optional, Dict
from datetime import datetime
from uuid import uuid4
import json

from app.database.supabase_client import supabase, is_supabase_available
from app.services.embeddings import generate_embedding
from app.agent.schema import HistoryEntry


class ThreadService:
    """Service for managing chat threads and messages"""

    @staticmethod
    def create_thread(user_id: Optional[str] = None, title: Optional[str] = None) -> str:
        thread_id = str(uuid4())

        data = {
            "id": thread_id,
            "user_id": user_id,
            "title": title or "New Chat",
        }

        if not is_supabase_available():
            print(f"[THREAD] Created thread (in-memory): {thread_id}")
            return thread_id

        try:
            supabase.table("threads").insert(data).execute()
            return thread_id
        except Exception as e:
            print(f"[ERROR] Failed to create thread: {e}")
            return thread_id

    @staticmethod
    def get_thread(thread_id: str) -> Optional[Dict]:
        if not is_supabase_available():
            return {
                "id": thread_id,
                "title": "Thread",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

        try:
            result = supabase.table("threads").select("*").eq("id", thread_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get thread: {e}")
            return None

    @staticmethod
    def list_threads(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        if not is_supabase_available():
            return []

        try:
            query = supabase.table("threads").select("*").order("updated_at", desc=True).limit(limit)
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"[ERROR] Failed to list threads: {e}")
            return []

    @staticmethod
    def delete_thread(thread_id: str) -> bool:
        """Delete a thread and its messages"""
        if not is_supabase_available():
            print(f"[THREAD] Deleted thread (in-memory): {thread_id}")
            return True

        try:
            supabase.table("messages").delete().eq("thread_id", thread_id).execute()
            supabase.table("threads").delete().eq("id", thread_id).execute()
            print(f"[THREAD] Deleted thread: {thread_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete thread: {e}")
            return False

    @staticmethod
    def add_message(
        thread_id: str,
        role: str,
        message: str,
        command: Optional[str] = None,
        command_output: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        message_id = str(uuid4())

        embed_text = message
        if command:
            embed_text += f" {command}"
        if command_output:
            embed_text += f" {command_output}"

        embedding = generate_embedding(embed_text)

        msg_data = {
            "id": message_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": role,
            "content": message,
            "command": command,
            "command_output": command_output,
        }

        emb_data = {
            "id": str(uuid4()),
            "message_id": message_id,
            "thread_id": thread_id,
            "embedding": embedding,
        }

        if not is_supabase_available():
            print(f"[MESSAGE] Added message (in-memory): {message_id} to thread {thread_id}")
            return message_id

        try:
            supabase.table("messages").insert(msg_data).execute()
            supabase.table("message_embeddings").insert(emb_data).execute()
            return message_id
        except Exception as e:
            print(f"[ERROR] Failed to add message: {e}")
            return message_id

    @staticmethod
    def get_messages(thread_id: str, limit: int = 100) -> List[HistoryEntry]:
        if not is_supabase_available():
            return []

        try:
            res = supabase.table("messages") \
                .select("*") \
                .eq("thread_id", thread_id) \
                .order("created_at", desc=False) \
                .limit(limit).execute()

            entries = []
            for msg in res.data or []:
                try:
                    timestamp = datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00"))
                except Exception:
                    timestamp = datetime.utcnow()

                prefix = "User" if msg["role"] == "user" else "Assistant"
                full_msg = f"{prefix}: {msg['content']}"

                entries.append(
                    HistoryEntry(
                        timestamp=timestamp,
                        message=full_msg,
                        command=msg.get("command"),
                        command_output=msg.get("command_output"),
                    )
                )

            return entries
        except Exception as e:
            print(f"[ERROR] Failed to get messages: {e}")
            return []
