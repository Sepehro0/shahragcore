# -*- coding: utf-8 -*-
"""
Tool Registry API — CRUD endpoints for managing user-defined API tools.

Endpoints:
  POST   /tools/register              → Register a new tool
  GET    /tools/{collection_name}     → List tools for a collection
  PUT    /tools/{collection_name}/{tool_id}  → Update a tool
  DELETE /tools/{collection_name}/{tool_id}  → Delete a tool
  POST   /tools/test                  → Test a tool endpoint (dry-run)
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, HTTPException

from api.v1.schemas.tool_schemas import (
    RegisterToolRequest,
    TestToolRequest,
    TestToolResponse,
    ToolListResponse,
    ToolResponse,
    UpdateToolRequest,
)
from services.tool_executor import ToolExecutor
from services.tool_registry import RegisteredTool, ToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Tool Registry"])

_registry = ToolRegistry()
_executor = ToolExecutor()


def _tool_to_response(t: RegisteredTool) -> ToolResponse:
    return ToolResponse(
        tool_id=t.tool_id,
        name=t.name,
        description=t.description,
        parameters=t.parameters,
        http_method=t.http_method,
        endpoint_url=t.endpoint_url,
        trigger_description=t.trigger_description,
        collection_name=t.collection_name,
        is_enabled=t.is_enabled,
        timeout_seconds=t.timeout_seconds,
        is_auth_tool=getattr(t, "is_auth_tool", False),
        token_path=getattr(t, "token_path", ""),
        token_key=getattr(t, "token_key", "user_token"),
    )


@router.post("/register", response_model=ToolResponse)
async def register_tool(req: RegisterToolRequest):
    """Register a new API tool for a collection."""
    tool = RegisteredTool(
        tool_id="",
        name=req.name,
        description=req.description,
        parameters=req.parameters.model_dump(),
        http_method=req.http_method.upper(),
        endpoint_url=req.endpoint_url,
        auth_config=req.auth_config.model_dump(),
        trigger_description=req.trigger_description,
        collection_name=req.collection_name,
        tenant_id=req.tenant_id,
        headers=req.headers,
        request_body_template=req.request_body_template,
        response_jmespath=req.response_jmespath,
        timeout_seconds=req.timeout_seconds,
        is_auth_tool=req.is_auth_tool,
        token_path=req.token_path,
        token_key=req.token_key,
    )
    try:
        created = _registry.register(tool)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _tool_to_response(created)


@router.get("/{collection_name}", response_model=ToolListResponse)
async def list_tools(collection_name: str, include_disabled: bool = False):
    """List all tools registered for a collection."""
    if include_disabled:
        tools = _registry._load(collection_name)
    else:
        tools = _registry.get_tools(collection_name)
    return ToolListResponse(
        collection_name=collection_name,
        tools=[_tool_to_response(t) for t in tools],
        count=len(tools),
    )


@router.put("/{collection_name}/{tool_id}", response_model=ToolResponse)
async def update_tool(collection_name: str, tool_id: str, req: UpdateToolRequest):
    """Update an existing tool."""
    updates: Dict[str, Any] = {}
    for field_name, value in req.model_dump(exclude_unset=True).items():
        if value is not None:
            if field_name == "parameters":
                updates[field_name] = value if isinstance(value, dict) else value
            elif field_name == "auth_config":
                updates[field_name] = value if isinstance(value, dict) else value
            else:
                updates[field_name] = value

    updated = _registry.update(collection_name, tool_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return _tool_to_response(updated)


@router.delete("/{collection_name}/{tool_id}")
async def delete_tool(collection_name: str, tool_id: str):
    """Delete a tool."""
    deleted = _registry.delete(collection_name, tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return {"status": "deleted", "tool_id": tool_id}


@router.post("/test", response_model=TestToolResponse)
async def test_tool(req: TestToolRequest):
    """Dry-run a tool with test arguments."""
    tool = _registry.get_tool_by_name(req.collection_name, req.tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{req.tool_name}' not found in collection '{req.collection_name}'",
        )

    start = time.time()
    result = await _executor.execute(
        tool_call_id="test",
        function_name=req.tool_name,
        arguments=req.test_arguments,
        registered_tool=tool,
    )
    elapsed_ms = round((time.time() - start) * 1000, 1)

    return TestToolResponse(
        success=result.get("success", False),
        status_code=result.get("status_code"),
        data=result.get("data"),
        error=result.get("error"),
        elapsed_ms=elapsed_ms,
    )
