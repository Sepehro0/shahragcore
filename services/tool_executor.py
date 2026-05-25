# -*- coding: utf-8 -*-
"""
Tool Executor — securely call user-defined HTTP API endpoints.

Includes:
  - **Result caching** with configurable TTL (in-memory, keyed by tool+args hash)
  - **Per-collection rate limiting** (sliding-window, configurable max calls/minute)
  - **Audit log** (structured JSON lines, one file per day)
  - Security: timeout, response-size cap, private-IP block
"""

import hashlib
import ipaddress
import json
import logging
import os
import re
import time
import threading
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from services.tool_registry import RegisteredTool
from services.session_token_store import SessionTokenStore

logger = logging.getLogger(__name__)

_MAX_RESPONSE_BYTES = 1_048_576  # 1 MB
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]

_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")

_DEFAULT_AUDIT_DIR = Path(__file__).resolve().parent.parent / "data" / "audit_logs"
_DEFAULT_CACHE_TTL = 120  # 2 minutes
_DEFAULT_RATE_LIMIT = 30  # max calls per minute per collection


def _is_private_host(hostname: str) -> bool:
    """Reject requests to private/loopback IPs."""
    if hostname in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        addr = ipaddress.ip_address(hostname)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        return False


def _build_url(template: str, arguments: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    remaining = dict(arguments)
    used_keys: list[str] = []

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in remaining:
            used_keys.append(key)
            return str(remaining[key])
        return match.group(0)

    resolved = _PATH_PARAM_RE.sub(_replacer, template)
    for k in used_keys:
        remaining.pop(k, None)
    return resolved, remaining


# ─────────────────────────────────────────────────────────────
# Result Cache (in-memory, thread-safe)
# ─────────────────────────────────────────────────────────────

class _ToolResultCache:
    """In-memory TTL cache keyed by ``(tool_name, arguments_hash)``."""

    def __init__(self, default_ttl: int = _DEFAULT_CACHE_TTL, max_entries: int = 500):
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._ttl = default_ttl
        self._max = max_entries
        self._lock = threading.Lock()

    @staticmethod
    def _hash_key(tool_name: str, arguments: Dict[str, Any]) -> str:
        raw = json.dumps({"t": tool_name, "a": arguments}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self._hash_key(tool_name, arguments)
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expiry, data = entry
            if time.time() > expiry:
                del self._store[key]
                return None
            return data

    def put(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any], ttl: Optional[int] = None):
        key = self._hash_key(tool_name, arguments)
        expiry = time.time() + (ttl or self._ttl)
        with self._lock:
            if len(self._store) >= self._max:
                self._evict()
            self._store[key] = (expiry, result)

    def _evict(self):
        now = time.time()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        if len(self._store) >= self._max:
            oldest = sorted(self._store, key=lambda k: self._store[k][0])
            for k in oldest[: len(self._store) - self._max // 2]:
                del self._store[k]


# ─────────────────────────────────────────────────────────────
# Per-collection Rate Limiter (sliding window)
# ─────────────────────────────────────────────────────────────

class _RateLimiter:
    """Sliding-window rate limiter per collection."""

    def __init__(self, default_max_per_minute: int = _DEFAULT_RATE_LIMIT):
        self._default_max = default_max_per_minute
        self._windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._limits: Dict[str, int] = {}
        self._lock = threading.Lock()

    def set_limit(self, collection_name: str, max_per_minute: int):
        self._limits[collection_name] = max_per_minute

    def allow(self, collection_name: str) -> bool:
        limit = self._limits.get(collection_name, self._default_max)
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            window = self._windows[collection_name]
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= limit:
                return False
            window.append(now)
            return True

    def remaining(self, collection_name: str) -> int:
        limit = self._limits.get(collection_name, self._default_max)
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            window = self._windows[collection_name]
            while window and window[0] < cutoff:
                window.popleft()
            return max(0, limit - len(window))


# ─────────────────────────────────────────────────────────────
# Audit Logger (structured JSONL)
# ─────────────────────────────────────────────────────────────

class _AuditLogger:
    """Append-only JSONL audit log for tool calls."""

    def __init__(self, log_dir: Path = _DEFAULT_AUDIT_DIR):
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(
        self,
        collection_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result_success: bool,
        status_code: Optional[int],
        latency_ms: float,
        error: Optional[str] = None,
        conversation_id: Optional[str] = None,
        cached: bool = False,
    ):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "collection": collection_name,
            "tool": tool_name,
            "args_hash": _ToolResultCache._hash_key(tool_name, arguments),
            "success": result_success,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 1),
            "cached": cached,
            "error": error,
            "conversation_id": conversation_id,
        }
        today = datetime.utcnow().strftime("%Y-%m-%d")
        path = self._log_dir / f"tool_audit_{today}.jsonl"
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)


