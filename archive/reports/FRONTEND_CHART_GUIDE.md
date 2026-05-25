# راهنمای جامع Chart برای فرانت

**تاریخ**: 1403/11/08 (2026-01-28)  
**نسخه**: 1.0

---

## 📋 خلاصه

این مستند نحوه استفاده از API response برای تشخیص و نمایش chart مناسب را شرح می‌دهد.

---

## 🎯 Response فعلی API

API در حال حاضر این فیلدها را برای chart ارائه می‌دهد:

### 1. `chart_data` (موجود)

```json
{
  "chart_data": {
    "type": "bar",
    "suggestions": ["pie", "bar"],
    "data": {
      "labels": ["بخش چهارم: درآمدهای..."],
      "datasets": [
        {
          "label": "total_amount",
          "data": [125000]
        }
      ]
    },
    "columns": ["عنوان_بخش", "عنوان_بند", "عنوان_جزء", "total_amount"],
    "rows": [...]
  }
}
```

### 2. `statistics` (موجود)

```json
{
  "statistics": {
    "total_rows": 1,
    "total_columns": 4,
    "column_statistics": {
      "total_amount": {
        "type": "numeric",
        "count": 1,
        "min": 125000,
        "max": 125000,
        "sum": 125000,
        "avg": 125000
      }
    }
  }
}
```

### 3. `metadata.analysis_used` (موجود)

```json
{
  "metadata": {
    "database_results": {
      "analysis_used": "simple_sum"
    }
  }
}
```

---

## 🎨 روش‌های تشخیص نوع Chart

### روش 1: استفاده مستقیم از `chart_data.type` ⭐ (ساده‌ترین)

```javascript
function selectChart(response) {
  const chartType = response.chart_data.type;
  const chartData = response.chart_data.data;
  const chartConfig = {};
  
  switch(chartType) {
    case 'bar':
      return renderBarChart(chartData, chartConfig);
    case 'line':
      return renderLineChart(chartData, chartConfig);
    case 'pie':
      return renderPieChart(chartData, chartConfig);
    case 'single_value':
      return renderSingleValue(chartData.datasets[0].data[0], chartConfig);
    default:
      return renderBarChart(chartData, chartConfig);
  }
}
```

### روش 2: استفاده از Query Classification (پیشنهادی - دقیق‌تر) ⭐⭐

اگر API بخش `query_classification` را اضافه کند:

```javascript
function selectChartAdvanced(response) {
  const classification = response.query_classification;
  const chartData = response.chart_data.data;
  
  // انتخاب بر اساس دسته‌بندی
  const chartType = classification.chart_type;
  const chartConfig = classification.chart_config;
  
  // نمایش اطلاعات به کاربر
  displayQueryInfo({
    category: classification.category_name,
    confidence: classification.confidence,
    dataType: classification.data_type
  });
  
  // رندر chart
  return renderChart(chartType, chartData, chartConfig);
}
```

### روش 3: تصمیم‌گیری هوشمند در فرانت (پیشرفته)

```javascript
function intelligentChartSelection(response) {
  const { chart_data, statistics, metadata } = response;
  
  // تحلیل داده‌ها
  const rowCount = statistics.total_rows;
  const hasMultipleYears = detectMultipleYears(chart_data.rows);
  const analysisType = metadata.database_results?.analysis_used;
  
  // تصمیم‌گیری
  if (rowCount === 1) {
    // یک ردیف = نمایش عددی
    return {
      type: 'single_value',
      config: {
        showUnit: true,
        showComparison: true
      }
    };
  } else if (hasMultipleYears) {
    // چند سال = نمودار خطی (روند)
    return {
      type: 'line',
      config: {
        showTrend: true,
        showGrowthRate: true
      }
    };
  } else if (analysisType === 'comparison') {
    // مقایسه = نمودار میله‌ای
    return {
      type: 'bar',
      config: {
        horizontal: false,
        showValues: true
      }
    };
  } else if (rowCount <= 5) {
    // تعداد کم = دایره‌ای
    return {
      type: 'pie',
      config: {
        showPercentage: true
      }
    };
  } else {
    // پیش‌فرض = میله‌ای
    return {
      type: 'bar',
      config: {
        horizontal: true,
        showValues: true
      }
    };
  }
}

// توابع کمکی
function detectMultipleYears(rows) {
  if (!rows || rows.length === 0) return false;
  const years = new Set(rows.map(r => r.سال).filter(Boolean));
  return years.size > 1;
}
```

