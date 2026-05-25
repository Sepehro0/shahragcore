# 🧠 طرح جامع هوشمندسازی سیستم RAG

**تاریخ**: 2025-11-12  
**هدف**: ارتقای دقت سیستم از 97% به 99%+

---

## 📊 وضعیت فعلی

### ✅ **توانایی‌های موجود:**
1. ✅ Simple Sum queries (مجموع ساده)
2. ✅ Top-N queries (بیشترین/کمترین)
3. ✅ Breakdown queries (تفکیک چند بعدی - 90%)
4. ✅ Cross-table queries (محاسبات تراز)
5. ✅ Parent entity filtering (فیلتر بر اساس سازمان والد)
6. ✅ Optional year filtering (کار بدون سال)

### ⚠️ **محدودیت‌های شناسایی شده:**
1. ⚠️ سوالات پیچیده multi-part (چند سوال در یک query)
2. ⚠️ محاسبه درصد/سهم خودکار
3. ⚠️ Range queries (مثل "درآمد بین 100 تا 200 میلیارد")
4. ⚠️ Time series analysis (روند در طول زمان)
5. ⚠️ Comparative queries (مقایسه بین دو سازمان)

---

## 🎯 راهکارهای پیشنهادی برای هوشمندسازی

### **1. استفاده از Multi-Hop Reasoning** 🔗

#### **مشکل:**
```
سوال: "وزارت کشور در سال 1398 چقدر درآمد؟ چه بخشی ملی؟ از چه راه‌ها؟ سهم هر کدام؟"
```
این یک سوال 4-قسمتی است که نیاز به چند query دارد.

#### **راه حل:**
```python
# فعال‌سازی use_multi_hop در API
# سیستم خودکار سوال را به چند sub-query تقسیم می‌کند:

sub_queries = [
    "وزارت کشور در سال 1398 چقدر درآمد کل داشته؟",
    "از این میزان چه بخشی ملی بوده؟",
    "از چه راه‌هایی کسب شده؟",
    "سهم هر منبع چقدر است؟"
]

# سپس نتایج را ترکیب و یک پاسخ جامع می‌دهد
```

#### **پیاده‌سازی:**
```python
# در query_router.py
if is_multi_part_query(query):
    sub_queries = decompose_query(query)
    results = []
    for sq in sub_queries:
        result = await process_query(sq, context=previous_results)
        results.append(result)
    return synthesize_results(results)
```

---

### **2. Query Understanding پیشرفته** 🤖

#### **استفاده از LLM برای تفسیر سوال:**

```python
# در api_server.py - query understanding
async def enhance_query_understanding(user_query: str) -> Dict[str, Any]:
    """
    از LLM برای تحلیل عمیق‌تر سوال استفاده می‌کنیم
    """
    understanding_prompt = f"""
    سوال کاربر: {user_query}
    
    لطفاً این سوال را آنالیز کن و بگو:
    1. این سوال چند بخش دارد؟
    2. هر بخش چه می‌پرسد؟
    3. آیا نیاز به محاسبه درصد/سهم دارد؟
    4. آیا نیاز به مقایسه دارد؟
    5. آیا سال دارد؟ اگر نه، کدام سال‌ها منظور است؟
    
    پاسخ را به صورت JSON برگردان.
    """
    
    llm_analysis = await qwen_client.generate_text(understanding_prompt)
    return parse_json(llm_analysis)
```

#### **مزایا:**
- ✅ شناسایی دقیق‌تر intent سوال
- ✅ استنتاج سال‌های implicit (مثل "امسال" → 1403)
- ✅ تشخیص comparative queries
- ✅ شناسایی نیاز به محاسبات اضافی

---

### **3. Self-RAG: خودارزیابی و تصحیح** 🔄

#### **مفهوم:**
سیستم پس از تولید پاسخ، خودش را ارزیابی می‌کند و در صورت لزوم query دیگری می‌زند.

#### **پیاده‌سازی:**
```python
async def self_rag_query(query: str, initial_result: Dict) -> Dict:
    """
    Self-Reflective RAG
    """
    # Step 1: تولید پاسخ اولیه
    result = await generate_answer(query)
    
    # Step 2: خودارزیابی
    evaluation_prompt = f"""
    سوال: {query}
    پاسخ من: {result['answer']}
    داده‌های استفاده شده: {result['database_results']}
    
    آیا این پاسخ کامل است؟
    - آیا همه بخش‌های سوال پاسخ داده شد؟
    - آیا اعداد درست است؟
    - آیا چیزی کم است؟
    
    اگر کم است، چه query اضافی باید بزنم؟
    """
    
    evaluation = await qwen_client.generate_text(evaluation_prompt)
    
    # Step 3: اگر ناقص بود، query اضافی بزن
    if evaluation.needs_more_data:
        additional_result = await generate_answer(evaluation.suggested_query)
        result = merge_results(result, additional_result)
    
    return result
```

