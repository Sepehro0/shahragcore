# تغییرات collection zinaf_dakheli

## 🎯 مشکل
سوالات زیر در `zinaf_dakheli` reject می‌شدند:
- من معاون یکی از هولدینگام دوره خاصی برای من وجود داره؟
- من به چه ادرسی باید ایمیل بزنم؟
- یوزرنیم پسورد سامانمو یادم نمیاد چیکار کنم
- ادرس ایمیل اموزش های ضمن خدمت
- من یه پیشنهادی دارم برای بهتر شدن دوره ها چجوری باید اعلام کنم؟

## 🔍 علت
1. **Thresholds خیلی بالا**: IntentGate (0.25), RelevanceGate (0.28)
2. **Pre-Generation Guard**: فقط برای `karbaran_omomi` fallback logic داشت
3. **Keyword Coverage**: threshold خیلی بالا برای سوالات متنوع

## ✅ راه‌حل

### 1. کاهش Thresholds
```python
# IntentGate
"zinaf_dakheli": 0.20  # کاهش از 0.25 به 0.20

# RelevanceGate  
"zinaf_dakheli": 0.23  # کاهش از 0.28 به 0.23
```

### 2. بهبود Pre-Generation Guard
```python
# اضافه کردن zinaf_dakheli به fallback logic
if collection_name == "zinaf_dakheli":
    threshold = 0.10  # keyword coverage پایین
    good_semantic_alignment = semantic_alignment_score >= 0.20
    high_quality_score = quality_score >= 0.50
```

### 3. Dynamic Fallback برای zinaf_dakheli
```python
only_keyword_failed = (
    len(failed_gates) == 1 and 
    'keyword_coverage' in failed_gates and
    collection_name in ["karbaran_omomi", "zinaf_dakheli"]  # اضافه شد
)
```

## 📊 نتایج تست

**قبل از بهبود**: 0/5 passed (0%)
**بعد از بهبود**: 5/5 passed (100%) ✅

### ✅ سوالات موفق:
1. ✅ من معاون یکی از هولدینگام دوره خاصی برای من وجود داره؟
2. ✅ من به چه ادرسی باید ایمیل بزنم؟
3. ✅ یوزرنیم پسورد سامانمو یادم نمیاد چیکار کنم
4. ✅ ادرس ایمیل اموزش های ضمن خدمت
5. ✅ من یه پیشنهادی دارم برای بهتر شدن دوره ها چجوری باید اعلام کنم؟

## 🎉 خلاصه

سیستم حالا برای **دو collection عمومی/متنوع** بهینه شده:
- `karbaran_omomi`: سوالات عمومی درباره صندوق‌ها
- `zinaf_dakheli`: سوالات متنوع درباره آموزش‌ها

هر دو collection threshold های پایین‌تر و fallback logic مشترک دارند که امکان پاسخگویی به سوالات متنوع را فراهم می‌کند.



