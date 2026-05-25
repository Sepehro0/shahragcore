# -*- coding: utf-8 -*-
"""
Budget Calculator Utility
ابزار محاسبات بودجه (جمع، مقایسه، رشد درصدی)
"""

from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BudgetCalculator:
    """کلاس برای محاسبات بودجه"""
    
    def __init__(self, chroma_client, collection_name: str = "budget_financial"):
        """
        Args:
            chroma_client: کلاینت ChromaDB
            collection_name: نام collection بودجه
        """
        self.chroma_client = chroma_client
        self.collection_name = collection_name
    
    def sum_multiple_organizations(
        self,
        organization_names: List[str],
        year: str,
        budget_field: str = "grand_total",
        table_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        محاسبه مجموع بودجه چند دستگاه
        
        Args:
            organization_names: لیست نام دستگاه‌ها
            year: سال
            budget_field: فیلد بودجه (مثل "grand_total", "expense_total", ...)
            table_type: نوع جدول ("expenses" یا "income")
        
        Returns:
            دیکشنری شامل جمع کل و جزئیات هر دستگاه
        """
        result = {
            'total': 0.0,
            'details': [],
            'missing': [],
            'year': year,
            'field': budget_field
        }
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            for org_name in organization_names:
                # جستجو برای این دستگاه
                where_filter = {
                    "year": year
                }
                
                if table_type:
                    where_filter["table_type"] = table_type
                
                # جستجو در هر دو فیلد
                found = False
                org_value = 0.0
                
                # جستجو در main_organization
                try:
                    results = collection.get(
                        where={
                            **where_filter,
                            "main_organization": {"$contains": org_name}
                        },
                        include=["metadatas"],
                        limit=10
                    )
                    
                    if results and results.get('metadatas'):
                        for metadata in results['metadatas']:
                            value = metadata.get(budget_field, 0)
                            if value:
                                org_value += float(value)
                                found = True
                except:
                    pass
                
                # جستجو در executive_organization
                try:
                    results = collection.get(
                        where={
                            **where_filter,
                            "executive_organization": {"$contains": org_name}
                        },
                        include=["metadatas"],
                        limit=10
                    )
                    
                    if results and results.get('metadatas'):
                        for metadata in results['metadatas']:
                            value = metadata.get(budget_field, 0)
                            if value:
                                org_value += float(value)
                                found = True
                except:
                    pass
                
                if found:
                    result['details'].append({
                        'organization': org_name,
                        'value': org_value
                    })
                    result['total'] += org_value
                else:
                    result['missing'].append(org_name)
            
            logger.info(f"✅ Sum of {len(organization_names)} organizations: {result['total']:,.0f}")
            
        except Exception as e:
            logger.error(f"❌ Error calculating sum: {e}")
        
        return result
    
    def compare_years(
        self,
        organization_name: str,
        year1: str,
        year2: str,
        budget_field: str = "grand_total",
        table_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        مقایسه بودجه یک دستگاه در دو سال
        
        Args:
            organization_name: نام دستگاه
            year1: سال اول
            year2: سال دوم
            budget_field: فیلد بودجه
            table_type: نوع جدول
        
        Returns:
            دیکشنری شامل مقادیر هر سال، تفاوت و رشد درصدی
        """
        result = {
            'organization': organization_name,
            'year1': {
                'year': year1,
                'value': 0.0,
                'found': False
            },
            'year2': {
                'year': year2,
                'value': 0.0,
                'found': False
            },
            'difference': 0.0,
            'growth_rate': 0.0,
            'growth_percentage': '0%'
        }
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # دریافت مقدار برای سال اول
            value1 = self._get_organization_value(
                collection, organization_name, year1, budget_field, table_type
            )
            if value1 is not None:
                result['year1']['value'] = value1
                result['year1']['found'] = True
            
            # دریافت مقدار برای سال دوم
            value2 = self._get_organization_value(
                collection, organization_name, year2, budget_field, table_type
            )
            if value2 is not None:
                result['year2']['value'] = value2
                result['year2']['found'] = True
            
            # محاسبه تفاوت و رشد
            if result['year1']['found'] and result['year2']['found']:
                result['difference'] = value2 - value1
                
                if value1 > 0:
                    result['growth_rate'] = (value2 - value1) / value1
                    result['growth_percentage'] = f"{result['growth_rate'] * 100:.1f}%"
                
                logger.info(f"✅ Comparison: {year1}={value1:,.0f}, {year2}={value2:,.0f}, Growth={result['growth_percentage']}")
            
        except Exception as e:
            logger.error(f"❌ Error comparing years: {e}")
        
        return result
    
    def calculate_growth_rate(
        self,
        organization_name: str,
        years: List[str],
        budget_field: str = "grand_total",
        table_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        محاسبه نرخ رشد برای چند سال
        
        Args:
            organization_name: نام دستگاه
            years: لیست سال‌ها (مرتب شده)
            budget_field: فیلد بودجه
            table_type: نوع جدول
        
        Returns:
            دیکشنری شامل مقادیر هر سال و نرخ رشد سالانه
        """
        result = {
            'organization': organization_name,
            'years_data': [],
            'average_growth_rate': 0.0,
            'total_growth_rate': 0.0
        }
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # دریافت مقادیر برای تمام سال‌ها
            for year in years:
                value = self._get_organization_value(
                    collection, organization_name, year, budget_field, table_type
                )
                
                result['years_data'].append({
                    'year': year,
                    'value': value if value is not None else 0.0,
                    'found': value is not None
                })
            
            # محاسبه نرخ رشد بین سال‌ها
            growth_rates = []
            for i in range(1, len(result['years_data'])):
                prev = result['years_data'][i-1]
                curr = result['years_data'][i]
                
                if prev['found'] and curr['found'] and prev['value'] > 0:
                    growth = (curr['value'] - prev['value']) / prev['value']
                    result['years_data'][i]['growth_from_previous'] = growth
                    result['years_data'][i]['growth_percentage'] = f"{growth * 100:.1f}%"
                    growth_rates.append(growth)
            
            # محاسبه میانگین نرخ رشد
            if growth_rates:
                result['average_growth_rate'] = sum(growth_rates) / len(growth_rates)
                result['average_growth_percentage'] = f"{result['average_growth_rate'] * 100:.1f}%"
            
            # محاسبه نرخ رشد کل (از اولین به آخرین سال)
            if len(result['years_data']) >= 2:
                first = result['years_data'][0]
                last = result['years_data'][-1]
                
                if first['found'] and last['found'] and first['value'] > 0:
                    result['total_growth_rate'] = (last['value'] - first['value']) / first['value']
                    result['total_growth_percentage'] = f"{result['total_growth_rate'] * 100:.1f}%"
            
            logger.info(f"✅ Growth rate for {len(years)} years: avg={result.get('average_growth_percentage', 'N/A')}")
            
        except Exception as e:
            logger.error(f"❌ Error calculating growth rate: {e}")
        
        return result
    
    def _get_organization_value(
        self,
        collection,
        organization_name: str,
        year: str,
        budget_field: str,
        table_type: Optional[str]
    ) -> Optional[float]:
        """
        دریافت مقدار بودجه یک دستگاه در یک سال
        
        Returns:
            مقدار یا None اگر یافت نشد
        """
        where_filter = {"year": year}
        if table_type:
            where_filter["table_type"] = table_type
        
        total_value = 0.0
        found = False
        
        # جستجو در main_organization
        try:
            results = collection.get(
                where={
                    **where_filter,
                    "main_organization": {"$contains": organization_name}
                },
                include=["metadatas"],
                limit=10
            )
            
            if results and results.get('metadatas'):
                for metadata in results['metadatas']:
                    value = metadata.get(budget_field, 0)
                    if value:
                        total_value += float(value)
                        found = True
        except:
            pass
        
        # جستجو در executive_organization
        try:
            results = collection.get(
                where={
                    **where_filter,
                    "executive_organization": {"$contains": organization_name}
                },
                include=["metadatas"],
                limit=10
            )
            
            if results and results.get('metadatas'):
                for metadata in results['metadatas']:
                    value = metadata.get(budget_field, 0)
                    if value:
                        total_value += float(value)
                        found = True
        except:
            pass
        
        return total_value if found else None
    
    def format_comparison_report(self, comparison: Dict[str, any]) -> str:
        """
        فرمت کردن گزارش مقایسه برای نمایش
        
        Args:
            comparison: نتیجه تابع compare_years
        
        Returns:
            متن فرمت شده
        """
        report = f"📊 مقایسه بودجه {comparison['organization']}\n\n"
        
        year1 = comparison['year1']
        year2 = comparison['year2']
        
        if year1['found']:
            report += f"سال {year1['year']}: {year1['value']:,.0f} میلیون ریال\n"
        else:
            report += f"سال {year1['year']}: داده موجود نیست\n"
        
        if year2['found']:
            report += f"سال {year2['year']}: {year2['value']:,.0f} میلیون ریال\n\n"
        else:
            report += f"سال {year2['year']}: داده موجود نیست\n\n"
        
        if year1['found'] and year2['found']:
            diff = comparison['difference']
            growth = comparison['growth_percentage']
            
            if diff > 0:
                report += f"📈 افزایش: {diff:,.0f} میلیون ریال ({growth})\n"
            elif diff < 0:
                report += f"📉 کاهش: {abs(diff):,.0f} میلیون ریال ({growth})\n"
            else:
                report += f"➡️ بدون تغییر\n"
        
        return report


# نمونه استفاده
if __name__ == "__main__":
    import chromadb
    
    client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
    calculator = BudgetCalculator(client, "budget_financial")
    
    # تست جمع
    result = calculator.sum_multiple_organizations(
        ["وزارت علوم", "وزارت نفت"],
        "1403",
        "grand_total"
    )
    print("Sum result:", result)
    
    # تست مقایسه
    comparison = calculator.compare_years(
        "وزارت علوم",
        "1402",
        "1403"
    )
    print("Comparison:", comparison)
    print(calculator.format_comparison_report(comparison))

