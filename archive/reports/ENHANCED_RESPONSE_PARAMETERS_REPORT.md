# گزارش کامل پارامترهای جدید Response API

## تاریخ: 2025-11-27

این گزارش توضیح می‌دهد که هر پارامتر جدید در response API چه داده‌ای برمی‌گرداند و چگونه می‌توان از آن استفاده کرد.

---

## 1. `raw_table_data` - داده‌های خام جدولی

**نوع:** `Dict[str, Any]` یا `None`

**توضیح:** این پارامتر داده‌های خام جدول را به صورت structured (بدون توضیحات متنی) برمی‌گرداند. این فیلد برای استفاده در جداول، export به فرمت‌های مختلف، و پردازش‌های بعدی مفید است.

**ساختار:**
```json
{
  "columns": ["column1", "column2", ...],  // لیست نام ستون‌ها
  "rows": [                                // آرایه ردیف‌ها
    {"column1": "value1", "column2": "value2", ...},
    ...
  ],
  "row_count": 10,                         // تعداد ردیف‌ها
  "column_count": 5,                       // تعداد ستون‌ها
  "sql": "SELECT ...",                     // SQL query که اجرا شده
  "table_type": "database"                 // نوع جدول
}
```

**مثال استفاده:**
- نمایش جدول در UI
- Export به CSV, Excel, JSON
- پردازش داده‌ها در backend
- رسم چارت از داده‌ها

**نکته:** اگر query به database متصل نباشد یا نتیجه‌ای نداشته باشد، مقدار `null` برمی‌گرداند.

---

## 2. `detailed_sources` - منابع با جزئیات کامل

**نوع:** `List[Dict[str, Any]]` یا `None`

**توضیح:** این پارامتر لیست کامل منابعی را که برای پاسخ از آن‌ها استفاده شده، با جزئیات کامل برمی‌گرداند. شامل منابع RAG (متن از اسناد) و Database (نتایج SQL) است.

**ساختار برای RAG Sources:**
```json
{
  "id": "rag_0",                           // شناسه یکتا
  "type": "rag",                           // نوع: "rag" یا "database"
  "source": "filename.pdf",                // نام فایل منبع
  "page": 5,                               // شماره صفحه (در صورت وجود)
  "chunk_index": 12,                       // اندیس chunk
  "content": "متن chunk...",               // محتوای chunk (حداکثر 500 کاراکتر)
  "score": 0.85,                           // نمره relevancy
  "dense_score": 0.80,                     // نمره dense retrieval
  "sparse_score": 0.75,                    // نمره sparse retrieval
  "rerank_score": 0.88,                    // نمره reranking
  "metadata": {...}                        // metadata اضافی
}
```

**ساختار برای Database Source:**
```json
{
  "id": "database_0",
  "type": "database",
  "source": "database_query",
  "sql": "SELECT ...",                     // SQL query اجرا شده
  "table_name": "costs_sheet1",            // نام جدول
  "row_count": 10,                         // تعداد ردیف‌های برگشتی
  "column_count": 5,                       // تعداد ستون‌ها
  "columns": ["col1", "col2", ...],        // لیست ستون‌ها
  "sample_rows": [...],                    // نمونه 3 ردیف اول
  "total_rows": 10,                        // تعداد کل ردیف‌ها
  "metadata": {
    "query_type": "aggregation",
    "success": true
  }
}
```

**مثال استفاده:**
- نمایش منابع استفاده شده در UI
- لینک به صفحات/بخش‌های مرتبط
- نمایش SQL query برای debugging
- تحلیل کیفیت retrieval

---

## 3. `chart_data` - داده‌های آماده برای رسم چارت

**نوع:** `Dict[str, Any]` یا `None`

**توضیح:** این پارامتر داده‌ها را به فرمتی آماده برای رسم چارت (Chart.js, D3.js, و غیره) برمی‌گرداند. همچنین نوع چارت پیشنهادی را نیز مشخص می‌کند.

**ساختار:**
```json
{
  "type": "bar",                           // نوع چارت پیشنهادی: "bar", "line", "pie", "table"
  "suggestions": ["bar", "line", "pie"],   // لیست پیشنهادات نوع چارت (حداکثر 3)
  "data": {
    "labels": ["label1", "label2", ...],   // لیبل‌های محور X
    "datasets": [                          // آرایه dataset‌ها
      {
        "label": "column_name",
        "data": [value1, value2, ...]      // مقادیر عددی
      },
      ...
    ]
  },
  "columns": ["col1", "col2", ...],        // لیست ستون‌ها
  "rows": [...]                            // تمام ردیف‌ها
}
```

**مثال استفاده:**
- رسم چارت Bar, Line, Pie
- نمایش داده‌ها به صورت گرافیکی
- Dashboard و Analytics

