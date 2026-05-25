# -*- coding: utf-8 -*-
"""
Persistent Conversation Memory — SQLite-backed + in-memory LRU cache.

Drop-in replacement for the simple ``chat_histories`` dict.  Provides:
  - Persistence across server restarts (SQLite)
  - Fast reads via in-memory LRU cache
  - Conversation summarization (via LLM)
  - Lightweight entity extraction per turn (regex, no embeddings)
  - TTL / LRU eviction identical to the old in-memory store

The public API is intentionally identical to the five methods that
``UltimateRAGSystem`` already exposes so wiring is a one-line swap.
"""

import json
import logging
import os
import re
import sqlite3
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "conversation_memory.db"
_MAX_CONVERSATIONS = 5000
_TTL_SECONDS = 7200  # 2 hours
_MAX_MESSAGES_PER_KEY = 20
_SUMMARY_TRIGGER = 12  # summarize when messages exceed this


# ─────────────────────────────────────────────────────────────
# Entity extraction (lightweight, no model needed)
# ─────────────────────────────────────────────────────────────

_ENTITY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("order_id", re.compile(r"\b(?:ORD|سفارش)[- ]?(\d{3,})\b", re.IGNORECASE)),
    ("phone", re.compile(r"\b09\d{9}\b")),
    ("tracking", re.compile(r"\b(?:PTT|پست)[- ]?(\d{6,})\b", re.IGNORECASE)),
    ("amount", re.compile(r"\b(\d[\d,]{2,})\s*(?:تومان|ریال|تومن)\b")),
    ("product_code", re.compile(r"\b(?:SKU|کد)[- ]?([A-Za-z0-9]{3,})\b", re.IGNORECASE)),
    ("year", re.compile(r"\b(1[34]\d{2})\b")),
]


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities from Persian/mixed text using regex."""
    entities: Dict[str, List[str]] = {}
    for etype, pattern in _ENTITY_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            entities[etype] = list(set(matches))
    return entities


# ─────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────

@dataclass
class ConversationMessage:
    user: str
    assistant: str
    timestamp: float
    entities: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ConversationEntry:
    key: str
    messages: List[ConversationMessage]
    last_access: float
    summary: str = ""
    session_entities: Dict[str, List[str]] = field(default_factory=dict)

    def to_legacy_list(self, max_messages: int = 5) -> List[Dict[str, str]]:
        """Return the format that build_context_prompt expects."""
        result: List[Dict[str, str]] = []
        for m in self.messages[-max_messages:]:
            result.append({
                "user": m.user,
                "assistant": m.assistant,
                "timestamp": m.timestamp,
            })
        return result


# ─────────────────────────────────────────────────────────────
# SQLite persistence layer
# ─────────────────────────────────────────────────────────────

class _SQLiteBackend:
    """Thread-safe SQLite backend.  One DB file for all conversations."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema(self._get_conn())

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path), timeout=5)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    @staticmethod
    def _init_schema(conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                key         TEXT PRIMARY KEY,
                messages    TEXT NOT NULL DEFAULT '[]',
                summary     TEXT NOT NULL DEFAULT '',
                entities    TEXT NOT NULL DEFAULT '{}',
                last_access REAL NOT NULL,
                created_at  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_last_access
                ON conversations(last_access);
        """)
        conn.commit()

    def load(self, key: str) -> Optional[ConversationEntry]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT messages, summary, entities, last_access FROM conversations WHERE key=?",
            (key,),
        ).fetchone()
        if not row:
            return None
        raw_msgs = json.loads(row[0])
        messages = [
            ConversationMessage(
                user=m["user"],
                assistant=m["assistant"],
                timestamp=m.get("timestamp", 0),
                entities=m.get("entities", {}),
            )
            for m in raw_msgs
        ]
        return ConversationEntry(
            key=key,
            messages=messages,
            last_access=row[3],
            summary=row[1],
            session_entities=json.loads(row[2]),
        )

    def save(self, entry: ConversationEntry):
        conn = self._get_conn()
        msgs_json = json.dumps(
            [{"user": m.user, "assistant": m.assistant, "timestamp": m.timestamp, "entities": m.entities} for m in entry.messages],
            ensure_ascii=False,
        )
        conn.execute(
            """INSERT INTO conversations (key, messages, summary, entities, last_access, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   messages=excluded.messages,
                   summary=excluded.summary,
                   entities=excluded.entities,
                   last_access=excluded.last_access""",
            (entry.key, msgs_json, entry.summary, json.dumps(entry.session_entities, ensure_ascii=False), entry.last_access, time.time()),
        )
        conn.commit()

    def delete(self, key: str):
        conn = self._get_conn()
        conn.execute("DELETE FROM conversations WHERE key=?", (key,))
        conn.commit()

    def evict_expired(self, ttl: float, max_count: int):
        conn = self._get_conn()
        cutoff = time.time() - ttl
        conn.execute("DELETE FROM conversations WHERE last_access < ?", (cutoff,))
        count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        if count > max_count:
            excess = count - max_count
            conn.execute(
                "DELETE FROM conversations WHERE key IN (SELECT key FROM conversations ORDER BY last_access ASC LIMIT ?)",
                (excess,),
            )
        conn.commit()


# ─────────────────────────────────────────────────────────────
# Main public class
# ─────────────────────────────────────────────────────────────

class ConversationStore:
    """
    Drop-in replacement for the five ``chat_history`` methods in
    ``UltimateRAGSystem``.  Backed by SQLite + LRU in-memory cache.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        qwen_client=None,
        max_conversations: int = _MAX_CONVERSATIONS,
        ttl_seconds: int = _TTL_SECONDS,
    ):
        self._db = _SQLiteBackend(db_path or _DEFAULT_DB_PATH)
        self._cache: Dict[str, ConversationEntry] = {}
        self._max = max_conversations
        self._ttl = ttl_seconds
        self._qwen_client = qwen_client
        self._evict_counter = 0
        logger.info(f"ConversationStore initialized (db={self._db._db_path})")

    # ── key helpers ──

    @staticmethod
    def make_key(collection_name: str, conversation_id: Optional[str] = None) -> str:
        base = collection_name or "default"
        if conversation_id:
            return f"{base}::session::{conversation_id}"
        return base

    # ── core CRUD (public API identical to old methods) ──

    def add(
        self,
        collection_name: str,
        user_query: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
    ):
        """add_to_chat_history replacement."""
        key = self.make_key(collection_name, conversation_id)
        entry = self._get_or_create(key)
        entities = extract_entities(user_query + " " + assistant_response)
        entry.messages.append(ConversationMessage(
            user=user_query,
            assistant=assistant_response,
            timestamp=time.time(),
            entities=entities,
        ))
        _merge_entities(entry.session_entities, entities)
        if len(entry.messages) > _MAX_MESSAGES_PER_KEY:
            entry.messages = entry.messages[-_MAX_MESSAGES_PER_KEY:]
        entry.last_access = time.time()
        self._put(key, entry)

    def update_last_assistant(
        self,
        collection_name: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
    ):
        """update_last_assistant_message replacement."""
        key = self.make_key(collection_name, conversation_id)
        entry = self._get(key)
        if entry and entry.messages:
            entry.messages[-1].assistant = assistant_response
            new_entities = extract_entities(assistant_response)
            entry.messages[-1].entities.update(new_entities)
            _merge_entities(entry.session_entities, new_entities)
            entry.last_access = time.time()
            self._put(key, entry)

    def get(
        self,
        collection_name: str,
        max_messages: int = 5,
        conversation_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """get_chat_history replacement.  Returns the legacy list format."""
        key = self.make_key(collection_name, conversation_id)
        entry = self._get(key)
        if not entry:
            return []
        entry.last_access = time.time()
        return entry.to_legacy_list(max_messages)

    def clear(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ):
        """clear_chat_history replacement."""
        key = self.make_key(collection_name, conversation_id)
        self._cache.pop(key, None)
        self._db.delete(key)

    # ── entity memory ──

    def get_session_entities(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """Return all entities mentioned so far in this session."""
        key = self.make_key(collection_name, conversation_id)
        entry = self._get(key)
        if not entry:
            return {}
        return dict(entry.session_entities)

    # ── summarization ──

    async def maybe_summarize(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ) -> Optional[str]:
        """Summarize the conversation if it exceeds the trigger threshold.
        Returns the summary string, or None if no summarization was needed."""
        if not self._qwen_client:
            return None
        key = self.make_key(collection_name, conversation_id)
        entry = self._get(key)
        if not entry or len(entry.messages) < _SUMMARY_TRIGGER:
            return None
        if entry.summary and len(entry.messages) < _SUMMARY_TRIGGER + 4:
            return entry.summary

        history_text = _format_for_summary(entry.messages[:-3])
        prompt = (
            "خلاصه‌ای فارسی از گفتگوی زیر بنویس. فقط نکات کلیدی، entities، و تصمیمات مهم را بنویس. "
            "خلاصه باید حداکثر ۴ خط باشد.\n\n"
            f"{history_text}"
        )
        try:
            resp = await self._qwen_client.generate_text(
                prompt=prompt,
                max_tokens=256,
                temperature=0.2,
            )
            if resp.success and resp.text:
                entry.summary = resp.text.strip()
                self._put(key, entry)
                logger.info(f"[ConversationStore] Summarized {len(entry.messages)} messages for {key}")
                return entry.summary
        except Exception as e:
            logger.warning(f"[ConversationStore] Summarization failed: {e}")
        return None

    def get_summary(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ) -> str:
        key = self.make_key(collection_name, conversation_id)
        entry = self._get(key)
        return entry.summary if entry else ""

    # ── internal ──

    def _get_or_create(self, key: str) -> ConversationEntry:
        entry = self._get(key)
        if entry:
            return entry
        entry = ConversationEntry(key=key, messages=[], last_access=time.time())
        return entry

    def _get(self, key: str) -> Optional[ConversationEntry]:
        if key in self._cache:
            return self._cache[key]
        entry = self._db.load(key)
        if entry:
            self._cache[key] = entry
        return entry

    def _put(self, key: str, entry: ConversationEntry):
        self._cache[key] = entry
        self._db.save(entry)
        self._evict_counter += 1
        if self._evict_counter % 50 == 0:
            self._evict()

    def _evict(self):
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v.last_access > self._ttl]
        for k in expired:
            del self._cache[k]
        if len(self._cache) > self._max:
            sorted_keys = sorted(self._cache, key=lambda k: self._cache[k].last_access)
            for k in sorted_keys[: len(self._cache) - self._max]:
                del self._cache[k]
        self._db.evict_expired(self._ttl, self._max)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _merge_entities(target: Dict[str, List[str]], source: Dict[str, List[str]]):
    for etype, values in source.items():
        existing = set(target.get(etype, []))
        existing.update(values)
        target[etype] = list(existing)


def _format_for_summary(messages: List[ConversationMessage]) -> str:
    parts: List[str] = []
    for m in messages:
        parts.append(f"کاربر: {m.user}")
        if m.assistant:
            resp = m.assistant[:300] + "..." if len(m.assistant) > 300 else m.assistant
            parts.append(f"دستیار: {resp}")
    return "\n".join(parts)
