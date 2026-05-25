# -*- coding: utf-8 -*-
"""
Retrieval orchestration for the refactored RAG system.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from search.retrieval_manager import RetrievalManager
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class RetrievalOrchestrator:
    """Coordinate hybrid retrieval, optional multi-hop retrieval, and reranking."""

    def __init__(
        self,
        chroma_client,
        embedding_client=None,
        cache_manager: Optional[CacheManager] = None,
        reranker=None,
        multi_hop_retriever=None,
    ):
        self.chroma_client = chroma_client
        self.cache_manager = cache_manager or CacheManager(chroma_client)
        self.retrieval_manager = RetrievalManager(
            chroma_client=chroma_client,
            embedding_client=embedding_client,
            cache_manager=self.cache_manager,
        )
        self.reranker = reranker
        self.multi_hop_retriever = multi_hop_retriever

    async def retrieve(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        additional_search_terms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return retrieved, deduplicated, optionally reranked results."""
        search_queries = [query]
        used_multi_hop = False
        multi_hop_analysis = None

        if additional_search_terms:
            search_queries.extend([term for term in additional_search_terms if term])

        if use_multi_hop and self.multi_hop_retriever is not None:
            try:
                multi_hop_analysis = self.multi_hop_retriever.analyze_query(query)
                if multi_hop_analysis and multi_hop_analysis.get("requires_multi_hop"):
                    hop_queries = [
                        hop.get("query")
                        for hop in multi_hop_analysis.get("hops", [])
                        if hop.get("query")
                    ]
                    if hop_queries:
                        search_queries = hop_queries
                        used_multi_hop = True
            except Exception as e:
                logger.warning(f"Multi-hop analysis failed, continuing with single query: {e}")

        raw_results: List[Dict[str, Any]] = []
        per_query_k = max(top_k * 2, 8) if used_multi_hop else max(top_k * 3, top_k)
        for search_query in search_queries:
            results = await self.retrieval_manager.hybrid_search(
                query=search_query,
                collection_name=collection_name,
                top_k=per_query_k,
            )
            for result in results:
                result.setdefault("retrieval_query", search_query)
            raw_results.extend(results)

        deduped = self._deduplicate(raw_results)
        deduped.sort(key=self._score, reverse=True)

        used_reranking = False
        if use_reranking and self.reranker is not None and deduped:
            try:
                reranked = self.reranker.rerank_with_fusion(
                    query=query,
                    documents=deduped,
                    top_k=top_k,
                    alpha=0.65,
                )
                if reranked:
                    deduped = reranked
                    used_reranking = True
            except Exception as e:
                logger.warning(f"Reranking failed, using hybrid order: {e}")

        final_results = deduped[:top_k]
        return {
            "results": final_results,
            "used_reranking": used_reranking,
            "used_multi_hop": used_multi_hop,
            "multi_hop_analysis": multi_hop_analysis,
            "route_path": "multi_hop_rag" if used_multi_hop else "rag",
        }

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[str, Dict[str, Any]] = {}
        for result in results:
            key = result.get("id") or f"{result.get('metadata', {}).get('source')}::{hash(result.get('text', ''))}"
            existing = unique.get(key)
            if existing is None or self._score(result) > self._score(existing):
                unique[key] = result
        return list(unique.values())

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
