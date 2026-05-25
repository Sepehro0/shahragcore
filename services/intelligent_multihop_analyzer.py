# -*- coding: utf-8 -*-
"""
Intelligent Multi-Hop Analyzer
تحلیل‌گر هوشمند برای تشخیص خودکار نیاز به Multi-Hop Retrieval
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """سطح پیچیدگی سوال"""
    SIMPLE = "simple"              # 1 row کافی است
    MODERATE = "moderate"          # 2-3 rows
    COMPLEX = "complex"            # 4-6 rows
    VERY_COMPLEX = "very_complex"  # 7+ rows


class QueryType(Enum):
    """نوع سوال"""
    FACTUAL = "factual"                    # سوال ساده واقعی
    COMPARISON = "comparison"              # مقایسه دو یا چند entity
    AGGREGATION = "aggregation"            # جمع‌آوری اطلاعات از چند منبع
    MULTI_ENTITY = "multi_entity"          # سوال در مورد چند entity
    PROCEDURAL = "procedural"              # سوال فرآیندی (چگونه)
    ANALYTICAL = "analytical"              # تحلیل و استنتاج
    CAUSAL = "causal"                      # علت و معلول


@dataclass
class MultiHopDecision:
    """تصمیم برای استفاده از Multi-Hop"""
    should_use_multihop: bool
    confidence: float
    query_type: QueryType
    complexity: QueryComplexity
    estimated_rows_needed: int
    entities: List[str]
    sub_questions: List[str]
    reasoning: str


class IntelligentMultiHopAnalyzer:
    """
    تحلیل‌گر هوشمند برای تشخیص خودکار نیاز به Multi-Hop
    
    ویژگی‌ها:
    - تشخیص نوع سوال (مقایسه، جمع‌آوری، چند موجودیته)
    - استخراج entities به صورت هوشمند
    - تعیین تعداد documents مورد نیاز
    - Query decomposition خودکار
    - تصمیم‌گیری بر اساس complexity
    """
    
    def __init__(self):
        """Initialize analyzer"""
        
        # الگوهای comparison
        self.comparison_patterns = [
            r'تفاوت\s+(.+?)\s+(?:و|با)\s+(.+?)(?:\s+چیست|چیه|$)',
            r'فرق\s+(?:بین\s+)?(.+?)\s+(?:و|با)\s+(.+?)(?:\s+چیست|چیه|$)',
            r'مقایسه\s+(.+?)\s+(?:و|با)\s+(.+?)(?:\s+چیست|چیه|$)',
            r'(.+?)\s+(?:و|با)\s+(.+?)\s+چه\s+(?:تفاوتی|فرقی)',
        ]
        
        # کلمات کلیدی برای هر نوع سوال
        self.query_type_keywords = {
            QueryType.COMPARISON: [
                'تفاوت', 'فرق', 'مقایسه', 'متفاوت', 'مشابه', 'برابر',
                'بهتر', 'بدتر', 'مزیت', 'معایب', 'نسبت به'
            ],
            QueryType.AGGREGATION: [
                'همه', 'تمام', 'لیست', 'فهرست', 'چند', 'چه چیزهایی',
                'چیا', 'مجموع', 'جمع', 'کل'
            ],
            QueryType.MULTI_ENTITY: [
                ' و ', 'هم ', 'همچنین', 'علاوه بر', 'به علاوه'
            ],
            QueryType.PROCEDURAL: [
                'چگونه', 'چطور', 'روش', 'نحوه', 'فرآیند', 'مراحل',
                'چه کار کنم', 'چیکار کنم'
            ],
            QueryType.CAUSAL: [
                'چرا', 'علت', 'دلیل', 'به خاطر', 'بخاطر', 'چون'
            ]
        }
        
        # وزن‌های هر نوع برای تصمیم‌گیری
        self.type_weights = {
            QueryType.FACTUAL: 1,
            QueryType.COMPARISON: 2,
            QueryType.MULTI_ENTITY: 2,
            QueryType.PROCEDURAL: 1.5,
            QueryType.AGGREGATION: 3,
            QueryType.ANALYTICAL: 2,
            QueryType.CAUSAL: 1.5
        }
    
    def analyze(self, query: str, collection_name: str = None) -> MultiHopDecision:
        """
        تحلیل سوال و تصمیم‌گیری درباره Multi-Hop
        
        Args:
            query: سوال کاربر
            collection_name: نام collection (برای context)
            
        Returns:
            MultiHopDecision با تمام اطلاعات تصمیم
        """
        logger.info(f"🧠 Analyzing query for multi-hop: {query[:80]}...")
        
        # 1. تشخیص نوع سوال
        query_type = self._detect_query_type(query)
        
        # 2. استخراج entities
        entities = self._extract_entities(query, query_type)
        
        # 3. محاسبه complexity
        complexity = self._calculate_complexity(query, query_type, entities)
        
        # 4. تخمین تعداد rows مورد نیاز
        estimated_rows = self._estimate_rows_needed(query_type, complexity, len(entities))
        
        # 5. Query decomposition
        sub_questions = self._decompose_query(query, query_type, entities)
        
        # 6. تصمیم نهایی
        should_use = self._make_decision(query_type, complexity, entities, sub_questions)
        
        # 7. محاسبه confidence
        confidence = self._calculate_confidence(query_type, complexity, entities, sub_questions)
        
        # 8. توضیح reasoning
        reasoning = self._generate_reasoning(query_type, complexity, entities, estimated_rows)
        
        decision = MultiHopDecision(
            should_use_multihop=should_use,
            confidence=confidence,
            query_type=query_type,
            complexity=complexity,
            estimated_rows_needed=estimated_rows,
            entities=entities,
            sub_questions=sub_questions,
            reasoning=reasoning
        )
        
        logger.info(f"📊 Decision: multi-hop={should_use}, type={query_type.value}, "
                   f"complexity={complexity.value}, rows={estimated_rows}, confidence={confidence:.2f}")
        
        return decision
    
    def _detect_query_type(self, query: str) -> QueryType:
        """تشخیص نوع سوال"""
        query_lower = query.lower()
        
        # بررسی الگوهای comparison
        for pattern in self.comparison_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryType.COMPARISON
        
        # بررسی کلمات کلیدی
        type_scores = {}
        for qtype, keywords in self.query_type_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                type_scores[qtype] = score
        
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        return QueryType.FACTUAL
    
    def _extract_entities(self, query: str, query_type: QueryType) -> List[str]:
        """استخراج entities از سوال"""
        entities = []
        
        if query_type == QueryType.COMPARISON:
            # برای سوالات مقایسه‌ای، از regex استفاده کن
            for pattern in self.comparison_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    entity1 = self._cleanup_entity(match.group(1))
                    entity2 = self._cleanup_entity(match.group(2))
                    if entity1 and entity2:
                        entities = [entity1, entity2]
                        break
        
        elif query_type == QueryType.MULTI_ENTITY:
            # تقسیم بر اساس ' و '
            if ' و ' in query:
                parts = query.split(' و ')
                for part in parts:
                    cleaned = self._cleanup_entity(part)
                    if cleaned and len(cleaned.split()) <= 4:
                        entities.append(cleaned)
        
        else:
            # برای سوالات دیگر، سعی کن موضوع اصلی را پیدا کنی
            main_entity = self._extract_main_entity(query)
            if main_entity:
                entities = [main_entity]
        
        return entities[:5]  # حداکثر 5 entity
    
    def _cleanup_entity(self, text: str) -> str:
        """پاکسازی entity"""
        # حذف کلمات کلیدی
        keywords_to_remove = [
            'تفاوت', 'فرق', 'مقایسه', 'بین', 'چیست', 'چیه', 
            'است', 'هست', 'دارد', 'دارند', 'چه', 'تفاوتی', 'فرقی'
        ]
        
        text = text.strip()
        for kw in keywords_to_remove:
            text = re.sub(r'\s*' + kw + r'\s*', ' ', text, flags=re.IGNORECASE)
        
        # حذف نشانه‌گذاری
        text = re.sub(r'[؟،.]', '', text).strip()
        
        return text
    
    def _extract_main_entity(self, query: str) -> Optional[str]:
        """استخراج موضوع اصلی سوال"""
        # حذف کلمات پرسشی
        question_words = ['چیست', 'چیه', 'چگونه', 'چطور', 'چرا', 'کی', 'کجا', 'چه']
        
        words = query.split()
        entity_words = []
        
        for word in words:
            cleaned = word.strip('؟،.')
            if cleaned and cleaned not in question_words and len(cleaned) > 2:
                entity_words.append(cleaned)
        
        if entity_words:
            # اگر entity کوتاه است (1-2 کلمه)، همه را برگردان
            if len(entity_words) <= 3:
                return ' '.join(entity_words)
            # در غیر این صورت، اولین 3 کلمه
            return ' '.join(entity_words[:3])
        
        return None
    
    def _calculate_complexity(self, query: str, query_type: QueryType, 
                             entities: List[str]) -> QueryComplexity:
        """محاسبه پیچیدگی سوال"""
        complexity_score = 0
        
        # 1. طول سوال
        word_count = len(query.split())
        if word_count > 20:
            complexity_score += 2
        elif word_count > 10:
            complexity_score += 1
        
        # 2. تعداد entities
        complexity_score += len(entities)
        
        # 3. وزن نوع سوال
        complexity_score += self.type_weights.get(query_type, 1)
        
        # 4. تعداد سوال‌های فرعی (تقسیم بر اساس '؟' یا ' و ')
        sub_q_count = query.count('؟') + query.count(' و ')
        complexity_score += sub_q_count * 0.5
        
        # تعیین سطح
        if complexity_score < 3:
            return QueryComplexity.SIMPLE
        elif complexity_score < 5:
            return QueryComplexity.MODERATE
        elif complexity_score < 7:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    def _estimate_rows_needed(self, query_type: QueryType, 
                              complexity: QueryComplexity,
                              entity_count: int) -> int:
        """تخمین تعداد rows مورد نیاز"""
        base_rows = {
            QueryType.FACTUAL: 1,
            QueryType.COMPARISON: 2,
            QueryType.MULTI_ENTITY: entity_count if entity_count > 0 else 2,
            QueryType.PROCEDURAL: 2,
            QueryType.AGGREGATION: 5,
            QueryType.ANALYTICAL: 3,
            QueryType.CAUSAL: 2
        }
        
        rows = base_rows.get(query_type, 1)
        
        # تعدیل بر اساس complexity
        if complexity == QueryComplexity.MODERATE:
            rows += 1
        elif complexity == QueryComplexity.COMPLEX:
            rows += 2
        elif complexity == QueryComplexity.VERY_COMPLEX:
            rows += 3
        
        # برای comparison، حداقل به اندازه تعداد entities
        if query_type == QueryType.COMPARISON and entity_count > rows:
            rows = entity_count
        
        return min(rows, 10)  # حداکثر 10 rows
    
    def _decompose_query(self, query: str, query_type: QueryType, 
                        entities: List[str]) -> List[str]:
        """تقسیم سوال به sub-questions"""
        sub_questions = []
        
        if query_type == QueryType.COMPARISON and len(entities) >= 2:
            # برای مقایسه، یک sub-question برای هر entity
            base_question = self._extract_comparison_topic(query)
            for entity in entities:
                sub_q = f"{entity} {base_question}"
                sub_questions.append(sub_q.strip())
        
        elif query_type == QueryType.MULTI_ENTITY and entities:
            # برای multi-entity، یک سوال برای هر entity
            for entity in entities:
                sub_questions.append(entity)
        
        elif query_type == QueryType.PROCEDURAL:
            # برای سوالات فرآیندی، تقسیم به مراحل
            if 'مرحله' in query or 'قدم' in query:
                # اگر خود سوال درباره مراحل است، نیازی به تقسیم نیست
                sub_questions = [query]
            else:
                # سوال را به "مراحل" و "نحوه" تقسیم کن
                sub_questions = [
                    query,
                    f"مراحل {self._extract_main_entity(query) or query}"
                ]
        
        elif query_type == QueryType.AGGREGATION:
            # برای aggregation، سوال اصلی + "تمام موارد"
            sub_questions = [query]
        
        else:
            # برای سوالات ساده، همان سوال اصلی
            sub_questions = [query]
        
        return sub_questions[:5]  # حداکثر 5 sub-question
    
    def _extract_comparison_topic(self, query: str) -> str:
        """استخراج موضوع مقایسه"""
        # حذف entities و کلمات مقایسه‌ای
        topic = query
        
        # حذف الگوی comparison
        topic = re.sub(r'تفاوت\s+.+?\s+(?:و|با)\s+.+?(?:\s+چیست|چیه)?', '', topic, flags=re.IGNORECASE)
        topic = re.sub(r'فرق\s+(?:بین\s+)?.+?\s+(?:و|با)\s+.+?(?:\s+چیست|چیه)?', '', topic, flags=re.IGNORECASE)
        topic = re.sub(r'مقایسه\s+.+?\s+(?:و|با)\s+.+?', '', topic, flags=re.IGNORECASE)
        
        if not topic.strip():
            return "چیست"
        
        return topic.strip()
    
    def _make_decision(self, query_type: QueryType, complexity: QueryComplexity,
                      entities: List[str], sub_questions: List[str]) -> bool:
        """تصمیم‌گیری نهایی درباره استفاده از Multi-Hop"""
        
        # شرط 1: سوالات مقایسه‌ای همیشه multi-hop
        if query_type == QueryType.COMPARISON and len(entities) >= 2:
            return True
        
        # شرط 2: سوالات aggregation همیشه multi-hop
        if query_type == QueryType.AGGREGATION:
            return True
        
        # شرط 3: سوالات multi-entity با بیش از 1 entity
        if query_type == QueryType.MULTI_ENTITY and len(entities) > 1:
            return True
        
        # شرط 4: complexity بالا
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX]:
            return True
        
        # شرط 5: بیش از 2 sub-question
        if len(sub_questions) > 2:
            return True
        
        return False
    
    def _calculate_confidence(self, query_type: QueryType, complexity: QueryComplexity,
                             entities: List[str], sub_questions: List[str]) -> float:
        """محاسبه اطمینان تصمیم"""
        confidence = 0.5  # base confidence
        
        # اگر pattern واضح مقایسه‌ای وجود دارد
        if query_type == QueryType.COMPARISON and len(entities) >= 2:
            confidence += 0.4
        
        # اگر entities واضح استخراج شده‌اند
        if entities:
            confidence += 0.1 * len(entities)
        
        # اگر sub-questions منطقی هستند
        if len(sub_questions) >= 2:
            confidence += 0.15
        
        # اگر complexity بالا است
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX]:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_reasoning(self, query_type: QueryType, complexity: QueryComplexity,
                           entities: List[str], estimated_rows: int) -> str:
        """تولید توضیح برای تصمیم"""
        reasons = []
        
        reasons.append(f"نوع سوال: {query_type.value}")
        reasons.append(f"پیچیدگی: {complexity.value}")
        
        if entities:
            reasons.append(f"تعداد entities: {len(entities)} ({', '.join(entities[:3])})")
        
        reasons.append(f"تعداد rows تخمینی: {estimated_rows}")
        
        return " | ".join(reasons)


# Test
if __name__ == "__main__":
    analyzer = IntelligentMultiHopAnalyzer()
    
    test_queries = [
        "تفاوت صندوق نوآور و باور چیه؟",
        "صندوق باور چیست؟",
        "چگونه می‌توانم در جایزه نوآوری ثبت‌نام کنم؟",
        "تمام دوره‌های آموزشی موسسه دانشمند چیست؟",
        "صندوق نوآور و صندوق باور و شبکه تحقیق و توسعه چه خدماتی دارند؟"
    ]
    
    print("🧪 Testing Intelligent Multi-Hop Analyzer\n")
    
    for query in test_queries:
        print(f"📝 Query: {query}")
        decision = analyzer.analyze(query)
        print(f"   🎯 Multi-hop: {decision.should_use_multihop}")
        print(f"   📊 Type: {decision.query_type.value}")
        print(f"   🔢 Estimated rows: {decision.estimated_rows_needed}")
        print(f"   💡 Entities: {decision.entities}")
        print(f"   📈 Confidence: {decision.confidence:.2f}")
        print(f"   🧠 Reasoning: {decision.reasoning}")
        print()

