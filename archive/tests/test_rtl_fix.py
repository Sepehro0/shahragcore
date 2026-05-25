#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from processors.dynamic_title_extractor import DynamicTitleExtractor

# تست fix_rtl_text
pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
extractor = DynamicTitleExtractor(pdf_path)

# عنوان صحیح که باید باشد
correct_title = "مالیات بنگاه های اقتصادی نهادها و بنیادهای انقالب اسلامی"

# نمونه‌های مختلف از متن که ممکن است در PDF باشد
test_texts = [
    "نهادها و بنیادهای انقالب ،اسالمی مالیات بنگاه های اقتصادی",
    "مالیات بنگاه های اقتصادی نهادها و بنیادهای انقالب اسلامی",
    "نهادها و بنیادهای انقالب، اسالمی مالیات بنگاه‌های اقتصادی"
]

print("🔍 Testing RTL Fix:")
print("="*80)
print(f"Correct Title: {correct_title}")
print("="*80)

for text in test_texts:
    fixed = extractor.fix_rtl_text(text)
    print(f"\nOriginal: {text}")
    print(f"Fixed:    {fixed}")
    print(f"Match: {'✅' if correct_title in fixed else '❌'}")

# چک کردن اینکه چه عنوانی استخراج شده
print("\n" + "="*80)
print("📊 Extracted Title for 110104:")
print("="*80)
title_110104 = extractor.get_title("110104")
print(f"Title: {title_110104}")
print(f"Match: {'✅' if title_110104 and correct_title in title_110104 else '❌'}")
