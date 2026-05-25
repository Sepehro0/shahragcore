#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بهینه‌سازی حجم Response برای جلوگیری از crash و کندی
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 80)
    print("🔧 بهینه‌سازی حجم Response")
    print("=" * 80)
    print()
    
    print("📊 مشکلات فعلی:")
    print("   - حجم response: 12.24 MB (خیلی زیاد!)")
    print("   - max_tokens: 2000 (برای بعضی سوالات زیاد است)")
    print("   - تکرار در answer/full_answer/full_text")
    print("   - metadata زیاد در sources")
    print()
    
    print("✅ راه‌حل‌ها:")
    print("   1. کاهش max_tokens به 800 (برای سوالات ساده)")
    print("   2. حذف فیلدهای تکراری از response")
    print("   3. خلاصه کردن metadata در sources")
    print("   4. اضافه کردن truncation به متن")
    print()
    
    # راه‌حل 1: بررسی طول سوال و تنظیم max_tokens
    print("📝 پیشنهاد 1: تنظیم دینامیک max_tokens")
    print("   - سوالات کوتاه (<10 کلمه): 600 tokens")
    print("   - سوالات متوسط (10-20 کلمه): 800 tokens")
    print("   - سوالات طولانی (>20 کلمه): 1200 tokens")
    print("   - سوالات مقایسه‌ای: 1000 tokens")
    print()
    
    # راه‌حل 2: بهینه‌سازی response structure
    print("📝 پیشنهاد 2: بهینه‌سازی Response Structure")
    print("   - حذف یکی از answer/full_answer (تکراری)")
    print("   - کاهش metadata در sources (فقط فیلدهای مهم)")
    print("   - اضافه کردن max_response_size_mb")
    print()
    
    # راه‌حل 3: truncation
    print("📝 پیشنهاد 3: Truncation")
    print("   - اگر response > 5MB: truncate کن")
    print("   - اضافه کردن warning به client")
    print()
    
    print("=" * 80)
    print("🔨 اعمال تغییرات...")
    print("=" * 80)
    
    # تغییرات را در فایل‌ها اعمال می‌کنیم
    changes = {
        "answer_orchestrator.py": {
            "old_max_tokens": 2000,
            "new_max_tokens": "dynamic (600-1200)",
            "reason": "کاهش حجم پاسخ برای سوالات ساده"
        },
        "api_server.py": {
            "optimization": "remove full_text duplicate",
            "reason": "حذف تکرار"
        }
    }
    
    for file, change in changes.items():
        print(f"\n📄 {file}:")
        for key, value in change.items():
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 80)
    print("✅ راهنمای پیاده‌سازی آماده است")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


