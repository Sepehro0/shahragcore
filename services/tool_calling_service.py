# -*- coding: utf-8 -*-
"""
Tool Calling Service — agentic orchestration loop.

Flow:
  1. Load registered tools for the collection
  2. Send user query + tools to Qwen via ``generate_with_tools``
  3. If the model returns ``tool_calls``, execute each tool
  4. Append tool results as ``role=tool`` messages and call the model again
  5. Repeat until the model produces a final text answer (or max rounds)
"""

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from services.qwen_client import QwenClient
from services.tool_registry import ToolRegistry, RegisteredTool
from services.tool_executor import ToolExecutor
from services.session_token_store import SessionTokenStore, get_session_token_store

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "تو یک دستیار هوشمند هستی. وقتی برای پاسخ دادن به سوال کاربر نیاز به اطلاعات "
    "بروز داری (مثلاً وضعیت سفارش، موجودی، قیمت لحظه‌ای و ...)، از tool‌هایی که در "
    "اختیار داری استفاده کن. اگر tool مناسبی نداری، مستقیم پاسخ بده.\n"
    "همیشه به فارسی پاسخ بده مگر اینکه کاربر زبان دیگری درخواست کند."
)


def _extract_nested(data: Any, path: str) -> Optional[str]:
    """
    Extract a value from a nested dict/list using a dot-notation path.
    e.g. path="data.access_token" → data["data"]["access_token"]
    Returns None if the path is invalid or the value is not a string.
    """
    if not path or data is None:
        return None
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
        if current is None:
            return None
    return str(current) if current is not None else None


