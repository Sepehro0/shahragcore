# -*- coding: utf-8 -*-
"""
BGE Reranker Service Client
کلاینت سرویس BGE Reranker
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
import json

logger = logging.getLogger(__name__)


@dataclass
class RerankRequest:
    """درخواست rerank"""
    query: str
    documents: List[str]
    top_k: Optional[int] = None


@dataclass
class RerankResult:
    """نتیجه rerank"""
    document: str
    score: float
    index: int


@dataclass
class RerankResponse:
    """پاسخ rerank"""
    results: List[RerankResult]
    success: bool
    error: Optional[str] = None


class RerankerClient:
    """کلاینت BGE Reranker Service"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8004",
                 timeout: int = 30,
                 max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        
        logger.info(f"RerankerClient initialized: {self.base_url}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """اطمینان از وجود session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Enhanced-RAG-System/1.0"
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def close(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _rate_limit(self):
        """Rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def rerank(self, 
                     query: str, 
                     documents: List[str], 
                     top_k: Optional[int] = None) -> RerankResponse:
        """Rerank کردن اسناد"""
        await self._ensure_session()
        await self._rate_limit()
        
        # Prepare request
        request_data = {
            "query": query,
            "documents": documents
        }
        
        if top_k is not None:
            request_data["top_k"] = top_k
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/rerank",
                    json=request_data
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Parse results
                        results = []
                        for item in result.get("results", []):
                            results.append(RerankResult(
                                document=item.get("document", ""),
                                score=item.get("score", 0.0),
                                index=item.get("index", 0)
                            ))
                        
                        return RerankResponse(
                            results=results,
                            success=True
                        )
                    
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"
                        logger.error(error_msg)
                        last_error = error_msg
                        
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        
                        return RerankResponse(
                            results=[],
                            success=False,
                            error=error_msg
                        )
            
            except asyncio.TimeoutError:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.error(error_msg)
                last_error = error_msg
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except Exception as e:
                error_msg = f"Request failed: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        # All retries failed
        return RerankResponse(
            results=[],
            success=False,
            error=last_error or "All retries failed"
        )
    
    async def rerank_documents(self, 
                               query: str, 
                               documents: List[Dict[str, Any]], 
                               top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Rerank کردن اسناد با metadata"""
        # Extract text content
        doc_texts = []
        for doc in documents:
            if isinstance(doc, dict):
                text = doc.get('content', doc.get('text', ''))
            else:
                text = str(doc)
            doc_texts.append(text)
        
        # Rerank
        response = await self.rerank(query, doc_texts, top_k)
        
        if not response.success:
            logger.error(f"Reranking failed: {response.error}")
            return documents  # Return original order
        
        # Reorder documents based on rerank results
        reranked_docs = []
        for result in response.results:
            if result.index < len(documents):
                doc = documents[result.index].copy() if isinstance(documents[result.index], dict) else documents[result.index]
                if isinstance(doc, dict):
                    doc['rerank_score'] = result.score
                reranked_docs.append(doc)
        
        return reranked_docs
    
    async def health_check(self) -> bool:
        """بررسی سلامت سرویس"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "session_active": self.session is not None and not self.session.closed
        }


# Global reranker client instance
reranker_client = RerankerClient()
