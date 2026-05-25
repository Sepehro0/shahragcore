# 🎯 طراحی سیستم پاسخگویی به سوالات پیچیده مالی

## 📊 تحلیل نیازمندی‌ها

### **مشکلات فعلی:**
1. ❌ سیستم فعلی فقط `SUM` ساده انجام می‌دهد
2. ❌ نمی‌تواند بدون فیلتر entity/component کار کند (مثل "بیشترین درآمد")
3. ❌ نمی‌تواند روی فیلدهای ملی/استانی تفکیک کند
4. ❌ نمی‌تواند بین جداول JOIN بزند (income + cost)
5. ❌ نمی‌تواند سوالات چند بخشی (multi-part) را handle کند

### **نیازمندی‌های جدید:**

#### 1️⃣ **Aggregation Queries (بدون فیلتر خاص)**
```
"کدام سازمان ها در سال 1398 بیشترین درامد را کسب کردند ؟"
```
- نیاز به: `GROUP BY عنوان_دستگاه` + `ORDER BY SUM DESC` + `LIMIT`
- **فیلتر**: فقط سال
- **خروجی**: لیست Top N دستگاه

#### 2️⃣ **Filtered Aggregation (فیلتر روی component + تفکیک ملی/استانی)**
```
"درامد های ملی حاصل از اجاره در سال 1398 چقدر بوده است و توسط چه دستگاهی وصول شده است ؟"
```
- نیاز به: فیلتر `عنوان_جزء ILIKE '%اجاره%'` + `SUM(ملي_جمع_کل)` + `GROUP BY دستگاه`
- **فیلتر**: سال + component + نوع درآمد (ملی)
- **خروجی**: لیست دستگاه‌ها با مبالغ

#### 3️⃣ **Multi-Part Breakdown (تفکیک چند بعدی)**
```
"وزارت کشور در سال 1398 مجموعا چقدر درامد داشته است ؟ 
چه بخشی از ان ملی و چه بخشی استانی بوده است ؟ 
و از چه راه هایی کسب شده است ؟ هرکدام چقدر سهم دارند ؟"
```
- نیاز به: 
  - `SUM(ملي_جمع_کل)` + `SUM(استاني_جمع_کل)` + `SUM(جمع_کل)`
  - `GROUP BY عنوان_جزء, عنوان_بند`
- **فیلتر**: سال + entity
- **خروجی**: 
  - مبلغ کل
  - تفکیک ملی/استانی
  - breakdown منابع

#### 4️⃣ **Cross-Table Calculation (محاسبه تراز)**
```
"زیان ده ترین دستگاه سال 1403 چه دستگاهی است ؟"
```
- نیاز به: 
  - `JOIN` بین `incomes_sheet1` و `costs_sheet1`
  - محاسبه: `total_income - total_cost`
  - `ORDER BY balance ASC`
- **فیلتر**: سال
- **خروجی**: دستگاه با بیشترین زیان

---

## 🏗️ معماری پیشنهادی

### **1. توسعه QueryAnalyzer**

باید قابلیت‌های زیر را اضافه کنیم:

```python
class AdvancedQueryAnalyzer:
    """
    تحلیلگر پیشرفته سوالات
    """
    
    def detect_query_category(self, query: str) -> str:
        """
        تشخیص دسته‌بندی اصلی سوال:
        - 'simple_sum': جمع ساده با فیلتر (مثل سوالات فعلی)
        - 'top_n': بیشترین/کمترین (نیاز به ORDER + LIMIT)
        - 'breakdown': تفکیک چند بعدی
        - 'cross_table': محاسبات بین جداولی
        """
        
    def detect_aggregation_type(self, query: str) -> Dict:
        """
        تشخیص نوع تجمیع:
        - needs_groupby: آیا نیاز به GROUP BY دارد؟
        - group_fields: ['عنوان_دستگاه', 'عنوان_جزء', ...]
        - needs_sort: آیا نیاز به ORDER BY دارد؟
        - sort_direction: 'DESC' | 'ASC'
        - limit: تعداد نتایج (None | int)
        """
        
    def detect_multi_dimension(self, query: str) -> Dict:
        """
        تشخیص ابعاد مختلف در سوال:
        - asks_total: آیا مجموع می‌خواهد؟
        - asks_national_provincial: آیا تفکیک ملی/استانی می‌خواهد؟
        - asks_sources: آیا breakdown منابع می‌خواهد؟
        - asks_share: آیا درصد/سهم می‌خواهد؟
        """
        
    def detect_cross_table_need(self, query: str) -> Dict:
        """
        تشخیص نیاز به JOIN بین جداول:
        - needs_income: True/False
        - needs_cost: True/False
        - calculation_type: 'balance' | 'ratio' | None
        """
```

### **2. توسعه TextToSQLAgent**

