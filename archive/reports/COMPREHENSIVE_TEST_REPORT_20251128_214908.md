# گزارش جامع تست Query ها

**تاریخ:** 2025-11-28 21:49:08
**Collection:** finance_budget_new_1764252643

## 📊 آمار کلی

- **تعداد کل query ها:** 13
- **موفق:** 11 (84.6%)
- **Database Route:** 7 (53.8%)
- **RAG Route:** 4 (30.8%)

---

## 📋 جزئیات Query ها

### Query 1: مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور ...

**وضعیت:** ❌
**Route:** `N/A`
**Database Rows:** 0

**پاسخ کامل:**
```
{"detail":"Streaming retrieval returned no data"}
```

---

### Query 2: درآمد های گمرک جمهوری اسلامی ایران در سال 1398...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
درآمد گمرک جمهوری اسلامی ایران در سال 1398 به میزان 341,763,001 میلیون ریال ثبت شده است. این مقدار معادل 341,763,001,000,000 ریال می‌باشد.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 1,
  "sources_count": 0,
  "processing_time_seconds": 0.367535,
  "timestamp": "2025-11-28T21:45:30.691788",
  "retrieval_method": "database"
}
```

---

### Query 3: در امد های سازمان ملي استاندارد در سال ها 1399 تا ...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
در سال‌های 1399 تا 1402، مجموع درآمدهای سازمان ملی استاندارد به میزان 8,318,600 میلیون ریال ثبت شده است. این مقدار معادل 8,318,600,000,000 ریال می‌باشد.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 1,
  "sources_count": 0,
  "processing_time_seconds": 1.465337,
  "timestamp": "2025-11-28T21:43:34.594893",
  "retrieval_method": "database",
  "from_cache": true
}
```

---

### Query 4: درامد های حاصل از واگذاری دارایی های سرمایه ای در ...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
در سال 1402، درآمدهای حاصل از واگذاری دارایی‌های سرمایه‌ای به مبلغ 7,331,373,990 میلیون ریال ثبت شده است. این مقدار معادل 7,331,373,990,000,000 ریال است.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 2,
  "sources_count": 0,
  "processing_time_seconds": 2.11415,
  "timestamp": "2025-11-28T21:45:33.547784",
  "retrieval_method": "database"
}
```

---

### Query 5: درامدهای مالیاتی در سال 1402...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
درآمدهای مالیاتی در سال 1402 مبلغ 9,071,142,500 میلیون ریال به دست آمده است که معادل 9,071,142,500,000,000 ریال می‌شود. این مقدار کل درآمدهای مالیاتی در یک بخش گزارش شده است.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 3,
  "sources_count": 0,
  "processing_time_seconds": 1.996361,
  "timestamp": "2025-11-28T21:45:36.359975",
  "retrieval_method": "database"
}
```

---

### Query 6: درامد حاصل از جرایم و خسارات در سال های 1398 تا 14...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
در بازه سال‌های 1398 تا 1400، درآمد حاصل از جرایم و خسارات به میزان 334,466,650 میلیون ریال ثبت شده است. این مبلغ معادل 334,466,650,000,000 ریال است.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 3,
  "sources_count": 0,
  "processing_time_seconds": 5.662865,
  "timestamp": "2025-11-28T21:45:42.743214",
  "retrieval_method": "database"
}
```

---

### Query 7: درامد های دانشگاه امیرکبیر در سال 1403 از چه جز ها...

**وضعیت:** ✅
**Route:** `rag`
**Database Rows:** 0

**پاسخ کامل:**
```
اطلاعات کافی برای پاسخ به این پرسش در متن موجود نیست.
```

**Metadata:**
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
  "processing_time_seconds": 39.158783,
  "timestamp": "2025-11-28T21:46:22.194807",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

---

### Query 8: راه های در امدی بنیاد ملی نخبگان در سال 1402 چه مو...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
در سال 1402، مجموع درآمد بنیاد ملی نخبگان به 12,000 میلیون ریال رسیده بود که کل آن مربوط به درآمدهای ملی بود و هیچ درآمدی از سطح استانی ثبت نشده بود. این مقدار معادل 12,000,000,000 ریال است.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 3,
  "sources_count": 0,
  "processing_time_seconds": 0.345497,
  "timestamp": "2025-11-28T21:46:23.465375",
  "retrieval_method": "database"
}
```

