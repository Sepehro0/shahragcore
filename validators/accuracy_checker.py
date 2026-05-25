# -*- coding: utf-8 -*-
"""
Accuracy Checker Module
ماژول بررسی دقت
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AccuracyLevel(Enum):
    """سطوح دقت"""
    EXACT = "exact"
    CLOSE = "close"
    APPROXIMATE = "approximate"
    INCORRECT = "incorrect"
    UNKNOWN = "unknown"


@dataclass
class AccuracyResult:
    """نتیجه بررسی دقت"""
    accuracy_level: AccuracyLevel
    confidence: float
    matched_values: List[str]
    expected_values: List[str]
    differences: List[Dict[str, Any]]
    suggestions: List[str]


class AccuracyChecker:
    """بررسی‌کننده دقت"""
    
    def __init__(self):
        # الگوهای اعداد
        self.number_patterns = [
            r'[\d,]+(?:\s*میلیون|\s*میلیارد)?\s*ریال',
            r'[\d,]+(?:\s*میلیون|\s*میلیارد)?\s*دلار',
            r'[\d,]+(?:\s*هزار|\s*میلیون|\s*میلیارد)?',
            r'\d+(?:[.,]\d+)?%',
            r'\d+(?:[.,]\d+)?\s*درصد'
        ]
        
        # الگوهای کلیدواژه‌های مهم
        self.keyword_patterns = [
            r'مالیات',
            r'بودجه',
            r'درآمد',
            r'هزینه',
            r'جمع',
            r'کل',
            r'ملی',
            r'استانی',
            r'عمومی',
            r'اختصاصی'
        ]
    
    def check_numeric_accuracy(self, response: str, expected_values: List[str]) -> AccuracyResult:
        """بررسی دقت اعداد"""
        try:
            # استخراج اعداد از پاسخ
            response_numbers = self._extract_numbers(response)
            
            # استخراج اعداد مورد انتظار
            expected_numbers = []
            for expected in expected_values:
                expected_numbers.extend(self._extract_numbers(expected))
            
            if not response_numbers:
                return AccuracyResult(
                    accuracy_level=AccuracyLevel.UNKNOWN,
                    confidence=0.0,
                    matched_values=[],
                    expected_values=expected_numbers,
                    differences=[],
                    suggestions=["هیچ عددی در پاسخ یافت نشد"]
                )
            
            if not expected_numbers:
                return AccuracyResult(
                    accuracy_level=AccuracyLevel.UNKNOWN,
                    confidence=0.0,
                    matched_values=response_numbers,
                    expected_values=[],
                    differences=[],
                    suggestions=["هیچ مقدار مورد انتظاری تعریف نشده"]
                )
            
            # مقایسه اعداد
            matches, differences = self._compare_numbers(response_numbers, expected_numbers)
            
            # تعیین سطح دقت
            accuracy_level = self._determine_accuracy_level(matches, len(expected_numbers))
            
            # محاسبه اعتماد
            confidence = len(matches) / len(expected_numbers) if expected_numbers else 0.0
            
            # تولید پیشنهادات
            suggestions = self._generate_suggestions(matches, differences, accuracy_level)
            
            return AccuracyResult(
                accuracy_level=accuracy_level,
                confidence=confidence,
                matched_values=matches,
                expected_values=expected_numbers,
                differences=differences,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Numeric accuracy check failed: {e}")
            return AccuracyResult(
                accuracy_level=AccuracyLevel.UNKNOWN,
                confidence=0.0,
                matched_values=[],
                expected_values=expected_numbers,
                differences=[],
                suggestions=[f"خطا در بررسی دقت: {str(e)}"]
            )
    
    def check_keyword_accuracy(self, response: str, expected_keywords: List[str]) -> AccuracyResult:
        """بررسی دقت کلیدواژه‌ها"""
        try:
            response_lower = response.lower()
            expected_lower = [kw.lower() for kw in expected_keywords]
            
            matched_keywords = []
            missing_keywords = []
            
            for keyword in expected_lower:
                if keyword in response_lower:
                    matched_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            # تعیین سطح دقت
            if len(matched_keywords) == len(expected_keywords):
                accuracy_level = AccuracyLevel.EXACT
            elif len(matched_keywords) > len(expected_keywords) * 0.8:
                accuracy_level = AccuracyLevel.CLOSE
            elif len(matched_keywords) > len(expected_keywords) * 0.5:
                accuracy_level = AccuracyLevel.APPROXIMATE
            else:
                accuracy_level = AccuracyLevel.INCORRECT
            
            # محاسبه اعتماد
            confidence = len(matched_keywords) / len(expected_keywords) if expected_keywords else 0.0
            
            # تولید پیشنهادات
            suggestions = []
            if missing_keywords:
                suggestions.append(f"کلیدواژه‌های مفقود: {', '.join(missing_keywords)}")
            
            return AccuracyResult(
                accuracy_level=accuracy_level,
                confidence=confidence,
                matched_values=matched_keywords,
                expected_values=expected_keywords,
                differences=[{"missing": missing_keywords}],
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Keyword accuracy check failed: {e}")
            return AccuracyResult(
                accuracy_level=AccuracyLevel.UNKNOWN,
                confidence=0.0,
                matched_values=[],
                expected_values=expected_keywords,
                differences=[],
                suggestions=[f"خطا در بررسی کلیدواژه‌ها: {str(e)}"]
            )
    
    def check_structural_accuracy(self, response: str, expected_structure: Dict[str, Any]) -> AccuracyResult:
        """بررسی دقت ساختاری"""
        try:
            issues = []
            suggestions = []
            
            # بررسی وجود بخش‌های مورد انتظار
            if 'sections' in expected_structure:
                for section in expected_structure['sections']:
                    if section not in response:
                        issues.append(f"بخش '{section}' یافت نشد")
                        suggestions.append(f"بخش '{section}' را اضافه کنید")
            
            # بررسی وجود جداول
            if expected_structure.get('has_tables', False):
                if not re.search(r'\|.*\|', response):
                    issues.append("جدول مورد انتظار یافت نشد")
                    suggestions.append("اطلاعات جدولی اضافه کنید")
            
            # بررسی وجود اعداد
            if expected_structure.get('has_numbers', False):
                if not re.search(r'\d+', response):
                    issues.append("اعداد مورد انتظار یافت نشد")
                    suggestions.append("اطلاعات عددی اضافه کنید")
            
            # تعیین سطح دقت
            if not issues:
                accuracy_level = AccuracyLevel.EXACT
            elif len(issues) <= 2:
                accuracy_level = AccuracyLevel.CLOSE
            elif len(issues) <= 4:
                accuracy_level = AccuracyLevel.APPROXIMATE
            else:
                accuracy_level = AccuracyLevel.INCORRECT
            
            # محاسبه اعتماد
            confidence = max(0.0, 1.0 - len(issues) * 0.2)
            
            return AccuracyResult(
                accuracy_level=accuracy_level,
                confidence=confidence,
                matched_values=[],
                expected_values=[],
                differences=[{"issues": issues}],
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Structural accuracy check failed: {e}")
            return AccuracyResult(
                accuracy_level=AccuracyLevel.UNKNOWN,
                confidence=0.0,
                matched_values=[],
                expected_values=[],
                differences=[],
                suggestions=[f"خطا در بررسی ساختاری: {str(e)}"]
            )
    
    def _extract_numbers(self, text: str) -> List[str]:
        """استخراج اعداد از متن"""
        numbers = []
        for pattern in self.number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            numbers.extend(matches)
        return numbers
    
    def _compare_numbers(self, response_numbers: List[str], expected_numbers: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """مقایسه اعداد"""
        matches = []
        differences = []
        
        for expected in expected_numbers:
            found_match = False
            for response in response_numbers:
                if self._numbers_match(response, expected):
                    matches.append(response)
                    found_match = True
                    break
            
            if not found_match:
                differences.append({
                    "expected": expected,
                    "found": "None",
                    "type": "missing"
                })
        
        return matches, differences
    
    def _numbers_match(self, num1: str, num2: str) -> bool:
        """بررسی تطبیق دو عدد"""
        try:
            # پاکسازی اعداد
            clean1 = self._clean_number(num1)
            clean2 = self._clean_number(num2)
            
            # تبدیل به عدد
            val1 = float(clean1) if clean1 else 0
            val2 = float(clean2) if clean2 else 0
            
            # مقایسه با تلرانس
            tolerance = 0.01  # 1% tolerance
            return abs(val1 - val2) <= max(val1, val2) * tolerance
            
        except (ValueError, TypeError):
            return False
    
    def _clean_number(self, number_str: str) -> str:
        """پاکسازی رشته عددی"""
        # حذف واحدها
        cleaned = re.sub(r'[^\d,.-]', '', number_str)
        # حذف کاما
        cleaned = cleaned.replace(',', '')
        return cleaned
    
    def _determine_accuracy_level(self, matches: List[str], total_expected: int) -> AccuracyLevel:
        """تعیین سطح دقت"""
        if not total_expected:
            return AccuracyLevel.UNKNOWN
        
        match_ratio = len(matches) / total_expected
        
        if match_ratio >= 1.0:
            return AccuracyLevel.EXACT
        elif match_ratio >= 0.8:
            return AccuracyLevel.CLOSE
        elif match_ratio >= 0.5:
            return AccuracyLevel.APPROXIMATE
        else:
            return AccuracyLevel.INCORRECT
    
    def _generate_suggestions(self, matches: List[str], differences: List[Dict[str, Any]], 
                            accuracy_level: AccuracyLevel) -> List[str]:
        """تولید پیشنهادات"""
        suggestions = []
        
        if accuracy_level == AccuracyLevel.EXACT:
            suggestions.append("✅ دقت عالی! تمام مقادیر صحیح هستند.")
        elif accuracy_level == AccuracyLevel.CLOSE:
            suggestions.append("✅ دقت خوب! اکثر مقادیر صحیح هستند.")
        elif accuracy_level == AccuracyLevel.APPROXIMATE:
            suggestions.append("⚠️ دقت متوسط. برخی مقادیر نیاز به بررسی دارند.")
        else:
            suggestions.append("❌ دقت پایین. مقادیر نیاز به تصحیح دارند.")
        
        # پیشنهادات خاص بر اساس تفاوت‌ها
        for diff in differences:
            if diff.get('type') == 'missing':
                suggestions.append(f"مقدار '{diff['expected']}' را اضافه کنید")
        
        return suggestions
    
    def check_comprehensive_accuracy(self, response: str, expected: Dict[str, Any]) -> AccuracyResult:
        """بررسی جامع دقت"""
        try:
            results = []
            
            # بررسی اعداد
            if 'numbers' in expected:
                numeric_result = self.check_numeric_accuracy(response, expected['numbers'])
                results.append(numeric_result)
            
            # بررسی کلیدواژه‌ها
            if 'keywords' in expected:
                keyword_result = self.check_keyword_accuracy(response, expected['keywords'])
                results.append(keyword_result)
            
            # بررسی ساختاری
            if 'structure' in expected:
                structural_result = self.check_structural_accuracy(response, expected['structure'])
                results.append(structural_result)
            
            if not results:
                return AccuracyResult(
                    accuracy_level=AccuracyLevel.UNKNOWN,
                    confidence=0.0,
                    matched_values=[],
                    expected_values=[],
                    differences=[],
                    suggestions=["هیچ معیار دقتی تعریف نشده"]
                )
            
            # ترکیب نتایج
            return self._combine_accuracy_results(results)
            
        except Exception as e:
            logger.error(f"Comprehensive accuracy check failed: {e}")
            return AccuracyResult(
                accuracy_level=AccuracyLevel.UNKNOWN,
                confidence=0.0,
                matched_values=[],
                expected_values=[],
                differences=[],
                suggestions=[f"خطا در بررسی جامع: {str(e)}"]
            )
    
    def _combine_accuracy_results(self, results: List[AccuracyResult]) -> AccuracyResult:
        """ترکیب نتایج دقت"""
        if not results:
            return AccuracyResult(
                accuracy_level=AccuracyLevel.UNKNOWN,
                confidence=0.0,
                matched_values=[],
                expected_values=[],
                differences=[],
                suggestions=[]
            )
        
        # محاسبه میانگین اعتماد
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        # تعیین بدترین سطح دقت
        accuracy_levels = [r.accuracy_level for r in results]
        worst_level = min(accuracy_levels, key=lambda x: x.value)
        
        # ترکیب مسائل و پیشنهادات
        all_differences = []
        all_suggestions = []
        for result in results:
            all_differences.extend(result.differences)
            all_suggestions.extend(result.suggestions)
        
        return AccuracyResult(
            accuracy_level=worst_level,
            confidence=avg_confidence,
            matched_values=[],
            expected_values=[],
            differences=all_differences,
            suggestions=all_suggestions
        )


# Global accuracy checker instance
accuracy_checker = AccuracyChecker()
