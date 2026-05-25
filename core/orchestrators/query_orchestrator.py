# -*- coding: utf-8 -*-
"""
Query Orchestrator
هماهنگ‌کننده فرآیند پردازش query
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re

from services.smart_query_preprocessor import SmartQueryPreprocessor, QueryType
from utils.text_utils import TextNormalizer
from utils.matching_helpers import MatchingHelpers

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """
    مدیریت کل فرآیند پردازش query
    
    مسئولیت‌ها:
    - Smart preprocessing
    - Normalization
    - Multi-part detection
    - Query expansion
    """
    
    def __init__(
        self,
        smart_preprocessor: SmartQueryPreprocessor,
        text_normalizer: TextNormalizer,
        matching_helpers: MatchingHelpers,
        query_analyzer=None
    ):
        """
        Args:
            smart_preprocessor: Smart query preprocessor
            text_normalizer: Text normalizer
            matching_helpers: Matching helpers
            query_analyzer: Query analyzer (optional, for financial queries)
        """
        self.smart_preprocessor = smart_preprocessor
        self.text_normalizer = text_normalizer
        self.matching_helpers = matching_helpers
        self.query_analyzer = query_analyzer
        
    async def process_query(
        self,
        query: str,
        collection_name: str,
        domain_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        پردازش کامل query
        
        Args:
            query: Query اصلی
            collection_name: نام collection
            domain_info: اطلاعات domain
            
        Returns:
            Dict حاوی:
                - processed_query: Query پردازش شده
                - normalized_query: Query نرمال شده
                - is_greeting: آیا سلام است؟
                - is_multi_part: آیا چند قسمتی است؟
                - sub_queries: لیست sub queries (اگر multi-part باشد)
                - metadata: metadata اضافی
        """
        original_query = query
        
        # === Smart Preprocessing ===
        preprocess_result = await self.smart_preprocessor.preprocess(
            query=query,
            collection_name=collection_name,
            domain_info=domain_info or {}
        )
        
        # بررسی سلام
        if preprocess_result.query_type == QueryType.GREETING:
            return {
                'processed_query': query,
                'normalized_query': query,
                'is_greeting': True,
                'greeting_response': preprocess_result.response,
                'is_multi_part': False,
                'sub_queries': [],
                'metadata': preprocess_result.metadata or {}
            }
        
        # استفاده از processed query
        query = preprocess_result.processed_query
        
        # === Budget Financial: سال پیش‌فرض ===
        year_was_mentioned = False
        if collection_name == "budget_financial":
            query, year_was_mentioned = self._add_default_year_if_missing(query, original_query)
        
        # === Synonym Expansion (for zabete_qa) ===
        if collection_name == 'zabete_qa':
            from config.collection_prompts import expand_zabete_query_with_synonyms
            query = expand_zabete_query_with_synonyms(query)
            logger.info(f"📝 [SYNONYM] Expanded query with synonyms: {query[:100]}...")
        
        # === Normalization ===
        normalized_query = self.text_normalizer.normalize_text(query)
        
        # === Multi-part Detection ===
        sub_queries = self.matching_helpers.split_multi_part_query(original_query)
        is_multi_part = len(sub_queries) >= 2
        
        # === Query Analysis (for financial queries) ===
        query_analysis = None
        if self.query_analyzer and collection_name == "budget_financial":
            try:
                logger.info(f"🔍 [QUERY_ANALYZER] Starting analysis for: {original_query[:50]}...")
                logger.info(f"🔍 [QUERY_ANALYZER] Analyzer type: {type(self.query_analyzer).__name__}")
                
                # Try async method first
                if hasattr(self.query_analyzer, 'analyze_query_async'):
                    logger.info(f"🔍 [QUERY_ANALYZER] Using analyze_query_async method")
                    query_analysis = await self.query_analyzer.analyze_query_async(
                        query=original_query,
                        collection_name=collection_name
                    )
                elif hasattr(self.query_analyzer, 'analyze_query'):
                    logger.info(f"🔍 [QUERY_ANALYZER] Using analyze_query method")
                    query_analysis = self.query_analyzer.analyze_query(
                        query=original_query
                    )
                elif hasattr(self.query_analyzer, 'analyze'):
                    logger.info(f"🔍 [QUERY_ANALYZER] Using analyze method")
                    query_analysis = await self.query_analyzer.analyze(
                        query=original_query
                    )
                
                if query_analysis:
                    logger.info(f"✅ [QUERY_ANALYZER] Analysis successful:")
                    logger.info(f"   - query_category: {query_analysis.get('query_category', 'N/A')}")
                    logger.info(f"   - entity_names: {query_analysis.get('entity_names', [])}")
                    logger.info(f"   - years: {query_analysis.get('years', [])}")
                    logger.info(f"   - confidence: {query_analysis.get('confidence', 'N/A')}")
                else:
                    logger.warning(f"⚠️ [QUERY_ANALYZER] Analysis returned None")
            except Exception as e:
                logger.error(f"❌ [QUERY_ANALYZER] Analysis failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # === Material Reference Detection ===
        # اگر ماده در پرانتز است، برای retrieval آن را حذف کن
        retrieval_query = normalized_query
        material_is_reference = False
        
        if collection_name == 'zabete_qa':
            # اول synonym expansion (قبل از material optimization)
            # چون ممکن است material optimization معادل‌ها را حذف کند
            from config.collection_prompts import expand_zabete_query_with_synonyms
            retrieval_query = expand_zabete_query_with_synonyms(retrieval_query)
            logger.info(f"📝 [SYNONYM] Expanded retrieval query: {retrieval_query[:100]}...")
            
            # سپس material optimization
            retrieval_query, material_is_reference = self._optimize_query_for_material_reference(
                retrieval_query, original_query
            )
            if material_is_reference:
                logger.info(f"📝 [QUERY_OPTIMIZER] Detected material as reference, optimized query for retrieval")
                logger.info(f"   Original: {normalized_query[:80]}...")
                logger.info(f"   Optimized: {retrieval_query[:80]}...")
        
        # === Build Result ===
        return {
            'processed_query': query,
            'normalized_query': normalized_query,
            'retrieval_query': retrieval_query,  # برای embedding و retrieval
            'material_is_reference': material_is_reference,
            'original_query': original_query,
            'is_greeting': False,
            'is_multi_part': is_multi_part,
            'sub_queries': sub_queries if is_multi_part else [],
            'metadata': preprocess_result.metadata or {},
            'additional_search_terms': preprocess_result.metadata.get('additional_search_terms', []) if preprocess_result.metadata else [],
            'query_analysis': query_analysis,
            'used_query_understanding': query_analysis is not None,
            'year_was_mentioned': year_was_mentioned  # Flag برای تشخیص اینکه آیا سال در query اصلی ذکر شده است
        }
    
    def _add_default_year_if_missing(self, query: str, original_query: str) -> tuple[str, bool]:
        """
        اضافه کردن سال پیش‌فرض 1403 اگر ذکر نشده باشد
        
        Returns:
            tuple: (processed_query, year_was_mentioned)
                - processed_query: Query پردازش شده (با سال اضافه شده اگر لازم باشد)
                - year_was_mentioned: آیا سال در query اصلی ذکر شده است؟
        """
        # Pattern برای تشخیص سال در query
        # شامل: سال 1403، 1403، سال 03، 03، سال 1401، 1401، و غیره
        # بهبود: تشخیص سال‌های شمسی (1398-1403) و سال‌های دو رقمی (98-03)
        year_patterns = [
            r'سال\s+(1[3-4]\d{2})',  # سال 1403
            r'(1[3-4]\d{2})',  # 1403 (بدون "سال")
            r'سال\s+([۰-۹]{4})',  # سال ۱۴۰۳ (فارسی)
            r'([۰-۹]{4})',  # ۱۴۰۳ (فارسی، بدون "سال")
            r'سال\s+([0-9]{2})',  # سال 03
            r'\b([0-9]{2})\b',  # 03 (با word boundary)
            r'سال\s+([۰-۹]{2})',  # سال ۰۳ (فارسی)
            r'\b([۰-۹]{2})\b',  # ۰۳ (فارسی، با word boundary)
        ]
        
        # بررسی در query اصلی (قبل از پردازش)
        has_year_in_original = False
        for pattern in year_patterns:
            if re.search(pattern, original_query):
                has_year_in_original = True
                break
        
        # بررسی در query پردازش شده
        has_year_in_processed = False
        for pattern in year_patterns:
            if re.search(pattern, query):
                has_year_in_processed = True
                break
        
        # اگر سال در هیچ کدام ذکر نشده است، اضافه می‌کنیم
        if not has_year_in_original and not has_year_in_processed:
            logger.info(f"📅 [BUDGET] No year detected in original query, appending default year 1403")
            return query + " در سال 1403", False
        
        # اگر سال در query اصلی ذکر شده است
        if has_year_in_original:
            logger.info(f"📅 [BUDGET] Year detected in original query")
            return query, True
        
        # اگر سال در query پردازش شده ذکر شده است (اما نه در اصلی)
        logger.info(f"📅 [BUDGET] Year detected in processed query (but not in original)")
        return query, False
    
    def _optimize_query_for_material_reference(
        self, 
        query: str, 
        original_query: str
    ) -> Tuple[str, bool]:
        """
        بهینه‌سازی query وقتی "ماده XX" فقط یک reference/context است
        
        **مشکل**: وقتی کاربر می‌گوید "با توجه به ... ماده ۲۹ ... آیا تضمین ..."
        سیستم embedding روی "ماده ۲۹" focus می‌کند و sources اشتباه برمی‌گرداند.
        
        **راه‌حل**: 
        1. تشخیص اینکه ماده در پرانتز یا به عنوان reference است
        2. حذف آن از retrieval query
        3. نگه داشتن original query برای answer generation
        
        Returns:
            tuple: (optimized_query, is_material_reference)
        """
        # Normalize اعداد فارسی
        query_normalized = query
        for persian, english in {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
                                  '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}.items():
            query_normalized = query_normalized.replace(persian, english)
        
        # پیدا کردن شماره ماده
        material_match = re.search(r'ماده\s*(\d+)', query_normalized)
        if not material_match:
            return query, False
        
        material_number = material_match.group(1)
        words_count = len(query.split())
        
        # تشخیص کلمات کلیدی موضوعی
        topic_keywords = [
            'تضمین', 'پیش پرداخت', 'پرداخت', 'فسخ', 'خاتمه', 'تعلیق',
            'کسور', 'خسارت', 'تاخیر', 'جریمه', 'افزایش', 'کاهش', 'مبلغ'
        ]
        query_lower = query.lower()
        keywords_found = [kw for kw in topic_keywords if kw in query_lower]
        keywords_count = len(keywords_found)
        
        # بررسی 1: آیا ماده در پرانتز است؟
        in_parentheses = bool(re.search(r'\([^)]*ماده\s*' + material_number + r'[^)]*\)', query_normalized))
        
        # بررسی 2: آیا سوال طولانی و پر از کلمات کلیدی است؟
        is_complex_query = words_count > 15 and keywords_count >= 2
        
        # بررسی 3: آیا کلمات کلیدی موضوعی وجود دارد؟
        has_topic_keywords = keywords_count >= 2
        
        # تصمیم‌گیری
        if in_parentheses or (is_complex_query and has_topic_keywords):
            logger.info(f"🎯 [MATERIAL_REF] Detected material {material_number} as reference")
            logger.info(f"   in_parentheses={in_parentheses}, words={words_count}, keywords={keywords_found}")
            
            # === حذف reference ماده از query برای بهبود retrieval ===
            # روش 1: حذف پرانتز حاوی ماده
            optimized = re.sub(r'\([^)]*ماده\s*' + material_number + r'[^)]*\)', '', query_normalized)
            
            # روش 2: حذف عبارات "با توجه به ماده XX" یا "در چارچوب ماده XX"
            optimized = re.sub(r'(با توجه به|در چارچوب|طبق|مطابق)\s+ماده\s*' + material_number, '', optimized)
            
            # روش 3: حذف "ماده XX" تنها اگر هنوز وجود دارد
            optimized = re.sub(r'ماده\s*' + material_number + r'\s*(شرایط عمومی پیمان)?', '', optimized)
            
            # تمیز کردن
            optimized = re.sub(r'\s+', ' ', optimized).strip()
            optimized = re.sub(r',\s*,', ',', optimized)
            optimized = re.sub(r'\(\s*\)', '', optimized)
            
            logger.info(f"   Optimized query: {optimized[:100]}...")
            return optimized, True
        
        return query, False

