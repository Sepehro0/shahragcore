# -*- coding: utf-8 -*-
"""
Answer orchestration for the refactored RAG system.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnswerOrchestrator:
    """End-to-end query -> retrieval -> grounded answer orchestration."""

    def __init__(
        self,
        query_orchestrator,
        retrieval_orchestrator,
        answer_generator,
        chat_manager,
        qwen_client,
        collection_manager,
        database_handler=None,
        result_fusion=None,
        embedding_client=None,
        feature_flags=None,
    ):
        self.query_orchestrator = query_orchestrator
        self.retrieval_orchestrator = retrieval_orchestrator
        self.answer_generator = answer_generator
        self.chat_manager = chat_manager
        self.qwen_client = qwen_client
        self.collection_manager = collection_manager
        self.database_handler = database_handler
        self.result_fusion = result_fusion
        self.embedding_client = embedding_client
        self.feature_flags = feature_flags

    async def retrieve_and_answer(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        original_query = query
        domain_info = self._get_domain_info(collection_name)

        processed = await self.query_orchestrator.process_query(
            query=query,
            collection_name=collection_name,
            domain_info=domain_info,
        )

        if processed.get("is_greeting"):
            answer = processed.get("greeting_response") or "سلام، چطور می‌توانم کمک کنم؟"
            self._add_history(collection_name, original_query, answer, conversation_id)
            return {
                "success": True,
                "answer": answer,
                "top_results": [],
                "top_score": 1.0,
                "confidence": 1.0,
                "metadata": {"type": "greeting", "orchestrated": True},
                "used_query_understanding": True,
                "used_reranking": False,
                "used_multi_hop": False,
                "route_path": "greeting",
            }

        database_result = await self._try_database_first(
            query=processed.get("processed_query") or original_query,
            collection_name=collection_name,
            top_k=top_k,
            conversation_id=conversation_id,
            processed=processed,
            domain_info=domain_info,
        )
        if database_result is not None:
            answer = database_result.get("answer")
            if not answer:
                answer = self._build_database_answer(
                    query=original_query,
                    collection_name=collection_name,
                    database_results=database_result.get("database_results") or {},
                )
            self._add_history(collection_name, original_query, answer, conversation_id)
            return {
                "success": True,
                "answer": answer,
                "top_results": database_result.get("top_results", []),
                "top_score": 1.0,
                "confidence": 0.95,
                "metadata": {
                    **(database_result.get("metadata") or {}),
                    "orchestrated": True,
                    "query_processing": processed,
                    "route_path": "database",
                },
                "database_results": database_result.get("database_results"),
                "used_query_understanding": bool(processed.get("used_query_understanding")),
                "used_reranking": False,
                "used_multi_hop": False,
                "used_features": database_result.get("used_features", {}),
                "route_path": "database",
            }

        retrieval_query = processed.get("retrieval_query") or processed.get("normalized_query") or query
        retrieval = await self.retrieval_orchestrator.retrieve(
            query=retrieval_query,
            collection_name=collection_name,
            top_k=top_k,
            use_reranking=use_reranking,
            use_multi_hop=use_multi_hop,
            additional_search_terms=processed.get("additional_search_terms") or [],
        )
        results = retrieval.get("results", [])

        if not results:
            answer = "متأسفانه اطلاعاتی در مورد این سوال در منابع موجود پیدا نکردم."
            self._add_history(collection_name, original_query, answer, conversation_id)
            return {
                "success": False,
                "answer": answer,
                "top_results": [],
                "top_score": 0.0,
                "confidence": 0.0,
                "metadata": {"orchestrated": True, "query_processing": processed},
                "used_query_understanding": bool(processed.get("used_query_understanding")),
                "used_reranking": retrieval.get("used_reranking", False),
                "used_multi_hop": retrieval.get("used_multi_hop", False),
                "route_path": retrieval.get("route_path", "rag"),
            }

        context_prompt, system_prompt = self.answer_generator.build_context_prompt(
            query=original_query,
            collection_name=collection_name,
            top_results=results,
            conversation_id=conversation_id,
        )

        response = await self.qwen_client.generate_text(
            prompt=context_prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )
        answer = self._extract_text(response)
        if not answer:
            answer = self._fallback_answer(results)

        self._add_history(collection_name, original_query, answer, conversation_id)
        top_score = self._score(results[0]) if results else 0.0

        return {
            "success": True,
            "answer": answer,
            "top_results": results,
            "top_score": top_score,
            "confidence": min(top_score, 1.0),
            "metadata": {
                "orchestrated": True,
                "query_processing": processed,
                "multi_hop_analysis": retrieval.get("multi_hop_analysis"),
            },
            "used_query_understanding": bool(processed.get("used_query_understanding")),
            "used_reranking": retrieval.get("used_reranking", False),
            "used_multi_hop": retrieval.get("used_multi_hop", False),
            "route_path": retrieval.get("route_path", "rag"),
        }

    async def retrieve_and_answer_stream(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        result = await self.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            use_reranking=use_reranking,
            use_multi_hop=use_multi_hop,
            conversation_id=conversation_id,
        )
        if not result.get("success"):
            yield {**result, "chunk": result.get("answer", ""), "done": True}
            return

        answer = result.get("answer", "")
        words = answer.split()
        for idx, word in enumerate(words):
            yield {
                **result,
                "chunk": word + " ",
                "full_response": " ".join(words[: idx + 1]),
                "done": idx == len(words) - 1,
            }

    def _get_domain_info(self, collection_name: str) -> Dict[str, Any]:
        try:
            return self.collection_manager.get_collection_domain(collection_name)
        except Exception:
            return {"domain": "general", "confidence": 0.5}

    async def _try_database_first(
        self,
        query: str,
        collection_name: str,
        top_k: int,
        conversation_id: Optional[str],
        processed: Dict[str, Any],
        domain_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if self.database_handler is None:
            return None

        try:
            return await self.database_handler.try_database_before_rag(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                conversation_id=conversation_id,
                build_metadata=self._build_metadata,
                used_query_understanding=bool(processed.get("used_query_understanding")),
                query_analysis=processed.get("query_analysis"),
                streaming=False,
                collection_metadata=domain_info,
            )
        except Exception as e:
            logger.warning(f"Database-first route failed, falling back to RAG: {e}")
            return None

    def _build_metadata(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        metadata = {"orchestrated": True}
        if extra:
            metadata.update(extra)
        return metadata

    def _build_database_answer(
        self,
        query: str,
        collection_name: str,
        database_results: Dict[str, Any],
    ) -> str:
        try:
            if collection_name == "budget_financial":
                from services.field_specific_answer_generator import get_field_answer_generator
                generator = get_field_answer_generator()
                return generator.format_answer_with_specific_field(
                    user_query=query,
                    database_results=database_results,
                    collection_name=collection_name,
                )
        except Exception as e:
            logger.debug(f"Field-specific database answer failed: {e}")

        rows = database_results.get("rows") or database_results.get("results") or []
        if not rows:
            return "متأسفانه داده‌ای برای این سوال در پایگاه داده یافت نشد."

        first_row = rows[0]
        if isinstance(first_row, dict) and "total_amount" in first_row:
            try:
                value = float(str(first_row["total_amount"]).replace(",", ""))
                return f"نتیجه محاسبه پایگاه داده برای سوال شما **{value:,.0f}** میلیون ریال است."
            except Exception:
                return f"نتیجه محاسبه پایگاه داده: **{first_row['total_amount']}**"

        preview = []
        for row in rows[:5]:
            if isinstance(row, dict):
                preview.append("، ".join(f"{key}: {value}" for key, value in list(row.items())[:5]))
        return "نتایج پایگاه داده:\n" + "\n".join(f"- {item}" for item in preview)

    def _add_history(
        self,
        collection_name: str,
        query: str,
        answer: str,
        conversation_id: Optional[str],
    ) -> None:
        try:
            self.chat_manager.add_to_chat_history(
                collection_name,
                query,
                answer,
                conversation_id,
            )
        except Exception as e:
            logger.debug(f"Could not update chat history: {e}")

    def _extract_text(self, response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, str):
            return response.strip()
        for attr in ("text", "content"):
            value = getattr(response, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _fallback_answer(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "متأسفانه نتوانستم پاسخ مناسبی تولید کنم."
        text = results[0].get("text") or results[0].get("content") or ""
        return text[:700] if text else "متأسفانه نتوانستم پاسخ مناسبی تولید کنم."

    def _score(self, result: Dict[str, Any]) -> float:
        score = (
            result.get("final_score")
            or result.get("rerank_score")
            or result.get("hybrid_score")
            or result.get("score")
            or 0.0
        )
        try:
            return float(score)
        except Exception:
            return 0.0