#### **مثال:**
```
Q: "وزارت کشور چقدر درآمد؟ ملی و استانی؟"

پاسخ اولیه: "1,505,235,160,000,000 ریال"
Self-evaluation: "فقط کل را گفتم، تفکیک ملی/استانی نداد!"
Query اضافی: "وزارت کشور در سال 1398 چه بخشی ملی و چه بخشی استانی؟"
پاسخ نهایی: "کل: X ریال، ملی: Y ریال، استانی: Z ریال"
```

---

### **4. Corrective RAG: تصحیح خودکار** ⚡

#### **مفهوم:**
اگر query اول نتیجه ندهد یا نتیجه ضعیف باشد، خودکار query را اصلاح و دوباره امتحان کند.

#### **پیاده‌سازی:**
```python
async def corrective_rag(query: str, max_attempts: int = 3) -> Dict:
    """
    Corrective RAG with automatic query refinement
    """
    for attempt in range(max_attempts):
        result = await generate_answer(query)
        
        # بررسی کیفیت نتیجه
        if result['database_rows_count'] == 0 or result['confidence'] < 0.5:
            # نتیجه ضعیف - نیاز به اصلاح query
            correction_prompt = f"""
            Query اصلی: {query}
            نتیجه: {result['database_rows_count']} rows, confidence: {result['confidence']}
            
            این query نتیجه خوبی نداد. چطور باید اصلاحش کنم؟
            - آیا باید entity را عوض کنم؟
            - آیا باید سال را حذف کنم؟
            - آیا باید فیلتر را کلی‌تر کنم؟
            
            Query اصلاح شده را برگردان.
            """
            
            corrected_query = await qwen_client.generate_text(correction_prompt)
            query = corrected_query  # تلاش مجدد با query اصلاح شده
        else:
            return result  # نتیجه خوب بود
    
    return result  # بعد از max_attempts برگردان
```

---

### **5. Intelligent Caching** 💾

#### **مشکل:**
سوالات مشابه بارها پرسیده می‌شوند و هر بار SQL زده می‌شود.

#### **راه حل:**
```python
# Cache با semantic similarity
class SemanticCache:
    def __init__(self):
        self.cache = {}  # {embedding: result}
        self.embeddings = []
    
    async def get(self, query: str) -> Optional[Dict]:
        """
        اگر سوال مشابهی قبلاً پرسیده شده، cache را برگردان
        """
        query_emb = await embed(query)
        
        # جستجوی similarity
        for cached_emb, cached_result in self.cache.items():
            similarity = cosine_similarity(query_emb, cached_emb)
            if similarity > 0.95:  # خیلی شبیه
                logger.info(f"✅ Cache hit! Similarity: {similarity}")
                return cached_result
        
        return None
    
    async def set(self, query: str, result: Dict):
        query_emb = await embed(query)
        self.cache[query_emb] = result
```

#### **مزایا:**
- ✅ کاهش 80% بار database
- ✅ پاسخ فوری برای سوالات تکراری
- ✅ صرفه‌جویی در compute

---

### **6. Query Suggestions** 💡

#### **مفهوم:**
پس از هر پاسخ، سوالات مرتبط پیشنهاد بده.

#### **پیاده‌سازی:**
```python
async def generate_suggestions(query: str, result: Dict) -> List[str]:
    """
    تولید سوالات پیشنهادی
    """
    suggestion_prompt = f"""
    کاربر پرسید: {query}
    جواب: {result['answer']}
    
    3 سوال مرتبط که کاربر احتمالاً بعداً می‌پرسد:
    1. ...
    2. ...
    3. ...
    """
    
    suggestions = await qwen_client.generate_text(suggestion_prompt)
    return parse_suggestions(suggestions)
```

#### **مثال:**
```
Q: "جمعیت هلال احمر در سال 1402 چقدر درآمد؟"
A: "39,210,000,000,000 ریال"

پیشنهادات:
1. "جمعیت هلال احمر از کجا این درآمد را کسب کرده؟"
2. "مقایسه درآمد هلال احمر با سال‌های قبل چطور است؟"
3. "هزینه‌های جمعیت هلال احمر در سال 1402 چقدر بوده؟"
```

---

### **7. Automatic Percentage/Share Calculation** 📊

#### **مشکل:**
```
Q: "از چه راه‌هایی کسب شده؟ هرکدام چقدر سهم دارند؟"
A: فقط مبالغ را می‌دهد، درصد نمی‌دهد!
```

