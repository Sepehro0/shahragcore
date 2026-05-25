# گزارش کامل تست 6 سوال جدید با پاسخ‌های API

**تاریخ:** 2025-11-29 06:50  
**Collection:** finance_budget_new_1764252643  
**API URL:** http://185.13.230.254:8010/v2/query

---

## 📊 خلاصه نتایج

| # | سوال | Route | وضعیت | زمان | DB Rows | مشکل |
|---|------|-------|-------|------|---------|------|
| 1 | تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399 | `rag` | ⚠️ | 36.38s | 0 | به RAG رفت |
| 2 | اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98 | `rag` | ⚠️ | 47.13s | 0 | به RAG رفت |
| 3 | اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98 | `ERROR` | ❌ | 55.10s | 0 | خطای 500 |
| 4 | مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402 | `ERROR` | ❌ | 57.88s | 0 | خطای 500 |
| 5 | تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402 | `rag` | ⚠️ | 34.38s | 0 | به RAG رفت |
| 6 | مصارف اختصاصی پژوهشکده آمار در سال 1403 | `rag` | ⚠️ | 31.60s | 0 | به RAG رفت |

**آمار کلی:**
- ✅ موفق (HTTP 200): 4/6 (66.7%)
- ❌ خطا (HTTP 500): 2/6 (33.3%)
- 🗄️ Database Routes: 0/6 (0.0%) ⚠️ **مشکل اصلی: همه queries به RAG می‌روند**
- ⏱️ میانگین زمان: 43.75s

---

## 📝 جزئیات کامل هر سوال

### سوال 1: تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399

**Route:** `rag`  
**Status Code:** 200  
**Processing Time:** 35.81s

**پاسخ کامل API:**
```
اطلاعات کافی برای تهیه خلاصه درباره تملک دارایی‌های سرمایه‌ای پارک فناوری پردیس در سال 1399 در متن موجود نیست.
```

**Metadata کامل:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": "user_enabled",
  "multi_hop_sub_questions": [],
  "multi_hop_analysis": {
    "type": "simple",
    "hops": [],
    "target_entity": null,
    "operation": null,
    "requires_multi_hop": false
  },
  "answer_mode": "llm",
  "used_query_analyzer": true,
  "used_structure_detection": false,
  "used_table_normalization": false,
  "used_advanced_retrieval": false,
  "processing_time_seconds": 35.809184,
  "timestamp": "2025-11-29T06:39:38.300046",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

**تحلیل:**
- ❌ Entity "پارک فناوری پردیس" در database یافت نشد
- ❌ Entity extraction: `['سرمایه', 'پارک', 'فناوری', 'پردیس']` - entity تقسیم شده
- ❌ Entity Filter شامل کلمات اضافی: `'%سرمایه ای پارک فناوری پردیس%'`
- ⚠️ باید به database می‌رفت اما به RAG رفت

---

### سوال 2: اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98

**Route:** `rag`  
**Status Code:** 200  
**Processing Time:** 46.51s

