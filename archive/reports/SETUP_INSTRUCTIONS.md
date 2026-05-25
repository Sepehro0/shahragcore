# دستورالعمل راه‌اندازی کامل سیستم RAG + Database

## مراحل راه‌اندازی

### مرحله 1: نصب PostgreSQL

اجرای اسکریپت setup:

```bash
cd /home/user01/qwen-api/enhanced_rag_system
bash scripts/setup_postgresql.sh
```

یا به صورت دستی:

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# ایجاد database و user
sudo -u postgres psql <<EOF
CREATE USER rag_user WITH PASSWORD 'rag_password';
CREATE DATABASE rag_database OWNER rag_user;
GRANT ALL PRIVILEGES ON DATABASE rag_database TO rag_user;
\c rag_database
GRANT ALL ON SCHEMA public TO rag_user;
\q
EOF
```

### مرحله 2: راه‌اندازی Qwen3-30B

```bash
bash start_qwen3_30b_sglang.sh
```

> با این فرمان سرویس SGLang روی پورت 8009 بالا می‌آید و مدل Qwen3-30B ارائه می‌شود.

یا به صورت background:

```bash
cd /home/user01/qwen-api/enhanced_rag_system
nohup bash start_qwen3_30b_sglang.sh > logs/qwen3_30b_startup.log 2>&1 &
```

بررسی وضعیت:

```bash
curl http://localhost:8080/health
```

### مرحله 3: راه‌اندازی Database Schema

```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 scripts/init_database.py
```

### مرحله 4: تست سیستم

```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 test_database_integration.py
```

## تنظیمات Environment Variables

اگر می‌خواهید از تنظیمات پیش‌فرض استفاده نکنید:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=rag_user
export POSTGRES_PASSWORD=rag_password
export POSTGRES_DB=rag_database
export QWEN_URL=http://localhost:8080
```

## Troubleshooting

### PostgreSQL connection failed
```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

### Qwen service not responding
```bash
curl http://localhost:8080/v1/models
ps aux | grep vllm
```

### Database tables not created
```bash
cd /home/user01/qwen-api/enhanced_rag_system
PYTHONPATH=. python3 scripts/init_database.py
```

