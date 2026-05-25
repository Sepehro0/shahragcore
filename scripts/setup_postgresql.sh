#!/bin/bash
# -*- coding: utf-8 -*-
# Setup PostgreSQL for RAG System
# این اسکریپت PostgreSQL را نصب و پیکربندی می‌کند

set -e

echo "🗄️  نصب و راه‌اندازی PostgreSQL برای RAG System"
echo "================================================"

# Step 1: نصب PostgreSQL
echo ""
echo "📦 Step 1: نصب PostgreSQL..."
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib

# Step 2: راه‌اندازی سرویس
echo ""
echo "🚀 Step 2: راه‌اندازی PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Step 3: ایجاد Database و User
echo ""
echo "📝 Step 3: ایجاد Database و User..."
sudo -u postgres psql <<EOF
-- Drop if exists
DROP DATABASE IF EXISTS rag_database;
DROP USER IF EXISTS rag_user;

-- Create user
CREATE USER rag_user WITH PASSWORD 'rag_password';

-- Create database
CREATE DATABASE rag_database OWNER rag_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE rag_database TO rag_user;

-- Connect to database and grant schema privileges
\c rag_database
GRANT ALL ON SCHEMA public TO rag_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO rag_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO rag_user;

\q
EOF

# Step 4: تنظیم pg_hba.conf برای اتصال محلی
echo ""
echo "🔧 Step 4: تنظیم pg_hba.conf..."
sudo sed -i '/^local.*all.*postgres.*peer/i local   all             all                                     md5' /etc/postgresql/*/main/pg_hba.conf
sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' /etc/postgresql/*/main/pg_hba.conf

# Step 5: Restart PostgreSQL
echo ""
echo "🔄 Step 5: راه‌اندازی مجدد PostgreSQL..."
sudo systemctl restart postgresql

# Step 6: تست اتصال
echo ""
echo "🧪 Step 6: تست اتصال..."
PGPASSWORD=rag_password psql -h localhost -U rag_user -d rag_database -c "SELECT version();" || {
    echo "⚠️  اتصال با password failed، تست با sudo..."
    sudo -u postgres psql -d rag_database -c "SELECT version();"
}

echo ""
echo "✅ PostgreSQL setup completed successfully!"
echo ""
echo "📋 اطلاعات اتصال:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: rag_database"
echo "   User: rag_user"
echo "   Password: rag_password"