**پاسخ کامل API:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق دربارهٔ اعتبارات هزینه‌ای ستاد مبارزه با مواد مخدر سال 98 در متن موجود نیست.
```

**Metadata کامل:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": "user_enabled",
  "multi_hop_sub_questions": [],
  "multi_hop_analysis": {
    "type": "simple",
    "hops": [],
    "target_entity": null,
    "operation": null,
    "requires_multi_hop": false
  },
  "answer_mode": "llm",
  "used_query_analyzer": true,
  "used_structure_detection": false,
  "used_table_normalization": false,
  "used_advanced_retrieval": false,
  "processing_time_seconds": 46.514739,
  "timestamp": "2025-11-29T06:40:27.432421",
  "sources_count": 3,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

**تحلیل:**
- ✅ Entity "ستاد مبارزه با مواد مخدر" در database موجود است
- ✅ Entity extraction: `['ستاد مبارزه با مواد مخدر']` - درست استخراج شد
- ✅ سال 98 به 1398 تبدیل شد
- ❌ باید به database می‌رفت اما به RAG رفت
- ⚠️ **مشکل اصلی:** Routing به database کار نمی‌کند

---

### سوال 3: اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98

**Route:** `ERROR` (HTTP 500)  
**Status Code:** 500  
**Processing Time:** 55.10s

**خطای کامل:**
```json
{
  "detail": "Streaming retrieval returned no data"
}
```

**تحلیل:**
- ❌ خطای 500 در streaming retrieval
- ⚠️ نیاز به بررسی لاگ‌های سرور
- احتمالاً در routing یا query processing خطا رخ داده

---

### سوال 4: مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402

**Route:** `ERROR` (HTTP 500)  
**Status Code:** 500  
**Processing Time:** 57.88s

**خطای کامل:**
```json
{
  "detail": "Streaming retrieval returned no data"
}
```

**تحلیل:**
- ❌ خطای 500 در streaming retrieval
- ❌ Entity extraction: `['معاونت', 'علمی', 'فناوری', 'رییس', 'جمهور']` - entity تقسیم شده
- ⚠️ Entity در database: "معاونت علمي ، فناوري  و اقتصاد دانش بنيان رييس جمهور" (با کاما و فاصله)
- ❌ باید "معاونت علمی و فناوری رییس جمهور" را به صورت یک entity واحد استخراج کند

---

### سوال 5: تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402

**Route:** `rag`  
**Status Code:** 200  
**Processing Time:** 33.68s

**پاسخ کامل API:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره تملک دارایی‌های سرمایه‌ای متفرقه مرکز ملی فضای مجازی کشور در سال‌های 98 تا 1402 در متن ارائه‌شده وجود ندارد.
```

**Metadata کامل:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": "user_enabled",
  "multi_hop_sub_questions": [],
  "multi_hop_analysis": {
    "type": "simple",
    "hops": [],
    "target_entity": null,
    "operation": null,
    "requires_multi_hop": false
  },
  "answer_mode": "llm",
  "used_query_analyzer": true,
  "used_structure_detection": false,
  "used_table_normalization": false,
  "used_advanced_retrieval": false,
  "processing_time_seconds": 33.676873,
  "timestamp": "2025-11-29T06:43:00.797705",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

**تحلیل:**
- ✅ Years: `['1398', '1399', '1400', '1401', '1402']` - range به درستی استخراج شد
- ❌ Entity extraction: `['سرمایه', 'متفرقه', 'مرکز', 'فضای', 'مجازی', 'کشور']` - entity تقسیم شده
- ❌ Entity Filter: `'%سرمایه ای متفرقه مرکز ملی فضای مجازی کشور%'` - شامل کلمات اضافی
- ⚠️ باید "مرکز ملی فضای مجازی کشور" را به صورت یک entity واحد استخراج کند

---

### سوال 6: مصارف اختصاصی پژوهشکده آمار در سال 1403

**Route:** `rag`  
**Status Code:** 200  
**Processing Time:** 31.12s

**پاسخ کامل API:**
```
اطلاعات کافی برای تهیه خلاصه‌ای درباره مصارف اختصاصی پژوهشکده آمار در سال 1403 در متن موجود نیست.
```

**Metadata کامل:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": "user_enabled",
  "multi_hop_sub_questions": [],
  "multi_hop_analysis": {
    "type": "simple",
    "hops": [],
    "target_entity": null,
    "operation": null,
    "requires_multi_hop": false
  },
  "answer_mode": "llm",
  "used_query_analyzer": true,
  "used_structure_detection": false,
  "used_table_normalization": false,
  "used_advanced_retrieval": false,
  "processing_time_seconds": 31.11704,
  "timestamp": "2025-11-29T06:43:34.398652",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

**تحلیل:**
- ✅ Entity extraction: `['پژوهشکده امار']` - درست استخراج شد
- ⚠️ Entity در database: "مركز آمار ايران" (نه "پژوهشکده آمار")
- ❌ نام در database متفاوت است - نیاز به fuzzy matching بهتر
- ⚠️ باید به database می‌رفت اما به RAG رفت

---

## 🔍 مشکلات شناسایی شده

### 1. ⚠️ مشکل اصلی: Routing به Database کار نمی‌کند

**وضعیت:** همه 6 query به RAG می‌روند حتی وقتی که باید به database بروند.

**علل احتمالی:**
1. Entity extraction مشکل دارد → Entity ها به درستی استخراج نمی‌شوند
2. Entity matching در database موفق نیست → حتی entity های درست هم match نمی‌شوند
3. Routing logic اشکال دارد → منطق routing درست کار نمی‌کند

