# -*- coding: utf-8 -*-
"""
Tool Registry — CRUD storage for user-defined API tools.

Each collection can have zero or more tools.  Tool definitions are
persisted as JSON files under ``collections_config/tools/<collection>.json``.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent / "collections_config" / "tools"


@dataclass
class RegisteredTool:
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    http_method: str
    endpoint_url: str
    auth_config: Dict[str, Any] = field(default_factory=dict)
    trigger_description: str = ""
    collection_name: str = ""
    tenant_id: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    request_body_template: Optional[Dict[str, Any]] = None
    response_jmespath: Optional[str] = None
    timeout_seconds: int = 10
    is_enabled: bool = True
    # ── Auth-tool fields ─────────────────────────────────────────
    # Set is_auth_tool=True on tools whose response contains a login token.
    # After execution, the system extracts the token and stores it in
    # SessionTokenStore so subsequent tools can use {{session.user_token}}.
    is_auth_tool: bool = False
    token_path: str = ""   # JMESPath (dot-notation) to the token in the response
                           # e.g. "data.access_token" or "token"
    token_key: str = "user_token"  # key under which to store the token in SessionTokenStore

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI ``tools`` array element."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Per-collection tool storage backed by JSON files.

    Cache invalidation: uses file modification time so multiple in-process
    instances (API endpoint + RAG system) always see the latest data after
    a write without needing a shared singleton.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = base_dir or _BASE_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[RegisteredTool]] = {}
        self._cache_mtime: Dict[str, float] = {}  # file mtime at last load

    def _file_for(self, collection_name: str) -> Path:
        safe = collection_name.replace("/", "_").replace("\\", "_")
        return self._base_dir / f"{safe}.json"

    def _load(self, collection_name: str) -> List[RegisteredTool]:
        path = self._file_for(collection_name)
        if not path.exists():
            self._cache[collection_name] = []
            return []

        # Invalidate cache if file was modified by another process/instance
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            current_mtime = 0.0

        if (
            collection_name in self._cache
            and self._cache_mtime.get(collection_name, 0) >= current_mtime
        ):
            return self._cache[collection_name]

        # Load fresh from disk
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            tools = []
            for t in raw:
                # Forward-compatibility: drop unknown keys so old JSON still loads
                known = {f.name for f in RegisteredTool.__dataclass_fields__.values()}  # type: ignore[attr-defined]
                filtered = {k: v for k, v in t.items() if k in known}
                tools.append(RegisteredTool(**filtered))
            self._cache[collection_name] = tools
            self._cache_mtime[collection_name] = current_mtime
            logger.debug(f"[ToolRegistry] Loaded {len(tools)} tools for '{collection_name}' (mtime={current_mtime:.0f})")
            return tools
        except Exception as e:
            logger.error(f"Failed to load tools for {collection_name}: {e}")
            self._cache[collection_name] = []
            return []

    def _save(self, collection_name: str, tools: List[RegisteredTool]) -> None:
        path = self._file_for(collection_name)
        data = [asdict(t) for t in tools]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._cache[collection_name] = tools
        # Update our mtime so we don't reload immediately on next access
        try:
            self._cache_mtime[collection_name] = path.stat().st_mtime
        except OSError:
            self._cache_mtime.pop(collection_name, None)

    def has_tools(self, collection_name: str) -> bool:
        tools = self._load(collection_name)
        return any(t.is_enabled for t in tools)

    def get_tools(self, collection_name: str) -> List[RegisteredTool]:
        return [t for t in self._load(collection_name) if t.is_enabled]

    def get_tool_by_name(self, collection_name: str, tool_name: str) -> Optional[RegisteredTool]:
        for t in self._load(collection_name):
            if t.name == tool_name:
                return t
        return None

    def get_tool_by_id(self, collection_name: str, tool_id: str) -> Optional[RegisteredTool]:
        for t in self._load(collection_name):
            if t.tool_id == tool_id:
                return t
        return None

    def register(self, tool: RegisteredTool) -> RegisteredTool:
        if not tool.tool_id:
            tool.tool_id = str(uuid.uuid4())
        tools = self._load(tool.collection_name)
        existing = [t for t in tools if t.name == tool.name]
        if existing:
            raise ValueError(f"Tool '{tool.name}' already exists in collection '{tool.collection_name}'")
        tools.append(tool)
        self._save(tool.collection_name, tools)
        logger.info(f"Registered tool '{tool.name}' for collection '{tool.collection_name}'")
        return tool

    def update(self, collection_name: str, tool_id: str, updates: Dict[str, Any]) -> Optional[RegisteredTool]:
        tools = self._load(collection_name)
        for i, t in enumerate(tools):
            if t.tool_id == tool_id:
                d = asdict(t)
                d.update(updates)
                d.pop("tool_id", None)
                tools[i] = RegisteredTool(tool_id=tool_id, **{k: v for k, v in d.items() if k != "tool_id"})
                self._save(collection_name, tools)
                return tools[i]
        return None

    def delete(self, collection_name: str, tool_id: str) -> bool:
        tools = self._load(collection_name)
        new_tools = [t for t in tools if t.tool_id != tool_id]
        if len(new_tools) == len(tools):
            return False
        self._save(collection_name, new_tools)
        logger.info(f"Deleted tool {tool_id} from collection {collection_name}")
        return True

    def get_openai_tools(self, collection_name: str) -> List[Dict[str, Any]]:
        """Return the OpenAI-compatible ``tools`` array for a collection."""
        return [t.to_openai_tool() for t in self.get_tools(collection_name)]

    def get_trigger_descriptions(self, collection_name: str) -> str:
        """Build a merged trigger-description block for the system prompt."""
        parts: List[str] = []
        for t in self.get_tools(collection_name):
            if t.trigger_description:
                parts.append(f"- {t.name}: {t.trigger_description}")
        return "\n".join(parts)

    def list_all_collections_with_tools(self) -> List[str]:
        collections: List[str] = []
        for f in self._base_dir.glob("*.json"):
            name = f.stem
            if self.has_tools(name):
                collections.append(name)
        return collections

    def clear_cache(self, collection_name: Optional[str] = None) -> None:
        if collection_name:
            self._cache.pop(collection_name, None)
        else:
            self._cache.clear()
