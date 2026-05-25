# -*- coding: utf-8 -*-
"""
Domain Analysis and Content Classification
تحلیل domain و طبقه‌بندی محتوا
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from services.qwen_client import QwenClient
import logging

logger = logging.getLogger(__name__)


class DomainAnalyzer:
    """تحلیلگر domain و تولید تنظیمات مناسب"""
    
    def __init__(self):
        self.qwen_client = QwenClient()
        
        # الگوهای domain
        self.domain_patterns = {
            "legal": [
                r"\b(قانون|حقوق|دادگاه|قاضی|وکیل|ماده|تبصره|مقررات|دستور|حکم)\b",
                r"\b(law|legal|court|judge|attorney|article|regulation|order|ruling)\b"
            ],
            "medical": [
                r"\b(پزشک|درمان|بیماری|دارو|جراحی|علائم|تشخیص|درمان|بیمارستان)\b",
                r"\b(doctor|treatment|disease|medicine|surgery|symptoms|diagnosis|hospital)\b"
            ],
            "technical": [
                r"\b(کد|برنامه|نرم‌افزار|الگوریتم|دیتابیس|سرور|شبکه|سیستم)\b",
                r"\b(code|program|software|algorithm|database|server|network|system)\b"
            ],
            "business": [
                r"\b(کسب‌وکار|تجارت|فروش|بازاریابی|مدیریت|استراتژی|سود|زیان)\b",
                r"\b(business|commerce|sales|marketing|management|strategy|profit|loss)\b"
            ],
            "academic": [
                r"\b(تحقیق|مقاله|دانشگاه|تحصیل|آموزش|کتاب|منبع|مرجع)\b",
                r"\b(research|paper|university|education|book|source|reference)\b"
            ],
            "mathematics": [
                r"\b(ریاضی|محاسبه|فرمول|معادله|تابع|مشتق|انتگرال|هندسه)\b",
                r"\b(math|mathematics|calculation|formula|equation|function|derivative|integral|geometry)\b"
            ],
            "financial": [
                r"\b(مالیات|بودجه|درآمد|هزینه|جدول|بخش|فصل|میلیون|میلیارد|ریال)\b",
                r"\b(tax|budget|income|expense|table|section|chapter|million|billion|currency)\b"
            ]
        }
    
    async def analyze_content_domain(self, content_samples: List[str]) -> Dict[str, Any]:
        """تحلیل محتوا برای تعیین domain و ویژگی‌ها"""
        try:
            # ترکیب نمونه‌های محتوا
            combined_content = "\n\n".join(content_samples[:5])  # استفاده از 5 نمونه اول
            content_preview = combined_content[:10000]  # محدود به 10k کاراکتر
            
            # تحلیل مبتنی بر الگو
            pattern_scores = self._analyze_patterns(content_preview)
            
            # تحلیل مبتنی بر LLM
            llm_analysis = await self._llm_domain_analysis(content_preview)
            
            # ترکیب نتایج
            domain_info = self._combine_analyses(pattern_scores, llm_analysis)
            
            logger.info(f"Domain analysis completed: {domain_info['domain']}")
            return domain_info
            
        except Exception as e:
            logger.error(f"Domain analysis failed: {e}")
            return self._get_default_domain_info()
    
    def _analyze_patterns(self, content: str) -> Dict[str, float]:
        """تحلیل محتوا با استفاده از regex patterns"""
        content_lower = content.lower()
        scores = {}
        
        for domain, patterns in self.domain_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches
            scores[domain] = score
        
        # نرمال‌سازی امتیازات
        total_matches = sum(scores.values())
        if total_matches > 0:
            scores = {k: v / total_matches for k, v in scores.items()}
        
        return scores
    
    async def _llm_domain_analysis(self, content: str) -> Dict[str, Any]:
        """استفاده از LLM برای تحلیل domain و ویژگی‌ها"""
        prompt = f"""
        محتوای زیر را تحلیل کن و مشخصات زیر را تعیین کن:

        محتوا:
        {content}

        لطفاً پاسخ را به صورت JSON ارائه بده:
        {{
            "domain": "حوزه اصلی (legal, medical, technical, business, academic, mathematics, financial, general)",
            "subdomain": "زیرحوزه (اختیاری)",
            "language": "زبان اصلی (fa, en, ar)",
            "complexity": "سطح پیچیدگی (beginner, intermediate, advanced, expert)",
            "keywords": ["کلیدواژه1", "کلیدواژه2", "..."],
            "topics": ["موضوع1", "موضوع2", "..."],
            "content_type": "نوع محتوا (documentation, tutorial, reference, academic, legal, medical, financial)",
            "target_audience": "مخاطب هدف (general, professional, academic, technical)",
            "has_formulas": true/false,
            "has_code": true/false,
            "has_tables": true/false,
            "has_examples": true/false,
            "requires_citations": true/false,
            "is_technical": true/false,
            "confidence": 0.0-1.0
        }}

        فقط JSON برگردان، بدون توضیح اضافی.
        """
        
        try:
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt="شما یک تحلیلگر متخصص محتوا هستید که باید محتوا را تحلیل و دسته‌بندی کنید.",
                max_tokens=1024,
                temperature=0.3
            )
            
            if response.success:
                # تلاش برای پیدا کردن JSON در پاسخ
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    logger.warning("Could not extract JSON from LLM response")
                    return self._get_default_llm_analysis()
            else:
                logger.error(f"LLM domain analysis failed: {response.error}")
                return self._get_default_llm_analysis()
                
        except Exception as e:
            logger.error(f"LLM domain analysis failed: {e}")
            return self._get_default_llm_analysis()
    
    def _combine_analyses(self, pattern_scores: Dict[str, float], llm_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """ترکیب تحلیل‌های مبتنی بر الگو و LLM"""
        # دریافت top domain از patterns
        top_pattern_domain = max(pattern_scores.items(), key=lambda x: x[1])[0] if pattern_scores else "general"
        
        # استفاده از تحلیل LLM به عنوان اولویت، fallback به patterns
        domain = llm_analysis.get("domain", top_pattern_domain)
        
        # اطمینان از معتبر بودن domain
        valid_domains = ["legal", "medical", "technical", "business", "academic", "mathematics", "financial", "general"]
        if domain not in valid_domains:
            domain = "general"
        
        return {
            "domain": domain,
            "subdomain": llm_analysis.get("subdomain", ""),
            "language": llm_analysis.get("language", "fa"),
            "complexity": llm_analysis.get("complexity", "intermediate"),
            "keywords": llm_analysis.get("keywords", []),
            "topics": llm_analysis.get("topics", []),
            "content_type": llm_analysis.get("content_type", "documentation"),
            "target_audience": llm_analysis.get("target_audience", "general"),
            "has_formulas": llm_analysis.get("has_formulas", False),
            "has_code": llm_analysis.get("has_code", False),
            "has_tables": llm_analysis.get("has_tables", False),
            "has_examples": llm_analysis.get("has_examples", False),
            "requires_citations": llm_analysis.get("requires_citations", False),
            "is_technical": llm_analysis.get("is_technical", False),
            "confidence": llm_analysis.get("confidence", 0.7),
            "pattern_scores": pattern_scores
        }
    
    def generate_domain_config(self, domain_info: Dict[str, Any]) -> Dict[str, Any]:
        """تولید تنظیمات بر اساس تحلیل domain"""
        domain = domain_info["domain"]
        complexity = domain_info["complexity"]
        
        # تنظیمات پایه
        config = {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "similarity_threshold": 0.7,
            "search_strategy": "balanced",
            "response_style": "professional",
            "citation_style": "minimal",
            "max_sources": 5,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        # تنظیمات مخصوص domain
        if domain == "legal":
            config.update({
                "chunk_size": 1500,  # چانک‌های بزرگتر برای context حقوقی
                "similarity_threshold": 0.8,  # دقت بالاتر مورد نیاز
                "citation_style": "detailed",
                "requires_citations": True,
                "max_sources": 8
            })
        elif domain == "medical":
            config.update({
                "chunk_size": 1200,
                "similarity_threshold": 0.85,  # دقت بسیار بالا
                "citation_style": "detailed",
                "requires_citations": True,
                "max_sources": 6,
                "temperature": 0.3  # دما پایین‌تر برای دقت
            })
        elif domain == "technical":
            config.update({
                "chunk_size": 800,  # چانک‌های کوچک‌تر برای کد
                "similarity_threshold": 0.75,
                "citation_style": "code_friendly",
                "max_sources": 4
            })
        elif domain == "mathematics":
            config.update({
                "chunk_size": 1000,
                "similarity_threshold": 0.8,
                "citation_style": "formula_friendly",
                "max_sources": 5,
                "temperature": 0.5
            })
        elif domain == "financial":
            config.update({
                "chunk_size": 1200,
                "similarity_threshold": 0.85,
                "citation_style": "detailed",
                "requires_citations": True,
                "max_sources": 6,
                "temperature": 0.3,
                "enable_table_extraction": True,
                "enable_numeric_processing": True
            })
        
        # تنظیمات پیچیدگی
        if complexity == "beginner":
            config.update({
                "response_style": "friendly",
                "max_tokens": 1500,
                "temperature": 0.8
            })
        elif complexity == "expert":
            config.update({
                "response_style": "technical",
                "max_tokens": 3000,
                "temperature": 0.4
            })
        
        return config
    
    def _get_default_domain_info(self) -> Dict[str, Any]:
        """اطلاعات domain پیش‌فرض هنگام شکست تحلیل"""
        return {
            "domain": "general",
            "subdomain": "",
            "language": "fa",
            "complexity": "intermediate",
            "keywords": [],
            "topics": [],
            "content_type": "documentation",
            "target_audience": "general",
            "has_formulas": False,
            "has_code": False,
            "has_tables": False,
            "has_examples": False,
            "requires_citations": False,
            "is_technical": False,
            "confidence": 0.5,
            "pattern_scores": {}
        }
    
    def _get_default_llm_analysis(self) -> Dict[str, Any]:
        """تحلیل LLM پیش‌فرض هنگام شکست LLM"""
        return {
            "domain": "general",
            "subdomain": "",
            "language": "fa",
            "complexity": "intermediate",
            "keywords": [],
            "topics": [],
            "content_type": "documentation",
            "target_audience": "general",
            "has_formulas": False,
            "has_code": False,
            "has_tables": False,
            "has_examples": False,
            "requires_citations": False,
            "is_technical": False,
            "confidence": 0.3
        }


# Global domain analyzer instance
domain_analyzer = DomainAnalyzer()
