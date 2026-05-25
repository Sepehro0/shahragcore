# -*- coding: utf-8 -*-
"""
Persian Numeric Processing
پردازش اعداد فارسی
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NumberType(Enum):
    """انواع عدد"""
    INTEGER = "integer"
    FLOAT = "float"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    SCIENTIFIC = "scientific"


@dataclass
class ProcessedNumber:
    """عدد پردازش شده"""
    original_text: str
    normalized_value: float
    number_type: NumberType
    unit: Optional[str] = None
    currency: Optional[str] = None
    context: Optional[str] = None
    confidence: float = 1.0


class NumericProcessor:
    """پردازشگر اعداد فارسی"""
    
    def __init__(self):
        # Persian/Arabic to English digit mapping
        self.persian_digits = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        
        # Arabic digits
        self.arabic_digits = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        # Persian number words
        self.persian_words = {
            'صفر': 0, 'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5,
            'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10,
            'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14, 'پانزده': 15,
            'شانزده': 16, 'هفده': 17, 'هجده': 18, 'نوزده': 19, 'بیست': 20,
            'سی': 30, 'چهل': 40, 'پنجاه': 50, 'شصت': 60, 'هفتاد': 70,
            'هشتاد': 80, 'نود': 90, 'صد': 100, 'هزار': 1000,
            'میلیون': 1000000, 'میلیارد': 1000000000
        }
        
        # Currency units
        self.currency_units = {
            'ریال': 'IRR',
            'تومان': 'IRR',
            'دلار': 'USD',
            'یورو': 'EUR',
            'پوند': 'GBP',
            'ین': 'JPY',
            'یوان': 'CNY'
        }
        
        # Multiplier words
        self.multipliers = {
            'هزار': 1000,
            'میلیون': 1000000,
            'میلیارد': 1000000000,
            'تریلیون': 1000000000000
        }
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """کامپایل regex patterns"""
        # Persian/Arabic digits pattern
        persian_digit_pattern = '[' + ''.join(self.persian_digits.keys()) + ']'
        arabic_digit_pattern = '[' + ''.join(self.arabic_digits.keys()) + ']'
        
        # Number patterns
        self.number_patterns = {
            'persian_digits': re.compile(f'[{re.escape(persian_digit_pattern)}]+'),
            'arabic_digits': re.compile(f'[{re.escape(arabic_digit_pattern)}]+'),
            'english_digits': re.compile(r'\d+'),
            'decimal': re.compile(r'\d+[.,]\d+'),
            'currency': re.compile(r'[\d,]+(?:\s*(?:هزار|میلیون|میلیارد)?\s*(?:ریال|تومان|دلار|یورو|پوند|ین|یوان))?'),
            'percentage': re.compile(r'\d+(?:[.,]\d+)?\s*%'),
            'scientific': re.compile(r'\d+(?:[.,]\d+)?[eE][+-]?\d+')
        }
        
        # Persian number word pattern
        persian_word_pattern = '|'.join(self.persian_words.keys())
        self.persian_word_pattern = re.compile(f'\\b({persian_word_pattern})\\b', re.IGNORECASE)
    
    def normalize_digits(self, text: str) -> str:
        """تبدیل ارقام فارسی/عربی به انگلیسی"""
        # Convert Persian digits
        for persian, english in self.persian_digits.items():
            text = text.replace(persian, english)
        
        # Convert Arabic digits
        for arabic, english in self.arabic_digits.items():
            text = text.replace(arabic, english)
        
        return text
    
    def extract_numbers(self, text: str) -> List[ProcessedNumber]:
        """استخراج اعداد از متن"""
        numbers = []
        
        # Normalize digits first
        normalized_text = self.normalize_digits(text)
        
        # Find all number patterns
        for pattern_name, pattern in self.number_patterns.items():
            for match in pattern.finditer(normalized_text):
                number_text = match.group()
                processed = self._process_number_text(number_text, pattern_name)
                if processed:
                    numbers.append(processed)
        
        # Find Persian number words
        for match in self.persian_word_pattern.finditer(text):
            word = match.group(1).lower()
            if word in self.persian_words:
                processed = ProcessedNumber(
                    original_text=word,
                    normalized_value=float(self.persian_words[word]),
                    number_type=NumberType.INTEGER,
                    confidence=0.9
                )
                numbers.append(processed)
        
        return numbers
    
    def _process_number_text(self, text: str, pattern_name: str) -> Optional[ProcessedNumber]:
        """پردازش متن عدد"""
        try:
            # Clean the text
            cleaned = re.sub(r'[^\d.,]', '', text)
            
            if not cleaned:
                return None
            
            # Determine number type
            if pattern_name == 'percentage':
                number_type = NumberType.PERCENTAGE
                # Handle both comma and dot as decimal separator
                if ',' in cleaned and '.' in cleaned:
                    # Both present, assume comma is thousands separator
                    value = float(cleaned.replace(',', ''))
                elif ',' in cleaned:
                    # Only comma, check if it's decimal or thousands separator
                    if len(cleaned.split(',')[-1]) <= 2:
                        value = float(cleaned.replace(',', '.'))
                    else:
                        value = float(cleaned.replace(',', ''))
                else:
                    value = float(cleaned)
                unit = '%'
            elif pattern_name == 'currency':
                number_type = NumberType.CURRENCY
                # Extract currency unit
                currency_match = re.search(r'(ریال|تومان|دلار|یورو|پوند|ین|یوان)', text)
                currency = currency_match.group(1) if currency_match else None
                
                # Extract multiplier
                multiplier = 1
                if 'هزار' in text:
                    multiplier = 1000
                elif 'میلیون' in text:
                    multiplier = 1000000
                elif 'میلیارد' in text:
                    multiplier = 1000000000
                
                # Handle both comma and dot as decimal separator for currency
                if ',' in cleaned and '.' in cleaned:
                    # Both present, assume comma is thousands separator
                    value = float(cleaned.replace(',', '')) * multiplier
                elif ',' in cleaned:
                    # Only comma, check if it's decimal or thousands separator
                    if len(cleaned.split(',')[-1]) <= 2:
                        value = float(cleaned.replace(',', '.')) * multiplier
                    else:
                        value = float(cleaned.replace(',', '')) * multiplier
                else:
                    value = float(cleaned) * multiplier
                unit = currency
            elif pattern_name == 'scientific':
                number_type = NumberType.SCIENTIFIC
                # Handle both comma and dot as decimal separator
                if ',' in cleaned and '.' in cleaned:
                    value = float(cleaned.replace(',', ''))
                elif ',' in cleaned:
                    if len(cleaned.split(',')[-1]) <= 2:
                        value = float(cleaned.replace(',', '.'))
                    else:
                        value = float(cleaned.replace(',', ''))
                else:
                    value = float(cleaned)
            elif '.' in cleaned or ',' in cleaned:
                number_type = NumberType.FLOAT
                # Handle both comma and dot as decimal separator
                if ',' in cleaned and '.' in cleaned:
                    value = float(cleaned.replace(',', ''))
                elif ',' in cleaned:
                    if len(cleaned.split(',')[-1]) <= 2:
                        value = float(cleaned.replace(',', '.'))
                    else:
                        value = float(cleaned.replace(',', ''))
                else:
                    value = float(cleaned)
            else:
                number_type = NumberType.INTEGER
                value = float(cleaned.replace(',', ''))
            
            return ProcessedNumber(
                original_text=text,
                normalized_value=value,
                number_type=number_type,
                unit=unit if 'unit' in locals() else None,
                currency=currency if 'currency' in locals() else None,
                confidence=1.0
            )
        
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to process number text '{text}': {e}")
            return None
    
    def format_number(self, value: float, format_type: str = "standard") -> str:
        """فرمت کردن عدد"""
        if format_type == "currency":
            return f"{value:,.0f} ریال"
        elif format_type == "percentage":
            return f"{value:.2f}%"
        elif format_type == "scientific":
            return f"{value:.2e}"
        else:
            return f"{value:,.0f}"
    
    def compare_numbers(self, num1: ProcessedNumber, num2: ProcessedNumber) -> int:
        """مقایسه دو عدد"""
        # Normalize to same unit if possible
        val1 = self._normalize_value(num1)
        val2 = self._normalize_value(num2)
        
        if val1 > val2:
            return 1
        elif val1 < val2:
            return -1
        else:
            return 0
    
    def _normalize_value(self, number: ProcessedNumber) -> float:
        """نرمال کردن مقدار عدد"""
        value = number.normalized_value
        
        # Apply unit conversion if needed
        if number.unit == '%':
            value = value / 100
        elif number.currency == 'USD':
            # Assume 1 USD = 42000 IRR (this should be configurable)
            value = value * 42000
        
        return value
    
    def calculate_sum(self, numbers: List[ProcessedNumber]) -> Optional[ProcessedNumber]:
        """محاسبه مجموع اعداد"""
        if not numbers:
            return None
        
        total = 0
        unit = None
        currency = None
        
        for num in numbers:
            normalized_value = self._normalize_value(num)
            total += normalized_value
            
            if unit is None:
                unit = num.unit
                currency = num.currency
        
        return ProcessedNumber(
            original_text=f"مجموع {len(numbers)} عدد",
            normalized_value=total,
            number_type=NumberType.INTEGER,
            unit=unit,
            currency=currency,
            confidence=0.9
        )
    
    def find_largest(self, numbers: List[ProcessedNumber]) -> Optional[ProcessedNumber]:
        """پیدا کردن بزرگترین عدد"""
        if not numbers:
            return None
        
        largest = numbers[0]
        for num in numbers[1:]:
            if self.compare_numbers(num, largest) > 0:
                largest = num
        
        return largest
    
    def find_smallest(self, numbers: List[ProcessedNumber]) -> Optional[ProcessedNumber]:
        """پیدا کردن کوچکترین عدد"""
        if not numbers:
            return None
        
        smallest = numbers[0]
        for num in numbers[1:]:
            if self.compare_numbers(num, smallest) < 0:
                smallest = num
        
        return smallest
    
    def filter_by_range(self, numbers: List[ProcessedNumber], 
                       min_value: Optional[float] = None, 
                       max_value: Optional[float] = None) -> List[ProcessedNumber]:
        """فیلتر کردن اعداد بر اساس محدوده"""
        filtered = []
        
        for num in numbers:
            normalized_value = self._normalize_value(num)
            
            if min_value is not None and normalized_value < min_value:
                continue
            if max_value is not None and normalized_value > max_value:
                continue
            
            filtered.append(num)
        
        return filtered
    
    def extract_currency_amounts(self, text: str) -> List[ProcessedNumber]:
        """استخراج مبالغ پولی"""
        currency_pattern = re.compile(
            r'([\d,]+(?:\s*(?:هزار|میلیون|میلیارد)?\s*(?:ریال|تومان|دلار|یورو|پوند|ین|یوان))?)',
            re.IGNORECASE
        )
        
        amounts = []
        for match in currency_pattern.finditer(text):
            amount_text = match.group(1)
            processed = self._process_number_text(amount_text, 'currency')
            if processed:
                amounts.append(processed)
        
        return amounts
    
    def validate_number(self, number: ProcessedNumber) -> bool:
        """اعتبارسنجی عدد"""
        if number.normalized_value is None:
            return False
        
        if number.number_type == NumberType.PERCENTAGE:
            return 0 <= number.normalized_value <= 100
        elif number.number_type == NumberType.CURRENCY:
            return number.normalized_value >= 0
        else:
            return True


# Global numeric processor instance
numeric_processor = NumericProcessor()
