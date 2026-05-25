# -*- coding: utf-8 -*-
"""
Unit Tests for Text Utils Module
تست‌های واحد برای ماژول text_utils
"""

import unittest
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from utils.text_utils import TextNormalizer


class TestTextNormalizer(unittest.TestCase):
    """تست TextNormalizer"""
    
    def setUp(self):
        """Setup برای هر تست"""
        self.normalizer = TextNormalizer()
    
    def test_normalize_text_basic(self):
        """تست normalization ساده"""
        text = "سلام  دنیا"
        result = self.normalizer.normalize_text(text)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"✅ normalize_text_basic: '{text}' → '{result}'")
    
    def test_normalize_text_with_numbers(self):
        """تست با اعداد فارسی و انگلیسی"""
        text = "۱۲۳ 456 ۷۸۹"
        result = self.normalizer.normalize_text(text)
        self.assertIn("123", result)
        self.assertIn("456", result)
        self.assertIn("789", result)
        print(f"✅ normalize_text_with_numbers: '{text}' → '{result}'")
    
    def test_normalize_text_with_special_chars(self):
        """تست با کاراکترهای خاص"""
        text = "سلام‌ دنیا! چطوری؟"
        result = self.normalizer.normalize_text(text)
        self.assertIsNotNone(result)
        print(f"✅ normalize_text_with_special_chars: '{text}' → '{result}'")
    
    def test_normalize_empty_string(self):
        """تست با رشته خالی"""
        text = ""
        result = self.normalizer.normalize_text(text)
        self.assertEqual(result, "")
        print("✅ normalize_empty_string: '' → ''")
    
    def test_fix_persian_text_for_display(self):
        """تست RTL fixing"""
        text = "سلام دنیا"
        result = self.normalizer.fix_persian_text_for_display(text)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"✅ fix_persian_text_for_display: passed")
    
    def test_normalize_colloquial_static(self):
        """تست تبدیل محاوره‌ای به رسمی"""
        test_cases = [
            ("چیه", "چیست"),
            ("میشه", "می‌شود"),
            ("میتونم", "می‌توانم"),
        ]
        
        for informal, expected_formal in test_cases:
            result = self.normalizer.normalize_colloquial_static(informal)
            self.assertIn(expected_formal, result)
            print(f"✅ normalize_colloquial: '{informal}' → '{result}'")
    
    def test_tokenize_meaningful(self):
        """تست tokenization"""
        text = "چگونه می‌توانم طرح خود را ثبت کنم؟"
        tokens = self.normalizer.tokenize_meaningful(text)
        
        self.assertIsInstance(tokens, set)
        self.assertGreater(len(tokens), 0)
        
        # باید stopwords را حذف کرده باشد
        stopwords = {"برای", "در", "از", "به", "و"}
        for stopword in stopwords:
            self.assertNotIn(stopword, tokens)
        
        print(f"✅ tokenize_meaningful: {len(tokens)} tokens extracted")
        print(f"   Tokens: {list(tokens)[:5]}...")


def run_tests():
    """اجرای تست‌ها"""
    print("\n" + "="*60)
    print("🧪 Testing TextNormalizer")
    print("="*60 + "\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTextNormalizer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   ⚠️  Errors: {len(result.errors)}")
    print("="*60 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

