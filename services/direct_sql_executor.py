# -*- coding: utf-8 -*-
"""
Direct SQL Executor
اجرای مستقیم SQL queries بدون نیاز به Text-to-SQL Agent
برای حالتی که Qwen Service در دسترس نیست
"""

import logging
from typing import Dict, Any, Optional, List
import re
import os
import sys
import importlib.util

from services.database_service import DatabaseService

_base_path = os.path.dirname(os.path.dirname(__file__))
if _base_path not in sys.path:
    sys.path.insert(0, _base_path)
_schema_path = os.path.join(_base_path, "models", "database_schema.py")
_spec = importlib.util.spec_from_file_location("direct_sql_database_schema", _schema_path)
_database_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_database_schema)
TableRow = _database_schema.TableRow

logger = logging.getLogger(__name__)


class DirectSQLExecutor:
    """اجرای مستقیم SQL queries برای query های ساده"""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
    
    def execute_simple_count_query(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """اجرای query ساده برای شمارش ردیف‌ها"""
        try:
            tables = self.database_service.list_tables(collection_name)
            if not tables:
                logger.warning(f"No tables found for collection: {collection_name}")
                return None
            
            total_rows = 0
            table_counts = []
            
            for table in tables:
                table_counts.append({
                    "table_name": table.table_name,
                    "row_count": table.row_count
                })
                total_rows += table.row_count
            
            logger.info(f"✅ Count query: {total_rows} total rows in {len(tables)} tables")
            
            return {
                "success": True,
                "total_rows": total_rows,
                "tables": table_counts,
                "count": len(table_counts),
                "query_type": "direct_count"
            }
            
        except Exception as e:
            logger.error(f"Direct count query failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_aggregation_query(self, collection_name: str, column_name: str, operation: str = "SUM") -> Optional[Dict[str, Any]]:
        """اجرای query aggregation (SUM, AVG, MAX, MIN)"""
        try:
            tables = self.database_service.list_tables(collection_name)
            if not tables:
                return None
            
            results = []
            
            for table in tables:
                with self.database_service.get_session() as session:
                    
                    rows = (
                        session.query(TableRow)
                        .filter(TableRow.table_id == table.id)
                        .all()
                    )
                    
                    if not rows:
                        continue
                    
                    # Extract column values
                    values = []
                    for row in rows:
                        row_data = row.data if isinstance(row.data, dict) else {}
                        # Try different column name formats
                        col_value = None
                        for key in row_data.keys():
                            if column_name.lower() in key.lower() or key.lower() in column_name.lower():
                                col_value = row_data.get(key)
                                break
                        
                        if col_value is not None:
                            try:
                                # Try to convert to number
                                if isinstance(col_value, (int, float)):
                                    values.append(float(col_value))
                                elif isinstance(col_value, str):
                                    # Remove commas and convert
                                    clean_value = col_value.replace(',', '').replace('،', '')
                                    values.append(float(clean_value))
                            except (ValueError, TypeError):
                                continue
                    
                    if values:
                        if operation.upper() == "SUM":
                            result_value = sum(values)
                        elif operation.upper() == "AVG":
                            result_value = sum(values) / len(values)
                        elif operation.upper() == "MAX":
                            result_value = max(values)
                        elif operation.upper() == "MIN":
                            result_value = min(values)
                        else:
                            result_value = sum(values)  # Default to SUM
                        
                        results.append({
                            "table_name": table.table_name,
                            "column": column_name,
                            "operation": operation.upper(),
                            "result": result_value,
                            "count": len(values)
                        })
            
            if results:
                total_result = sum(r["result"] for r in results if operation.upper() == "SUM")
                
                logger.info(f"✅ Aggregation query ({operation}): {total_result if operation.upper() == 'SUM' else results[0]['result']}")
                
                return {
                    "success": True,
                    "results": results,
                    "total": total_result if operation.upper() == "SUM" else None,
                    "query_type": "direct_aggregation",
                    "operation": operation.upper()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Aggregation query failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_lookup_query(self, collection_name: str, column_name: str, value: str) -> Optional[Dict[str, Any]]:
        """جستجو برای یک مقدار خاص در یک ستون"""
        try:
            tables = self.database_service.list_tables(collection_name)
            if not tables:
                return None
            
            matches = []
            
            for table in tables:
                with self.database_service.get_session() as session:
                    
                    rows = (
                        session.query(TableRow)
                        .filter(TableRow.table_id == table.id)
                        .all()
                    )
                    
                    for row in rows:
                        row_data = row.data if isinstance(row.data, dict) else {}
                        
                        # Try to find matching column and value
                        for key in row_data.keys():
                            if column_name.lower() in key.lower() or key.lower() in column_name.lower():
                                cell_value = str(row_data.get(key, ""))
                                if value in cell_value or cell_value == value:
                                    matches.append({
                                        "table_name": table.table_name,
                                        "row_index": row.row_index,
                                        "data": row_data
                                    })
                                    break
            
            if matches:
                logger.info(f"✅ Lookup query: Found {len(matches)} matches for {column_name}={value}")
                return {
                    "success": True,
                    "matches": matches,
                    "count": len(matches),
                    "query_type": "direct_lookup"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Lookup query failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_table_query(self, collection_name: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """نمایش چند ردیف اول از جداول"""
        try:
            tables = self.database_service.list_tables(collection_name)
            if not tables:
                return None
            
            results = []
            
            for table in tables[:1]:  # فقط اولین table
                with self.database_service.get_session() as session:
                    
                    rows = (
                        session.query(TableRow)
                        .filter(TableRow.table_id == table.id)
                        .order_by(TableRow.row_index)
                        .limit(limit)
                        .all()
                    )
                    
                    rows_data = []
                    for row in rows:
                        rows_data.append(row.data)
                    
                    results.extend(rows_data)
            
            return {
                "success": True,
                "rows": results,
                "count": len(results),
                "columns": list(results[0].keys()) if results else [],
                "query_type": "direct_select"
            }
            
        except Exception as e:
            logger.error(f"Direct table query failed: {e}")
            return None
    
    def generate_simple_answer(self, query: str, results: Dict[str, Any]) -> str:
        """تولید پاسخ ساده از نتایج"""
        if not results or not results.get("success"):
            return "متأسفانه نتوانستم پاسخ سوال شما را پیدا کنم."
        
        query_lower = query.lower()
        
        if "چند" in query or "تعداد" in query or "ردیف" in query:
            if results.get("query_type") == "direct_count":
                total = results.get("total_rows", 0)
                tables = results.get("tables", [])
                
                answer = f"تعداد کل ردیف‌ها در جدول: **{total}** ردیف\n\n"
                
                if tables:
                    answer += "تعداد ردیف‌ها در هر جدول:\n"
                    for table in tables:
                        answer += f"- {table.get('table_name')}: {table.get('row_count')} ردیف\n"
                
                return answer
        
        if "نمایش" in query or "نمایش بده" in query or results.get("rows"):
            rows = results.get("rows", [])
            if rows:
                answer = f"نمایش {len(rows)} ردیف از جدول:\n\n"
                
                # نمایش به صورت جدول
                if rows:
                    columns = list(rows[0].keys())
                    answer += "| " + " | ".join(columns[:5]) + " |\n"  # فقط 5 ستون اول
                    answer += "| " + " | ".join(["---"] * min(5, len(columns))) + " |\n"
                    
                    for row in rows[:5]:  # فقط 5 ردیف اول
                        values = [str(row.get(col, ""))[:30] for col in columns[:5]]
                        answer += "| " + " | ".join(values) + " |\n"
                
                return answer
        
        return "نتایج یافت شد اما نمی‌توانم پاسخ دقیق تولید کنم."

