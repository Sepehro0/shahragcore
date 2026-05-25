# گزارش جامع تست کالکشن budget_financial
**تاریخ تست:** 2025-12-21 11:56:13
**کالکشن:** budget_financial
**API Endpoint:** http://localhost:8010/v2/query/streaming
**تعداد کل تست‌ها:** 18

## 📊 آمار کلی

- ✅ **موفق:** 0 (0.0%)
- ❌ **ناموفق:** 18 (100.0%)

---

## 📋 تحلیل بر اساس دسته‌بندی

### مصارف

- کل تست‌ها: 12
- موفق: 0 (0.0%)
- ناموفق: 12 (100.0%)

### منابع

- کل تست‌ها: 6
- موفق: 0 (0.0%)
- ناموفق: 6 (100.0%)

---

## 🔍 تحلیل بر اساس نوع سوال

### single_cell

- کل تست‌ها: 10
- موفق: 0 (0.0%)
- ناموفق: 10 (100.0%)

### aggregation

- کل تست‌ها: 6
- موفق: 0 (0.0%)
- ناموفق: 6 (100.0%)

### comparison

- کل تست‌ها: 2
- موفق: 0 (0.0%)
- ناموفق: 2 (100.0%)

---

## 📝 جزئیات تست‌ها

### 1a_مصارف_سلول_خاص

#### 1a_1: اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102c910>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_2: اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d210>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_3: اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102da80>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_4: تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - با عنوان متفاوت از کاربر (معاونت علمي، فناوري و اقتصاد دانش بنيان رييس جمهور)

**⚠️ نکته:** عنوان از سمت کاربر متفاوت آمده - سیستم باید این را بفهمد

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e2f0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_5: تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - با عنوان کوتاه شده (عنوان دقیق: سازمان سنجش آموزش كشور موضوع بند"ج" تبصره 49 قانون بودجه سال 1364 كل كشور)

**⚠️ نکته:** عنوان کوتاه شده - سیستم باید عنوان کامل را پیدا کند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102dde0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_6: تملک دارایی عمومی دانشگاه تهران در سال 1403

**توضیحات:** ارجاع یک سلول خاص - مصارف - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d570>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_7: تملک دارایی اختصاصی ستاد کل نیروهای مسلح در سال 1400

**توضیحات:** ارجاع یک سلول خاص - مصارف - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cb80>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1a_8: تملک دارایی اختصاصی کد دستگاه اجرایی 111400 در سال 1400

**توضیحات:** ارجاع یک سلول خاص - مصارف - با کد دستگاه اجرایی

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102eb60>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1b_منابع_سلول_خاص

#### 1b_1: درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟

**توضیحات:** ارجاع یک سلول خاص - منابع - ستون + سطر + سال

**⚠️ نکته:** پست بانک خالی هم می‌تواند باشد

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102f3d0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 1b_2: درآمد استانی عمومی سازمان پزشکی قانونی کشور در سال 1402 چقدر است؟

**توضیحات:** ارجاع یک سلول خاص - منابع - ستون + سطر + سال

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f0febeb0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2a_جمع_مصارف

#### 2a_1: بودجه فرهنگستان هنر در سال 1403

**توضیحات:** جمع چند سلول - مصارف - باید تمام ردیف‌های مربوط به فرهنگستان هنر را جمع کند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102f0d0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 2a_2: اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403

**توضیحات:** جمع چند سلول - مصارف - باید هم به عنوان نهاد دستگاه اصلی و هم به عنوان نهاد دستگاه اجرایی سرچ کند و هر دو را در جواب بیاورد

**⚠️ نکته:** باید هم نهاد دستگاه اصلی و هم نهاد دستگاه اجرایی را پیدا کند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cbb0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 2a_3: درآمدهای وزارت نفت در سال 1401 چقدر است

**توضیحات:** جمع چند سلول - منابع - باید تمام درآمدهای مربوط به وزارت نفت را جمع کند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d4b0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2b_جمع_منابع_چند_جز

#### 2b_1: درامد استانی اختصاصی دانشگاه تبریز در سال 1403

**توضیحات:** جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102dd20>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 2b_2: درامد ملی سازمان تامین اجتماعی در سال 1403

**توضیحات:** جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e950>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 2b_3: درامد کل موسسه کار و تامین اجتماعی در سال 1402

**توضیحات:** جمع چند سلول - منابع - برای دستگاه‌هایی که از طریق بیش از یک جز کسب درآمد کرده‌اند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e050>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2c_مقایسه

#### 2c_1: هزینه عمومی نهاد ریاست جمهوری در سال 1403 بیشتر بوده یا شورای عالی امنیت ملی

**توضیحات:** مقایسه چند سلول خاص با هم - مصارف

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d7e0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

#### 2c_2: هزینه عمومی کدام یک از مجموعه های نهاد ریاست جمهوری در سال 1403 از بقیه بیشتر است؟

**توضیحات:** مقایسه چند سلول خاص با هم - مصارف - باید تمام مجموعه‌های نهاد ریاست جمهوری را پیدا کند و مقایسه کند

**وضعیت:** ❌ ناموفق

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cf70>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

## ⚠️ تحلیل مشکلات

### 1a_1

**سوال:** اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102c910>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_2

**سوال:** اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d210>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_3

**سوال:** اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102da80>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_4

**سوال:** تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e2f0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_5

**سوال:** تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102dde0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_6

**سوال:** تملک دارایی عمومی دانشگاه تهران در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d570>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_7

**سوال:** تملک دارایی اختصاصی ستاد کل نیروهای مسلح در سال 1400

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cb80>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1a_8

**سوال:** تملک دارایی اختصاصی کد دستگاه اجرایی 111400 در سال 1400

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102eb60>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1b_1

**سوال:** درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102f3d0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 1b_2

**سوال:** درآمد استانی عمومی سازمان پزشکی قانونی کشور در سال 1402 چقدر است؟

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f0febeb0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2a_1

**سوال:** بودجه فرهنگستان هنر در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102f0d0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2a_2

**سوال:** اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cbb0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2a_3

**سوال:** درآمدهای وزارت نفت در سال 1401 چقدر است

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d4b0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2b_1

**سوال:** درامد استانی اختصاصی دانشگاه تبریز در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102dd20>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2b_2

**سوال:** درامد ملی سازمان تامین اجتماعی در سال 1403

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e950>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2b_3

**سوال:** درامد کل موسسه کار و تامین اجتماعی در سال 1402

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102e050>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2c_1

**سوال:** هزینه عمومی نهاد ریاست جمهوری در سال 1403 بیشتر بوده یا شورای عالی امنیت ملی

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102d7e0>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

### 2c_2

**سوال:** هزینه عمومی کدام یک از مجموعه های نهاد ریاست جمهوری در سال 1403 از بقیه بیشتر است؟

**خطا:** HTTPConnectionPool(host='localhost', port=8010): Max retries exceeded with url: /v2/query/streaming (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f34f102cf70>: Failed to establish a new connection: [Errno 111] Connection refused'))

---

## 💡 توصیه‌ها و نکات

- ⚠️ نرخ موفقیت کمتر از 80% است. نیاز به بررسی و بهبود دارد.

