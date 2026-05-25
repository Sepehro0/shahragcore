# 🚀 Quick Start Guide: Document Structure Understanding

## برای شروع سریع

### 1️⃣ ریستارت Streamlit

```bash
# توقف Streamlit فعلی
pkill -f streamlit

# شروع مجدد
cd /home/user01/qwen-api/streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

یا استفاده از اسکریپت موجود:
```bash
bash /home/user01/qwen-api/quick_restart.sh
```

### 2️⃣ استفاده از سیستم در UI

#### گام 1: آپلود PDF
1. به تب **"Ultimate RAG"** بروید
2. مطمئن شوید که **3 فیچر پیشرفته** فعال هستند:
   - 🧠 Semantic Chunking: ✅
   - 🔍 Query Understanding: ✅
   - 🚀 Advanced Retrieval: ✅
3. فایل PDF خود را آپلود کنید
4. منتظر بمانید تا پردازش تکمیل شود

**نکته:** سیستم به طور خودکار ساختار سند را تحلیل می‌کند!

#### گام 2: سوال بپرسید
به تب **"Smart Chat"** بروید و سوالات ساختاری بپرسید:

**نمونه سوالات:**
- ✅ چند بند داریم؟
- ✅ چند بخش داریم؟
- ✅ ساختار این سند چیست؟
- ✅ بخش اول چند بند دارد؟
- ✅ فهرست بندها چیست؟

#### گام 3: دریافت پاسخ ساختاریافته
سیستم پاسخ را در فرمت زیر ارائه می‌دهد:

```
✅ خلاصه:
[توضیح کلی درباره تعداد بخش‌ها و بندها]

📋 جزئیات:
• بخش اول: [نام] - شامل X بند
  - بند اول: [عنوان]
  - بند دوم: [عنوان]
• بخش دوم: [نام] - شامل Y بند
  ...

📌 اطلاعات تکمیلی:
[جزئیات بیشتر در صورت نیاز]
```

---

## 🧪 تست سریع با Python

```python
import asyncio
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

async def test():
    # ایجاد سیستم
    rag = UltimateRAGSystem(
        enable_semantic_chunking=True,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        retrieval_strategy="iterative"
    )
    
    # پردازش PDF
    with open("your_file.pdf", 'rb') as f:
        result = await rag.process_pdf_advanced(
            f.read(), 
            'your_file.pdf', 
            'test_collection'
        )
    
    print(f"✅ Processed: {result['chunks_count']} chunks")
    
    # سوال ساختاری
    answer = await rag.retrieve_and_answer(
        query="چند بند داریم؟",
        collection_name='test_collection',
        top_k=10,
        use_reranking=True,
        use_multi_hop=True
    )
    
    print(f"\n📊 پاسخ:\n{answer['answer']}")
    
    await rag.close()

asyncio.run(test())
```

---

## 📝 تنظیمات پیشنهادی

### برای اسناد مالی (مثل جداول بودجه):

| تنظیم | مقدار پیشنهادی | دلیل |
|-------|----------------|------|
| Semantic Chunking | ✅ ON | حفظ بهتر context |
| Query Understanding | ✅ ON | تشخیص سوالات ساختاری |
| Advanced Retrieval | ✅ ON | دقت بالاتر |
| Retrieval Strategy | `iterative` یا `advanced` | برای queries پیچیده |
| Top K | 10-15 | پوشش بهتر |
| Reranking | ✅ ON | دقت بالاتر |
| Multi-hop | ✅ ON | سوالات چند مرحله‌ای |
| Temperature | 0.1 | پاسخ‌های دقیق‌تر |

---

## ❓ سوالات متداول

### Q1: چرا سیستم "سند" می‌گوید به جای "بند"؟
**A:** این اشکال در نسخه قدیم بود. در نسخه جدید (با Document Structure Understanding) این مشکل برطرف شده است.

### Q2: چطور می‌توانم مطمئن شوم که ساختار سند تحلیل شده؟
**A:** در لاگ‌ها به دنبال پیام زیر بگردید:
```
✅ Document structure analyzed and metadata enriched
   - Sections: 6, Clauses: 13
```

### Q3: اگر ساختار سند تشخیص داده نشد چه کنم?
**A:** سیستم به طور خودکار به روش عادی fallback می‌کند. هیچ خطایی نمی‌دهد.

### Q4: آیا می‌توانم الگوهای سفارشی تعریف کنم؟
**A:** بله! در `document_structure_analyzer.py` می‌توانید الگوهای خود را اضافه کنید:
```python
self.hierarchy_levels = {
    'custom_level': {
        'persian': ['کلمه کلیدی شما'],
        'code_pattern': r'^your_regex$',
        ...
    }
}
```

### Q5: چطور می‌توانم کیفیت پاسخ را بهبود بدهم؟
**A:** 
1. مطمئن شوید که 3 فیچر پیشرفته فعال هستند
2. Top K را به 10-15 افزایش دهید
3. از Retrieval Strategy `iterative` یا `advanced` استفاده کنید
4. Reranking را فعال کنید

---

## 🔧 عیب‌یابی (Troubleshooting)

### مشکل: "Structure summary not found"
**راه‌حل:** 
- مطمئن شوید که PDF با Advanced Features پردازش شده
- چک کنید که لاگ "Document structure analyzed" را نشان می‌دهد
- اگر نه، PDF را دوباره آپلود کنید

### مشکل: پاسخ‌ها همچنان "سند" می‌گویند
**راه‌حل:**
- Cache متصفح را پاک کنید
- Streamlit را ریستارت کنید
- مطمئن شوید که Query Understanding فعال است

### مشکل: Semantic Chunking/Query Understanding load نمی‌شوند
**راه‌حل:**
- چک کنید مدل local موجود است: `/home/user01/qwen-api/persian_models/bert-fa-base-uncased`
- اگر نه، سیستم به طور خودکار fallback به `paraphrase-multilingual-MiniLM-L12-v2` می‌کند

---

## 📚 مستندات کامل

برای اطلاعات بیشتر:
- 📖 [DOCUMENT_STRUCTURE_IMPLEMENTATION.md](./DOCUMENT_STRUCTURE_IMPLEMENTATION.md) - مستندات کامل پیاده‌سازی
- 📊 [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - خلاصه پیاده‌سازی
- 🧪 [tests/test_document_structure.py](./tests/test_document_structure.py) - نمونه تست‌ها

---

## 💬 پشتیبانی

اگر مشکلی داشتید:
1. لاگ‌ها را چک کنید
2. مستندات را مطالعه کنید
3. تست‌ها را اجرا کنید تا مشکل را شناسایی کنید

---

**نسخه:** 1.0.0  
**آخرین به‌روزرسانی:** 21 اکتبر 2025  
**وضعیت:** ✅ Production Ready


