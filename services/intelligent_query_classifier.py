# -*- coding: utf-8 -*-
"""
Intelligent Query Classifier
LLM-based query classification for intelligent routing decisions
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
from dataclasses import dataclass, field

from services.qwen_client import QwenClient

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Types of query intents"""
    AGGREGATION = "aggregation"     # Sum, average, count, etc.
    LOOKUP = "lookup"               # Find specific item by ID/code
    COMPARISON = "comparison"       # Compare multiple items
    CONCEPTUAL = "conceptual"       # Explain concept, definition
    LIST = "list"                   # List items matching criteria
    GREETING = "greeting"           # Hello, hi, etc.
    IRRELEVANT = "irrelevant"       # Off-topic questions
    UNKNOWN = "unknown"


class DataSource(str, Enum):
    """Target data source for query"""
    DATABASE = "database"           # Structured data (SQL)
    RAG = "rag"                     # Semantic search
    HYBRID = "hybrid"               # Both database and RAG
    DIRECT = "direct"               # Direct answer without search
    TOOL_CALL = "tool_call"         # External API via registered tools


class CollectionType(str, Enum):
    """Types of collections"""
    FINANCIAL = "financial"         # Budget, income, expenses
    QA = "qa"                       # Question/Answer datasets
    BOOKLET = "booklet"             # Legal documents with articles
    GENERAL = "general"             # General documents


@dataclass
class ClassificationResult:
    """Result of query classification"""
    intent: QueryIntent
    data_source: DataSource
    confidence: float
    collection_type: Optional[CollectionType] = None
    entities: List[str] = field(default_factory=list)
    years: List[str] = field(default_factory=list)
    requires_aggregation: bool = False
    aggregation_type: Optional[str] = None  # sum, count, avg, max, min
    reason: str = ""