```python
class AdvancedTextToSQLAgent:
    
    def build_advanced_sql(self, analysis: Dict, collection: str) -> str:
        """
        ساخت SQL پیشرفته بر اساس آنالیز
        """
        category = analysis['category']
        
        if category == 'simple_sum':
            return self._build_simple_sum_sql(analysis)
        elif category == 'top_n':
            return self._build_top_n_sql(analysis)
        elif category == 'breakdown':
            return self._build_breakdown_sql(analysis)
        elif category == 'cross_table':
            return self._build_cross_table_sql(analysis)
    
    def _build_top_n_sql(self, analysis: Dict) -> str:
        """
        مثال: "کدام سازمان ها بیشترین درآمد را داشتند؟"
        
        SELECT "عنوان_دستگاه", "عنوان_دستگاه_اصلی",
               SUM(CAST("جمع_کل" AS DOUBLE PRECISION)) as total
        FROM incomes_sheet1
        WHERE "سال" IN ('1398')
        GROUP BY "عنوان_دستگاه", "عنوان_دستگاه_اصلی"
        ORDER BY total DESC
        LIMIT 10
        """
    
    def _build_breakdown_sql(self, analysis: Dict) -> str:
        """
        مثال: "وزارت کشور چقدر درآمد؟ ملی و استانی؟ از چه راه‌ها؟"
        
        SELECT 
            SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_national,
            SUM(CAST("استاني_جمع_کل" AS DOUBLE PRECISION)) as total_provincial,
            SUM(CAST("جمع_کل" AS DOUBLE PRECISION)) as total_all,
            "عنوان_جزء", "عنوان_بند",
            SUM(CAST("جمع_کل" AS DOUBLE PRECISION)) as source_total
        FROM incomes_sheet1
        WHERE "سال" = '1398'
          AND entity_filter
        GROUP BY "عنوان_جزء", "عنوان_بند"
        ORDER BY source_total DESC
        """
    
    def _build_cross_table_sql(self, analysis: Dict) -> str:
        """
        مثال: "زیان‌ده‌ترین دستگاه"
        
        WITH income_agg AS (...),
             cost_agg AS (...)
        SELECT ..., (income - cost) as balance
        FROM income_agg
        FULL OUTER JOIN cost_agg ON ...
        ORDER BY balance ASC
        LIMIT 10
        """
```

### **3. بهبود Response Formatting**

```python
class AdvancedResponseFormatter:
    
    def format_top_n_response(self, rows: List[Dict]) -> str:
        """
        فرمت پاسخ برای سوالات Top N:
        "سازمان‌های برتر از نظر درآمد در سال 1398:
        1. شرکت ملی نفت ایران: 1,574,215,334,000,000 ریال
        2. سازمان امور مالیاتی: 1,438,789,479,000,000 ریال
        ..."
        """
    
    def format_breakdown_response(self, rows: List[Dict], totals: Dict) -> str:
        """
        فرمت پاسخ برای سوالات breakdown:
        "وزارت کشور در سال 1398:
        - درآمد کل: XXX ریال
        - درآمد ملی: XXX ریال (YY%)
        - درآمد استانی: XXX ریال (YY%)
        
        منابع درآمد:
        1. منبع A: XXX ریال (ZZ%)
        2. منبع B: XXX ریال (ZZ%)
        ..."
        """
    
    def format_cross_table_response(self, rows: List[Dict]) -> str:
        """
        فرمت پاسخ برای محاسبات cross-table:
        "زیان‌ده‌ترین دستگاه‌ها در سال 1403:
        1. دستگاه A: 
           - درآمد: XXX ریال
           - هزینه: YYY ریال
           - تراز: ZZZ ریال (زیان)
        ..."
        """
```

---

## 🚀 Implementation Plan

### **Phase 1: توسعه QueryAnalyzer** ✅
- [ ] اضافه کردن `detect_query_category`
- [ ] اضافه کردن `detect_aggregation_type`
- [ ] اضافه کردن `detect_multi_dimension`
- [ ] اضافه کردن `detect_cross_table_need`

### **Phase 2: توسعه SQL Builder** ✅
- [ ] پیاده‌سازی `_build_top_n_sql`
- [ ] پیاده‌سازی `_build_breakdown_sql`
- [ ] پیاده‌سازی `_build_cross_table_sql`
- [ ] تست هر builder به صورت مجزا

### **Phase 3: بهبود Response Formatter** ✅
- [ ] پیاده‌سازی `format_top_n_response`
- [ ] پیاده‌سازی `format_breakdown_response`
- [ ] پیاده‌سازی `format_cross_table_response`

### **Phase 4: Integration & Testing** ✅
- [ ] یکپارچه‌سازی با سیستم فعلی
- [ ] Regression test سوالات قبلی
- [ ] تست سوالات جدید
- [ ] بهینه‌سازی performance

---

## ⚠️ نکات مهم

### **1. Backward Compatibility**
- تمام تغییرات باید به گونه‌ای باشد که سوالات قبلی همچنان کار کنند
- از strategy pattern برای انتخاب SQL builder استفاده می‌کنیم

### **2. کارایی**
- برای سوالات Top N از `LIMIT` استفاده می‌کنیم
- برای محاسبات پیچیده از `CTE` (Common Table Expressions) استفاده می‌کنیم

### **3. خوانایی**
- پاسخ‌ها باید ساختار یافته و خوانا باشند
- استفاده از bullet points و شماره‌گذاری
- نمایش درصدها در کنار اعداد مطلق

### **4. دقت**
- همیشه normalization کاراکترهای فارسی
- handle کردن NULL values در JOIN
- استفاده از COALESCE برای مقادیر پیش‌فرض