# ─────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────

class ToolExecutor:
    """Execute a registered tool against the external API with caching, rate limiting & audit."""

    def __init__(
        self,
        allow_private: bool = False,
        cache_ttl: int = _DEFAULT_CACHE_TTL,
        rate_limit_per_minute: int = _DEFAULT_RATE_LIMIT,
        audit_dir: Optional[Path] = None,
        session_token_store: Optional[SessionTokenStore] = None,
    ):
        self._allow_private = allow_private
        self._cache = _ToolResultCache(default_ttl=cache_ttl)
        self._rate_limiter = _RateLimiter(default_max_per_minute=rate_limit_per_minute)
        self._audit = _AuditLogger(log_dir=audit_dir or _DEFAULT_AUDIT_DIR)
        self._token_store = session_token_store

    @property
    def rate_limiter(self) -> _RateLimiter:
        return self._rate_limiter

    async def execute(
        self,
        tool_call_id: str,
        function_name: str,
        arguments: Dict[str, Any],
        registered_tool: RegisteredTool,
        collection_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call the external HTTP endpoint described by *registered_tool*
        using the *arguments* produced by the LLM.

        *session_id* is used to resolve ``{{session.*}}`` placeholders in
        auth_config (e.g. ``"token": "{{session.user_token}}"``).

        Returns a dict with ``success``, ``data`` (or ``error``),
        and ``tool_call_id``.
        """
        col = collection_name or getattr(registered_tool, "collection_name", "unknown")
        # Resolve session token placeholders in auth_config BEFORE anything else
        effective_session = session_id or conversation_id
        effective_auth = registered_tool.auth_config
        if effective_session and self._token_store:
            effective_auth = self._token_store.resolve_auth_config(
                registered_tool.auth_config, effective_session
            )

        t0 = time.time()

        # ── 1. Cache check ──
        cached = self._cache.get(function_name, arguments)
        if cached is not None:
            latency = (time.time() - t0) * 1000
            self._audit.log(
                collection_name=col,
                tool_name=function_name,
                arguments=arguments,
                result_success=cached.get("success", False),
                status_code=cached.get("status_code"),
                latency_ms=latency,
                cached=True,
                conversation_id=conversation_id,
            )
            logger.info(f"[ToolExecutor] Cache HIT for {function_name}")
            return {**cached, "tool_call_id": tool_call_id, "_cached": True}

        # ── 2. Rate-limit check ──
        if not self._rate_limiter.allow(col):
            latency = (time.time() - t0) * 1000
            self._audit.log(
                collection_name=col,
                tool_name=function_name,
                arguments=arguments,
                result_success=False,
                status_code=None,
                latency_ms=latency,
                error="rate_limited",
                conversation_id=conversation_id,
            )
            remaining = self._rate_limiter.remaining(col)
            return {
                "tool_call_id": tool_call_id,
                "success": False,
                "error": f"Rate limit exceeded for collection '{col}'. Try again shortly.",
            }

        # ── 3. Auto-refresh token if needed ──
        await self._maybe_refresh_token(registered_tool)

        # ── 4. Build URL & security ──
        url, remaining_args = _build_url(registered_tool.endpoint_url, arguments)
        parsed = urlparse(url)
        if not self._allow_private and _is_private_host(parsed.hostname or ""):
            latency = (time.time() - t0) * 1000
            self._audit.log(
                collection_name=col, tool_name=function_name, arguments=arguments,
                result_success=False, status_code=None, latency_ms=latency,
                error="blocked_private_host", conversation_id=conversation_id,
            )
            return {
                "tool_call_id": tool_call_id,
                "success": False,
                "error": f"Blocked: private/internal host '{parsed.hostname}'",
            }

        headers = dict(registered_tool.headers)
        self._apply_auth(headers, effective_auth)  # use resolved auth

        method = registered_tool.http_method.upper()
        timeout = httpx.Timeout(registered_tool.timeout_seconds, connect=5.0)

        body: Optional[Dict[str, Any]] = None
        params: Optional[Dict[str, Any]] = None
        if method in ("POST", "PUT", "PATCH"):
            if registered_tool.request_body_template:
                body = {**registered_tool.request_body_template, **remaining_args}
            else:
                body = remaining_args
        else:
            params = remaining_args or None

        # ── 4. Execute HTTP call ──
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                resp = await client.request(
                    method, url,
                    headers=headers,
                    params=params,
                    json=body if body else None,
                )

            if len(resp.content) > _MAX_RESPONSE_BYTES:
                latency = (time.time() - t0) * 1000
                result = {"tool_call_id": tool_call_id, "success": False, "error": "Response too large (>1 MB)"}
                self._audit.log(col, function_name, arguments, False, resp.status_code, latency, "response_too_large", conversation_id)
                return result

            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text[:2000]}

            latency = (time.time() - t0) * 1000

            if resp.is_success:
                result = {"tool_call_id": tool_call_id, "success": True, "data": data, "status_code": resp.status_code}
                self._cache.put(function_name, arguments, result)
            else:
                result = {"tool_call_id": tool_call_id, "success": False, "error": f"HTTP {resp.status_code}", "data": data, "status_code": resp.status_code}

            self._audit.log(col, function_name, arguments, resp.is_success, resp.status_code, latency, conversation_id=conversation_id)
            return result

        except httpx.TimeoutException:
            latency = (time.time() - t0) * 1000
            error_msg = f"Timeout after {registered_tool.timeout_seconds}s"
            self._audit.log(col, function_name, arguments, False, None, latency, error_msg, conversation_id)
            return {"tool_call_id": tool_call_id, "success": False, "error": error_msg}

        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.error(f"Tool execution failed ({function_name}): {e}")
            self._audit.log(col, function_name, arguments, False, None, latency, str(e), conversation_id)
            return {"tool_call_id": tool_call_id, "success": False, "error": str(e)}

    @staticmethod
    def _apply_auth(headers: Dict[str, str], auth_config: Dict[str, Any]) -> None:
        auth_type = auth_config.get("type", "")
        if auth_type in ("bearer", "oauth2"):
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
        elif auth_type == "api_key":
            key_name = auth_config.get("header_name", "X-API-Key")
            headers[key_name] = auth_config.get("key", "")
        elif auth_type == "basic":
            import base64
            creds = base64.b64encode(
                f"{auth_config.get('username', '')}:{auth_config.get('password', '')}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

    async def _maybe_refresh_token(self, registered_tool: RegisteredTool) -> None:
        """Auto-refresh OAuth2 token if it has expired."""
        ac = registered_tool.auth_config
        if ac.get("type") not in ("bearer", "oauth2"):
            return
        refresh_url = ac.get("refresh_url")
        if not refresh_url:
            return
        expires_at = ac.get("token_expires_at", 0)
        if expires_at and time.time() < expires_at - 30:
            return

        logger.info(f"[ToolExecutor] Refreshing OAuth2 token for {registered_tool.name}")
        try:
            body = {"grant_type": "refresh_token"}
            if ac.get("refresh_token"):
                body["refresh_token"] = ac["refresh_token"]
            if ac.get("client_id"):
                body["client_id"] = ac["client_id"]
            if ac.get("client_secret"):
                body["client_secret"] = ac["client_secret"]

            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
                resp = await c.post(refresh_url, data=body)
            if resp.is_success:
                data = resp.json()
                ac["token"] = data.get("access_token", ac.get("token", ""))
                if data.get("refresh_token"):
                    ac["refresh_token"] = data["refresh_token"]
                expires_in = data.get("expires_in", 3600)
                ac["token_expires_at"] = time.time() + expires_in
                logger.info(f"[ToolExecutor] Token refreshed, expires in {expires_in}s")
            else:
                logger.warning(f"[ToolExecutor] Token refresh failed: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"[ToolExecutor] Token refresh error: {e}")