---

## 📊 نقشه راه Chart Types

| وضعیت | Chart Type | استفاده | مثال سوال |
|-------|-----------|----------|-----------|
| 1 ردیف، 1 سال | `single_value` | نمایش عددی بزرگ | "درآمد پست بانک در 1403" |
| 1 دستگاه، چند سال | `line` | روند زمانی | "درآمد از 1398 تا 1403" |
| چند دستگاه، 1 سال | `bar` | مقایسه | "مقایسه A و B در 1403" |
| چند دستگاه، چند سال | `grouped_bar` | مقایسه زمانی | "مقایسه A و B از 1398 تا 1403" |
| تعداد کم (≤5) | `pie` | سهم نسبی | "توزیع بودجه بخش‌ها" |

---

## 🔧 پیکربندی Chart بر اساس نوع

### Single Value

```javascript
{
  type: 'single_value',
  config: {
    value: 125000,
    unit: 'میلیون ریال',
    showUnit: true,
    showComparison: true,
    comparisonText: 'نسبت به سال قبل',
    color: '#4CAF50'
  }
}
```

### Line Chart

```javascript
{
  type: 'line',
  config: {
    xAxis: {
      label: 'سال',
      values: ['1398', '1399', '1400', '1401', '1402', '1403']
    },
    yAxis: {
      label: 'مبلغ (میلیون ریال)',
      showGrid: true
    },
    showTrend: true,
    showGrowthRate: true,
    smooth: true,
    colors: ['#2196F3']
  }
}
```

### Bar Chart

```javascript
{
  type: 'bar',
  config: {
    horizontal: false,
    xAxis: {
      label: 'دستگاه',
      rotate: 45
    },
    yAxis: {
      label: 'مبلغ (میلیون ریال)',
      showGrid: true
    },
    showValues: true,
    colors: ['#FF9800', '#4CAF50', '#2196F3']
  }
}
```

### Pie Chart

```javascript
{
  type: 'pie',
  config: {
    showPercentage: true,
    showLegend: true,
    colors: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
    doughnut: false
  }
}
```

### Grouped Bar Chart

```javascript
{
  type: 'grouped_bar',
  config: {
    xAxis: {
      label: 'سال',
      values: ['1398', '1399', '1400']
    },
    yAxis: {
      label: 'مبلغ (میلیون ریال)'
    },
    groupBy: 'entity',
    showLegend: true,
    showValues: true,
    colors: ['#2196F3', '#FF9800']
  }
}
```

---

## 💡 مثال‌های کامل

### مثال 1: سوال "منابع پارک فناوری پردیس سال 99"

**Response API**:
```json
{
  "chart_data": {
    "type": "bar",
    "data": {
      "labels": ["بخش چهارم"],
      "datasets": [{"label": "total_amount", "data": [125000]}]
    }
  },
  "statistics": {
    "total_rows": 1
  }
}
```

**کد فرانت**:
```javascript
// تشخیص
const rowCount = response.statistics.total_rows;  // 1
const chartType = rowCount === 1 ? 'single_value' : response.chart_data.type;

// رندر
if (chartType === 'single_value') {
  renderSingleValue({
    value: 125000,
    unit: 'میلیون ریال',
    label: 'منابع پارک فناوری پردیس',
    year: '1399'
  });
}
```

### مثال 2: سوال "درآمد وزارت نفت از 1398 تا 1403"

