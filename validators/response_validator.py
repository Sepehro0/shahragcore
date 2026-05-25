# -*- coding: utf-8 -*-
"""
Response Validation Module
ماژول اعتبارسنجی پاسخ
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from services.qwen_client import QwenClient
import logging

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """سطوح اعتبارسنجی"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    EXPERT = "expert"


class QualityScore(Enum):
    """امتیازات کیفیت"""
    EXCELLENT = 5
    GOOD = 4
    AVERAGE = 3
    POOR = 2
    VERY_POOR = 1


@dataclass
class ValidationResult:
    """نتیجه اعتبارسنجی"""
    is_valid: bool
    quality_score: QualityScore
    confidence: float
    issues: List[str]
    suggestions: List[str]
    metrics: Dict[str, Any]


class ResponseValidator:
    """اعتبارسنج پاسخ"""
    
    def __init__(self):
        self.qwen_client = QwenClient()
        
        # الگوهای تشخیص مشکلات
        self.issue_patterns = {
            'hallucination': [
                r'من نمی‌دانم',
                r'اطلاعاتی ندارم',
                r'نمی‌توانم',
                r'مطمئن نیستم',
                r'احتمالاً',
                r'شاید',
                r'ممکن است'
            ],
            'incomplete': [
                r'\.\.\.',
                r'و غیره',
                r'و غیره',
                r'و موارد مشابه',
                r'و غیره'
            ],
            'contradiction': [
                r'اما از طرفی',
                r'از یک سو',
                r'از سوی دیگر',
                r'در مقابل',
                r'برعکس'
            ],
            'vague': [
                r'چندین',
                r'مختلف',
                r'متنوع',
                r'گوناگون',
                r'متعدد'
            ]
        }
        
        # الگوهای کیفیت بالا
        self.quality_patterns = {
            'specific': [
                r'\d+',  # اعداد مشخص
                r'درصد',
                r'میلیون',
                r'میلیارد',
                r'ریال',
                r'دلار'
            ],
            'structured': [
                r'اول|دوم|سوم',
                r'۱|۲|۳|۴|۵',
                r'•',
                r'\-',
                r'\*'
            ],
            'authoritative': [
                r'طبق',
                r'بر اساس',
                r'مطابق',
                r'طبق قانون',
                r'طبق مقررات'
            ]
        }
    
    async def validate_response(self, query: str, response: str, 
                              sources: List[Dict[str, Any]] = None,
                              validation_level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
        """اعتبارسنجی پاسخ"""
        try:
            # اعتبارسنجی پایه
            basic_validation = self._basic_validation(response)
            
            # اعتبارسنجی محتوا
            content_validation = self._content_validation(response)
            
            # اعتبارسنجی با LLM
            llm_validation = await self._llm_validation(query, response, sources)
            
            # اعتبارسنجی منابع
            source_validation = self._source_validation(response, sources)
            
            # ترکیب نتایج
            validation_result = self._combine_validations(
                basic_validation, content_validation, llm_validation, source_validation
            )
            
            # اعمال سطح اعتبارسنجی
            validation_result = self._apply_validation_level(validation_result, validation_level)
            
            logger.info(f"Response validation completed: {validation_result.quality_score.name}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                quality_score=QualityScore.VERY_POOR,
                confidence=0.0,
                issues=["خطا در اعتبارسنجی"],
                suggestions=["لطفاً دوباره تلاش کنید"],
                metrics={}
            )
    
    def _basic_validation(self, response: str) -> Dict[str, Any]:
        """اعتبارسنجی پایه"""
        issues = []
        suggestions = []
        metrics = {}
        
        # بررسی طول پاسخ
        response_length = len(response.strip())
        metrics['length'] = response_length
        
        if response_length < 10:
            issues.append("پاسخ خیلی کوتاه است")
            suggestions.append("پاسخ را کامل‌تر کنید")
        elif response_length > 5000:
            issues.append("پاسخ خیلی طولانی است")
            suggestions.append("پاسخ را خلاصه‌تر کنید")
        
        # بررسی وجود محتوا
        if not response.strip():
            issues.append("پاسخ خالی است")
            suggestions.append("پاسخی ارائه دهید")
        
        # بررسی وجود اعداد (برای سوالات عددی)
        has_numbers = bool(re.search(r'\d+', response))
        metrics['has_numbers'] = has_numbers
        
        # بررسی وجود علائم نگارشی
        has_punctuation = bool(re.search(r'[.!?]', response))
        metrics['has_punctuation'] = has_punctuation
        
        return {
            'issues': issues,
            'suggestions': suggestions,
            'metrics': metrics
        }
    
    def _content_validation(self, response: str) -> Dict[str, Any]:
        """اعتبارسنجی محتوا"""
        issues = []
        suggestions = []
        metrics = {}
        
        response_lower = response.lower()
        
        # بررسی الگوهای مشکل‌ساز
        for issue_type, patterns in self.issue_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response_lower):
                    if issue_type == 'hallucination':
                        issues.append("پاسخ شامل عدم اطمینان است")
                        suggestions.append("اطلاعات دقیق‌تر ارائه دهید")
                    elif issue_type == 'incomplete':
                        issues.append("پاسخ ناقص به نظر می‌رسد")
                        suggestions.append("پاسخ را کامل کنید")
                    elif issue_type == 'contradiction':
                        issues.append("پاسخ شامل تناقض است")
                        suggestions.append("تناقض را برطرف کنید")
                    elif issue_type == 'vague':
                        issues.append("پاسخ مبهم است")
                        suggestions.append("اطلاعات مشخص‌تر ارائه دهید")
                    break
        
        # بررسی الگوهای کیفیت
        quality_indicators = 0
        for quality_type, patterns in self.quality_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response):
                    quality_indicators += 1
                    break
        
        metrics['quality_indicators'] = quality_indicators
        
        return {
            'issues': issues,
            'suggestions': suggestions,
            'metrics': metrics
        }
    
    async def _llm_validation(self, query: str, response: str, 
                            sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """اعتبارسنجی با LLM"""
        try:
            sources_info = ""
            if sources:
                sources_text = "\n".join([s.get('content', '') for s in sources[:3]])
                sources_info = f"\n\nمنابع:\n{sources_text}"
            
            prompt = f"""
            سوال و پاسخ زیر را اعتبارسنجی کن:

            سوال: {query}
            پاسخ: {response}
            {sources_info}

            لطفاً پاسخ را به صورت JSON ارائه بده:
            {{
                "is_accurate": true/false,
                "is_complete": true/false,
                "is_relevant": true/false,
                "has_hallucination": true/false,
                "quality_score": 1-5,
                "confidence": 0.0-1.0,
                "issues": ["مشکل1", "مشکل2", "..."],
                "suggestions": ["پیشنهاد1", "پیشنهاد2", "..."],
                "strengths": ["قوت1", "قوت2", "..."]
            }}

            فقط JSON برگردان، بدون توضیح اضافی.
            """
            
            llm_response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt="شما یک متخصص اعتبارسنجی پاسخ‌های هوش مصنوعی هستید.",
                max_tokens=1024,
                temperature=0.3
            )
            
            if llm_response.success:
                # تلاش برای پیدا کردن JSON در پاسخ
                json_match = re.search(r'\{.*\}', llm_response.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    logger.warning("Could not extract JSON from LLM validation response")
                    return self._get_default_llm_validation()
            else:
                logger.error(f"LLM validation failed: {llm_response.error}")
                return self._get_default_llm_validation()
                
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return self._get_default_llm_validation()
    
    def _source_validation(self, response: str, sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """اعتبارسنجی منابع"""
        issues = []
        suggestions = []
        metrics = {}
        
        if not sources:
            issues.append("هیچ منبعی ارائه نشده")
            suggestions.append("منابع مرتبط اضافه کنید")
            return {
                'issues': issues,
                'suggestions': suggestions,
                'metrics': {'source_count': 0}
            }
        
        source_count = len(sources)
        metrics['source_count'] = source_count
        
        if source_count < 2:
            issues.append("تعداد منابع کم است")
            suggestions.append("منابع بیشتری اضافه کنید")
        
        # بررسی کیفیت منابع
        high_quality_sources = 0
        for source in sources:
            if isinstance(source, dict):
                content = source.get('content', '')
                if len(content) > 50:  # منبع با محتوای کافی
                    high_quality_sources += 1
        
        metrics['high_quality_sources'] = high_quality_sources
        
        if high_quality_sources < source_count * 0.5:
            issues.append("کیفیت منابع پایین است")
            suggestions.append("منابع با کیفیت بالاتر انتخاب کنید")
        
        return {
            'issues': issues,
            'suggestions': suggestions,
            'metrics': metrics
        }
    
    def _combine_validations(self, basic: Dict[str, Any], content: Dict[str, Any], 
                           llm: Dict[str, Any], source: Dict[str, Any]) -> ValidationResult:
        """ترکیب نتایج اعتبارسنجی"""
        # ترکیب مسائل
        all_issues = basic['issues'] + content['issues'] + llm.get('issues', [])
        
        # ترکیب پیشنهادات
        all_suggestions = basic['suggestions'] + content['suggestions'] + llm.get('suggestions', [])
        
        # ترکیب متریک‌ها
        all_metrics = {
            **basic['metrics'],
            **content['metrics'],
            **llm.get('metrics', {}),
            **source['metrics']
        }
        
        # محاسبه امتیاز کیفیت
        quality_score = self._calculate_quality_score(llm, all_metrics)
        
        # محاسبه اعتماد
        confidence = self._calculate_confidence(llm, all_issues)
        
        # تعیین اعتبار
        is_valid = len(all_issues) == 0 and quality_score.value >= 3
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            confidence=confidence,
            issues=all_issues,
            suggestions=all_suggestions,
            metrics=all_metrics
        )
    
    def _calculate_quality_score(self, llm: Dict[str, Any], metrics: Dict[str, Any]) -> QualityScore:
        """محاسبه امتیاز کیفیت"""
        # استفاده از امتیاز LLM اگر موجود باشد
        if 'quality_score' in llm:
            score = llm['quality_score']
            if score >= 5:
                return QualityScore.EXCELLENT
            elif score >= 4:
                return QualityScore.GOOD
            elif score >= 3:
                return QualityScore.AVERAGE
            elif score >= 2:
                return QualityScore.POOR
            else:
                return QualityScore.VERY_POOR
        
        # محاسبه بر اساس متریک‌ها
        score = 3  # پایه
        
        if metrics.get('has_numbers', False):
            score += 1
        if metrics.get('has_punctuation', False):
            score += 1
        if metrics.get('quality_indicators', 0) > 2:
            score += 1
        if metrics.get('source_count', 0) > 2:
            score += 1
        
        if score >= 5:
            return QualityScore.EXCELLENT
        elif score >= 4:
            return QualityScore.GOOD
        elif score >= 3:
            return QualityScore.AVERAGE
        elif score >= 2:
            return QualityScore.POOR
        else:
            return QualityScore.VERY_POOR
    
    def _calculate_confidence(self, llm: Dict[str, Any], issues: List[str]) -> float:
        """محاسبه اعتماد"""
        # استفاده از اعتماد LLM اگر موجود باشد
        if 'confidence' in llm:
            base_confidence = llm['confidence']
        else:
            base_confidence = 0.7
        
        # کاهش اعتماد بر اساس مسائل
        issue_penalty = len(issues) * 0.1
        
        return max(0.0, min(1.0, base_confidence - issue_penalty))
    
    def _apply_validation_level(self, result: ValidationResult, 
                               level: ValidationLevel) -> ValidationResult:
        """اعمال سطح اعتبارسنجی"""
        if level == ValidationLevel.BASIC:
            # فقط مسائل جدی
            result.issues = [issue for issue in result.issues 
                           if 'خالی' in issue or 'خطا' in issue]
        elif level == ValidationLevel.STRICT:
            # سخت‌گیری بیشتر
            if result.quality_score.value < 4:
                result.is_valid = False
        elif level == ValidationLevel.EXPERT:
            # سخت‌گیری بسیار زیاد
            if result.quality_score.value < 5:
                result.is_valid = False
        
        return result
    
    def _get_default_llm_validation(self) -> Dict[str, Any]:
        """اعتبارسنجی LLM پیش‌فرض"""
        return {
            'is_accurate': True,
            'is_complete': True,
            'is_relevant': True,
            'has_hallucination': False,
            'quality_score': 3,
            'confidence': 0.5,
            'issues': [],
            'suggestions': [],
            'strengths': []
        }


# Global response validator instance
response_validator = ResponseValidator()
