# -*- coding: utf-8 -*-
"""
Enhanced Comparison System - سیستم پیشرفته تشخیص و پردازش مقایسه‌ها
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """پیچیدگی سوال"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class ComparisonPair:
    """جفت entities برای مقایسه"""
    entity1: str
    entity2: str
    confidence: float
    pattern_used: str
    
    def __str__(self):
        return f"{self.entity1} vs {self.entity2} (confidence: {self.confidence:.2f})"


class EnhancedComparisonDetector:
    """
    تشخیص‌دهنده پیشرفته سوالات مقایسه‌ای 🎯
    
    ویژگی‌ها:
    - 5 الگوی regex مختلف
    - fallback برای حالات پیچیده
    - اعتبارسنجی entities
    """
    
    def __init__(self):
        # الگوهای مقایسه به ترتیب اولویت
        self.comparison_patterns = [
            # الگو 1: تفاوت X و Y
            {
                'pattern': r'(?:تفاوت|فرق)\s+(?:بین\s+)?(.+?)\s+(?:و|با)\s+(.+?)(?:\s+چیست|\s+چیه|\s+چه\s+تفاوتی|\s*[\?؟]|$)',
                'priority': 1,
                'name': 'tafavot_pattern'
            },
            # الگو 2: مقایسه X و Y
            {
                'pattern': r'مقایسه\s+(?:بین\s+)?(.+?)\s+(?:و|با)\s+(.+?)(?:\s+[\?؟]|$)',
                'priority': 2,
                'name': 'moghayese_pattern'
            },
            # الگو 3: X و Y چه تفاوتی دارند
            {
                'pattern': r'(.+?)\s+(?:و|با)\s+(.+?)\s+چه\s+(?:تفاوتی|فرقی)\s+دارند',
                'priority': 1,
                'name': 'tafavot_darand_pattern'
            },
            # الگو 4: X بهتر است یا Y
            {
                'pattern': r'(.+?)\s+بهتر\s+است\s+یا\s+(.+?)(?:\s*[\?؟]|$)',
                'priority': 3,
                'name': 'behtar_pattern'
            },
            # الگو 5: X در مقابل Y
            {
                'pattern': r'(.+?)\s+در\s+مقابل\s+(.+?)(?:\s*[\?؟]|$)',
                'priority': 2,
                'name': 'dar_moghabel_pattern'
            }
        ]
        
        # کلیدواژه‌های مقایسه برای fallback
        self.comparison_keywords = [
            'تفاوت', 'فرق', 'مقایسه', 'بهتر', 'بیشتر', 'کمتر',
            'در مقابل', 'نسبت به', 'چه فرقی', 'چه تفاوتی'
        ]
    
    def detect(self, query: str) -> Optional[ComparisonPair]:
        """
        تشخیص سوال مقایسه‌ای و استخراج entities
        
        Returns:
            ComparisonPair اگر سوال مقایسه‌ای بود، وگرنه None
        """
        query = query.strip()
        
        # تلاش با الگوهای regex
        for pattern_info in self.comparison_patterns:
            match = re.search(pattern_info['pattern'], query, re.IGNORECASE)
            if match:
                entity1_raw = match.group(1).strip()
                entity2_raw = match.group(2).strip()
                
                # پاکسازی entities
                entity1 = self._cleanup_entity(entity1_raw)
                entity2 = self._cleanup_entity(entity2_raw)
                
                # اعتبارسنجی
                if self._validate_entities(entity1, entity2):
                    confidence = 1.0 if pattern_info['priority'] == 1 else 0.9
                    pair = ComparisonPair(
                        entity1=entity1,
                        entity2=entity2,
                        confidence=confidence,
                        pattern_used=pattern_info['name']
                    )
                    logger.info(f"✅ Comparison detected: {pair}")
                    return pair
        
        # Fallback: تشخیص با کلیدواژه
        if any(kw in query for kw in self.comparison_keywords):
            entities = self._extract_entities_fallback(query)
            if entities and len(entities) >= 2:
                pair = ComparisonPair(
                    entity1=entities[0],
                    entity2=entities[1],
                    confidence=0.7,
                    pattern_used='fallback'
                )
                logger.info(f"⚠️ Comparison detected (fallback): {pair}")
                return pair
        
        logger.debug(f"❌ No comparison detected in: {query}")
        return None
    
    def _cleanup_entity(self, entity: str) -> str:
        """پاکسازی entity از کلمات اضافی و enrichment"""
        # حذف کلیدواژه‌های مقایسه
        entity = re.sub(r'^(?:تفاوت|فرق|مقایسه|بین)\s+', '', entity, flags=re.IGNORECASE)
        
        # ⚠️ حذف کلمات محاوره‌ای و اضافی از انتها
        entity = re.sub(r'\s+(?:چیست|چیه|چیا|هستش|هستند|است|هست|دارد|دارند|چه|تفاوتی|فرقی|چی|چه هستند|چیان).*$', '', entity, flags=re.IGNORECASE)
        
        # حذف نشانه‌گذاری
        entity = re.sub(r'[؟،.\?!]', '', entity)
        
        # نرمال‌سازی فاصله‌ها
        entity = re.sub(r'\s+', ' ', entity).strip()
        
        # ⚠️ Entity Enrichment: اگر فقط نام کوتاه است، پیشوند "صندوق" اضافه کن
        known_funds = {
            'باور': 'صندوق باور',
            'نوآور': 'صندوق نوآور',
            'دانشمند': 'موسسه دانشمند'
        }
        entity_lower = entity.lower()
        for short_name, full_name in known_funds.items():
            if entity_lower == short_name or entity_lower == short_name.strip():
                entity = full_name
                break
        
        return entity
    
    def _validate_entities(self, entity1: str, entity2: str) -> bool:
        """اعتبارسنجی entities"""
        # بررسی طول
        if not entity1 or not entity2:
            return False
        
        if len(entity1) < 2 or len(entity2) < 2:
            return False
        
        # بررسی تکراری نبودن
        if entity1.lower() == entity2.lower():
            return False
        
        # بررسی طول معقول (نه خیلی کوتاه، نه خیلی بلند)
        if len(entity1.split()) > 6 or len(entity2.split()) > 6:
            return False
        
        return True
    
    def _extract_entities_fallback(self, query: str) -> List[str]:
        """استخراج entities با روش fallback (تقسیم با 'و')"""
        # حذف کلیدواژه‌های مقایسه
        for kw in self.comparison_keywords:
            query = query.replace(kw, '')
        
        # تقسیم با 'و'
        if ' و ' in query:
            parts = query.split(' و ')
            entities = []
            for part in parts[:2]:  # فقط 2 تا اول
                cleaned = self._cleanup_entity(part)
                if cleaned and len(cleaned) >= 2:
                    entities.append(cleaned)
            return entities
        
        return []


