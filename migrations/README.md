# Database Migrations

این دایرکتوری شامل migration scripts برای تغییرات schema دیتابیس است.

## Migration Scripts

### `add_optimization_indexes.py`
اضافه کردن index‌های بهینه‌سازی برای بهبود performance:

- `idx_table_source_file`: Index روی `data_tables.source_file`
- `idx_row_created_at`: Index روی `table_rows.created_at`
- `idx_table_rows_data_gin`: GIN index روی `table_rows.data` (PostgreSQL only)
- `idx_query_cache_collection`: Index روی `query_cache.collection_id`
- `idx_query_cache_expires`: Index روی `query_cache.expires_at`
- `idx_query_cache_hash`: Index روی `query_cache.result_hash`

## اجرای Migration

```bash
# اجرای migration
python migrations/add_optimization_indexes.py
```

## نکات مهم

1. **Backup**: قبل از اجرای migration حتماً backup بگیرید
2. **PostgreSQL vs SQLite**: برخی index‌ها (مثل GIN) فقط برای PostgreSQL هستند
3. **Downtime**: ایجاد index‌ها ممکن است زمان‌بر باشد برای جداول بزرگ

## Rollback

برای rollback کردن migration، index‌ها را به صورت دستی حذف کنید:

```sql
-- PostgreSQL
DROP INDEX IF EXISTS idx_table_source_file;
DROP INDEX IF EXISTS idx_row_created_at;
DROP INDEX IF EXISTS idx_table_rows_data_gin;
DROP INDEX IF EXISTS idx_query_cache_collection;
DROP INDEX IF EXISTS idx_query_cache_expires;
DROP INDEX IF EXISTS idx_query_cache_hash;

-- SQLite
DROP INDEX IF EXISTS idx_table_source_file;
DROP INDEX IF EXISTS idx_row_created_at;
DROP INDEX IF EXISTS idx_query_cache_collection;
DROP INDEX IF EXISTS idx_query_cache_expires;
DROP INDEX IF EXISTS idx_query_cache_hash;
```

