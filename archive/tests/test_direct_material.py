#!/usr/bin/env python3
import sys
import re

# Test normalization function
def normalize_text(text):
    if not text:
        return ""
    
    # تبدیل ی و ک عربی به فارسی
    text = text.replace('ي', 'ی').replace('ى', 'ی')
    text = text.replace('ك', 'ک')
    
    # تبدیل اعداد فارسی به انگلیسی
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
    }
    for persian, english in persian_to_english.items():
        text = text.replace(persian, english)
    
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\u200c', ' ')
    text = text.replace('­', '')
    
    return text.strip().lower()

# Test
query1 = "ماده 46 شرایط عمومی پیمان"
query2 = "ماده ۵۳ شرايط عمومي پيمان"

norm1 = normalize_text(query1)
norm2 = normalize_text(query2)

print(f"Original 1: {query1}")
print(f"Normalized 1: {norm1}")
print(f"Extract number: {re.search(r'ماده\s*(\d+)', norm1).group(1) if re.search(r'ماده\s*(\d+)', norm1) else 'NOT FOUND'}")

print(f"\nOriginal 2: {query2}")
print(f"Normalized 2: {norm2}")
print(f"Extract number: {re.search(r'ماده\s*(\d+)', norm2).group(1) if re.search(r'ماده\s*(\d+)', norm2) else 'NOT FOUND'}")

# Test answer matching
answer_sample = "وفق بند (الف-1) ماده 53 شرایط عمومی پیمان موضوع نشریه 4311"
norm_answer = normalize_text(answer_sample)
print(f"\nAnswer original: {answer_sample}")
print(f"Answer normalized: {norm_answer}")
print(f"'ماده 53' in answer: {'ماده 53' in norm_answer}")
