# -*- coding: utf-8 -*-
"""
Result Fusion
ترکیب نتایج RAG و Database
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from services.field_specific_answer_generator import get_field_answer_generator

logger = logging.getLogger(__name__)


class ResultFusion:
    """ترکیب نتایج از RAG و Database"""
    
    def __init__(
        self,
        rag_weight: float = 0.5,
        database_weight: float = 0.5,
        max_total_results: int = 20
    ):
        self.rag_weight = rag_weight
        self.database_weight = database_weight
        self.max_total_results = max_total_results
    
    def fuse_results(
        self,
        rag_results: Optional[List[Dict[str, Any]]],
        database_results: Optional[Dict[str, Any]],
        query_route: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ترکیب نتایج RAG و Database"""
        try:
            fused_context = []
            
            # وزن‌ها بر اساس routing
            if query_route["primary_path"] == "database":
                db_weight = 0.8
                rag_weight = 0.2
            elif query_route["primary_path"] == "rag":
                db_weight = 0.2
                rag_weight = 0.8
            else:  # hybrid
                db_weight = self.database_weight
                rag_weight = self.rag_weight
            
            # افزودن نتایج Database
            if database_results and database_results.get("success"):
                db_context = self._format_database_results(database_results)
                if db_context:
                    fused_context.append({
                        "type": "database",
                        "content": db_context,
                        "weight": db_weight,
                        "count": database_results.get("count", 0),
                        "sql": database_results.get("sql"),
                        "database_results": database_results  # Include raw results for fallback
                    })
            
            # افزودن نتایج RAG
            if rag_results:
                rag_context = self._format_rag_results(rag_results)
                if rag_context:
                    fused_context.append({
                        "type": "rag",
                        "content": rag_context,
                        "weight": rag_weight,
                        "count": len(rag_results),
                        "sources": [r.get("metadata", {}).get("source", "") for r in rag_results]
                    })
            
            # ساخت context نهایی
            final_context = self._build_final_context(fused_context)
            
            return {
                "success": True,
                "context": final_context,
                "components": fused_context,
                "has_database": database_results is not None and database_results.get("success"),
                "has_rag": rag_results is not None and len(rag_results) > 0
            }
            
        except Exception as e:
            logger.error(f"Result fusion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "context": ""
            }
    
    def _format_database_results(self, database_results: Dict[str, Any]) -> str:
        """فرمت‌سازی نتایج Database"""
        if not database_results.get("success"):
            return ""
        
        # Check for results format (can be "results" or "rows")
        rows = database_results.get("rows", [])
        if not rows:
            rows = database_results.get("results", [])
        
        if not rows:
            # Check for total_rows (from direct count)
            total_rows = database_results.get("total_rows")
            if total_rows is not None:
                return f"تعداد کل ردیف‌ها در جدول: {total_rows} ردیف\n"
            
            # Check for aggregation results
            total = database_results.get("total")
            if total is not None:
                operation = database_results.get("operation", "SUM")
                results = database_results.get("results", [])
                if results:
                    col_name = results[0].get("column", "")
                    return f"نتیجه {operation} برای ستون '{col_name}': {total:,.2f}\n"
            
            # Check for lookup results
            matches = database_results.get("matches", [])
            if matches:
                match_data = matches[0].get("data", {})
                return f"نتایج جستجو:\n{json.dumps(match_data, ensure_ascii=False, indent=2)}\n"
            
            return ""
        
        columns = database_results.get("columns", [])
        
        # ساخت متن از نتایج
        context = "نتایج جستجو در پایگاه داده:\n\n"
        
        # نمایش header
        if columns:
            context += "| " + " | ".join(columns) + " |\n"
            context += "| " + " | ".join(["---"] * len(columns)) + " |\n"
        
        # نمایش داده‌ها (حداکثر 10 سطر برای context)
        for row in rows[:10]:
            values = []
            for col in columns:
                value = row.get(col, "")
                values.append(str(value) if value is not None else "")
            context += "| " + " | ".join(values) + " |\n"
        
        if len(rows) > 10:
            context += f"\n... و {len(rows) - 10} سطر دیگر\n"
        
        return context
    
    def _format_rag_results(self, rag_results: List[Dict[str, Any]]) -> str:
        """فرمت‌سازی نتایج RAG"""
        if not rag_results:
            return ""
        
        context = "نتایج جستجو در اسناد:\n\n"
        
        for idx, result in enumerate(rag_results[:5], 1):  # حداکثر 5 نتیجه
            text = result.get("text", result.get("content", ""))
            metadata = result.get("metadata", {})
            
            source = metadata.get("source", metadata.get("filename", ""))
            page = metadata.get("page", metadata.get("row_index", ""))
            
            context += f"[{idx}] "
            if source:
                context += f"منبع: {source}"
                if page:
                    context += f", صفحه/ردیف: {page}"
                context += "\n"
            
            # متن (حداکثر 300 کاراکتر)
            text_preview = text[:300] + "..." if len(text) > 300 else text
            context += f"{text_preview}\n\n"
        
        if len(rag_results) > 5:
            context += f"... و {len(rag_results) - 5} نتیجه دیگر\n"
        
        return context
    
    def _build_final_context(self, components: List[Dict[str, Any]]) -> str:
        """ساخت context نهایی برای LLM"""
        if not components:
            return ""
        
        # مرتب‌سازی بر اساس weight
        sorted_components = sorted(components, key=lambda x: x["weight"], reverse=True)
        
        final_context = ""
        
        for comp in sorted_components:
            if comp["type"] == "database":
                final_context += "# داده‌های ساختاریافته از پایگاه داده:\n\n"
                final_context += comp["content"]
                if comp.get("sql"):
                    final_context += f"\n\n(Query SQL: {comp['sql']})\n"
                final_context += "\n\n"
            elif comp["type"] == "rag":
                final_context += "# اطلاعات از اسناد:\n\n"
                final_context += comp["content"]
                final_context += "\n\n"
        
        return final_context.strip()
    
    def create_enhanced_prompt(
        self,
        user_query: str,
        fused_results: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """ساخت prompt بهبود یافته برای LLM"""
        context = fused_results.get("context", "")
        
        prompt = ""
        
        # Context
        if context:
            prompt += f"# اطلاعات موجود:\n\n{context}\n\n"
        
        # سوال کاربر
        prompt += f"# سوال کاربر:\n{user_query}\n\n"
        
        # دستورالعمل
        prompt += "# دستورالعمل پاسخ‌گویی:\n"
        
        if fused_results.get("has_database") and fused_results.get("has_rag"):
            prompt += "- از اطلاعات هر دو منبع (پایگاه داده و اسناد) استفاده کن\n"
            prompt += "- اگر سوال نیاز به داده‌های دقیق دارد، از نتایج پایگاه داده استفاده کن\n"
            prompt += "- اگر نیاز به توضیح یا مفاهیم است، از اطلاعات اسناد استفاده کن\n"
            prompt += "- تمام ردیف‌ها یا دستگاه‌های موجود در نتایج پایگاه داده را با جزئیات کامل گزارش کن (هیچ سطری را حذف نکن)\n"
        elif fused_results.get("has_database"):
            prompt += "- از داده‌های پایگاه داده برای پاسخ استفاده کن\n"
            prompt += "- اعداد و داده‌ها را دقیق بیان کن\n"
            prompt += "- اگر چند ردیف یا دستگاه وجود دارد، تک‌تک آن‌ها را با مقادیرشان (مثلاً در قالب جدول یا فهرست) گزارش کن و چیزی را حذف نکن\n"
        else:
            prompt += "- از اطلاعات اسناد برای پاسخ استفاده کن\n"
        
        prompt += "- پاسخ باید کامل و دقیق باشد\n"
        prompt += "- اگر اطلاعات کافی نیست، صراحتاً بگو\n"
        
        return prompt
    
    def create_simple_answer_from_results(
        self,
        user_query: str,
        fused_results: Dict[str, Any],
        collection_name: str = 'budget_financial',
        field_names: Optional[List[str]] = None,
        year_was_defaulted: bool = False
    ) -> str:
        """ساخت پاسخ ساده بدون نیاز به LLM (fallback)
        
        Args:
            user_query: سوال کاربر (ممکن است enriched شده باشد)
            fused_results: نتایج ادغام شده
            year_was_defaulted: آیا سیستم سال پیش‌فرض (1403) را خودکار اضافه کرده است
            collection_name: نام کالکشن
            field_names: لیست ستون‌های مورد نظر برای نمایش (از _build_smart_field_names)
        """
        
        def _translate_column_name(col_name: str) -> str:
            """ترجمه نام ستون‌های انگلیسی به فارسی"""
            col_lower = col_name.lower()
            translations = {
                'total_amount': 'جمع کل',
                'total_current_cost': 'هزینه‌های جاری',
                'total_capital_cost': 'هزینه‌های سرمایه‌ای',
                'total_national': 'جمع ملی',
                'total_provincial': 'جمع استانی',
                'amount': 'مبلغ',
                'cost': 'هزینه',
                'income': 'درآمد'
            }
            # جستجوی دقیق
            if col_lower in translations:
                return translations[col_lower]
            # جستجوی شامل
            for en_key, fa_value in translations.items():
                if en_key in col_lower:
                    return fa_value
            return col_name
        
        def _format_numeric(value: Any) -> str:
            """تبدیل مقادیر عددی به نمایش خوانا"""
            if value is None:
                return "-"
            if isinstance(value, (int, float)):
                return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
            try:
                from decimal import Decimal
                if isinstance(value, Decimal):
                    return f"{value:,.0f}" if value == value.to_integral() else f"{float(value):,.2f}"
            except Exception:
                pass
            text = str(value).strip()
            cleaned = text.replace(',', '').replace('٬', '').replace(' ', '')
            if cleaned.isdigit():
                return f"{int(cleaned):,}"
            return text

        def _normalize_text(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            return value.replace('ي', 'ی').replace('ك', 'ک')

        def _parse_numeric(value: Any) -> Optional[float]:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = value.replace(',', '').replace('٬', '').replace(' ', '').strip()
                if cleaned == "":
                    return None
                try:
                    return float(cleaned)
                except Exception:
                    return None
            return None

        components = fused_results.get("components", [])
        database_component = next((comp for comp in components if comp.get("type") == "database"), None)
        database_results = None
        if database_component:
            database_results = database_component.get("database_results") or {}
        else:
            database_results = fused_results.get("database_results", {})
        
        # 🆕 DUAL SEARCH: اگر هر دو جدول منابع و مصارف جواب دادند، جواب ترکیبی بساز
        is_dual_search = fused_results.get('is_dual_search', False) or (database_results and database_results.get('dual_search', False))
        masaref_db = fused_results.get('masaref_result') or (database_results.get('masaref_result') if database_results else None)
        
        if is_dual_search and masaref_db:
            try:
                manabe_total = None
                masaref_total = None
                
                # استخراج total از منابع (درآمد)
                manabe_results = database_results.get('results') or database_results.get('rows', [])
                if manabe_results:
                    raw = manabe_results[0].get('total_amount')
                    if raw is not None:
                        try:
                            manabe_total = float(str(raw).replace(',', ''))
                        except Exception:
                            pass
                
                # استخراج total از مصارف (هزینه)
                masaref_results = masaref_db.get('results') or masaref_db.get('rows', [])
                if masaref_results:
                    raw = masaref_results[0].get('total_amount')
                    if raw is not None:
                        try:
                            masaref_total = float(str(raw).replace(',', ''))
                        except Exception:
                            pass
                
                has_manabe = manabe_total is not None and manabe_total > 0
                has_masaref = masaref_total is not None and masaref_total > 0
                
                # استخراج سال از query
                year_match = None
                import re
                year_pat = re.search(r'(1[34]\d{2}|99|98|97)', user_query)
                if year_pat:
                    y = year_pat.group(1)
                    year_match = '1399' if y == '99' else ('1398' if y == '98' else ('1397' if y == '97' else y))
                year_str = f" در سال {year_match}" if year_match else ""
                
                if has_manabe and has_masaref:
                    # هر دو نتیجه دارند
                    answer = f"اطلاعات مربوط به **{user_query.strip()}**{year_str}:\n\n"
                    answer += f"- **درآمد (منابع):** {manabe_total:,.0f} میلیون ریال\n"
                    answer += f"- **هزینه (مصارف):** {masaref_total:,.0f} میلیون ریال\n"
                    logger.info(f"✅ [DUAL-ANSWER] Both manabe ({manabe_total:,.0f}) and masaref ({masaref_total:,.0f}) found")
                    return answer
                elif has_manabe:
                    # فقط درآمد
                    logger.info(f"✅ [DUAL-ANSWER] Only manabe found ({manabe_total:,.0f}), using manabe answer")
                    # ادامه با جریان عادی از manabe
                elif has_masaref:
                    # فقط مصارف - جایگزین کردن database_results با masaref_db
                    logger.info(f"✅ [DUAL-ANSWER] Only masaref found ({masaref_total:,.0f}), switching to masaref")
                    database_results = masaref_db
            except Exception as dual_err:
                logger.warning(f"⚠️ [DUAL-ANSWER] Error building dual answer: {dual_err}")
        
        # ========== 🆕 COMPARISON / BALANCE: تشخیص نوع نتیجه ==========
        if database_results and database_results.get('success'):
            sql_results = database_results.get('results') or database_results.get('rows', [])
            if sql_results:
                first_row = sql_results[0] if sql_results else {}
                
                # --- تراز (balance) ---
                if 'balance_amount' in first_row:
                    try:
                        entity_name = first_row.get('entity_name', '')
                        income_amount = _parse_numeric(first_row.get('income_amount'))
                        expense_amount = _parse_numeric(first_row.get('expense_amount'))
                        balance_amount = _parse_numeric(first_row.get('balance_amount'))
                        balance_status = first_row.get('balance_status', '')
                        
                        # استخراج سال از query
                        import re
                        year_match = re.search(r'(1[34]\d{2})', user_query)
                        year_str = f" در سال {year_match.group(1)}" if year_match else ""
                        
                        answer = f"## تراز مالی **{entity_name}**{year_str}\n\n"
                        if income_amount is not None:
                            answer += f"- **درآمد (منابع):** {income_amount:,.0f} میلیون ریال\n"
                        if expense_amount is not None:
                            answer += f"- **مصارف (هزینه):** {expense_amount:,.0f} میلیون ریال\n"
                        if balance_amount is not None:
                            sign = "+" if balance_amount >= 0 else ""
                            answer += f"\n**تراز مالی:** {sign}{balance_amount:,.0f} میلیون ریال ({balance_status})\n"
                            if balance_amount >= 0:
                                answer += "\n✅ درآمدها بیشتر از مصارف است."
                            else:
                                answer += "\n⚠️ مصارف بیشتر از درآمدها است."
                        logger.info(f"✅ [BALANCE] Formatted balance answer for {entity_name}")
                        return answer
                    except Exception as bal_err:
                        logger.warning(f"⚠️ [BALANCE] Error formatting balance: {bal_err}")
                
                # --- مقایسه entity ها (entity_name column) ---
                elif 'entity_name' in first_row and len(sql_results) >= 2:
                    try:
                        # استخراج سال از query
                        import re
                        year_match = re.search(r'(1[34]\d{2})', user_query)
                        year_str = f" در سال {year_match.group(1)}" if year_match else ""
                        
                        # تشخیص ستون‌های مبلغ
                        has_national = 'total_national' in first_row
                        has_regional = 'total_regional' in first_row
                        has_total = 'total_amount' in first_row
                        
                        answer = f"## مقایسه{year_str}\n\n"
                        answer += "| موجودیت | "
                        if has_national:
                            answer += "درآمد ملی | "
                        if has_regional:
                            answer += "درآمد استانی | "
                        if has_total:
                            answer += "جمع کل | "
                        answer = answer.rstrip('| ') + " |\n"
                        answer += "| --- | "
                        if has_national:
                            answer += "--- | "
                        if has_regional:
                            answer += "--- | "
                        if has_total:
                            answer += "--- | "
                        answer = answer.rstrip('| ') + " |\n"
                        
                        for row in sql_results:
                            entity_n = row.get('entity_name', '-')
                            answer += f"| **{entity_n}** | "
                            if has_national:
                                nat_val = _parse_numeric(row.get('total_national'))
                                answer += f"{nat_val:,.0f} | " if nat_val is not None else "- | "
                            if has_regional:
                                reg_val = _parse_numeric(row.get('total_regional'))
                                answer += f"{reg_val:,.0f} | " if reg_val is not None else "- | "
                            if has_total:
                                tot_val = _parse_numeric(row.get('total_amount'))
                                answer += f"{tot_val:,.0f} | " if tot_val is not None else "- | "
                            answer = answer.rstrip('| ') + " |\n"
                        
                        # یافتن برنده (بیشترین total)
                        if has_total:
                            best_row = max(sql_results, key=lambda r: _parse_numeric(r.get('total_amount')) or 0)
                            best_entity = best_row.get('entity_name', '')
                            best_total = _parse_numeric(best_row.get('total_amount'))
                            if best_entity and best_total:
                                answer += f"\n**نتیجه مقایسه:** {best_entity} با مبلغ **{best_total:,.0f}** میلیون ریال بیشترین مقدار را دارد."
                        
                        logger.info(f"✅ [COMPARISON] Formatted comparison for {len(sql_results)} entities")
                        return answer
                    except Exception as comp_err:
                        logger.warning(f"⚠️ [COMPARISON] Error formatting comparison: {comp_err}")
        
        # 🎯 NEW: استفاده از Field-Specific Answer Generator
        # اگر collection_name بودجه است، از generator استفاده کن
        if 'budget' in collection_name.lower() or 'financial' in collection_name.lower():
            try:
                field_generator = get_field_answer_generator()
                
                # بهبود database_results با اطلاعات فیلد خاص
                if database_results and database_results.get('success'):
                    logger.info(f"🎯 [FIELD-SPECIFIC] Starting field-specific answer generation")
                    # 🎯 CRITICAL: استفاده از total_amount از SQL results که ستون detected رو داره
                    # نه detail_rows که تمام ستون‌ها رو داره و ممکنه گمراه‌کننده باشه
                    
                    sql_results = database_results.get('results') or database_results.get('rows', [])
                    detail_rows = database_results.get('detail_rows', [])
                    logger.info(f"🎯 [FIELD-SPECIFIC] sql_results count: {len(sql_results) if sql_results else 0}, detail_rows count: {len(detail_rows) if detail_rows else 0}")
                    
                    # اگر SQL results داریم، از total_amount استفاده کن
                    if sql_results and len(sql_results) >= 1 and 'total_amount' in sql_results[0]:
                        logger.info(f"🎯 [FIELD-SPECIFIC] Found total_amount in SQL results: {sql_results[0].get('total_amount')}")
                        
                        # 🔧 CRITICAL: چک کردن اینکه آیا چند سال داریم (GROUP BY year)
                        has_multiple_years = len(sql_results) > 1 and 'سال' in sql_results[0]
                        
                        # 🔧 FALLBACK: اگر SQL نتایج aggregated بدون GROUP BY year دارد
                        # ولی detail_rows شامل چند سال مختلف هستند
                        if not has_multiple_years and detail_rows:
                            detail_years = set()
                            for dr in detail_rows:
                                y = dr.get('سال')
                                if y:
                                    detail_years.add(str(y))
                            if len(detail_years) > 1:
                                has_multiple_years = True
                                logger.info(f"🎯 [FIELD-SPECIFIC] Multi-year detected from detail_rows: {sorted(detail_years)}")
                                
                                # محاسبه مجموع هر سال از detail_rows
                                # استخراج نام ستون مبلغ از SQL query
                                import re as _re
                                sql_query = database_results.get('sql', '')
                                amount_col_match = _re.search(r'CAST\("?([^"]+)"?\s+AS\s+DOUBLE', sql_query)
                                amount_col_name = amount_col_match.group(1) if amount_col_match else None
                                
                                if amount_col_name:
                                    # ساخت sql_results مجازی با GROUP BY year از detail_rows
                                    yearly_totals = {}
                                    for dr in detail_rows:
                                        y = str(dr.get('سال', ''))
                                        if not y:
                                            continue
                                        val = dr.get(amount_col_name)
                                        if val is not None:
                                            try:
                                                yearly_totals[y] = yearly_totals.get(y, 0) + float(str(val).replace(',', ''))
                                            except (ValueError, TypeError):
                                                pass
                                    
                                    # تبدیل به لیست مرتب شده
                                    sql_results = [
                                        {'سال': y, 'total_amount': yearly_totals[y]}
                                        for y in sorted(yearly_totals.keys())
                                    ]
                                    logger.info(f"🎯 [FIELD-SPECIFIC] Computed yearly totals from detail_rows: {len(sql_results)} years")
                        
                        if has_multiple_years:
                            # 🎯 Multi-year query: ساخت جدول با breakdown هر سال
                            logger.info(f"🎯 [FIELD-SPECIFIC] Multi-year query detected: {len(sql_results)} years")
                            
                            # استخراج نام فیلد از query
                            requested_field = field_generator.detect_requested_field(user_query, collection_name)
                            field_display_name = field_generator.get_field_display_name(requested_field)
                            
                            # 🔧 تشخیص نوع سوال: موضوعی (عنوان_جزء/بند/بخش) یا سازمانی (عنوان_دستگاه)
                            sql_query_text = database_results.get('sql', '')
                            
                            # 🔧 FIX: اگر query از جدول manabe است، field_display_name نباید فیلد masaref باشد
                            _is_manabe_for_field_my = 'manabe' in sql_query_text.lower()
                            _masaref_kws_my = ['تملک', 'تملك', 'اعتبارات', 'هزینه_ای', 'هزينه_اي', 'براورد', 'برآورد']
                            if _is_manabe_for_field_my and requested_field and any(kw in requested_field for kw in _masaref_kws_my):
                                logger.info(f"🔧 [FIELD-FIX-MY] Manabe multiyear query but masaref field '{requested_field}' → overriding to جمع_کل")
                                requested_field = 'جمع_کل'
                                field_display_name = 'جمع کل'
                            elif field_names and any(fn in ('جمع_کل', 'جمع_كل') for fn in field_names):
                                if requested_field not in ('جمع_کل', 'جمع_كل', 'ملی_جمع_کل', 'استانی_جمع_کل', 'جمع_در_آمد_عمومی', 'جمع_در_آمد_اختصاصی'):
                                    logger.info(f"🔧 [FIELD-FIX-MY] field_names has جمع_کل but detected '{requested_field}' → overriding")
                                    requested_field = 'جمع_کل'
                                    field_display_name = 'جمع کل'
                            _topic_cols = ['عنوان_جزء', 'عنوان_بند', 'عنوان_بخش', 'عنوان_قسمت']
                            _entity_cols = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي']
                            _has_topic_filter = any(col in sql_query_text for col in _topic_cols)
                            _has_entity_filter = any(col in sql_query_text for col in _entity_cols)
                            
                            # 🔧 FIX: استفاده از field_names برای تشخیص primary column (entity یا hierarchy)
                            primary_col_name = None
                            if field_names:
                                # جستجوی primary column در field_names
                                # اولویت: hierarchy columns (قسمت/بخش/بند/جزء) > entity columns (دستگاه)
                                hierarchy_cols = ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']
                                entity_cols = ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي']
                                
                                # ابتدا hierarchy را چک کن
                                for fn in field_names:
                                    if fn in hierarchy_cols:
                                        primary_col_name = fn
                                        logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Found hierarchy column in field_names: {primary_col_name}")
                                        break
                                
                                # اگر پیدا نشد، entity را چک کن
                                if not primary_col_name:
                                    for fn in field_names:
                                        if fn in entity_cols:
                                            primary_col_name = fn
                                            logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Found entity column in field_names: {primary_col_name}")
                                            break
                            
                            # استخراج subject مناسب
                            subject_name = None
                            if primary_col_name and detail_rows:
                                # استفاده از ستون مشخص شده در field_names
                                detail_row = detail_rows[0]
                                subject_name = detail_row.get(primary_col_name)
                                logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Using primary column from field_names: {primary_col_name} = {subject_name}")
                            elif _has_topic_filter and not _has_entity_filter and detail_rows:
                                # fallback: سوال موضوعی (از جزئی به کلی)
                                detail_row = detail_rows[0]
                                subject_name = (
                                    detail_row.get('عنوان_جزء') or
                                    detail_row.get('عنوان_بند') or
                                    detail_row.get('عنوان_بخش') or
                                    detail_row.get('عنوان_قسمت')
                                )
                                logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Topic-based query (fallback), subject: {subject_name}")
                            else:
                                # fallback: سوال سازمانی (از کلی به جزئی)
                                if detail_rows:
                                    # 🔧 FIX: پیدا کردن correct row که با query match می‌کند
                                    detail_row = detail_rows[0]  # default
                                    
                                    if len(detail_rows) > 1:
                                        # استخراج entity name از user query
                                        query_normalized = user_query.lower().replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
                                        
                                        # جستجوی بهترین match
                                        best_match_row = None
                                        best_match_score = 0
                                        
                                        for row in detail_rows:
                                            entity = (
                                                row.get('عنوان_دستگاه_اصلي') or 
                                                row.get('عنوان_دستگاه_اصلی') or
                                                row.get('عنوان_دستگاه_اجرايي') or
                                                row.get('عنوان_دستگاه_اجرایی') or
                                                ''
                                            )
                                            
                                            if entity:
                                                entity_normalized = entity.lower().replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
                                                
                                                # Exact match strategy
                                                if entity_normalized in query_normalized:
                                                    match_score = 1.0
                                                else:
                                                    entity_words = entity_normalized.split()
                                                    query_words = query_normalized.split()
                                                    first_word_match = len(entity_words) > 0 and entity_words[0] in query_words
                                                    
                                                    if first_word_match:
                                                        common_words = ['در', 'از', 'به', 'با', 'که', 'این', 'آن', 'و', 'یا']
                                                        entity_significant_words = [w for w in entity_words if len(w) > 2 and w not in common_words]
                                                        match_count = sum(1 for word in entity_significant_words if word in query_normalized)
                                                        match_score = (match_count / len(entity_significant_words)) * 0.8 if entity_significant_words else 0
                                                    else:
                                                        match_score = 0
                                                
                                                if match_score > best_match_score:
                                                    best_match_score = match_score
                                                    best_match_row = row
                                        
                                        if best_match_row and best_match_score >= 0.6:
                                            detail_row = best_match_row
                                            logger.info(f"✅ [FIELD-SPECIFIC-MULTIYEAR] Selected best matching entity (score={best_match_score:.2f})")
                                    
                                    if primary_col_name:
                                        # استفاده از ستون مشخص شده در field_names
                                        subject_name = detail_row.get(primary_col_name)
                                        logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Using primary column from field_names: {primary_col_name} = {subject_name}")
                                    else:
                                        # fallback: ابتدا اصلی بعد اجرایی
                                        subject_name = (
                                            detail_row.get('عنوان_دستگاه_اصلي') or 
                                            detail_row.get('عنوان_دستگاه_اصلی') or 
                                            detail_row.get('عنوان_دستگاه_اجرايي') or 
                                            detail_row.get('عنوان_دستگاه_اجرایی') or 
                                            detail_row.get('عنوان_دستگاه')
                                        )
                                        logger.info(f"🎯 [FIELD-SPECIFIC-MULTIYEAR] Entity-based query (fallback), device: {subject_name}")
                            
                            # تشخیص نوع بودجه (منابع/مصارف) برای multi-year
                            _sql_text_my = database_results.get('sql', '').lower()
                            _is_manabe_my = 'manabe' in _sql_text_my
                            _is_masaref_my = 'masaref' in _sql_text_my
                            _budget_type_my = 'منابع' if _is_manabe_my else ('مصارف' if _is_masaref_my else '')
                            # اگر نام فیلد از قبل حاوی نوع بودجه است (مثل "جمع منابع ملی")، آن را دوباره اضافه نکن
                            if _budget_type_my and _budget_type_my in field_display_name:
                                _full_label_my = field_display_name
                            elif _budget_type_my:
                                _full_label_my = f"{field_display_name} {_budget_type_my}".strip()
                            else:
                                _full_label_my = field_display_name
                            
                            # ساخت جدول
                            table_lines = []
                            if subject_name:
                                table_lines.append(f"{_full_label_my} **{subject_name}** در سال‌های مختلف:\n")
                            else:
                                table_lines.append(f"{_full_label_my} در سال‌های مختلف:\n")
                            table_lines.append("| سال | مقدار (میلیون ریال) |")
                            table_lines.append("|-----|---------------------|")
                            
                            # تجمیع مبالغ بر اساس سال (چند sub-agency در یک سال → یک ردیف)
                            yearly_totals: dict = {}
                            for row in sql_results:
                                year = str(row.get('سال', '') or '').strip()
                                if not year:
                                    continue
                                amount = row.get('total_amount', 0)
                                try:
                                    amount_float = float(amount) if amount else 0
                                except (ValueError, TypeError):
                                    amount_float = 0
                                yearly_totals[year] = yearly_totals.get(year, 0) + amount_float

                            grand_total = 0
                            for year in sorted(yearly_totals.keys()):
                                amount_float = yearly_totals[year]
                                grand_total += amount_float
                                formatted = f"{amount_float:,.0f}"
                                table_lines.append(f"| {year} | {formatted} |")

                            unique_years = len(yearly_totals)
                            # اضافه کردن جمع کل
                            table_lines.append(f"| **جمع کل {unique_years} سال** | **{grand_total:,.0f}** |")
                            
                            answer = "\n".join(table_lines)
                            
                            # اضافه کردن توضیح نوع بودجه برای multi-year
                            if _is_manabe_my:
                                answer += "\n\n> کلمه «درآمد» یا «منابع» در سوال، سیستم را به جدول **منابع** (درآمدهای عمومی دولت) هدایت کرده است."
                            elif _is_masaref_my:
                                answer += "\n\n> کلمه «هزینه» یا «مصارف» در سوال، سیستم را به جدول **مصارف** (اعتبارات هزینه‌ای) هدایت کرده است."
                            
                            answer += "\n\n### جزئیات:\n"
                            
                            logger.info(f"🎯 [FIELD-SPECIFIC] Generated multi-year answer with {len(sql_results)} rows")
                            return answer
                        
                        # Single year case: کد قبلی
                        # 🔧 FIX: اگر SQL چند row برگردانده (به خاطر GROUP BY عنوان_جزء و غیره)
                        # باید جمع تمام rows را محاسبه کنیم، نه فقط اولین row
                        if len(sql_results) > 1:
                            # محاسبه جمع تمام rows
                            total_amount = sum(
                                float(str(row.get('total_amount', 0) or 0).replace(',', ''))
                                for row in sql_results
                                if row.get('total_amount') is not None
                            )
                            logger.info(f"🎯 [FIELD-SPECIFIC] Computed sum of {len(sql_results)} rows: {total_amount}")
                        else:
                            total_amount = sql_results[0].get('total_amount')
                        
                        if total_amount is not None and detail_rows:
                            logger.info(f"🎯 [FIELD-SPECIFIC] All conditions met, generating answer...")
                            
                            # 🔧 FIX: پیدا کردن correct row از detail_rows که با query match می‌کند
                            # اگر چند entity داریم، باید اون یکی رو پیدا کنیم که user query کرده
                            detail_row = detail_rows[0]  # default
                            
                            if len(detail_rows) > 1:
                                # استخراج entity name از user query
                                import re
                                query_normalized = user_query.lower().replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
                                
                                # جستجوی بهترین match
                                best_match_row = None
                                best_match_score = 0
                                
                                for row in detail_rows:
                                    entity = (
                                        row.get('عنوان_دستگاه_اصلي') or 
                                        row.get('عنوان_دستگاه_اصلی') or
                                        row.get('عنوان_دستگاه_اجرايي') or
                                        row.get('عنوان_دستگاه_اجرایی') or
                                        ''
                                    )
                                    
                                    if entity:
                                        entity_normalized = entity.lower().replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
                                        
                                        # 🔧 CRITICAL: Exact match strategy
                                        # 1. Check if entity is substring of query (exact phrase match)
                                        if entity_normalized in query_normalized:
                                            match_score = 1.0  # perfect match
                                        # 2. Check first word match (type: سازمان vs وزارت vs موسسه)
                                        else:
                                            entity_words = entity_normalized.split()
                                            query_words = query_normalized.split()
                                            
                                            # First word should match (سازمان، وزارت، موسسه، etc.)
                                            first_word_match = len(entity_words) > 0 and entity_words[0] in query_words
                                            
                                            if first_word_match:
                                                # Count matching words (excluding common words)
                                                common_words = ['در', 'از', 'به', 'با', 'که', 'این', 'آن', 'و', 'یا']
                                                entity_significant_words = [w for w in entity_words if len(w) > 2 and w not in common_words]
                                                match_count = sum(1 for word in entity_significant_words if word in query_normalized)
                                                match_score = (match_count / len(entity_significant_words)) * 0.8 if entity_significant_words else 0
                                            else:
                                                match_score = 0
                                        
                                        logger.info(f"🎯 [FIELD-SPECIFIC] Entity match: '{entity[:50]}' score={match_score:.2f}")
                                        
                                        if match_score > best_match_score:
                                            best_match_score = match_score
                                            best_match_row = row
                                
                                if best_match_row and best_match_score >= 0.6:
                                    detail_row = best_match_row
                                    entity_name = (
                                        detail_row.get('عنوان_دستگاه_اصلي') or 
                                        detail_row.get('عنوان_دستگاه_اصلی') or
                                        ''
                                    )
                                    logger.info(f"✅ [FIELD-SPECIFIC] Selected best matching entity: '{entity_name}' (score={best_match_score:.2f})")
                                else:
                                    logger.warning(f"⚠️ [FIELD-SPECIFIC] No good match found (best={best_match_score:.2f}), using first row")
                            
                            # گرفتن اطلاعات از detail_row انتخاب شده
                            
                            # 🎯 استخراج نام فیلد از query
                            requested_field = field_generator.detect_requested_field(user_query, collection_name)
                            field_display_name = field_generator.get_field_display_name(requested_field)
                            logger.info(f"🎯 [FIELD-SPECIFIC] Detected field: {requested_field} -> {field_display_name}")
                            
                            # 🔧 FIX: اگر query از جدول manabe است، field_display_name نباید فیلد masaref باشد
                            # مثال: "واگذاری دارایی سرمایه‌ای" → detect_requested_field بر اساس کلمه "سرمایه"
                            # فیلد masaref "جمع تملک دارایی سرمایه‌ای" را برمی‌گرداند که اشتباه است
                            _sql_for_field_check = database_results.get('sql', '').lower()
                            _is_manabe_for_field = 'manabe' in _sql_for_field_check
                            _masaref_specific_keywords = ['تملک', 'تملك', 'اعتبارات', 'هزینه_ای', 'هزينه_اي', 'براورد', 'برآورد']
                            if _is_manabe_for_field and requested_field and any(kw in requested_field for kw in _masaref_specific_keywords):
                                logger.info(f"🔧 [FIELD-FIX] Manabe query but masaref field '{requested_field}' detected → overriding to جمع_کل")
                                requested_field = 'جمع_کل'
                                field_display_name = 'جمع کل'
                            # همچنین اگر field_names صراحتاً 'جمع_کل' دارد، به آن اعتماد کنیم
                            elif field_names and any(fn in ('جمع_کل', 'جمع_كل') for fn in field_names):
                                if requested_field not in ('جمع_کل', 'جمع_كل', 'ملی_جمع_کل', 'استانی_جمع_کل', 'جمع_در_آمد_عمومی', 'جمع_در_آمد_اختصاصی'):
                                    logger.info(f"🔧 [FIELD-FIX] field_names has جمع_کل but detected '{requested_field}' → overriding")
                                    requested_field = 'جمع_کل'
                                    field_display_name = 'جمع کل'
                            
                            # استفاده از total_amount به عنوان field_value
                            field_value = total_amount
                            logger.info(f"🎯 [FIELD-SPECIFIC] Using total_amount as field_value: {field_value}")
                            
                            if field_value is not None:
                                # فرمت کردن عدد
                                try:
                                    numeric_value = float(str(field_value).replace(',', ''))
                                    formatted_value = f"{numeric_value:,.0f}"
                                except (ValueError, TypeError):
                                    formatted_value = str(field_value)
                                
                                # 🔧 تشخیص نوع سوال: موضوعی یا سازمانی
                                sql_query_text = database_results.get('sql', '')
                                _topic_cols = ['عنوان_جزء', 'عنوان_بند', 'عنوان_بخش', 'عنوان_قسمت']
                                _entity_cols = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي']
                                _has_topic_filter = any(col in sql_query_text for col in _topic_cols)
                                _has_entity_filter = any(col in sql_query_text for col in _entity_cols)
                                
                                # 🔧 FIX: استفاده از field_names برای تشخیص primary column (entity یا hierarchy)
                                primary_col_name = None
                                if field_names:
                                    # جستجوی primary column در field_names
                                    # اولویت: hierarchy columns (قسمت/بخش/بند/جزء) > entity columns (دستگاه)
                                    hierarchy_cols = ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']
                                    entity_cols = ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي', 'عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي']
                                    
                                    # ابتدا hierarchy را چک کن
                                    for fn in field_names:
                                        if fn in hierarchy_cols:
                                            primary_col_name = fn
                                            logger.info(f"🎯 [FIELD-SPECIFIC] Found hierarchy column in field_names: {primary_col_name}")
                                            break
                                    
                                    # اگر پیدا نشد، entity را چک کن
                                    if not primary_col_name:
                                        for fn in field_names:
                                            if fn in entity_cols:
                                                primary_col_name = fn
                                                logger.info(f"🎯 [FIELD-SPECIFIC] Found entity column in field_names: {primary_col_name}")
                                                break
                                
                                subject_name = None
                                if primary_col_name:
                                    # استفاده از ستون مشخص شده در field_names
                                    subject_name = detail_row.get(primary_col_name)
                                    logger.info(f"🎯 [FIELD-SPECIFIC] Using primary column from field_names: {primary_col_name} = {subject_name}")
                                elif _has_topic_filter and not _has_entity_filter:
                                    # fallback: سوال موضوعی (از جزئی به کلی)
                                    subject_name = (
                                        detail_row.get('عنوان_جزء') or
                                        detail_row.get('عنوان_بند') or
                                        detail_row.get('عنوان_بخش') or
                                        detail_row.get('عنوان_قسمت')
                                    )
                                    logger.info(f"🎯 [FIELD-SPECIFIC] Using topic (fallback): {subject_name}")
                                else:
                                    # fallback: سوال سازمانی (از کلی به جزئی)
                                    subject_name = (
                                        detail_row.get('عنوان_دستگاه_اصلي') or 
                                        detail_row.get('عنوان_دستگاه_اصلی') or 
                                        detail_row.get('عنوان_دستگاه_اجرايي') or 
                                        detail_row.get('عنوان_دستگاه_اجرایی') or 
                                        detail_row.get('عنوان_دستگاه')
                                    )
                                    logger.info(f"🎯 [FIELD-SPECIFIC] Using entity (fallback): {subject_name}")
                                
                                year = detail_row.get('سال')
                                
                                # تشخیص نوع بودجه (منابع/مصارف) از SQL
                                _is_manabe = 'manabe' in sql_query_text.lower()
                                _is_masaref = 'masaref' in sql_query_text.lower()
                                _budget_type = 'منابع' if _is_manabe else ('مصارف' if _is_masaref else '')
                                # اگر نام فیلد از قبل حاوی نوع بودجه است (مثل "جمع منابع ملی")، آن را دوباره اضافه نکن
                                if _budget_type and _budget_type in field_display_name:
                                    _full_label = field_display_name
                                elif _budget_type:
                                    _full_label = f"{field_display_name} {_budget_type}".strip()
                                else:
                                    _full_label = field_display_name
                                
                                if subject_name and year:
                                    answer = f"{_full_label} **{subject_name}** در سال {year} مبلغ **{formatted_value}** میلیون ریال است."
                                elif subject_name:
                                    answer = f"{_full_label} **{subject_name}** مبلغ **{formatted_value}** میلیون ریال است."
                                elif year:
                                    answer = f"{_full_label} در سال {year} مبلغ **{formatted_value}** میلیون ریال است."
                                else:
                                    answer = f"{_full_label} مبلغ **{formatted_value}** میلیون ریال است."
                                
                                # اضافه کردن توضیحات reasoning
                                _context_notes = []
                                if _is_manabe:
                                    _context_notes.append("کلمه «درآمد» یا «منابع» در سوال، سیستم را به جدول **منابع** (درآمدهای عمومی دولت) هدایت کرده است.")
                                elif _is_masaref:
                                    _context_notes.append("کلمه «هزینه» یا «مصارف» در سوال، سیستم را به جدول **مصارف** (اعتبارات هزینه‌ای) هدایت کرده است.")
                                if year_was_defaulted and year:
                                    _context_notes.append(f"چون در سوال سالی ذکر نشده، سیستم به صورت خودکار **سال {year}** (آخرین سال موجود در پایگاه داده) را در نظر گرفته است.")
                                if _context_notes:
                                    answer += "\n\n> " + " | ".join(_context_notes)
                                
                                # اضافه کردن جدول جزئیات (اختیاری)
                                answer += "\n\n### جزئیات:\n\n"
                                
                                # 🔧 FIX: تشخیص نوع table (masaref vs manabe)
                                is_manabe_table = _is_manabe
                                is_masaref_table = _is_masaref
                                
                                if is_masaref_table:
                                    # برای masaref: نمایش breakdown هزینه‌ای/تملک
                                    all_important_fields = {
                                        'هزینه_ای': [
                                            'براورد_اعتبارات_هزینه_ای_عمومی',
                                            'برآورد_اعتبارات_هزینه_ای_متفرقه',
                                            'براورد_اعتبارات_هزینه_ای_اختصاصی',
                                            'جمع_براورد_اعتبارات_هزینه_ای',
                                        ],
                                        'تملک': [
                                            'براورد_تملك_دارايي_هاي_سرمايه_اي_ع',
                                            'براورد_تملك_دارايي_هاي_سرمايه_اي_م',
                                            'براورد_تملك_دارايي_هاي_سرمايه_اي_ا',
                                            'جمع_برآورد_تملك_دارايي_هاي_سرمايه_',
                                        ],
                                        'جمع_کل': ['جمع_كل']
                                    }
                                    
                                    # تشخیص نوع query از requested_field
                                    important_fields = []
                                    if 'هزینه' in requested_field or 'هزينه' in requested_field:
                                        important_fields = all_important_fields['هزینه_ای']
                                        logger.info(f"🎯 [DETAILS] Showing هزینه‌ای fields only")
                                    elif 'تملک' in requested_field or 'تملك' in requested_field or 'سرمایه' in requested_field or 'سرمايه' in requested_field:
                                        important_fields = all_important_fields['تملک']
                                        logger.info(f"🎯 [DETAILS] Showing تملک fields only")
                                    elif 'جمع' in requested_field or requested_field == 'جمع_كل':
                                        important_fields = all_important_fields['هزینه_ای'] + all_important_fields['تملک'] + all_important_fields['جمع_کل']
                                        logger.info(f"🎯 [DETAILS] Showing all fields (جمع کل query)")
                                    else:
                                        important_fields = all_important_fields['هزینه_ای'] + all_important_fields['تملک'] + all_important_fields['جمع_کل']
                                        logger.info(f"🎯 [DETAILS] Showing all fields (fallback)")
                                    
                                    # محاسبه جمع از همه detail_rows
                                    field_totals = {}
                                    for row in detail_rows:
                                        for field in important_fields:
                                            if field in row:
                                                value = row[field]
                                                if value is not None and value != '' and str(value).lower() not in ['null', 'none', '-']:
                                                    try:
                                                        numeric_value = float(str(value).replace(',', ''))
                                                        if numeric_value > 0:
                                                            field_totals[field] = field_totals.get(field, 0) + numeric_value
                                                    except (ValueError, TypeError):
                                                        pass
                                    
                                    # نمایش جمع‌های محاسبه شده
                                    for field in important_fields:
                                        if field in field_totals:
                                            total_value = field_totals[field]
                                            formatted_value = f"{total_value:,.0f}"
                                            display_name = field_generator.get_field_display_name(field)
                                            answer += f"- {display_name}: **{formatted_value}** میلیون ریال\n"
                                            logger.info(f"🎯 [FIELD-SPECIFIC] {field} total (from {len(detail_rows)} rows): {total_value:,.0f}")
                                
                                elif is_manabe_table and len(detail_rows) > 1:
                                    # 🆕 برای manabe: اگر چند row داریم، breakdown بر اساس entity/جزء نمایش بده
                                    # پیدا کردن جزئی‌ترین hierarchy column که متفاوت است
                                    hierarchy_cols = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اصلی', 'عنوان_جزء', 'عنوان_بند']
                                    breakdown_col = None
                                    
                                    for hcol in hierarchy_cols:
                                        if hcol in detail_rows[0]:
                                            # بررسی اینکه آیا این column مقادیر متفاوت دارد
                                            values = set()
                                            for row in detail_rows[:min(10, len(detail_rows))]:
                                                val = row.get(hcol)
                                                if val:
                                                    values.add(str(val).strip())
                                            
                                            if len(values) > 1:
                                                # این column breakdown خوبی است
                                                breakdown_col = hcol
                                                logger.info(f"🎯 [DETAILS-MANABE] Using breakdown column: {hcol} ({len(values)} unique values)")
                                                break
                                    
                                    if breakdown_col:
                                        # ساخت breakdown
                                        breakdown_totals = {}
                                        for row in detail_rows:
                                            key = row.get(breakdown_col, 'نامشخص')
                                            amount = row.get('جمع_کل') or row.get('ملی_جمع_کل') or 0
                                            try:
                                                amount_float = float(str(amount).replace(',', ''))
                                                if amount_float > 0:
                                                    breakdown_totals[key] = breakdown_totals.get(key, 0) + amount_float
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # نمایش top 10
                                        sorted_items = sorted(breakdown_totals.items(), key=lambda x: x[1], reverse=True)[:10]
                                        for name, amount in sorted_items:
                                            answer += f"- {name[:60]}: **{amount:,.0f}** میلیون ریال\n"
                                        
                                        if len(breakdown_totals) > 10:
                                            answer += f"\n*و {len(breakdown_totals) - 10} مورد دیگر...*\n"
                                        
                                        logger.info(f"🎯 [DETAILS-MANABE] Showed {len(sorted_items)} breakdown items")
                                    else:
                                        logger.info(f"🎯 [DETAILS-MANABE] No breakdown column found, skipping details")
                                else:
                                    logger.info(f"🎯 [DETAILS] Skipping details (manabe with single row or unknown table type)")
                                
                                return answer
                        
            except Exception as e:
                logger.warning(f"⚠️ Field-specific answer generation failed: {e}")
                import traceback
                logger.warning(traceback.format_exc())
                # fallback به روش قبلی

        primary_rows = database_results.get("rows") or database_results.get("results") or []
        primary_columns = database_results.get("columns", [])
        detail_rows = database_results.get("detail_rows") or []
        detail_columns = database_results.get("detail_columns") or []

        # اگر primary_rows موجود است، از آن استفاده کن (مخصوصاً برای Top-N queries)
        # فقط اگر primary_rows خالی باشد و detail_rows موجود باشد، از detail_rows استفاده می‌کنیم
        if primary_rows:
            rows = primary_rows
            columns = primary_columns
        elif detail_rows:
            use_detail_rows = len(detail_rows) <= max(50, len(primary_rows) * 10) if primary_rows else len(detail_rows) <= 50
            rows = detail_rows if use_detail_rows else primary_rows
            columns = detail_columns if use_detail_rows else primary_columns
        else:
            rows = []
            columns = []

        lines: List[str] = []

        if not rows and not columns:
            context = fused_results.get("context", "")
            if context:
                return context[:500] + "..." if len(context) > 500 else context
            return "متأسفانه نتوانستم اطلاعات کافی برای پاسخ به سوال شما پیدا کنم."

        row_count = len(rows)
        # 🔧 اگر count در database_results موجود باشد، از آن استفاده کن (تعداد واقعی)
        # count معمولاً تعداد ردیف‌های واقعی query است، نه تعداد ردیف‌های برگشتی که محدود شده‌اند
        actual_count = database_results.get("count")
        if actual_count is not None and actual_count != row_count:
            # استفاده از count به جای len(rows) چون count دقیق‌تر است
            row_count = actual_count
        if row_count:
            column_pairs: List[Tuple[str, str]] = []
            if columns:
                for col in columns:
                    # ابتدا ترجمه کن، بعد normalize
                    translated = _translate_column_name(col)
                    if translated == col:
                        # اگر ترجمه نشد، normalize کن
                        translated = _normalize_text(col).replace('_', ' ')
                    column_pairs.append((col, translated))

            # Prepare entity and total insights
            entity_keys = [
                "عنوان_دستگاه_اجرایی",
                "عنوان_دستگاه",
                "عنوان دستگاه اجرایی",
                "عنوان دستگاه",
                "دستگاه",
                "name",
                "title"
            ]
            total_columns: List[str] = []
            preferred_total_column: Optional[str] = None
            for original, display in column_pairs:
                normalized = _normalize_text(display).replace(" ", "")
                if "جمعکل" in normalized or "جمع_کل" in normalized or "جمعكل" in normalized:
                    total_columns.append(original)
                    is_plain_total = normalized.endswith("جمعکل") or normalized.endswith("جمع_کل")
                    is_prefixed_total = normalized.startswith("ملي") or normalized.startswith("ملی") or normalized.startswith("استاني") or normalized.startswith("استانی")
                    if is_plain_total and not is_prefixed_total and preferred_total_column is None:
                        preferred_total_column = original
                elif "جمعبراورد" in normalized or "جمعبراورداعتبارات" in normalized:
                    total_columns.append(original)
            if preferred_total_column is None and total_columns:
                preferred_total_column = total_columns[0]
            top_entity: Optional[str] = None
            top_total: Optional[float] = None
            overall_total: Optional[float] = None

            if preferred_total_column:
                overall_total = 0.0
                for row in rows:
                    numeric_value = _parse_numeric(row.get(preferred_total_column))
                    if numeric_value is None:
                        continue
                    overall_total += numeric_value
                    if top_total is None or numeric_value > top_total:
                        top_total = numeric_value
                        for key in entity_keys:
                            raw_name = row.get(key)
                            if isinstance(raw_name, str) and raw_name.strip():
                                top_entity = _normalize_text(raw_name.strip())
                                break

            aggregate_totals: Dict[str, float] = {}
            # استخراج aggregate totals از primary_rows یا rows
            source_rows = primary_rows if primary_rows else rows
            source_cols = primary_columns if primary_columns else columns
            
            if source_rows and source_cols:
                for aggregate_row in source_rows:
                    for col in source_cols:
                        value = aggregate_row.get(col)
                        numeric_value = _parse_numeric(value)
                        if numeric_value is None:
                            continue
                        # استفاده از نام اصلی ستون برای key
                        aggregate_totals[col] = aggregate_totals.get(col, 0.0) + numeric_value

            # تشخیص نوع query: aggregation یا list
            # اگر فقط یک row داریم و ستون‌های aggregation داریم، احتمالاً aggregation است
            has_aggregation_columns = any(
                'total_amount' in col.lower() or 
                'total_current_cost' in col.lower() or 
                'total_capital_cost' in col.lower()
                for col in columns
            )
            is_aggregation = (
                row_count == 1 and 
                (has_aggregation_columns or aggregate_totals) and
                not any(key in col.lower() for col in columns 
                       for key in ['عنوان_دستگاه', 'عنوان دستگاه', 'device'])
            )

            summary_bullets: List[str] = []
            
            if is_aggregation:
                # برای aggregation queries
                if aggregate_totals:
                    for col_name, total_value in aggregate_totals.items():
                        translated_col = _translate_column_name(col_name)
                        summary_bullets.append(
                            f"{translated_col}: **{_format_numeric(total_value)}**"
                        )
                elif overall_total:
                    summary_bullets.append(
                        f"جمع کل: **{_format_numeric(overall_total)}**"
                    )
                elif source_rows and source_cols:
                    # اگر فقط یک row aggregation داریم
                    agg_row = source_rows[0]
                    for col in source_cols:
                        value = agg_row.get(col)
                        numeric_value = _parse_numeric(value)
                        if numeric_value is not None:
                            translated_col = _translate_column_name(col)
                            summary_bullets.append(
                                f"{translated_col}: **{_format_numeric(numeric_value)}**"
                            )
            else:
                # برای list queries
                summary_bullets.append(f"{row_count} ردیف مالی مرتبط شناسایی شد.")
            if top_entity and top_total is not None:
                summary_bullets.append(
                    f"بیشترین مقدار ثبت شده مربوط به **{top_entity}** با مبلغ **{_format_numeric(top_total)}** است."
                )
            if overall_total:
                summary_bullets.append(
                    f"جمع کل مقادیر در این بازه برابر **{_format_numeric(overall_total)}** است."
                    )

            lines.append("### خلاصه پاسخ")
            for bullet in summary_bullets:
                lines.append(f"- {bullet}")
            lines.append("")

            lines.append("### نتایج پایگاه داده")
            lines.append("")
            if column_pairs:
                header = "| " + " | ".join(display for _, display in column_pairs) + " |"
                separator = "| " + " | ".join(["---"] * len(column_pairs)) + " |"
                lines.append(header)
                lines.append(separator)
                for row in rows:
                    values = []
                    for original, _ in column_pairs:
                        raw_value = row.get(original)
                        if isinstance(raw_value, str):
                            raw_value = _normalize_text(raw_value)
                        values.append(_format_numeric(raw_value))
                    lines.append("| " + " | ".join(values) + " |")
            else:
                for idx, row in enumerate(rows, 1):
                    normalized_row = {
                        _normalize_text(k): _normalize_text(v) if isinstance(v, str) else v
                        for k, v in row.items()
                    }
                    lines.append(f"- ردیف {idx}: {normalized_row}")

            lines.append("")
            lines.append(f"تعداد ردیف‌ها: **{row_count}**")

            summary_values: Dict[str, str] = {}
            summary_keywords = ["مجموع", "جمع"]
            for original_col, display_col in column_pairs:
                if not any(keyword in original_col for keyword in summary_keywords):
                    continue
                total = 0.0
                numeric_rows = 0
                for row in rows:
                    numeric_value = _parse_numeric(row.get(original_col))
                    if numeric_value is None:
                        continue
                    total += numeric_value
                    numeric_rows += 1
                if numeric_rows:
                    summary_values[_normalize_text(display_col)] = _format_numeric(total)

            if not summary_values and aggregate_totals:
                for col, total_value in aggregate_totals.items():
                    # ترجمه نام ستون
                    translated_col = _translate_column_name(col)
                    summary_values[translated_col] = _format_numeric(total_value)

            if summary_values:
                lines.append("\n### جمع‌بندی")
                for col, total in summary_values.items():
                    lines.append(f"- {col}: **{total}**")

        rag_component = next((comp for comp in components if comp.get("type") == "rag"), None)
        if rag_component:
            rag_content = rag_component.get("content", "")
            if rag_content:
                lines.append("\n### اطلاعات تکمیلی از اسناد")
                lines.append(rag_content[:500] + "..." if len(rag_content) > 500 else rag_content)

        return "\n".join(lines).strip()

