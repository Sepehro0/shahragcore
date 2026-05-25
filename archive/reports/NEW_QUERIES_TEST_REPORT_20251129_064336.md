# گزارش تست 6 سوال جدید

**تاریخ:** 2025-11-29 06:43:36  
**Collection:** finance_budget_new_1764252643  
**API URL:** http://185.13.230.254:8010/v2/query

---

## 📊 خلاصه نتایج

| # | سوال | Route | موفقیت | زمان پاسخ | Rows |
|---|------|-------|--------|-----------|------|
| 1 | تملک دارایی های سرمایه ای پارک فناوری پردیس در سال... | `rag` | ✅ | 36.38s | 0 |
| 2 | اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98 | `rag` | ✅ | 47.13s | 0 |
| 3 | اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال ... | `ERROR` | ❌ | 55.10s | 0 |
| 4 | مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور ... | `ERROR` | ❌ | 57.88s | 0 |
| 5 | تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجا... | `rag` | ✅ | 34.38s | 0 |
| 6 | مصارف اختصاصی پژوهشکده آمار در سال 1403 | `rag` | ✅ | 31.60s | 0 |

**موفق:** 4/6 | **Database Routes:** 0/6

---

## سوال 1: تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای تهیه خلاصه درباره تملک دارایی‌های سرمایه‌ای پارک فناوری پردیس در سال 1399 در متن موجود نیست.
```

### Metadata:

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

### زمان پاسخ: 36.38 ثانیه

---

## سوال 2: اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق دربارهٔ اعتبارات هزینه‌ای ستاد مبارزه با مواد مخدر سال 98 در متن موجود نیست.
```

### Metadata:

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

### زمان پاسخ: 47.13 ثانیه

---

## سوال 3: اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98

### وضعیت: ❌ ناموفق

### خطا:

```
HTTP 500
```

### زمان پاسخ: 55.10 ثانیه

---

## سوال 4: مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402

### وضعیت: ❌ ناموفق

### خطا:

```
HTTP 500
```

### زمان پاسخ: 57.88 ثانیه

---

## سوال 5: تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره تملک دارایی‌های سرمایه‌ای متفرقه مرکز ملی فضای مجازی کشور در سال‌های 98 تا 1402 در متن ارائه‌شده وجود ندارد.
```

### Metadata:

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

### زمان پاسخ: 34.38 ثانیه

---

## سوال 6: مصارف اختصاصی پژوهشکده آمار در سال 1403

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای تهیه خلاصه‌ای درباره مصارف اختصاصی پژوهشکده آمار در سال 1403 در متن موجود نیست.
```

### Metadata:

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

### زمان پاسخ: 31.60 ثانیه

---


## 📈 آمار کلی

- **تعداد سوالات:** 6
- **موفق:** 4 (66.7%)
- **ناموفق:** 2 (33.3%)
- **مسیر Database:** 0 (0.0%)
- **میانگین زمان پاسخ:** 43.75 ثانیه

---

**گزارش تهیه شده توسط:** AI Assistant  
**تاریخ:** 2025-11-29 06:43:36
