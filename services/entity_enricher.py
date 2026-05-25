# -*- coding: utf-8 -*-
"""
Entity Enricher
غنی‌سازی entities کوتاه با context از سوال اصلی
"""

import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class EntityEnricher:
    """
    غنی‌سازی entities کوتاه با context
    
    مثال:
    - "باور" → "صندوق باور"
    - "نوآور" → "صندوق نوآور"
    - "جایزه" → "جایزه نوآوری"
    """
    
    def __init__(self):
        """Initialize enricher"""
        
        # الگوهای رایج برای context
        self.context_patterns = {
            'صندوق': ['صندوق', 'فاند'],
            'جایزه': ['جایزه', 'مسابقه'],
            'دوره': ['دوره', 'آموزش', 'کلاس'],
            'شبکه': ['شبکه', 'نتورک'],
            'پروژه': ['پروژه', 'طرح', 'پرژه'],
            'سرمایه': ['سرمایه', 'فاندینگ'],
        }
        
        # واژه‌های معمول در collection
        self.common_prefixes = [
            'صندوق', 'شبکه', 'جایزه', 'دوره', 'پروژه', 'برنامه',
            'سیستم', 'فرآیند', 'خدمات', 'محصول'
        ]
    
    def enrich_entities(self, entities: List[str], original_query: str) -> List[str]:
        """
        غنی‌سازی لیست entities
        
        Args:
            entities: لیست entities استخراج شده
            original_query: سوال اصلی
            
        Returns:
            لیست entities غنی شده
        """
        enriched = []
        
        for entity in entities:
            enriched_entity = self.enrich_single_entity(entity, original_query)
            enriched.append(enriched_entity)
            logger.debug(f"Entity enrichment: '{entity}' → '{enriched_entity}'")
        
        return enriched
    
    def enrich_single_entity(self, entity: str, original_query: str) -> str:
        """
        غنی‌سازی یک entity
        
        استراتژی:
        1. اگر entity خیلی کوتاه است (1 کلمه، < 6 حرف)
        2. context مناسب را از سوال اصلی پیدا کن
        3. entity را با context ترکیب کن
        """
        # اگر entity قبلاً کامل است، تغییری نده
        if len(entity.split()) >= 2:
            return entity
        
        # اگر entity کوتاه است
        if len(entity) < 6 or len(entity.split()) == 1:
            # جستجوی context در سوال اصلی
            context = self._find_context_in_query(entity, original_query)
            if context:
                # ترکیب context + entity
                if entity not in context:  # جلوگیری از تکرار
                    return f"{context} {entity}"
        
        return entity
    
    def _find_context_in_query(self, entity: str, query: str) -> Optional[str]:
        """
        پیدا کردن context مناسب برای entity در سوال
        
        مثال:
        - entity: "باور", query: "تفاوت صندوق نوآور و باور"
        - context: "صندوق" (چون "صندوق نوآور" در query هست)
        """
        query_lower = query.lower()
        entity_lower = entity.lower()
        
        # 1. جستجوی مستقیم context در کنار entity
        for prefix in self.common_prefixes:
            # بررسی اگر "prefix entity" در query وجود دارد
            pattern = rf'{prefix}\s+\w+.*?{entity_lower}'
            if re.search(pattern, query_lower, re.IGNORECASE):
                return prefix
            
            # بررسی اگر entity قبلاً با prefix آمده
            pattern2 = rf'{prefix}\s+{entity_lower}'
            if re.search(pattern2, query_lower, re.IGNORECASE):
                return prefix
        
        # 2. استنتاج context از entities دیگر
        # اگر query "صندوق X و Y" دارد، پس Y هم صندوق است
        comparison_pattern = r'(\w+)\s+(\w+)\s+(?:و|با)\s+(\w+)'
        match = re.search(comparison_pattern, query, re.IGNORECASE)
        if match:
            prefix = match.group(1)  # مثلاً "صندوق"
            entity1 = match.group(2)  # مثلاً "نوآور"
            entity2 = match.group(3)  # مثلاً "باور"
            
            if entity_lower == entity2.lower() and prefix in self.common_prefixes:
                return prefix
        
        # 3. جستجوی context در الگوهای شناخته شده
        for context_key, keywords in self.context_patterns.items():
            if any(kw in query_lower for kw in keywords):
                return context_key
        
        return None
    
    def create_enriched_hops(self, entities: List[str], original_query: str) -> List[Tuple[str, str]]:
        """
        ایجاد hops با entities اصلی و غنی شده
        
        Returns:
            لیست (entity_original, entity_enriched)
        """
        hops = []
        
        for entity in entities:
            enriched = self.enrich_single_entity(entity, original_query)
            hops.append((entity, enriched))
        
        return hops


# Test
if __name__ == "__main__":
    enricher = EntityEnricher()
    
    test_cases = [
        {
            'entities': ['صندوق نوآور', 'باور'],
            'query': 'تفاوت صندوق نوآور و باور چیه؟'
        },
        {
            'entities': ['نوآور', 'باور'],
            'query': 'مقایسه صندوق نوآور با صندوق باور'
        },
        {
            'entities': ['جایزه', 'مسابقه'],
            'query': 'جایزه نوآوری و مسابقه فناوری چه تفاوتی دارند؟'
        },
        {
            'entities': ['شبکه', 'صندوق'],
            'query': 'شبکه تحقیق و توسعه و صندوق باور چه خدماتی دارند؟'
        }
    ]
    
    print("🧪 Testing Entity Enricher\n")
    
    for test in test_cases:
        entities = test['entities']
        query = test['query']
        
        print(f"📝 Query: {query}")
        print(f"   Original entities: {entities}")
        
        enriched = enricher.enrich_entities(entities, query)
        print(f"   Enriched entities: {enriched}")
        print()

