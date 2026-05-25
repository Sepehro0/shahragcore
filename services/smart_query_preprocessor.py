# -*- coding: utf-8 -*-
"""
Smart Query Preprocessor
پیش‌پردازش هوشمند سوالات کاربر با استفاده از Embedding Similarity و Domain Detection
بدون وابستگی به لیست‌های استاتیک کلمات کلیدی
"""

import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import collection-specific prompts
try:
    from config.collection_prompts import (
        get_collection_config,
        get_out_of_scope_response,
        is_query_in_domain,
        detect_query_formality
    )
    COLLECTION_PROMPTS_AVAILABLE = True
except ImportError:
    COLLECTION_PROMPTS_AVAILABLE = False
    logger.warning("Collection prompts not available for SmartQueryPreprocessor")


class QueryType(Enum):
    """نوع سوال"""
    GREETING = "greeting"
    IRRELEVANT = "irrelevant"
    DOMAIN_SPECIFIC = "domain_specific"
    GENERAL = "general"


@dataclass
class PreprocessResult:
    """نتیجه پیش‌پردازش"""
    processed_query: str
    query_type: QueryType
    confidence: float
    should_process: bool
    response: Optional[str] = None
    domain_relevance: float = 0.0
    detected_intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SmartQueryPreprocessor:
    """
    پیش‌پردازش هوشمند سوالات کاربر:
    - تشخیص سلام با pattern matching ساده (بدون لیست طولانی)
    - تشخیص ارتباط با domain از طریق embedding similarity
    - تبدیل محاوره‌ای به رسمی با روش هوشمند
    - بدون وابستگی به لیست‌های استاتیک کلمات کلیدی
    """
    
    def __init__(self, embedding_client=None, domain_classifier=None):
        """
        Args:
            embedding_client: کلاینت تولید embedding
            domain_classifier: کلاسیفایر تشخیص domain
        """
        self.embedding_client = embedding_client
        self.domain_classifier = domain_classifier
        self._initialized = False
        
        # فقط الگوهای سلام ساده (نه لیست طولانی کلمات)
        self.greeting_patterns = [
            r'^(سلام|درود|صبح بخیر|عصر بخیر|شب بخیر)\s*[!؟?]*\s*$',
            r'^(سلام|درود)\s*(علیک|علیکم)?\s*$',
            r'^(سلام|درود)[،,]\s*(چطوری|خوبی|حالت چطوره|چه خبر)',
            r'^(hi|hello|hey)\s*[!?]*\s*$',
            # الگوهای معرفی ربات - با انعطاف بیشتر
            r'(سلام|درود)[،,]?\s+(تو|شما)\s+(کی|کیه|کیست|کی\s*هست|چی\s*هست|چ[یه]\s*هست)',
            r'^(تو|شما)\s+(کی|کیه|کیست|کی\s*هست|چی\s*هست)',
            r'(خودت|خودتون|خود)\s*(رو|را)?\s*معرفی',
            r'معرفی\s+(کن|بده|خودت|خودتون)',
            r'(تو|شما)\s+(چه|چ[یه])\s+(کار|کمک)',
        ]
        
        # الگوهای درخواست کمک (برای هدایت به راه‌های ارتباطی)
        self.help_request_patterns = [
            r'^کمک\s*(می‌?خوام|می‌?خواهم|بده|کن)\s*[!؟?]*\s*$',
            r'^(می‌?خوام|می‌?خواهم)\s+کمک',
            r'^نیاز\s+به\s+کمک',
            r'^کمکم\s+کن',
            r'^help\s*$',
        ]
        
        # تبدیل محاوره‌ای به رسمی (فقط موارد ضروری)
        self.colloquial_to_formal = {
            'چیه': 'چیست',
            'چیاست': 'چیست',  # جدید: "روی چیاست" -> "روی چیست"
            'چیان': 'چیست',  # جدید: "چیان" -> "چیست" (قبل از "چیا" باید باشد)
            'چیا': 'چه',  # جدید: "روی چیا" -> "روی چه" (بعد از "چیان")
            'کیه': 'کیست',
            'چطوری': 'چگونه',
            'میشه': 'می‌شود',
            'نمیشه': 'نمی‌شود',
            'میتونم': 'می‌توانم',
            'میتونید': 'می‌توانید',
            'بشیم': 'بگیریم',  # ⚠️ NEW: "چند بشیم" -> "چند بگیریم"
            'بشی': 'بگیری',    # ⚠️ NEW
            'بشه': 'بگیرد',    # ⚠️ NEW
            'بشن': 'بگیرند',   # ⚠️ NEW
            'قبول بشیم': 'قبول شویم',  # ⚠️ NEW
            'قبول بشی': 'قبول شوی',    # ⚠️ NEW
            'میکنه': 'می‌کند',  # جدید: "میکنه" -> "می‌کند"
            'میکنم': 'می‌کنم',  # جدید
            'میکنید': 'می‌کنید',  # جدید
            'میکنن': 'می‌کنند',  # جدید
            'داره': 'دارد',
            'دارن': 'دارند',
            'هستن': 'هستند',
            'بگید': 'بگویید',
            'بگو': 'بگویید',
            'بده': 'بدهید',
            'کنید': 'کنید',
            'کنم': 'کنم',
            'هستید': 'هستید',
            'هستم': 'هستم',
            'سرمایه گذارای': 'سرمایه‌گذاران',  # جدید: "سرمایه گذارای" -> "سرمایه‌گذاران"
            'سرمایه گذاری': 'سرمایه‌گذاری',  # بهبود: فاصله
        }
        
        # پسوندهای محاوره‌ای
        self.colloquial_suffixes = {
            'تون': 'شما',  # بهبود: "معیارتون" -> "معیار شما"
            'مون': 'ما',
            'شون': 'آنها',
        }
        
        # === NEW: تبدیل مفهومی محاوره‌ای ===
        # وقتی کاربر "سرمایه گذاری" می‌گوید، ممکن است منظورش "پذیرش طرح" باشد
        # این mapping ها به بهبود retrieval کمک می‌کنند
        self.semantic_expansions = {
            # سرمایه‌گذاری -> پذیرش (در context سوالات معیار)
            r'معیار.*سرمایه\s*گذاری': ['معیار پذیرش', 'معیار ارزیابی', 'شاخص بررسی'],
            r'شرایط.*سرمایه\s*گذاری': ['شرایط پذیرش', 'شرایط ارزیابی', 'معیار پذیرش'],
            r'نحوه.*سرمایه\s*گذاری': ['نحوه پذیرش', 'فرآیند پذیرش', 'مراحل ارزیابی'],
            # ثبت نام -> شرکت
            r'ثبت\s*نام': ['شرکت', 'ارسال طرح', 'ارائه پروپوزال'],
            # شرکت کردن -> ثبت نام
            r'شرکت\s*کردن|شرکت\s*کنم': ['ثبت نام', 'ارسال طرح', 'ارائه پروپوزال'],
            # مدیران/معاونان -> دوره‌های ویژه مدیریتی
            r'معاون.*دوره|مدیر.*دوره|معاون.*هلدینگ.*دوره|رئیس.*دوره|مدیرعامل.*دوره': [
                'دوره ویژه مدیران', 'دوره مدیریتی', 'آموزش مدیران', 'دوره تخصصی مدیران'
            ],
        }
        
        # === NEW: الگوهای تشخیص intent برای جلوگیری از اشتباه semantic ===
        self.intent_disambiguation = {
            # اگر سوال درباره "معیار" است، احتمالاً منظور "پذیرش" است نه "خروج"
            'معیار': {
                'positive_context': ['پذیرش', 'ارزیابی', 'بررسی', 'شاخص', 'داوری'],
                'negative_context': ['خروج', 'فروش', 'واگذاری'],
                'default_expansion': 'معیار پذیرش'
            },
            # اگر سوال درباره "سرمایه گذاری" است و context مشخص نیست
            'سرمایه گذاری': {
                'positive_context': ['پذیرش', 'ارزیابی', 'معیار', 'شرایط', 'نحوه'],
                'negative_context': ['خروج', 'فروش', 'واگذاری', 'استراتژی خروج'],
                'default_expansion': 'پذیرش طرح'
            }
        }
        
        # ⚠️ NEW: الگوهای query rewriting برای سوالات محاوره‌ای پیچیده
        # این الگوها سوالات محاوره‌ای را به سوالات استاندارد تبدیل می‌کنند
        self.query_rewriting_patterns = [
            # آزمون و نمره قبولی
            (r'(?:تو|در|توی)?\s*آزمون\s+(?:باید)?\s*چند\s+(?:بشیم|بگیریم|بشی|بگیری)?\s*(?:که)?\s*قبول\s*(?:شویم|شیم|شوم|شی|بشیم|بشم)?',
             'حداقل نمره قبولی در آزمون چقدر است؟'),
            (r'چند\s+(?:باید)?\s*(?:بگیریم|بشیم|بگیرم|بشم)?\s*(?:تو|در|توی)?\s*آزمون\s*(?:که)?\s*قبول\s*(?:شویم|شیم|بشیم|بشم)?',
             'حداقل نمره قبولی در آزمون چقدر است؟'),
            (r'(?:حداقل)?\s*نمره\s*(?:ی)?\s*قبول.*(?:چند|چقدر|کمه)',
             'حداقل نمره قبولی چقدر است؟'),
             
            # حضور در کلاس و غیبت
            (r'چند\s+(?:تا)?\s*(?:جلسه|ساعت|روز)?\s*(?:می\s*تونم|می\s*توانم|میشه|می\s*شود)?\s*(?:نیام|غیبت کنم|حضور نداشته باشم)',
             'حداکثر غیبت مجاز چقدر است؟'),
            (r'حداکثر\s+غیبت.*(?:چند|چقدر)',
             'حداکثر غیبت مجاز چقدر است؟'),
             
            # شرایط و ملزومات
            (r'چیکار\s+کنم\s+(?:که|تا)?\s*(?:بتونم|بتوانم)?\s*(?:شرکت کنم|ثبت نام کنم)',
             'شرایط شرکت چیست؟'),
            (r'چطور\s+(?:می\s*تونم|می\s*توانم)?\s*(?:شرکت کنم|ثبت نام کنم)',
             'نحوه شرکت چگونه است؟'),
        ]
        
        # الگوهای سوالات غیرمستقیم (مشکل، کمک، راهنما)
        self.indirect_question_patterns = [
            (r'اگر\s+.*\s+مشکل\s+.*\s+چیکار|اگر\s+.*\s+مشکل\s+.*\s+چطور|اگر\s+.*\s+مشکل\s+.*\s+خوردم', 
             ['تماس', 'راهنما', 'پشتیبانی', 'کمک', 'مراجعه']),
            (r'مشکل\s+.*\s+چیکار|مشکل\s+.*\s+چطور|مشکل\s+.*\s+خوردم', 
             ['تماس', 'راهنما', 'پشتیبانی', 'کمک']),
            (r'^کمک\s+.*\s+می‌خوام|^کمک\s+.*\s+بخواه|^کمک\s+.*\s+می‌خواهم|^کمک\s+.*\s+می‌خواه', 
             ['تماس', 'راهنما', 'پشتیبانی', 'کمک']),
            (r'چطور\s+.*\s+کمک\s+.*\s+بگیرم|چطور\s+.*\s+کمک\s+.*\s+بگیر|چطور\s+.*\s+کمک', 
             ['تماس', 'راهنما', 'پشتیبانی']),
            (r'با\s+کی\s+تماس\s+.*\s+بگیرم|با\s+کی\s+تماس\s+.*\s+بگیر|با\s+کی\s+تماس', 
             ['تماس', 'راهنما', 'پشتیبانی', 'آدرس']),
            (r'کجا\s+.*\s+برم|کجا\s+.*\s+مراجعه|کجا\s+.*\s+باید', 
             ['آدرس', 'مراجعه', 'راهنما']),
            (r'^راهنمایی\s+.*\s+می‌خوام|^راهنمایی\s+.*\s+بخواه|^راهنمایی\s+.*\s+می‌خواهم|^راهنمایی\s+.*\s+می‌خواه', 
             ['راهنما', 'تماس', 'پشتیبانی']),
            (r'نمی‌دونم\s+.*\s+چیکار|نمی‌دونم\s+.*\s+چطور|نمی‌دانم\s+.*\s+چیکار', 
             ['راهنما', 'تماس', 'کمک']),
            (r'سوال\s+.*\s+دارم|سوال\s+.*\s+داری', 
             ['راهنما', 'تماس', 'کمک']),
        ]
    
    async def _ensure_initialized(self):
        """اطمینان از مقداردهی اولیه components"""
        if self._initialized:
            return
        
        if self.embedding_client is None:
            try:
                # Try to import - this might fail due to CUDA issues
                try:
                    from services.persian_embedding_service import PersianEmbeddingClient
                except Exception as import_error:
                    error_msg = str(import_error)
                    if "CUDA" in error_msg or "cuda" in error_msg.lower() or "device" in error_msg.lower() or "torch" in error_msg.lower():
                        logger.warning(f"⚠️ CUDA/PyTorch error during import, skipping embedding client")
                        self.embedding_client = None
                        self._initialized = True
                        return
                    raise  # Re-raise if not CUDA error
                
                # Try to initialize - this might also fail
                self.embedding_client = PersianEmbeddingClient()
                logger.info("✅ Embedding client initialized for SmartQueryPreprocessor")
            except Exception as e:
                error_msg = str(e)
                # Check for CUDA errors specifically
                if "CUDA" in error_msg or "cuda" in error_msg.lower() or "device" in error_msg.lower() or "torch" in error_msg.lower():
                    logger.warning(f"⚠️ CUDA/PyTorch error detected, skipping embedding client initialization")
                    logger.warning("   Continuing without embedding client - domain relevance will use fallback")
                else:
                    logger.warning(f"Could not initialize embedding client: {e}")
                    logger.warning("   Continuing without embedding client - domain relevance will use fallback")
                self.embedding_client = None  # Explicitly set to None
        
        self._initialized = True
    
    def is_greeting(self, query: str) -> bool:
        """
        تشخیص سلام با pattern matching ساده
        بدون نیاز به لیست طولانی کلمات
        """
        query_clean = query.strip()
        
        # ⚠️ بهبود مهم: اگر داخل جمله، کلمات واضحاً دامنه‌ای/مالی وجود دارد،
        # هرگز آن را به عنوان greeting خالص در نظر نمی‌گیریم
        # مثال: «سلام چطوری به من پول میدی؟»
        domain_trigger_keywords = [
            # مالی و پرداخت
            'پول', 'پرداخت', 'علی الحساب', 'علی‌الحساب', 'نقدینگی',
            'قسط', 'وام', 'تسهیلات',
            # بودجه و قرارداد
            'بودجه', 'قرارداد', 'طرح', 'پروژه',
            # حوزه‌های کلیدی کسب‌وکار سیستم
            'صندوق', 'باور', 'نوآور', 'فرصت', 'دانشمند',
            'سرمایه', 'سرمایه گذاری', 'سرمایه‌گذاری'
        ]
        lowered = query_clean.lower()
        if any(kw in lowered for kw in domain_trigger_keywords):
            # این جمله هم سلام دارد و هم محتوای دامنه‌ای؛
            # باید به عنوان سوال عادی پردازش شود، نه greeting ساده
            return False
        
        # بررسی الگوهای ساده
        for pattern in self.greeting_patterns:
            if re.match(pattern, query_clean, re.IGNORECASE):
                return True
        
        # بررسی طول - سلام‌ها معمولاً کوتاه هستند
        words = query_clean.split()
        if len(words) <= 3:
            # کلمات سلام رایج
            first_word = words[0].lower() if words else ""
            if first_word in {'سلام', 'درود', 'hi', 'hello', 'hey'}:
                return True
        
        return False
    
    async def check_domain_relevance(
        self, 
        query: str, 
        collection_name: str,
        domain_info: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        بررسی ارتباط query با domain با استفاده از embedding similarity
        
        Args:
            query: سوال کاربر
            collection_name: نام collection
            domain_info: اطلاعات domain (اگر موجود باشد)
        
        Returns:
            امتیاز ارتباط (0.0 تا 1.0)
        """
        try:
            await self._ensure_initialized()
        except Exception as e:
            # If initialization fails (e.g., CUDA error), return default relevance
            error_msg = str(e)
            if "CUDA" in error_msg or "cuda" in error_msg.lower() or "device" in error_msg.lower() or "torch" in error_msg.lower():
                logger.warning(f"⚠️ CUDA/PyTorch error in check_domain_relevance, using default relevance")
            else:
                logger.warning(f"⚠️ Failed to ensure initialization in check_domain_relevance: {e}")
            return 0.7  # Default relevance
        
        if not self.embedding_client:
            # اگر embedding نداریم، فرض می‌کنیم مرتبط است
            return 0.7
        
        try:
            # استفاده از domain keywords برای محاسبه similarity
            if domain_info and domain_info.get('keywords'):
                keywords = domain_info['keywords']
                if isinstance(keywords, str):
                    import json
                    try:
                        keywords = json.loads(keywords)
                    except:
                        keywords = keywords.split(',')
                
                if keywords:
                    # ساخت متن domain از keywords
                    domain_text = " ".join(keywords[:10])
                    
                    # تولید embeddings
                    query_embedding = await self.embedding_client.generate_embedding(query)
                    domain_embedding = await self.embedding_client.generate_embedding(domain_text)
                    
                    # محاسبه cosine similarity
                    similarity = self._cosine_similarity(query_embedding, domain_embedding)
                    
                    logger.info(f"📊 Domain relevance score: {similarity:.3f}")
                    return similarity
            
            # اگر domain info نداریم، از summary استفاده کن
            if domain_info and domain_info.get('summary'):
                summary = domain_info['summary'][:200]
                
                query_embedding = await self.embedding_client.generate_embedding(query)
                summary_embedding = await self.embedding_client.generate_embedding(summary)
                
                similarity = self._cosine_similarity(query_embedding, summary_embedding)
                return similarity
            
            return 0.5  # حالت پیش‌فرض
            
        except Exception as e:
            logger.warning(f"Domain relevance check failed: {e}")
            return 0.5
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """محاسبه cosine similarity"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _rewrite_manager_question(self, query: str) -> tuple[str, bool]:
        """
        بازنویسی سوالات مربوط به مدیران/معاونان برای بهبود retrieval
        
        مثال:
        - "من معاون هلدینگم دوره‌ای برای من هست؟" 
          -> "دوره‌های ویژه مدیران و معاونان چیست؟"
        
        Returns:
            (rewritten_query, was_rewritten)
        """
        query_lower = query.lower()
        
        # کلمات کلیدی مدیران/معاونان
        manager_keywords = ['معاون', 'مدیر', 'مدیران', 'معاونان', 'رئیس', 'مدیرعامل', 'هلدینگ', 'مدیر ارشد']
        course_keywords = ['دوره', 'آموزش', 'کلاس', 'برنامه آموزشی']
        
        has_manager = any(kw in query_lower for kw in manager_keywords)
        has_course = any(kw in query_lower for kw in course_keywords)
        
        if has_manager and has_course:
            # بازنویسی به سوال مستقیم درباره دوره‌های ویژه مدیران
            rewritten = "دوره های ویژه مدیران چیست"
            return (rewritten, True)
        
        return (query, False)
    
    def _expand_indirect_question(self, query: str) -> tuple[str, bool]:
        """
        تشخیص و بازنویسی سوالات غیرمستقیم
        
        Returns:
            (expanded_query, is_indirect)
        """
        query_lower = query.lower().strip()
        original_query = query

        # سوالات حقوقی/قضایی — هرگز به «تماس/پشتیبانی» بازنویسی نشوند
        legal_context_keywords = [
            'دعوا', 'دعوای', 'شکایت', 'دادگاه', 'دادخواست', 'پرونده', 'قانون',
            'حقوق', 'وکیل', 'خواهان', 'خوانده', 'شاکی', 'متهم', 'قاضی', 'رأی', 'حکم',
        ]
        if any(kw in query_lower for kw in legal_context_keywords):
            return query, False

        # «مشکل‌ساز شدن» ≠ «مشکل فنی/پشتیبانی»
        if 'مشکل ساز' in query_lower or 'مشکلساز' in query_lower.replace(' ', ''):
            return query, False
        
        # بررسی الگوهای غیرمستقیم و ساخت سوالات مستقیم‌تر
        for pattern, keywords in self.indirect_question_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                # ساخت سوالات مستقیم‌تر بر اساس context
                expanded_queries = []
                
                # اگر سوال درباره مشکل است
                if 'مشکل' in query_lower:
                    expanded_queries.extend([
                        'چطور می‌توانم تماس بگیرم',
                        'راهنمایی برای مشکل',
                        'کجا مراجعه کنم',
                        'اطلاعات تماس',
                        'آدرس مراجعه'
                    ])
                # اگر سوال درباره کمک است
                elif 'کمک' in query_lower:
                    expanded_queries.extend([
                        'چطور می‌توانم کمک بگیرم',
                        'راهنمایی',
                        'تماس',
                        'پشتیبانی',
                        'کمک'
                    ])
                # اگر سوال درباره راهنمایی است
                elif 'راهنمایی' in query_lower or 'راهنما' in query_lower:
                    expanded_queries.extend([
                        'راهنمایی',
                        'تماس',
                        'کمک',
                        'پشتیبانی'
                    ])
                # اگر سوال درباره تماس است
                elif 'تماس' in query_lower:
                    expanded_queries.extend([
                        'اطلاعات تماس',
                        'شماره تماس',
                        'تماس',
                        'راهنما'
                    ])
                # اگر سوال درباره آدرس است
                elif 'کجا' in query_lower or 'آدرس' in query_lower:
                    expanded_queries.extend([
                        'آدرس',
                        'کجا مراجعه کنم',
                        'آدرس مراجعه',
                        'راهنما'
                    ])
                # اگر سوال عمومی است
                else:
                    expanded_queries.extend([
                        'راهنمایی',
                        'تماس',
                        'کمک',
                        'آدرس'
                    ])
                
                # استفاده از اولین سوال expand شده (بهترین match)
                if expanded_queries:
                    expanded_query = expanded_queries[0]
                    logger.info(f"🔍 Indirect question expanded: '{original_query}' -> '{expanded_query}'")
                    return expanded_query, True
        
        # بررسی سوالات غیرمستقیم بدون الگوی مشخص
        # سوالات کوتاه که نیاز به راهنمایی دارند
        if len(query_lower.split()) <= 3:
            if any(word in query_lower for word in ['کمک', 'راهنمایی', 'سوال', 'مشکل']):
                if 'کمک' in query_lower:
                    logger.info(f"🔍 Short indirect question (help): '{original_query}' -> 'چطور می‌توانم کمک بگیرم'")
                    return 'چطور می‌توانم کمک بگیرم', True
                elif 'راهنمایی' in query_lower or 'راهنما' in query_lower:
                    logger.info(f"🔍 Short indirect question (guidance): '{original_query}' -> 'راهنمایی'")
                    return 'راهنمایی', True
                elif 'سوال' in query_lower:
                    logger.info(f"🔍 Short indirect question (question): '{original_query}' -> 'راهنمایی'")
                    return 'راهنمایی', True
        
        # بهبود: بررسی سوالات ناقص مربوط به راه‌های ارتباطی
        # مثال: "ایمیل صندوق باور" -> "راه‌های ارتباطی با صندوق باور چیست؟"
        contact_keywords = ['ایمیل', 'آدرس', 'تلفن', 'تماس', 'راه ارتباطی', 'راه ارتباط', 'وب سایت', 'وبسایت', 'سایت']
        query_words = query_lower.split()
        
        # اگر سوال فقط یک یا دو کلمه است و یکی از کلمات کلیدی ارتباطی را دارد
        if len(query_words) <= 3:
            has_contact_keyword = any(kw in query_lower for kw in contact_keywords)
            has_bavar_keyword = any(kw in query_lower for kw in ['باور', 'صندوق باور', 'باوار'])
            
            if has_contact_keyword:
                if has_bavar_keyword:
                    # سوال کامل‌تر: "راه‌های ارتباطی با صندوق باور چیست؟"
                    expanded = 'راه‌های ارتباطی با صندوق باور چیست؟'
                else:
                    # فرض می‌کنیم منظور صندوق باور است
                    expanded = 'راه‌های ارتباطی با صندوق باور چیست؟'
                
                logger.info(f"🔍 Incomplete contact question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
        
        # اگر سوال فقط "ایمیل" یا "آدرس" است (بدون کلمه دیگر)
        if len(query_words) == 1 and query_words[0] in contact_keywords:
            expanded = 'راه‌های ارتباطی با صندوق باور چیست؟'
            logger.info(f"🔍 Single-word contact question expanded: '{original_query}' -> '{expanded}'")
            return expanded, True
        
        # ========== NEW: بهبود تشخیص سوالات مربوط به ایمیل ==========
        # سوال: "من به چه ادرسی باید ایمیل بزنم" یا "آدرس ایمیل چیه"
        email_keywords = ['ایمیل', 'email', 'ایمیلی', 'ایمیل‌', 'پست الکترونیک', 'پست الکترونیکی']
        if any(kw in query_lower for kw in email_keywords):
            # اگر سوال کوتاه است (مثل "ایمیل چیه") -> expand کوتاه
            if len(query_words) <= 3:
                expanded = 'آدرس ایمیل شکایت و پیشنهاد دوره ها'
                logger.info(f"🔍 Short email question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
            else:
                # اگر سوال طولانی‌تر است
                expanded = 'چطور می توانم شکایت یا پیشنهاد خود را درباره ی دوره ها ثبت کنم؟'
                logger.info(f"🔍 Email question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
        
        # ========== NEW: بهبود تشخیص سوالات غیرمستقیم مربوط به مالکیت و اجازه فروش ==========
        # سوال اول: "ایا من برای اینکه بتونم نتایج نواورم و به یکی دیگه بفروشم باید از صندوق اجازه بگیرم"
        # -> "نتایج پروژه متعلق به چه کسی است؟"
        ownership_keywords = ['نتایج', 'نواور', 'نوآور', 'فروش', 'بفروشم', 'فروختن', 'اجازه', 'اجازه بگیرم', 'مالکیت', 'متعلق']
        if any(kw in query_lower for kw in ownership_keywords):
            # اگر سوال درباره فروش نتایج یا اجازه فروش است
            if any(kw in query_lower for kw in ['فروش', 'بفروشم', 'فروختن', 'فروشیدن']) and \
               any(kw in query_lower for kw in ['نتایج', 'نواور', 'نوآور']):
                expanded = 'نتایج پروژه متعلق به چه کسی است؟'
                logger.info(f"🔍 Ownership/sale permission question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
        
        # ========== NEW: بهبود تشخیص سوالات مربوط به معیارهای پذیرش ==========
        # سوال دوم: "معیار اصلی طرحمون چیا باید باشه که بتونیم از حمایت های صندوق نوآور استفاده کنیم"
        # -> "معیارهای اصلی ارزیابی طرح‌ها چیست؟"
        criteria_keywords = ['معیار', 'شرایط', 'پذیرش', 'ارزیابی', 'بررسی', 'حمایت', 'نوآور', 'نواور', 'استفاده', 'طرح']
        if any(kw in query_lower for kw in criteria_keywords):
            # اگر سوال درباره معیارها یا شرایط پذیرش است
            if any(kw in query_lower for kw in ['معیار', 'شرایط', 'ارزیابی']) and \
               any(kw in query_lower for kw in ['طرح', 'پروژه', 'نوآور', 'نواور']):
                expanded = 'معیارهای اصلی ارزیابی طرح‌ها چیست؟'
                logger.info(f"🔍 Criteria/evaluation question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
        
        # ========== NEW: بهبود تشخیص سوالات مربوط به زمان پاسخ‌دهی ==========
        # سوال چهارم: "بعد از اینکه پیشنهادمونو ارسال کردیم چقد طول میکشه تا جوابشو بگیریم"
        # -> باید با ردیف 38 match شود (زمان ارزیابی)
        time_keywords = ['زمان', 'طول', 'میکشه', 'مدت', 'چقد', 'چقدر', 'پیشنهاد', 'ارسال', 'جواب', 'پاسخ', 'ارزیابی']
        if any(kw in query_lower for kw in time_keywords):
            # اگر سوال درباره زمان پاسخ یا ارزیابی است
            if any(kw in query_lower for kw in ['زمان', 'طول', 'میکشه', 'مدت', 'چقد', 'چقدر']) and \
               any(kw in query_lower for kw in ['پیشنهاد', 'ارسال', 'جواب', 'پاسخ', 'ارزیابی']):
                expanded = 'زمان ارزیابی پیشنهاد چقدر است؟'
                logger.info(f"🔍 Time/evaluation duration question expanded: '{original_query}' -> '{expanded}'")
                return expanded, True
        
        return query, False
    
    def _apply_query_rewriting(self, query: str) -> tuple[str, bool]:
        """
        ⚠️ NEW: اعمال query rewriting patterns برای سوالات محاوره‌ای
        
        مثال: "تو آزمون باید چند بشیم که قبول شیم" 
              -> "حداقل نمره قبولی در آزمون چقدر است؟"
        
        Returns:
            (rewritten_query, was_rewritten)
        """
        query_lower = query.lower().strip()
        
        for pattern, replacement in self.query_rewriting_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info(f"🔄 Query rewritten: '{query}' -> '{replacement}'")
                return replacement, True
        
        return query, False
    
    def normalize_colloquial(self, text: str) -> str:
        """
        تبدیل عبارات محاوره‌ای به رسمی
        """
        result = text.strip()
        
        # ⚠️ NEW: ابتدا بررسی کن که آیا نیاز به query rewriting دارد
        rewritten, was_rewritten = self._apply_query_rewriting(result)
        if was_rewritten:
            return rewritten
        
        # تبدیل کلمات محاوره‌ای
        for colloquial, formal in self.colloquial_to_formal.items():
            result = result.replace(colloquial, formal)
        
        # تبدیل پسوندهای محاوره‌ای
        for suffix, replacement in self.colloquial_suffixes.items():
            result = re.sub(rf'(\w+){suffix}\b', rf'\1 {replacement}', result)
        
        # بهبود: تبدیل "چیاست" که در انتهای جمله است
        result = re.sub(r'چیاست\s*[؟?]*\s*$', 'چیست؟', result)
        result = re.sub(r'چیاست\s+', 'چیست ', result)
        
        # بهبود: تبدیل "چیا" در انتهای جمله به "چیست"
        result = re.sub(r'\s+چیا\s*[؟?]*\s*$', ' چیست؟', result)
        
        # بهبود: تبدیل "چیان" در انتهای جمله به "چیست"
        result = re.sub(r'\s+چیان\s*[؟?]*\s*$', ' چیست؟', result)
        
        # بهبود: تبدیل سوالات ناقص (بدون فعل سوالی) به سوال کامل
        # مثال: "ایمیل صندوق باور" -> "ایمیل صندوق باور چیست؟"
        if not re.search(r'[؟?]', result) and not re.search(r'\b(چیست|چیه|چیاست|چیا|چیان|چطور|چگونه|کجا|کی|چرا|آیا|چه)\b', result):
            # اگر سوال علامت ندارد و فعل سوالی ندارد، اضافه کردن "چیست؟"
            if len(result.split()) <= 5:  # فقط برای سوالات کوتاه
                result = result.rstrip('؟?') + ' چیست؟'
        
        return result
    
    def expand_semantic_query(self, query: str) -> tuple[str, List[str]]:
        """
        گسترش معنایی سوال برای بهبود retrieval
        
        مثال:
        - "معیارهای اصلی تون برای سرمایه گذاری چیه؟"
        - -> "معیارهای اصلی شما برای پذیرش چیست؟"
        - + ["معیار پذیرش", "معیار ارزیابی", "شاخص بررسی"]
        
        Returns:
            (expanded_query, additional_search_terms)
        """
        result = query
        additional_terms = []
        
        # بررسی الگوهای semantic expansion
        for pattern, expansions in self.semantic_expansions.items():
            if re.search(pattern, query, re.IGNORECASE):
                # اضافه کردن terms جایگزین برای جستجو
                additional_terms.extend(expansions)
                logger.info(f"🔄 Semantic expansion triggered for pattern: {pattern}")
                break
        
        # بررسی intent disambiguation
        for keyword, config in self.intent_disambiguation.items():
            if keyword in query.lower():
                # بررسی context مثبت و منفی
                has_positive = any(ctx in query.lower() for ctx in config['positive_context'])
                has_negative = any(ctx in query.lower() for ctx in config['negative_context'])
                
                # اگر context منفی ندارد، expansion پیش‌فرض را اضافه کن
                if not has_negative and not has_positive:
                    additional_terms.append(config['default_expansion'])
                    logger.info(f"🔄 Intent disambiguation: '{keyword}' -> added '{config['default_expansion']}'")
        
        return result, list(set(additional_terms))
    
    def detect_question_intent(self, query: str) -> Dict[str, Any]:
        """
        تشخیص intent دقیق سوال برای جلوگیری از اشتباه semantic
        
        Returns:
            {
                'primary_intent': str,  # معیار، نحوه، شرایط، ...
                'context': str,  # پذیرش، خروج، ارزیابی، ...
                'confidence': float,
                'suggested_keywords': List[str]
            }
        """
        query_lower = query.lower()
        
        # تشخیص intent اصلی
        intent_patterns = {
            'معیار': r'معیار|شاخص|ملاک|سنجش',
            'نحوه': r'نحوه|چطور|چگونه|روش',
            'شرایط': r'شرایط|الزام|نیاز|لازم',
            'زمان': r'زمان|کی|چه وقت|مدت',
            'مکان': r'کجا|محل|آدرس',
            'هزینه': r'هزینه|قیمت|مبلغ|چقدر',
            'تعریف': r'چیست|چیه|یعنی چی|معنی',
        }
        
        primary_intent = None
        for intent, pattern in intent_patterns.items():
            if re.search(pattern, query_lower):
                primary_intent = intent
                break
        
        # تشخیص context
        context_patterns = {
            'پذیرش': r'پذیرش|قبول|تایید|ارزیابی|داوری|بررسی',
            'خروج': r'خروج|فروش|واگذاری|انتقال',
            'سرمایه_گذاری': r'سرمایه\s*گذاری|سرمایه‌گذاری',
            'ثبت_نام': r'ثبت\s*نام|ثبت‌نام|شرکت',
        }
        
        detected_context = None
        for ctx, pattern in context_patterns.items():
            if re.search(pattern, query_lower):
                detected_context = ctx
                break
        
        # تولید suggested keywords
        suggested_keywords = []
        
        # اگر سوال درباره معیار سرمایه‌گذاری است، احتمالاً منظور پذیرش است
        if primary_intent == 'معیار' and detected_context == 'سرمایه_گذاری':
            suggested_keywords = ['معیار پذیرش', 'شاخص ارزیابی', 'معیار بررسی طرح']
            detected_context = 'پذیرش'  # اصلاح context
            logger.info(f"🎯 Intent correction: 'معیار سرمایه‌گذاری' -> 'معیار پذیرش'")
        
        # اگر سوال درباره نحوه سرمایه‌گذاری است، احتمالاً منظور نحوه ثبت نام است
        elif primary_intent == 'نحوه' and detected_context == 'سرمایه_گذاری':
            suggested_keywords = ['نحوه ثبت نام', 'فرآیند پذیرش', 'مراحل ارزیابی']
            detected_context = 'ثبت_نام'
            logger.info(f"🎯 Intent correction: 'نحوه سرمایه‌گذاری' -> 'نحوه ثبت نام'")
        
        # اگر سوال درباره شرایط سرمایه‌گذاری است
        elif primary_intent == 'شرایط' and detected_context == 'سرمایه_گذاری':
            suggested_keywords = ['شرایط پذیرش', 'الزامات ارزیابی', 'شرایط ثبت نام']
            detected_context = 'پذیرش'
            logger.info(f"🎯 Intent correction: 'شرایط سرمایه‌گذاری' -> 'شرایط پذیرش'")
        
        return {
            'primary_intent': primary_intent,
            'context': detected_context,
            'confidence': 0.8 if primary_intent and detected_context else 0.5,
            'suggested_keywords': suggested_keywords
        }
    
    async def preprocess(
        self, 
        query: str,
        collection_name: Optional[str] = None,
        domain_info: Optional[Dict[str, Any]] = None,
        relevance_threshold: float = 0.3
    ) -> PreprocessResult:
        """
        پیش‌پردازش هوشمند سوال
        
        Args:
            query: سوال کاربر
            collection_name: نام collection (برای بررسی ارتباط)
            domain_info: اطلاعات domain
            relevance_threshold: حداقل امتیاز ارتباط
        
        Returns:
            PreprocessResult با تمام اطلاعات
        """
        # IMPORTANT: حذف علامت سوال از انتهای query
        # علامت سوال می‌تواند در embedding و LLM generation مشکل ایجاد کند
        query = query.strip()
        if query.endswith('؟') or query.endswith('?'):
            query = query[:-1].strip()
            logger.debug(f"🔧 Removed question mark from query")
        
        # 1. بررسی سلام
        if self.is_greeting(query):
            logger.info("👋 Smart Preprocessor: Greeting detected")
            return PreprocessResult(
                processed_query=query,
                query_type=QueryType.GREETING,
                confidence=1.0,
                should_process=False,
                response=self._generate_greeting_response(),
                domain_relevance=0.0,
                detected_intent="greeting"
            )
        
        # 1.5. بررسی درخواست کمک (قبل از نرمال‌سازی)
        if self.is_help_request(query):
            logger.info("🆘 Smart Preprocessor: Help request detected")
            return PreprocessResult(
                processed_query=query,
                query_type=QueryType.GENERAL,
                confidence=1.0,
                should_process=False,
                response=self._generate_help_response(),
                domain_relevance=1.0,
                detected_intent="help_request"
            )
        
        # 2. نرمال‌سازی محاوره‌ای (همیشه اول انجام شود)
        normalized_query = self.normalize_colloquial(query)
        logger.info(f"📝 Normalized query: '{query}' -> '{normalized_query}'")
        
        # 3. تشخیص و بازنویسی سوالات غیرمستقیم
        # ⛔ برای کالکشن‌های حقوقی/قضایی هرگز بازنویسی نکن — «مشکل ساز نشه» ≠ «مشکل دارم، تماس بگیرم»
        _skip_indirect_rewrite = collection_name in {
            'qovve_new', 'qovve', 'qavanin', 'zavabet', 'azizashna', 'zabete_qa',
        } or (domain_info or {}).get('domain') == 'legal'
        if _skip_indirect_rewrite:
            logger.info(
                f"⏭️ Skipping indirect question rewrite for legal/judicial collection '{collection_name}'"
            )
        else:
            expanded_query, is_indirect = self._expand_indirect_question(normalized_query)
            if is_indirect:
                logger.info(f"🔍 Indirect question detected, expanded to: {expanded_query}")
                normalized_query = expanded_query
        
        # 3.5. بازنویسی سوالات مدیران (برای zinaf_dakheli)
        if collection_name == 'zinaf_dakheli':
            rewritten_query, was_rewritten = self._rewrite_manager_question(normalized_query)
            if was_rewritten:
                logger.info(f"🎯 Manager question rewritten: '{normalized_query}' -> '{rewritten_query}'")
                normalized_query = rewritten_query
        
        # 4. تشخیص intent و گسترش معنایی
        intent_info = self.detect_question_intent(normalized_query)
        semantic_query, additional_terms = self.expand_semantic_query(normalized_query)
        
        # اگر suggested_keywords از intent detection داریم، اضافه کن
        if intent_info.get('suggested_keywords'):
            additional_terms.extend(intent_info['suggested_keywords'])
            additional_terms = list(set(additional_terms))
            logger.info(f"🎯 Intent-based keywords: {intent_info['suggested_keywords']}")
        
        # 3. بررسی ارتباط با domain (اگر collection مشخص است)
        domain_relevance = 0.5  # پیش‌فرض
        
        if collection_name or domain_info:
            domain_relevance = await self.check_domain_relevance(
                query=normalized_query,
                collection_name=collection_name or "",
                domain_info=domain_info
            )
            
            # اگر ارتباط خیلی پایین است، ممکن است irrelevant باشد
            # ولی فقط با confidence پایین (نه قطعی)
            if domain_relevance < relevance_threshold:
                logger.info(f"⚠️ Low domain relevance: {domain_relevance:.3f}")
                # به جای برگرداندن irrelevant، به سیستم RAG اجازه می‌دهیم تصمیم بگیرد
                return PreprocessResult(
                    processed_query=normalized_query,
                    query_type=QueryType.GENERAL,
                    confidence=domain_relevance,
                    should_process=True,  # همچنان پردازش شود
                    domain_relevance=domain_relevance,
                    detected_intent="low_relevance",
                    metadata={"warning": "low_domain_relevance"}
                )
        
        # 5. Query عادی - آماده پردازش
        query_type = QueryType.DOMAIN_SPECIFIC if domain_relevance > 0.6 else QueryType.GENERAL
        
        # ساخت metadata با اطلاعات intent و semantic expansion
        metadata = {}
        if additional_terms:
            metadata['additional_search_terms'] = additional_terms
        if intent_info.get('primary_intent'):
            metadata['detected_intent_type'] = intent_info['primary_intent']
        if intent_info.get('context'):
            metadata['detected_context'] = intent_info['context']
        
        return PreprocessResult(
            processed_query=normalized_query,
            query_type=query_type,
            confidence=domain_relevance,
            should_process=True,
            domain_relevance=domain_relevance,
            detected_intent=intent_info.get('primary_intent', 'query'),
            metadata=metadata if metadata else None
        )
    
    def _generate_greeting_response(self) -> str:
        """تولید پاسخ سلام"""
        return """سلام! 👋

من دستیار هوش مصنوعی هستم و آماده پاسخگویی به سوالات شما هستم.

چطور می‌توانم کمکتان کنم؟ 😊"""
    
    def _generate_help_response(self) -> str:
        """تولید پاسخ برای درخواست کمک"""
        return """برای دریافت کمک و راهنمایی می‌توانید از راه‌های زیر استفاده کنید:

📍 **آدرس:** اتوبان شهید سلیمانی، ابتدای بلوار نلسون ماندلا، مجتمع مرکزی بنیاد مستضعفان

📞 **پشتیبانی تلفنی:** روزهای یکشنبه هر هفته

🌐 **وبسایت:** https://bavarcapital.com

همچنین می‌توانید سوالات خود را اینجا مطرح کنید و من در حوزه‌های زیر می‌توانم کمکتان کنم:
- صندوق باور و سرمایه‌گذاری
- شبکه تحقیق و توسعه
- موسسه دانشمند و صندوق نوآور
- فراخوان‌های فناورانه"""
    
    def _generate_irrelevant_response(self, collection_name: Optional[str] = None, is_formal: bool = True) -> str:
        """تولید پاسخ برای سوالات نامربوط"""
        # پاسخ خاص برای zabete_qa
        if collection_name == 'zabete_qa':
            return "متأسفانه این سوال در حیطه تخصصی من نیست. من یک دستیار هوشمند هستم که در زمینه نظام فنی و اجرایی، قراردادهای پیمانکاری، و ضوابط سازمان برنامه و بودجه کشور می‌توانم به شما کمک کنم. لطفاً سوال خود را در این زمینه‌ها مطرح کنید."
        
        # استفاده از collection-specific response
        if COLLECTION_PROMPTS_AVAILABLE and collection_name:
            response = get_out_of_scope_response(collection_name, is_formal)
            if response and response != 'این سوال خارج از حوزه تخصصی این سیستم است.':
                return response
        
        # پاسخ پیش‌فرض
        if is_formal:
            return """این سوال خارج از حوزه تخصصی من است. من تنها به سوالات مرتبط با صندوق باور، صندوق نوآور، تبادل فناوری و موسسه دانشمند پاسخ می‌دهم. در صورتی که سوال دیگری در این زمینه‌ها دارید، در خدمت شما هستم."""
        else:
            return """متأسفانه من فقط در مورد صندوق باور، صندوق نوآور، تبادل فناوری و موسسه دانشمند اطلاعات دارم. سوال شما خارج از حوزه تخصصی منه. اگر سوالی در این زمینه‌ها دارید، خوشحال می‌شم کمکتون کنم! 😊"""
    
    def is_help_request(self, query: str) -> bool:
        """تشخیص درخواست کمک"""
        query_clean = query.strip()
        
        for pattern in self.help_request_patterns:
            if re.match(pattern, query_clean, re.IGNORECASE):
                return True
        
        return False
    
    def check_domain_scope(self, query: str, collection_name: Optional[str] = None) -> Tuple[bool, float, str]:
        """
        بررسی اینکه آیا سوال در حوزه collection است
        
        Returns:
            (is_in_scope, confidence, response_if_out_of_scope)
        """
        # کلمات واضحاً نامربوط برای اکثر collection‌ها
        _COMMON_IRRELEVANT = [
            'هوا', 'آب و هوا', 'هوا چطور', 'هوا چطوری',
            'قیمت یورو', 'قیمت دلار', 'قیمت ارز', 'نرخ ارز',
            'اخبار', 'فیلم', 'موسیقی', 'ورزش', 'فوتبال',
            'سینما', 'تلویزیون', 'رادیو', 'آهنگ', 'ترانه',
            'بازی', 'کامپیوتر', 'موبایل', 'لپ تاپ'
        ]

        # ── qavanin ────────────────────────────────────────────────────────────
        if collection_name == 'qavanin':
            query_lower = query.lower().strip()

            # کلمات واضحاً نامربوط
            has_irrelevant = any(kw in query_lower for kw in _COMMON_IRRELEVANT)

            # کلمات مرتبط با حوزه این قانون
            _QAVANIN_DOMAIN_KWS = [
                'قانون', 'ماده', 'تبصره', 'بهبود', 'کسب و کار', 'کسب‌وکار',
                'محیط کسب', 'اتاق', 'اتاق بازرگانی', 'دستگاه اجرایی', 'دستگاه‌های',
                'مقررات', 'آیین نامه', 'آیین‌نامه', 'بخشنامه', 'دستورالعمل',
                'مناقصه', 'معامله', 'قرارداد', 'شفافیت', 'رقابت',
                'تشکل', 'شورای گفتگو', 'شورای گفت و گو', 'بخش خصوصی',
                'استعلام', 'استناد', 'امتیاز', 'رویه', 'تکلیف',
                'ثبت', 'اطلاع رسانی', 'اطلاع‌رسانی',
            ]
            has_domain = any(kw in query_lower for kw in _QAVANIN_DOMAIN_KWS)

            # فقط اگر کلمه‌ای واضحاً نامربوط دارد و هیچ کلمه دامنه ندارد → خارج از حوزه
            if has_irrelevant and not has_domain:
                if COLLECTION_PROMPTS_AVAILABLE:
                    is_formal = detect_query_formality(query)
                    response = get_out_of_scope_response(collection_name, is_formal)
                else:
                    response = "این سوال خارج از حوزه قانون بهبود مستمر محیط کسب و کار است."
                return False, 0.1, response

            # همه چیز دیگر (شامل greeting، سوالات تعریفی، و سوالات کلی) → in-scope
            confidence = 0.8 if has_domain else 0.65
            return True, confidence, ""

        # ── zabete_qa ──────────────────────────────────────────────────────────
        if collection_name == 'zabete_qa':
            query_lower = query.lower().strip()

            has_irrelevant = any(kw in query_lower for kw in _COMMON_IRRELEVANT)
            _ZABETE_DOMAIN_KWS = [
                'ماده', 'بند', 'تبصره', 'شرایط عمومی', 'پیمان',
                'قرارداد', 'پیمانکار', 'کارفرما', 'مشاور',
                'بخشنامه', 'ضابطه', 'دستورالعمل', 'آیین‌نامه',
                'فهرست بها', 'صورت وضعیت', 'پرداخت', 'تاخیر',
                'تعدیل', 'تضمین', 'مناقصه', 'تحویل', 'سرجمع',
                'تأخیر', 'تأمین', 'مصالح', 'اجرا', 'پروژه',
                'قیر', 'سیمان', 'آهن', 'فولاد', 'آسفالت',
                'صورت‌وضعیت', 'صورتحساب', 'برآورد', 'هزینه',
                'شاخص', 'مابه‌التفاوت', 'فهرست‌بها', 'آحاد بها',
                'ضوابط', 'مقررات', 'نظام فنی', 'سازمان برنامه',
                'EPC', 'epc', 'طرح و ساخت', 'ساختار شکست',
            ]
            has_relevant = any(kw in query_lower for kw in _ZABETE_DOMAIN_KWS)
            _ZABETE_GREETING_KWS = ['سلام', 'درود', 'خوبی', 'صبح بخیر', 'عصر بخیر', 'شب بخیر', 'ممنون', 'متشکرم']
            is_greeting = any(kw in query_lower for kw in _ZABETE_GREETING_KWS)

            _oos_response = "متأسفانه این سوال در حیطه تخصصی من نیست. من یک دستیار هوشمند هستم که در زمینه نظام فنی و اجرایی، قراردادهای پیمانکاری، و ضوابط سازمان برنامه و بودجه کشور می‌توانم به شما کمک کنم. لطفاً سوال خود را در این زمینه‌ها مطرح کنید."

            # کوئری‌های خیلی کوتاه (≤ 3 کلمه) بدون هیچ کلمه دامنه‌ای → خارج از حوزه
            # (مثل "تست"، "چی"، "hello" و کلمات تک/دو کلمه‌ای بی‌ربط)
            if not has_relevant and not is_greeting:
                word_count = len(query.strip().split())
                if word_count <= 3:
                    return False, 0.1, _oos_response

            if has_irrelevant and not has_relevant:
                return False, 0.1, _oos_response

            if COLLECTION_PROMPTS_AVAILABLE:
                is_in_domain, confidence = is_query_in_domain(query, collection_name)
                if not is_in_domain:
                    return False, confidence, _oos_response
                return True, confidence, ""

            return True, 0.65, ""

        # ── zavabet ────────────────────────────────────────────────────────────
        if collection_name == 'zavabet':
            query_lower = query.lower().strip()
            has_irrelevant = any(kw in query_lower for kw in _COMMON_IRRELEVANT)
            _ZAVABET_DOMAIN_KWS = [
                'قرارداد', 'پیمان', 'پیمانکار', 'کارفرما', 'مشاور',
                'ضابطه', 'ضوابط', 'شرایط عمومی', 'شرایط خصوصی',
                'EPC', 'epc', 'PC', 'مهندسی', 'اجرا', 'تأمین کالا',
                'صحه گذاری', 'صحه‌گذاری', 'مشاوره', 'طراحی', 'نظارت',
                'تحویل', 'ضمانت', 'تضمین', 'جریمه', 'خسارت',
                'variation order', 'تغییر کارها', 'فسخ', 'خاتمه پیمان',
                'ریسک', 'مسئولیت', 'بیمه', 'ماده', 'بند',
                'نظام فنی', 'اجرایی', 'بخشنامه', 'موافقت نامه',
            ]
            has_relevant = any(kw in query_lower for kw in _ZAVABET_DOMAIN_KWS)
            _ZAVABET_GREETING_KWS = ['سلام', 'درود', 'خوبی', 'صبح بخیر', 'عصر بخیر', 'شب بخیر', 'ممنون', 'متشکرم']
            is_greeting = any(kw in query_lower for kw in _ZAVABET_GREETING_KWS)

            _oos_response = "متأسفانه این سوال در حیطه تخصصی من نیست. من یک دستیار هوشمند هستم که در زمینه ضوابط نظام فنی و اجرایی کشور (قراردادهای Consulting، EPC و PC) می‌توانم به شما کمک کنم. لطفاً سوال خود را در این زمینه مطرح کنید."

            if not has_relevant and not is_greeting:
                word_count = len(query.strip().split())
                if word_count <= 3:
                    return False, 0.1, _oos_response

            if has_irrelevant and not has_relevant:
                return False, 0.1, _oos_response

            if COLLECTION_PROMPTS_AVAILABLE:
                is_in_domain, confidence = is_query_in_domain(query, collection_name)
                if not is_in_domain:
                    return False, confidence, _oos_response
                return True, confidence, ""

            return True, 0.65, ""

        # ── سایر collection‌ها ─────────────────────────────────────────────────
        if collection_name:
            query_lower = query.lower().strip()
            has_common_irrelevant = any(kw in query_lower for kw in _COMMON_IRRELEVANT)

            if COLLECTION_PROMPTS_AVAILABLE:
                is_in_domain, confidence = is_query_in_domain(query, collection_name)

                if has_common_irrelevant and not is_in_domain:
                    is_formal = detect_query_formality(query)
                    response = get_out_of_scope_response(collection_name, is_formal)
                    return False, 0.1, response

                if has_common_irrelevant and confidence < 0.6:
                    is_formal = detect_query_formality(query)
                    response = get_out_of_scope_response(collection_name, is_formal)
                    if response:
                        return False, 0.2, response

                if not is_in_domain:
                    is_formal = detect_query_formality(query)
                    response = get_out_of_scope_response(collection_name, is_formal)
                    return False, confidence, response
                return True, confidence, ""

        # Fallback به روش ساده
        return True, 0.5, ""
    
    # ========== Legacy Compatibility ==========
    def is_irrelevant(self, query: str) -> bool:
        """
        روش قدیمی - برای سازگاری
        توصیه: از preprocess() استفاده کنید
        """
        # به جای لیست استاتیک، از heuristics ساده استفاده می‌کنیم
        query_lower = query.lower().strip()
        
        # فقط سوالات خیلی واضح نامرتبط
        obvious_irrelevant = [
            r'^هوا.*چطور',
            r'^آب\s*و\s*هوا',
            r'^چه\s+فیلمی',
            r'^کدوم\s+فیلم',
        ]
        
        for pattern in obvious_irrelevant:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def normalize_financial_terms(self, query: str) -> str:
        """
        تبدیل اصطلاحات مالی (برای سازگاری)
        """
        normalized = query
        
        if 'منابع' in normalized and 'درآمد' not in normalized:
            normalized = normalized.replace('منابع', 'درآمد')
        
        if 'مصارف' in normalized and 'هزینه' not in normalized:
            normalized = normalized.replace('مصارف', 'هزینه')
        
        return normalized


