# -*- coding: utf-8 -*-
"""
Content Classification Module
ماژول طبقه‌بندی محتوا
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """انواع محتوا"""
    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    CODE = "code"
    IMAGE = "image"
    CHART = "chart"
    LIST = "list"
    QUOTE = "quote"
    HEADER = "header"
    FOOTER = "footer"
    MIXED = "mixed"


class ContentQuality(Enum):
    """کیفیت محتوا"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    POOR = "poor"


@dataclass
class ContentClassification:
    """نتیجه طبقه‌بندی محتوا"""
    content_type: ContentType
    quality: ContentQuality
    confidence: float
    features: Dict[str, Any]
    metadata: Dict[str, Any]


class ContentClassifier:
    """طبقه‌بندی‌کننده محتوا"""
    
    def __init__(self):
        # الگوهای تشخیص نوع محتوا
        self.content_patterns = {
            ContentType.TABLE: [
                r'\|.*\|',  # جدول با جداکننده |
                r'جدول\s+\d+',
                r'بخش\s+\d+',
                r'فصل\s+\d+',
                r'\b(جمع|کل|ملی|استانی|عمومی|اختصاصی)\b.*\b(جمع|کل|ملی|استانی|عمومی|اختصاصی)\b'
            ],
            ContentType.FORMULA: [
                r'[=+\-*/^()]+',  # فرمول‌های ریاضی
                r'\\[a-zA-Z]+',  # LaTeX commands
                r'∑|∫|√|π|α|β|γ|δ|ε|ζ|η|θ|λ|μ|ν|ξ|ο|π|ρ|σ|τ|υ|φ|χ|ψ|ω',  # نمادهای یونانی
                r'قضیه|لم|اثبات|فرمول'
            ],
            ContentType.CODE: [
                r'```[\s\S]*?```',  # Code blocks
                r'def\s+\w+\(',  # Python functions
                r'class\s+\w+',  # Python classes
                r'function\s+\w+',  # JavaScript functions
                r'import\s+\w+',  # Import statements
                r'#include\s*<',  # C++ includes
                r'<\?php',  # PHP code
                r'<script',  # JavaScript
                r'<style',  # CSS
            ],
            ContentType.LIST: [
                r'^\d+\.',  # Numbered lists
                r'^[-*•]',  # Bullet lists
                r'^\s*[-*•]\s+',  # Indented bullet lists
                r'^\s*\d+\)',  # Numbered lists with parentheses
            ],
            ContentType.QUOTE: [
                r'^>',  # Markdown quotes
                r'^"',  # Quoted text
                r'^«',  # Persian quotes
                r'^"',  # Arabic quotes
            ],
            ContentType.HEADER: [
                r'^#+\s+',  # Markdown headers
                r'^عنوان\s*:',
                r'^فصل\s+\d+',
                r'^بخش\s+\d+',
                r'^ماده\s+\d+',
            ]
        }
        
        # الگوهای تشخیص کیفیت
        self.quality_indicators = {
            ContentQuality.HIGH: [
                r'[آ-ی]{3,}',  # کلمات فارسی با حداقل 3 حرف
                r'[a-zA-Z]{3,}',  # کلمات انگلیسی با حداقل 3 حرف
                r'\d+',  # وجود اعداد
                r'[.!?]',  # علائم نگارشی
            ],
            ContentQuality.POOR: [
                r'^\s*$',  # خطوط خالی
                r'^[^\w\s]*$',  # فقط کاراکترهای خاص
                r'^.{1,2}$',  # خطوط خیلی کوتاه
                r'[^\w\s.,!?]',  # کاراکترهای غیرمعمول
            ]
        }
    
    def classify_content(self, content: str, metadata: Dict[str, Any] = None) -> ContentClassification:
        """طبقه‌بندی محتوا"""
        try:
            if not content or not content.strip():
                return ContentClassification(
                    content_type=ContentType.TEXT,
                    quality=ContentQuality.POOR,
                    confidence=0.0,
                    features={},
                    metadata=metadata or {}
                )
            
            # تشخیص نوع محتوا
            content_type, type_confidence = self._detect_content_type(content)
            
            # تشخیص کیفیت
            quality, quality_confidence = self._detect_content_quality(content)
            
            # استخراج ویژگی‌ها
            features = self._extract_features(content)
            
            # محاسبه اعتماد کلی
            overall_confidence = (type_confidence + quality_confidence) / 2
            
            return ContentClassification(
                content_type=content_type,
                quality=quality,
                confidence=overall_confidence,
                features=features,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            return ContentClassification(
                content_type=ContentType.TEXT,
                quality=ContentQuality.LOW,
                confidence=0.0,
                features={},
                metadata=metadata or {}
            )
    
    def _detect_content_type(self, content: str) -> Tuple[ContentType, float]:
        """تشخیص نوع محتوا"""
        content_lower = content.lower()
        type_scores = {}
        
        # محاسبه امتیاز برای هر نوع محتوا
        for content_type, patterns in self.content_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))
                score += matches
            type_scores[content_type] = score
        
        # تعیین نوع اصلی
        if type_scores:
            primary_type = max(type_scores.items(), key=lambda x: x[1])[0]
            max_score = type_scores[primary_type]
            
            # محاسبه اعتماد
            total_possible = sum(len(patterns) for patterns in self.content_patterns.values())
            confidence = min(max_score / max(total_possible, 1), 1.0)
            
            return primary_type, confidence
        
        return ContentType.TEXT, 0.0
    
    def _detect_content_quality(self, content: str) -> Tuple[ContentQuality, float]:
        """تشخیص کیفیت محتوا"""
        content_lower = content.lower()
        
        # محاسبه امتیاز کیفیت بالا
        high_quality_score = 0
        for pattern in self.quality_indicators[ContentQuality.HIGH]:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            high_quality_score += matches
        
        # محاسبه امتیاز کیفیت پایین
        poor_quality_score = 0
        for pattern in self.quality_indicators[ContentQuality.POOR]:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            poor_quality_score += matches
        
        # تعیین کیفیت
        if poor_quality_score > high_quality_score:
            return ContentQuality.POOR, 0.8
        elif high_quality_score > 5:
            return ContentQuality.HIGH, 0.8
        elif high_quality_score > 2:
            return ContentQuality.MEDIUM, 0.6
        else:
            return ContentQuality.LOW, 0.4
    
    def _extract_features(self, content: str) -> Dict[str, Any]:
        """استخراج ویژگی‌های محتوا"""
        features = {
            'length': len(content),
            'word_count': len(content.split()),
            'line_count': len(content.split('\n')),
            'has_numbers': bool(re.search(r'\d', content)),
            'has_persian': bool(re.search(r'[آ-ی]', content)),
            'has_english': bool(re.search(r'[a-zA-Z]', content)),
            'has_punctuation': bool(re.search(r'[.!?]', content)),
            'has_special_chars': bool(re.search(r'[^\w\s.,!?]', content)),
            'has_tables': bool(re.search(r'\|.*\|', content)),
            'has_formulas': bool(re.search(r'[=+\-*/^()]+', content)),
            'has_code': bool(re.search(r'```|def\s+|class\s+', content)),
            'has_lists': bool(re.search(r'^\d+\.|^[-*•]', content, re.MULTILINE)),
            'has_quotes': bool(re.search(r'^>|^"', content, re.MULTILINE)),
            'has_headers': bool(re.search(r'^#+\s+', content, re.MULTILINE)),
            'numeric_density': len(re.findall(r'\d', content)) / max(len(content), 1),
            'persian_density': len(re.findall(r'[آ-ی]', content)) / max(len(content), 1),
            'english_density': len(re.findall(r'[a-zA-Z]', content)) / max(len(content), 1)
        }
        
        return features
    
    def classify_batch(self, contents: List[str], metadatas: List[Dict[str, Any]] = None) -> List[ContentClassification]:
        """طبقه‌بندی دسته‌ای محتوا"""
        if metadatas is None:
            metadatas = [{}] * len(contents)
        
        classifications = []
        for content, metadata in zip(contents, metadatas):
            classification = self.classify_content(content, metadata)
            classifications.append(classification)
        
        return classifications
    
    def get_content_statistics(self, classifications: List[ContentClassification]) -> Dict[str, Any]:
        """دریافت آمار محتوا"""
        if not classifications:
            return {}
        
        # شمارش انواع محتوا
        type_counts = {}
        for classification in classifications:
            content_type = classification.content_type.value
            type_counts[content_type] = type_counts.get(content_type, 0) + 1
        
        # شمارش کیفیت‌ها
        quality_counts = {}
        for classification in classifications:
            quality = classification.quality.value
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        # محاسبه میانگین اعتماد
        avg_confidence = sum(c.confidence for c in classifications) / len(classifications)
        
        # محاسبه ویژگی‌های کلی
        total_length = sum(c.features.get('length', 0) for c in classifications)
        total_words = sum(c.features.get('word_count', 0) for c in classifications)
        
        return {
            'total_items': len(classifications),
            'content_types': type_counts,
            'quality_distribution': quality_counts,
            'average_confidence': avg_confidence,
            'total_length': total_length,
            'total_words': total_words,
            'average_length': total_length / len(classifications) if classifications else 0,
            'average_words': total_words / len(classifications) if classifications else 0
        }
    
    def filter_by_type(self, classifications: List[ContentClassification], 
                      content_type: ContentType) -> List[ContentClassification]:
        """فیلتر کردن بر اساس نوع محتوا"""
        return [c for c in classifications if c.content_type == content_type]
    
    def filter_by_quality(self, classifications: List[ContentClassification], 
                         min_quality: ContentQuality) -> List[ContentClassification]:
        """فیلتر کردن بر اساس حداقل کیفیت"""
        quality_order = {
            ContentQuality.POOR: 0,
            ContentQuality.LOW: 1,
            ContentQuality.MEDIUM: 2,
            ContentQuality.HIGH: 3
        }
        
        min_quality_level = quality_order.get(min_quality, 0)
        
        return [
            c for c in classifications 
            if quality_order.get(c.quality, 0) >= min_quality_level
        ]


# Global content classifier instance
content_classifier = ContentClassifier()
