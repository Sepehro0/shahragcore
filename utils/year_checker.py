# -*- coding: utf-8 -*-
"""
Year Checker Utility for Budget Data
ابزار بررسی سال‌های موجود در داده‌های بودجه
"""

from typing import List, Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class YearChecker:
    """کلاس برای بررسی و مدیریت سال‌های موجود در dataset"""
    
    def __init__(self, chroma_client, collection_name: str = "budget_financial"):
        """
        Args:
            chroma_client: کلاینت ChromaDB
            collection_name: نام collection بودجه
        """
        self.chroma_client = chroma_client
        self.collection_name = collection_name
        self._available_years_cache: Optional[Set[str]] = None
    
    def get_available_years(self, force_refresh: bool = False) -> List[str]:
        """
        دریافت لیست سال‌های موجود در dataset
        
        Args:
            force_refresh: اگر True، cache را نادیده بگیر و مجدد بررسی کن
        
        Returns:
            لیست سال‌های موجود (مرتب شده)
        """
        # استفاده از cache
        if self._available_years_cache is not None and not force_refresh:
            return sorted(list(self._available_years_cache))
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # دریافت همه metadatas
            results = collection.get(
                include=["metadatas"],
                limit=50000  # حداکثر تعداد
            )
            
            years = set()
            if results and 'metadatas' in results:
                for metadata in results['metadatas']:
                    year = metadata.get('year', '')
                    if year:
                        years.add(str(year))
            
            # ذخیره در cache
            self._available_years_cache = years
            
            logger.info(f"✅ Found {len(years)} unique years in dataset: {sorted(years)}")
            return sorted(list(years))
            
        except Exception as e:
            logger.error(f"❌ Error getting available years: {e}")
            return []
    
    def is_year_available(self, year: str) -> bool:
        """
        بررسی اینکه آیا سال مورد نظر در dataset موجود است
        
        Args:
            year: سال (مثل "1403")
        
        Returns:
            True اگر سال موجود باشد
        """
        available_years = self.get_available_years()
        return str(year) in available_years
    
    def get_closest_year(self, target_year: str) -> Optional[str]:
        """
        یافتن نزدیک‌ترین سال موجود به سال مورد نظر
        
        Args:
            target_year: سال مورد نظر (مثل "1403")
        
        Returns:
            نزدیک‌ترین سال موجود یا None
        """
        available_years = self.get_available_years()
        
        if not available_years:
            return None
        
        try:
            target = int(target_year)
            available_ints = [int(y) for y in available_years]
            
            # یافتن نزدیک‌ترین
            closest = min(available_ints, key=lambda x: abs(x - target))
            
            return str(closest)
            
        except (ValueError, TypeError):
            # اگر تبدیل به عدد ممکن نبود، اولین سال موجود را برگردان
            return available_years[0] if available_years else None
    
    def get_year_range(self) -> Optional[Dict[str, str]]:
        """
        دریافت بازه سال‌های موجود (کمترین و بیشترین)
        
        Returns:
            دیکشنری شامل 'min' و 'max' یا None
        """
        available_years = self.get_available_years()
        
        if not available_years:
            return None
        
        try:
            year_ints = [int(y) for y in available_years]
            return {
                'min': str(min(year_ints)),
                'max': str(max(year_ints))
            }
        except (ValueError, TypeError):
            # اگر تبدیل ممکن نبود
            return {
                'min': available_years[0],
                'max': available_years[-1]
            }
    
    def suggest_alternative_year(self, requested_year: str) -> str:
        """
        پیشنهاد سال جایگزین اگر سال درخواستی موجود نیست
        
        Args:
            requested_year: سال درخواست شده
        
        Returns:
            پیام پیشنهاد با سال جایگزین
        """
        if self.is_year_available(requested_year):
            return f"سال {requested_year} در داده‌ها موجود است."
        
        closest = self.get_closest_year(requested_year)
        year_range = self.get_year_range()
        
        if not closest or not year_range:
            return f"متأسفانه سال {requested_year} در داده‌ها موجود نیست و سال جایگزینی یافت نشد."
        
        message = f"⚠️ سال {requested_year} در داده‌ها موجود نیست.\n\n"
        message += f"📅 سال‌های موجود: {year_range['min']} تا {year_range['max']}\n"
        message += f"💡 پیشنهاد: استفاده از سال {closest} (نزدیک‌ترین سال موجود)"
        
        return message
    
    def get_years_for_organization(
        self,
        organization_name: str,
        table_type: Optional[str] = None
    ) -> List[str]:
        """
        دریافت سال‌های موجود برای یک دستگاه خاص
        
        Args:
            organization_name: نام دستگاه
            table_type: نوع جدول ("expenses" یا "income" یا None برای هر دو)
        
        Returns:
            لیست سال‌های موجود برای آن دستگاه
        """
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # ساخت فیلتر
            where_filter = {}
            
            if table_type:
                where_filter["table_type"] = table_type
            
            # جستجو بر اساس نام دستگاه (هر دو فیلد)
            # Note: ChromaDB doesn't support OR in where clause directly
            # So we need to do two queries and merge
            
            years = set()
            
            # جستجو در main_organization
            try:
                where_main = dict(where_filter)
                where_main["main_organization"] = {"$contains": organization_name}
                
                results = collection.get(
                    where=where_main,
                    include=["metadatas"],
                    limit=10000
                )
                
                if results and 'metadatas' in results:
                    for metadata in results['metadatas']:
                        year = metadata.get('year', '')
                        if year:
                            years.add(str(year))
            except:
                pass
            
            # جستجو در executive_organization
            try:
                where_exec = dict(where_filter)
                where_exec["executive_organization"] = {"$contains": organization_name}
                
                results = collection.get(
                    where=where_exec,
                    include=["metadatas"],
                    limit=10000
                )
                
                if results and 'metadatas' in results:
                    for metadata in results['metadatas']:
                        year = metadata.get('year', '')
                        if year:
                            years.add(str(year))
            except:
                pass
            
            return sorted(list(years))
            
        except Exception as e:
            logger.error(f"❌ Error getting years for organization: {e}")
            return []
    
    def validate_year_request(
        self,
        requested_year: str,
        organization_name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        اعتبارسنجی درخواست سال و ارائه پیشنهادات
        
        Args:
            requested_year: سال درخواست شده
            organization_name: نام دستگاه (اختیاری)
        
        Returns:
            دیکشنری شامل وضعیت، پیام و پیشنهادات
        """
        result = {
            'is_valid': False,
            'message': '',
            'suggested_year': None,
            'available_years': []
        }
        
        # بررسی سال در کل dataset
        if self.is_year_available(requested_year):
            result['is_valid'] = True
            result['message'] = f"✅ سال {requested_year} در داده‌ها موجود است."
            
            # اگر دستگاه مشخص شده، بررسی کن که برای آن دستگاه هم موجود است
            if organization_name:
                org_years = self.get_years_for_organization(organization_name)
                if requested_year not in org_years:
                    result['is_valid'] = False
                    result['message'] = f"⚠️ سال {requested_year} برای {organization_name} موجود نیست."
                    result['available_years'] = org_years
                    if org_years:
                        closest = min(org_years, key=lambda x: abs(int(x) - int(requested_year)))
                        result['suggested_year'] = closest
                        result['message'] += f"\n💡 پیشنهاد: سال {closest}"
        else:
            result['is_valid'] = False
            closest = self.get_closest_year(requested_year)
            year_range = self.get_year_range()
            
            if closest and year_range:
                result['suggested_year'] = closest
                result['message'] = f"⚠️ سال {requested_year} در داده‌ها موجود نیست.\n"
                result['message'] += f"📅 بازه سال‌های موجود: {year_range['min']} - {year_range['max']}\n"
                result['message'] += f"💡 پیشنهاد: سال {closest}"
            else:
                result['message'] = f"❌ سال {requested_year} در داده‌ها موجود نیست."
        
        result['available_years'] = self.get_available_years()
        
        return result


# نمونه استفاده
if __name__ == "__main__":
    import chromadb
    
    client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
    checker = YearChecker(client, "budget_financial")
    
    # تست
    print("Available years:", checker.get_available_years())
    print("Year range:", checker.get_year_range())
    print("Is 1403 available?", checker.is_year_available("1403"))
    print("Closest to 1405:", checker.get_closest_year("1405"))