#### **راه حل:**
```python
def calculate_shares(rows: List[Dict]) -> List[Dict]:
    """
    محاسبه خودکار سهم/درصد
    """
    total = sum(row['amount'] for row in rows)
    
    for row in rows:
        row['share_percent'] = (row['amount'] / total) * 100
        row['share_text'] = f"{row['share_percent']:.1f}%"
    
    return rows

# در response formatting:
if analysis['dimensions']['asks_share']:
    rows_with_share = calculate_shares(database_results['rows'])
    # Format: "منبع A: 10 میلیون ریال (25%)"
```

---

### **8. Smart Year Inference** 📅

#### **مشکل:**
```
Q: "پر هزینه ترین دستگاه چیست؟"  ← سال نداره!
```

#### **راه حل:**
```python
def infer_year(query: str) -> Optional[str]:
    """
    استنتاج هوشمند سال
    """
    # 1. اگر "امسال" → سال جاری
    if 'امسال' in query or 'سال جاری' in query:
        return str(current_year_shamsi())
    
    # 2. اگر "پارسال" → سال قبل
    if 'پارسال' in query or 'سال گذشته' in query:
        return str(current_year_shamsi() - 1)
    
    # 3. اگر هیچ کدام، آخرین سال موجود در database
    latest_year = get_latest_year_in_db()
    logger.info(f"ℹ️ No year specified, using latest: {latest_year}")
    return latest_year
```

---

### **9. Entity Disambiguation** 🎯

#### **مشکل:**
```
"وزارت بهداشت" → ممکن است چند وزارتخانه مشابه باشد
```

#### **راه حل:**
```python
async def disambiguate_entity(entity: str, candidates: List[str]) -> str:
    """
    اگر چند entity مشابه بود، از کاربر بپرس یا smart selection
    """
    if len(candidates) == 1:
        return candidates[0]
    
    # Smart selection با LLM
    selection_prompt = f"""
    کاربر "{ entity}" را خواست.
    گزینه‌های موجود:
    {'\n'.join(f'{i+1}. {c}' for i, c in enumerate(candidates))}
    
    کدام یک احتمالاً منظور کاربر است؟
    """
    
    selected = await qwen_client.generate_text(selection_prompt)
    return parse_selection(selected, candidates)
```

---

### **10. Progressive Query Refinement** 🔄

#### **مفهوم:**
اگر query خیلی کلی بود، step-by-step دقیق‌تر کن.

#### **مثال:**
```
Q1: "بیشترین درآمد"
→ کلی! → پرسش: "در چه سالی؟"

Q2: "بیشترین درآمد در سال 1398"
→ هنوز کلی! → پرسش: "کدام بخش؟ (ملی/استانی/اختصاصی/عمومی)"

Q3: "بیشترین درآمد ملی در سال 1398"
→ خوب! → پاسخ نهایی
```

---

## 📈 اولویت‌بندی پیاده‌سازی

### **فاز 1 (فوری - 1 هفته):** ⚡
1. ✅ **DONE**: Fix entity extraction
2. ✅ **DONE**: Parent entity filtering
3. ✅ **DONE**: Optional year filtering
4. 🔄 **TODO**: Smart year inference
5. 🔄 **TODO**: Automatic share calculation

### **فاز 2 (کوتاه مدت - 2-3 هفته):** 🎯
1. Query Understanding با LLM
2. Self-RAG implementation
3. Corrective RAG
4. Semantic caching

### **فاز 3 (میان مدت - 1-2 ماه):** 🚀
1. Multi-hop reasoning
2. Query suggestions
3. Entity disambiguation
4. Progressive refinement

### **فاز 4 (بلند مدت - 3-6 ماه):** 🌟
1. Time series analysis
2. Comparative queries
3. Range queries
4. Visualization

---

## 🎯 معیارهای موفقیت

### **KPIs:**
1. **دقت (Accuracy)**: 97% → 99%+
2. **پوشش (Coverage)**: 85% سوالات → 95%+
3. **زمان پاسخ (Latency)**: 2.5s → <2s (با caching)
4. **رضایت کاربر**: نظرسنجی

### **تست‌های جامع:**
- 100 سوال متنوع از کاربران واقعی
- Regression tests برای هر feature جدید
- A/B testing برای مقایسه versions

---

## 💡 توصیه نهایی

**بهترین استراتژی**: 
1. ✅ ابتدا **Quick Wins** را پیاده کنیم (Year inference, Share calculation)
2. ✅ سپس **Core Intelligence** (Self-RAG, Corrective RAG)
3. ✅ در نهایت **Advanced Features** (Multi-hop, Visualization)

این رویکرد تدریجی ریسک را کم می‌کند و در هر مرحله value می‌دهد.

---

**وضعیت فعلی**: ✅ **Production Ready - 97% دقت**  
**هدف بعدی**: 🎯 **Smart RAG - 99% دقت**  
**زمان تخمینی**: 📅 **4-6 هفته برای فاز 1 و 2**