class ToolCallingService:
    """Orchestrate the LLM <-> Tool execution loop."""

    def __init__(
        self,
        qwen_client: QwenClient,
        tool_registry: ToolRegistry,
        tool_executor: Optional[ToolExecutor] = None,
        session_token_store: Optional[SessionTokenStore] = None,
    ):
        self.qwen_client = qwen_client
        self.tool_registry = tool_registry
        self._token_store = session_token_store or get_session_token_store()
        self.tool_executor = tool_executor or ToolExecutor(
            session_token_store=self._token_store
        )

    def _handle_auth_tool_result(
        self,
        registered_tool: RegisteredTool,
        tool_result: Dict[str, Any],
        session_id: str,
    ) -> Optional[str]:
        """
        If *registered_tool* is an auth tool and the call succeeded,
        extract the token and store it in SessionTokenStore.
        Returns the stored token value (or None).
        """
        if not registered_tool.is_auth_tool:
            return None
        if not tool_result.get("success"):
            return None

        response_data = tool_result.get("data")
        token_value = _extract_nested(response_data, registered_tool.token_path)

        if token_value:
            self._token_store.set(
                session_id=session_id,
                token_key=registered_tool.token_key or "user_token",
                value=token_value,
            )
            logger.info(
                f"[ToolCalling] Auth token stored for session {session_id[:8]}… "
                f"(key={registered_tool.token_key})"
            )
        else:
            logger.warning(
                f"[ToolCalling] Auth tool '{registered_tool.name}' succeeded but "
                f"token_path='{registered_tool.token_path}' found no value in response."
            )
        return token_value

    async def process_with_tools(
        self,
        query: str,
        collection_name: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_tool_rounds: int = 3,
        max_tokens: int = 1024,
        temperature: float = 0.7,  # Qwen3.6 recommended for normal mode
    ) -> Dict[str, Any]:
        """
        Run the agentic tool-calling loop.

        Returns a dict compatible with the existing RAG answer format::

            {
                "answer": str,
                "metadata": {...},
                "tool_calls_made": [...],
                "success": bool,
            }
        """
        tools = self.tool_registry.get_tools(collection_name)
        if not tools:
            return {"answer": "", "success": False, "error": "No tools registered"}

        openai_tools = self.tool_registry.get_openai_tools(collection_name)
        trigger_ctx = self.tool_registry.get_trigger_descriptions(collection_name)

        sys_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
        if trigger_ctx:
            sys_prompt += f"\n\nابزارهای موجود و زمان استفاده:\n{trigger_ctx}"

        messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]

        if chat_history:
            for msg in chat_history[-6:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": query})

        # Effective session for token resolution (prefer explicit session_id)
        eff_session = session_id or conversation_id or ""

        all_tool_calls: List[Dict[str, Any]] = []
        start = time.time()

        for round_idx in range(max_tool_rounds):
            resp = await self.qwen_client.generate_with_tools(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not resp.success:
                logger.warning(f"[ToolCalling] LLM call failed: {resp.error}")
                return {
                    "answer": "",
                    "success": False,
                    "error": f"LLM error: {resp.error}",
                    "tool_calls_made": all_tool_calls,
                }

            if not resp.tool_calls:
                answer = resp.text or ""
                elapsed = round(time.time() - start, 2)
                logger.info(
                    f"[ToolCalling] Final answer after {round_idx} tool round(s) "
                    f"({elapsed}s, {len(all_tool_calls)} tool calls)"
                )
                return {
                    "answer": answer,
                    "success": True,
                    "tool_calls_made": all_tool_calls,
                    "metadata": {
                        "source": "tool_calling",
                        "tool_rounds": round_idx,
                        "total_tool_calls": len(all_tool_calls),
                        "elapsed_seconds": elapsed,
                        "collection_name": collection_name,
                        "conversation_id": conversation_id,
                    },
                }

            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": resp.text or ""}
            raw_tc_for_msg = []
            for tc in resp.tool_calls:
                raw_tc_for_msg.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(tc["function"]["arguments"], ensure_ascii=False),
                    },
                })
            assistant_msg["tool_calls"] = raw_tc_for_msg
            messages.append(assistant_msg)

            for tc in resp.tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"]["arguments"]
                tc_id = tc["id"]

                registered = self.tool_registry.get_tool_by_name(collection_name, fn_name)
                if not registered:
                    tool_result = {"error": f"Unknown tool: {fn_name}"}
                    logger.warning(f"[ToolCalling] Unknown tool requested: {fn_name}")
                else:
                    logger.info(f"[ToolCalling] Executing tool '{fn_name}' with args: {fn_args}")
                    tool_result = await self.tool_executor.execute(
                        tool_call_id=tc_id,
                        function_name=fn_name,
                        arguments=fn_args,
                        registered_tool=registered,
                        collection_name=collection_name,
                        conversation_id=conversation_id,
                        session_id=eff_session,
                    )
                    # If this was an auth tool, extract & store the token
                    if eff_session:
                        self._handle_auth_tool_result(registered, tool_result, eff_session)

                all_tool_calls.append({
                    "tool_call_id": tc_id,
                    "function_name": fn_name,
                    "arguments": fn_args,
                    "result": tool_result,
                    "round": round_idx,
                })

                result_content = json.dumps(
                    tool_result.get("data", tool_result),
                    ensure_ascii=False,
                    default=str,
                )
                if len(result_content) > 4000:
                    result_content = result_content[:4000] + "...(truncated)"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_content,
                })

        final_resp = await self.qwen_client.generate_with_tools(
            messages=messages,
            tools=openai_tools,
            tool_choice="none",
            max_tokens=max_tokens,
            temperature=temperature,
        )

        elapsed = round(time.time() - start, 2)
        return {
            "answer": final_resp.text if final_resp.success else "",
            "success": final_resp.success,
            "tool_calls_made": all_tool_calls,
            "metadata": {
                "source": "tool_calling",
                "tool_rounds": max_tool_rounds,
                "total_tool_calls": len(all_tool_calls),
                "elapsed_seconds": elapsed,
                "forced_final": True,
                "collection_name": collection_name,
                "conversation_id": conversation_id,
            },
        }

    async def process_with_tools_stream(
        self,
        query: str,
        collection_name: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_tool_rounds: int = 3,
        max_tokens: int = 1024,
        temperature: float = 0.7,  # Qwen3.6 recommended for normal mode
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming variant of ``process_with_tools``.

        Yields SSE-friendly dicts with ``event`` field:
          - ``tool_start``   — tool execution is about to begin
          - ``tool_result``  — tool execution completed
          - ``answer_start`` — final LLM answer generation begins
          - ``token``        — streamed token from the final answer
          - ``complete``     — full answer assembled
          - ``error``        — something went wrong
        """
        tools = self.tool_registry.get_tools(collection_name)
        if not tools:
            yield {"event": "error", "error": "No tools registered", "success": False}
            return

        openai_tools = self.tool_registry.get_openai_tools(collection_name)
        trigger_ctx = self.tool_registry.get_trigger_descriptions(collection_name)

        sys_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
        if trigger_ctx:
            sys_prompt += f"\n\nابزارهای موجود و زمان استفاده:\n{trigger_ctx}"

        messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]

        if chat_history:
            for msg in chat_history[-6:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": query})

        eff_session = session_id or conversation_id or ""

        all_tool_calls: List[Dict[str, Any]] = []
        start = time.time()

        for round_idx in range(max_tool_rounds):
            resp = await self.qwen_client.generate_with_tools(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not resp.success:
                yield {"event": "error", "error": f"LLM error: {resp.error}", "success": False}
                return

            if not resp.tool_calls:
                break

            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": resp.text or ""}
            raw_tc_for_msg = []
            for tc in resp.tool_calls:
                raw_tc_for_msg.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(tc["function"]["arguments"], ensure_ascii=False),
                    },
                })
            assistant_msg["tool_calls"] = raw_tc_for_msg
            messages.append(assistant_msg)

            for tc in resp.tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"]["arguments"]
                tc_id = tc["id"]

                yield {
                    "event": "tool_start",
                    "tool_name": fn_name,
                    "arguments": fn_args,
                    "round": round_idx,
                }

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
                        session_id=eff_session,
                    )
                    if eff_session:
                        self._handle_auth_tool_result(registered, tool_result, eff_session)

                all_tool_calls.append({
                    "tool_call_id": tc_id,
                    "function_name": fn_name,
                    "arguments": fn_args,
                    "result": tool_result,
                    "round": round_idx,
                })

                yield {
                    "event": "tool_result",
                    "tool_name": fn_name,
                    "success": tool_result.get("success", False),
                    "round": round_idx,
                }

                result_content = json.dumps(
                    tool_result.get("data", tool_result),
                    ensure_ascii=False,
                    default=str,
                )
                if len(result_content) > 4000:
                    result_content = result_content[:4000] + "...(truncated)"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_content,
                })

        # Stream the final answer token-by-token
        yield {"event": "answer_start", "tool_calls_count": len(all_tool_calls)}

        # Build the final prompt from the full conversation for streaming
        final_prompt = messages[-1]["content"] if messages else query
        sys_content = messages[0]["content"] if messages and messages[0].get("role") == "system" else sys_prompt

        # Re-serialize the conversation for the streaming endpoint
        # (generate_stream takes a simple prompt, so we flatten the conversation)
        conversation_flat = ""
        for msg in messages[1:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                conversation_flat += f"\nکاربر: {content}"
            elif role == "assistant":
                conversation_flat += f"\nدستیار: {content}"
            elif role == "tool":
                conversation_flat += f"\nنتیجه ابزار: {content}"

        stream_prompt = (
            f"{conversation_flat}\n\n"
            "بر اساس اطلاعات بالا، به سوال کاربر پاسخ بده. به فارسی و به صورت طبیعی پاسخ بده."
        )

        full_response = ""
        async for token in self.qwen_client.generate_stream(
            prompt=stream_prompt,
            system_prompt=sys_content,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            if token.startswith("Error:"):
                yield {"event": "error", "error": token, "success": False}
                return
            full_response += token
            yield {
                "event": "token",
                "token": token,
                "full_response": full_response,
            }

        elapsed = round(time.time() - start, 2)
        yield {
            "event": "complete",
            "success": True,
            "answer": full_response,
            "tool_calls_made": all_tool_calls,
            "metadata": {
                "source": "tool_calling",
                "tool_rounds": len(set(tc["round"] for tc in all_tool_calls)) if all_tool_calls else 0,
                "total_tool_calls": len(all_tool_calls),
                "elapsed_seconds": elapsed,
                "collection_name": collection_name,
                "conversation_id": conversation_id,
            },
        }
