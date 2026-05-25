# گزارش مشکلات بحرانی سیستم RAG

**تاریخ:** 2025-12-07  
**نتیجه تست:** 2/12 (16.7% موفق)

---

## 🔴 مشکلات بحرانی شناسایی شده

### 1. Entity Extraction چند تکه‌ای می‌شود
**مشکل:** برای "ستاد مبارزه با مواد مخدر" → `['ستاد', 'مبارزه', 'مواد']`

**تاثیر:** SQL query با OR برای هر تکه جستجو می‌کند که نتیجه اشتباه می‌دهد

**علت:** Special case patterns کار نمی‌کنند چون:
- قبل از entity extraction، کلمات مالی حذف می‌شوند
- "اعتبارات هزینه‌ای متفرقه" از query حذف می‌شود
- بعد "ستاد مبارزه با مواد مخدر" می‌ماند
- اما pattern matching روی query تمیز شده اتفاق نمی‌افتد

**راه‌حل:** Special case patterns باید روی query اصلی (قبل از cleaning) اعمال شوند

---

### 2. SQL Query نمی‌تواند Entity پیدا کند
**مشکل:** حتی با ILIKE، برخی entity‌ها پیدا نمی‌شوند

**علت احتمالی:**
- کاراکترهای خاص (non-breaking space، نیم‌فاصله)
- تفاوت در ی/ي و ک/ك بعد از TRANSLATE
- Entity در database با نام کمی متفاوت ذخیره شده

**Test شده:**
- "فرهنگستان هنر" → با ILIKE مستقیم کار می‌کند ✅
- اما از طریق API کار نمی‌کند ❌

**راه‌حل پیشنهادی:**
- Log کردن SQL query برای بررسی دقیق
- بررسی اینکه آیا SQL به database می‌رسد یا نه
- Check کردن اینکه آیا exception می‌دهد یا نه

---

### 3. HTTP 500 بدون پیام خطای مشخص
**مشکل:** 10 از 12 تست HTTP 500 برمی‌گردانند اما علت واضح نیست

**تحلیل:**
- Entity extraction: ✅ کار می‌کند
- Entity در database: ✅ موجود است
- SQL با ILIKE: ✅ کار می‌کند
- API call: ❌ HTTP 500

**نتیجه:** مشکل در middleware بین entity extraction و SQL execution است

---

## 📝 دستورالعمل رفع فوری

### فاز 1: Log کردن SQL
```python
# در text_to_sql_agent.py در هر جایی که SQL تولید می‌شود:
logger.info(f"📊 GENERATED SQL:\n{sql}")

# در database_service.py قبل از execute:
logger.info(f"🔍 EXECUTING SQL:\n{sql}")
```

### فاز 2: Test مستقیم SQL
```bash
# Test query مستقیم در PostgreSQL:
psql -U postgres -d rag_database -c "
SELECT * FROM masaref2_sheet1 
WHERE TRANSLATE(\"عنوان_دستگاه_اجرايي\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%فرهنگستان هنر%'
AND \"سال\" = '1403'
LIMIT 3
"
```

### فاز 3: بهبود Entity Extraction
```python
# در query_analyzer.py - special case patterns باید روی query اصلی اعمال شوند:
query_normalized = self.normalize_text(query)  # بدون cleaning
for pattern_info in known_patterns:
    if isinstance(pattern_info, tuple):
        pattern, use_full_match = pattern_info
        if use_full_match:
            matches = re.finditer(pattern, query_normalized, re.IGNORECASE)
            # ...
```

---

## 🎯 اولویت‌بندی

1. **اولویت فوری:** Log کردن SQL queries
2. **اولویت بالا:** رفع مشکل special case patterns
3. **اولویت متوسط:** بهبود error handling

---

## 💡 نتیجه‌گیری

مشکل اصلی **در logic بین entity extraction و SQL execution** است. 

Entity extraction درست کار می‌کند اما:
- یا SQL درست تولید نمی‌شود
- یا SQL تولید می‌شود اما execute نمی‌شود
- یا execute می‌شود اما نتیجه‌ای برنمی‌گرداند

**بدون logging دقیق نمی‌توانیم بفهمیم کدام مورد است.**