**مثال مشکل:**
- Query 2: Entity "ستاد مبارزه با مواد مخدر" در database موجود است
- اما query به RAG می‌رود نه database
- این نشان می‌دهد routing logic مشکل دارد

---

### 2. Entity Extraction مشکلات دارد

#### مشکل 1: Entity های چند کلمه‌ای تقسیم می‌شوند

| Query | Entity واقعی | Entity استخراج شده | مشکل |
|-------|--------------|-------------------|------|
| Query 1 | "پارک فناوری پردیس" | `['سرمایه', 'پارک', 'فناوری', 'پردیس']` | تقسیم شده |
| Query 4 | "معاونت علمی و فناوری رییس جمهور" | `['معاونت', 'علمی', 'فناوری', 'رییس', 'جمهور']` | تقسیم شده |
| Query 5 | "مرکز ملی فضای مجازی کشور" | `['سرمایه', 'متفرقه', 'مرکز', 'فضای', 'مجازی', 'کشور']` | تقسیم شده |

#### مشکل 2: کلمات اضافی در Entity Filter

- "تملک دارایی های سرمایه ای پارک..." → Filter: `'%سرمایه ای پارک فناوری پردیس%'`
- باید فقط: `'%پارک فناوری پردیس%'`
- کلمات "سرمایه ای" و "متفرقه" نباید در entity filter باشند

---

### 3. خطاهای 500

**Queries با خطا:**
- Query 3: "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98"
- Query 4: "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402"

**خطا:**
```json
{
  "detail": "Streaming retrieval returned no data"
}
```

**تحلیل:**
- خطا در streaming retrieval
- احتمالاً در routing یا query processing خطا رخ داده
- نیاز به بررسی لاگ‌های سرور

---

### 4. عدم تطابق نام‌های Entity

| Query | Entity در Query | Entity در Database | وضعیت |
|-------|----------------|-------------------|-------|
| Query 1 | "پارک فناوری پردیس" | یافت نشد | ❌ |
| Query 2 | "ستاد مبارزه با مواد مخدر" | "ستاد مبارزه با مواد مخدر" | ✅ |
| Query 3 | "بنیاد ایران شناسی" | یافت نشد | ❌ |
| Query 4 | "معاونت علمی و فناوری رییس جمهور" | "معاونت علمي ، فناوري  و اقتصاد دانش بنيان رييس جمهور" | ⚠️ |
| Query 5 | "مرکز ملی فضای مجازی کشور" | یافت نشد | ❌ |
| Query 6 | "پژوهشکده آمار" | "مركز آمار ايران" | ⚠️ |

**مشکلات:**
- برخی entity ها در database وجود ندارند
- برخی entity ها نام متفاوتی دارند (نیاز به fuzzy matching)
- برخی entity ها با کاما و فاصله اضافی نوشته شده‌اند

---

## 📈 آمار کلی

- **تعداد سوالات:** 6
- **موفق (HTTP 200):** 4 (66.7%)
- **خطا (HTTP 500):** 2 (33.3%)
- **Database Routes:** 0 (0.0%) ⚠️
- **RAG Routes:** 4 (66.7%)
- **میانگین زمان پاسخ:** 43.75 ثانیه

---

## 🎯 نتیجه‌گیری

### مشکلات اصلی:
1. ⚠️ **Routing به Database کار نمی‌کند** - همه queries به RAG می‌روند
2. ⚠️ **Entity Extraction مشکل دارد** - entity های چند کلمه‌ای تقسیم می‌شوند
3. ❌ **خطاهای 500** - 2 query با خطا مواجه شدند
4. ⚠️ **عدم تطابق نام‌های Entity** - برخی entity ها در database وجود ندارند یا نام متفاوتی دارند

### اقدامات لازم:
1. بررسی و رفع routing logic
2. بهبود entity extraction برای entity های چند کلمه‌ای
3. فیلتر کردن کلمات اضافی از entity filter
4. بهبود fuzzy matching برای نام‌های مشابه
5. بررسی و رفع خطاهای 500

---

**گزارش تهیه شده توسط:** AI Assistant  
**تاریخ:** 2025-11-29 06:50  
**فایل JSON کامل:** `API_RESPONSES_FULL_20251129_064838.json`


