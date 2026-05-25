# گزارش کامل تست سوالات API Server

**تاریخ تست:** 2025-11-28 20:28:29

**Collection:** finance_budget_new_1764252643

**API URL:** http://185.13.230.254:8010/v2/query


## خلاصه نتایج

- **تعداد کل سوالات:** 8

- **موفق:** 6 (75.0%)

- **ناموفق:** 2 (25.0%)


## توزیع Route

- **rag:** 6 سوال



## جزئیات نتایج


### Query 1: expense_summary


**سوال:** مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402


#### خطا:


```
{"detail":"Streaming retrieval returned no data"}
```


- **Status Code:** 500

- **زمان:** 47.64 ثانیه


---


### Query 2: income_entity_year


**سوال:** درآمد های گمرک جمهوری اسلامی ایران در سال 1398


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای ارائه درآمد گمرک جمهوری اسلامی ایران در سال 1398 در متن موجود نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای ارائه درآمد گمرک جمهوری اسلامی ایران در سال 1398 در متن موجود نیست.",
  "table_data": null,
  "full_text": "ش",
  "sources": [
    {
      "id": "chunk_12",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 13: قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401\nعنوان: سازمان امور مالیاتی کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 13,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      },
      "dense_score": 0.95,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 8.042415618896484,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 31.099913,
    "timestamp": "2025-11-28T20:19:46.583209",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 8.4e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.95,
      "sparse_score": null,
      "rerank_score": 8.042415618896484,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 13,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export_formats": null
}...
```


</details>


---


### Query 3: income_entity_years


**سوال:** در امد های سازمان ملي استاندارد در سال ها 1399 تا 1402


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای ارائه خلاصه‌ای درباره درآمدهای سازمان ملی استاندارد در سال‌های 1399 تا 1402 در دسترس نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای ارائه خلاصه‌ای درباره درآمدهای سازمان ملی استاندارد در سال‌های 1399 تا 1402 در دسترس نیست.",
  "table_data": null,
  "full_text": "📌",
  "sources": [
    {
      "id": "chunk_12",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 13: قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401\nعنوان: سازمان امور مالیاتی کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 13,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      },
      "dense_score": 0.95,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 8.30186653137207,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 30.288768,
    "timestamp": "2025-11-28T20:21:41.426557",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 7.7e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.95,
      "sparse_score": null,
      "rerank_score": 8.30186653137207,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110200 | بند دوم: مالیات بر درآمدها | 110207 | درآمد حاصل از رسیدگی پرونده های مالیاتی مراکز درمانی مربوط به عملکرد سالهای 1400،1399،1398 | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 1000.0 | 0 | 1000.0 | 0 | 0 | 0 | 1000.0 | 0 | 1000.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 13,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export...
```


</details>


---


### Query 4: income_component


