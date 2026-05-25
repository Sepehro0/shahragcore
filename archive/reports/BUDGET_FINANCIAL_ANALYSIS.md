# 🔍 تحلیل Collection budget_financial

**تاریخ**: 19 دسامبر 2025  
**وضعیت**: ❌ **نیاز به بازسازی**

---

## 📊 خلاصه مشکل

Collection `budget_financial` با embedding model متفاوتی ساخته شده و با سیستم فعلی سازگار نیست.

### خطای اصلی

```
InvalidArgumentError: Collection expecting embedding with dimension of 768, got 384
```

**علت**:
- Collection با embedding model dimension 768 ساخته شده
- سیستم فعلی از model dimension 384 استفاده می‌کند
- ChromaDB نمی‌تواند embeddings با dimensions مختلف را query کند

---

## 📂 اطلاعات Collection

### وضعیت فعلی

```
Collection: budget_financial
Documents: 402
Embedding Dimension: 768 (incompatible)
Status: ❌ Not Queryable
```

### Metadata Structure

```json
{
  "سال": "1403",
  "table": "masaref",
  "جمع_کل": "17133379",
  "دستگاه_اجرایی": "نهاد رياست جمهوري",
  "type": "budget",
  "دستگاه_اصلی": "نهاد رياست جمهوري",
  "source": "masaref2.xlsx"
}
```

### فایل‌های منبع

1. **masaref2.xlsx** (مصارف - هزینه‌ها)
   - Shape: (?, 15 columns)
   - Columns: دستگاه اصلی، دستگاه اجرایی، اعتبارات هزینه‌ای، تملک دارایی، سال
   - Data: بودجه هزینه‌ای و سرمایه‌ای دستگاه‌ها

2. **manabe.xlsx** (منابع - درآمدها)
   - Shape: (?, 20 columns)
   - Columns: قسمت، بخش، بند، جزء، دستگاه، درآمد عمومی، درآمد اختصاصی، سال
   - Data: درآمدهای ملی و استانی دستگاه‌ها

---

## 🎯 نوع Queryهای مورد انتظار

### 1. ارجاع سلول خاص

**الگو**: `[نوع اعتبار] + [دستگاه] + [سال]`

```
✅ "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403"
✅ "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403"
✅ "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403"
✅ "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403"
✅ "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403"
```

**پاسخ مورد انتظار**: عدد مشخص (مثلاً 11823985 میلیون ریال)

### 2. جمع چند سلول

**الگو**: `بودجه [دستگاه] در سال [سال]`

```
✅ "بودجه فرهنگستان هنر در سال 1403"
✅ "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403"
✅ "درآمدهای وزارت نفت در سال 1401 چقدر است"
✅ "بودجه دانشگاه تهران"  # سال 1403 پیش‌فرض
```

**پاسخ مورد انتظار**: جمع کل (هزینه‌ای + سرمایه‌ای)

### 3. درآمد با تفکیک

**الگو**: `درآمد [نوع] [دستگاه] در سال [سال]`

```
✅ "درامد استانی اختصاصی دانشگاه تبریز در سال 1403"
✅ "درامد ملی سازمان تامین اجتماعی در سال 1403"
✅ "درامد کل موسسه کار و تامین اجتماعی در سال 1402"
```

**پاسخ مورد انتظار**: عدد با تفکیک (ملی/استانی، عمومی/اختصاصی)

---

## 🔧 راه‌حل‌های پیشنهادی

### گزینه 1: بازسازی Collection (توصیه می‌شود) ✅

#### مزایا:
- ✅ سازگار با سیستم فعلی
- ✅ استفاده از embedding model بهینه
- ✅ metadata structure بهتر
- ✅ chunking strategy بهینه

#### مراحل:

**Step 1: حذف Collection قدیمی**
```python
import chromadb

client = chromadb.PersistentClient(path="chroma_db")
client.delete_collection("budget_financial")
```

