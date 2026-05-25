# -*- coding: utf-8 -*-
"""
Jina Embedding Service Client
کلاینت سرویس Jina Embedding
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time
import json

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRequest:
    """درخواست embedding"""
    texts: List[str]
    task: str = "retrieval.query"  # یا "retrieval.document"
    model: str = "jina-embeddings-v2-base-en"


@dataclass
class EmbeddingResponse:
    """پاسخ embedding"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]
    success: bool
    error: Optional[str] = None


class JinaClient:
    """کلاینت Jina Embedding Service"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8080",
                 api_key: str = "qwen-dev-2024-abc123def456",
                 timeout: int = 30,
                 max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        
        logger.info(f"JinaClient initialized: {self.base_url}")
    
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
                "Authorization": f"Bearer {self.api_key}",
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
    
    async def generate_embedding(self, 
                                text: str, 
                                task: str = "retrieval.query",
                                model: str = "jina-embeddings-v2-base-en") -> EmbeddingResponse:
        """تولید embedding برای یک متن"""
        return await self.generate_embeddings([text], task, model)
    
    async def generate_embeddings(self, 
                                 texts: List[str], 
                                 task: str = "retrieval.query",
                                 model: str = "jina-embeddings-v2-base-en") -> EmbeddingResponse:
        """تولید embeddings برای چندین متن"""
        await self._ensure_session()
        await self._rate_limit()
        
        # Prepare request
        request_data = {
            "input": texts,
            "model": model,
            "task": task
        }
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/v1/embeddings",
                    json=request_data
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract embeddings
                        embeddings = []
                        for item in result.get("data", []):
                            embeddings.append(item.get("embedding", []))
                        
                        return EmbeddingResponse(
                            embeddings=embeddings,
                            model=result.get("model", model),
                            usage=result.get("usage", {}),
                            success=True
                        )
                    
                    elif response.status == 401:
                        error_msg = "Authentication failed - check API key"
                        logger.error(error_msg)
                        return EmbeddingResponse(
                            embeddings=[],
                            model=model,
                            usage={},
                            success=False,
                            error=error_msg
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
                        
                        return EmbeddingResponse(
                            embeddings=[],
                            model=model,
                            usage={},
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
        return EmbeddingResponse(
            embeddings=[],
            model=model,
            usage={},
            success=False,
            error=last_error or "All retries failed"
        )
    
    async def generate_embedding_async(self, 
                                      text: str, 
                                      task: str = "retrieval.query") -> List[float]:
        """تولید embedding به صورت async (برای سازگاری)"""
        response = await self.generate_embedding(text, task)
        if response.success and response.embeddings:
            return response.embeddings[0]
        else:
            logger.error(f"Failed to generate embedding: {response.error}")
            return []
    
    async def batch_embeddings(self, 
                              texts: List[str], 
                              batch_size: int = 100,
                              task: str = "retrieval.document") -> List[List[float]]:
        """تولید embeddings به صورت batch"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            response = await self.generate_embeddings(batch_texts, task)
            
            if response.success:
                all_embeddings.extend(response.embeddings)
            else:
                logger.error(f"Batch {i//batch_size + 1} failed: {response.error}")
                # Add empty embeddings for failed batch
                all_embeddings.extend([[] for _ in batch_texts])
        
        return all_embeddings
    
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


class JinaEmbeddingService:
    """سرویس Jina Embedding (برای سازگاری)"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8080",
                 api_key: str = "qwen-dev-2024-abc123def456",
                 timeout: int = 30):
        self.client = JinaClient(base_url, api_key, timeout)
    
    async def generate_embedding(self, text: str, task: str = "retrieval.query") -> List[float]:
        """تولید embedding"""
        response = await self.client.generate_embedding(text, task)
        if response.success and response.embeddings:
            return response.embeddings[0]
        return []
    
    async def generate_embeddings(self, texts: List[str], task: str = "retrieval.query") -> List[List[float]]:
        """تولید embeddings"""
        response = await self.client.generate_embeddings(texts, task)
        if response.success:
            return response.embeddings
        return []
    
    async def health_check(self) -> bool:
        """بررسی سلامت"""
        return await self.client.health_check()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """آمار استفاده"""
        return self.client.get_usage_stats()


# Global Jina client instance
jina_client = JinaClient()
