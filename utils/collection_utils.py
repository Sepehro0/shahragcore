# -*- coding: utf-8 -*-
"""
Collection Utilities Module
ابزارهای مدیریت collections و domain detection
"""

import json
import logging
from typing import Dict, Any, List, Optional
import chromadb

from processors.document_domain_classifier import DocumentDomain
from utils.text_utils import TextNormalizer

logger = logging.getLogger(__name__)


class CollectionManager:
    """مدیریت collections و domain information"""
    
    def __init__(self, chroma_client: chromadb.Client):
        """
        Args:
            chroma_client: ChromaDB client instance
        """
        self.chroma_client = chroma_client
        
        # Default mappings
        self.default_keywords_map = {
            DocumentDomain.FINANCIAL: ["بودجه", "مالی", "هزینه", "اعتبار", "درآمد"],
            DocumentDomain.EDUCATIONAL: ["آموزشی", "دانش", "درس", "تحقیق"],
            DocumentDomain.TECHNICAL: ["فنی", "مهندسی", "سیستم", "فناوری"],
            DocumentDomain.GENERAL: []
        }
        
        self.default_summary_map = {
            DocumentDomain.FINANCIAL: "مجموعه‌ای از داده‌های مالی و بودجه‌ای شامل جداول ارقام و اعتبارات.",
            DocumentDomain.EDUCATIONAL: "محصولی آموزشی شامل دستورالعمل‌ها و توضیحات ساختاری.",
            DocumentDomain.TECHNICAL: "مستندات فنی و راهنمای پیاده‌سازی یا راه‌اندازی سیستم‌ها.",
            DocumentDomain.GENERAL: "محتوای عمومی با ترکیبی از متون و داده‌ها."
        }
    
    def get_collection_domain(self, collection_name: str) -> Dict[str, Any]:
        """
        بازیابی اطلاعات domain از collection metadata
        
        Returns:
            {
                'domain': str,
                'confidence': float,
                'summary': str,
                'keywords': List[str],
                'method': str
            }
        """
        try:
            collection = self.chroma_client.get_collection(collection_name)
            metadata = collection.metadata or {}
            
            # استخراج domain info از metadata
            domain_type = metadata.get('domain_type')
            domain_confidence = float(metadata.get('domain_confidence', '0.5'))
            method = metadata.get('domain_method')
            lowered_name = (collection_name or "").lower()
            
            # اگر domain_type وجود ندارد، بر اساس نام collection حدس بزن
            if not domain_type:
                method = 'name_heuristic'
                if any(token in lowered_name for token in ['budget', 'financial', 'finance', 'malieh', 'mali', 'بودجه', 'مالی']):
                    domain_type = DocumentDomain.FINANCIAL
                    domain_confidence = max(domain_confidence, 0.9)
                elif any(token in lowered_name for token in ['educational', 'rag', 'guide', 'tutorial', 'آموزشی']):
                    domain_type = DocumentDomain.EDUCATIONAL
                    domain_confidence = max(domain_confidence, 0.85)
                elif any(token in lowered_name for token in ['technical', 'tech', 'engineer', 'فنی']):
                    domain_type = DocumentDomain.TECHNICAL
                    domain_confidence = max(domain_confidence, 0.6)
                else:
                    domain_type = DocumentDomain.GENERAL
                    domain_confidence = max(domain_confidence, 0.6)
            
            document_summary = metadata.get('document_summary', '')
            
            # Parse keywords از JSON
            keywords = []
            keywords_json = metadata.get('domain_keywords', '[]')
            try:
                keywords = json.loads(keywords_json)
            except:
                pass
            
            if not keywords:
                keywords = self.default_keywords_map.get(domain_type, [])[:6]
            if not document_summary:
                document_summary = self.default_summary_map.get(domain_type, '')
            if not method:
                method = 'name_heuristic'
            
            logger.info(f"📂 Collection domain: {domain_type} (confidence: {domain_confidence:.2f})")
            
            return {
                'domain': domain_type,
                'confidence': domain_confidence,
                'summary': document_summary,
                'keywords': keywords,
                'method': method
            }
                
        except Exception as e:
            logger.warning(f"Could not retrieve domain info for collection {collection_name}: {e}")
            # Fallback: بر اساس نام collection حدس بزن
            return self._guess_domain_from_name(collection_name)
    
    def _guess_domain_from_name(self, collection_name: str) -> Dict[str, Any]:
        """حدس زدن domain بر اساس نام collection"""
        lowered_name = (collection_name or "").lower()
        
        if any(token in lowered_name for token in ['budget', 'financial', 'finance', 'malieh', 'mali', 'بودجه', 'مالی']):
            guessed_domain = DocumentDomain.FINANCIAL
        elif any(token in lowered_name for token in ['educational', 'rag', 'guide', 'tutorial', 'آموزشی']):
            guessed_domain = DocumentDomain.EDUCATIONAL
        elif any(token in lowered_name for token in ['technical', 'tech', 'engineer', 'فنی']):
            guessed_domain = DocumentDomain.TECHNICAL
        else:
            guessed_domain = DocumentDomain.GENERAL
        
        return {
            'domain': guessed_domain,
            'confidence': 0.6 if guessed_domain == DocumentDomain.FINANCIAL else 0.4,
            'summary': self.default_summary_map.get(guessed_domain, ''),
            'keywords': self.default_keywords_map.get(guessed_domain, [])[:6],
            'method': 'guessed'
        }
    
    def get_collections(self) -> List[str]:
        """دریافت لیست تمام collections"""
        try:
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def get_structure_summary(self, collection_name: str) -> Optional[Dict]:
        """دریافت خلاصه ساختار collection"""
        try:
            collection = self.chroma_client.get_collection(collection_name)
            count = collection.count()
            metadata = collection.metadata or {}
            
            return {
                'name': collection_name,
                'count': count,
                'metadata': metadata
            }
        except Exception as e:
            logger.warning(f"Could not get structure summary for {collection_name}: {e}")
            return None
    
    def extract_keywords(self, query: str) -> List[str]:
        """استخراج کلمات کلیدی از query"""
        # Simple keyword extraction - can be enhanced
        text_normalizer = TextNormalizer()
        words = query.split()
        
        # Define stopwords
        stopwords = {"برای", "در", "از", "به", "و", "یا", "که", "چه", "چطور", "چگونه"}
        
        # Filter out stopwords and short words
        keywords = [
            word for word in words 
            if len(word) > 2 and word not in stopwords
        ]
        return keywords[:10]  # Limit to top 10

