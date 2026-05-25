# -*- coding: utf-8 -*-
"""
Agent Planner API — endpoints for multi-step planning and ReAct execution.

Endpoints:
  POST  /agent/plan      → Decompose and plan a query
  POST  /agent/execute   → Execute a plan (or run ReAct loop directly)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent Planner"])


# ── Schemas ──

class PlanRequest(BaseModel):
    query: str = Field(..., description="User query to decompose and plan")
    collection_name: str = Field(..., description="Collection to use tools from")

class PlanResponse(BaseModel):
    sub_queries: List[str]
    steps: List[Dict[str, Any]]
    is_multi_part: bool
    verified: bool

class ExecuteRequest(BaseModel):
    query: str = Field(..., description="User query")
    collection_name: str = Field(..., description="Collection name")
    conversation_id: Optional[str] = None
    use_react: bool = Field(False, description="Use ReAct loop instead of plan-based approach")
    max_react_rounds: int = Field(5, ge=1, le=10)

class ExecuteResponse(BaseModel):
    answer: str
    success: bool
    metadata: Dict[str, Any] = {}
    plan: Optional[Dict[str, Any]] = None
    thoughts: Optional[List[Dict[str, Any]]] = None


# ── Helpers ──

def _get_rag_system():
    try:
        from api_server import get_rag_system
        return get_rag_system()
    except Exception:
        raise HTTPException(status_code=503, detail="RAG system not initialized")


# ── Endpoints ──

@router.post("/plan", response_model=PlanResponse)
async def create_plan(payload: PlanRequest):
    """Decompose a query and create an execution plan."""
    rag = _get_rag_system()
    if not hasattr(rag, "agent_planner"):
        raise HTTPException(status_code=501, detail="Agent planner not available")

    planner = rag.agent_planner
    sub_queries = await planner.decompose_query(payload.query)
    plan = await planner.create_plan(payload.query, payload.collection_name, sub_queries)
    plan = planner.verify_plan(plan, payload.collection_name)

    return PlanResponse(
        sub_queries=plan.sub_queries,
        steps=[{"id": s.step_id, "type": s.step_type.value, "description": s.description,
                "tool_name": s.tool_name, "depends_on": s.depends_on}
               for s in plan.steps],
        is_multi_part=plan.is_multi_part,
        verified=plan.verified,
    )


@router.post("/execute", response_model=ExecuteResponse)
async def execute_agent(payload: ExecuteRequest):
    """Execute the agent pipeline (plan-based or ReAct)."""
    rag = _get_rag_system()
    if not hasattr(rag, "agent_planner"):
        raise HTTPException(status_code=501, detail="Agent planner not available")

    planner = rag.agent_planner
    result = await planner.run(
        query=payload.query,
        collection_name=payload.collection_name,
        conversation_id=payload.conversation_id,
        use_react=payload.use_react,
        max_react_rounds=payload.max_react_rounds,
    )

    return ExecuteResponse(
        answer=result.get("answer", ""),
        success=result.get("success", False),
        metadata=result.get("metadata", {}),
        plan=result.get("plan"),
        thoughts=result.get("thoughts"),
    )
