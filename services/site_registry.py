# -*- coding: utf-8 -*-
"""
Site Registry — Registry for site-specific extraction strategies
ثبت و مدیریت استراتژی‌های استخراج برای سایت‌های خاص

ایده:
- هر سایت می‌تواند یک handler اختصاصی داشته باشد
- اگر handler وجود نداشته باشد، generic extraction استفاده می‌شود
- handler ها می‌توانند API endpoints، CSS selectors خاص و ... تعریف کنند
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin

import httpx

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SiteConfig:
    """
    تنظیمات استخراج برای یک سایت خاص.
    """
    # شناسه سایت (مثلاً 'zoomit', 'digikala')
    site_id: str
    
    # Domain patterns برای شناسایی (مثلاً ['zoomit.ir', 'www.zoomit.ir'])
    domains: List[str]
    
    # آیا این سایت SPA است و نیاز به browser دارد؟
    requires_browser: bool = False
    
    # آیا این سایت API جداگانه دارد؟
    has_api: bool = False
    
    # URL base برای API (در صورت وجود)
    api_base: Optional[str] = None
    
    # تابع async برای fetch محصولات از API (در صورت وجود)
    api_fetcher: Optional[Callable] = None
    
    # CSS selectors اختصاصی برای محصولات
    product_selectors: List[str] = field(default_factory=list)
    
    # Price selectors اختصاصی
    price_selectors: List[str] = field(default_factory=list)
    
    # آیا از JSON-LD استفاده می‌کند؟
    uses_jsonld: bool = True
    
    # آیا از Microdata استفاده می‌کند؟
    uses_microdata: bool = True
    
    # الگوهای استخراج قیمت (regex)
    price_patterns: List[str] = field(default_factory=list)
    
    # Mapping برای تبدیل مقادیر
    field_mappings: Dict[str, str] = field(default_factory=dict)
    
    # حداکثر تعداد محصولات برای fetch
    max_products: int = 500


@dataclass
class ExtractionResult:
    """
    نتیجه استخراج از یک صفحه یا سایت.
    """
    items: List[Dict[str, Any]]
    source: str  # 'api', 'jsonld', 'microdata', 'css', 'price_pattern', 'browser'
    confidence: float  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Built-in Site Handlers
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch_zoomit_products(max_per_category: int = 100) -> List[Dict[str, Any]]:
    """
    Handler اختصاصی برای زومیت - fetch محصولات از API.
    """
    pages: List[Dict[str, Any]] = []
    
    # دسته‌بندی‌های اصلی
    categories = [
        ("1", "گوشی"), ("9", "لپ‌تاپ"), ("3", "تبلت"),
        ("4", "ساعت هوشمند"), ("10", "کنسول بازی"), ("18", "هدفون"),
        ("14", "کارت گرافیک"), ("11", "تلویزیون"), ("6", "دوربین عکاسی"),
        ("12", "مانیتور"), ("13", "پردازنده"), ("20", "اس اس دی"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.zoomit.ir/",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        for cat_id, cat_name in categories:
            try:
                r = await client.get(
                    "https://api2.zoomit.ir/catalog/api/search/category",
                    params={"categoryId": cat_id, "size": max_per_category},
                )
                if r.status_code != 200:
                    continue
                items = r.json()
                if not isinstance(items, list):
                    continue
                
                for item in items:
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue
                    
                    english_title = (item.get("englishTitle") or "").strip()
                    slug = (item.get("slug") or "").strip()
                    min_price = item.get("minPrice")
                    brand = item.get("brand") or {}
                    brand_name = (brand.get("title") or "") if isinstance(brand, dict) else ""
                    
                    price_str = ""
                    if min_price and min_price > 0:
                        price_str = f"از {int(min_price):,} تومان"
                    
                    specs = []
                    for spec in item.get("keySpecifications") or []:
                        pv = (spec.get("primaryValue") or "").strip()
                        if pv:
                            specs.append(pv)
                    
                    product_url = f"https://www.zoomit.ir/product/{slug}/" if slug else ""
                    full_title = f"{title} ({english_title})" if english_title else title
                    
                    pages.append({
                        "url": product_url,
                        "content": f"{full_title} — برند: {brand_name} — دسته: {cat_name} — {price_str} — {' | '.join(specs[:3])}",
                        "metadata": {
                            "title": title,
                            "page_product_title": title,
                            "page_product_price": price_str,
                            "brand": brand_name,
                            "category": cat_name,
                            "source_type": "api",
                        },
                        "_structured_items": [{
                            "title": full_title,
                            "price": price_str,
                            "description": f"برند: {brand_name} | {' | '.join(specs[:3])}",
                            "link": product_url,
                        }],
                    })
                
                logger.info(f"  Zoomit API: {len(items)} from '{cat_name}'")
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"  Zoomit category '{cat_name}' failed: {e}")
    
    return pages


# ──────────────────────────────────────────────────────────────────────────────
# Site Registry
# ──────────────────────────────────────────────────────────────────────────────

class SiteRegistry:
    """
    Registry برای مدیریت سایت‌های خاص و استراتژی‌های extraction.
    """
    
    _instance: Optional['SiteRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._sites: Dict[str, SiteConfig] = {}
        self._domain_map: Dict[str, str] = {}  # domain -> site_id
        
        # ثبت سایت‌های built-in
        self._register_builtin_sites()
    
    def _register_builtin_sites(self):
        """ثبت سایت‌های شناخته‌شده."""
        
        # Zoomit
        self.register(SiteConfig(
            site_id="zoomit",
            domains=["zoomit.ir", "www.zoomit.ir"],
            requires_browser=True,
            has_api=True,
            api_base="https://api2.zoomit.ir",
            api_fetcher=_fetch_zoomit_products,
            product_selectors=[
                "div[class*='product']", "article[class*='product']",
                "div[class*='card']", "a[href*='/product/']",
            ],
            price_patterns=[r'[\d٬,]+\s*تومان', r'از\s*[\d٬,]+\s*تومان'],
            max_products=1000,
        ))
        
        # Digikala (generic - no special handler yet)
        self.register(SiteConfig(
            site_id="digikala",
            domains=["digikala.com", "www.digikala.com"],
            requires_browser=True,
            has_api=False,
            uses_jsonld=True,
            product_selectors=[
                "div[class*='product-list_ProductList']",
                "article[data-testid='product-card']",
                "a[href*='/product/dkp-']",
            ],
            price_patterns=[r'[\d٬,]+\s*تومان'],
            price_selectors=["span[data-testid='price']", "div[class*='price']"],
        ))
        
        # Torob
        self.register(SiteConfig(
            site_id="torob",
            domains=["torob.com", "www.torob.com"],
            requires_browser=False,
            uses_jsonld=True,
            product_selectors=[
                "div[class*='product']", "a[href*='/product/']",
            ],
            price_patterns=[r'[\d٬,]+\s*تومان'],
        ))
        
        # Amazon (generic)
        self.register(SiteConfig(
            site_id="amazon",
            domains=["amazon.com", "www.amazon.com", "amazon.ir"],
            requires_browser=False,
            uses_jsonld=True,
            uses_microdata=True,
            product_selectors=[
                "div[data-component-type='s-search-result']",
                "div[data-asin]",
            ],
            price_patterns=[r'\$[\d,]+', r'[\d,]+\s*USD'],
        ))
        
        # Generic (catch-all)
        # این در register نشود - برای fallback استفاده می‌شود
    
    def register(self, config: SiteConfig):
        """ثبت یک سایت جدید."""
        self._sites[config.site_id] = config
        for domain in config.domains:
            normalized = domain.lower().lstrip("www.")
            self._domain_map[normalized] = config.site_id
            # همچنین www دار را هم ثبت کن
            self._domain_map[f"www.{normalized}"] = config.site_id
        logger.info(f"📝 Registered site: {config.site_id} (domains: {config.domains})")
    
    def get_site(self, site_id: str) -> Optional[SiteConfig]:
        """دریافت config یک سایت."""
        return self._sites.get(site_id)
    
    def detect_site(self, url: str) -> Optional[SiteConfig]:
        """
        شناسایی سایت از روی URL.
        Returns SiteConfig یا None برای سایت‌های ناشناس.
        """
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            
            # مستقیم
            if host in self._domain_map:
                return self._sites.get(self._domain_map[host])
            
            # بدون www
            host_no_www = host.lstrip("www.")
            if host_no_www in self._domain_map:
                return self._sites.get(self._domain_map[host_no_www])
            
            # جستجوی partial (مثلاً subdomain.zoomit.ir)
            for domain, site_id in self._domain_map.items():
                if host.endswith(domain) or domain in host:
                    return self._sites.get(site_id)
            
            return None
        except Exception:
            return None
    
    def has_api_handler(self, url: str) -> bool:
        """آیا این سایت handler API دارد؟"""
        config = self.detect_site(url)
        return config is not None and config.has_api and config.api_fetcher is not None
    
    async def fetch_via_api(self, url: str, max_items: int = 500) -> Optional[List[Dict[str, Any]]]:
        """
        تلاش برای fetch محصولات از API سایت (در صورت وجود handler).
        """
        config = self.detect_site(url)
        if not config or not config.api_fetcher:
            return None
        
        try:
            logger.info(f"  🛍️ Using API handler for {config.site_id}")
            result = await config.api_fetcher(max_per_category=min(100, max_items // 10))
            return result
        except Exception as e:
            logger.warning(f"  ⚠️ API handler failed for {config.site_id}: {e}")
            return None
    
    def get_product_selectors(self, url: str) -> List[str]:
        """دریافت CSS selectors برای محصولات."""
        config = self.detect_site(url)
        if config and config.product_selectors:
            return config.product_selectors
        return [
            "div.product", "div[class*='product']", "article.product",
            "div[class*='card']", "li[class*='product']",
            "div[class*='item']", "div[class*='listing']",
            "div[class*='ProductCard']", "div[class*='product-card']",
            "article", "div[class*='post']",
        ]
    
    def get_price_patterns(self, url: str) -> List[str]:
        """دریافت الگوهای قیمت."""
        config = self.detect_site(url)
        if config and config.price_patterns:
            return config.price_patterns
        return [
            r'[\d,]{3,}\s*تومان',
            r'[\d,]{3,}\s*ریال',
            r'\$[\d,]+',
            r'[\d,]+\s*[€£]',
        ]


# Singleton
def get_site_registry() -> SiteRegistry:
    return SiteRegistry()


# ──────────────────────────────────────────────────────────────────────────────
# Smart Detection Functions
# ──────────────────────────────────────────────────────────────────────────────

def detect_site_type(html: str, url: str) -> Dict[str, Any]:
    """
    شناسایی نوع سایت و قابلیت‌های آن از روی HTML.
    Returns: {
        'is_ecommerce': bool,
        'is_blog': bool,
        'is_news': bool,
        'has_jsonld': bool,
        'has_microdata': bool,
        'has_products': bool,
        'detected_patterns': list,
    }
    """
    from bs4 import BeautifulSoup
    
    result = {
        'is_ecommerce': False,
        'is_blog': False,
        'is_news': False,
        'has_jsonld': False,
        'has_microdata': False,
        'has_products': False,
        'detected_patterns': [],
    }
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # JSON-LD
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        if jsonld_scripts:
            result['has_jsonld'] = True
            for script in jsonld_scripts[:5]:
                try:
                    data = json.loads(script.string or '{}')
                    types = []
                    if isinstance(data, dict):
                        types = [data.get('@type', '')]
                    elif isinstance(data, list):
                        types = [d.get('@type', '') for d in data if isinstance(d, dict)]
                    
                    for t in types:
                        if t in ['Product', 'ItemList', 'Offer']:
                            result['is_ecommerce'] = True
                            result['has_products'] = True
                            result['detected_patterns'].append(f'jsonld:{t}')
                        if t in ['Article', 'NewsArticle', 'BlogPosting']:
                            result['is_blog'] = True
                            result['is_news'] = t == 'NewsArticle'
                            result['detected_patterns'].append(f'jsonld:{t}')
                except:
                    pass
        
        # Microdata
        microdata = soup.find_all(attrs={'itemtype': True})
        if microdata:
            result['has_microdata'] = True
            for el in microdata[:10]:
                itemtype = el.get('itemtype', '')
                if 'Product' in itemtype or 'Offer' in itemtype:
                    result['is_ecommerce'] = True
                    result['has_products'] = True
                    result['detected_patterns'].append('microdata:Product')
                if 'Article' in itemtype:
                    result['is_blog'] = True
                    result['detected_patterns'].append('microdata:Article')
        
        # Price patterns
        text = soup.get_text(' ', strip=True)
        if re.search(r'[\d٬,]{4,}\s*تومان', text):
            result['is_ecommerce'] = True
            result['has_products'] = True
            result['detected_patterns'].append('price:toman')
        if re.search(r'\$[\d,]{2,}', text):
            result['is_ecommerce'] = True
            result['has_products'] = True
            result['detected_patterns'].append('price:dollar')
        
        # E-commerce signals
        ecommerce_signals = [
            'add-to-cart', 'add to cart', 'افزودن به سبد',
            'خرید', 'قیمت', 'تومان', 'سبد خرید',
            'checkout', 'cart', 'shop', 'store',
        ]
        text_lower = text.lower()
        for signal in ecommerce_signals:
            if signal in text_lower:
                result['is_ecommerce'] = True
                result['detected_patterns'].append(f'keyword:{signal}')
                break
        
        # Blog/News signals
        blog_signals = ['blog', 'مقاله', 'نویسنده', 'author', 'published']
        news_signals = ['news', 'خبر', 'breaking', 'اخبار']
        
        for signal in blog_signals:
            if signal in text_lower:
                result['is_blog'] = True
                break
        for signal in news_signals:
            if signal in text_lower:
                result['is_news'] = True
                break
        
    except Exception as e:
        logger.debug(f"Site type detection failed: {e}")
    
    return result


async def detect_api_endpoints(url: str) -> List[Dict[str, Any]]:
    """
    تلاش برای کشف API endpoints از روی URL.
    برمی‌گرداند: [{'url': str, 'type': str, 'confidence': float}, ...]
    """
    results = []
    
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common API patterns
        api_patterns = [
            "/api/products",
            "/api/v1/products",
            "/api/catalog",
            "/api/search",
            "/api/items",
            "/api/list",
            "/graphql",
            "/v1/products",
            "/v2/products",
        ]
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for pattern in api_patterns:
                test_url = urljoin(base, pattern)
                try:
                    r = await client.head(test_url)
                    if r.status_code in [200, 401, 403, 405]:
                        results.append({
                            'url': test_url,
                            'type': 'api',
                            'confidence': 0.7 if r.status_code == 200 else 0.4,
                        })
                except:
                    pass
    
    except Exception as e:
        logger.debug(f"API detection failed: {e}")
    
    return results