class EnhancedEntityExtractor:
    """
    استخراج‌کننده پیشرفته entities 🌟
    
    ویژگی‌ها:
    - لیست entities شناخته‌شده
    - الگوهای compound (صندوق + نوآور)
    - غنی‌سازی entities کوتاه
    """
    
    def __init__(self):
        # لیست entities شناخته‌شده
        self.known_entities = {
            'صندوق نوآور': ['نوآور', 'صندوق نوآور'],
            'صندوق باور': ['باور', 'صندوق باور'],
            'موسسه دانشمند': ['موسسه دانشمند', 'دانشمند'],
            'شبکه تحقیق و توسعه': ['شبکه تحقیق', 'شبکه توسعه', 'شبکه تحقیق و توسعه'],
            'جایزه نوآوری': ['جایزه نوآوری', 'جایزه فناوری'],
            'جایزه مدیریت نوآوری': ['جایزه مدیریت', 'مدیریت نوآوری']
        }
        
        # الگوهای compound
        self.compound_patterns = [
            (r'صندوق\s+(\w+)', 'صندوق'),  # صندوق + X
            (r'(\w+)\s+صندوق', 'صندوق'),  # X + صندوق
            (r'موسسه\s+(\w+)', 'موسسه'),
            (r'جایزه\s+(\w+)', 'جایزه'),
            (r'شبکه\s+(\w+)', 'شبکه')
        ]
    
    def extract_and_enrich(self, entities: List[str], query: str) -> List[str]:
        """
        استخراج و غنی‌سازی entities
        
        Args:
            entities: لیست entities اولیه
            query: سوال اصلی (برای context)
            
        Returns:
            لیست entities غنی‌شده
        """
        enriched = []
        
        for entity in entities:
            enriched_entity = self._enrich_entity(entity, query)
            enriched.append(enriched_entity)
        
        logger.info(f"🌟 Entity enrichment: {entities} → {enriched}")
        return enriched
    
    def _enrich_entity(self, entity: str, query: str) -> str:
        """غنی‌سازی یک entity"""
        entity_lower = entity.lower()
        query_lower = query.lower()
        
        # 1. بررسی entities شناخته‌شده
        for canonical, variants in self.known_entities.items():
            for variant in variants:
                if variant.lower() == entity_lower:
                    # اگر entity قبلاً کامل است (مثل "صندوق نوآور")، همان را برگردان
                    if entity_lower == canonical.lower():
                        return canonical
                    
                    # اگر entity کوتاه است (مثل "باور")، از canonical استفاده کن
                    if len(entity.split()) == 1:
                        # بررسی اگر prefix canonical در query وجود دارد
                        # مثلاً برای "باور" → "صندوق باور"، چک کن که "صندوق" در query هست
                        canonical_parts = canonical.lower().split()
                        prefix_in_query = any(part in query_lower for part in canonical_parts[:-1])
                        
                        if prefix_in_query or canonical.lower() in query_lower:
                            logger.debug(f"🌟 Enriching '{entity}' → '{canonical}' (prefix in query)")
                            return canonical
                        
                        # fallback: اگر هیچکدام نبود، سعی کن با compound enrichment
                        return self._try_compound_enrichment(entity, query)
        
        # 2. تلاش برای غنی‌سازی با الگوهای compound
        if len(entity.split()) == 1:
            enriched = self._try_compound_enrichment(entity, query)
            if enriched != entity:
                return enriched
        
        # 3. اگر هیچکدام نتوانست غنی کند، entity اصلی را برگردان
        return entity
    
    def _try_compound_enrichment(self, entity: str, query: str) -> str:
        """تلاش برای غنی‌سازی با الگوهای compound"""
        query_lower = query.lower()
        entity_lower = entity.lower()
        
        # بررسی اگر entity + کلیدواژه در query هست
        prefixes = ['صندوق', 'موسسه', 'جایزه', 'شبکه']
        
        for prefix in prefixes:
            # بررسی "prefix entity"
            compound1 = f"{prefix} {entity_lower}"
            if compound1 in query_lower:
                return f"{prefix} {entity}"
            
            # بررسی "entity prefix"
            compound2 = f"{entity_lower} {prefix}"
            if compound2 in query_lower:
                return f"{entity} {prefix}"
        
        return entity


