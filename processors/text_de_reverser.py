# -*- coding: utf-8 -*-
"""
Text De-Reverser for Persian PDFs
تبدیل متن reversed فارسی به متن قابل خواندن
"""

import re
import logging

logger = logging.getLogger(__name__)


class TextDeReverser:
    """تبدیل متن reversed فارسی به متن عادی"""
    
    def __init__(self):
        # Pattern برای شناسایی متن reversed
        self.reversed_pattern = re.compile(r'"[^"]*"')
        
        # Mapping برای کاراکترهای reversed
        self.char_mapping = {
            # اعداد
            '"0"': '0', '"1"': '1', '"2"': '2', '"3"': '3', '"4"': '4',
            '"5"': '5', '"6"': '6', '"7"': '7', '"8"': '8', '"9"': '9',
            
            # حروف فارسی
            '"ﺍ"': 'ا', '"ﺏ"': 'ب', '"ﺕ"': 'ت', '"ﺙ"': 'ث', '"ﺝ"': 'ج',
            '"ﺡ"': 'ح', '"ﺥ"': 'خ', '"ﺩ"': 'د', '"ﺫ"': 'ذ', '"ﺭ"': 'ر',
            '"ﺯ"': 'ز', '"ﺱ"': 'س', '"ﺵ"': 'ش', '"ﺹ"': 'ص', '"ﺽ"': 'ض',
            '"ﻁ"': 'ط', '"ﻅ"': 'ظ', '"ﻉ"': 'ع', '"ﻍ"': 'غ', '"ﻑ"': 'ف',
            '"ﻕ"': 'ق', '"ﻙ"': 'ک', '"ﻝ"': 'ل', '"ﻡ"': 'م', '"ﻥ"': 'ن',
            '"ﻭ"': 'و', '"ﻩ"': 'ه', '"ﻱ"': 'ی',
            
            # حروف بزرگ
            '"ﺁ"': 'آ', '"ﺍ"': 'ا', '"ﺏ"': 'ب', '"ﺕ"': 'ت', '"ﺙ"': 'ث',
            '"ﺝ"': 'ج', '"ﺡ"': 'ح', '"ﺥ"': 'خ', '"ﺩ"': 'د', '"ﺫ"': 'ذ',
            '"ﺭ"': 'ر', '"ﺯ"': 'ز', '"ﺱ"': 'س', '"ﺵ"': 'ش', '"ﺹ"': 'ص',
            '"ﺽ"': 'ض', '"ﻁ"': 'ط', '"ﻅ"': 'ظ', '"ﻉ"': 'ع', '"ﻍ"': 'غ',
            '"ﻑ"': 'ف', '"ﻕ"': 'ق', '"ﻙ"': 'ک', '"ﻝ"': 'ل', '"ﻡ"': 'م',
            '"ﻥ"': 'ن', '"ﻭ"': 'و', '"ﻩ"': 'ه', '"ﻱ"': 'ی',
            
            # علائم
            '" "': ' ', '","': ',', '"."': '.', '":"': ':', '";"': ';',
            '"("': '(', '")"': ')', '"["': '[', '"]"': ']', '"{"': '{',
            '"}"': '}', '"|"': '|', '"-"': '-', '"_"': '_', '"+"': '+',
            '"="': '=', '"*"': '*', '"/"': '/', '"\\"': '\\', '"\'"': "'",
            '"`"': '`', '"~"': '~', '"!"': '!', '"@"': '@', '"#"': '#',
            '"$"': '$', '"%"': '%', '"^"': '^', '"&"': '&', '">"': '>',
            '"<"': '<', '"?"': '?', '"\\""': '"',
        }
    
    def de_reverse_text(self, text: str) -> str:
        """
        تبدیل متن reversed به متن عادی
        
        Args:
            text: متن reversed
            
        Returns:
            متن عادی
        """
        if not text:
            return text
        
        try:
            # ابتدا کاراکترهای reversed را تبدیل کن
            de_reversed = text
            
            # تبدیل کاراکترهای reversed
            for reversed_char, normal_char in self.char_mapping.items():
                de_reversed = de_reversed.replace(reversed_char, normal_char)
            
            # حذف گیومه‌های اضافی
            de_reversed = re.sub(r'"+', '', de_reversed)
            
            # نرمال‌سازی فاصله‌ها
            de_reversed = re.sub(r'\s+', ' ', de_reversed)
            
            # حذف کاراکترهای اضافی
            de_reversed = de_reversed.replace('\u200c', '')  # نیم‌فاصله
            
            return de_reversed.strip()
            
        except Exception as e:
            logger.error(f"Error in de_reverse_text: {e}")
            return text
    
    def is_reversed_text(self, text: str) -> bool:
        """
        بررسی اینکه آیا متن reversed است یا نه
        
        Args:
            text: متن برای بررسی
            
        Returns:
            True اگر متن reversed باشد
        """
        if not text:
            return False
        
        # اگر بیش از 30% کاراکترها reversed باشند، متن reversed است
        reversed_count = len(self.reversed_pattern.findall(text))
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        reversed_ratio = reversed_count / total_chars
        return reversed_ratio > 0.3
    
    def process_document(self, text: str) -> str:
        """
        پردازش کامل سند
        
        Args:
            text: متن سند
            
        Returns:
            متن پردازش شده
        """
        if not text:
            return text
        
        try:
            # بررسی اینکه آیا متن reversed است
            if self.is_reversed_text(text):
                logger.info("Detected reversed text, applying de-reversing")
                return self.de_reverse_text(text)
            else:
                logger.info("Text appears normal, no de-reversing needed")
                return text
                
        except Exception as e:
            logger.error(f"Error in process_document: {e}")
            return text


# Test function
def test_de_reverser():
    """تست de-reverser"""
    try:
        print("🧪 Testing Text De-Reverser...")
        
        de_reverser = TextDeReverser()
        
        # Test cases
        test_cases = [
            '"ﺍ"ﻥ" "ﻱ"ﻙ" "ﺝ"ﻣ"ﻝ"ﻩ" "ﺕ"ﺱ"ﺕ"ﻱ" "ﺍ"ﺱ"ﺕ"',
            '"ﻡ"ﺍ"ﻝ"ﻱ"ﺍ"ﺕ" "ﺏ"ﺭ" "ﺍ"ﺭ"ﺯ"ﺵ" "ﺍ"ﻑ"ﺯ"ﻭ"ﺩ"ﻩ"',
            '"ﺝ"ﺩ"ﻭ"ﻝ" "ﺵ"ﻡ"ﺍ"ﺭ"ﻩ" "ﻱ"ﻙ"',
            'Normal text without reversing',
            '"1"4"0"1"8"4" "("ﭖ")"',
        ]
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"\nTest {i}:")
            print(f"  Input:  {test_text}")
            
            is_reversed = de_reverser.is_reversed_text(test_text)
            print(f"  Reversed: {is_reversed}")
            
            de_reversed = de_reverser.de_reverse_text(test_text)
            print(f"  Output: {de_reversed}")
        
        print("\n✅ Text De-Reverser test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    test_de_reverser()