**Step 2: پردازش فایل‌های Excel**
```python
import pandas as pd

# masaref2.xlsx - مصارف
df_masaref = pd.read_excel('archive/data_files/masaref2.xlsx')

# manabe.xlsx - منابع
df_manabe = pd.read_excel('archive/data_files/manabe.xlsx')

# ساخت chunks
chunks = []

# برای هر سطر از masaref
for idx, row in df_masaref.iterrows():
    chunk = {
        'text': f"""
دستگاه: {row['عنوان دستگاه اجرايي']}
سال: {row['سال']}
اعتبارات هزینه‌ای عمومی: {row['براورد اعتبارات هزینه ای - عمومی']}
اعتبارات هزینه‌ای متفرقه: {row['برآورد اعتبارات هزینه ای - متفرقه']}
اعتبارات هزینه‌ای اختصاصی: {row['براورد اعتبارات هزینه ای - اختصاصی']}
جمع اعتبارات هزینه‌ای: {row['جمع براورد اعتبارات هزینه ای']}
تملک دارایی سرمایه‌ای عمومی: {row[' براورد تملك دارايي هاي سرمايه اي - عمومی']}
تملک دارایی سرمایه‌ای متفرقه: {row[' براورد تملك دارايي هاي سرمايه اي - متفرقه']}
جمع کل: {row['جمع كل']}
        """.strip(),
        'metadata': {
            'دستگاه_اجرایی': row['عنوان دستگاه اجرايي'],
            'دستگاه_اصلی': row['عنوان دستگاه اصلي'],
            'سال': str(row['سال']),
            'جمع_کل': str(row['جمع كل']),
            'type': 'masaref',
            'source': 'masaref2.xlsx'
        }
    }
    chunks.append(chunk)

# مشابه برای manabe
# ...
```

**Step 3: ساخت Collection جدید**
```python
from sentence_transformers import SentenceTransformer

# Load embedding model (dimension 384)
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

# Create collection
collection = client.create_collection(
    name="budget_financial",
    metadata={"description": "Budget and Financial Data"}
)

# Add documents
for chunk in chunks:
    embedding = model.encode(chunk['text'])
    collection.add(
        documents=[chunk['text']],
        metadatas=[chunk['metadata']],
        embeddings=[embedding.tolist()],
        ids=[f"doc_{idx}"]
    )
```

---

### گزینه 2: Database Route (بهتر برای queryهای محاسباتی) ✅

برای queryهای محاسباتی (جمع، مقایسه)، استفاده از database بهتر است:

**مزایا**:
- ✅ محاسبات دقیق
- ✅ جمع و تفریق آسان
- ✅ فیلتر پیشرفته (سال، دستگاه، نوع)
- ✅ سرعت بالا

**معماری پیشنهادی**:
```
User Query
    ↓
Intent Detection
    ↓
    ├─→ Computational Query → Database Route
    │   (جمع، مقایسه، محاسبه)
    │
    └─→ Descriptive Query → RAG Route
        (توضیح، تعریف، چرایی)
```

**مثال Database Route**:
```python
# Query: "بودجه نهاد ریاست جمهوری در سال 1403"

# SQL Generation
sql = """
SELECT 
    SUM(جمع_کل) as total_budget
FROM budget_financial
WHERE 
    دستگاه_اجرایی LIKE '%ریاست جمهوری%'
    AND سال = '1403'
"""

# Execute & Format
result = execute_sql(sql)
answer = f"بودجه نهاد ریاست جمهوری در سال 1403: {result['total_budget']} میلیون ریال"
```

---

### گزینه 3: Hybrid Approach (توصیه نهایی) ⭐

ترکیب Database + RAG:

**1. Database برای queryهای محاسباتی**:
- جمع، تفریق، مقایسه
- فیلتر دقیق (سال، دستگاه)
- محاسبات آماری

**2. RAG برای queryهای توضیحی**:
- "چرا بودجه افزایش یافت؟"
- "تفاوت اعتبارات عمومی و اختصاصی چیست؟"
- "روند بودجه در 3 سال اخیر"

**Decision Tree**:
```python
def route_query(query):
    # Detect intent
    if has_computational_intent(query):  # جمع، چقدر، مقایسه
        return "database"
    elif has_descriptive_intent(query):  # چرا، چگونه، تفاوت
        return "rag"
    else:
        return "hybrid"  # هر دو
```

---

## 📝 Script بازسازی

