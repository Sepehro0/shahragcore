# خلاصه تغییرات Routing

## تغییرات انجام شده:

### 1. بهبود QueryRouter (`services/query_router.py`):
- اضافه کردن الگوهای مالی: `تملک`, `دارایی`, `اعتبارات`, `هزینه`, `مصارف`, `درآمد`, `بودجه`, `سرمایه‌ای`
- اضافه کردن الگوهای سال: `در\s*سال`, `سال\s*های`, `سال\s*\d{2,4}`
- تقویت confidence برای queries مالی: اگر query مالی + (سال یا دستگاه) باشد → confidence = 0.9-0.95

### 2. بهبود `_try_database_before_rag` (`ultimate_rag_system.py`):
- بررسی مستقیم برای queries مالی قبل از QueryRouter
- اگر query مالی است، مستقیماً Text-to-SQL را فراخوانی می‌کند (بدون QueryRouter)
- بررسی valid values و return کردن نتیجه

### 3. بهبود منطق در `retrieve_and_answer_stream` و `retrieve_and_answer`:
- بررسی اینکه آیا query مالی است (مستقل از domain collection)
- اگر query مالی است یا `should_check_financial_patterns = True`، `_try_database_before_rag` فراخوانی می‌شود

## مشکل باقی‌مانده:

هنوز queries به RAG route می‌روند. نیاز به بررسی بیشتر.

## پیشنهادات بعدی:

1. بررسی logs برای فهم دقیق‌تر مشکل
2. بررسی اینکه آیا database query درست اجرا می‌شود
3. بررسی اینکه آیا database results null هستند

