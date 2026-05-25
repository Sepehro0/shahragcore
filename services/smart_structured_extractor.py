# -*- coding: utf-8 -*-
"""
Smart Structured Data Extractor
استخراج هوشمند داده‌های ساختاریافته از صفحات وب

این ماژول یک layered approach دارد:
1. Site-specific API handlers (اگر سایت شناخته شده باشد)
2. JSON-LD extraction
3. Microdata extraction
4. Open Graph / Meta tags
5. CSS selectors (product cards)
6. Price pattern matching
7. Browser rendering fallback (crawl4ai)

هر لایه نتایج خود را با confidence برمی‌گرداند.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)


class SmartStructuredDataExtractor:
    """
    استخراج‌کننده هوشمند داده‌های ساختاریافته.
    از چندین استراتژی با fallback استفاده می‌کند.
    """
    
    def __init__(self):
        from services.site_registry import get_site_registry
        self.registry = get_site_registry()
        self._browser_instance = None
        self._browser_lock = None
    
    async def extract_from_url(
        self,
        url: str,
        html: Optional[str] = None,
        max_items: int = 100,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        استخراج محصولات/آیتم‌ها از یک URL.
        
        Returns:
            (items, metadata)
            items: لیست {title, price, link, description, image}
            metadata: {source, confidence, methods_tried, ...}
        """
        metadata = {
            'url': url,
            'methods_tried': [],
            'final_method': None,
            'confidence': 0.0,
        }
        
        items = []
        
        # ── Layer 1: Site-specific API handler ─────────────────────────────
        if self.registry.has_api_handler(url):
            metadata['methods_tried'].append('site_api')
            try:
                api_items = await self.registry.fetch_via_api(url, max_items)
                if api_items:
                    items = api_items
                    metadata['final_method'] = 'site_api'
                    metadata['confidence'] = 0.95
                    logger.info(f"  ✅ Site API: {len(items)} items for {url}")
                    return items, metadata
            except Exception as e:
                logger.debug(f"  Site API failed: {e}")
        
        # اگر HTML نداریم، fetch کن
        if not html:
            html = await self._fetch_html(url)
        
        if not html:
            metadata['error'] = 'Could not fetch HTML'
            return [], metadata
        
        # ── Layer 2: JSON-LD ───────────────────────────────────────────────
        metadata['methods_tried'].append('jsonld')
        jsonld_items = self._extract_jsonld(html, url)
        if jsonld_items:
            items.extend(jsonld_items)
            metadata['final_method'] = 'jsonld'
            metadata['confidence'] = 0.90
            logger.info(f"  ✅ JSON-LD: {len(jsonld_items)} items")
            # ادامه نده اگر محصولات کافی داریم
            if len(items) >= max_items:
                return items[:max_items], metadata
        
        # ── Layer 3: Microdata ─────────────────────────────────────────────
        metadata['methods_tried'].append('microdata')
        microdata_items = self._extract_microdata(html, url)
        if microdata_items:
            # فقط آیتم‌های جدید را اضافه کن
            existing_titles = {i.get('title', '').lower() for i in items}
            for item in microdata_items:
                if item.get('title', '').lower() not in existing_titles:
                    items.append(item)
            if not metadata['final_method']:
                metadata['final_method'] = 'microdata'
                metadata['confidence'] = 0.80
            logger.info(f"  ✅ Microdata: {len(microdata_items)} items")
            if len(items) >= max_items:
                return items[:max_items], metadata
        
        # ── Layer 4: Open Graph / Meta ─────────────────────────────────────
        if len(items) < max_items:
            metadata['methods_tried'].append('meta')
            meta_item = self._extract_from_meta(html, url)
            if meta_item:
                items.append(meta_item)
                if not metadata['final_method']:
                    metadata['final_method'] = 'meta'
                    metadata['confidence'] = 0.60
        
        # ── Layer 5: CSS Selectors (Product Cards) ─────────────────────────
        if len(items) < max_items:
            metadata['methods_tried'].append('css_selectors')
            css_items = self._extract_from_css(html, url)
            if css_items:
                existing_titles = {i.get('title', '').lower() for i in items}
                for item in css_items:
                    if item.get('title', '').lower() not in existing_titles:
                        items.append(item)
                if not metadata['final_method']:
                    metadata['final_method'] = 'css_selectors'
                    metadata['confidence'] = 0.50
                logger.info(f"  ✅ CSS: {len(css_items)} items")
        
        # ── Layer 6: Price Pattern Matching ───────────────────────────────
        if len(items) < max_items:
            metadata['methods_tried'].append('price_patterns')
            price_items = self._extract_from_price_patterns(html, url)
            if price_items:
                existing_titles = {i.get('title', '').lower() for i in items}
                for item in price_items:
                    if item.get('title', '').lower() not in existing_titles:
                        items.append(item)
                if not metadata['final_method']:
                    metadata['final_method'] = 'price_patterns'
                    metadata['confidence'] = 0.35
        
        # ── Layer 7: Browser Rendering Fallback ───────────────────────────
        if len(items) < 3 and self._is_likely_spa(html):
            metadata['methods_tried'].append('browser_render')
            browser_items = await self._extract_with_browser(url)
            if browser_items:
                items.extend(browser_items)
                if not metadata['final_method']:
                    metadata['final_method'] = 'browser_render'
                    metadata['confidence'] = 0.45
                logger.info(f"  ✅ Browser: {len(browser_items)} items")
        
        return items[:max_items], metadata
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML with httpx."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    return r.text
        except Exception as e:
            logger.debug(f"Fetch failed for {url}: {e}")
        return None
    
    def _extract_jsonld(self, html: str, url: str) -> List[Dict[str, Any]]:
        """استخراج از JSON-LD تگ‌ها."""
        items = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw = script.string or script.get_text()
                    if not raw:
                        continue
                    data = json.loads(raw)
                    
                    if isinstance(data, list):
                        ld_items = data
                    elif isinstance(data, dict):
                        # ممکن است @graph داشته باشد
                        if '@graph' in data:
                            ld_items = data['@graph']
                        else:
                            ld_items = [data]
                    else:
                        continue
                    
                    for obj in ld_items:
                        if not isinstance(obj, dict):
                            continue
                        
                        obj_type = obj.get('@type', '')
                        if isinstance(obj_type, list):
                            obj_type = obj_type[0] if obj_type else ''
                        
                        item = {}
                        
                        # Product
                        if obj_type == 'Product':
                            item['title'] = str(obj.get('name', ''))[:200]
                            offers = obj.get('offers') or obj.get('offer')
                            if offers:
                                if isinstance(offers, list):
                                    offers = offers[0]
                                if isinstance(offers, dict):
                                    price = offers.get('price') or offers.get('lowPrice')
                                    currency = offers.get('priceCurrency', '')
                                    if price:
                                        item['price'] = f"{price} {currency}".strip()
                            if obj.get('description'):
                                item['description'] = str(obj['description'])[:300]
                            if obj.get('url'):
                                item['link'] = urljoin(url, str(obj['url']))
                            if obj.get('image'):
                                img = obj['image']
                                item['image'] = img if isinstance(img, str) else (img[0] if isinstance(img, list) and img else '')
                        
                        # ItemList
                        elif obj_type == 'ItemList':
                            for li in obj.get('itemListElement', [])[:20]:
                                if not isinstance(li, dict):
                                    continue
                                product = li.get('item') or li
                                if not isinstance(product, dict):
                                    continue
                                sub_item = {}
                                sub_item['title'] = str(product.get('name', ''))[:200]
                                offers = product.get('offers') or {}
                                if isinstance(offers, dict):
                                    price = offers.get('price') or offers.get('lowPrice')
                                    currency = offers.get('priceCurrency', '')
                                    if price:
                                        sub_item['price'] = f"{price} {currency}".strip()
                                if product.get('url'):
                                    sub_item['link'] = urljoin(url, str(product['url']))
                                if sub_item.get('title'):
                                    items.append(sub_item)
                            continue  # ItemList handled
                        
                        # Article
                        elif obj_type in ('Article', 'NewsArticle', 'BlogPosting'):
                            item['title'] = str(obj.get('headline') or obj.get('name', ''))[:200]
                            if obj.get('description'):
                                item['description'] = str(obj['description'])[:300]
                            if obj.get('url'):
                                item['link'] = urljoin(url, str(obj['url']))
                        
                        if item.get('title'):
                            items.append(item)
                
                except Exception as e:
                    logger.debug(f"JSON-LD parse error: {e}")
        
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
        
        return items
    
    def _extract_microdata(self, html: str, url: str) -> List[Dict[str, Any]]:
        """استخراج از Microdata."""
        items = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            for item_type in ['Product', 'Offer', 'Article']:
                for el in soup.find_all(attrs={'itemtype': re.compile(item_type, re.I)}):
                    item = {}
                    
                    name_el = el.find(attrs={'itemprop': 'name'})
                    if name_el:
                        item['title'] = name_el.get_text(strip=True)[:200]
                    
                    price_el = el.find(attrs={'itemprop': 'price'})
                    if price_el:
                        item['price'] = (price_el.get('content') or price_el.get_text(strip=True))[:50]
                    
                    link_el = el.find(attrs={'itemprop': 'url'})
                    if link_el:
                        href = link_el.get('href') or link_el.get('content') or ''
                        if href and not href.startswith('#'):
                            item['link'] = urljoin(url, href)
                    
                    desc_el = el.find(attrs={'itemprop': 'description'})
                    if desc_el:
                        item['description'] = desc_el.get_text(strip=True)[:300]
                    
                    img_el = el.find(attrs={'itemprop': 'image'})
                    if img_el:
                        src = img_el.get('src') or img_el.get('content') or ''
                        if src:
                            item['image'] = urljoin(url, src)
                    
                    if item.get('title'):
                        items.append(item)
        
        except Exception as e:
            logger.debug(f"Microdata extraction failed: {e}")
        
        return items
    
    def _extract_from_meta(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """استخراج از Meta tags (Open Graph, Twitter Cards, etc)."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            item = {}
            
            # og:title
            og_title = soup.find('meta', property='og:title')
            if og_title:
                item['title'] = og_title.get('content', '').strip()[:200]
            
            # og:description
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                item['description'] = og_desc.get('content', '').strip()[:300]
            
            # og:url
            og_url = soup.find('meta', property='og:url')
            if og_url:
                item['link'] = og_url.get('content', '').strip()
            
            # og:image
            og_image = soup.find('meta', property='og:image')
            if og_image:
                item['image'] = urljoin(url, og_image.get('content', '').strip())
            
            # product:price
            price_meta = soup.find('meta', property='product:price:amount')
            currency_meta = soup.find('meta', property='product:price:currency')
            if price_meta:
                price = price_meta.get('content', '')
                currency = currency_meta.get('content', '') if currency_meta else ''
                item['price'] = f"{price} {currency}".strip()
            
            if item.get('title'):
                return item
        
        except Exception as e:
            logger.debug(f"Meta extraction failed: {e}")
        
        return None
    
    def _extract_from_css(self, html: str, url: str) -> List[Dict[str, Any]]:
        """استخراج از CSS selectors."""
        items = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # دریافت selectors از registry یا استفاده از defaults
            selectors = self.registry.get_product_selectors(url)
            
            for selector in selectors:
                cards = soup.select(selector)[:30]
                for card in cards:
                    item = self._extract_from_card(card, url)
                    if item and item.get('title'):
                        items.append(item)
                if items:
                    break
        
        except Exception as e:
            logger.debug(f"CSS extraction failed: {e}")
        
        return items
    
    def _extract_from_card(self, card, url: str) -> Optional[Dict[str, Any]]:
        """استخراج از یک المان کارت."""
        item = {}
        
        # عنوان
        title_el = card.find(['h2', 'h3', 'h4', 'a', 'span'])
        if title_el:
            title_text = title_el.get_text(strip=True)
            if 3 < len(title_text) < 200:
                item['title'] = title_text
        
        # لینک
        link_el = card.find('a', href=True)
        if link_el:
            href = link_el.get('href', '')
            if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                item['link'] = urljoin(url, href)
        
        # قیمت
        card_text = card.get_text(' ', strip=True)
        price_patterns = [
            r'([\d٬,]{3,})\s*(تومان|ریال)',
            r'\$([\d,]+)',
            r'([\d,]+)\s*(USD|EUR)',
        ]
        for pattern in price_patterns:
            m = re.search(pattern, card_text)
            if m:
                item['price'] = f"{m.group(1)} {m.group(2)}".strip()
                break
        
        # تصویر
        img_el = card.find('img', src=True)
        if img_el:
            src = img_el.get('src') or img_el.get('data-src', '')
            if src and not src.startswith('data:'):
                item['image'] = urljoin(url, src)
        
        return item if item.get('title') else None
    
    def _extract_from_price_patterns(self, html: str, url: str) -> List[Dict[str, Any]]:
        """استخراج بر اساس الگوهای قیمت."""
        items = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # الگوهای قیمت
            price_re = re.compile(r'([\d٬,]{4,})\s*(تومان|ریال)', re.UNICODE)
            
            for text_el in soup.find_all(string=price_re):
                parent = text_el.parent
                if not parent:
                    continue
                
                # به سمت بالا برو تا به کارت برسی
                container = parent
                for _ in range(5):
                    if container.parent and container.parent.name in ('li', 'div', 'article', 'section'):
                        container = container.parent
                    else:
                        break
                
                # استخراج قیمت
                m = price_re.search(container.get_text())
                if not m:
                    continue
                price_str = f"{m.group(1)} {m.group(2)}"
                
                # عنوان: نزدیک‌ترین لینک یا heading
                title = ''
                link = ''
                heading = container.find(['h2', 'h3', 'h4', 'a'])
                if heading:
                    title = heading.get_text(strip=True)[:200]
                if heading and heading.name == 'a':
                    href = heading.get('href', '')
                    if href and not href.startswith(('#', 'javascript:')):
                        link = urljoin(url, href)
                elif not link:
                    a = container.find('a', href=True)
                    if a:
                        href = a.get('href', '')
                        if href and not href.startswith(('#', 'javascript:')):
                            link = urljoin(url, href)
                
                if title and len(title) > 3:
                    items.append({
                        'title': title,
                        'price': price_str,
                        'link': link,
                    })
        
        except Exception as e:
            logger.debug(f"Price pattern extraction failed: {e}")
        
        # Deduplicate
        seen = set()
        unique = []
        for item in items:
            key = item.get('title', '').lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique[:30]
    
    def _is_likely_spa(self, html: str) -> bool:
        """بررسی اینکه آیا صفحه SPA است."""
        if not html or len(html) < 1000:
            return False
        
        # نشانه‌های SPA
        spa_indicators = [
            'id="root"',
            'id="__next"',
            'id="app"',
            'ng-app',
            'data-reactroot',
            'window.__INITIAL_STATE__',
            'window.__NUXT__',
            '__NEXT_DATA__',
        ]
        
        for indicator in spa_indicators:
            if indicator in html:
                return True
        
        # اگر متن خیلی کم است
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            text = soup.get_text(' ', strip=True)
            if len(text) < 500:
                return True
        except:
            pass
        
        return False
    
    async def _extract_with_browser(self, url: str) -> List[Dict[str, Any]]:
        """استخراج با browser rendering."""
        items = []
        try:
            # استفاده از crawl4ai
            from crawl4ai import AsyncWebCrawler
            from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
            
            browser_cfg = BrowserConfig(headless=True, verbose=False)
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=30000,
                wait_until='networkidle',
                delay_before_return_html=3.0,
            )
            
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
                if result.success and result.html:
                    # استخراج از HTML رندر شده
                    items = self._extract_from_css(result.html, url)
                    if not items:
                        items = self._extract_from_price_patterns(result.html, url)
        
        except ImportError:
            logger.debug("crawl4ai not available")
        except Exception as e:
            logger.debug(f"Browser extraction failed: {e}")
        
        return items
    
    async def extract_site_wide(
        self,
        seed_url: str,
        max_pages: int = 50,
        max_items: int = 500,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        استخراج محصولات از کل یک سایت.
        این متد برای سایت‌های بزرگ استفاده می‌شود.
        """
        all_items = []
        metadata = {
            'seed_url': seed_url,
            'pages_processed': 0,
            'total_items': 0,
            'sources': {},
        }
        
        # اگر سایت API handler دارد، از آن استفاده کن
        if self.registry.has_api_handler(seed_url):
            api_items = await self.registry.fetch_via_api(seed_url, max_items)
            if api_items:
                all_items = api_items
                metadata['sources']['site_api'] = len(api_items)
                metadata['pages_processed'] = 1
                metadata['total_items'] = len(all_items)
                return all_items, metadata
        
        # در غیر این صورت، crawl ساده
        # (این بخش را می‌توان با discover + crawl کامل کرد)
        items, page_meta = await self.extract_from_url(seed_url, max_items=max_items)
        all_items.extend(items)
        metadata['pages_processed'] = 1
        metadata['sources'][page_meta.get('final_method', 'unknown')] = len(items)
        metadata['total_items'] = len(all_items)
        
        return all_items, metadata


# Singleton
_extractor_instance: Optional[SmartStructuredDataExtractor] = None

def get_smart_extractor() -> SmartStructuredDataExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SmartStructuredDataExtractor()
    return _extractor_instance
