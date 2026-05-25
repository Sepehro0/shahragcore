# -*- coding: utf-8 -*-
"""
Agent Planner — multi-step reasoning, query decomposition, and tool chaining.

Architecture:
  User Query → Planner (LLM) → Plan [step1, step2, ...]
             → Executor → step1 result → step2 result → ...
             → Synthesizer (LLM) → Final Answer

Key capabilities:
  - **ReAct loop**: Reason → Act → Observe → Reason (up to N rounds)
  - **Query decomposition**: Split "A و B و C" into parallel sub-tasks
  - **Tool dependency graph**: Step B can depend on output of Step A
  - **Plan verification**: Validate the plan before execution
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from services.qwen_client import QwenClient
from services.tool_registry import ToolRegistry
from services.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────

class StepType(str, Enum):
    TOOL_CALL = "tool_call"
    RAG_QUERY = "rag_query"
    REASON = "reason"
    SYNTHESIZE = "synthesize"


@dataclass
class PlanStep:
    step_id: int
    step_type: StepType
    description: str
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    depends_on: List[int] = field(default_factory=list)
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class ExecutionPlan:
    original_query: str
    sub_queries: List[str]
    steps: List[PlanStep]
    is_multi_part: bool = False
    verified: bool = False


# ─────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────

_DECOMPOSE_SYSTEM = (
    "تو یک مدیر وظایف هستی. وظیفه‌ات تجزیه سوالات پیچیده به زیرسوالات ساده‌تر است.\n"
    "اگر سوال ساده است و نیاز به تجزیه ندارد، فقط یک آیتم برگردان.\n"
    "خروجی باید JSON باشد با فرمت: {\"sub_queries\": [\"سوال ۱\", \"سوال ۲\", ...]}\n"
    "فقط JSON خالص برگردان، بدون هیچ توضیح اضافی."
)

_PLAN_SYSTEM = (
    "تو یک برنامه‌ریز هوشمند هستی. وظیفه‌ات ساختن یک plan اجرایی برای پاسخ به سوال کاربر است.\n"
    "ابزارهای موجود:\n{tools_desc}\n\n"
    "خروجی باید JSON باشد با فرمت:\n"
    '{{"steps": [{{"step_id": 1, "type": "tool_call"|"reason", "description": "...", '
    '"tool_name": "..." | null, "arguments": {{...}} | null, "depends_on": []}}]}}\n'
    "اگر step فعلی به نتیجه step قبلی نیاز دارد، شماره آن step را در depends_on بگذار.\n"
    "فقط JSON خالص برگردان."
)

_REACT_SYSTEM = (
    "تو یک دستیار هوشمند هستی که به صورت مرحله‌ای فکر می‌کنی.\n"
    "در هر مرحله:\n"
    "1. **فکر** (Thought): تحلیل کن چه اطلاعاتی داری و چه نیاز داری\n"
    "2. **عمل** (Action): از ابزار مناسب استفاده کن یا پاسخ نهایی بده\n"
    "3. **مشاهده** (Observation): نتیجه عمل را بررسی کن\n\n"
    "ابزارهای موجود:\n{tools_desc}\n\n"
    "وقتی پاسخ نهایی آماده است، با [FINAL_ANSWER] شروع کن.\n"
    "همیشه به فارسی پاسخ بده."
)

_SYNTHESIZE_SYSTEM = (
    "تو یک دستیار هوشمند هستی. اطلاعات زیر از اجرای چندین مرحله به دست آمده.\n"
    "با استفاده از همه این اطلاعات، یک پاسخ جامع و طبیعی به فارسی بنویس.\n"
    "سوال اصلی کاربر: {query}"
)


# ─────────────────────────────────────────────────────────────
# Agent Planner
# ─────────────────────────────────────────────────────────────

class AgentPlanner:
    """Multi-step agent with ReAct loop, query decomposition, and synthesis."""

    def __init__(
        self,
        qwen_client: QwenClient,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ):
        self.qwen_client = qwen_client
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor

    # ── Query Decomposition ──

    async def decompose_query(self, query: str) -> List[str]:
        """Break a complex query into simpler sub-queries."""
        if not self._looks_multi_part(query):
            return [query]

        try:
            resp = await self.qwen_client.generate_text(
                prompt=f"سوال: {query}",
                system_prompt=_DECOMPOSE_SYSTEM,
                max_tokens=256,
                temperature=0.1,
            )
            if resp.success and resp.text:
                parsed = self._extract_json(resp.text)
                subs = parsed.get("sub_queries", [query])
                if isinstance(subs, list) and len(subs) >= 1:
                    logger.info(f"[AgentPlanner] Decomposed into {len(subs)} sub-queries")
                    return subs
        except Exception as e:
            logger.warning(f"[AgentPlanner] Decomposition failed: {e}")

        return [query]

    # ── Plan Generation ──

    async def create_plan(
        self,
        query: str,
        collection_name: str,
        sub_queries: Optional[List[str]] = None,
    ) -> ExecutionPlan:
        """Generate an execution plan for the query using available tools."""
        subs = sub_queries or await self.decompose_query(query)
        tools = self.tool_registry.get_tools(collection_name)
        is_multi = len(subs) > 1

        if not tools:
            steps = [PlanStep(step_id=i + 1, step_type=StepType.RAG_QUERY, description=sq) for i, sq in enumerate(subs)]
            return ExecutionPlan(original_query=query, sub_queries=subs, steps=steps, is_multi_part=is_multi)

        tools_desc = self.tool_registry.get_trigger_descriptions(collection_name)
        combined_query = " | ".join(subs) if is_multi else query

        try:
            prompt = f"سوال کاربر: {combined_query}\n\nابزارهای موجود:\n{tools_desc}"
            resp = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt=_PLAN_SYSTEM.format(tools_desc=tools_desc),
                max_tokens=512,
                temperature=0.1,
            )
            if resp.success and resp.text:
                parsed = self._extract_json(resp.text)
                raw_steps = parsed.get("steps", [])
                steps = []
                for s in raw_steps:
                    stype = StepType.TOOL_CALL if s.get("type") == "tool_call" else StepType.REASON
                    steps.append(PlanStep(
                        step_id=s.get("step_id", len(steps) + 1),
                        step_type=stype,
                        description=s.get("description", ""),
                        tool_name=s.get("tool_name"),
                        arguments=s.get("arguments"),
                        depends_on=s.get("depends_on", []),
                    ))
                if steps:
                    return ExecutionPlan(
                        original_query=query, sub_queries=subs,
                        steps=steps, is_multi_part=is_multi,
                    )
        except Exception as e:
            logger.warning(f"[AgentPlanner] Plan generation failed: {e}")

        steps = [PlanStep(step_id=i + 1, step_type=StepType.RAG_QUERY, description=sq) for i, sq in enumerate(subs)]
        return ExecutionPlan(original_query=query, sub_queries=subs, steps=steps, is_multi_part=is_multi)

    # ── Plan Verification ──

    def verify_plan(self, plan: ExecutionPlan, collection_name: str) -> ExecutionPlan:
        """Validate the plan before execution."""
        valid_steps = []
        for step in plan.steps:
            if step.step_type == StepType.TOOL_CALL and step.tool_name:
                tool = self.tool_registry.get_tool_by_name(collection_name, step.tool_name)
                if not tool:
                    logger.warning(f"[AgentPlanner] Removing step {step.step_id}: tool '{step.tool_name}' not found")
                    step.step_type = StepType.RAG_QUERY
                    step.tool_name = None
            for dep_id in step.depends_on:
                if not any(s.step_id == dep_id for s in plan.steps):
                    step.depends_on.remove(dep_id)
            valid_steps.append(step)
        plan.steps = valid_steps
        plan.verified = True
        return plan

    # ── Plan Execution ──

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        collection_name: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a verified plan step by step, respecting dependencies."""
        if not plan.verified:
            plan = self.verify_plan(plan, collection_name)

        results: Dict[int, Any] = {}
        start = time.time()

        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in results:
                    logger.warning(f"[AgentPlanner] Step {step.step_id} dependency {dep_id} not resolved")

            step.status = "running"
            try:
                if step.step_type == StepType.TOOL_CALL and step.tool_name:
                    dep_context = {f"step_{did}_result": results.get(did, "") for did in step.depends_on}
                    args = step.arguments or {}
                    if dep_context:
                        args = {**args, **dep_context}

                    registered = self.tool_registry.get_tool_by_name(collection_name, step.tool_name)
                    if registered:
                        result = await self.tool_executor.execute(
                            tool_call_id=f"plan_step_{step.step_id}",
                            function_name=step.tool_name,
                            arguments=args,
                            registered_tool=registered,
                            collection_name=collection_name,
                            conversation_id=conversation_id,
                        )
                        step.result = result
                        results[step.step_id] = result.get("data", result)
                    else:
                        step.result = {"error": f"Tool '{step.tool_name}' not found"}
                        results[step.step_id] = step.result

                elif step.step_type == StepType.RAG_QUERY:
                    results[step.step_id] = {"query": step.description, "type": "rag_needed"}
                    step.result = results[step.step_id]

                elif step.step_type == StepType.REASON:
                    results[step.step_id] = {"reasoning": step.description}
                    step.result = results[step.step_id]

                step.status = "completed"

            except Exception as e:
                logger.error(f"[AgentPlanner] Step {step.step_id} failed: {e}")
                step.status = "failed"
                step.result = {"error": str(e)}
                results[step.step_id] = step.result

        elapsed = round(time.time() - start, 2)
        return {
            "results": results,
            "steps": [{"id": s.step_id, "type": s.step_type.value, "status": s.status, "result": s.result} for s in plan.steps],
            "elapsed_seconds": elapsed,
        }

    # ── ReAct Loop ──

    async def react_loop(
        self,
        query: str,
        collection_name: str,
        conversation_id: Optional[str] = None,
        max_rounds: int = 5,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Full ReAct loop: Reason → Act → Observe → Reason.
        Falls back to simple tool calling if the collection has no tools.
        """
        tools = self.tool_registry.get_tools(collection_name)
        if not tools:
            return {"answer": "", "success": False, "error": "No tools registered for ReAct"}

        openai_tools = self.tool_registry.get_openai_tools(collection_name)
        tools_desc = self.tool_registry.get_trigger_descriptions(collection_name)
        sys_prompt = _REACT_SYSTEM.format(tools_desc=tools_desc)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query},
        ]

        all_tool_calls = []
        thoughts = []
        start = time.time()

        for round_idx in range(max_rounds):
            resp = await self.qwen_client.generate_with_tools(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not resp.success:
                return {"answer": "", "success": False, "error": f"LLM error at round {round_idx}: {resp.error}"}

            text = resp.text or ""
            thoughts.append({"round": round_idx, "thought": text})

            if "[FINAL_ANSWER]" in text:
                answer = text.split("[FINAL_ANSWER]", 1)[1].strip()
                elapsed = round(time.time() - start, 2)
                return {
                    "answer": answer,
                    "success": True,
                    "thoughts": thoughts,
                    "tool_calls_made": all_tool_calls,
                    "metadata": {
                        "source": "react_agent",
                        "rounds": round_idx + 1,
                        "total_tool_calls": len(all_tool_calls),
                        "elapsed_seconds": elapsed,
                    },
                }

            if not resp.tool_calls:
                if round_idx == max_rounds - 1:
                    break
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": "ادامه بده و اگر پاسخ آماده است با [FINAL_ANSWER] شروع کن."})
                continue

            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": text}
            raw_tc = []
            for tc in resp.tool_calls:
                raw_tc.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(tc["function"]["arguments"], ensure_ascii=False),
                    },
                })
            assistant_msg["tool_calls"] = raw_tc
            messages.append(assistant_msg)

            for tc in resp.tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"]["arguments"]
                tc_id = tc["id"]

                registered = self.tool_registry.get_tool_by_name(collection_name, fn_name)
                if not registered:
                    tool_result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    tool_result = await self.tool_executor.execute(
                        tool_call_id=tc_id,
                        function_name=fn_name,
                        arguments=fn_args,
                        registered_tool=registered,
                        collection_name=collection_name,
                        conversation_id=conversation_id,
                    )

                all_tool_calls.append({
                    "tool_call_id": tc_id,
                    "function_name": fn_name,
                    "arguments": fn_args,
                    "result": tool_result,
                    "round": round_idx,
                })

                result_content = json.dumps(
                    tool_result.get("data", tool_result), ensure_ascii=False, default=str,
                )
                if len(result_content) > 4000:
                    result_content = result_content[:4000] + "...(truncated)"

                messages.append({"role": "tool", "tool_call_id": tc_id, "content": result_content})

        # All rounds exhausted — force a final answer
        messages.append({"role": "user", "content": "بر اساس تمام اطلاعات بالا، پاسخ نهایی را بده."})
        final = await self.qwen_client.generate_with_tools(
            messages=messages, tools=openai_tools, tool_choice="none",
            max_tokens=max_tokens, temperature=temperature,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "answer": final.text if final.success else "",
            "success": final.success,
            "thoughts": thoughts,
            "tool_calls_made": all_tool_calls,
            "metadata": {
                "source": "react_agent",
                "rounds": max_rounds,
                "total_tool_calls": len(all_tool_calls),
                "elapsed_seconds": elapsed,
                "forced_final": True,
            },
        }

    # ── Synthesize multiple results ──

    async def synthesize(
        self,
        query: str,
        step_results: Dict[int, Any],
        max_tokens: int = 1024,
    ) -> str:
        """Combine multiple step results into a single coherent answer."""
        parts = []
        for step_id in sorted(step_results):
            result = step_results[step_id]
            if isinstance(result, dict):
                parts.append(f"نتیجه مرحله {step_id}: {json.dumps(result, ensure_ascii=False, default=str)[:800]}")
            else:
                parts.append(f"نتیجه مرحله {step_id}: {str(result)[:800]}")

        prompt = "\n".join(parts)
        sys = _SYNTHESIZE_SYSTEM.format(query=query)

        try:
            resp = await self.qwen_client.generate_text(
                prompt=prompt, system_prompt=sys,
                max_tokens=max_tokens, temperature=0.3,
            )
            if resp.success and resp.text:
                return resp.text
        except Exception as e:
            logger.warning(f"[AgentPlanner] Synthesis failed: {e}")

        return "\n".join(f"- {p}" for p in parts)

    # ── Full pipeline: decompose → plan → verify → execute → synthesize ──

    async def run(
        self,
        query: str,
        collection_name: str,
        conversation_id: Optional[str] = None,
        use_react: bool = False,
        max_react_rounds: int = 5,
    ) -> Dict[str, Any]:
        """
        Full agent planning pipeline.

        If ``use_react`` is True, uses the ReAct loop directly.
        Otherwise uses the plan-based approach:
          decompose → plan → verify → execute → synthesize.
        """
        start = time.time()

        if use_react:
            return await self.react_loop(
                query=query,
                collection_name=collection_name,
                conversation_id=conversation_id,
                max_rounds=max_react_rounds,
            )

        sub_queries = await self.decompose_query(query)
        plan = await self.create_plan(query, collection_name, sub_queries)
        plan = self.verify_plan(plan, collection_name)

        execution = await self.execute_plan(plan, collection_name, conversation_id)

        tool_results = {sid: r for sid, r in execution["results"].items()
                        if not (isinstance(r, dict) and r.get("type") == "rag_needed")}
        rag_needed = [r["query"] for r in execution["results"].values()
                      if isinstance(r, dict) and r.get("type") == "rag_needed"]

        answer = ""
        if tool_results:
            answer = await self.synthesize(query, tool_results)

        elapsed = round(time.time() - start, 2)
        return {
            "answer": answer,
            "success": True,
            "plan": {
                "sub_queries": sub_queries,
                "steps": execution["steps"],
                "is_multi_part": plan.is_multi_part,
            },
            "rag_queries_needed": rag_needed,
            "metadata": {
                "source": "agent_planner",
                "total_steps": len(plan.steps),
                "elapsed_seconds": elapsed,
            },
        }

    # ── Helpers ──

    @staticmethod
    def _looks_multi_part(query: str) -> bool:
        """Heuristic: does the query contain multiple sub-questions?"""
        indicators = [" و ", "؟"]
        q_lower = query.lower()
        conjunction_count = q_lower.count(" و ")
        question_mark_count = q_lower.count("؟")
        question_words = ["چیست", "چطور", "چگونه", "کجا", "کی", "چرا", "چقدر", "چند"]
        qw_count = sum(1 for w in question_words if w in q_lower)
        return conjunction_count >= 2 or question_mark_count >= 2 or (conjunction_count >= 1 and qw_count >= 2)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response text (may have markdown fences)."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.split("```", 1)[0]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}
