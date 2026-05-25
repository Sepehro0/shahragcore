# -*- coding: utf-8 -*-
"""
Migration Script: Add Optimization Indexes
اضافه کردن index‌های بهینه‌سازی برای بهبود performance
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config.settings import Settings

logger = None
try:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
except:
    pass

def log_info(msg):
    if logger:
        logger.info(msg)
    else:
        print(f"INFO: {msg}")

def log_error(msg):
    if logger:
        logger.error(msg)
    else:
        print(f"ERROR: {msg}")

def log_warning(msg):
    if logger:
        logger.warning(msg)
    else:
        print(f"WARNING: {msg}")

def check_postgresql(engine):
    """بررسی اینکه آیا از PostgreSQL استفاده می‌شود"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            if "PostgreSQL" in version:
                return True
    except:
        pass
    return False

def add_indexes(engine):
    """اضافه کردن index‌های بهینه‌سازی"""
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                is_postgresql = check_postgresql(engine)
                
                # Index برای data_tables.source_file
                log_info("Adding index on data_tables.source_file...")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_table_source_file 
                        ON data_tables(source_file)
                    """))
                    log_info("✅ Index idx_table_source_file created")
                except Exception as e:
                    log_warning(f"⚠️ Could not create idx_table_source_file: {e}")
                
                # Index برای table_rows.created_at
                log_info("Adding index on table_rows.created_at...")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_row_created_at 
                        ON table_rows(created_at)
                    """))
                    log_info("✅ Index idx_row_created_at created")
                except Exception as e:
                    log_warning(f"⚠️ Could not create idx_row_created_at: {e}")
                
                # GIN Index برای JSONB data field (PostgreSQL only)
                if is_postgresql:
                    log_info("Adding GIN index on table_rows.data (PostgreSQL only)...")
                    try:
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_table_rows_data_gin 
                            ON table_rows USING GIN (data)
                        """))
                        log_info("✅ GIN index idx_table_rows_data_gin created")
                    except Exception as e:
                        log_warning(f"⚠️ Could not create GIN index: {e}")
                else:
                    log_info("⏭️ Skipping GIN index (not PostgreSQL)")
                
                # Indexes برای query_cache
                log_info("Adding indexes on query_cache...")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_query_cache_collection 
                        ON query_cache(collection_id)
                    """))
                    log_info("✅ Index idx_query_cache_collection created")
                except Exception as e:
                    log_warning(f"⚠️ Could not create idx_query_cache_collection: {e}")
                
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_query_cache_expires 
                        ON query_cache(expires_at)
                    """))
                    log_info("✅ Index idx_query_cache_expires created")
                except Exception as e:
                    log_warning(f"⚠️ Could not create idx_query_cache_expires: {e}")
                
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_query_cache_hash 
                        ON query_cache(result_hash)
                    """))
                    log_info("✅ Index idx_query_cache_hash created")
                except Exception as e:
                    log_warning(f"⚠️ Could not create idx_query_cache_hash: {e}")
                
                trans.commit()
                log_info("✅ All indexes created successfully")
                return True
                
            except Exception as e:
                trans.rollback()
                log_error(f"❌ Error creating indexes: {e}")
                return False
                
    except Exception as e:
        log_error(f"❌ Database connection error: {e}")
        return False

def main():
    """اجرای migration"""
    log_info("🚀 Starting database optimization migration...")
    
    settings = Settings()
    
    # ساخت connection URL
    if settings.database.postgres_url:
        database_url = settings.database.postgres_url
    else:
        database_url = (
            f"postgresql://{settings.database.postgres_user}:"
            f"{settings.database.postgres_password}@"
            f"{settings.database.postgres_host}:"
            f"{settings.database.postgres_port}/"
            f"{settings.database.postgres_db}"
        )
    
    # Test connection, fallback to SQLite
    try:
        test_engine = create_engine(database_url, connect_args={"connect_timeout": 2})
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        log_info("✅ PostgreSQL connection successful")
    except Exception as pg_error:
        log_warning(f"⚠️ PostgreSQL not available ({pg_error}), using SQLite")
        sqlite_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "rag_database.db"
        )
        database_url = f"sqlite:///{sqlite_path}"
        log_info(f"📁 Using SQLite database: {sqlite_path}")
    
    # Create engine
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
    
    # Run migration
    success = add_indexes(engine)
    
    if success:
        log_info("✅ Migration completed successfully")
        return 0
    else:
        log_error("❌ Migration failed")
        return 1

if __name__ == "__main__":
    exit(main())

