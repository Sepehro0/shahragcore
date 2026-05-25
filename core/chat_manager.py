# -*- coding: utf-8 -*-
"""
Chat Manager Module
مدیریت chat history و conversation sessions
"""

import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ChatManager:
    """مدیریت chat history"""
    
    def __init__(self):
        """Initialize chat manager"""
        self.chat_histories: Dict[str, List[Dict[str, str]]] = {}
        self.chat_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _get_chat_key(self, collection_name: str, conversation_id: Optional[str]) -> str:
        """Generate chat key"""
        base = collection_name or "default"
        if conversation_id:
            return f"{base}::session::{conversation_id}"
        return base
    
    def add_to_chat_history(
        self,
        collection_name: str,
        user_query: str,
        assistant_response: str,
        conversation_id: Optional[str] = None
    ):
        """اضافه کردن به تاریخچه چت"""
        key = self._get_chat_key(collection_name, conversation_id)
        if key not in self.chat_histories:
            self.chat_histories[key] = []
        
        self.chat_histories[key].append({
            "user": user_query,
            "assistant": assistant_response,
            "timestamp": time.time()
        })
        
        # Keep only last 10 messages
        if len(self.chat_histories[key]) > 10:
            self.chat_histories[key] = self.chat_histories[key][-10:]
    
    def update_last_assistant_message(
        self,
        collection_name: str,
        assistant_response: str,
        conversation_id: Optional[str] = None
    ):
        """به‌روزرسانی آخرین پیام assistant"""
        key = self._get_chat_key(collection_name, conversation_id)
        history = self.chat_histories.get(key)
        if history and isinstance(history, list) and len(history) > 0:
            history[-1]["assistant"] = assistant_response
    
    def get_chat_history(
        self,
        collection_name: str,
        max_messages: int = 5,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """دریافت تاریخچه چت"""
        key = self._get_chat_key(collection_name, conversation_id)
        history = self.chat_histories.get(key, [])
        return history[-max_messages:]
    
    def clear_chat_history(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None
    ):
        """پاک کردن تاریخچه چت"""
        key = self._get_chat_key(collection_name, conversation_id)
        if key in self.chat_histories:
            self.chat_histories[key] = []