---

### Query 9: تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجا...

**وضعیت:** ✅
**Route:** `rag`
**Database Rows:** 0

**پاسخ کامل:**
```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره تملک دارایی‌های سرمایه‌ای متفرقه مرکز ملی فضای مجازی کشور در سال‌های 98 تا 1402 در متن ارائه‌شده وجود ندارد.
```

**Metadata:**
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
  "processing_time_seconds": 37.150988,
  "timestamp": "2025-11-28T21:47:01.323479",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

---

### Query 10: مصارف اختصاصی پژوهشکده آمار در سال 1399...

**وضعیت:** ✅
**Route:** `rag`
**Database Rows:** 0

**پاسخ کامل:**
```
اطلاعات کافی برای تهیه خلاصه‌ای درباره مصارف اختصاصی پژوهشکده آمار در سال 1399 در متن موجود نیست.
```

**Metadata:**
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
  "processing_time_seconds": 30.802745,
  "timestamp": "2025-11-28T21:47:32.672682",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

---

### Query 11: درامد های استانی سازمان پزشكي قانوني كشور در سال ه...

**وضعیت:** ✅
**Route:** `database_override`
**Database Rows:** 1

**پاسخ کامل:**
```
درآمدهای استانی سازمان پزشکی قانونی کشور در سال‌های 1401 تا 1403 مجموعاً 10,100,000 میلیون ریال به دست آمده است. این مبلغ معادل 10,100,000,000,000 ریال است.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database_override",
  "database_rows_count": 1,
  "database_columns_count": 1,
  "sources_count": 0,
  "processing_time_seconds": 0.410849,
  "timestamp": "2025-11-28T21:47:34.056950",
  "retrieval_method": "database"
}
```

---

### Query 12: در سال 1403 وزارت ورزش و جوانان مصارف بیشتری داشته...

**وضعیت:** ❌
**Route:** `N/A`
**Database Rows:** 0

**پاسخ کامل:**
```
{"detail":"Streaming retrieval returned no data"}
```

---

### Query 13: مصارف دانشگاه تهران در سال 1401 چقدر بیشتر از مصار...

**وضعیت:** ✅
**Route:** `rag`
**Database Rows:** 0

**پاسخ کامل:**
```
اطلاعات کافی برای محاسبه تفاوت مصارف دانشگاه تهران در سال‌های 1401 و 1399 در متن موجود نیست.
```

**Metadata:**
```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": "user_enabled",
  "multi_hop_sub_questions": [],
  "multi_hop_analysis": {
    "type": "comparison",
    "hops": [
      {
        "query": "",
        "purpose": "find_entity1",
        "top_k": 5
      },
      {
        "query": "",
        "purpose": "find_entity2",
        "top_k": 5
      }
    ],
    "target_entity": "مصارف دانشگاه تهران در سال 1401 بیشتر از مصارف ان در سال 1399 بوده",
    "operation": "بیشتر",
    "requires_multi_hop": true,
    "executed_hops": [
      {
        "hop_number": 1,
        "purpose": "find_entity1",
        "query": "",
        "results_count": 5,
        "top_result_score": 0.0
      },
      {
        "hop_number": 2,
        "purpose": "find_entity2",
        "query": "",
        "results_count": 5,
        "top_result_score": 0.0
      }
    ]
  },
  "answer_mode": "llm",
  "used_query_analyzer": true,
  "used_structure_detection": false,
  "used_table_normalization": false,
  "used_advanced_
```

---


## نتیجه‌گیری

⚠️ سیستم عملکرد خوبی دارد - بیش از 50% query ها به database می‌روند.