**سوال:** درامد های حاصل از واگذاری دارایی های سرمایه ای در سال 1402


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره درآمدهای حاصل از واگذاری دارایی‌های سرمایه‌ای در سال 1402 در متن موجود نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای تهیه خلاصه‌ای دقیق درباره درآمدهای حاصل از واگذاری دارایی‌های سرمایه‌ای در سال 1402 در متن موجود نیست.",
  "table_data": null,
  "full_text": "ش",
  "sources": [
    {
      "id": "chunk_0",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 1: قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401\nعنوان: سازمان امور مالیاتی کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      },
      "dense_score": 0.9,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 6.8300323486328125,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 29.890974,
    "timestamp": "2025-11-28T20:22:12.977368",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 7.9e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.9,
      "sparse_score": null,
      "rerank_score": 6.8300323486328125,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export_form...
```


</details>


---


### Query 5: income_component


**سوال:** درامدهای مالیاتی در سال 1402


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای ارائه خلاصه‌ای درباره درآمدهای مالیاتی در سال 1402 در متن موجود نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای ارائه خلاصه‌ای درباره درآمدهای مالیاتی در سال 1402 در متن موجود نیست.",
  "table_data": null,
  "full_text": "ش",
  "sources": [
    {
      "id": "chunk_0",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 1: قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401\nعنوان: سازمان امور مالیاتی کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      },
      "dense_score": 0.9,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 7.545069217681885,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 29.488002,
    "timestamp": "2025-11-28T20:22:43.930998",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 7.7e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.9,
      "sparse_score": null,
      "rerank_score": 7.545069217681885,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export_formats": null
}...
```


</details>


---


### Query 6: income_component_years


**سوال:** درامد حاصل از جرایم و خسارات در سال های 1398 تا 1400


#### خطا:


```
{"detail":"Streaming retrieval returned no data"}
```


- **Status Code:** 500

- **زمان:** 33.77 ثانیه


---


### Query 7: breakdown_entity


**سوال:** درامد های دانشگاه امیرکبیر در سال 1403 از چه جز هایی وصول شده است ؟


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای ذکر جزئیات درآمدهای دانشگاه امیرکبیر در سال 1403 در متن موجود نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای ذکر جزئیات درآمدهای دانشگاه امیرکبیر در سال 1403 در متن موجود نیست.",
  "table_data": null,
  "full_text": "ح",
  "sources": [
    {
      "id": "chunk_256",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 257: قسمت اول: درآمدها | 140000 | بخش چهارم: درآمدهای حاصل از فروش کالاها و خدمات | 140100 | بنداول: درآمدهای حاصل از خدمات | 140103 | درآمد حاصل از خدمات آموزشی و فرهنگی | 114030 | موسسه نشر آثار حضرت امام قدس سره | سازمان برنامه و بودجه کشور | 0.0 | 0 | 0.0 | 5000 | 0 | 5000 | 5000.0 | 0 | 5000.0 | 1401\nعنوان: سازمان برنامه و بودجه کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 140000 | بخش چهارم: درآمدهای حاصل از فروش کالاها و خدمات | 140100 | بنداول: درآمدهای حاصل از خدمات | 140103 | درآمد حاصل از خدمات آموزشی و فرهنگی | 114030 | موسسه نشر آثار حضرت امام قدس سره | سازمان برنامه و بودجه کشور | 0.0 | 0 | 0.0 | 5000 | 0 | 5000 | 5000.0 | 0 | 5000.0 | 1401",
        "code": "114030",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 257,
        "sheet_name": "Sheet1",
        "title": "سازمان برنامه و بودجه کشور",
        "type": "excel_row"
      },
      "dense_score": 0.95,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 7.672056198120117,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 39.050263,
    "timestamp": "2025-11-28T20:24:06.230253",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 8.8e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.95,
      "sparse_score": null,
      "rerank_score": 7.672056198120117,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 140000 | بخش چهارم: درآمدهای حاصل از فروش کالاها و خدمات | 140100 | بنداول: درآمدهای حاصل از خدمات | 140103 | درآمد حاصل از خدمات آموزشی و فرهنگی | 114030 | موسسه نشر آثار حضرت امام قدس سره | سازمان برنامه و بودجه کشور | 0.0 | 0 | 0.0 | 5000 | 0 | 5000 | 5000.0 | 0 | 5000.0 | 1401",
        "code": "114030",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 257,
        "sheet_name": "Sheet1",
        "title": "سازمان برنامه و بودجه کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export_formats": null
}...
```


</details>


---


### Query 8: breakdown_entity


**سوال:** راه های در امدی بنیاد ملی نخبگان در سال 1402 چه مواردی بودند ؟


#### نتایج:


- **Route:** `rag`

- **زمان پاسخ:** 0.00 ثانیه

- **Confidence:** 0.00

- **تعداد ردیف:** 0

- **تعداد منابع:** 1


#### پاسخ:


```
اطلاعات کافی برای پاسخ به پرسش در متن موجود نیست.
```


#### منابع (1 مورد):


**منبع 1:**

- صفحه: None

- متن: ...


#### پاسخ کامل API (JSON):


<details>
<summary>مشاهده پاسخ کامل</summary>


```json
{
  "success": true,
  "answer": "اطلاعات کافی برای پاسخ به پرسش در متن موجود نیست.",
  "table_data": null,
  "full_text": "ش",
  "sources": [
    {
      "id": "chunk_0",
      "text": "Sheet: Sheet1\nHeaders: عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال\nRow 1: قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401\nعنوان: سازمان امور مالیاتی کشور",
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      },
      "dense_score": 0.9,
      "bm25_score": 10.0,
      "hybrid_score": 0.95,
      "rerank_score": 7.246212005615234,
      "original_score": 0.95
    }
  ],
  "confidence": 0.04000000000000001,
  "metadata": {
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
    "processing_time_seconds": 31.483589,
    "timestamp": "2025-11-28T20:24:38.965879",
    "sources_count": 1,
    "database_rows_count": 0,
    "database_columns_count": 0,
    "retrieval_method": "hybrid_with_reranking",
    "retrieval_route": "rag",
    "from_cache": true
  },
  "domain_info": {
    "domain": "financial",
    "confidence": 0.7062937062937062,
    "summary": "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها: قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | اس",
    "keywords": [
      "مالی",
      "درآمد",
      "سازمان",
      "دولتی",
      "بند",
      "بخش",
      "قسمت",
      "حساب"
    ],
    "method": "heuristic"
  },
  "error": null,
  "processing_time": 8.8e-05,
  "used_features": {
    "reranking": true,
    "multi_hop": false,
    "query_understanding": true,
    "self_rag": false,
    "corrective_rag": false
  },
  "self_rag_metadata": {},
  "corrective_rag_metadata": {},
  "conversation_id": null,
  "database_results": {},
  "route_path": "rag",
  "suggested_questions": [],
  "applicable_filters": [],
  "api_version": "v2",
  "raw_table_data": null,
  "detailed_sources": [
    {
      "id": "rag_0",
      "type": "rag",
      "source": "",
      "page": null,
      "chunk_index": null,
      "content": "",
      "score": 0.95,
      "dense_score": 0.9,
      "sparse_score": null,
      "rerank_score": 7.246212005615234,
      "metadata": {
        "cells": "قسمت اول: درآمدها | 110000 | بخش اول: درآمدهای مالیاتی | 110100 | بند اول: مالیات اشخاص حقوقی | 110102 | مالیات علی الحساب اشخاص حقوقی دولتی - وصول ماهانه یک دوازدهم رقم | 110100 | سازمان امور مالیاتی کشور | سازمان امور مالیاتی کشور | 116092864.0 | 0 | 116092864.0 | 0 | 0 | 0 | 116092864.0 | 0 | 116092864.0 | 1401",
        "code": "110100",
        "dataset_type": "financial",
        "file_type": "excel",
        "headers": "عنوان قسمت | کد بخش | عنوان بخش | کد بند | عنوان بند | کد جزء | عنوان جزء | کد دستگاه | عنوان دستگاه | عنوان دستگاه اصلی | ملی در آمد عمومی | استانی در آمد عمومی | جمع در آمد عمومی | ملی در آمد اختصاصی | استانی در آمد اختصاصی | جمع در آمد اختصاصی | ملی جمع کل | استانی جمع کل | جمع کل | سال",
        "row_index": 1,
        "sheet_name": "Sheet1",
        "title": "سازمان امور مالیاتی کشور",
        "type": "excel_row"
      }
    }
  ],
  "chart_data": null,
  "statistics": null,
  "export_formats": null
}...
```


</details>


---

