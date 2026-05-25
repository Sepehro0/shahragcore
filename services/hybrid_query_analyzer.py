# -*- coding: utf-8 -*-
"""
Hybrid Query Analyzer - ترکیب روش استاتیک و LLM
این ماژول یک wrapper هوشمند است که ابتدا از روش استاتیک استفاده می‌کند
و در صورت نیاز به LLM fallback می‌کند.

بهبودها:
- استفاده از schema database برای شناسایی entity های موجود
- LLM-based entity extraction برای موارد پیچیده
- Fuzzy matching با مقادیر unique جدول
"""

import json
import re
import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from difflib import SequenceMatcher
from .query_analyzer import QueryAnalyzer

logger = logging.getLogger(__name__)


class HybridQueryAnalyzer:
    """
    تحلیلگر ترکیبی که از روش استاتیک شروع می‌کند
    و در صورت نیاز به LLM fallback می‌کند.
    
    قابلیت‌های جدید:
    - استفاده از schema database برای شناسایی entity های موجود
    - Fuzzy matching با مقادیر unique جدول
    - LLM-based entity extraction برای موارد پیچیده
    """
    
    def __init__(self, llm_client=None, database_service=None, confidence_threshold: float = 0.7):
        """
        Args:
            llm_client: کلاینت LLM (Qwen API)
            database_service: سرویس دیتابیس برای دسترسی به schema
            confidence_threshold: حداقل confidence برای استفاده از نتایج استاتیک
        """
        self.static_analyzer = QueryAnalyzer()
        self.llm_client = llm_client
        self.database_service = database_service
        self.confidence_threshold = confidence_threshold
        
        # کش برای مقادیر unique جدول
        self._entity_cache: Dict[str, Set[str]] = {}
        self._component_cache: Dict[str, Set[str]] = {}
        self._cache_ttl = 300  # 5 دقیقه
        self._last_cache_update = 0
        
        # Entity Disambiguator (legacy)
        self.entity_disambiguator = None
        if database_service:
            try:
                from services.entity_disambiguator import EntityDisambiguator
                self.entity_disambiguator = EntityDisambiguator(database_service)
                logger.info("✅ EntityDisambiguator initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize EntityDisambiguator: {e}")
        
        # Semantic Entity Matcher (جدید - هوشمندتر)
        self.semantic_matcher = None
        self._semantic_matcher_initialized = False
        
        # Entity Learning Service (یادگیری از اصلاحات کاربر)
        self.learning_service = None
        try:
            from services.entity_learning_service import get_learning_service
            self.learning_service = get_learning_service()
            logger.info("✅ EntityLearningService initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize EntityLearningService: {e}")
        
        # آمار استفاده
        self.stats = {
            'total_queries': 0,
            'static_used': 0,
            'llm_used': 0,
            'static_success': 0,
            'llm_success': 0,
            'fuzzy_match_used': 0,
            'dynamic_entity_found': 0,
            'disambiguation_needed': 0,
            'disambiguation_success': 0
        }
    
    # ========== Semantic Entity Matcher ==========
    
    async def _initialize_semantic_matcher(self, embedding_client=None):
        """مقداردهی اولیه Semantic Entity Matcher"""
        if self._semantic_matcher_initialized:
            return
        
        try:
            from services.semantic_entity_matcher import SemanticEntityMatcher
            
            # اگر embedding_client داده نشده، سعی کن از Persian Embedding استفاده کنی
            if embedding_client is None:
                try:
                    from services.persian_embedding_service import PersianEmbeddingClient
                    embedding_client = PersianEmbeddingClient()
                    logger.info("✅ PersianEmbeddingClient created for SemanticEntityMatcher")
                except Exception as e:
                    logger.info(f"⚠️ PersianEmbeddingClient not available: {e}, using fuzzy matching only")
                    embedding_client = None
            
            self.semantic_matcher = SemanticEntityMatcher(
                embedding_client=embedding_client,
                database_service=self.database_service,
                use_cache=True
            )
            self._semantic_matcher_initialized = True
            
            if embedding_client:
                logger.info("✅ SemanticEntityMatcher initialized with embedding support")
            else:
                logger.info("✅ SemanticEntityMatcher initialized (fuzzy-only mode)")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize SemanticEntityMatcher: {e}")
            self.semantic_matcher = None
    
    async def semantic_match_entity(
        self,
        query_entity: str,
        query: str,
        table_name: str = "masaref2_sheet1",
        embedding_client=None
    ) -> Optional[str]:
        """
        Entity matching با استفاده از Semantic Similarity
        
        Args:
            query_entity: entity استخراج شده از query
            query: سوال کامل کاربر
            table_name: نام جدول
            embedding_client: کلاینت embedding
            
        Returns:
            بهترین entity match یا None
        """
        # Initialize semantic matcher if needed
        if not self._semantic_matcher_initialized:
            await self._initialize_semantic_matcher(embedding_client)
        
        if not self.semantic_matcher:
            logger.warning("⚠️ SemanticEntityMatcher not available, using fuzzy matching")
            return self.fuzzy_match_entity(query_entity, table_name, query=query)
        
        try:
            # Load entity embeddings if needed
            await self.semantic_matcher.load_entity_embeddings(table_name)
            
            # Find best match
            result = await self.semantic_matcher.find_best_match(
                query_entity=query_entity,
                query=query,
                table_name=table_name
            )
            
            if result.confidence >= self.semantic_matcher.LOW_CONFIDENCE:
                self.stats['dynamic_entity_found'] += 1
                
                if result.needs_confirmation:
                    self.stats['disambiguation_needed'] += 1
                    logger.warning(f"⚠️ [SEMANTIC] Needs confirmation: {result.confirmation_message}")
                
                logger.info(
                    f"✅ [SEMANTIC MATCH] '{query_entity}' -> '{result.matched_entity}' "
                    f"(confidence: {result.confidence:.3f}, method: {result.method})"
                )
                return result.matched_entity
            else:
                logger.warning(
                    f"❌ [SEMANTIC] Low confidence match for '{query_entity}': "
                    f"{result.confidence:.3f}"
                )
                return None
                
        except Exception as e:
            logger.error(f"❌ Semantic matching failed: {e}")
            # Fallback to fuzzy matching
            return self.fuzzy_match_entity(query_entity, table_name, query=query)
    
    # ========== Dynamic Entity Discovery ==========
    
    async def load_entities_from_database(self, table_name: str = "incomes_sheet1") -> None:
        """
        بارگذاری entity های موجود از دیتابیس
        
        این متد مقادیر unique ستون‌های عنوان_دستگاه و عنوان_جزء را از دیتابیس می‌خواند
        و در کش ذخیره می‌کند برای fuzzy matching
        """
        import time
        current_time = time.time()
        
        # بررسی TTL کش
        if current_time - self._last_cache_update < self._cache_ttl:
            return
        
        if not self.database_service:
            logger.warning("Database service not available for entity loading")
            return
        
        try:
            # خواندن entity های unique
            entity_query = f"""
                SELECT DISTINCT "عنوان_دستگاه" 
                FROM {table_name} 
                WHERE "عنوان_دستگاه" IS NOT NULL
            """
            entity_result = await self.database_service.execute_query(entity_query)
            
            if entity_result and 'rows' in entity_result:
                self._entity_cache[table_name] = {
                    self._normalize_for_match(row.get('عنوان_دستگاه', ''))
                    for row in entity_result['rows']
                    if row.get('عنوان_دستگاه')
                }
                logger.info(f"📦 Loaded {len(self._entity_cache[table_name])} unique entities from {table_name}")
            
            # خواندن component های unique
            component_query = f"""
                SELECT DISTINCT "عنوان_جزء" 
                FROM {table_name} 
                WHERE "عنوان_جزء" IS NOT NULL
            """
            component_result = await self.database_service.execute_query(component_query)
            
            if component_result and 'rows' in component_result:
                self._component_cache[table_name] = {
                    self._normalize_for_match(row.get('عنوان_جزء', ''))
                    for row in component_result['rows']
                    if row.get('عنوان_جزء')
                }
                logger.info(f"📦 Loaded {len(self._component_cache[table_name])} unique components from {table_name}")
            
            self._last_cache_update = current_time
            
        except Exception as e:
            logger.warning(f"Failed to load entities from database: {e}")
    
    def _normalize_for_match(self, text: str) -> str:
        """نرمال‌سازی متن برای مقایسه"""
        if not text:
            return ""
        # حذف کاراکترهای خاص و نرمال‌سازی
        text = text.replace('\u200c', ' ').replace('\u200f', ' ')
        text = text.replace('-', ' ').replace('،', ' ').replace(',', ' ')
        # نرمال‌سازی کاراکترهای فارسی/عربی
        char_map = str.maketrans({
            'ي': 'ی', 'ك': 'ک', 'ة': 'ه', 'ۀ': 'ه',
            'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا', 'آ': 'ا'
        })
        text = text.translate(char_map)
        return ' '.join(text.split()).lower()
    
    def fuzzy_match_entity(
        self, 
        query_entity: str, 
        table_name: str = "incomes_sheet1",
        threshold: float = 0.7,
        collection_name: Optional[str] = None,
        query: str = None
    ) -> Optional[str]:
        """
        Fuzzy matching برای پیدا کردن نزدیک‌ترین entity در دیتابیس
        با استفاده از Entity Disambiguator برای دقت بالاتر
        
        Args:
            query_entity: entity استخراج شده از query
            table_name: نام جدول
            threshold: حداقل شباهت برای match
            collection_name: نام collection برای استفاده از entity mappings
            query: سوال کامل کاربر (برای disambiguation)
            
        Returns:
            نزدیک‌ترین entity یا None
        """
        # ⭐ مرحله 0: بررسی patterns یاد گرفته شده از اصلاحات کاربر
        if self.learning_service:
            learned_entity = self.learning_service.check_learned_pattern(query_entity)
            if learned_entity:
                logger.info(f"📚 [LEARNING] Using learned pattern: '{query_entity}' -> '{learned_entity}'")
                return learned_entity
        
        # بهبود: استفاده از collection-specific entity mappings
        if collection_name:
            try:
                from config.collection_instructions import CollectionInstructions
                mapped_entities = CollectionInstructions.map_entity(query_entity, collection_name)
                if len(mapped_entities) > 1:
                    logger.info(f"📋 Using collection entity mapping: {query_entity} -> {mapped_entities}")
                    # امتحان کردن همه variant ها
                    for variant in mapped_entities:
                        if variant != query_entity:
                            match = self._try_fuzzy_match(variant, table_name, threshold)
                            if match:
                                logger.info(f"✅ Entity mapped: '{query_entity}' -> '{variant}' -> '{match}'")
                                return match
            except Exception as e:
                logger.debug(f"Collection entity mapping failed: {e}")
        
        # استفاده از Entity Disambiguator برای دقت بالاتر
        if self.entity_disambiguator and query:
            try:
                matched_entity, disambiguation_msg, needs_confirmation = self.entity_disambiguator.disambiguate_entity(
                    query_entity=query_entity,
                    query=query,
                    table_name=table_name
                )
                
                if needs_confirmation:
                    self.stats['disambiguation_needed'] += 1
                    logger.warning(f"⚠️ [DISAMBIGUATION] Needs user confirmation for: {query_entity}")
                    logger.warning(f"   Suggested: {matched_entity}")
                    # TODO: در آینده می‌توانیم پیام را به کاربر نمایش دهیم
                    # فعلاً از best match استفاده می‌کنیم
                
                if matched_entity:
                    self.stats['disambiguation_success'] += 1
                    logger.info(f"✅ [DISAMBIGUATION] Matched: '{query_entity}' -> '{matched_entity}'")
                    return matched_entity
                    
            except Exception as e:
                logger.warning(f"⚠️ Entity Disambiguator failed: {e}, falling back to fuzzy match")
        
        # Fallback به fuzzy match معمولی
        return self._try_fuzzy_match(query_entity, table_name, threshold)
    
    def _try_fuzzy_match(self, query_entity: str, table_name: str, threshold: float) -> Optional[str]:
        """تلاش برای fuzzy matching با بررسی دقیق‌تر و جلوگیری از match های نادرست"""
        if table_name not in self._entity_cache:
            return None
        
        normalized_query = self._normalize_for_match(query_entity)
        best_match = None
        best_ratio = 0.0
        best_word_overlap = 0.0
        
        # لیست کلمات کلیدی query (بدون stop words)
        stop_words = {'و', 'در', 'به', 'از', 'با', 'که', 'این', 'آن', 'یک', 'را', 'های', 'ای'}
        query_words = set(normalized_query.split()) - stop_words
        
        # شناسایی کلمات کلیدی اصلی (اولین کلمه معنادار)
        # مثلاً در "معاونت علمی و فناوری"، کلمه کلیدی "معاونت" است
        primary_keywords = set()
        entity_type_words = {'معاونت', 'سازمان', 'وزارت', 'دانشگاه', 'بانک', 'بانك', 'شرکت', 
                            'موسسه', 'ستاد', 'نهاد', 'بنیاد', 'فرهنگستان', 'شورا', 'هیات',
                            'پارک', 'پارك', 'مرکز', 'اداره', 'کمیته', 'صندوق'}
        
        for word in query_words:
            if word in entity_type_words:
                primary_keywords.add(word)
        
        # اگر query خیلی کوتاه است، threshold را افزایش بده
        if len(query_words) <= 2:
            threshold = max(threshold, 0.75)
        
        candidates = []
        
        for db_entity in self._entity_cache[table_name]:
            normalized_db = self._normalize_for_match(db_entity)
            
            # محاسبه similarity ratio
            ratio = SequenceMatcher(None, normalized_query, normalized_db).ratio()
            
            # بررسی word overlap (بدون stop words)
            db_words = set(normalized_db.split()) - stop_words
            
            if len(query_words) == 0:
                continue
            
            word_overlap = len(query_words & db_words) / len(query_words)
            
            # ⭐ شرط جدید: کلمات کلیدی اصلی باید match شوند
            # مثلاً "معاونت" در query باید "معاونت" در entity داشته باشد
            if primary_keywords:
                primary_match = primary_keywords & db_words
                if not primary_match:
                    # اگر کلمه کلیدی اصلی match نشده، این entity را رد کن
                    logger.debug(f"   ❌ Rejected: '{db_entity}' - primary keyword not matched ({primary_keywords})")
                    continue
            
            # محاسبه امتیاز ترکیبی
            # وزن بیشتر به word overlap برای جلوگیری از match های نادرست
            combined_score = (0.4 * ratio) + (0.6 * word_overlap)
            
            # شرایط سخت‌تر برای match:
            if ratio >= threshold:
                # 1. Word overlap باید حداقل 50% باشد
                if word_overlap < 0.50:
                    logger.debug(f"   ❌ Rejected: '{db_entity}' - low word overlap ({word_overlap:.2f})")
                    continue
                
                # 2. اگر query کوتاه است، word overlap باید خیلی بالا باشد
                if len(query_words) <= 2 and word_overlap < 0.70:
                    logger.debug(f"   ❌ Rejected: '{db_entity}' - short query needs high overlap ({word_overlap:.2f})")
                    continue
                
                # 3. اگر ratio پایین است، word overlap باید کامل باشد
                if ratio < 0.75 and word_overlap < 0.80:
                    logger.debug(f"   ❌ Rejected: '{db_entity}' - low ratio needs high overlap (ratio: {ratio:.2f}, overlap: {word_overlap:.2f})")
                    continue
                
                # ذخیره کاندید
                candidates.append({
                    'entity': db_entity,
                    'ratio': ratio,
                    'word_overlap': word_overlap,
                    'combined_score': combined_score
                })
        
        # اگر کاندیدی پیدا شد، بهترین را انتخاب کن
        if candidates:
            # مرتب‌سازی بر اساس combined_score
            candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            best = candidates[0]
            
            # بررسی نهایی: آیا best candidate واقعاً خوب است؟
            if best['combined_score'] >= 0.60:
                best_match = best['entity']
                best_ratio = best['ratio']
                best_word_overlap = best['word_overlap']
                
                self.stats['fuzzy_match_used'] += 1
                logger.info(f"🔍 Fuzzy match: '{query_entity}' -> '{best_match}'")
                logger.info(f"   📊 Scores: ratio={best_ratio:.3f}, word_overlap={best_word_overlap:.3f}, combined={best['combined_score']:.3f}")
                
                # اگر امتیاز بین 0.60 تا 0.80 است، هشدار بده
                if 0.60 <= best['combined_score'] < 0.80:
                    logger.warning(f"⚠️ Medium confidence match - consider asking user for confirmation")
                    # اگر کاندید دوم نزدیک است، هشدار بده
                    if len(candidates) > 1 and (best['combined_score'] - candidates[1]['combined_score']) < 0.15:
                        logger.warning(f"⚠️ Close second candidate: '{candidates[1]['entity']}' (score: {candidates[1]['combined_score']:.3f})")
            else:
                logger.warning(f"⚠️ Best candidate score too low: {best['combined_score']:.3f}")
        
        return best_match
    
    def fuzzy_search_entities_multiple(
        self,
        query_entity: str,
        table_name: str = "incomes_sheet1",
        threshold: float = 0.5,
        max_results: int = 10,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuzzy search برای پیدا کردن تمام entity های مشابه با score
        
        Args:
            query_entity: entity استخراج شده از query
            table_name: نام جدول
            threshold: حداقل شباهت برای match
            max_results: حداکثر تعداد نتایج
            collection_name: نام collection
            
        Returns:
            لیست entity های مشابه با score: [{"entity": "...", "score": 0.8}, ...]
        """
        if table_name not in self._entity_cache:
            return []
        
        normalized_query = self._normalize_for_match(query_entity)
        matches = []
        
        for db_entity in self._entity_cache[table_name]:
            normalized_db = self._normalize_for_match(db_entity)
            ratio = SequenceMatcher(None, normalized_query, normalized_db).ratio()
            
            # بررسی اینکه آیا query_entity در db_entity موجود است (partial match)
            if normalized_query in normalized_db or normalized_db in normalized_query:
                # برای partial matches، score را بالاتر ببر
                ratio = max(ratio, 0.7)
            
            if ratio >= threshold:
                matches.append({
                    "entity": db_entity,
                    "score": ratio
                })
        
        # مرتب‌سازی بر اساس score (نزولی)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # برگرداندن حداکثر max_results نتیجه
        return matches[:max_results]
    
    def fuzzy_match_component(
        self, 
        query_component: str, 
        table_name: str = "incomes_sheet1",
        threshold: float = 0.6
    ) -> Optional[str]:
        """
        Fuzzy matching برای پیدا کردن نزدیک‌ترین component در دیتابیس
        """
        if table_name not in self._component_cache:
            return None
        
        normalized_query = self._normalize_for_match(query_component)
        best_match = None
        best_ratio = 0.0
        
        for db_component in self._component_cache[table_name]:
            ratio = SequenceMatcher(None, normalized_query, db_component).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = db_component
        
        if best_match:
            logger.info(f"🔍 Fuzzy match component: '{query_component}' -> '{best_match}' (ratio: {best_ratio:.2f})")
        
        return best_match
    
    async def extract_entities_with_llm(self, query: str) -> Dict[str, Any]:
        """
        استخراج entity ها با استفاده از LLM
        
        این متد زمانی استفاده می‌شود که روش static confidence پایینی دارد
        """
        if not self.llm_client:
            return {'entity_names': [], 'income_component': None}
        
        prompt = f"""از این سوال فارسی، نام سازمان‌ها/دستگاه‌ها و جزء درآمد را استخراج کن:

سوال: {query}

فقط JSON برگردان:
{{
    "entity_names": ["نام کامل سازمان یا دستگاه"],
    "income_component": "عنوان جزء درآمد یا null"
}}

نکات:
- entity_names باید نام کامل باشد (مثل "گمرک جمهوری اسلامی ایران")
- income_component برای چیزهایی مثل "واگذاری دارایی های سرمایه ای" یا "مالیاتی" است
- اگر پیدا نشد، [] یا null برگردان
"""
        
        try:
            response = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.2
            )
            
            if response.success:
                json_match = re.search(r'\{[^}]+\}', response.text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    self.stats['dynamic_entity_found'] += 1
                    return result
        except Exception as e:
            logger.warning(f"LLM entity extraction failed: {e}")
        
        return {'entity_names': [], 'income_component': None}
    
    # ========== Main Analysis Methods ==========
    
    async def analyze(
        self, 
        query: str, 
        collection_name: str = None, 
        domain_info: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        متد اصلی برای تحلیل query (سازگار با QueryAnalyzer.analyze)
        
        Args:
            query: سوال کاربر
            collection_name: نام collection برای استفاده از entity mappings
            domain_info: اطلاعات domain
        
        Returns:
            {
                'intent_type': str,
                'requires_multi_hop': bool,
                'complexity_score': float,
                'entities': List[str],
                'query_category': str,
                ...
            }
        """
        try:
            # تعیین table_name بر اساس domain
            domain_type = domain_info.get('domain', 'general') if domain_info else 'general'
            table_name = "incomes_sheet1" if domain_type == 'financial' else "incomes_sheet1"
            
            if domain_type == 'financial':
                # برای domain مالی، از analyze_query_async استفاده می‌کنیم
                analysis = await self.analyze_query_async(
                    query=query,
                    table_name=table_name,
                    use_dynamic_matching=True,
                    collection_name=collection_name
                )
                
                # تبدیل به فرمت مورد نیاز
                return {
                    'intent_type': analysis.get('query_category', 'unknown'),
                    'requires_multi_hop': (
                        len(analysis.get('entity_names', [])) > 1 or
                        analysis.get('dimensions', {}).get('asks_sources', False) or
                        analysis.get('cross_table', {}).get('needs_income', False) or
                        analysis.get('query_category') in ['breakdown', 'cross_table', 'comparison']
                    ),
                    'complexity_score': analysis.get('confidence', 0.5),
                    'entities': analysis.get('entity_names', []),
                    'entity_names': analysis.get('entity_names', []),
                    'query_category': analysis.get('query_category', 'simple_sum'),
                    'query_type': analysis.get('query_type', ''),
                    'income_type': analysis.get('income_type', ''),
                    'years': analysis.get('years', []),
                    'filters': analysis.get('filters', {}),
                    'aggregation': analysis.get('aggregation', {}),
                    'dimensions': analysis.get('dimensions', {}),
                    'comparison_info': analysis.get('comparison_info'),  # اضافه کردن comparison_info
                    'original_analysis': analysis,
                    'method': analysis.get('method', 'hybrid'),
                    'fuzzy_enhanced': analysis.get('fuzzy_enhanced', False)
                }
            else:
                # برای domain های دیگر، تحلیل ساده‌تر (delegate به static analyzer)
                return await self.static_analyzer.analyze(query, collection_name, domain_info)
        
        except Exception as e:
            logger.warning(f"Hybrid analyzer failed: {e}")
            # Fallback به static analyzer
            try:
                return await self.static_analyzer.analyze(query, collection_name, domain_info)
            except:
                return None
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        تحلیل query با استفاده از روش ترکیبی (sync wrapper)
        
        Returns:
            Dict با نتایج تحلیل + metadata
        """
        # استفاده از async version
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # اگر در event loop هستیم، باید از async version استفاده کنیم
                # اما برای sync interface، یک task ایجاد می‌کنیم
                import nest_asyncio
                try:
                    nest_asyncio.apply()
                except:
                    pass
                return loop.run_until_complete(self.analyze_query_async(query))
            else:
                return loop.run_until_complete(self.analyze_query_async(query))
        except RuntimeError:
            # اگر event loop وجود ندارد، یک جدید ایجاد می‌کنیم
            return asyncio.run(self.analyze_query_async(query))
    
    async def analyze_query_async(
        self, 
        query: str, 
        table_name: str = "incomes_sheet1",
        use_dynamic_matching: bool = True,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        تحلیل query با استفاده از روش ترکیبی (async)
        
        Args:
            query: سوال کاربر
            table_name: نام جدول برای fuzzy matching
            use_dynamic_matching: استفاده از fuzzy matching داینامیک
            collection_name: نام collection برای entity mappings
        
        Returns:
            Dict با نتایج تحلیل + metadata
        """
        self.stats['total_queries'] += 1
        
        # مرحله 0: بارگذاری entity ها از دیتابیس (اگر fuzzy matching فعال است)
        if use_dynamic_matching and self.database_service:
            await self.load_entities_from_database(table_name)
        
        # مرحله 1: تلاش با روش استاتیک
        static_result = self.static_analyzer.analyze_query(query)
        
        # مرحله 2: استفاده از confidence از static analyzer (اگر موجود باشد)
        confidence = static_result.get('confidence')
        if confidence is None:
            # اگر static analyzer confidence نداشت، خودمان محاسبه می‌کنیم
            confidence = self._calculate_confidence(static_result, query)
        
        static_result['confidence'] = confidence
        static_result['method'] = 'static'
        
        logger.info(f"📊 Static Analysis - Confidence: {confidence:.2f}")
        
        # مرحله 2.5: بهبود نتایج با Fuzzy Matching (همیشه فعال برای entity merging)
        if use_dynamic_matching:
            static_result = await self._enhance_with_fuzzy_matching(
                static_result, query, table_name, collection_name
            )
            # محاسبه مجدد confidence بعد از fuzzy matching
            if static_result.get('fuzzy_enhanced'):
                confidence = min(confidence + 0.15, 0.95)
                static_result['confidence'] = confidence
                logger.info(f"📈 Enhanced confidence after fuzzy matching: {confidence:.2f}")
        
        # مرحله 3: تصمیم‌گیری برای fallback
        if confidence >= self.confidence_threshold:
            # استفاده از نتایج استاتیک (یا enhanced)
            self.stats['static_used'] += 1
            
            # اعتبارسنجی نتایج
            if self._validate_result(static_result, query):
                self.stats['static_success'] += 1
                logger.info("✅ Using static/enhanced results")
                return static_result
            else:
                logger.warning("⚠️ Static results failed validation, trying LLM")
        
        # مرحله 4: Fallback به LLM
        if self.llm_client:
            self.stats['llm_used'] += 1
            logger.info("🔄 Falling back to LLM")
            
            llm_result = await self._analyze_with_llm(query)
            if llm_result:
                self.stats['llm_success'] += 1
                llm_result['method'] = 'llm_fallback'
                llm_result['static_confidence'] = confidence
                
                # بهبود نتایج LLM با fuzzy matching
                if use_dynamic_matching:
                    llm_result = await self._enhance_with_fuzzy_matching(
                        llm_result, query, table_name, collection_name
                    )
                
                return llm_result
        
        # اگر LLM هم در دسترس نبود، نتایج استاتیک را برمی‌گردانیم
        logger.warning("⚠️ LLM not available, returning static results despite low confidence")
        return static_result
    
    async def _enhance_with_fuzzy_matching(
        self, 
        result: Dict[str, Any], 
        query: str,
        table_name: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        بهبود نتایج با استفاده از Fuzzy Matching با مقادیر دیتابیس
        و ترکیب خودکار entity های چند کلمه‌ای
        """
        enhanced = result.copy()
        was_enhanced = False
        
        # بهبود entity names - ترکیب خودکار entity های چند کلمه‌ای
        entity_names = result.get('entity_names', [])
        if entity_names:
            # مرحله 1: ترکیب entity های مرتبط (مثل "دانشگاه" + "امیرکبیر")
            merged_entities = self._merge_related_entities(entity_names, query)
            logger.info(f"🔗 Merged entities: {entity_names} -> {merged_entities}")
            
            # مرحله 2: Semantic + Fuzzy matching با database
            enhanced_entities = []
            for entity in merged_entities:
                matched = None
                
                # ابتدا سعی کن با Semantic Matcher
                if self.semantic_matcher or not self._semantic_matcher_initialized:
                    try:
                        matched = await self.semantic_match_entity(
                            query_entity=entity,
                            query=query,
                            table_name=table_name
                        )
                    except Exception as e:
                        logger.debug(f"Semantic matching failed: {e}")
                
                # اگر semantic match نداشت، از fuzzy استفاده کن
                if not matched:
                    matched = self.fuzzy_match_entity(entity, table_name, collection_name=collection_name, query=query)
                
                if matched:
                    enhanced_entities.append(matched)
                    was_enhanced = True
                    logger.info(f"✅ Entity matched: '{entity}' -> '{matched}'")
                else:
                    # اگر fuzzy match پیدا نشد، سعی کن با ترکیب چند entity match کنی
                    combined_match = await self._try_combined_entity_match(entity, entity_names, query, table_name, collection_name)
                    if combined_match:
                        enhanced_entities.append(combined_match)
                        was_enhanced = True
                        logger.info(f"✅ Combined match: '{entity}' -> '{combined_match}'")
                    else:
                        enhanced_entities.append(entity)
            
            enhanced['entity_names'] = enhanced_entities
        
        # بهبود income component
        income_component = result.get('income_component')
        if income_component:
            matched = self.fuzzy_match_component(income_component, table_name)
            if matched:
                enhanced['income_component'] = matched
                was_enhanced = True
        
        # بازسازی filters با entity های بهبود یافته
        if was_enhanced:
            enhanced['filters'] = self.static_analyzer._build_sql_filters(
                enhanced.get('entity_names', []),
                enhanced.get('income_component'),
                query
            )
            enhanced['fuzzy_enhanced'] = True
            logger.info("✨ Results enhanced with fuzzy matching")
        
        return enhanced
    
    def _merge_related_entities(self, entity_names: List[str], query: str) -> List[str]:
        """
        ترکیب خودکار entity های مرتبط که احتمالاً بخشی از یک entity بزرگتر هستند
        
        مثال: ['دانشگاه', 'امیرکبیر'] -> ['دانشگاه امیرکبیر']
        این متد به صورت داینامیک کار می‌کند و برای همه entity ها قابل استفاده است
        """
        if len(entity_names) <= 1:
            return entity_names
        
        # الگوهای ترکیبی شناخته شده (prefixes)
        prefix_patterns = {
            'دانشگاه': ['دانشگاه'],
            'بنیاد': ['بنیاد'],
            'شرکت': ['شرکت'],
            'سازمان': ['سازمان'],
            'مرکز': ['مرکز'],
            'پارک': ['پارک'],
            'معاونت': ['معاونت'],
            'پژوهشکده': ['پژوهشکده'],
            'ستاد': ['ستاد'],
            'نهاد': ['نهاد'],
            'وزارت': ['وزارت'],
            'انستیتو': ['انستیتو'],
            'آزمایشگاه': ['آزمایشگاه']
        }
        
        merged = []
        i = 0
        used_indices = set()
        
        while i < len(entity_names):
            if i in used_indices:
                i += 1
                continue
            
            current = entity_names[i].strip()
            
            # بررسی اینکه آیا این entity یک prefix است
            is_prefix = False
            prefix_type = None
            for prefix, patterns in prefix_patterns.items():
                if current == prefix or current.startswith(prefix):
                    is_prefix = True
                    prefix_type = prefix
                    break
            
            # اگر prefix است، سعی کن با entity های بعدی ترکیب کنی
            if is_prefix:
                best_combination = current
                best_length = 1
                best_indices = [i]
                
                # سعی کن با entity های بعدی ترکیب کنی (تا 3 entity بعدی)
                for j in range(i + 1, min(i + 4, len(entity_names))):
                    if j in used_indices:
                        continue
                    
                    next_entity = entity_names[j].strip()
                    combined = f"{current} {next_entity}"
                    
                    # بهبود: بررسی اینکه آیا کلمات میانی در query وجود دارند
                    # مثلاً "سازمان ملی استاندارد" که "ملی" بین "سازمان" و "استاندارد" است
                    combined_with_middle = self._extract_combined_with_middle(current, next_entity, query)
                    if combined_with_middle:
                        combined = combined_with_middle
                    
                    # بررسی اینکه آیا این ترکیب در query وجود دارد
                    if self._is_valid_combined_entity(combined, query):
                        # سعی کن با entity بعدی هم ترکیب کنی
                        best_combination = combined
                        best_length = j - i + 1
                        best_indices = list(range(i, j + 1))
                        
                        # بررسی ترکیب با entity بعدی
                        if j + 1 < len(entity_names) and j + 1 not in used_indices:
                            next_next = entity_names[j + 1].strip()
                            triple_combined = f"{combined} {next_next}"
                            if self._is_valid_combined_entity(triple_combined, query):
                                best_combination = triple_combined
                                best_length = j - i + 2
                                best_indices = list(range(i, j + 2))
                                break
                    else:
                        # اگر ترکیب معتبر نیست، break کن
                        break
                
                # اضافه کردن بهترین ترکیب
                merged.append(best_combination)
                used_indices.update(best_indices)
                i += best_length
            else:
                # اگر prefix نیست، به صورت عادی اضافه کن
                merged.append(current)
                used_indices.add(i)
                i += 1
        
        # اگر هیچ ترکیبی انجام نشد، entity های اصلی را برگردان
        if len(merged) == len(entity_names) and all(m == e for m, e in zip(merged, entity_names)):
            return entity_names
        
        logger.info(f"🔗 Merged entities: {entity_names} -> {merged}")
        return merged
    
    def _extract_combined_with_middle(self, first: str, second: str, query: str) -> Optional[str]:
        """
        استخراج ترکیب entity با کلمات میانی از query
        مثال: "سازمان ملی استاندارد" از query که "سازمان" و "استاندارد" جدا هستند
        """
        first_pos = query.find(first)
        second_pos = query.find(second)
        
        if first_pos == -1 or second_pos == -1:
            return None
        
        # اگر second قبل از first است، جایشان را عوض کن
        if second_pos < first_pos:
            first, second = second, first
            first_pos, second_pos = second_pos, first_pos
        
        # استخراج متن بین دو entity
        start = first_pos + len(first)
        end = second_pos
        middle_text = query[start:end].strip()
        
        # اگر متن میانی وجود دارد و معقول است (کوتاه‌تر از 20 کاراکتر)
        if middle_text and len(middle_text) < 20:
            combined = f"{first} {middle_text} {second}"
            # نرمال‌سازی فاصله‌ها
            combined = ' '.join(combined.split())
            return combined
        
        return None
    
    def _is_valid_combined_entity(self, combined: str, query: str) -> bool:
        """
        بررسی اینکه آیا entity ترکیبی معتبر است
        """
        # حذف entity ترکیبی از query و بررسی اینکه آیا query هنوز معنی‌دار است
        query_without_entity = query.replace(combined, '')
        
        # اگر entity ترکیبی در query وجود دارد، معتبر است
        if combined.lower() in query.lower():
            return True
        
        # اگر entity های جداگانه در query وجود دارند، ترکیب معتبر است
        words = combined.split()
        if len(words) >= 2:
            # بررسی اینکه آیا کلمات در query نزدیک هم هستند
            first_word = words[0]
            second_word = words[1]
            if first_word.lower() in query.lower() and second_word.lower() in query.lower():
                # پیدا کردن موقعیت کلمات در query
                first_pos = query.lower().find(first_word.lower())
                second_pos = query.lower().find(second_word.lower())
                
                # اگر کلمات نزدیک هم هستند (حداکثر 10 کاراکتر فاصله)
                if first_pos != -1 and second_pos != -1:
                    distance = abs(second_pos - first_pos - len(first_word))
                    if distance <= 10:
                        return True
        
        return False
    
    async def _try_combined_entity_match(
        self, 
        entity: str, 
        all_entities: List[str],
        query: str,
        table_name: str,
        collection_name: Optional[str] = None
    ) -> Optional[str]:
        """
        تلاش برای پیدا کردن match با ترکیب چند entity
        """
        if table_name not in self._entity_cache:
            return None
        
        # اگر entity خیلی کوتاه است (یک کلمه)، سعی کن با entity های دیگر ترکیب کنی
        if len(entity.split()) == 1:
            for other_entity in all_entities:
                if other_entity != entity:
                    combined = f"{entity} {other_entity}"
                    matched = self.fuzzy_match_entity(combined, table_name, threshold=0.6, collection_name=collection_name, query=query)
                    if matched:
                        return matched
        
        return None
    
    def _calculate_confidence(self, result: Dict[str, Any], query: str) -> float:
        """
        محاسبه confidence score برای نتایج استاتیک
        
        Returns:
            float بین 0.0 تا 1.0
        """
        score = 1.0
        
        # Factor 1: Entity extraction (40% weight)
        entity_names = result.get('entity_names', [])
        if not entity_names:
            score *= 0.2  # اگر entity پیدا نشد، confidence خیلی پایین است
        elif len(entity_names) > 3:
            score *= 0.7  # چند entity ممکن است مشکل باشد
        elif any(' ' in name for name in entity_names):
            # موجودیت‌های چندکلمه‌ای معمولاً خوب استخراج می‌شوند
            score *= 1.0
        else:
            score *= 0.9
        
        # Factor 2: Year extraction (20% weight)
        years = result.get('years', [])
        has_year_in_query = bool(re.search(r'\d{2,4}', query))
        if has_year_in_query and not years:
            score *= 0.3  # سال در query هست ولی پیدا نشد
        elif not has_year_in_query and years:
            score *= 0.8  # سال پیدا شد ولی در query نبود (ممکن است اشتباه باشد)
        elif years:
            score *= 1.0  # سال‌ها درست استخراج شدند
        
        # Factor 3: Query complexity (20% weight)
        word_count = len(query.split())
        if word_count > 25:
            score *= 0.6  # سوالات خیلی طولانی ممکن است پیچیده باشند
        elif word_count > 15:
            score *= 0.8
        elif word_count < 5:
            score *= 0.7  # سوالات خیلی کوتاه ممکن است مبهم باشند
        
        # Factor 4: Component extraction (10% weight)
        income_component = result.get('income_component')
        if 'حاصل از' in query.lower() or 'component' in query.lower():
            if not income_component:
                score *= 0.5  # component در query هست ولی پیدا نشد
        
        # Factor 5: Query category detection (10% weight)
        query_category = result.get('query_category')
        if query_category == 'breakdown' and word_count < 10:
            score *= 0.7  # breakdown queries معمولاً طولانی‌تر هستند
        
        return min(max(score, 0.0), 1.0)
    
    def _validate_result(self, result: Dict[str, Any], query: str) -> bool:
        """
        اعتبارسنجی نتایج استاتیک
        
        Returns:
            True if result is valid, False otherwise
        """
        has_entity = bool(result.get('entity_names'))
        has_component = bool(result.get('income_component'))
        query_category = result.get('query_category', 'simple_sum')
        has_years = bool(result.get('years'))
        
        # بهبود: برای سوالات بودجه‌ای، اگر سال داشته باشیم validation را آسان‌تر می‌کنیم
        # چون ممکن است entity extraction ضعیف باشد اما سال و query_category صحیح باشد
        if has_years and query_category in ['simple_sum', 'top_n', 'breakdown', 'cross_table', 'comparison']:
            # اگر سال و query_category معتبر است، به entity نیاز نیست
            logger.info(f"✅ Validation passed: has years ({result.get('years')}) and valid query_category ({query_category})")
            return True
        
        # بررسی وجود entity یا component (حداقل یکی باید باشد)
        if not has_entity and not has_component:
            # استثنا: سوالات top_n و breakdown ممکن است entity نداشته باشند
            if query_category not in ['top_n', 'breakdown']:
                # بررسی اینکه آیا سوال درباره مجموع کل است
                if 'کل' not in query.lower() and 'همه' not in query.lower():
                    logger.warning(f"⚠️ Validation failed: no entity/component and not a 'total' query")
                    return False
        
        # بررسی format سال‌ها
        for year in result.get('years', []):
            if not re.match(r'^1[34]\d{2}$', str(year)):
                logger.warning(f"Invalid year format: {year}")
                return False
        
        # بررسی consistency
        query_type = result.get('query_type')
        if query_type == 'amount' and not result.get('years'):
            # سوالات amount معمولاً سال دارند
            if 'همه' not in query.lower() and 'کل' not in query.lower():
                # 🔧 CRITICAL: اگر سال ذکر نشده، سال پیش‌فرض 1403 را اضافه کن
                logger.info(f"⚠️ Amount query without year - adding default year 1403")
                result['years'] = ['1403']
        
        return True
    
    async def _analyze_with_llm(self, query: str) -> Optional[Dict[str, Any]]:
        """
        تحلیل query با استفاده از LLM (async)
        
        Returns:
            Dict با نتایج یا None در صورت خطا
        """
        if not self.llm_client:
            logger.error("LLM client not available")
            return None
        
        try:
            # بررسی سریع اینکه آیا vLLM در دسترس است
            # اگر در دسترس نباشد، مستقیماً None برمی‌گردانیم تا به static fallback شود
            try:
                is_available = await self.llm_client.is_available()
                if not is_available:
                    logger.warning("⚠️ vLLM service unavailable, skipping LLM analysis")
                    return None
            except Exception as health_check_error:
                logger.warning(f"⚠️ vLLM health check failed: {health_check_error}, skipping LLM analysis")
                return None
            
            prompt = self._build_llm_prompt(query)
            logger.info(f"📤 Sending query to LLM: {query[:100]}...")
            
            # استفاده از QwenClient.generate_text
            response_obj = await self.llm_client.generate_text(
                prompt=prompt,
                system_prompt="تو یک تحلیلگر متخصص سوالات مالی فارسی هستی. باید سوالات را تحلیل کنی و JSON معتبر برگردانی.",
                max_tokens=500,
                temperature=0.3  # پایین برای دقت بیشتر
            )
            
            if not response_obj.success:
                # اگر error مربوط به connection است، warning بده نه error
                if "connection" in str(response_obj.error).lower() or "unavailable" in str(response_obj.error).lower():
                    logger.warning(f"⚠️ LLM generation failed (service unavailable): {response_obj.error}")
                else:
                    logger.error(f"❌ LLM generation failed: {response_obj.error}")
                return None
            
            response_text = response_obj.text
            logger.debug(f"📥 LLM Response: {response_text[:200]}...")
            
            # Parse JSON response
            result = self._parse_llm_response(response_text, query)
            
            if result:
                logger.info("✅ LLM analysis successful")
                return result
            else:
                logger.warning("⚠️ Failed to parse LLM response")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM analysis failed: {e}", exc_info=True)
            return None
    
    def _build_llm_prompt(self, query: str) -> str:
        """ساخت prompt برای LLM"""
        return f"""تحلیل این سوال مالی را انجام بده و خروجی را به صورت JSON معتبر برگردان:

سوال: {query}

خروجی باید شامل این فیلدها باشد:
{{
    "entity_names": ["لیست نام سازمان‌ها/دستگاه‌ها به صورت عبارات کامل"],
    "years": ["لیست سال‌ها به صورت 4 رقمی مثل 1398"],
    "query_type": "amount|device|sources|amount_and_device",
    "query_category": "simple_sum|top_n|breakdown|cross_table|comparison",
    "income_component": "عنوان جزء درآمد یا null",
    "income_type": "اختصاصی|عمومی|ملی|استانی|کل",
    "aggregation": {{
        "needs_groupby": true/false,
        "group_fields": ["لیست فیلدها"],
        "needs_sort": true/false,
        "sort_direction": "ASC|DESC|null",
        "limit": عدد یا null
    }},
    "comparison_info": {{
        "is_comparison": true/false,
        "entities_to_compare": ["لیست entity ها برای مقایسه"],
        "comparison_metric": "هزینه|درآمد|بودجه|..."
    }}
}}

مهم: 
- entity_names باید عبارات کامل باشند (مثلاً "بنیاد ایران شناسی" نه ["بنیاد", "ایران", "شناسی"])
- years باید به صورت 4 رقمی باشند (مثلاً "1398" نه "98")
- فقط JSON معتبر برگردان، بدون توضیحات اضافی
- اگر چیزی پیدا نشد، از null یا [] استفاده کن
"""
    
    def _parse_llm_response(self, response: str, query: str) -> Optional[Dict[str, Any]]:
        """Parse کردن پاسخ LLM"""
        # تلاش برای استخراج JSON از response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                
                # اعتبارسنجی و normalize کردن
                result = self._normalize_llm_result(result, query)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
        
        return None
    
    def _normalize_llm_result(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """نرمال‌سازی و اعتبارسنجی نتایج LLM"""
        # اطمینان از وجود فیلدهای ضروری
        normalized = {
            'entity_names': result.get('entity_names', []),
            'years': result.get('years', []),
            'query_type': result.get('query_type', 'amount'),
            'query_category': result.get('query_category', 'simple_sum'),
            'income_component': result.get('income_component'),
            'income_type': result.get('income_type', 'کل'),
            'aggregation': result.get('aggregation', {}),
            'dimensions': result.get('dimensions', {}),
            'cross_table': result.get('cross_table', {})
        }
        
        # نرمال‌سازی سال‌ها
        normalized['years'] = [
            self._normalize_year(str(y)) for y in normalized['years']
            if self._normalize_year(str(y))
        ]
        
        # ساخت filters (مثل static analyzer)
        from .query_analyzer import QueryAnalyzer
        temp_analyzer = QueryAnalyzer()
        normalized['filters'] = temp_analyzer._build_sql_filters(
            normalized['entity_names'],
            normalized['income_component'],
            query
        )
        
        # اضافه کردن dimensions و cross_table اگر موجود نباشند
        if 'dimensions' not in normalized or not normalized['dimensions']:
            normalized['dimensions'] = temp_analyzer._detect_multi_dimension(query.lower())
        
        if 'cross_table' not in normalized or not normalized['cross_table']:
            normalized['cross_table'] = temp_analyzer._detect_cross_table_need(query.lower())
        
        # اضافه کردن aggregation اگر موجود نباشد
        if 'aggregation' not in normalized or not normalized['aggregation']:
            normalized['aggregation'] = temp_analyzer._detect_aggregation_type(
                query.lower(),
                normalized['entity_names'],
                normalized['income_component']
            )
        
        # اضافه کردن income_type اگر موجود نباشد
        if 'income_type' not in normalized or not normalized['income_type']:
            normalized['income_type'] = temp_analyzer._detect_income_type(query.lower())
        
        # اضافه کردن query_type اگر موجود نباشد
        if 'query_type' not in normalized or not normalized['query_type']:
            normalized['query_type'] = temp_analyzer._detect_query_type(query.lower())
        
        return normalized
    
    def _normalize_year(self, year_str: str) -> Optional[str]:
        """نرمال‌سازی سال"""
        if not year_str.isdigit():
            return None
        
        length = len(year_str)
        if length == 4:
            return year_str if year_str.startswith(('13', '14')) else None
        if length == 2:
            value = int(year_str)
            base = 1300 if value >= 50 else 1400
            return str(base + value)
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        total = self.stats['total_queries']
        if total == 0:
            return {}
        
        return {
            'total_queries': total,
            'static_usage_rate': self.stats['static_used'] / total,
            'llm_usage_rate': self.stats['llm_used'] / total,
            'static_success_rate': (
                self.stats['static_success'] / self.stats['static_used']
                if self.stats['static_used'] > 0 else 0
            ),
            'llm_success_rate': (
                self.stats['llm_success'] / self.stats['llm_used']
                if self.stats['llm_used'] > 0 else 0
            ),
            'fuzzy_match_rate': self.stats['fuzzy_match_used'] / total,
            'dynamic_entity_rate': self.stats['dynamic_entity_found'] / total,
            'entity_cache_size': sum(len(v) for v in self._entity_cache.values()),
            'component_cache_size': sum(len(v) for v in self._component_cache.values())
        }
    
    def clear_cache(self):
        """پاک کردن کش entity ها"""
        self._entity_cache.clear()
        self._component_cache.clear()
        self._last_cache_update = 0
        logger.info("🗑️ Entity cache cleared")
    
    def update_confidence_threshold(self, new_threshold: float):
        """به‌روزرسانی threshold"""
        if 0.0 <= new_threshold <= 1.0:
            self.confidence_threshold = new_threshold
            logger.info(f"Updated confidence threshold to {new_threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
    
    # ================== Budget Financial Support ==================
    
    async def analyze_budget_query(
        self,
        query: str,
        table_name: str = "masaref2_sheet1",
        use_llm_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        تحلیل تخصصی سوالات budget_financial با پشتیبانی از LLM fallback
        
        این متد ترکیبی از:
        1. تحلیل استاتیک (QueryAnalyzer.analyze_budget_query)
        2. تشخیص جدول با LLM (در موارد مبهم)
        3. جستجوی سلسله‌مراتبی
        4. Fuzzy matching با entity های دیتابیس
        
        Args:
            query: سوال کاربر
            table_name: نام جدول پیش‌فرض
            use_llm_fallback: استفاده از LLM برای موارد مبهم
            
        Returns:
            تحلیل کامل با اطلاعات budget-specific
        """
        self.stats['total_queries'] += 1
        
        # مرحله 1: تحلیل استاتیک budget
        budget_analysis = self.static_analyzer.analyze_budget_query(query)
        
        # مرحله 2: تشخیص جدول هدف
        table_detection = budget_analysis.get('table_detection', {})
        target_table = self._get_budget_table_name(table_detection.get('table_type', 'masaref'))
        
        # مرحله 3: LLM fallback برای تشخیص جدول (اگر confidence پایین است)
        if use_llm_fallback and self.llm_client:
            if table_detection.get('confidence', 0) < 0.6:
                logger.info("🔄 Using LLM for table detection (low confidence)")
                llm_table_type = await self._detect_table_with_llm(query)
                if llm_table_type:
                    table_detection['table_type'] = llm_table_type
                    table_detection['confidence'] = 0.85
                    table_detection['method'] = 'llm'
                    target_table = self._get_budget_table_name(llm_table_type)
                    budget_analysis['table_detection'] = table_detection
        
        # مرحله 4: بارگذاری entity ها از دیتابیس
        if self.database_service:
            await self.load_entities_from_database(target_table)
        
        # مرحله 5: Fuzzy matching برای entity ها
        entity_names = budget_analysis.get('entity_names', [])
        if entity_names:
            enhanced_entities = []
            for entity in entity_names:
                matched = None
                
                # Semantic matching
                if self.semantic_matcher or not self._semantic_matcher_initialized:
                    try:
                        matched = await self.semantic_match_entity(
                            query_entity=entity,
                            query=query,
                            table_name=target_table
                        )
                    except Exception as e:
                        logger.debug(f"Semantic matching failed: {e}")
                
                # Fuzzy fallback
                if not matched:
                    matched = self.fuzzy_match_entity(
                        entity, target_table, 
                        collection_name='budget_financial',
                        query=query
                    )
                
                if matched:
                    enhanced_entities.append(matched)
                    logger.info(f"✅ [BUDGET] Entity matched: '{entity}' -> '{matched}'")
                else:
                    enhanced_entities.append(entity)
            
            budget_analysis['entity_names'] = enhanced_entities
            budget_analysis['original_entities'] = entity_names
        
        # مرحله 6: تعیین ستون‌های جستجو بر اساس سلسله‌مراتب
        hierarchy = budget_analysis.get('hierarchy', {})
        search_columns = self._get_budget_search_columns(
            table_detection.get('table_type', 'masaref'),
            hierarchy.get('level')
        )
        budget_analysis['search_columns'] = search_columns
        
        # مرحله 7: ساخت فیلترهای SQL
        budget_analysis['filters'] = self._build_budget_filters(budget_analysis, target_table)
        
        # مرحله 8: metadata
        budget_analysis['target_table'] = target_table
        budget_analysis['method'] = 'hybrid_budget'
        
        logger.info(f"📊 [BUDGET] Analysis complete: table={target_table}, entities={budget_analysis.get('entity_names', [])}")
        
        return budget_analysis
    
    def _get_budget_table_name(self, table_type: str) -> str:
        """تبدیل نوع جدول به نام فیزیکی"""
        if table_type == 'manabe':
            return 'manabe_sheet1'
        elif table_type == 'masaref':
            return 'masaref2_sheet1'
        else:
            return 'masaref2_sheet1'  # پیش‌فرض
    
    async def _detect_table_with_llm(self, query: str) -> Optional[str]:
        """تشخیص نوع جدول با LLM"""
        if not self.llm_client:
            return None
        
        try:
            prompt = """سوال زیر درباره بودجه کشور است. تشخیص بده این سوال مربوط به کدام جدول است:

1. MANABE (منابع/درآمد): شامل واگذاری، درآمد، منابع، وصول، حاصل از
2. MASAREF (مصارف/هزینه): شامل برآورد، هزینه، مخارج، مصارف، تملک، اعتبار

سوال: {query}

فقط یکی از این دو کلمه را پاسخ بده: MANABE یا MASAREF""".format(query=query)

            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.generate(
                messages=messages,
                max_tokens=10,
                temperature=0.1
            )
            
            if response and response.get('content'):
                answer = response['content'].strip().upper()
                if 'MANABE' in answer:
                    return 'manabe'
                elif 'MASAREF' in answer:
                    return 'masaref'
        
        except Exception as e:
            logger.warning(f"⚠️ LLM table detection failed: {e}")
        
        return None
    
    def _get_budget_search_columns(self, table_type: str, hierarchy_level: Optional[str]) -> List[str]:
        """
        تعیین ستون‌های جستجو بر اساس نوع جدول و سطح سلسله‌مراتب
        
        MANABE: عنوان_دستگاه_اصلی، عنوان_دستگاه_اجرایی
        MASAREF: قسمت -> بخش -> بند -> دستگاه_اصلی -> دستگاه_اجرایی -> جزء
        """
        if table_type == 'manabe':
            return ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اجرایی']
        
        # MASAREF - جستجوی سلسله‌مراتبی
        hierarchy_columns = {
            'قسمت': ['عنوان_قسمت'],
            'بخش': ['عنوان_بخش'],
            'بند': ['عنوان_بند'],
            'دستگاه اصلی': ['عنوان_دستگاه_اصلی'],
            'دستگاه اجرایی': ['عنوان_دستگاه_اجرایی'],
            'جزء': ['عنوان_جزء']
        }
        
        if hierarchy_level and hierarchy_level in hierarchy_columns:
            return hierarchy_columns[hierarchy_level]
        
        # پیش‌فرض: جستجو در دستگاه اصلی و اجرایی
        return ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اجرایی']
    
    def _build_budget_filters(self, analysis: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """ساخت فیلترهای SQL برای budget queries"""
        filters = analysis.get('filters', {}).copy()
        
        entity_names = analysis.get('entity_names', [])
        years = analysis.get('years', [])
        search_columns = analysis.get('search_columns', [])
        
        # ساخت entity filter
        if entity_names and search_columns:
            entity_conditions = []
            for entity in entity_names:
                for col in search_columns:
                    entity_conditions.append(f'"{col}" ILIKE \'%{entity}%\'')
            
            if entity_conditions:
                filters['entity_filter'] = ' OR '.join(entity_conditions)
        
        # ساخت year filter
        if years:
            year_col = '"سال"' if 'manabe' in table_name else '"سال"'
            if len(years) == 1:
                filters['year_filter'] = f'{year_col} = \'{years[0]}\''
            else:
                years_str = ', '.join([f"'{y}'" for y in years])
                filters['year_filter'] = f'{year_col} IN ({years_str})'
        
        # فیلتر نوع هزینه
        cost_type = analysis.get('cost_type', {})
        if cost_type.get('cost_type') and cost_type['cost_type'] != 'کل':
            filters['cost_type_columns'] = cost_type.get('columns', [])
        
        return filters
    
    async def get_budget_hierarchical_results(
        self,
        query: str,
        analysis: Dict[str, Any],
        max_results_per_level: int = 20
    ) -> Dict[str, Any]:
        """
        جستجوی سلسله‌مراتبی در جداول بودجه
        
        استراتژی:
        1. جستجو در سطح تشخیص داده شده
        2. اگر نتایج زیاد بود، به سطح پایین‌تر برو
        3. اگر نتیجه‌ای نبود، به سطح بالاتر برو
        """
        if not self.database_service:
            return {'success': False, 'error': 'Database service not available'}
        
        table_name = analysis.get('target_table', 'masaref2_sheet1')
        hierarchy = analysis.get('hierarchy', {})
        filters = analysis.get('filters', {})
        
        # ترتیب سطوح برای MASAREF
        masaref_levels = [
            ('قسمت', 'عنوان_قسمت'),
            ('بخش', 'عنوان_بخش'),
            ('بند', 'عنوان_بند'),
            ('دستگاه اصلی', 'عنوان_دستگاه_اصلی'),
            ('دستگاه اجرایی', 'عنوان_دستگاه_اجرایی'),
            ('جزء', 'عنوان_جزء')
        ]
        
        current_level = hierarchy.get('level_priority', 5) - 1  # 0-indexed
        
        # جستجو در سطح فعلی
        level_name, column_name = masaref_levels[current_level]
        results = await self._search_at_level(table_name, column_name, filters, max_results_per_level)
        
        if results.get('success') and results.get('rows'):
            row_count = len(results['rows'])
            
            # اگر نتایج زیاد است، به سطح پایین‌تر برو
            if row_count > max_results_per_level and current_level < len(masaref_levels) - 1:
                logger.info(f"📊 Too many results ({row_count}), drilling down to lower level")
                current_level += 1
                level_name, column_name = masaref_levels[current_level]
                results = await self._search_at_level(table_name, column_name, filters, max_results_per_level)
            
            results['hierarchy_level'] = level_name
            results['column_searched'] = column_name
        
        elif not results.get('rows') and current_level > 0:
            # اگر نتیجه‌ای نبود، به سطح بالاتر برو
            logger.info(f"📊 No results at {level_name}, going up to higher level")
            current_level -= 1
            level_name, column_name = masaref_levels[current_level]
            results = await self._search_at_level(table_name, column_name, filters, max_results_per_level)
            results['hierarchy_level'] = level_name
            results['column_searched'] = column_name
        
        return results
    
    async def _search_at_level(
        self,
        table_name: str,
        column_name: str,
        filters: Dict[str, Any],
        limit: int
    ) -> Dict[str, Any]:
        """جستجو در یک سطح خاص"""
        try:
            where_parts = []
            
            if filters.get('entity_filter'):
                where_parts.append(f"({filters['entity_filter']})")
            
            if filters.get('year_filter'):
                where_parts.append(f"({filters['year_filter']})")
            
            where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
            
            sql = f'''
                SELECT * FROM {table_name}
                WHERE {where_clause}
                LIMIT {limit}
            '''
            
            result = self.database_service.execute_sql_query(sql, collection_name='budget_financial')
            return result
            
        except Exception as e:
            logger.error(f"❌ Search at level failed: {e}")
            return {'success': False, 'error': str(e)}