class ImprovedMultiHopAnalyzer:
    """
    تحلیل‌گر بهبود یافته Multi-Hop 🧠
    
    ویژگی‌ها:
    - ترکیب detector و extractor
    - confidence scoring
    - reasoning برای توضیح تصمیمات
    """
    
    def __init__(self):
        self.comparison_detector = EnhancedComparisonDetector()
        self.entity_extractor = EnhancedEntityExtractor()
        
        # کلیدواژه‌های aggregation
        self.aggregation_keywords = ['تمام', 'همه', 'لیست', 'انواع', 'جمع', 'مجموع', 'کل']
        
        # کلیدواژه‌های procedural
        self.procedural_keywords = ['چگونه', 'چطور', 'نحوه', 'روش', 'فرآیند', 'مراحل']
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """
        تحلیل جامع سوال
        
        Returns:
            {
                'type': str,  # comparison, multi_entity, aggregation, procedural, factual
                'requires_multi_hop': bool,
                'entities': List[str],
                'estimated_rows': int,
                'confidence': float,
                'reasoning': str,
                'comparison_pair': Optional[ComparisonPair],
                'complexity': QueryComplexity
            }
        """
        query_lower = query.lower()
        reasoning_parts = []
        
        # 1. تشخیص comparison
        comparison_pair = self.comparison_detector.detect(query)
        if comparison_pair:
            # غنی‌سازی entities
            enriched_entities = self.entity_extractor.extract_and_enrich(
                [comparison_pair.entity1, comparison_pair.entity2],
                query
            )
            
            return {
                'type': 'comparison',
                'requires_multi_hop': True,
                'entities': enriched_entities,
                'estimated_rows': 4,
                'confidence': comparison_pair.confidence,
                'reasoning': f"سوال مقایسه‌ای تشخیص داده شد با الگوی {comparison_pair.pattern_used}",
                'comparison_pair': ComparisonPair(
                    entity1=enriched_entities[0],
                    entity2=enriched_entities[1],
                    confidence=comparison_pair.confidence,
                    pattern_used=comparison_pair.pattern_used
                ),
                'complexity': QueryComplexity.COMPLEX
            }
        
        # 2. تشخیص aggregation
        if any(kw in query_lower for kw in self.aggregation_keywords):
            reasoning_parts.append("کلیدواژه aggregation یافت شد")
            return {
                'type': 'aggregation',
                'requires_multi_hop': True,
                'entities': self._extract_simple_entities(query),
                'estimated_rows': 6,
                'confidence': 0.8,
                'reasoning': ' | '.join(reasoning_parts),
                'comparison_pair': None,
                'complexity': QueryComplexity.MODERATE
            }
        
        # 3. تشخیص multi-part (سوالات چندبخشی با ؟)
        question_marks = query.count('؟')
        if question_marks >= 2:
            sub_questions = self._split_multi_part_query(query)
            if len(sub_questions) >= 2:
                entities = []
                for sq in sub_questions:
                    entities.extend(self._extract_simple_entities(sq))
                reasoning_parts.append(f"{len(sub_questions)} sub-question یافت شد")
                return {
                    'type': 'multi_part',
                    'requires_multi_hop': True,
                    'entities': entities,
                    'estimated_rows': len(sub_questions) * 2,
                    'confidence': 0.9,
                    'reasoning': ' | '.join(reasoning_parts),
                    'comparison_pair': None,
                    'complexity': QueryComplexity.COMPLEX,
                    'sub_questions': sub_questions
                }
        
        # 4. تشخیص procedural
        if any(kw in query_lower for kw in self.procedural_keywords):
            reasoning_parts.append("کلیدواژه procedural یافت شد")
            return {
                'type': 'procedural',
                'requires_multi_hop': False,
                'entities': self._extract_simple_entities(query),
                'estimated_rows': 3,
                'confidence': 0.75,
                'reasoning': ' | '.join(reasoning_parts),
                'comparison_pair': None,
                'complexity': QueryComplexity.MODERATE
            }
        
        # 5. تشخیص multi-entity (چند 'و' در سوال)
        if query.count(' و ') >= 2:
            entities = self._extract_simple_entities(query)
            if len(entities) >= 2:
                reasoning_parts.append(f"{len(entities)} entity یافت شد")
                return {
                    'type': 'multi_entity',
                    'requires_multi_hop': True,
                    'entities': entities,
                    'estimated_rows': len(entities) * 2,
                    'confidence': 0.85,
                    'reasoning': ' | '.join(reasoning_parts),
                    'comparison_pair': None,
                    'complexity': QueryComplexity.COMPLEX
                }
        
        # 5. سوال ساده (factual)
        reasoning_parts.append("سوال ساده factual")
        return {
            'type': 'factual',
            'requires_multi_hop': False,
            'entities': self._extract_simple_entities(query),
            'estimated_rows': 1,
            'confidence': 0.6,
            'reasoning': ' | '.join(reasoning_parts),
            'comparison_pair': None,
            'complexity': QueryComplexity.SIMPLE
        }
    
    def _split_multi_part_query(self, query: str) -> List[str]:
        """تقسیم سوال چندبخشی به sub-questions"""
        # تقسیم بر اساس ؟
        parts = query.split('؟')
        
        sub_questions = []
        for part in parts:
            part = part.strip()
            if part and len(part) > 5:  # حداقل 5 کاراکتر
                # اگر ؟ نداشت، اضافه کن
                if not part.endswith('؟'):
                    part += '؟'
                sub_questions.append(part)
        
        return sub_questions
    
    def _extract_simple_entities(self, query: str) -> List[str]:
        """استخراج ساده entities از سوال"""
        # حذف کلمات stop
        stop_words = ['چیست', 'چیه', 'چگونه', 'چطور', 'است', 'هست', 'دارد', 'دارند', 
                      'میتونم', 'میتوانم', 'باید', 'باشد', 'به', 'از', 'در', 'را', 'که', 'آیا', 'ایا']
        
        words = query.split()
        entities = []
        current_entity = []
        
        for word in words:
            clean_word = re.sub(r'[؟،.\?!]', '', word).strip()
            if clean_word and clean_word not in stop_words and len(clean_word) > 1:
                current_entity.append(clean_word)
            elif current_entity:
                entities.append(' '.join(current_entity))
                current_entity = []
        
        if current_entity:
            entities.append(' '.join(current_entity))
        
        # فیلتر entities خیلی بلند
        entities = [e for e in entities if len(e.split()) <= 5]
        
        return entities[:3]  # حداکثر 3 entity


# ===== تست =====
if __name__ == "__main__":
    print("🧪 Testing Enhanced Comparison System...\n")
    
    detector = EnhancedComparisonDetector()
    extractor = EnhancedEntityExtractor()
    analyzer = ImprovedMultiHopAnalyzer()
    
    test_queries = [
        "تفاوت صندوق نوآور و باور چیه؟",
        "مقایسه صندوق نوآور با صندوق باور",
        "صندوق نوآور و باور چه تفاوتی دارند؟",
        "موسسه دانشمند چیه؟",
        "تمام دوره‌های آموزشی موسسه",
        "چگونه ثبت‌نام کنم؟"
    ]
    
    for query in test_queries:
        print(f"📝 Query: {query}")
        
        # تست detector
        pair = detector.detect(query)
        if pair:
            print(f"  ✅ Comparison: {pair}")
        
        # تست analyzer
        analysis = analyzer.analyze(query)
        print(f"  📊 Type: {analysis['type']}")
        print(f"  🎯 Multi-hop: {analysis['requires_multi_hop']}")
        print(f"  💡 Entities: {analysis['entities']}")
        print(f"  📈 Confidence: {analysis['confidence']:.2f}")
        print(f"  🧠 Reasoning: {analysis['reasoning']}")
        print()