class IntelligentQueryClassifier:
    """
    Unified query classifier that determines:
    1. Query intent (what user wants)
    2. Data source (where to get data)
    3. Collection type (what kind of data)
    """
    
    # Centralized keyword lists - single source of truth
    FINANCIAL_KEYWORDS = [
        'تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', 'درامد', 
        'در امد', 'درامدهای', 'درآمدهای', 'درامدها', 'درآمدها',
        'بودجه', 'سرمایه‌ای', 'سرمایه', 'منابع', 'مالی', 'ریال', 'تومان',
        'اختصاصی', 'عمومی', 'ملی', 'استانی', 'کل', 'جاری', 'عمرانی',
        # 🆕 کلمات مالیاتی و اقتصادی که ممکن است بدون keyword واضح استفاده شوند
        'مالیات', 'ماليات', 'عوارض', 'یارانه', 'ياراه', 'واردات', 'صادرات',
        'نفت', 'گاز', 'پتروشیمی', 'واگذاری', 'فروش', 'وام', 'تسهیلات',
        'یارانه', 'کمک', 'اعانه', 'حقوق', 'دستمزد', 'پاداش',
        'وصول', 'تحقق', 'پیش‌بینی', 'پیش بینی', 'برآورد', 'براورد'
    ]
    
    DEVICE_KEYWORDS = [
        'پارک', 'ستاد', 'بنیاد', 'بنياد', 'معاونت', 'مرکز', 'انستیتو', 'کشور',
        'پاستور', 'ایران', 'ايران', 'سازمان', 'وزارت', 'دانشگاه', 'پژوهشگاه',
        'شرکت', 'شركت', 'موسسه', 'اداره', 'نهاد', 'دفتر', 'فرهنگستان', 'پژوهشکده',
        'گمرک', 'گمرك', 'بانک', 'بانك'
    ]
    
    AGGREGATION_KEYWORDS = [
        'مجموع', 'جمع', 'کل', 'چقدر', 'چند', 'تعداد', 'میانگین',
        'بیشترین', 'کمترین', 'حداکثر', 'حداقل', 'درصد'
    ]
    
    YEAR_PATTERN = re.compile(r'(13|14)\d{2}|\d{2,4}\s*(?:تا|-)\s*\d{2,4}|سال\s*\d{2,4}|سال\s*های')
    
    GREETING_PATTERNS = [
        r'^سلام\b', r'^درود\b', r'^صبح\s*بخیر', r'^عصر\s*بخیر',
        r'^شب\s*بخیر', r'^خسته\s*نباشید', r'^ممنون', r'^تشکر',
        r'^hello\b', r'^hi\b', r'^hey\b'
    ]
    
    QA_INDICATORS = [
        'چیست', 'چی', 'کیست', 'چطور', 'چگونه', 'توضیح', 'معنی', 
        'مفهوم', 'تعریف', 'یعنی چه'
    ]
    
    BOOKLET_INDICATORS = [
        'ماده', 'بند', 'تبصره', 'فصل', 'باب', 'قانون', 'مقررات',
        'دستورالعمل', 'آیین‌نامه', 'بخشنامه'
    ]
    
    def __init__(self, qwen_client: QwenClient, tool_registry=None):
        self.qwen_client = qwen_client
        self._tool_registry = tool_registry
    
    def set_tool_registry(self, tool_registry) -> None:
        """Attach a ToolRegistry after construction (avoids circular imports)."""
        self._tool_registry = tool_registry
    
    async def classify(
        self,
        query: str,
        collection_name: str,
        collection_metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """
        Classify a query to determine intent and data source.
        
        Args:
            query: User's question
            collection_name: Name of the target collection
            collection_metadata: Optional metadata about the collection
            
        Returns:
            ClassificationResult with intent, data source, and confidence
        """
        normalized_query = self._normalize_text(query).lower()
        
        # Step 1: Check for greeting
        if self._is_greeting(normalized_query):
            return ClassificationResult(
                intent=QueryIntent.GREETING,
                data_source=DataSource.DIRECT,
                confidence=1.0,
                reason="Detected greeting pattern"
            )
        
        # Step 1.5: Tool-call routing — if the collection has registered
        # tools, check whether any tool trigger descriptions match the query.
        tool_result = self._check_tool_call_route(normalized_query, collection_name)
        if tool_result is not None:
            logger.info(
                f"🔧 Tool-call route matched: {tool_result.reason} "
                f"(confidence {tool_result.confidence:.2f})"
            )
            return tool_result
        
        # Step 2: Detect collection type
        collection_type = self._detect_collection_type(
            collection_name, 
            collection_metadata
        )
        
        # Step 3: Pattern-based classification (fast path)
        pattern_result = self._pattern_based_classification(
            normalized_query,
            collection_type
        )
        
        # If pattern-based is confident enough, return it
        if pattern_result.confidence >= 0.8:
            pattern_result.collection_type = collection_type
            logger.info(f"🎯 Pattern-based classification: {pattern_result.intent.value} -> {pattern_result.data_source.value} (confidence: {pattern_result.confidence:.2f})")
            return pattern_result
        
        # Step 4: LLM-based classification for uncertain cases
        llm_result = await self._llm_classification(
            query,
            collection_type,
            pattern_result
        )
        
        llm_result.collection_type = collection_type
        logger.info(f"🤖 LLM-based classification: {llm_result.intent.value} -> {llm_result.data_source.value} (confidence: {llm_result.confidence:.2f})")
        return llm_result
    
    def _check_tool_call_route(
        self,
        normalized_query: str,
        collection_name: str,
    ) -> Optional[ClassificationResult]:
        """
        If the collection has registered tools whose trigger descriptions
        overlap with the query, route to TOOL_CALL.

        Returns None when no tool match is detected so the existing
        classification pipeline continues unchanged.
        """
        if self._tool_registry is None:
            return None
        if not self._tool_registry.has_tools(collection_name):
            return None

        tools = self._tool_registry.get_tools(collection_name)
        best_score = 0.0
        best_tool_name = ""

        # Strip punctuation for cleaner matching
        import re as _re
        _strip_punct = lambda s: _re.sub(r'[،؛،,.!?؟«»\(\)\[\]{}]', ' ', s)

        for tool in tools:
            trigger_raw = self._normalize_text(tool.trigger_description).lower()
            trigger = _strip_punct(trigger_raw)
            if not trigger:
                continue

            trigger_words = {w for w in trigger.split() if len(w) > 1}
            query_clean = _strip_punct(normalized_query)
            query_words = {w for w in query_clean.split() if len(w) > 1}

            if not trigger_words:
                continue

            # 1. Word-level overlap
            overlap = trigger_words & query_words
            word_score = len(overlap) / len(trigger_words)

            # 2. Substring match: does any trigger word appear as substring in query?
            substring_hits = sum(
                1 for tw in trigger_words if any(tw in qw or qw in tw for qw in query_words)
            )
            substring_score = substring_hits / len(trigger_words)

            # 3. Keyword match: key topic words from description (1-2 highly specific words)
            # Take the top meaningful words from trigger (longer = more specific)
            key_words = sorted(trigger_words, key=len, reverse=True)[:4]
            keyword_hits = sum(1 for kw in key_words if kw in query_clean or any(kw in qw or qw in kw for qw in query_words))
            keyword_score = keyword_hits / max(len(key_words), 1)

            # Combined score — max of the three approaches
            score = max(word_score, substring_score * 0.8, keyword_score * 0.7)

            if score > best_score:
                best_score = score
                best_tool_name = tool.name

        if best_score >= 0.15:
            return ClassificationResult(
                intent=QueryIntent.LOOKUP,
                data_source=DataSource.TOOL_CALL,
                confidence=min(0.6 + best_score * 0.4, 0.95),
                reason=f"Tool trigger match '{best_tool_name}' (score={best_score:.2f})",
            )
        return None

    def _normalize_text(self, text: str) -> str:
        """Normalize Persian/Arabic text"""
        if not text:
            return ''
        translation_map = str.maketrans({
            '‌': ' ',
            '‏': ' ',
            'ي': 'ی',
            'ى': 'ی',
            'ئ': 'ی',
            'ك': 'ک',
            'ة': 'ه',
            'ۀ': 'ه',
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا'
        })
        normalized = text.translate(translation_map)
        return ' '.join(normalized.split())
    
    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting"""
        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    # Collections that should NEVER be routed to database (QA/Educational)
    NON_DATABASE_COLLECTIONS = [
        'karbaran_omomi', 'karbaran-omomi',
        'zinaf_dakheli', 'zinaf-dakheli',
        'booklet_bo', 'booklet__bo',
    ]
    
    def _detect_collection_type(
        self,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CollectionType:
        """Detect the type of collection"""
        name_lower = collection_name.lower()
        
        # ========== EXPLICIT QA COLLECTIONS (HIGHEST PRIORITY) ==========
        # These collections should ALWAYS be treated as QA, never financial
        if any(qa_col in name_lower for qa_col in ['karbaran_omomi', 'karbaran-omomi', 'zinaf_dakheli', 'zinaf-dakheli']):
            logger.info(f"🎯 Collection {collection_name} explicitly detected as QA collection")
            return CollectionType.QA
        # ================================================================
        
        # Check metadata first
        if metadata:
            domain = metadata.get('domain_type') or metadata.get('domain')
            if domain:
                domain_str = str(domain).lower()
                if 'financial' in domain_str:
                    return CollectionType.FINANCIAL
                elif 'qa' in domain_str or 'question' in domain_str or 'educational' in domain_str:
                    return CollectionType.QA
                elif 'booklet' in domain_str or 'legal' in domain_str:
                    return CollectionType.BOOKLET
        
        # Heuristic based on collection name
        if any(kw in name_lower for kw in ['budget', 'finance', 'mali', 'malieh', 'بودجه', 'مالی']):
            return CollectionType.FINANCIAL
        elif any(kw in name_lower for kw in ['qa', 'question', 'faq', 'سوال', 'پرسش', 'omomi', 'dakheli']):
            return CollectionType.QA
        elif any(kw in name_lower for kw in ['booklet', 'law', 'legal', 'قانون', 'مقرره']):
            return CollectionType.BOOKLET
        
        return CollectionType.GENERAL
    
    def _pattern_based_classification(
        self,
        query: str,
        collection_type: CollectionType
    ) -> ClassificationResult:
        """Fast pattern-based classification"""
        
        # Normalize query first to handle "در امد" -> "درآمد"
        normalized_query_text = query.replace('‌', ' ').replace('\u200c', ' ')
        normalized_query_text = re.sub(r'در\s+ا\s*مد', 'درآمد', normalized_query_text, flags=re.IGNORECASE)
        normalized_query_text = re.sub(r'در\s+امد', 'درآمد', normalized_query_text, flags=re.IGNORECASE)
        
        # Extract features
        has_financial = any(kw in normalized_query_text.lower() for kw in self.FINANCIAL_KEYWORDS)
        has_device = any(kw in query for kw in self.DEVICE_KEYWORDS)
        has_year = bool(self.YEAR_PATTERN.search(query))
        has_aggregation = any(kw in query for kw in self.AGGREGATION_KEYWORDS)
        has_qa_indicators = any(kw in query for kw in self.QA_INDICATORS)
        has_booklet_indicators = any(kw in query for kw in self.BOOKLET_INDICATORS)
        
        # Extract years
        years = self._extract_years(query)
        
        # Extract entities (device names)
        entities = self._extract_entities(query)
        
        # Decision logic based on collection type
        if collection_type == CollectionType.FINANCIAL:
            return self._classify_financial_query(
                query, has_financial, has_device, has_year, 
                has_aggregation, years, entities
            )
        elif collection_type == CollectionType.QA:
            return self._classify_qa_query(
                query, has_qa_indicators, entities
            )
        elif collection_type == CollectionType.BOOKLET:
            return self._classify_booklet_query(
                query, has_booklet_indicators, entities
            )
        else:
            # General collection - determine by query characteristics
            if has_financial and (has_year or has_device):
                return self._classify_financial_query(
                    query, has_financial, has_device, has_year,
                    has_aggregation, years, entities
                )
            elif has_qa_indicators:
                return self._classify_qa_query(query, True, entities)
            else:
                return ClassificationResult(
                    intent=QueryIntent.UNKNOWN,
                    data_source=DataSource.RAG,
                    confidence=0.5,
                    entities=entities,
                    years=years,
                    reason="General query, defaulting to RAG"
                )
    
    def _classify_financial_query(
        self,
        query: str,
        has_financial: bool,
        has_device: bool,
        has_year: bool,
        has_aggregation: bool,
        years: List[str],
        entities: List[str]
    ) -> ClassificationResult:
        """Classify financial domain query"""
        
        confidence = 0.5
        
        # Boost confidence based on features
        if has_financial:
            confidence += 0.15
        if has_device:
            confidence += 0.15
        if has_year:
            confidence += 0.1
        if has_aggregation:
            confidence += 0.1
        
        # 🆕 اگر هم financial و هم year داریم، confidence بالاتر می‌رود
        # (این مشخصه کافی است تا query مالی باشد)
        if has_financial and has_year:
            confidence += 0.15
        
        confidence = min(confidence, 0.95)
        
        # Determine intent
        if has_aggregation:
            intent = QueryIntent.AGGREGATION
            agg_type = self._detect_aggregation_type(query)
        elif has_device and not has_aggregation:
            intent = QueryIntent.LOOKUP
            agg_type = None
        else:
            intent = QueryIntent.LOOKUP
            agg_type = None
        
        # Financial queries with year/device should go to database
        if has_financial and (has_year or has_device):
            data_source = DataSource.DATABASE
        elif has_aggregation:
            data_source = DataSource.DATABASE
        else:
            data_source = DataSource.HYBRID
        
        return ClassificationResult(
            intent=intent,
            data_source=data_source,
            confidence=confidence,
            entities=entities,
            years=years,
            requires_aggregation=has_aggregation,
            aggregation_type=agg_type,
            reason=f"Financial query: financial={has_financial}, device={has_device}, year={has_year}, agg={has_aggregation}"
        )
    
    def _classify_qa_query(
        self,
        query: str,
        has_qa_indicators: bool,
        entities: List[str]
    ) -> ClassificationResult:
        """Classify Q&A domain query"""
        
        # Q&A datasets typically use semantic search (RAG)
        # but may benefit from exact match on question field
        
        return ClassificationResult(
            intent=QueryIntent.LOOKUP if has_qa_indicators else QueryIntent.CONCEPTUAL,
            data_source=DataSource.RAG,
            confidence=0.8 if has_qa_indicators else 0.6,
            entities=entities,
            reason=f"Q&A query: indicators={has_qa_indicators}"
        )
    
    def _classify_booklet_query(
        self,
        query: str,
        has_booklet_indicators: bool,
        entities: List[str]
    ) -> ClassificationResult:
        """Classify booklet/legal document query"""
        
        # Check for specific article/clause references
        has_specific_ref = bool(re.search(r'ماده\s*\d+|بند\s*\d+|تبصره\s*\d+', query))
        
        if has_specific_ref:
            return ClassificationResult(
                intent=QueryIntent.LOOKUP,
                data_source=DataSource.DATABASE,
                confidence=0.9,
                entities=entities,
                reason="Booklet query with specific article reference"
            )
        else:
            return ClassificationResult(
                intent=QueryIntent.CONCEPTUAL,
                data_source=DataSource.RAG,
                confidence=0.7,
                entities=entities,
                reason=f"Booklet query: indicators={has_booklet_indicators}"
            )
    
    def _extract_years(self, query: str) -> List[str]:
        """Extract years from query"""
        years = []
        # Match 4-digit years (1398-1403)
        matches = re.findall(r'\b(1[34]\d{2})\b', query)
        years.extend(matches)
        # Match 2-digit years (98-03)
        matches = re.findall(r'\b(9[89]|0[0-3])\b', query)
        for m in matches:
            # Convert to 4-digit
            if m.startswith('9'):
                years.append('13' + m)
            else:
                years.append('14' + m)
        return list(set(years))
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entity names from query"""
        entities = []
        for kw in self.DEVICE_KEYWORDS:
            if kw in query:
                # Try to extract the full entity name
                pattern = rf'({kw}[^\s،,]+(?:\s+[^\s،,]+){{0,5}})'
                matches = re.findall(pattern, query)
                entities.extend(matches)
        return entities[:5]  # Limit to 5 entities
    
    def _detect_aggregation_type(self, query: str) -> Optional[str]:
        """Detect type of aggregation requested"""
        if any(kw in query for kw in ['مجموع', 'جمع', 'کل']):
            return 'sum'
        elif any(kw in query for kw in ['تعداد', 'چند']):
            return 'count'
        elif 'میانگین' in query:
            return 'avg'
        elif any(kw in query for kw in ['بیشترین', 'حداکثر']):
            return 'max'
        elif any(kw in query for kw in ['کمترین', 'حداقل']):
            return 'min'
        return None
    
    async def _llm_classification(
        self,
        query: str,
        collection_type: CollectionType,
        pattern_result: ClassificationResult
    ) -> ClassificationResult:
        """Use LLM for uncertain classifications"""
        
        prompt = f"""تحلیل کن که این سوال چه نوع پاسخی نیاز دارد:

سوال: {query}
نوع مجموعه: {collection_type.value}

به صورت JSON پاسخ بده:
{{
    "intent": "aggregation|lookup|comparison|conceptual|list|irrelevant",
    "data_source": "database|rag|hybrid",
    "confidence": 0.0-1.0,
    "reason": "توضیح کوتاه"
}}

نکات:
- اگر سوال درباره مقادیر عددی (مجموع، تعداد، میانگین) است → database
- اگر سوال مفهومی یا توضیحی است → rag
- اگر سوال ترکیبی است → hybrid
"""
        
        try:
            # بررسی سریع اینکه آیا vLLM در دسترس است
            # اگر در دسترس نباشد، مستقیماً به pattern fallback می‌کنیم
            try:
                is_available = await self.qwen_client.is_available()
                if not is_available:
                    logger.warning("⚠️ vLLM service unavailable, skipping LLM classification")
                    return pattern_result
            except Exception as health_check_error:
                logger.warning(f"⚠️ vLLM health check failed: {health_check_error}, skipping LLM classification")
                return pattern_result
            
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response.success:
                # Extract JSON from response
                json_match = re.search(r'\{[^}]+\}', response.text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        return ClassificationResult(
                            intent=QueryIntent(result.get('intent', 'unknown')),
                            data_source=DataSource(result.get('data_source', 'rag')),
                            confidence=float(result.get('confidence', 0.7)),
                            entities=pattern_result.entities,
                            years=pattern_result.years,
                            requires_aggregation=pattern_result.requires_aggregation,
                            aggregation_type=pattern_result.aggregation_type,
                            reason=result.get('reason', 'LLM classification')
                        )
                    except (json.JSONDecodeError, ValueError):
                        pass
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
        
        # Fallback to pattern result
        return pattern_result
    
    def get_greeting_response(self) -> str:
        """Get standard greeting response"""
        return """سلام! 👋
من دستیار هوش مصنوعی سازمان برنامه و بودجه هستم.
می‌توانم به سوالات شما درباره بودجه، اعتبارات، و اطلاعات مالی پاسخ دهم.
چطور می‌توانم کمکتان کنم؟"""
    
    def get_irrelevant_response(self) -> str:
        """Get response for irrelevant queries"""
        return """پرسش مشابه به پرسش شما در بانک پرسش‌ و پاسخ‌ یافت نشد.
لطفاً سؤال خود را دقیق‌تر مطرح کرده و جزئیات بیشتری ارائه دهید.
چنانچه همچنان پاسخی یافت نشد و پرسش شما به‌عنوان پرسش جدید محسوب می‌شود، از طریق گزینه «سؤال من به‌عنوان سؤال جدید محسوب شود» اقدام نمایید."""

