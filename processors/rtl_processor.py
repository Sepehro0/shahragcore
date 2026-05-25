# -*- coding: utf-8 -*-
"""
RTL Text Processing
پردازش متن RTL (راست به چپ)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TextDirection(Enum):
    """جهت متن"""
    LTR = "ltr"  # Left to Right
    RTL = "rtl"  # Right to Left
    MIXED = "mixed"  # Mixed direction
    UNKNOWN = "unknown"


@dataclass
class ProcessedText:
    """متن پردازش شده"""
    original_text: str
    processed_text: str
    direction: TextDirection
    language: str
    confidence: float
    metadata: Dict[str, Any] = None


class RTLProcessor:
    """پردازشگر متن RTL"""
    
    def __init__(self):
        # Persian/Arabic character ranges
        self.persian_arabic_range = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
        
        # English/Latin character ranges
        self.latin_range = re.compile(r'[a-zA-Z]')
        
        # Persian specific characters
        self.persian_chars = re.compile(r'[\u0600-\u06FF]')
        
        # Arabic specific characters
        self.arabic_chars = re.compile(r'[\u0750-\u077F\u08A0-\u08FF]')
        
        # Common Persian words for language detection
        self.persian_words = {
            'در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یک', 'یا', 'و', 'اما',
            'است', 'بود', 'خواهد', 'کرد', 'شد', 'می', 'را', 'برای', 'تا', 'اگر'
        }
        
        # Common Arabic words for language detection
        self.arabic_words = {
            'في', 'من', 'إلى', 'على', 'مع', 'أن', 'هذا', 'هذه', 'واحد', 'أو', 'و',
            'كان', 'يكون', 'فعل', 'صار', 'قد', 'ل', 'حتى', 'إذا', 'التي', 'الذي'
        }
        
        # RTL punctuation marks
        self.rtl_punctuation = {
            '؟': '?',  # Arabic question mark
            '؛': ';',  # Arabic semicolon
            '،': ',',  # Arabic comma
            '؛': ';',  # Arabic semicolon
            '«': '"',  # Arabic quotation marks
            '»': '"',
            '': '"',  # Arabic quotation marks
            '': '"',
        }
        
        # LTR punctuation marks that should be flipped
        self.ltr_punctuation = {
            '?': '؟',
            ';': '؛',
            ',': '،',
            '"': '«»',
            "'": '""',
        }
    
    def detect_direction(self, text: str) -> TextDirection:
        """تشخیص جهت متن"""
        if not text.strip():
            return TextDirection.UNKNOWN
        
        # Count RTL and LTR characters
        rtl_chars = len(self.persian_arabic_range.findall(text))
        ltr_chars = len(self.latin_range.findall(text))
        
        total_chars = rtl_chars + ltr_chars
        if total_chars == 0:
            return TextDirection.UNKNOWN
        
        rtl_ratio = rtl_chars / total_chars
        
        if rtl_ratio > 0.7:
            return TextDirection.RTL
        elif rtl_ratio < 0.3:
            return TextDirection.LTR
        else:
            return TextDirection.MIXED
    
    def detect_language(self, text: str) -> str:
        """تشخیص زبان متن"""
        if not text.strip():
            return "unknown"
        
        # Count Persian and Arabic characters
        persian_count = len(self.persian_chars.findall(text))
        arabic_count = len(self.arabic_chars.findall(text))
        
        # Count Persian and Arabic words
        words = text.split()
        persian_word_count = sum(1 for word in words if word in self.persian_words)
        arabic_word_count = sum(1 for word in words if word in self.arabic_words)
        
        # Determine language based on character and word counts
        if persian_count > arabic_count and persian_word_count > arabic_word_count:
            return "fa"  # Persian
        elif arabic_count > persian_count and arabic_word_count > persian_word_count:
            return "ar"  # Arabic
        elif persian_count > 0 or arabic_count > 0:
            return "fa"  # Default to Persian for mixed content
        else:
            return "en"  # English
    
    def normalize_text(self, text: str) -> str:
        """نرمال کردن متن"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize Persian/Arabic characters
        text = self._normalize_persian_arabic(text)
        
        # Fix punctuation
        text = self._fix_punctuation(text)
        
        return text
    
    def _normalize_persian_arabic(self, text: str) -> str:
        """نرمال کردن کاراکترهای فارسی/عربی"""
        # Normalize different forms of same characters
        replacements = {
            'ي': 'ی',  # Arabic yeh to Persian yeh
            'ك': 'ک',  # Arabic kaf to Persian kaf
            'ة': 'ه',  # Arabic teh marbuta to heh
            'أ': 'ا',  # Arabic alef with hamza above to alef
            'إ': 'ا',  # Arabic alef with hamza below to alef
            'آ': 'ا',  # Arabic alef with madda above to alef
            'ؤ': 'و',  # Arabic waw with hamza above to waw
            'ئ': 'ی',  # Arabic yeh with hamza above to yeh
        }
        
        for arabic, persian in replacements.items():
            text = text.replace(arabic, persian)
        
        return text
    
    def _fix_punctuation(self, text: str) -> str:
        """تصحیح علائم نگارشی"""
        # Replace RTL punctuation with LTR equivalents
        for rtl_punct, ltr_punct in self.rtl_punctuation.items():
            text = text.replace(rtl_punct, ltr_punct)
        
        return text
    
    def process_text(self, text: str) -> ProcessedText:
        """پردازش کامل متن"""
        if not text.strip():
            return ProcessedText(
                original_text=text,
                processed_text=text,
                direction=TextDirection.UNKNOWN,
                language="unknown",
                confidence=0.0
            )
        
        # Detect direction and language
        direction = self.detect_direction(text)
        language = self.detect_language(text)
        
        # Normalize text
        processed_text = self.normalize_text(text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(text, direction, language)
        
        # Extract metadata
        metadata = {
            'original_length': len(text),
            'processed_length': len(processed_text),
            'rtl_character_count': len(self.persian_arabic_range.findall(text)),
            'ltr_character_count': len(self.latin_range.findall(text)),
            'word_count': len(text.split()),
            'has_numbers': bool(re.search(r'\d', text)),
            'has_punctuation': bool(re.search(r'[^\w\s]', text))
        }
        
        return ProcessedText(
            original_text=text,
            processed_text=processed_text,
            direction=direction,
            language=language,
            confidence=confidence,
            metadata=metadata
        )
    
    def _calculate_confidence(self, text: str, direction: TextDirection, language: str) -> float:
        """محاسبه اعتماد پردازش"""
        confidence = 0.5  # Base confidence
        
        # Direction confidence
        if direction == TextDirection.RTL:
            confidence += 0.3
        elif direction == TextDirection.LTR:
            confidence += 0.2
        elif direction == TextDirection.MIXED:
            confidence += 0.1
        
        # Language confidence
        if language in ['fa', 'ar']:
            confidence += 0.2
        elif language == 'en':
            confidence += 0.1
        
        # Text quality factors
        if len(text.strip()) > 10:
            confidence += 0.1
        
        if re.search(r'[^\w\s]', text):  # Has punctuation
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def split_mixed_text(self, text: str) -> List[Tuple[str, TextDirection]]:
        """تقسیم متن مختلط به بخش‌های RTL و LTR"""
        segments = []
        current_segment = ""
        current_direction = None
        
        for char in text:
            char_direction = self._get_char_direction(char)
            
            if char_direction != current_direction and current_segment:
                # Direction changed, save current segment
                segments.append((current_segment, current_direction))
                current_segment = char
                current_direction = char_direction
            else:
                current_segment += char
                if current_direction is None:
                    current_direction = char_direction
        
        # Add final segment
        if current_segment:
            segments.append((current_segment, current_direction))
        
        return segments
    
    def _get_char_direction(self, char: str) -> TextDirection:
        """تشخیص جهت یک کاراکتر"""
        if self.persian_arabic_range.match(char):
            return TextDirection.RTL
        elif self.latin_range.match(char):
            return TextDirection.LTR
        else:
            return TextDirection.UNKNOWN
    
    def reverse_text(self, text: str) -> str:
        """معکوس کردن متن RTL"""
        # Split into words
        words = text.split()
        
        # Reverse word order
        reversed_words = words[::-1]
        
        # Join back
        return ' '.join(reversed_words)
    
    def fix_text_direction(self, text: str) -> str:
        """تصحیح جهت متن"""
        processed = self.process_text(text)
        
        if processed.direction == TextDirection.RTL:
            # For RTL text, we might need to reverse word order
            return self.reverse_text(processed.processed_text)
        else:
            return processed.processed_text
    
    def extract_rtl_sentences(self, text: str) -> List[str]:
        """استخراج جملات RTL"""
        # Split by sentence endings
        sentences = re.split(r'[.!?؟]', text)
        
        rtl_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                processed = self.process_text(sentence)
                if processed.direction == TextDirection.RTL:
                    rtl_sentences.append(sentence)
        
        return rtl_sentences
    
    def extract_ltr_sentences(self, text: str) -> List[str]:
        """استخراج جملات LTR"""
        # Split by sentence endings
        sentences = re.split(r'[.!?؟]', text)
        
        ltr_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                processed = self.process_text(sentence)
                if processed.direction == TextDirection.LTR:
                    ltr_sentences.append(sentence)
        
        return ltr_sentences
    
    def is_rtl_text(self, text: str) -> bool:
        """بررسی RTL بودن متن"""
        direction = self.detect_direction(text)
        return direction == TextDirection.RTL
    
    def is_persian_text(self, text: str) -> bool:
        """بررسی فارسی بودن متن"""
        language = self.detect_language(text)
        return language == "fa"
    
    def is_arabic_text(self, text: str) -> bool:
        """بررسی عربی بودن متن"""
        language = self.detect_language(text)
        return language == "ar"


class RTLTextProcessor:
    """پردازشگر متن RTL (برای سازگاری)"""
    
    def __init__(self):
        self.processor = RTLProcessor()
    
    def process_text(self, text: str) -> str:
        """پردازش متن"""
        processed = self.processor.process_text(text)
        return processed.processed_text
    
    def detect_direction(self, text: str) -> str:
        """تشخیص جهت متن"""
        direction = self.processor.detect_direction(text)
        return direction.value
    
    def detect_language(self, text: str) -> str:
        """تشخیص زبان متن"""
        return self.processor.detect_language(text)
    
    def normalize_text(self, text: str) -> str:
        """نرمال کردن متن"""
        return self.processor.normalize_text(text)
    
    def is_rtl_text(self, text: str) -> bool:
        """بررسی RTL بودن متن"""
        return self.processor.is_rtl_text(text)
    
    def is_persian_text(self, text: str) -> bool:
        """بررسی فارسی بودن متن"""
        return self.processor.is_persian_text(text)


# Global RTL processor instance
rtl_processor = RTLProcessor()
rtl_text_processor = RTLTextProcessor()
