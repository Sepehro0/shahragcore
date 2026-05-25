# -*- coding: utf-8 -*-
"""
Answer prompt construction for the refactored RAG pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.domain_prompt_generator import DomainPromptGenerator

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Build grounded prompts from retrieved chunks and conversation history."""

    def __init__(
        self,
        qwen_client=None,
        domain_prompt_generator: Optional[DomainPromptGenerator] = None,
        chat_manager=None,
        collection_manager=None,
    ):
        self.qwen_client = qwen_client
        self.domain_prompt_generator = domain_prompt_generator or DomainPromptGenerator()
        self.chat_manager = chat_manager
        self.collection_manager = collection_manager

    def build_context_prompt(
        self,
        query: str,
        collection_name: str,
        top_results: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        preferred_answer: Optional[str] = None,
        preferred_source: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Return ``(user_prompt, system_prompt)`` for LLM generation."""
        context = self._format_context(top_results)
        chat_history = self._get_chat_history(collection_name, conversation_id)
        domain = self._get_domain(collection_name)

        try:
            system_prompt, user_prompt = self.domain_prompt_generator.generate_prompt(
                query=query,
                context=context,
                domain=domain,
                chat_history=chat_history,
                collection_name=collection_name,
                return_system_separate=True,
                preferred_answer=preferred_answer,
                preferred_source=preferred_source,
            )
        except Exception as e:
            logger.warning(f"Domain prompt generation failed, using fallback prompt: {e}")
            system_prompt = (
                "شما یک دستیار RAG هستید. فقط بر اساس متن‌های مرجع پاسخ بدهید. "
                "اگر پاسخ در منابع نبود، صریحاً بگویید اطلاعات کافی وجود ندارد."
            )
            user_prompt = (
                f"متن‌های مرجع:\n{context}\n\n"
                f"سوال کاربر:\n{query}\n\n"
                "پاسخ را دقیق، فارسی، و متکی به منابع بنویس."
            )

        return user_prompt, system_prompt

    def _format_context(self, top_results: List[Dict[str, Any]]) -> str:
        if not top_results:
            return "هیچ متن مرتبطی بازیابی نشد."

        parts: List[str] = []
        for idx, result in enumerate(top_results, 1):
            text = result.get("text") or result.get("content") or result.get("document") or ""
            metadata = result.get("metadata") or {}
            score = (
                result.get("final_score")
                or result.get("rerank_score")
                or result.get("hybrid_score")
                or result.get("score")
                or 0.0
            )
            source = (
                metadata.get("source")
                or metadata.get("source_file")
                or metadata.get("source_url")
                or metadata.get("filename")
                or ""
            )
            location = metadata.get("page") or metadata.get("row_index") or metadata.get("sheet_name") or ""

            header = f"### سند {idx}"
            if source:
                header += f" | منبع: {source}"
            if location:
                header += f" | موقعیت: {location}"
            header += f" | score: {float(score):.3f}" if isinstance(score, (int, float)) else ""

            parts.append(f"{header}\n{text}")

        return "\n\n".join(parts)

    def _get_chat_history(
        self,
        collection_name: str,
        conversation_id: Optional[str],
    ) -> List[Dict[str, str]]:
        if not self.chat_manager:
            return []
        try:
            return self.chat_manager.get_chat_history(
                collection_name,
                max_messages=5,
                conversation_id=conversation_id,
            )
        except Exception as e:
            logger.debug(f"Could not load chat history: {e}")
            return []

    def _get_domain(self, collection_name: str) -> str:
        if not self.collection_manager:
            return "general"
        try:
            domain_info = self.collection_manager.get_collection_domain(collection_name)
            domain = domain_info.get("domain", "general")
            return getattr(domain, "value", domain)
        except Exception:
            return "general"
