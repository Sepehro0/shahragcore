# -*- coding: utf-8 -*-
"""
Database Service
سرویس مدیریت اتصال و عملیات پایگاه داده PostgreSQL
"""

import logging
import re
import unicodedata
from typing import Optional, Dict, Any, List, Tuple, Set
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy import Text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
try:
    from sqlalchemy.dialects.postgresql import JSONB
    POSTGRES_AVAILABLE = True
except:
    POSTGRES_AVAILABLE = False
import json

# Direct import to avoid __init__.py conflicts
import sys
import os
_base_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _base_path)

# Import directly from file to bypass models/__init__.py
import importlib.util
_schema_path = os.path.join(_base_path, "models", "database_schema.py")
_spec = importlib.util.spec_from_file_location("database_schema", _schema_path)
_database_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_database_schema)

Base = _database_schema.Base
Collection = _database_schema.Collection
DataTable = _database_schema.DataTable
TableRow = _database_schema.TableRow
TableColumn = _database_schema.TableColumn
QueryCache = _database_schema.QueryCache
from config.settings import Settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """سرویس مدیریت پایگاه داده PostgreSQL"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
        
    def _is_booklet_collection(self, collection_name: Optional[str]) -> bool:
        """بررسی اینکه collection از نوع booklet است"""
        if not collection_name:
            return False
        normalized = collection_name.lower()
        return normalized.startswith("booklet_bo") or "booklet__bo" in normalized or "booklet" in normalized
    
    def _should_exclude_column(self, collection_name: Optional[str], column_name: Optional[str]) -> bool:
        """تشخیص اینکه آیا ستون باید از جستجو حذف شود"""
        if not collection_name or not column_name:
            return False
        return self._is_booklet_collection(collection_name) and column_name.strip().lower() == "maddeh_id"
    
    def _initialize_engine(self):
        """مقداردهی اولیه engine و session"""
        try:
            # ساخت connection URL
            if self.settings.database.postgres_url:
                database_url = self.settings.database.postgres_url
            else:
                # Try PostgreSQL first
                database_url = (
                    f"postgresql://{self.settings.database.postgres_user}:"
                    f"{self.settings.database.postgres_password}@"
                    f"{self.settings.database.postgres_host}:"
                    f"{self.settings.database.postgres_port}/"
                    f"{self.settings.database.postgres_db}"
                )
                
                # Test PostgreSQL connection, fallback to SQLite
                try:
                    test_engine = create_engine(database_url, connect_args={"connect_timeout": 2})
                    with test_engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    test_engine.dispose()
                    logger.info("✅ PostgreSQL connection successful")
                except Exception as pg_error:
                    logger.warning(f"⚠️ PostgreSQL not available ({pg_error}), falling back to SQLite")
                    # Fallback to SQLite
                    import os
                    sqlite_path = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        "rag_database.db"
                    )
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"📁 Using SQLite database: {sqlite_path}")
            
            # ایجاد engine با connection pooling
            if database_url.startswith("sqlite"):
                self.engine = create_engine(
                    database_url,
                    connect_args={"check_same_thread": False},
                    echo=False
                )
            else:
                self.engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=self.settings.database.postgres_pool_size,
                    max_overflow=self.settings.database.postgres_max_overflow,
                    pool_pre_ping=True,
                    echo=False
                )
            
            # ایجاد session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            logger.info("✅ Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database engine: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager برای session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """ایجاد جداول در پایگاه داده"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """حذف جداول (فقط برای development)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("⚠️ All database tables dropped")
        except Exception as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """تست اتصال به پایگاه داده"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
    
    # ========== Collection Operations ==========
    
    def get_or_create_collection(self, name: str, description: Optional[str] = None) -> Collection:
        """دریافت یا ایجاد collection"""
        with self.get_session() as session:
            collection = session.query(Collection).filter(Collection.name == name).first()
            if not collection:
                collection = Collection(name=name, description=description)
                session.add(collection)
                session.flush()
                logger.info(f"✅ Created new collection: {name}")
            return collection
    
    def get_collection(self, name: str) -> Optional[Collection]:
        """دریافت collection"""
        with self.get_session() as session:
            return session.query(Collection).filter(Collection.name == name).first()
    
    def list_collections(self) -> List[Collection]:
        """لیست تمام collections"""
        with self.get_session() as session:
            return session.query(Collection).all()
    
    # ========== Table Operations ==========
    
    def create_table_from_dataframe(
        self,
        collection_name: str,
        table_name: str,
        sheet_name: Optional[str],
        source_file: Optional[str],
        dataframe,
        schema_info: Optional[Dict[str, Any]] = None
    ) -> DataTable:
        """ایجاد table از DataFrame"""
        with self.get_session() as session:
            # دریافت یا ایجاد collection
            collection = self.get_or_create_collection(collection_name)
            
            # حذف table قبلی با همین نام (اگر وجود دارد)
            existing_table = (
                session.query(DataTable)
                .filter(
                    DataTable.collection_id == collection.id,
                    DataTable.table_name == table_name
                )
                .first()
            )
            if existing_table:
                session.delete(existing_table)
                session.flush()
            
            # ایجاد table جدید
            table = DataTable(
                collection_id=collection.id,
                table_name=table_name,
                sheet_name=sheet_name,
                source_file=source_file,
                schema_info=schema_info or {},
                row_count=len(dataframe),
                column_count=len(dataframe.columns)
            )
            session.add(table)
            session.flush()
            
            # ایجاد columns
            columns = []
            for idx, col_name in enumerate(dataframe.columns):
                # تشخیص data type
                sample_value = dataframe[col_name].dropna().iloc[0] if not dataframe[col_name].dropna().empty else None
                data_type = self._infer_data_type(sample_value) if sample_value is not None else "string"
                
                column = TableColumn(
                    table_id=table.id,
                    column_name=str(col_name),
                    column_index=idx,
                    data_type=data_type
                )
                columns.append(column)
                session.add(column)
            
            session.flush()
            
            # ایجاد rows
            for row_idx, (_, row) in enumerate(dataframe.iterrows()):
                row_data = {}
                for col_idx, col_name in enumerate(dataframe.columns):
                    row_data[str(col_name)] = self._normalize_value(row[col_name])
                
                table_row = TableRow(
                    table_id=table.id,
                    row_index=row_idx + 1,  # 1-indexed
                    data=row_data
                )
                session.add(table_row)
            
            session.flush()
            logger.info(f"✅ Created table '{table_name}' with {len(dataframe)} rows")


        # Materialize dataframe as a physical SQL table for direct SQL queries
        try:
            to_sql_kwargs = {
                "name": table_name,
                "con": self.engine,
                "if_exists": "replace",
                "index": False
            }
            if self.engine.dialect.name != "sqlite":
                to_sql_kwargs["method"] = "multi"
            to_sql_kwargs["dtype"] = {col: Text() for col in dataframe.columns}
            dataframe.to_sql(**to_sql_kwargs)
            logger.info(f"✅ Materialized SQL table '{table_name}' for direct queries")
        except Exception as materialize_error:
            logger.error(f"⚠️ Failed to materialize SQL table '{table_name}': {materialize_error}")

        return table
    
    def _infer_data_type(self, value: Any) -> str:
        """تشخیص نوع داده"""
        if isinstance(value, (int,)):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, bool):
            return "boolean"
        else:
            return "string"
    
    def _normalize_value(self, value: Any) -> Any:
        """نرمال‌سازی مقدار برای ذخیره در JSONB"""
        import pandas as pd
        if pd.isna(value):
            return None
        if isinstance(value, (pd.Timestamp,)):
            return value.isoformat()
        if isinstance(value, (pd.Timedelta,)):
            return str(value)
        return value
    
    def get_table(self, collection_name: str, table_name: str) -> Optional[DataTable]:
        """دریافت table"""
        with self.get_session() as session:
            collection = self.get_collection(collection_name)
            if not collection:
                return None
            return (
                session.query(DataTable)
                .filter(
                    DataTable.collection_id == collection.id,
                    DataTable.table_name == table_name
                )
                .first()
            )
    
    def list_tables(self, collection_name: str) -> List[DataTable]:
        """لیست tables یک collection"""
        with self.get_session() as session:
            collection = self.get_collection(collection_name)
            if not collection:
                return []
            return session.query(DataTable).filter(DataTable.collection_id == collection.id).all()
    
    # ========== Query Operations ==========
    
    def execute_sql_query(
        self,
        sql_query: str,
        collection_name: Optional[str] = None,
        timeout: int = 30,
        _attempted_device_fallback: bool = False
    ) -> Dict[str, Any]:
        """اجرای SQL query با امنیت"""
        try:
            # 🔍 LOG SQL FOR DEBUGGING
            logger.info(f"🔍 [DATABASE] EXECUTING SQL QUERY:\n{sql_query}")
            logger.info(f"🔍 [DATABASE] Collection: {collection_name}, Timeout: {timeout}")
            
            # بررسی محدودیت‌های امنیتی
            sql_query_lower = sql_query.lower().strip()
            
            # جلوگیری از دستورات خطرناک
            dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
            for keyword in dangerous_keywords:
                if f' {keyword} ' in f' {sql_query_lower} ':
                    raise ValueError(f"Unsafe SQL operation detected: {keyword}")
            
            # فقط SELECT queries مجاز (شامل WITH CTE)
            if not (sql_query_lower.startswith('select') or sql_query_lower.startswith('with')):
                raise ValueError("Only SELECT queries are allowed")

            device_fallback_sql: Optional[str] = None
            if not _attempted_device_fallback:
                device_fallback_sql = self._attempt_device_column_fallback(sql_query)

            prepared_sql = self._prepare_sql_query(sql_query, collection_name)
            logger.info(f"🔍 [DATABASE] Prepared SQL:\n{prepared_sql}")
            
            detail_rows: List[Dict[str, Any]] = []
            detail_columns: List[str] = []
            detail_sql: Optional[str] = None
            
            with self.engine.connect() as conn:
                logger.info(f"🔍 [DATABASE] Executing query with timeout {timeout}s...")
                result = conn.execute(text(f"SET statement_timeout = '{timeout}s'; {prepared_sql}"))
                
                # تبدیل نتیجه به dict
                columns = result.keys()
                rows = []
                for row in result:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        row_dict[col] = row[idx]
                    rows.append(row_dict)

                should_try_detail = self._query_has_aggregation(prepared_sql)

                if should_try_detail:
                    derived_sql = self._derive_detail_sql(prepared_sql)
                    if derived_sql:
                        prepared_detail_sql = self._prepare_sql_query(derived_sql, collection_name)
                        try:
                            detail_result = conn.execute(text(f"SET statement_timeout = '{timeout}s'; {prepared_detail_sql}"))
                            detail_columns = list(detail_result.keys())
                            for detail_row in detail_result:
                                detail_rows.append({detail_columns[idx]: detail_row[idx] for idx in range(len(detail_columns))})
                            detail_sql = prepared_detail_sql
                        except Exception as detail_error:
                            logger.debug(f"Failed to fetch detail rows: {detail_error}")

                if device_fallback_sql and not detail_rows and self._is_result_empty(rows):
                    logger.debug("🔁 Retrying query using 'عنوان_دستگاه' fallback")
                    return self.execute_sql_query(
                        device_fallback_sql,
                        timeout=timeout,
                        collection_name=collection_name,
                        _attempted_device_fallback=True
                    )
                
                response: Dict[str, Any] = {
                    "success": True,
                    "rows": rows,
                    "count": len(rows),
                    "columns": list(columns),
                    "prepared_sql": prepared_sql
                }

                if detail_rows:
                    response.update({
                        "detail_rows": detail_rows,
                        "detail_columns": detail_columns,
                        "detail_sql": detail_sql
                    })

                return response
                
        except Exception as e:
            logger.error(f"❌ [DATABASE] SQL query execution failed: {e}")
            logger.error(f"❌ [DATABASE] Failed SQL query was:\n{sql_query}")
            import traceback
            logger.error(f"❌ [DATABASE] Traceback:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "count": 0,
                "columns": []
            }

    def _prepare_sql_query(self, sql_query: str, collection_name: Optional[str]) -> str:
        """اعمال اصلاحات خودکار روی SQL قبل از اجرا"""
        if not sql_query:
            return sql_query

        prepared_sql = self._fix_select_distinct(sql_query)

        columns_map: Optional[Dict[str, Dict[str, str]]] = None

        if collection_name:
            columns_map = self.get_collection_columns(collection_name)
            # TEMPORARILY DISABLED: _align_known_identifiers به کاف عربی آسیب می‌زند
            # prepared_sql = self._align_known_identifiers(prepared_sql, columns_map)
            prepared_sql = self._cast_numeric_ilike(prepared_sql, columns_map)
            prepared_sql = self._cast_numeric_aggregations(prepared_sql, columns_map)
            prepared_sql = self._ensure_wildcard_ilike(prepared_sql)

        prepared_sql = self._normalize_ilike_columns(prepared_sql)
        prepared_sql = self._expand_phrase_ilike(prepared_sql)
        prepared_sql = self._fix_and_or_precedence(prepared_sql)
        
        # تبدیل نام ستون‌های فارسی به عربی (برای مطابقت با PostgreSQL)
        # این باید آخرین مرحله باشد تا همه تغییرات قبلی normalize شوند
        prepared_sql = self._normalize_column_names_to_arabic(prepared_sql)

        return prepared_sql
    
    def _normalize_column_names_to_arabic(self, sql_query: str) -> str:
        """
        تبدیل حروف فارسی به عربی در نام ستون‌ها برای مطابقت با PostgreSQL
        
        توجه: PostgreSQL نام ستون‌ها را به صورت مخلوط ذخیره می‌کند:
        - ستون‌های "هزینه" با یای فارسی: `براورد_اعتبارات_هزینه_ای_عمومی`
        - ستون‌های "تملک" با یای عربی: `براورد_تملك_دارايي_هاي_سرمايه_اي_ع`
        - ستون‌های "دستگاه" در masaref با یای عربی: `عنوان_دستگاه_اصلي`
        - ستون‌های "دستگاه" در manabe3 با یای فارسی: `عنوان_دستگاه_اجرایی`
        - ستون "جمع_كل" با کاف عربی
        
        بنابراین باید فقط ستون‌های خاص را تبدیل کنیم:
        - کاف فارسی -> ك عربی (فقط برای masaref، نه manabe3 که ک فارسی دارد)
        - یای فارسی -> ي عربی (فقط برای ستون‌های تملک و دستگاه در masaref)
        - برآورد -> براورد (بدون آ)
        - نام‌های طولانی به نام‌های کوتاه شده
        
        این تابع فقط نام ستون‌ها را (داخل double quotes) تبدیل می‌کند
        و مقادیر ILIKE را تغییر نمی‌دهد.
        """
        # تشخیص جدول manabe3 - ستون‌های دستگاه با ی فارسی هستند
        is_manabe3_query = 'manabe3_sheet1' in sql_query or 'manabe_sheet1' in sql_query
        # Mapping کلمات خاص (مانند برآورد -> براورد)
        # توجه: فقط برای ستون‌های خاص این تبدیل را انجام می‌دهیم
        # ستون "برآورد_اعتبارات_هزینه_ای_متفرقه" در database با آ است و نباید تبدیل شود
        # اما ستون‌های "براورد_تملك_دارايي" بدون آ هستند
        word_mappings = {
            # فقط برای ستون‌های تملک (که در database بدون آ هستند)
            # 'برآورد_تملك': 'براورد_تملك',  # این تبدیل در column_truncation_mappings انجام می‌شود
        }
        
        # Mapping نام ستون‌های کوتاه شده در PostgreSQL
        # نام‌های کامل از metadata به نام‌های واقعی در database
        column_truncation_mappings = {
            # تملک دارایی سرمایه‌ای (با یای عربی در database)
            'براورد_تملك_دارايي_هاي_سرمايه_اي_عمومي': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ع',
            'براورد_تملك_دارايي_هاي_سرمايه_اي_متفرقه': 'براورد_تملك_دارايي_هاي_سرمايه_اي_م',
            'براورد_تملك_دارايي_هاي_سرمايه_اي_اختصاصي': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ا',
            'جمع_براورد_تملك_دارايي_هاي_سرمايه_اي': 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_',
            # همچنین با یای فارسی (اگر قبل از تبدیل باشد)
            'براورد_تملک_دارایی_های_سرمایه_ای_عمومی': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ع',
            'براورد_تملک_دارایی_های_سرمایه_ای_متفرقه': 'براورد_تملك_دارايي_هاي_سرمايه_اي_م',
            'براورد_تملک_دارایی_های_سرمایه_ای_اختصاصی': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ا',
            'جمع_براورد_تملک_دارایی_های_سرمایه_ای': 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_',
            # یارانه‌ها
            'براورد_تملك_دارايي_هاي_سرمايه_اي_يارانه_ها': 'براورد_تملک_دارایی_های_سرمایه_ای_ی',
        }
        
        def replace_in_column_name(match: re.Match) -> str:
            """تبدیل حروف در نام ستون"""
            column_name = match.group(1)
            original_name = column_name
            
            # ابتدا کلمات خاص را تبدیل کن (فقط برای ستون‌های خاص)
            # توجه: ستون "برآورد_اعتبارات_هزینه_ای_متفرقه" با آ است و نباید تبدیل شود
            # فقط ستون‌های تملک که در database بدون آ هستند را تبدیل می‌کنیم
            if 'تملك' in column_name or 'تملک' in column_name:
                # فقط برای ستون‌های تملک: برآورد -> براورد
                # ⚠️ استثنا: ستون "جمع_برآورد_تملك_دارايي_هاي_سرمايه_" در database با آ است
                if not column_name.startswith('جمع_برآورد'):
                    column_name = column_name.replace('برآورد', 'براورد')
            # ستون‌های اعتبارات را تغییر نمی‌دهیم (با آ باقی می‌مانند)
            
            if is_manabe3_query:
                # 🔹 manabe3_sheet1: ستون‌های دستگاه با ی فارسی + ک فارسی هستند
                # فقط ستون‌های درآمد (ملي_، استاني_، جمع_) با ی عربی هستند
                # ک فارسی در manabe3 نباید تبدیل شود (مثل جمع_کل، کد_بخش)
                # اما ستون‌های درآمد ی عربی دارند و نیازی به تبدیل ندارند
                pass  # هیچ تبدیلی برای manabe3 لازم نیست
            else:
                # 🔹 masaref_sheet1: تبدیل کاف فارسی به عربی (همیشه)
                column_name = column_name.replace('ک', 'ك')
            
                # تبدیل یای فارسی به عربی (فقط برای ستون‌های خاص)
                # ستون‌های "تملک" و "دستگاه" در masaref با یای عربی هستند
                # اما ستون‌های "هزینه" با یای فارسی هستند
                if 'تملک' in column_name or 'تملك' in column_name or 'دارايي' in column_name or 'دارایی' in column_name:
                    # ستون‌های تملک: تبدیل یای فارسی به عربی
                    column_name = column_name.replace('ی', 'ي')
                    column_name = column_name.replace('های', 'هاي')
                elif 'دستگاه' in column_name:
                    # ستون‌های دستگاه: تبدیل یای فارسی به عربی
                    column_name = column_name.replace('ی', 'ي')
                # ستون‌های "هزینه" را تغییر نمی‌دهیم (با یای فارسی باقی می‌مانند)
            
            # حالا mapping نام ستون‌های کوتاه شده
            if column_name in column_truncation_mappings:
                column_name = column_truncation_mappings[column_name]
            
            return f'"{column_name}"'
        
        # Pattern برای یافتن نام ستون‌ها داخل double quotes
        # این الگو فقط نام‌های ستون را تغییر می‌دهد نه مقادیر string
        # از negative lookbehind استفاده می‌کنیم تا TRANSLATE و توابع دیگر را نادیده بگیریم
        # اما در واقع، ما می‌خواهیم همه نام‌های داخل double quotes را match کنیم
        # چون TRANSLATE("عنوان_دستگاه_اصلي", ...) هم باید normalize شود
        pattern = r'"([^"]+)"'
        
        result = re.sub(pattern, replace_in_column_name, sql_query)
        
        return result

    def _fix_select_distinct(self, sql_query: str) -> str:
        """افزودن * در صورت وجود SELECT DISTINCT بدون ستون"""
        def _replace(match: re.Match) -> str:
            return f"SELECT DISTINCT * {match.group('rest')}"

        pattern = re.compile(r'(?i)select\s+distinct\s*(?P<rest>from\s)', re.MULTILINE)
        return pattern.sub(_replace, sql_query)

    def _cast_numeric_ilike(self, sql_query: str, columns_map: Optional[Dict[str, Dict[str, Dict[str, str]]]]) -> str:
        """تبدیل مقایسه ILIKE روی ستون‌های عددی به CAST(... AS TEXT)"""
        if not columns_map:
            return sql_query

        prepared_sql = sql_query
        numeric_types = {"integer", "float", "numeric", "double", "double precision", "bigint", "smallint"}

        for table_columns in columns_map.values():
            for column_name, info in table_columns.items():
                data_type = (info.get("data_type") or "").lower()
                if data_type not in numeric_types:
                    continue

                physical_name = info.get("physical_name") or column_name
                escaped_column = re.escape(column_name)

                pattern = re.compile(
                    rf'(?i)(?P<prefix>[\s\(,])(?:(?P<alias>[A-Za-z0-9_]+)\.)?"{escaped_column}"\s+ILIKE'
                )

                def _replacer(match: re.Match) -> str:
                    prefix = match.group('prefix')
                    alias = match.group('alias')
                    qualified = f'{alias}."{physical_name}"' if alias else f'"{physical_name}"'
                    return f"{prefix}CAST({qualified} AS TEXT) ILIKE"

                prepared_sql, _ = pattern.subn(_replacer, prepared_sql)

                plain_pattern = re.compile(
                    rf'(?i)(?P<prefix>[\s\(,])(?:(?P<alias>[A-Za-z0-9_]+)\.)?{escaped_column}\s+ILIKE'
                )

                def _plain_replacer(match: re.Match) -> str:
                    prefix = match.group('prefix')
                    alias = match.group('alias')
                    qualified_column = f'{alias}."{physical_name}"' if alias else f'"{physical_name}"'
                    return f"{prefix}CAST({qualified_column} AS TEXT) ILIKE"

                prepared_sql, _ = plain_pattern.subn(_plain_replacer, prepared_sql)

        return prepared_sql

    def _cast_numeric_aggregations(
        self,
        sql_query: str,
        columns_map: Optional[Dict[str, Dict[str, Dict[str, str]]]]
    ) -> str:
        """Cast aggregation targets to DOUBLE PRECISION when source columns are numeric."""
        if not columns_map:
            return sql_query

        prepared_sql = sql_query
        transliteration_pairs = (
            ("ک", "ك"),
            ("ك", "ک"),
            ("ی", "ي"),
            ("ي", "ی")
        )

        # 🆕 تشخیص جداول موجود در SQL تا physical_name درست انتخاب شود
        # مثلاً برای manabe_sheet1 از ملی_جمع_کل استفاده شود، نه ملي_جمع_کل از manabe3_sheet1
        sql_tables_found = set()
        for tbl_name in columns_map.keys():
            if tbl_name in sql_query:
                sql_tables_found.add(tbl_name)

        for table_name, table_columns in columns_map.items():
            # 🆕 اگر جداول خاصی در SQL پیدا شدند، فقط از همان جداول استفاده کن
            if sql_tables_found and table_name not in sql_tables_found:
                continue

            for desired_name, info in table_columns.items():
                data_type = (info.get("data_type") or "").lower()
                if data_type not in {"integer", "float", "numeric", "double", "double precision", "bigint", "smallint"}:
                    continue

                physical_name = info.get("physical_name") or desired_name
                candidates = {desired_name, physical_name}

                for base in list(candidates):
                    for src, tgt in transliteration_pairs:
                        if src in base:
                            candidates.add(base.replace(src, tgt))

                for candidate in candidates:
                    if not candidate:
                        continue

                    escaped = re.escape(candidate)

                    pattern = re.compile(
                        rf'(?i)(?P<func>sum|avg|min|max)\s*\(\s*(?:(?P<alias>[A-Za-z0-9_]+)\.)?"{escaped}"\s*\)'
                    )

                    def _replacer(match: re.Match, _phys=physical_name) -> str:
                        func = match.group('func')
                        alias = match.group('alias')
                        qualified = f'{alias}."{_phys}"' if alias else f'"{_phys}"'
                        logger.debug(f"🔁 Casting aggregation column '{match.group(0)}' using {qualified}")
                        return f"{func.upper()}(CAST({qualified} AS DOUBLE PRECISION))"

                    prepared_sql, _ = pattern.subn(_replacer, prepared_sql)

                    plain_pattern = re.compile(
                        rf'(?i)(?P<func>sum|avg|min|max)\s*\(\s*(?:(?P<alias>[A-Za-z0-9_]+)\.)?{escaped}\s*\)'
                    )

                    def _plain_replacer(match: re.Match, _phys=physical_name) -> str:
                        func = match.group('func')
                        alias = match.group('alias')
                        qualified = f'{alias}."{_phys}"' if alias else f'"{_phys}"'
                        logger.debug(f"🔁 Casting aggregation column '{match.group(0)}' using {qualified}")
                        return f"{func.upper()}(CAST({qualified} AS DOUBLE PRECISION))"

                    prepared_sql, _ = plain_pattern.subn(_plain_replacer, prepared_sql)

        generic_pattern = re.compile(
            r'(?i)(?P<func>sum|avg|min|max)\s*\(\s*(?P<expr>(?:(?P<alias>[A-Za-z0-9_]+)\.)?"[^"]+"|(?:(?P<alias2>[A-Za-z0-9_]+)\.)?[A-Za-z0-9_]+)\s*\)'
        )

        def _generic_replacer(match: re.Match) -> str:
            original = match.group(0)
            if 'CAST' in original.upper():
                return original
            func = match.group('func').upper()
            expr = match.group('expr')
            logger.debug(f"🔁 Casting aggregation column '{original}' using {expr}")
            return f"{func}(CAST({expr} AS DOUBLE PRECISION))"

        prepared_sql = generic_pattern.sub(_generic_replacer, prepared_sql)

        return prepared_sql

    def _align_known_identifiers(
        self,
        sql_query: str,
        columns_map: Optional[Dict[str, Dict[str, Dict[str, str]]]]
    ) -> str:
        """هماهنگ سازی نام ستون‌ها و جداول با استفاده از نگاشت شناخته شده"""
        if not columns_map:
            return sql_query

        table_lookup: Dict[str, str] = {
            self._normalize_identifier(table_name): table_name
            for table_name in columns_map.keys()
        }

        alias_to_table: Dict[str, str] = {}

        def _register_alias(table: str, alias: Optional[str]) -> None:
            normalized_table = self._normalize_identifier(table)
            resolved_table = table_lookup.get(normalized_table, table)
            if alias:
                alias_to_table[alias] = resolved_table
            else:
                alias_to_table[resolved_table] = resolved_table

        for match in re.finditer(
            r"(?i)(from|join)\s+\"?([A-Za-z0-9_]+)\"?(?:\s+(?:as\s+)?([A-Za-z0-9_]+))?",
            sql_query
        ):
            table_name = match.group(2)
            alias = match.group(3)
            _register_alias(table_name, alias)

        normalized_column_map: Dict[str, List[str]] = {}
        for table_name, columns in columns_map.items():
            for desired_name, info in columns.items():
                physical_name = info.get("physical_name", desired_name)
                key = self._normalize_identifier(desired_name)
                normalized_column_map.setdefault(key, []).append(physical_name)

        def _resolve_column(identifier: str, alias: Optional[str]) -> Optional[str]:
            normalized = self._normalize_identifier(identifier)

            candidate_tables: List[str] = []
            if alias and alias in alias_to_table:
                candidate_tables.append(alias_to_table[alias])
            else:
                candidate_tables.extend(columns_map.keys())

            for table_name in candidate_tables:
                columns = columns_map.get(table_name, {})
                for desired_name, info in columns.items():
                    physical_name = info.get("physical_name", desired_name)
                    if self._normalize_identifier(desired_name) == normalized or \
                       self._normalize_identifier(physical_name) == normalized:
                        # بازگشت physical_name که مستقیماً از database آمده
                        # این باید با کاف عربی باشد اگر در database اینطور باشد
                        return physical_name

            if normalized in normalized_column_map:
                return normalized_column_map[normalized][0]

            candidates: List[Tuple[int, str]] = []
            for key, values in normalized_column_map.items():
                if not key:
                    continue
                if normalized.startswith(key) or key.startswith(normalized):
                    candidates.append((len(key), values[0]))
            if not candidates:
                reduced = normalized
                while reduced and reduced not in normalized_column_map:
                    reduced = reduced[:-1]
                if reduced in normalized_column_map:
                    return normalized_column_map[reduced][0]
                return None
            return max(candidates, key=lambda item: item[0])[1]

        def _replace_identifier(match: re.Match) -> str:
            alias = match.group('alias')
            identifier = match.group('identifier')

            target = _resolve_column(identifier, alias)
            if target and target != identifier:
                logger.debug(f"🔁 Rewriting identifier '{identifier}' -> '{target}'")
                prefix = f"{alias}." if alias else ""
                return f'{prefix}"{target}"'

            return match.group(0)

        return re.sub(
            r'(?:(?P<alias>[A-Za-z0-9_]+)\.)?"(?P<identifier>[^"\']+)"',
            _replace_identifier,
            sql_query
        )

    def get_collection_columns(self, collection_name: str) -> Dict[str, Dict[str, Dict[str, str]]]:
        """دریافت نقشه ستون‌ها و نوع داده برای یک collection"""
        with self.get_session() as session:
            collection = (
                session.query(Collection)
                .filter(Collection.name == collection_name)
                .first()
            )

            if not collection:
                return {}

            tables = (
                session.query(DataTable)
                .filter(DataTable.collection_id == collection.id)
                .all()
            )

            column_map: Dict[str, Dict[str, Dict[str, str]]] = {}

            for table in tables:
                columns = (
                    session.query(TableColumn)
                    .filter(TableColumn.table_id == table.id)
                    .all()
                )

                physical_columns = self._get_physical_columns(table.table_name)
                physical_lookup = {
                    self._normalize_identifier(col): col
                    for col in physical_columns
                }

                resolved_columns: Dict[str, Dict[str, str]] = {}
                for column in columns:
                    if self._should_exclude_column(collection_name, column.column_name):
                        continue
                    desired_name = column.column_name
                    normalized = self._normalize_identifier(desired_name)
                    physical_name = physical_lookup.get(normalized)
                    if not physical_name:
                        candidates = [
                            (len(key), value)
                            for key, value in physical_lookup.items()
                            if normalized.startswith(key) or key.startswith(normalized)
                        ]
                        if candidates:
                            physical_name = max(candidates, key=lambda item: item[0])[1]
                    resolved_columns[desired_name] = {
                        "physical_name": physical_name or desired_name,
                        "data_type": column.data_type or ""
                    }

                column_map[table.table_name] = resolved_columns

            return column_map

    def _get_physical_columns(self, table_name: str) -> List[str]:
        """دریافت نام ستون‌های واقعی جدول از PostgreSQL"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = :table"
                ), {"table": table_name})
                return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"⚠️ Unable to fetch physical columns for {table_name}: {e}")
            return []

    def _normalize_identifier(self, value: str) -> str:
        """نرمال‌سازی نام ستون/جدول برای مقایسه"""
        if not value:
            return ""

        normalized = unicodedata.normalize('NFKD', value)
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        translation_map = str.maketrans({
            'آ': 'ا',
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا',
            'ي': 'ی',
            'ى': 'ی',
            'ئ': 'ی',
            'ؤ': 'و',
            'ة': 'ه',
            'ک': 'ك'  # تبدیل کاف فارسی به عربی (برای تطابق با database)
        })
        normalized = normalized.translate(translation_map)
        normalized = normalized.replace('\u200c', '').replace('\u200f', '')
        normalized = re.sub(r'[\s_\-\/]+', '', normalized)
        return normalized.lower()

    def get_schema_description(self, collection_name: str) -> str:
        """دریافت توضیحات schema برای Text-to-SQL"""
        with self.get_session() as session:
            collection = self.get_collection(collection_name)
            if not collection:
                return ""
            
            tables = session.query(DataTable).filter(DataTable.collection_id == collection.id).all()
            
            schema_descriptions = []
            for table in tables:
                columns = session.query(TableColumn).filter(TableColumn.table_id == table.id).order_by(TableColumn.column_index).all()
                
                table_desc = f"جدول: {table.table_name}\n"
                if table.sheet_name:
                    table_desc += f"Sheet: {table.sheet_name}\n"
                table_desc += "ستون‌ها:\n"
                
                for col in columns:
                    if self._should_exclude_column(collection_name, col.column_name):
                        continue
                    table_desc += f"  - {col.column_name} ({col.data_type})\n"
                
                table_desc += f"تعداد سطرها: {table.row_count}\n"
                schema_descriptions.append(table_desc)
            
            return "\n\n".join(schema_descriptions)

    def _ensure_wildcard_ilike(self, sql_query: str) -> str:
        """Ensure ILIKE comparisons include wildcards to support substring matches."""
        def _replace_literal(match: re.Match) -> str:
            prefix = match.group('prefix') or ''
            value = match.group('value')
            if '%' in value or '_' in value:
                return match.group(0)
            normalized_value = value.strip()
            return f" {prefix}ILIKE '%{normalized_value}%'"

        pattern = re.compile(r"\s(?P<prefix>NOT\s+)?ILIKE\s+'(?P<value>[^']+)'", re.IGNORECASE)
        return pattern.sub(_replace_literal, sql_query)

    def _query_has_aggregation(self, sql_query: str) -> bool:
        return bool(re.search(r'\b(sum|avg|min|max|count)\s*\(', sql_query, re.IGNORECASE))

    def _derive_detail_sql(self, sql_query: str) -> Optional[str]:
        upper_sql = sql_query.upper()
        if ' JOIN ' in upper_sql:
            return None
        if ' UNION ' in upper_sql:
            return None
        match = re.search(
            r'FROM\s+(?P<table>"?[A-Za-z0-9_\.]+"?)\s*(?:AS\s+)?(?P<alias>[A-Za-z0-9_]+)?\s*(?P<rest>.*)',
            sql_query,
            re.IGNORECASE | re.DOTALL
        )
        if not match:
            return None
        table = match.group('table').strip()
        alias = match.group('alias')
        rest = match.group('rest') or ''

        keyword_aliases = {"WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET"}
        if alias and alias.upper() in keyword_aliases:
            rest = f"{alias} {rest}".strip()
            alias = None

        stop_keywords = [' GROUP BY', ' ORDER BY', ' HAVING', ' LIMIT', ' OFFSET']
        where_clause = ''
        where_match = re.search(r'(?i)\bWHERE\b', rest)
        if where_match:
            where_clause = rest[where_match.start():]
            for keyword in stop_keywords:
                keyword_pos = where_clause.upper().find(keyword)
                if keyword_pos != -1:
                    where_clause = where_clause[:keyword_pos]
                    break
            where_clause = where_clause.strip()
        if alias and where_clause:
            alias_pattern = re.compile(rf'\b{re.escape(alias)}\.', re.IGNORECASE)
            where_clause = alias_pattern.sub('', where_clause)
        detail_sql = f'SELECT * FROM {table}'
        if where_clause:
            detail_sql += f' {where_clause}'
        if ' LIMIT ' not in detail_sql.upper():
            detail_sql += ' LIMIT 500'
        return detail_sql

    def _fix_and_or_precedence(self, sql_query: str) -> str:
        where_match = re.search(r'(?i)\bWHERE\b', sql_query)
        if not where_match:
            return sql_query
        start = where_match.start()
        condition_start = where_match.end()
        rest = sql_query[condition_start:]
        keywords = [' GROUP BY', ' ORDER BY', ' HAVING', ' LIMIT', ' OFFSET']
        split_index = len(rest)
        upper_rest = rest.upper()
        for keyword in keywords:
            idx = upper_rest.find(keyword)
            if idx != -1 and idx < split_index:
                split_index = idx
        condition_text = rest[:split_index].strip()
        tail = rest[split_index:]
        if '(' in condition_text and ')' in condition_text:
            # اگر پرانتزها به صورت گروه‌بندی واضح استفاده شده باشد، تغییری اعمال نکن
            # با این حال، پرانتزهای داخل توابع (مانند TRANSLATE یا CAST) نباید مانع اصلاح شوند
            stripped = condition_text.replace('(', '').replace(')', '')
            if ' OR ' in condition_text.upper() and ' AND ' in condition_text.upper():
                pass
            else:
                return sql_query
        def _split_top_level(expr: str) -> Tuple[List[str], List[str]]:
            terms: List[str] = []
            ops: List[str] = []
            buffer: List[str] = []
            depth = 0
            idx = 0
            while idx < len(expr):
                segment = expr[idx:]
                char = expr[idx]
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth = max(depth - 1, 0)
                lower_segment = segment.lower()
                if depth == 0:
                    if lower_segment.startswith(' and '):
                        terms.append(''.join(buffer).strip())
                        ops.append('AND')
                        buffer = []
                        idx += 4
                        continue
                    if lower_segment.startswith(' or '):
                        terms.append(''.join(buffer).strip())
                        ops.append('OR')
                        buffer = []
                        idx += 3
                        continue
                buffer.append(char)
                idx += 1
            terms.append(''.join(buffer).strip())
            return [term for term in terms if term], ops

        terms, operators = _split_top_level(condition_text)
        if len(terms) < 2:
            return sql_query
        upper_ops = [op.upper() for op in operators]
        if 'OR' not in upper_ops or 'AND' not in upper_ops:
            return sql_query
        first_or_index = next((idx for idx, op in enumerate(upper_ops) if op == 'OR'), None)
        if first_or_index is None or first_or_index == 0:
            return sql_query
        base_terms = [terms[i].strip() for i in range(first_or_index)]
        or_terms = [terms[i].strip() for i in range(first_or_index, len(terms))]
        if not base_terms or not or_terms:
            return sql_query
        new_condition = ''
        if base_terms:
            new_condition = ' AND '.join(base_terms) + ' AND (' + ' OR '.join(or_terms) + ')'
        else:
            new_condition = '(' + ' OR '.join(or_terms) + ')'
        rebuilt_sql = sql_query[:start] + 'WHERE ' + new_condition
        if tail:
            rebuilt_sql += tail
        return rebuilt_sql

    def _normalize_ilike_columns(self, sql_query: str) -> str:
        translation_source = "يكيۀة"
        translation_target = "یکیهه"

        def _wrap_column(column: str) -> str:
            normalized_column = column.strip()
            if normalized_column.upper().startswith("TRANSLATE("):
                return column
            return f"TRANSLATE({column}, '{translation_source}', '{translation_target}')"

        pattern = re.compile(
            r'(?P<column>(?:(?P<alias>[A-Za-z0-9_]+)\.)?"[^"]+"|[A-Za-z0-9_\.]+)\s+ILIKE\s+(?P<value>"[^"]*"|\'[^\']*\')',
            re.IGNORECASE
        )

        def _replacer(match: re.Match) -> str:
            column = match.group('column')
            value = match.group('value')
            wrapped_column = _wrap_column(column)
            quote_char = value[0]
            literal = value[1:-1]
            translation_table = str.maketrans(translation_source, translation_target)
            normalized_literal = literal.translate(translation_table)
            normalized_literal = normalized_literal.replace('\u200c', '').replace('\u200f', '')
            return f"{wrapped_column} ILIKE {quote_char}{normalized_literal}{quote_char}"

        return pattern.sub(_replacer, sql_query)

    def _expand_phrase_ilike(self, sql_query: str) -> str:
        """
        اعمال اصلاحات روی ILIKE conditions
        
        IMPORTANT: این متد نباید exact phrase را به AND تبدیل کند!
        اگر exact phrase وجود دارد (مثل '%مراکز اموزشی رفاهی%')، باید حفظ شود.
        فقط برای عبارات بدون wildcard که چند کلمه دارند، از AND استفاده می‌شود.
        """
        pattern = re.compile(
            r'(?P<expr>TRANSLATE\([^\)]*\)|"[^"]+"|[A-Za-z0-9_\.]+)\s+ILIKE\s+(?P<quote>\'|\")(?P<value>[^\'\"]+)(?P=quote)',
            re.IGNORECASE
        )

        def _replacer(match: re.Match) -> str:
            column_expr = match.group('expr')
            raw_value = match.group('value')
            
            # IMPORTANT: اگر exact phrase وجود دارد (شروع و پایان با %)، آن را حفظ کن
            if raw_value.startswith('%') and raw_value.endswith('%'):
                # این یک exact phrase است - نباید آن را به AND تبدیل کنیم
                return match.group(0)
            
            cleaned = raw_value.replace('%', ' ').strip()
            if not cleaned:
                return match.group(0)
            tokens = [token for token in re.split(r'\s+', cleaned) if token]
            if len(tokens) <= 1:
                return match.group(0)

            unique_tokens: List[str] = []
            seen_tokens: Set[str] = set()
            for token in tokens:
                normalized = token.lower()
                if normalized in seen_tokens:
                    continue
                seen_tokens.add(normalized)
                unique_tokens.append(token)

            expanded = ' AND '.join(
                f"{column_expr} ILIKE '%{token}%'" for token in unique_tokens
            )
            return f'({expanded})'

        return pattern.sub(_replacer, sql_query)

    def _is_result_empty(self, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return True
        for row in rows:
            if not row:
                continue
            for value in row.values():
                if value is None:
                    continue
                if isinstance(value, (int, float)) and value == 0:
                    continue
                if isinstance(value, str) and value.strip() in {'', '-'}:
                    continue
                return False
        return True

    def _attempt_device_column_fallback(self, sql_query: str) -> Optional[str]:
        # ⚠️ برای manabe3_sheet1 این fallback لازم نیست
        # چون ستون‌های manabe3 با ی فارسی هستند (عنوان_دستگاه_اجرایی، عنوان_دستگاه_اصلی)
        if 'manabe3_sheet1' in sql_query or 'manabe_sheet1' in sql_query:
            return None
        
        # فقط "عنوان_دستگاه_اصلی" (با یای فارسی) را به "عنوان_دستگاه_اصلي" (با یای عربی) تبدیل می‌کنیم
        # چون "عنوان_دستگاه_اصلي" در masaref database وجود دارد و نباید به "عنوان_دستگاه" تبدیل شود
        targets = ["عنوان_دستگاه_اصلی"]  # فقط یای فارسی
        fallback_sql = sql_query
        changed = False

        for target in targets:
            pattern = re.compile(rf'(?P<alias>[A-Za-z0-9_]+\.)?"{target}"')

            def _replacer(match: re.Match) -> str:
                alias = match.group('alias') or ''
                # تبدیل به "عنوان_دستگاه_اصلي" (با یای عربی) که در database وجود دارد
                return f'{alias}"عنوان_دستگاه_اصلي"'

            fallback_sql, replacements = pattern.subn(_replacer, fallback_sql)
            if replacements:
                changed = True

        entity_keywords = ('وزارت', 'سازمان', 'ستاد', 'دانشگاه', 'بنیاد', 'بانک', 'صندوق', 'نهاد', 'معاونت', 'شرکت', 'صدا', 'شبکه')
        section_pattern = re.compile(
            r'TRANSLATE\("عنوان_بخش",\s*\'[^\']*\',\s*\'[^\']*\'\)\s+ILIKE\s+(?P<quote>"|\')(?P<value>[^"\']*)(?P=quote)',
            re.IGNORECASE
        )

        def _section_detector(match: re.Match) -> str:
            nonlocal changed
            literal = match.group('value')
            if any(keyword in literal for keyword in entity_keywords):
                changed = True
                return match.group(0).replace('"عنوان_بخش"', '"عنوان_دستگاه"')
            return match.group(0)

        fallback_sql = section_pattern.sub(_section_detector, fallback_sql)

        # فقط اگر "عنوان_بخش" وجود دارد و "عنوان_دستگاه_اصلي" وجود ندارد، تبدیل می‌کنیم
        # این برای جلوگیری از تبدیل اشتباه "عنوان_دستگاه_اصلي" به "عنوان_دستگاه" است
        if '"عنوان_بخش"' in fallback_sql and '"عنوان_دستگاه_اصلي"' not in fallback_sql:
            # فقط اگر "عنوان_دستگاه" (بدون _اصلي) وجود دارد، تبدیل می‌کنیم
            # این برای جلوگیری از تبدیل اشتباه "عنوان_دستگاه_اصلي" است
            if '"عنوان_دستگاه"' in fallback_sql and '"عنوان_دستگاه_اصلي"' not in fallback_sql:
                changed = True
                fallback_sql = fallback_sql.replace('"عنوان_بخش"', '"عنوان_دستگاه"')
                fallback_sql = fallback_sql.replace('TRANSLATE("عنوان_بخش"', 'TRANSLATE("عنوان_دستگاه"')

        return fallback_sql if changed else None

