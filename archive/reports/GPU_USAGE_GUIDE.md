# راهنمای استفاده از GPU برای محیط توسعه

## وضعیت فعلی

### Production (Port 8000)
- **Device**: CPU (CUDA_VISIBLE_DEVICES="")
- **Status**: در حال اجرا
- **GPU Usage**: استفاده نمی‌کند

### Development (Port 8001)
- **Device**: CPU (مثل production)
- **Status**: آماده برای راه‌اندازی
- **GPU Usage**: استفاده نمی‌کند

## وضعیت GPU های موجود

بر اساس بررسی سیستم:
- **GPU 0**: خالی (3 MiB استفاده)
- **GPU 1**: در حال استفاده (43476 MiB)
- **GPU 2**: خالی (3 MiB استفاده)
- **GPU 3**: در حال استفاده (44194 MiB)
- **GPU 4**: در حال استفاده (44194 MiB)
- **GPU 5**: در حال استفاده (43476 MiB)
- **GPU 6**: خالی (3 MiB استفاده)
- **GPU 7**: خالی (3 MiB استفاده)

## گزینه‌های استفاده از GPU برای Dev

### گزینه 1: استفاده از GPU های خالی (توصیه می‌شود)

اگر می‌خواهید از GPU برای سرعت بیشتر استفاده کنید، می‌توانید از GPU های 0، 2، 6 یا 7 استفاده کنید:

```bash
# استفاده از GPU 0
export CUDA_VISIBLE_DEVICES="0"
cd /home/user01/qwen-api/enhanced_rag_system_dev
python3 api_server.py

# یا استفاده از GPU 2
export CUDA_VISIBLE_DEVICES="2"
cd /home/user01/qwen-api/enhanced_rag_system_dev
python3 api_server.py

# یا استفاده از چند GPU خالی
export CUDA_VISIBLE_DEVICES="0,2,6,7"
cd /home/user01/qwen-api/enhanced_rag_system_dev
python3 api_server.py
```

### گزینه 2: استفاده از CPU (فعلی)

برای جلوگیری از هرگونه تداخل با production، از CPU استفاده کنید:

```bash
export CUDA_VISIBLE_DEVICES=""
cd /home/user01/qwen-api/enhanced_rag_system_dev
./start_api_dev.sh
```

## تغییر تنظیمات Device در کد

اگر می‌خواهید از GPU استفاده کنید، باید تنظیمات زیر را تغییر دهید:

### 1. Embedding Service
فایل: `services/persian_embedding_service.py`
```python
# تغییر از:
_CACHED_MODEL = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

# به:
_CACHED_MODEL = SentenceTransformer(EMBEDDING_MODEL, device="cuda")
```

### 2. Cross Encoder Reranker
فایل: `services/cross_encoder_reranker.py`
```python
# این فایل به صورت خودکار از CUDA استفاده می‌کند اگر در دسترس باشد
self.device = "cuda" if torch.cuda.is_available() else "cpu"
```

### 3. Query Understanding
فایل: `search/query_understanding.py`
```python
# این فایل به صورت خودکار از CUDA استفاده می‌کند اگر در دسترس باشد
self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

## نکات مهم

1. **تضمین عدم تداخل**: استفاده از GPU های خالی (0، 2، 6، 7) تضمین می‌کند که با production تداخلی ندارید
2. **سرعت**: استفاده از GPU می‌تواند سرعت پردازش را به طور قابل توجهی افزایش دهد
3. **مصرف حافظه**: GPU های خالی حدود 49GB حافظه دارند که برای dev کافی است
4. **Production Safety**: Production از CPU استفاده می‌کند، بنابراین هیچ تداخلی وجود ندارد

## اسکریپت راه‌اندازی با GPU

می‌توانید یک اسکریپت جدید برای استفاده از GPU ایجاد کنید:

```bash
# ایجاد فایل start_api_dev_gpu.sh
cat > start_api_dev_gpu.sh << 'EOF'
#!/bin/bash
export CUDA_VISIBLE_DEVICES="0"  # یا "2" یا "6" یا "7"
export PYTHONPATH="/home/user01/qwen-api/enhanced_rag_system_dev:$PYTHONPATH"
cd /home/user01/qwen-api/enhanced_rag_system_dev
python3 api_server.py
EOF

chmod +x start_api_dev_gpu.sh
```

## بررسی استفاده از GPU

برای بررسی استفاده از GPU:

```bash
# مشاهده وضعیت GPU ها
nvidia-smi

# مشاهده استفاده از حافظه
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
```

## نتیجه‌گیری

- **فعلی**: Dev از CPU استفاده می‌کند (مثل production) - **امن و بدون تداخل**
- **گزینه بهتر**: استفاده از GPU های خالی (0، 2، 6، 7) برای سرعت بیشتر - **هنوز امن و بدون تداخل**

هر دو گزینه با production تداخلی ندارند چون production از CPU استفاده می‌کند.

