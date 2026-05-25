# -*- coding: utf-8 -*-
"""
Session Token Store — per-session user credential storage.

Tokens are stored in-memory only (never persisted to disk or logs).
Each entry is keyed by (conversation_id, token_key) and has a TTL.

Design principles:
  - Zero disk footprint  → tokens never touch disk
  - TTL-based expiry     → stale sessions auto-cleaned
  - Thread-safe          → asyncio + threading lock
  - Placeholder resolution → {{session.user_token}} in auth_config
"""

import logging
import re
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{\{session\.(\w+)\}\}")

_DEFAULT_TTL = 3600        # 1 hour
_CLEANUP_INTERVAL = 300    # clean expired entries every 5 min


class SessionTokenStore:
    """
    Thread-safe in-memory store for user tokens, keyed by (conversation_id, token_key).

    Typical token_key values:
      - "user_token"  : the main Bearer / JWT token
      - "refresh_token": OAuth2 refresh token
      - "user_phone"  : phone number after OTP step 1
    """

    def __init__(self, default_ttl: int = _DEFAULT_TTL):
        self._store: Dict[str, Dict[str, tuple[float, str]]] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    # ── Public API ──────────────────────────────────────────────

    def set(
        self,
        session_id: str,
        token_key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> None:
        """Store *value* under *token_key* for *session_id* with TTL seconds."""
        if not session_id or not token_key or not value:
            return
        expiry = time.time() + (ttl or self._default_ttl)
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = {}
            self._store[session_id][token_key] = (expiry, value)
        self._maybe_cleanup()
        logger.debug(f"[SessionTokenStore] SET {token_key} for session {session_id[:8]}…")

    def get(self, session_id: str, token_key: str) -> Optional[str]:
        """Return stored value or None if missing / expired."""
        with self._lock:
            session = self._store.get(session_id, {})
            entry = session.get(token_key)
            if not entry:
                return None
            expiry, value = entry
            if time.time() > expiry:
                del session[token_key]
                return None
            return value

    def get_all(self, session_id: str) -> Dict[str, str]:
        """Return all non-expired values for a session."""
        now = time.time()
        result: Dict[str, str] = {}
        with self._lock:
            for key, (expiry, val) in list(self._store.get(session_id, {}).items()):
                if now <= expiry:
                    result[key] = val
        return result

    def clear_session(self, session_id: str) -> None:
        """Remove all tokens for a session (e.g. on logout or session end)."""
        with self._lock:
            self._store.pop(session_id, None)
        logger.info(f"[SessionTokenStore] Cleared session {session_id[:8]}…")

    def resolve_placeholders(self, template: str, session_id: str) -> str:
        """
        Replace ``{{session.key}}`` placeholders in *template* with stored values.

        Example:
            template  = "Bearer {{session.user_token}}"
            session   has user_token = "eyJhbGc..."
            → returns "Bearer eyJhbGc..."

        Unresolved placeholders are left unchanged.
        """
        if "{{session." not in template:
            return template

        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            val = self.get(session_id, key)
            if val is None:
                logger.warning(
                    f"[SessionTokenStore] Placeholder {{{{session.{key}}}}} "
                    f"not found for session {session_id[:8]}…"
                )
                return match.group(0)
            return val

        return _PLACEHOLDER_RE.sub(_replacer, template)

    def resolve_auth_config(
        self, auth_config: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """
        Return a *copy* of auth_config with all ``{{session.*}}`` placeholders resolved.
        The original dict is never mutated.
        """
        if not session_id or not auth_config:
            return auth_config

        resolved: Dict[str, Any] = {}
        for k, v in auth_config.items():
            if isinstance(v, str):
                resolved[k] = self.resolve_placeholders(v, session_id)
            else:
                resolved[k] = v
        return resolved

    # ── Internal ────────────────────────────────────────────────

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < _CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        removed_sessions = 0
        removed_keys = 0
        with self._lock:
            for sid in list(self._store.keys()):
                session = self._store[sid]
                expired_keys = [k for k, (exp, _) in session.items() if now > exp]
                for k in expired_keys:
                    del session[k]
                    removed_keys += 1
                if not session:
                    del self._store[sid]
                    removed_sessions += 1
        if removed_keys:
            logger.debug(
                f"[SessionTokenStore] Cleanup: removed {removed_keys} keys "
                f"across {removed_sessions} sessions"
            )


# ── Module-level singleton ───────────────────────────────────────
_store_instance: Optional[SessionTokenStore] = None


def get_session_token_store() -> SessionTokenStore:
    """Return the module-level singleton SessionTokenStore."""
    global _store_instance
    if _store_instance is None:
        _store_instance = SessionTokenStore()
    return _store_instance