**نکته:** 
- نوع چارت بر اساس نوع داده (عددی/متنی) و تعداد ردیف‌ها پیشنهاد می‌شود
- اگر داده‌های عددی و categorical وجود داشته باشد، چارت Bar یا Line پیشنهاد می‌شود
- برای داده‌های محدود (کمتر از 10 ردیف) معمولاً Bar پیشنهاد می‌شود
- برای داده‌های بیشتر، Line پیشنهاد می‌شود

---

## 4. `statistics` - آمار و ارقام

**نوع:** `Dict[str, Any]` یا `None`

**توضیح:** این پارامتر آمار و ارقام مفصل از داده‌ها را برمی‌گرداند. شامل آمار برای هر ستون (حداقل، حداکثر، میانگین برای ستون‌های عددی) است.

**ساختار:**
```json
{
  "total_rows": 100,                       // تعداد کل ردیف‌ها
  "total_columns": 5,                      // تعداد کل ستون‌ها
  "column_statistics": {
    "column_name_numeric": {
      "type": "numeric",                   // نوع: "numeric" یا "text"
      "count": 100,                        // تعداد مقادیر غیر null
      "min": 1000.0,                       // حداقل مقدار
      "max": 50000.0,                      // حداکثر مقدار
      "sum": 1000000.0,                    // جمع کل
      "avg": 10000.0                       // میانگین
    },
    "column_name_text": {
      "type": "text",
      "count": 95,                         // تعداد مقادیر غیر null
      "unique_count": 50                   // تعداد مقادیر یکتا
    }
  }
}
```

**مثال استفاده:**
- نمایش summary statistics در UI
- تحلیل داده‌ها
- نمایش min/max/avg برای ستون‌های عددی
- نمایش تعداد مقادیر یکتا برای ستون‌های متنی

---

## 5. `export_formats` - فرمت‌های قابل Export

**نوع:** `List[str]` یا `None`

**توضیح:** این پارامتر لیست فرمت‌هایی را که داده‌ها می‌توانند به آن‌ها export شوند، برمی‌گرداند.

**مقادیر ممکن:**
- `"csv"` - برای export به CSV
- `"json"` - برای export به JSON
- `"xlsx"` - برای export به Excel
- `"sql"` - برای export به SQL (فقط برای database queries)

**مثال:**
```json
["csv", "json", "xlsx", "sql"]
```

**مثال استفاده:**
- نمایش دکمه‌های export در UI
- دانلود داده‌ها در فرمت‌های مختلف
- به کاربر نشان دادن که چه فرمت‌هایی در دسترس است

---

## خلاصه فیلدهای جدید

| پارامتر | نوع | توضیح | استفاده اصلی |
|---------|-----|-------|--------------|
| `raw_table_data` | Dict/None | داده‌های خام جدول | نمایش جدول، Export |
| `detailed_sources` | List/None | منابع با جزئیات | نمایش منابع، Debugging |
| `chart_data` | Dict/None | داده‌های چارت | رسم چارت |
| `statistics` | Dict/None | آمار و ارقام | Analytics, Summary |
| `export_formats` | List/None | فرمت‌های export | دانلود داده‌ها |

---

## نکات مهم

1. **همه فیلدها optional هستند:** اگر داده‌ای موجود نباشد، مقدار `null` برمی‌گرداند.

2. **Endpoint:** این فیلدها فقط در endpoint `/v2/query` موجود هستند.

3. **Performance:** این فیلدها اضافه نمی‌شوند مگر اینکه داده‌ای برای نمایش وجود داشته باشد.

4. **Backward Compatibility:** فیلدهای قدیمی (`answer`, `table_data`, `sources`) همچنان موجود هستند و تغییری نکرده‌اند.

---

## مثال Response کامل

```json
{
  "success": true,
  "answer": "خلاصه پاسخ...",
  "table_data": "| col1 | col2 |\n| ... | ... |",
  "full_text": "توضیحات کامل...",
  "sources": [...],
  "raw_table_data": {
    "columns": ["col1", "col2"],
    "rows": [{"col1": "val1", "col2": "val2"}],
    "row_count": 1,
    "column_count": 2
  },
  "detailed_sources": [
    {
      "id": "database_0",
      "type": "database",
      "sql": "SELECT ...",
      "row_count": 1
    }
  ],
  "chart_data": {
    "type": "bar",
    "suggestions": ["bar", "line"],
    "data": {
      "labels": ["label1"],
      "datasets": [{"label": "col1", "data": [100]}]
    }
  },
  "statistics": {
    "total_rows": 1,
    "total_columns": 2,
    "column_statistics": {...}
  },
  "export_formats": ["csv", "json", "xlsx", "sql"]
}
```

---

## تاریخ به‌روزرسانی

این گزارش در تاریخ 2025-11-27 ایجاد شده است.


