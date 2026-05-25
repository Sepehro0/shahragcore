# -*- coding: utf-8 -*-
"""
Query Router
Router برای تصمیم‌گیری بین RAG و Database query
"""

import logging
from typing import Dict, Any, Optional, Literal
import re

from services.qwen_client import QwenClient

logger = logging.getLogger(__name__)


class QueryRouter:
    """Router برای تشخیص نوع query"""
    
    def __init__(self, qwen_client: QwenClient):
        self.qwen_client = qwen_client


    def _normalize_query_text(self, query: str) -> str:
        if not query:
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
        normalized = query.translate(translation_map)
        normalized = ' '.join(normalized.split())
        return normalized

    def _is_booklet_collection(self, collection_name: str) -> bool:
        """بررسی اینکه آیا collection از نوع booklet است"""
        if not collection_name:
            return False
        collection_lower = collection_name.lower()
        return collection_lower.startswith("booklet_bo") or "booklet__bo" in collection_lower or "booklet" in collection_lower
    
    def _is_general_collection(self, collection_name: str) -> bool:
        """بررسی اینکه آیا collection از نوع عمومی است (نه مالی)"""
        if not collection_name:
            return False
        collection_lower = collection_name.lower()
        # Collection های عمومی معمولاً نام‌هایی مثل zinaf_dakheli, karbaran_omomi دارند
        # یا نام‌هایی که شامل "general", "omomi", "dakheli" هستند
        general_keywords = ["zinaf", "karbaran", "omomi", "dakheli", "general", "public"]
        return any(keyword in collection_lower for keyword in general_keywords)
    
    async def route_query(
        self,
        user_query: str,
        collection_name: str,
        has_database: bool = True
    ) -> Dict[str, Any]:
        """مسیریابی query"""
        try:
            # اگر دیتابیس موجود نیست، فقط RAG
            if not has_database:
                return {
                    "primary_path": "rag",
                    "secondary_path": None,
                    "confidence": 1.0,
                    "reason": "No database available"
                }
            
            # بررسی ویژه برای booklet collections
            is_booklet = self._is_booklet_collection(collection_name)
            normalized_query = self._normalize_query_text(user_query)
            
            if is_booklet:
                # اگر query شامل کد دقیق است، حتماً database
                has_exact_code = bool(re.search(r'\d{5,}-\d{3,}', normalized_query))
                
                # اگر query خواسته "لیست" یا "همه" یا "تمام" → hybrid (database + RAG)
                wants_list = bool(re.search(r'\b(لیست|همه|تمام|تمامی|کل|چند|چندتا|چندین)\b', normalized_query, re.IGNORECASE))
                
                # اگر query شامل "ماده" و "بند" است → hybrid
                wants_article = bool(re.search(r'\b(ماده|بند|تبصره)\b', normalized_query, re.IGNORECASE))
                
                if has_exact_code:
                    logger.info(f"🔍 Booklet: exact code pattern detected, forcing database route")
                    return {
                        "primary_path": "database",
                        "secondary_path": "rag",  # fallback to RAG if database returns nothing
                        "confidence": 0.95,
                        "reason": "Booklet collection with exact code pattern"
                    }
                elif wants_list:
                    logger.info(f"🔍 Booklet: list query detected, using hybrid route")
                    return {
                        "primary_path": "hybrid",
                        "secondary_path": None,
                        "confidence": 0.85,
                        "reason": "Booklet collection with list query, using hybrid search"
                    }
                elif wants_article:
                    logger.info(f"🔍 Booklet: article/clause query, using hybrid route")
                    return {
                        "primary_path": "hybrid",
                        "secondary_path": None,
                        "confidence": 0.80,
                        "reason": "Booklet collection with article/clause query"
                    }
                else:
                    # برای سوالات عمومی booklet، از RAG استفاده کن
                    logger.info(f"🔍 Booklet: general query, using RAG")
                    return {
                        "primary_path": "rag",
                        "secondary_path": None,
                        "confidence": 0.75,
                        "reason": "Booklet collection with general query"
                    }
            
            # بررسی اینکه آیا collection عمومی است (نه مالی)
            # Collection های عمومی معمولاً نام‌هایی مثل zinaf_dakheli, karbaran_omomi دارند
            is_general_collection = self._is_general_collection(collection_name)
            
            # تحلیل query
            analysis = await self._analyze_query(user_query)
            
            # برای collection های عمومی، threshold را بالاتر می‌بریم
            if is_general_collection:
                # برای collection های عمومی، threshold بالاتر است
                # چون داده‌های آن‌ها معمولاً ساختار جدولی ندارند
                if analysis["database_confidence"] < 0.7:
                    logger.info(f"🔍 General collection detected, forcing RAG route (DB confidence: {analysis['database_confidence']:.2f})")
                    return {
                        "primary_path": "rag",
                        "secondary_path": None,
                        "confidence": analysis["rag_confidence"],
                        "reason": f"General collection - {analysis['reason']}"
                    }
                # اگر database_confidence بالا است، از hybrid استفاده می‌کنیم با fallback
                elif analysis["needs_database"]:
                    logger.info(f"🔍 General collection with high DB confidence, using hybrid with RAG fallback")
                    return {
                        "primary_path": "database",
                        "secondary_path": "rag",  # همیشه fallback به RAG
                        "confidence": analysis["database_confidence"],
                        "reason": f"General collection - {analysis['reason']}"
                    }
            
            # تصمیم‌گیری
            if analysis["needs_database"]:
                if analysis["needs_rag"]:
                    # ترکیبی
                    return {
                        "primary_path": "hybrid",
                        "secondary_path": "rag" if is_general_collection else None,  # برای عمومی fallback
                        "confidence": analysis["confidence"],
                        "reason": analysis["reason"],
                        "database_confidence": analysis["database_confidence"],
                        "rag_confidence": analysis["rag_confidence"]
                    }
                else:
                    # فقط database
                    return {
                        "primary_path": "database",
                        "secondary_path": "rag" if is_general_collection else None,  # برای عمومی fallback
                        "confidence": analysis["database_confidence"],
                        "reason": analysis["reason"]
                    }
            else:
                # فقط RAG
                return {
                    "primary_path": "rag",
                    "secondary_path": None,
                    "confidence": analysis["rag_confidence"],
                    "reason": analysis["reason"]
                }
                
        except Exception as e:
            logger.error(f"Query routing failed: {e}")
            # Fallback to RAG
            return {
                "primary_path": "rag",
                "secondary_path": None,
                "confidence": 0.5,
                "reason": f"Routing error, defaulting to RAG: {str(e)}"
            }
    
    async def _analyze_query(self, user_query: str) -> Dict[str, Any]:
        """تحلیل query برای تشخیص نیاز"""
        
        # الگوهای SQL-oriented (بهبود شده)
        sql_patterns = [
            r'\b(چند|چقدر|تعداد|مجموع|میانگین|حداکثر|حداقل|بیشترین|کمترین)\b',
            r'\b(تملک|دارایی|اعتبارات|هزینه|مصارف|درآمد|درامد|بودجه)\b',  # اضافه کردن الگوهای مالی
            r'\b(در\s*سال|سال\s*های|سال\s*\d{2,4})\b',  # اضافه کردن الگوهای سال
            r'پر\s*هزینه',
            r'\b(که|که در آن|جایی که)\b.*\b(است|می‌باشد|مساوی|بزرگتر|کوچکتر)\b',
            r'\b(فیلتر|فیلتر کن|جستجو کن|نمایش بده)\b',
            r'\b(مقایسه|مقایسه کن|جدول|داده‌ها)\b',
            r'\b(جمع|SUM|COUNT|AVG|MAX|MIN)\b',
            # الگوهای مربوط به کد و شناسه
            r'\b(کد|شماره|سوال\s+با\s+کد|پرسش\s+با\s+کد)\b',
            r'\d{5,}-\d{3,}',  # الگوی کد: 173073-1152
        ]
        
        # الگوهای RAG-oriented
        rag_patterns = [
            r'\b(چیست|چی|کیست|چطور|چگونه|توضیح|معنی|مفهوم)\b',
            r'\b(درباره|راجع به|مربوط به)\b',
            r'\b(متن|محتوا|اسناد|فایل|PDF)\b',
            r'\b(قوانین|مقررات|دستورالعمل)\b',
        ]
        
        normalized_query = self._normalize_query_text(user_query)

        # شمارش الگوها
        sql_score = sum(1 for pattern in sql_patterns if re.search(pattern, normalized_query, re.IGNORECASE))
        rag_score = sum(1 for pattern in rag_patterns if re.search(pattern, normalized_query, re.IGNORECASE))

        # ========== بهبود: تشخیص سریع queries مالی بدون LLM ==========
        financial_keywords = ['تملک', 'دارایی', 'اعتبارات', 'هزینه', 'مصارف', 'درآمد', 'درامد', 'بودجه', 'سرمایه‌ای', 'منابع', 'جاری', 'سرمایه']
        has_financial = any(kw in normalized_query for kw in financial_keywords)
        
        device_keywords = ['پارک', 'ستاد', 'بنیاد', 'معاونت', 'مرکز', 'انستیتو', 'کشور', 'سازمان', 'موسسه', 'مؤسسه', 'دانشگاه', 'وزارت', 'شرکت']
        has_device = any(kw in normalized_query for kw in device_keywords)
        
        has_year = bool(re.search(r'(13|14)\d{2}|\d{2,4}\s*(?:تا|-)\s*\d{2,4}', normalized_query))
        has_number_query = bool(re.search(r'\b(چقدر|چند|مجموع|تعداد|جمع)\b', normalized_query))
        
        # اگر query واضحاً مالی است، از LLM استفاده نکن (سریع‌تر و مطمئن‌تر)
        is_clear_financial_query = has_financial and (has_year or has_device or has_number_query)
        
        # استفاده از LLM فقط برای queries غیرمالی یا مبهم
        if is_clear_financial_query:
            logger.info(f"🚀 [FAST_PATH] Clear financial query detected - skipping LLM analysis")
            llm_analysis = {
                "database_score": 0.9,
                "rag_score": 0.1,
                "reason": "Financial query - fast path"
            }
        else:
            # استفاده از LLM برای تحلیل پیشرفته
            llm_analysis = await self._llm_analyze_query(user_query)

        # ترکیب نتایج
        database_confidence = min(0.9, (sql_score * 0.2) + (llm_analysis.get("database_score", 0) * 0.5))
        rag_confidence = min(0.9, (rag_score * 0.2) + (llm_analysis.get("rag_score", 0) * 0.5))

        # ========== بهبود: تقویت قوی برای queries مالی ==========
        
        # اگر query مالی + (سال یا دستگاه) باشد → حتماً database
        if has_financial and (has_year or has_device):
            # تقویت بسیار قوی
            boosted_confidence = 0.9
            if has_number_query:
                boosted_confidence = 0.95
            database_confidence = max(database_confidence, boosted_confidence)
            logger.info(f"🔍 Financial query detected (financial={has_financial}, year={has_year}, device={has_device}) - boosting database confidence to {boosted_confidence}")
        # ========================================================

        # تقویت اطمینان دیتابیس بر اساس کلیدواژه های مالی (قبلی - برای backward compatibility)
        has_income_keyword = bool(re.search(r'در\s*آمد', normalized_query)) or 'درامد' in normalized_query
        has_year_token = bool(re.search(r'(13|14)\d{2}', normalized_query))
        has_range_token = bool(re.search(r'\d{2,4}\s*(?:تا|-)\s*\d{2,4}', normalized_query))
        if has_income_keyword:
            boosted = 0.7
            if has_year_token:
                boosted = 0.82
            if has_range_token:
                boosted = 0.85
            if 'چه راه' in normalized_query or 'از چه طریقی' in normalized_query or 'چه روشی' in normalized_query:
                boosted = 0.88
            database_confidence = max(database_confidence, boosted)

        # تصمیم‌گیری
        needs_database = database_confidence > 0.4
        needs_rag = rag_confidence > 0.4 and database_confidence < 0.75
        if not needs_database:
            needs_rag = True

        confidence = max(database_confidence, rag_confidence)

        # دلیل
        if has_financial and (has_year or has_device):
            reason = "Financial query with year/device - requires database query"
        elif needs_database and needs_rag:
            reason = "Query needs both database lookup and semantic search"
        elif needs_database:
            reason = "Query needs structured database query"
        else:
            reason = "Query needs semantic search (RAG)"

        return {
            "needs_database": needs_database,
            "needs_rag": needs_rag,
            "confidence": confidence,
            "database_confidence": database_confidence,
            "rag_confidence": rag_confidence,
            "reason": reason
        }
    
    async def _llm_analyze_query(self, user_query: str) -> Dict[str, Any]:
        """تحلیل query با LLM"""
        try:
            prompt = f"""تحلیل کن که این سوال بیشتر نیاز به جستجوی ساختاریافته در دیتابیس دارد یا جستجوی معنایی در اسناد؟

سوال کاربر: {user_query}

پاسخ را به صورت JSON بده:
{{
    "database_score": 0.0-1.0,  // احتمال نیاز به دیتابیس
    "rag_score": 0.0-1.0,       // احتمال نیاز به جستجوی معنایی
    "reason": "توضیح کوتاه"
}}"""
            
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3,
                timeout=30  # 🔧 FIX: کاهش timeout از 120s به 30s
            )
            
            if response.success:
                # استخراج JSON از پاسخ
                import json
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        return {
                            "database_score": float(result.get("database_score", 0)),
                            "rag_score": float(result.get("rag_score", 0)),
                            "reason": result.get("reason", "")
                        }
                    except:
                        pass
            
            # Fallback
            return {
                "database_score": 0.5,
                "rag_score": 0.5,
                "reason": "LLM analysis failed"
            }
            
        except Exception as e:
            logger.warning(f"LLM query analysis failed: {e}")
            return {
                "database_score": 0.5,
                "rag_score": 0.5,
                "reason": "Analysis error"
            }

