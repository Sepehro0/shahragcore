# گزارش تست 6 سوال جدید

**تاریخ:** 2025-11-29 07:07:11  
**Collection:** finance_budget_new_1764252643  
**API URL:** http://185.13.230.254:8010/v2/query

---

## 📊 خلاصه نتایج

| # | سوال | Route | موفقیت | زمان پاسخ | Rows |
|---|------|-------|--------|-----------|------|
| 1 | تملک دارایی های سرمایه ای پارک فناوری پردیس در سال... | `rag` | ✅ | 34.62s | 0 |
| 2 | اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98 | `database` | ✅ | 9.51s | 1 |
| 3 | اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال ... | `rag` | ✅ | 76.28s | 0 |
| 4 | مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور ... | `database` | ✅ | 10.84s | 2 |
| 5 | تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجا... | `rag` | ✅ | 36.66s | 0 |
| 6 | مصارف اختصاصی پژوهشکده آمار در سال 1403 | `rag` | ✅ | 33.14s | 0 |

**موفق:** 6/6 | **Database Routes:** 2/6

---

## سوال 1: تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره تملک دارایی‌های سرمایه‌ای پارک فناوری پردیس در سال 1399 در متن موجود نیست.
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
  "processing_time_seconds": 34.03552,
  "timestamp": "2025-11-29T07:04:13.108442",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

### زمان پاسخ: 34.62 ثانیه

---

## سوال 2: اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98

### وضعیت: ✅ موفق

### پاسخ API:

```
اعتبارات هزینه‌ای ستاد مبارزه با مواد مخدر در سال 98 مبلغ 1,200,000 میلیون ریال ثبت شده است. این مبلغ کل اعتبارات مربوط به این دستگاه در پایگاه داده است.
```

### Metadata:

```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database",
  "database_rows_count": 1,
  "database_columns_count": 3,
  "sources_count": 0,
  "processing_time_seconds": 8.687072,
  "timestamp": "2025-11-29T07:04:24.617439",
  "retrieval_method": "database"
}
```

### Database Results:

```json
{
  "success": true,
  "count": 1,
  "columns": [
    "total_amount",
    "عنوان_دستگاه",
    "عنوان_دستگاه_اصلی"
  ],
  "rows_sample": [
    {
      "total_amount": 1200000.0,
      "عنوان_دستگاه": "ستاد مبارزه با مواد مخدر",
      "عنوان_دستگاه_اصلی": "ستاد مبارزه با مواد مخدر"
    }
  ]
}
```

### SQL Query:

```sql
SELECT SUM(COALESCE(CAST("جمع_کل" AS DOUBLE PRECISION), 0)) AS total_amount, "عنوان_دستگاه", "عنوان_دستگاه_اصلی" FROM incomes_sheet1 WHERE ((TRANSLATE("عنوان_دستگاه", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%ستاد مبارزه با مواد مخدر%' OR TRANSLATE("عنوان_دستگاه_اصلی", 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%ستاد مبارزه با مواد مخدر%')) AND TRANSLATE("سال", 'يكيۀة', 'یکیهه') IN ('1398') GROUP BY "عنوان_دستگاه", "عنوان_دستگاه_اصلی"
```

### زمان پاسخ: 9.51 ثانیه

---

## سوال 3: اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98

### وضعیت: ✅ موفق

### پاسخ API:

```
اطلاعات کافی برای ارائه خلاصه‌ای درباره اعتبارات هزینه‌ای متفرقه بنیاد ایران‌شناسی در سال 98 در دسترس نیست.
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
  "processing_time_seconds": 75.752243,
  "timestamp": "2025-11-29T07:05:42.903673",
  "sources_count": 3,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

### زمان پاسخ: 76.28 ثانیه

---

## سوال 4: مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402

### وضعیت: ✅ موفق

### پاسخ API:

```
مجموع مصارف معاونت علمی و فناوری رییس جمهور در سال 1402 به میزان 220,000 میلیون ریال ثبت شده است. بیشترین مبلغ مربوط به پارک فناوری پردیس با 200,000 میلیون ریال و مابقی به صندوق حمایت از پژوهشگران و فناوران کشور اختصاص یافته است.
```

### Metadata:

```json
{
  "auto_multi_hop": false,
  "multi_hop_reason": null,
  "multi_hop_sub_questions": [],
  "retrieval_route": "database",
  "database_rows_count": 2,
  "database_columns_count": 3,
  "sources_count": 0,
  "processing_time_seconds": 9.710674,
  "timestamp": "2025-11-29T07:05:55.750147",
  "retrieval_method": "database"
}
```

### Database Results:

```json
{
  "success": true,
  "count": 2,
  "columns": [
    "total_amount",
    "عنوان_دستگاه",
    "عنوان_دستگاه_اصلی"
  ],
  "rows_sample": [
    {
      "total_amount": 200000.0,
      "عنوان_دستگاه": "پارك فناوري پرديس",
      "عنوان_دستگاه_اصلی": "معاونت علمي و فناوري رييس جمهور"
    },
    {
      "total_amount": 20000.0,
      "عنوان_دستگاه": "صندوق حمايت از پژوهشگران و فناوران كشور",
      "عنوان_دستگاه_اصلی": "معاونت علمي و فناوري رييس جمهور"
    }
  ]
}
```

### SQL Query:

```sql
SELECT SUM(COALESCE(CAST("جمع_کل" AS DOUBLE PRECISION), 0)) AS total_amount, "عنوان_دستگاه", "عنوان_دستگاه_اصلی" FROM incomes_sheet1 WHERE ((TRANSLATE("عنوان_دستگاه", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%معاونت علمی و فناوری رییس جمهور%' OR TRANSLATE("عنوان_دستگاه_اصلی", 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%معاونت علمی و فناوری رییس جمهور%')) AND TRANSLATE("سال", 'يكيۀة', 'یکیهه') IN ('1402') GROUP BY "عنوان_دستگاه", "عنوان_دستگاه_اصلی"
```

### زمان پاسخ: 10.84 ثانیه

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
  "processing_time_seconds": 36.008175,
  "timestamp": "2025-11-29T07:06:34.410299",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

### زمان پاسخ: 36.66 ثانیه

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
  "processing_time_seconds": 32.633971,
  "timestamp": "2025-11-29T07:07:09.555156",
  "sources_count": 1,
  "database_rows_count": 0,
  "database_columns_count": 0,
  "retrieval_method": "hybrid_with_reranking",
  "retrieval_route": "rag"
}
```

### زمان پاسخ: 33.14 ثانیه

---


## 📈 آمار کلی

- **تعداد سوالات:** 6
- **موفق:** 6 (100.0%)
- **ناموفق:** 0 (0.0%)
- **مسیر Database:** 2 (33.3%)
- **میانگین زمان پاسخ:** 33.51 ثانیه

---

**گزارش تهیه شده توسط:** AI Assistant  
**تاریخ:** 2025-11-29 07:07:11
