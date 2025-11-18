"""
Thread and message management service using Supabase
"""
from typing import List, Optional, Dict
from datetime import datetime
from uuid import uuid4
import json

from app.database.supabase_client import supabase, is_supabase_available
from app.services.embeddings import generate_embedding, get_embedding_dimension
from app.agent.schema import HistoryEntry


class ThreadService:
    """Service for managing chat threads and messages"""
    
    @staticmethod
    def create_thread(user_id: Optional[str] = None, title: Optional[str] = None) -> str:
        """
        Create a new thread.
        
        Args:
            user_id: Optional user ID (for future user authentication)
            title: Optional thread title
            
        Returns:
            thread_id: UUID of the created thread
        """
        thread_id = str(uuid4())
        
        # Create thread in Supabase
        # Supabase will handle timestamps automatically, so we don't need to set them
        thread_data = {
            "id": thread_id,
            "user_id": user_id,
            "title": title or "New Chat",
        }
        
        if not is_supabase_available():
            print(f"[THREAD] Created thread (in-memory): {thread_id}")
            return thread_id
        
        try:
            result = supabase.table("threads").insert(thread_data).execute()
            print(f"[THREAD] Created thread: {thread_id}")
            return thread_id
        except Exception as e:
            print(f"[ERROR] Failed to create thread: {e}")
            # If Supabase fails, still return thread_id for in-memory fallback
            return thread_id
    
    @staticmethod
    def get_thread(thread_id: str) -> Optional[Dict]:
        """Get thread by ID"""
        if not is_supabase_available():
            # Return a basic thread structure for in-memory mode
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
        """
        List all threads, optionally filtered by user_id.
        
        Args:
            user_id: Optional user ID to filter threads
            limit: Maximum number of threads to return
            
        Returns:
            List of thread dictionaries
        """
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
        """Delete a thread and all its messages"""
        if not is_supabase_available():
            print(f"[THREAD] Deleted thread (in-memory): {thread_id}")
            return True
        
        try:
            # Delete messages first (cascade should handle this, but being explicit)
            supabase.table("messages").delete().eq("thread_id", thread_id).execute()
            # Delete thread
            supabase.table("threads").delete().eq("id", thread_id).execute()
            print(f"[THREAD] Deleted thread: {thread_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete thread: {e}")
            return False
    
    @staticmethod
    def add_message(
        thread_id: str,
        role: str,  # "user" or "assistant"
        message: str,
        command: Optional[str] = None,
        command_output: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Add a message to a thread and generate/store its embedding.
        
        Args:
            thread_id: Thread ID
            role: Message role ("user" or "assistant")
            message: Message content
            command: Optional command associated with the message
            command_output: Optional command output
            user_id: Optional user ID
            
        Returns:
            message_id: UUID of the created message
        """
        message_id = str(uuid4())
        
        # Generate embedding for the message
        embedding_text = f"{message}"
        if command:
            embedding_text += f" {command}"
        if command_output:
            embedding_text += f" {command_output}"
        
        embedding = generate_embedding(embedding_text)
        
        # Prepare message data
        # Supabase will handle created_at automatically
        message_data = {
            "id": message_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": role,
            "content": message,
            "command": command,
            "command_output": command_output,
        }
        
        # Prepare embedding data
        embedding_data = {
            "id": str(uuid4()),
            "message_id": message_id,
            "thread_id": thread_id,
            "embedding": embedding,
        }
        
        if not is_supabase_available():
            print(f"[MESSAGE] Added message (in-memory): {message_id} to thread {thread_id}")
            return message_id
        
        try:
            # Insert message
            supabase.table("messages").insert(message_data).execute()
            
            # Insert embedding
            supabase.table("message_embeddings").insert(embedding_data).execute()
            
            # Update thread's updated_at timestamp (Supabase trigger handles this, but we can force it)
            # The trigger will automatically update updated_at when messages are inserted
            
            print(f"[MESSAGE] Added message {message_id} to thread {thread_id}")
            return message_id
        except Exception as e:
            print(f"[ERROR] Failed to add message: {e}")
            # If Supabase fails, still return message_id
            return message_id
    
    @staticmethod
    def get_messages(thread_id: str, limit: int = 100) -> List[HistoryEntry]:
        """
        Get all messages for a thread as HistoryEntry objects.
        
        Args:
            thread_id: Thread ID
            limit: Maximum number of messages to return
            
        Returns:
            List of HistoryEntry objects
        """
        if not is_supabase_available():
            return []
        
        try:
            result = supabase.table("messages").select("*").eq("thread_id", thread_id).order("created_at", desc=False).limit(limit).execute()
            
            messages = []
            for msg in (result.data or []):
                # Format message for HistoryEntry
                if msg["role"] == "user":
                    message_text = f"User: {msg['content']}"
                else:
                    message_text = f"Assistant: {msg['content']}"
                
                # Parse timestamp from Supabase (handles both with and without timezone)
                try:
                    if "T" in msg["created_at"]:
                        # ISO format with timezone
                        timestamp_str = msg["created_at"].replace("Z", "+00:00")
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        # Fallback to current time if parsing fails
                        timestamp = datetime.utcnow()
                except:
                    timestamp = datetime.utcnow()
                
                entry = HistoryEntry(
                    timestamp=timestamp,
                    message=message_text,
                    command=msg.get("command"),
                    command_output=msg.get("command_output"),
                )
                messages.append(entry)
            
            return messages
        except Exception as e:
            print(f"[ERROR] Failed to get messages: {e}")
            return []
    
    @staticmethod
    def search_similar_messages(
        thread_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Search for similar messages in a thread using vector similarity.
        
        Args:
            thread_id: Thread ID
            query: Search query text
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of similar messages with similarity scores
        """
        try:
            # Generate embedding for query
            query_embedding = generate_embedding(query)
            
            # Use Supabase vector similarity search
            # Note: This requires pgvector extension and proper indexing
            result = supabase.rpc(
                "match_messages",
                {
                    "query_embedding": query_embedding,
                    "match_thread_id": thread_id,
                    "match_threshold": threshold,
                    "match_count": limit,
                }
            ).execute()
            
            return result.data or []
        except Exception as e:
            print(f"[ERROR] Failed to search similar messages: {e}")
            # Fallback to simple text search
            return []