**Response API**:
```json
{
  "chart_data": {
    "type": "line",
    "data": {
      "labels": ["1398", "1399", "1400", "1401", "1402", "1403"],
      "datasets": [{"label": "وزارت نفت", "data": [100, 120, 150, 180, 200, 250]}]
    }
  }
}
```

**کد فرانت**:
```javascript
renderLineChart({
  data: response.chart_data.data,
  options: {
    title: 'روند درآمد وزارت نفت',
    showTrend: true,
    showGrowthRate: true
  }
});
```

### مثال 3: سوال "مقایسه A و B در 1403"

**Response API**:
```json
{
  "chart_data": {
    "type": "bar",
    "data": {
      "labels": ["دستگاه A", "دستگاه B"],
      "datasets": [{"label": "مبلغ", "data": [500000, 300000]}]
    }
  }
}
```

**کد فرانت**:
```javascript
renderBarChart({
  data: response.chart_data.data,
  options: {
    title: 'مقایسه بودجه',
    horizontal: false,
    showValues: true
  }
});
```

---

## 🚀 پیشنهاد: افزودن `query_classification` به API

### تغییرات در API Server

```python
# در api_server.py یا answer_orchestrator.py
from services.budget_query_classifier import classify_budget_query

async def process_query(user_query: str, collection_name: str):
    # پردازش معمولی
    response = await answer_orchestrator.answer(user_query, collection_name)
    
    # افزودن classification برای budget_financial
    if collection_name == 'budget_financial':
        classification = classify_budget_query(user_query)
        response['query_classification'] = {
            'category_code': classification['category_code'],
            'category_name': classification['category_name'],
            'chart_type': classification['chart_type'],
            'chart_config': classification['chart_config'],
            'confidence': classification['confidence'],
            'data_type': classification['data_type'],
            'time_scope': classification['time_scope'],
            'query_intent': classification['query_intent']
        }
    
    return response
```

### نمونه Response بهبود یافته

```json
{
  "success": true,
  "answer": "...",
  "chart_data": {...},
  "statistics": {...},
  "query_classification": {
    "category_code": "FET_INC_DEV_1Y",
    "category_name": "درآمد دستگاه در یک سال",
    "chart_type": "single_value",
    "chart_config": {
      "show_unit": true,
      "show_comparison_to_prev_year": true
    },
    "confidence": 0.95,
    "data_type": "income",
    "time_scope": "single_year",
    "query_intent": "fetch"
  }
}
```

---

## 📝 چک لیست برای فرانت

- [ ] بررسی `response.chart_data.type`
- [ ] بررسی `response.statistics.total_rows`
- [ ] بررسی چند ساله بودن (`chart_data.rows`)
- [ ] استفاده از `query_classification` (اگر موجود باشد)
- [ ] نمایش مقدار واحد برای 1 ردیف
- [ ] نمایش نمودار خطی برای چند سال
- [ ] نمایش نمودار میله‌ای برای مقایسه
- [ ] نمایش درصد در نمودار دایره‌ای
- [ ] فرمت کردن اعداد (جداکننده هزارگان)
- [ ] نمایش واحد (میلیون ریال)
- [ ] پشتیبانی از RTL
- [ ] رنگ‌بندی مناسب

---

## 🎓 خلاصه

**برای شروع سریع**:
```javascript
// استفاده ساده
const chartType = response.chart_data.type;
renderChart(chartType, response.chart_data.data);
```

**برای دقت بیشتر**:
```javascript
// استفاده از classification (بعد از افزودن به API)
const classification = response.query_classification;
const chartType = classification.chart_type;
const chartConfig = classification.chart_config;
renderChart(chartType, response.chart_data.data, chartConfig);
```

**برای کنترل کامل**:
```javascript
// تصمیم‌گیری هوشمند در فرانت
const chartDecision = intelligentChartSelection(response);
renderChart(chartDecision.type, response.chart_data.data, chartDecision.config);
```

---

**تهیه شده توسط**: Backend Team  
**آخرین بروزرسانی**: 1403/11/08