```python
#!/usr/bin/env python3
# rebuild_budget_financial.py

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

def rebuild_budget_financial():
    """بازسازی collection budget_financial"""
    
    # 1. Initialize
    client = chromadb.PersistentClient(path="chroma_db")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    
    # 2. Delete old collection
    try:
        client.delete_collection("budget_financial")
        print("✅ Old collection deleted")
    except:
        print("⚠️ No old collection to delete")
    
    # 3. Create new collection
    collection = client.create_collection(
        name="budget_financial",
        metadata={"description": "Budget and Financial Data - Rebuilt"}
    )
    
    # 4. Process masaref2.xlsx
    print("\n📊 Processing masaref2.xlsx...")
    df_masaref = pd.read_excel('archive/data_files/masaref2.xlsx')
    
    for idx, row in tqdm(df_masaref.iterrows(), total=len(df_masaref)):
        text = f"""
دستگاه اجرایی: {row['عنوان دستگاه اجرايي']}
دستگاه اصلی: {row['عنوان دستگاه اصلي']}
سال: {row['سال']}

اعتبارات هزینه‌ای:
- عمومی: {row['براورد اعتبارات هزینه ای - عمومی']} میلیون ریال
- متفرقه: {row['برآورد اعتبارات هزینه ای - متفرقه']} میلیون ریال
- اختصاصی: {row['براورد اعتبارات هزینه ای - اختصاصی']} میلیون ریال
- جمع: {row['جمع براورد اعتبارات هزینه ای']} میلیون ریال

تملک دارایی سرمایه‌ای:
- عمومی: {row[' براورد تملك دارايي هاي سرمايه اي - عمومی']} میلیون ریال
- متفرقه: {row[' براورد تملك دارايي هاي سرمايه اي - متفرقه']} میلیون ریال
- جمع: {row['جمع برآورد تملك دارايي هاي سرمايه اي']} میلیون ریال

جمع کل بودجه: {row['جمع كل']} میلیون ریال
        """.strip()
        
        metadata = {
            'دستگاه_اجرایی': str(row['عنوان دستگاه اجرايي']),
            'دستگاه_اصلی': str(row['عنوان دستگاه اصلي']),
            'سال': str(row['سال']),
            'جمع_کل': str(row['جمع كل']),
            'type': 'masaref',
            'source': 'masaref2.xlsx'
        }
        
        embedding = model.encode(text)
        
        collection.add(
            documents=[text],
            metadatas=[metadata],
            embeddings=[embedding.tolist()],
            ids=[f"masaref_{idx}"]
        )
    
    # 5. Process manabe.xlsx
    print("\n📊 Processing manabe.xlsx...")
    df_manabe = pd.read_excel('archive/data_files/manabe.xlsx')
    
    for idx, row in tqdm(df_manabe.iterrows(), total=len(df_manabe)):
        text = f"""
دستگاه اجرایی: {row['عنوان دستگاه اجرایی']}
دستگاه اصلی: {row['عنوان دستگاه اصلی']}
سال: {row['سال']}

قسمت: {row['عنوان قسمت']}
بخش: {row['عنوان بخش']}
بند: {row['عنوان بند']}
جزء: {row['عنوان جزء']}

درآمد عمومی:
- ملی: {row[' در آمد عمومي ملي']} میلیون ریال
- استانی: {row[' در آمد عمومي استاني']} میلیون ریال
- جمع: {row[' جمع در آمد عمومي']} میلیون ریال

درآمد اختصاصی:
- ملی: {row[' در آمد اختصاصي ملي']} میلیون ریال
- استانی: {row[' در آمد اختصاصي استاني']} میلیون ریال
- جمع: {row[' جمع در آمد اختصاصي']} میلیون ریال

جمع کل درآمد: {row['جمع کل']} میلیون ریال
        """.strip()
        
        metadata = {
            'دستگاه_اجرایی': str(row['عنوان دستگاه اجرایی']),
            'دستگاه_اصلی': str(row['عنوان دستگاه اصلی']),
            'سال': str(row['سال']),
            'جمع_کل': str(row['جمع کل']),
            'type': 'manabe',
            'source': 'manabe.xlsx'
        }
        
        embedding = model.encode(text)
        
        collection.add(
            documents=[text],
            metadatas=[metadata],
            embeddings=[embedding.tolist()],
            ids=[f"manabe_{idx}"]
        )
    
    print(f"\n✅ Collection rebuilt successfully!")
    print(f"   Total documents: {collection.count()}")

if __name__ == "__main__":
    rebuild_budget_financial()
```

---

## ✅ توصیه نهایی

**برای Production**:
1. ✅ بازسازی collection با embedding dimension 384
2. ✅ پیاده‌سازی Database Route برای queryهای محاسباتی
3. ✅ استفاده از Hybrid Approach (Database + RAG)
4. ✅ تست کامل با queryهای واقعی

**اولویت**:
1. بازسازی collection (فوری)
2. تست queryهای نمونه
3. پیاده‌سازی Database Route (مرحله بعد)

---

**وضعیت**: ❌ Collection فعلی قابل استفاده نیست  
**راه‌حل**: بازسازی با script بالا  
**زمان تخمینی**: 10-15 دقیقه

