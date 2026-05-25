# -*- coding: utf-8 -*-
"""
Embedding Manager
مدیر embeddings
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
from collections import defaultdict

from services.jina_client import JinaClient
from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingCache:
    """Cache برای embeddings"""
    text: str
    embedding: List[float]
    timestamp: float
    task: str


class EmbeddingManager:
    """مدیر embeddings با cache و batch processing"""
    
    def __init__(self, config: Settings):
        self.config = config
        self.jina_client = JinaClient(
            base_url=config.services.jina_url,
            api_key=config.services.jina_api_key
        )
        
        # Cache settings
        self.cache = {}
        self.cache_size = 1000
        self.cache_ttl = 3600  # 1 hour
        
        # Batch processing
        self.batch_size = 100
        self.batch_delay = 0.1  # 100ms between batches
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_requests': 0,
            'error_count': 0
        }
    
    async def generate_embedding(self, text: str, task: str = "retrieval.query") -> List[float]:
        """تولید embedding برای یک متن"""
        try:
            self.stats['total_requests'] += 1
            
            # Check cache
            cache_key = f"{text}_{task}"
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if time.time() - cached.timestamp < self.cache_ttl:
                    self.stats['cache_hits'] += 1
                    return cached.embedding
                else:
                    # Remove expired cache entry
                    del self.cache[cache_key]
            
            self.stats['cache_misses'] += 1
            
            # Generate embedding
            response = await self.jina_client.generate_embedding(text, task)
            
            if response.success and response.embeddings:
                embedding = response.embeddings[0]
                
                # Cache the result
                self._add_to_cache(cache_key, text, embedding, task)
                
                return embedding
            else:
                logger.error(f"Embedding generation failed: {response.error}")
                self.stats['error_count'] += 1
                return []
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            self.stats['error_count'] += 1
            return []
    
    async def generate_embeddings_batch(self, texts: List[str], 
                                       task: str = "retrieval.document") -> List[List[float]]:
        """تولید embeddings برای دسته‌ای از متون"""
        try:
            self.stats['batch_requests'] += 1
            
            # Check cache first
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = f"{text}_{task}"
                if cache_key in self.cache:
                    cached = self.cache[cache_key]
                    if time.time() - cached.timestamp < self.cache_ttl:
                        cached_embeddings.append((i, cached.embedding))
                        continue
                    else:
                        del self.cache[cache_key]
                
                uncached_texts.append(text)
                uncached_indices.append(i)
            
            # Generate embeddings for uncached texts
            all_embeddings = [None] * len(texts)
            
            # Add cached embeddings
            for i, embedding in cached_embeddings:
                all_embeddings[i] = embedding
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                # Process in batches
                for i in range(0, len(uncached_texts), self.batch_size):
                    batch_texts = uncached_texts[i:i + self.batch_size]
                    batch_indices = uncached_indices[i:i + self.batch_size]
                    
                    response = await self.jina_client.batch_embeddings(batch_texts, task)
                    
                    if response.success and response.embeddings:
                        for j, embedding in enumerate(response.embeddings):
                            if j < len(batch_indices):
                                idx = batch_indices[j]
                                all_embeddings[idx] = embedding
                                
                                # Cache the result
                                cache_key = f"{batch_texts[j]}_{task}"
                                self._add_to_cache(cache_key, batch_texts[j], embedding, task)
                    
                    # Delay between batches
                    if i + self.batch_size < len(uncached_texts):
                        await asyncio.sleep(self.batch_delay)
            
            # Filter out None values
            valid_embeddings = [emb for emb in all_embeddings if emb is not None]
            
            return valid_embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            self.stats['error_count'] += 1
            return []
    
    def _add_to_cache(self, cache_key: str, text: str, embedding: List[float], task: str):
        """اضافه کردن به cache"""
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.cache_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        # Add new entry
        self.cache[cache_key] = EmbeddingCache(
            text=text,
            embedding=embedding,
            timestamp=time.time(),
            task=task
        )
    
    def clear_cache(self):
        """پاک کردن cache"""
        self.cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """دریافت آمار cache"""
        total_requests = self.stats['total_requests']
        cache_hits = self.stats['cache_hits']
        cache_misses = self.stats['cache_misses']
        
        hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'max_cache_size': self.cache_size,
            'cache_ttl': self.cache_ttl,
            'total_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'hit_rate': hit_rate,
            'batch_requests': self.stats['batch_requests'],
            'error_count': self.stats['error_count']
        }
    
    async def health_check(self) -> bool:
        """بررسی سلامت سرویس"""
        try:
            return await self.jina_client.health_check()
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        return {
            'jina_client': self.jina_client.get_usage_stats(),
            'cache_stats': self.get_cache_stats(),
            'config': {
                'batch_size': self.batch_size,
                'batch_delay': self.batch_delay,
                'cache_ttl': self.cache_ttl
            }
        }
