
# -*- coding: utf-8 -*-
"""
Web Crawler Service
سرویس crawl وبسایت‌ها و تبدیل محتوا به collection

معماری:
- مرحله ۱: کشف URL ها (sitemap.xml + BFS link following)
- مرحله ۲: استخراج محتوا با trafilatura (بدون نیاز به browser)
- مرحله ۳: chunking و embedding و ذخیره در ChromaDB
- مرحله ۴: ثبت تنظیمات collection در dynamic store

Fallback: اگر playwright نصب بود از crawl4ai استفاده می‌شود،
          در غیر این صورت از httpx+trafilatura استفاده می‌شود.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Job Store — in-memory, shared across requests
# ──────────────────────────────────────────────────────────────────────────────

_crawler_jobs: Dict[str, Dict[str, Any]] = {}


def get_crawler_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _crawler_jobs.get(job_id)


def list_crawler_jobs() -> List[Dict[str, Any]]:
    return list(_crawler_jobs.values())


def _create_job(
    url: str,
    collection_name: str,
    max_depth: int,
    max_pages: int,
    config: Dict[str, Any],
    job_type: str = "crawl",
    timeout_seconds: int = 300,
) -> str:
    job_id = str(uuid.uuid4())
    _crawler_jobs[job_id] = {
        "job_id": job_id,
        "job_type": job_type,
        "url": url,
        "collection_name": collection_name,
        "status": "pending",
        "pages_crawled": 0,
        "pages_indexed": 0,
        "pages_failed": 0,
        "total_chunks": 0,
        "progress_pct": 0.0,
        "max_pages": max_pages,
        "max_depth": max_depth,
        "config": config,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "errors": [],
        "discovered_pages": None,
        "timeout_seconds": timeout_seconds,
        "queue_size": 0,
        "estimated_remaining_seconds": None,
    }
    return job_id


def _update_job(job_id: str, **kwargs: Any) -> None:
    if job_id in _crawler_jobs:
        _crawler_jobs[job_id].update(kwargs)


def _aggregated_links_list(all_pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """لینک‌های داخلی منحصربه‌فرد از تمام صفحات crawl‌شده."""
    seen: Set[str] = set()
    result: List[Dict[str, str]] = []
    for p in all_pages:
        for lnk in (p.get("_internal_links") or []):
            u = lnk.get("url", "")
            if u and u not in seen:
                seen.add(u)
                result.append(lnk)
    return result[:100]


def _aggregated_items_list(all_pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """آیتم‌های ساختاریافته منحصربه‌فرد از تمام صفحات crawl‌شده."""
    seen: Set[str] = set()
    result: List[Dict[str, Any]] = []
    for p in all_pages:
        for item in (p.get("_structured_items") or []):
            key = (item.get("title", "") + "|" + item.get("link", "")).lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(item)
    return result[:50]


# ──────────────────────────────────────────────────────────────────────────────
# URL helpers
# ──────────────────────────────────────────────────────────────────────────────

SKIP_EXTENSIONS = {
    ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".mp4", ".mp3", ".avi", ".mov", ".woff", ".woff2", ".ttf", ".eot",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
}

SKIP_PATH_PATTERNS = [
    r"/login", r"/logout", r"/signin", r"/signout", r"/register",
    r"/cart", r"/checkout", r"/account", r"/profile", r"/search\?",
    r"/tag/", r"/author/", r"#", r"mailto:", r"tel:",
]


def _normalize_url(url: str, base: str) -> Optional[str]:
    """URL را normalize کن و بررسی کن که قابل crawl باشد."""
    try:
        full = urljoin(base, url)
        parsed = urlparse(full)
        # فقط http و https
        if parsed.scheme not in ("http", "https"):
            return None
        # حذف fragment
        clean = urlunparse(parsed._replace(fragment=""))
        # بررسی پسوند فایل
        path = parsed.path.lower()
        for ext in SKIP_EXTENSIONS:
            if path.endswith(ext):
                return None
        # بررسی path patterns
        for pattern in SKIP_PATH_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                return None
        return clean
    except Exception:
        return None


def _same_domain(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    return host == base_domain or host.endswith("." + base_domain)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Sitemap parser
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch_sitemap_urls(base_url: str, client: httpx.AsyncClient) -> List[str]:
    """URLs را از sitemap.xml استخراج کن."""
    urls: List[str] = []
    sitemap_urls = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
        urljoin(base_url, "/sitemap/"),
    ]
    for sitemap_url in sitemap_urls:
        try:
            resp = await client.get(sitemap_url, timeout=10, follow_redirects=True)
            if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
                # استخراج URL از <loc> تگ ها
                found = re.findall(r"<loc>\s*(https?://[^<\s]+)\s*</loc>", resp.text)
                urls.extend(found[:500])
                logger.info(f"  📍 Sitemap {sitemap_url}: {len(found)} URLs found")
                break
        except Exception:
            continue
    return urls


# ──────────────────────────────────────────────────────────────────────────────
# Content fetcher + extractor
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch_page(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    صفحه را fetch کن و HTML برگردان.
    برای سایت‌های SPA که محتوا با JS بارگذاری می‌شود،
    از crawl4ai با headless browser استفاده می‌کند.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fa,en;q=0.9",
        }
        resp = await client.get(
            url, timeout=20, follow_redirects=True, headers=headers
        )
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return None
        html = resp.text

        # اگر صفحه محتوای کافی دارد (نه SPA خالی)، برگردان
        if _has_sufficient_content(html):
            return html

        # Fallback به crawl4ai برای صفحات SPA
        logger.debug(f"  🔄 Trying crawl4ai for SPA page: {url[:60]}")
        crawl4ai_html = await _fetch_page_with_crawl4ai(url)
        if crawl4ai_html:
            return crawl4ai_html
        return html  # اگر crawl4ai هم کار نکرد، همان را برگردان

    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None


def _has_sufficient_content(html: str, min_text_length: int = 500) -> bool:
    """بررسی اینکه HTML محتوای کافی دارد (SPA نیست)."""
    if not html or len(html) < 1000:
        return False
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # ریمووال تگ‌های غیر محتوایی
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return len(text) >= min_text_length
    except Exception:
        # اگر BeautifulSoup کار نکرد، طول HTML را معیار قرار بده
        return len(html) > 5000


# نگه‌داشتن یک نمونه singleton از crawl4ai برای عملکرد بهتر
_crawl4ai_instance = None
_crawl4ai_lock = None


async def _fetch_page_with_crawl4ai(url: str, timeout: int = 30) -> Optional[str]:
    """
    از crawl4ai برای fetch صفحات SPA استفاده کن.
    از patchright (stealth) استفاده می‌کند تا anti-bot را دور بزند.
    """
    global _crawl4ai_instance, _crawl4ai_lock
    try:
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

        # ایجاد lock اگر وجود ندارد
        if _crawl4ai_lock is None:
            _crawl4ai_lock = asyncio.Lock()

        async with _crawl4ai_lock:
            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                accept_downloads=False,
                use_persistent_context=False,
            )
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=timeout * 1000,
                wait_until="networkidle",
                delay_before_return_html=2.0,
                scan_full_page=True,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
                if result and result.success and result.html:
                    return result.html
                return None

    except Exception as e:
        logger.debug(f"crawl4ai fetch failed for {url}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Zoomit.ir API-based Product Fetcher
# ──────────────────────────────────────────────────────────────────────────────

# دسته‌بندی‌های اصلی زوبین با id و نام فارسی
ZOOMIT_MAIN_CATEGORIES: List[Tuple[str, str]] = [
    ("1", "گوشی"),
    ("9", "لپ‌تاپ"),
    ("3", "تبلت"),
    ("4", "ساعت هوشمند"),
    ("10", "کنسول بازی"),
    ("18", "هدفون"),
    ("14", "کارت گرافیک"),
    ("11", "تلویزیون"),
    ("6", "دوربین عکاسی"),
    ("12", "مانیتور"),
    ("13", "پردازنده"),
    ("20", "اس اس دی"),
    ("19", "هارد دیسک"),
    ("17", "پاور بانک"),
    ("25", "ماوس"),
    ("30", "اسپیکر"),
    ("48", "یخچال فریزر"),
    ("51", "ماشین لباسشویی"),
    ("63", "جاروبرقی"),
    ("94", "قهوه‌ساز"),
]


def _is_product_site(url: str) -> bool:
    """
    بررسی هوشمند اینکه آیا URL مربوط به یک سایت محصول/فروشگاهی است.
    از site_registry و pattern matching استفاده می‌کند.
    """
    try:
        from services.site_registry import get_site_registry
        registry = get_site_registry()
        config = registry.detect_site(url)
        if config:
            return True
        
        # URL هایی که shop/store/product دارند
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        product_indicators = [
            '/product', '/products', '/shop', '/store',
            '/catalog', '/items', '/listing',
        ]
        for indicator in product_indicators:
            if indicator in path_lower:
                return True
        
        return False
    except Exception:
        return False


def _is_zoomit_product_url(url: str) -> bool:
    """بررسی کن که URL مربوط به بخش محصولات زوبین است."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    return "zoomit.ir" in host and "/product" in parsed.path


async def _fetch_zoomit_api_products(
    max_per_category: int = 150,
) -> List[Dict[str, Any]]:
    """
    محصولات زوبین را از API دریافت و به فرمت page برگردان.
    هر محصول یک «صفحه مجازی» با metadata غنی می‌شود تا
    WebContentProcessor بتواند virtual chunk تولید کند.
    """
    pages: List[Dict[str, Any]] = []

    api_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.zoomit.ir/",
        "Origin": "https://www.zoomit.ir",
    }

    async with httpx.AsyncClient(
        headers=api_headers, timeout=30, follow_redirects=True
    ) as client:
        for cat_id, cat_name in ZOOMIT_MAIN_CATEGORIES:
            try:
                r = await client.get(
                    "https://api2.zoomit.ir/catalog/api/search/category",
                    params={"categoryId": cat_id, "size": max_per_category},
                )
                if r.status_code != 200:
                    logger.warning(
                        f"  ⚠️ Zoomit API category '{cat_name}' (id={cat_id}) → {r.status_code}"
                    )
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
                    in_stock = bool(item.get("inStock"))
                    brand = item.get("brand") or {}
                    brand_name = (
                        (brand.get("title") or "")
                        if isinstance(brand, dict)
                        else ""
                    )

                    # فرمت قیمت
                    price_str = ""
                    if min_price and min_price > 0:
                        price_str = f"از {int(min_price):,} تومان"

                    # مشخصات کلیدی
                    specs: List[str] = []
                    for spec in item.get("keySpecifications") or []:
                        pv = (spec.get("primaryValue") or "").strip()
                        if pv:
                            specs.append(pv)

                    # URL محصول در سایت زوبین
                    product_url = (
                        f"https://www.zoomit.ir/product/{slug}/"
                        if slug
                        else f"https://www.zoomit.ir/product/list/{cat_id}/"
                    )

                    # متن محتوا برای chunk
                    content_parts: List[str] = [title]
                    if english_title:
                        content_parts.append(english_title)
                    if brand_name:
                        content_parts.append(f"برند: {brand_name}")
                    content_parts.append(f"دسته‌بندی: {cat_name}")
                    if price_str:
                        content_parts.append(price_str)
                    if not in_stock:
                        content_parts.append("(ناموجود)")
                    if specs:
                        content_parts.append(" | ".join(specs))

                    content = " — ".join(content_parts)
                    spec_desc = " | ".join(specs) if specs else ""
                    full_title = (
                        f"{title} ({english_title})" if english_title else title
                    )

                    pages.append(
                        {
                            "url": product_url,
                            "content": content,
                            "metadata": {
                                "title": title,
                                "page_product_title": title,
                                "page_product_price": price_str,
                                "page_product_description": spec_desc,
                                "page_product_image": "",
                                "brand": brand_name,
                                "category": cat_name,
                                "in_stock": "true" if in_stock else "false",
                                "source_type": "zoomit_api",
                            },
                            "_structured_items": [
                                {
                                    "title": full_title,
                                    "price": price_str,
                                    "description": (
                                        f"برند: {brand_name} | دسته: {cat_name}"
                                        + (f" | {spec_desc}" if spec_desc else "")
                                    ),
                                    "link": product_url,
                                }
                            ],
                            "_internal_links": [],
                        }
                    )

                logger.info(
                    f"  📦 Zoomit API: {len(items)} products from '{cat_name}' (id={cat_id})"
                )
                await asyncio.sleep(0.3)

            except Exception as exc:
                logger.warning(
                    f"  ⚠️ Zoomit category '{cat_name}' (id={cat_id}) failed: {exc}"
                )

    logger.info(f"  🛍️ Zoomit API total: {len(pages)} products fetched")
    return pages


def _extract_links(html: str, base_url: str, base_domain: str) -> List[str]:
    """لینک‌ها را از HTML استخراج کن."""
    links: List[str] = []
    for href in re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        norm = _normalize_url(href, base_url)
        if norm and _same_domain(norm, base_domain):
            links.append(norm)
    return links


def _quick_title_from_html(html: str) -> str:
    """عنوان صفحه بدون پردازش سنگین (برای مرحله discover)."""
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:500]
    return ""


def _extract_internal_links(html: str, base_url: str, base_domain: str, max_links: int = 50) -> List[Dict[str, str]]:
    """
    لینک‌های داخلی مهم صفحه را استخراج کن.
    هر لینک شامل: url, text (متن قابل کلیک), title (عنوان صفحه مقصد اگر باشد)
    """
    links: List[Dict[str, str]] = []
    seen: Set[str] = set()
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            norm = _normalize_url(href, base_url)
            if not norm or not _same_domain(norm, base_domain):
                continue
            if _url_hash(norm) in seen:
                continue
            seen.add(_url_hash(norm))
            link_text = a_tag.get_text(strip=True)[:200]
            link_title = (a_tag.get("title") or "").strip()[:200]
            if link_text:
                links.append({"url": norm, "text": link_text, "title": link_title})
            if len(links) >= max_links:
                break
    except Exception as e:
        logger.debug(f"_extract_internal_links failed for {base_url}: {e}")
    return links


def _extract_jsonld_items(html: str, url: str) -> List[Dict[str, Any]]:
    """
    از تگ‌های <script type="application/ld+json"> آیتم‌ها استخراج کن.
    این معتبرترین منبع structured data است.
    """
    items: List[Dict[str, Any]] = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string or script.get_text()
                if not raw or not raw.strip():
                    continue
                data = json.loads(raw)
                # ممکن آرایه یا تک object باشد
                if isinstance(data, list):
                    ld_items = data
                elif isinstance(data, dict):
                    ld_items = [data]
                else:
                    continue

                for obj in ld_items:
                    if not isinstance(obj, dict):
                        continue
                    obj_type = obj.get("@type", "")
                    if isinstance(obj_type, list):
                        obj_type = obj_type[0] if obj_type else ""

                    # Product
                    if obj_type == "Product":
                        item: Dict[str, Any] = {}
                        if obj.get("name"):
                            item["title"] = str(obj["name"])[:200]
                        offers = obj.get("offers") or obj.get("offer")
                        if offers:
                            if isinstance(offers, list):
                                offers = offers[0] if offers else None
                            if isinstance(offers, dict):
                                price_val = offers.get("price") or offers.get("lowPrice")
                                currency = offers.get("priceCurrency", "")
                                if price_val:
                                    item["price"] = f"{price_val} {currency}".strip()
                        if obj.get("description"):
                            item["description"] = str(obj["description"])[:300]
                        if obj.get("image"):
                            img = obj["image"]
                            item["image"] = img if isinstance(img, str) else (img[0] if isinstance(img, list) and img else "")
                            if item["image"]:
                                item["image"] = urljoin(url, item["image"])
                        if obj.get("url"):
                            item["link"] = urljoin(url, str(obj["url"]))
                        elif obj.get("@id"):
                            item["link"] = urljoin(url, str(obj["@id"]))
                        if item.get("title"):
                            items.append(item)

                    # ItemList (لیست محصولات)
                    elif obj_type == "ItemList":
                        list_items = obj.get("itemListElement", [])
                        for li in list_items:
                            if not isinstance(li, dict):
                                continue
                            product = li.get("item") or li
                            if not isinstance(product, dict):
                                continue
                            item = {}
                            if product.get("name"):
                                item["title"] = str(product["name"])[:200]
                            offers = product.get("offers") or product.get("offer")
                            if offers and isinstance(offers, dict):
                                price_val = offers.get("price") or offers.get("lowPrice")
                                currency = offers.get("priceCurrency", "")
                                if price_val:
                                    item["price"] = f"{price_val} {currency}".strip()
                            if product.get("url"):
                                item["link"] = urljoin(url, str(product["url"]))
                            elif li.get("url"):
                                item["link"] = urljoin(url, str(li["url"]))
                            if product.get("description"):
                                item["description"] = str(product["description"])[:300]
                            if product.get("image"):
                                img = product["image"]
                                item["image"] = img if isinstance(img, str) else (img[0] if isinstance(img, list) and img else "")
                                if item.get("image"):
                                    item["image"] = urljoin(url, item["image"])
                            if item.get("title"):
                                items.append(item)

                    # Article
                    elif obj_type in ("Article", "NewsArticle", "BlogPosting"):
                        item = {}
                        if obj.get("headline") or obj.get("name"):
                            item["title"] = str(obj.get("headline") or obj.get("name"))[:200]
                        if obj.get("url"):
                            item["link"] = urljoin(url, str(obj["url"]))
                        if obj.get("description"):
                            item["description"] = str(obj["description"])[:300]
                        if obj.get("image"):
                            img = obj["image"]
                            item["image"] = img if isinstance(img, str) else (img[0] if isinstance(img, list) and img else "")
                            if item.get("image"):
                                item["image"] = urljoin(url, item["image"])
                        if item.get("title"):
                            items.append(item)

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

    except Exception as e:
        logger.debug(f"_extract_jsonld_items failed for {url}: {e}")

    return items


def _extract_structured_items(html: str, url: str) -> List[Dict[str, Any]]:
    """
    از HTML محصولات/آیتم‌های ساختاریافته استخراج کن.
    استراتژی‌ها به ترتیب اولویت:
    1. JSON-LD (معتبرترین)
    2. Microdata (schema.org markup)
    3. CSS card selectors
    4. Price pattern matching
    هر آیتم: {title, price, link, description, image}
    """
    items: List[Dict[str, Any]] = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        # === استراتژی 1: JSON-LD (معتبرترین) ===
        items = _extract_jsonld_items(html, url)

        # === استراتژی 2: Microdata (schema.org markup) ===
        if not items:
            for item_type in ["Product", "Article", "ListItem", "Offer"]:
                for el in soup.find_all(attrs={"itemtype": re.compile(item_type, re.I)}):
                    item: Dict[str, Any] = {}
                    name_el = el.find(attrs={"itemprop": "name"})
                    if name_el:
                        item["title"] = name_el.get_text(strip=True)[:200]
                    price_el = el.find(attrs={"itemprop": "price"})
                    if price_el:
                        item["price"] = (price_el.get("content") or price_el.get_text(strip=True))[:50]
                    link_el = el.find(attrs={"itemprop": "url"})
                    if link_el:
                        href = link_el.get("href") or link_el.get("content") or ""
                        if href and not href.startswith("#"):
                            item["link"] = urljoin(url, href)
                    desc_el = el.find(attrs={"itemprop": "description"})
                    if desc_el:
                        item["description"] = desc_el.get_text(strip=True)[:300]
                    img_el = el.find(attrs={"itemprop": "image"})
                    if img_el:
                        src = img_el.get("src") or img_el.get("content") or ""
                        if src:
                            item["image"] = urljoin(url, src)
                    if item.get("title"):
                        items.append(item)

        # === استراتژی 3: CSS card selectors ===
        if not items:
            product_selectors = [
                "div.product", "div[class*='product']", "article.product",
                "div[class*='card']", "li[class*='product']",
                "div[class*='item']", "div[class*='listing']",
                # سلکتورهای سایت‌های فارسی
                "div[class*='productCard']", "div[class*='product-card']",
                "div[class*='ProductCard']", "a[class*='product']",
                "article", "div[class*='post']",
            ]
            for selector in product_selectors:
                for card in soup.select(selector)[:30]:
                    item = _extract_item_from_card(card, url)
                    if item and item.get("title"):
                        items.append(item)
                if items:
                    break

        # === استراتژی 4: الگوی قیمت ===
        if not items:
            items = _extract_items_from_price_patterns(soup, url)

    except Exception as e:
        logger.debug(f"_extract_structured_items failed for {url}: {e}")

    return items[:30]


def _extract_item_from_card(card, base_url: str) -> Optional[Dict[str, Any]]:
    """از یک المان کارت، اطلاعات آیتم استخراج کن."""
    item: Dict[str, Any] = {}

    # عنوان: اولین h2/h3/a با متن معنادار
    title_el = card.find(["h2", "h3", "h4", "a"])
    if title_el:
        title_text = title_el.get_text(strip=True)
        if 3 < len(title_text) < 200:
            item["title"] = title_text

    # لینک
    link_el = card.find("a", href=True)
    if link_el:
        href = link_el.get("href", "")
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            item["link"] = urljoin(base_url, href)

    # قیمت: الگوهای رایج فارسی/انگلیسی
    card_text = card.get_text(" ", strip=True)
    price_patterns = [
        r'[\d,]{3,}\s*تومان',
        r'[\d,]{3,}\s*ریال',
        r'[\d,]+\s*[\$€£]',
        r'\$[\d,]+',
        r'price[:\s]*[\d,]+',
        r'قیمت[:\s]*[\d,]+تومان',
    ]
    for pat in price_patterns:
        m = re.search(pat, card_text, re.I)
        if m:
            item["price"] = m.group(0).strip()[:50]
            break

    # توضیح کوتاه
    desc_el = card.find(["p", "span", "div"], class_=re.compile(r'desc|summary|excerpt|text', re.I))
    if desc_el:
        desc_text = desc_el.get_text(strip=True)
        if 10 < len(desc_text) < 500:
            item["description"] = desc_text[:300]

    # تصویر
    img_el = card.find("img", src=True)
    if img_el:
        src = img_el.get("src", "")
        if src:
            item["image"] = urljoin(base_url, src)

    return item if item.get("title") else None


def _extract_items_from_price_patterns(soup, base_url: str) -> List[Dict[str, Any]]:
    """
    وقتی schema markup و class selectorها کار نکردند:
    الگوهای قیمت (تومان/ریال/$) را در متن پیدا کن و آیتم‌های مرتبط بساز.
    """
    items: List[Dict[str, Any]] = []
    price_re = re.compile(r'([\d,]{3,})\s*(تومان|ریال|\$|€)', re.I)

    for text_el in soup.find_all(string=price_re):
        parent = text_el.parent
        if not parent:
            continue
        # به سمت بالا برو تا به کارت/لیست برسی
        container = parent
        for _ in range(5):
            if container.parent and container.parent.name in ("li", "div", "article", "section"):
                container = container.parent
            else:
                break
        m = price_re.search(container.get_text())
        if not m:
            continue
        price_str = f"{m.group(1)} {m.group(2)}"

        # عنوان: نزدیک‌ترین لینک یا heading
        title = ""
        link = ""
        heading = container.find(["h2", "h3", "h4", "a"])
        if heading:
            title = heading.get_text(strip=True)[:200]
        if heading and heading.name == "a":
            href = heading.get("href", "")
            if href and not href.startswith(("#", "javascript:")):
                link = urljoin(base_url, href)
        elif not link:
            a = container.find("a", href=True)
            if a:
                href = a.get("href", "")
                if href and not href.startswith(("#", "javascript:")):
                    link = urljoin(base_url, href)

        if title and len(title) > 3:
            items.append({
                "title": title,
                "price": price_str,
                "link": link,
            })

    # Deduplicate by title
    seen: Set[str] = set()
    unique: List[Dict[str, Any]] = []
    for it in items:
        key = it["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique[:30]


def _extract_page_product_meta(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    از یک صفحه محصول (نه لیست)، اطلاعات محصول را استخراج کن:
    عنوان، قیمت، توضیحات، مشخصات فنی و لینک.
    این برای صفحاتی مثل zoomit.ir/product/[slug]/ استفاده می‌شود.
    """
    if not html:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        product_info: Dict[str, Any] = {"link": url}

        # ۱. عنوان محصول — ترجیحاً از meta og:title یا title tag (کوتاه‌تر/خلاصه‌تر)
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            t = og_title.get("content", "").strip()
            if t and 3 < len(t) < 200:
                product_info["title"] = t
        if "title" not in product_info:
            title_tag = soup.find("title")
            if title_tag:
                t = title_tag.get_text(strip=True)
                # حذف نام سایت از عنوان (pattern: "نام محصول | سایت")
                for sep in [" | ", " - ", " — ", " – "]:
                    if sep in t:
                        parts = t.split(sep)
                        t = min(parts, key=len).strip() if len(parts) == 2 else parts[0].strip()
                        break
                if t and 3 < len(t) < 200:
                    product_info["title"] = t
        if "title" not in product_info:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
                if title and 3 < len(title) < 300:
                    product_info["title"] = title

        # ۲. قیمت — الگوهای رایج
        price_re = re.compile(
            r'([\d]{1,3}(?:[,،]\d{3})*)\s*(تومان|ریال|IRR|IRT)',
            re.UNICODE | re.IGNORECASE,
        )
        # ابتدا از meta description
        meta_desc = soup.find("meta", {"name": ["description", "og:description"]})
        if meta_desc:
            m = price_re.search(meta_desc.get("content", ""))
            if m:
                product_info["price"] = f"{m.group(1)} {m.group(2)}"

        # از کل HTML — اولین قیمت معتبر
        if "price" not in product_info:
            all_text = soup.get_text(" ")
            prices_found = price_re.findall(all_text)
            # فیلتر کردن اعداد خیلی کوچک (احتمالاً نه قیمت)
            valid_prices = [
                f"{p[0]} {p[1]}"
                for p in prices_found
                if len(p[0].replace(",", "").replace("،", "")) >= 5
            ]
            if valid_prices:
                product_info["price"] = valid_prices[0]

        # ۳. توضیحات — از meta description یا اولین پاراگراف طولانی
        if meta_desc:
            desc = meta_desc.get("content", "").strip()
            if desc and len(desc) > 30:
                product_info["description"] = desc[:400]

        if "description" not in product_info:
            # اولین پاراگراف طولانی
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 80:
                    product_info["description"] = text[:400]
                    break

        # ۴. تصویر محصول
        og_image = soup.find("meta", {"property": "og:image"})
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                product_info["image"] = urljoin(url, img_url)

        # فقط اگر عنوان دارد برگردان
        return product_info if product_info.get("title") else None

    except Exception as e:
        logger.debug(f"_extract_page_product_meta failed for {url}: {e}")
        return None


def _html_to_markdown(html: str, url: str, base_domain: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    HTML را به متن تمیز تبدیل کن — با حفظ لینک‌ها.
    از trafilatura با include_links=True برای نگه‌داشتن [text](url) استفاده می‌شود.
    """
    metadata: Dict[str, Any] = {}

    # استخراج لینک‌های داخلی
    if base_domain:
        metadata["internal_links"] = _extract_internal_links(html, url, base_domain)
        metadata["structured_items"] = _extract_structured_items(html, url)

    try:
        import trafilatura
        extracted = trafilatura.extract(
            html,
            include_tables=True,
            include_links=True,
            include_images=False,
            favor_precision=True,
            deduplicate=True,
        )
        meta = trafilatura.extract_metadata(html)
        if meta:
            if meta.title:
                metadata["title"] = meta.title
            if meta.description:
                metadata["description"] = meta.description
            if meta.sitename:
                metadata["site_name"] = meta.sitename
        if extracted and len(extracted.strip()) > 50:
            return extracted.strip(), metadata
    except Exception as e:
        logger.debug(f"trafilatura failed for {url}: {e}")

    # Fallback: BeautifulSoup — با حفظ لینک‌ها
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # تبدیل <a> به [text](url) قبل از get_text
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()
            link_text = a_tag.get_text(strip=True)
            if href and link_text and not href.startswith(("#", "javascript:", "mailto:")):
                abs_href = urljoin(url, href)
                a_tag.replace_with(soup.new_string(f"[{link_text}]({abs_href})"))

        body = soup.find("body") or soup
        text = body.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)
        if len(text) > 50:
            return text, metadata
    except Exception as e:
        logger.debug(f"BeautifulSoup fallback failed for {url}: {e}")

    return "", metadata


# ──────────────────────────────────────────────────────────────────────────────
# Discover-only (BFS بدون ایندکس؛ همه صفحات HTML موفق در لیست)
# ──────────────────────────────────────────────────────────────────────────────


async def discover_site_urls(
    job_id: str,
    url: str,
    max_depth: int,
    max_pages: int,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    concurrency: int = 5,
    delay: float = 0.3,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """
    همان منطق BFS + sitemap؛ برای هر صفحه HTML موفق، url و title سبک برمی‌گردد.
    محتوای کوتاه هم در لیست می‌آید تا کاربر بتواند انتخاب کند.
    
    بهبودها:
    - discovered_pages به‌صورت incremental آپدیت می‌شود
    - timeout کلی برای جلوگیری از گیر کردن
    - محاسبه تخمینی زمان باقی‌مانده
    """
    started_at = time.time()
    deadline = started_at + timeout_seconds
    
    _update_job(job_id, status="running", started_at=datetime.utcnow().isoformat())
    logger.info(f"🔎 [Job {job_id[:8]}] Discover URLs: {url} (timeout={timeout_seconds}s)")

    exclude_patterns = exclude_patterns or []
    include_patterns = include_patterns or []
    parsed_base = urlparse(url)
    base_domain = parsed_base.netloc.lower().lstrip("www.")

    compiled_exclude = [re.compile(p, re.IGNORECASE) for p in exclude_patterns]
    compiled_include = [re.compile(p, re.IGNORECASE) for p in include_patterns]

    def _should_crawl(u: str) -> bool:
        for pat in compiled_exclude:
            if pat.search(u):
                return False
        if compiled_include:
            for pat in compiled_include:
                if pat.search(u):
                    return True
            return False
        return True

    visited: Set[str] = set()
    discovered: List[Dict[str, Any]] = []
    errors: List[str] = []
    queue_size = 0
    timeout_reached = False

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=5)
    async with httpx.AsyncClient(limits=limits, timeout=20.0) as client:
        # مرحله ۱: sitemap - با timeout
        sitemap_urls = []
        if max_depth > 0:
            try:
                sitemap_urls = await asyncio.wait_for(
                    _fetch_sitemap_urls(url, client),
                    timeout=15.0
                )
                logger.info(f"  📍 Discover: {len(sitemap_urls)} URLs from sitemap")
            except asyncio.TimeoutError:
                logger.warning("  ⚠️ Sitemap fetch timeout, skipping...")
            except Exception as e:
                logger.warning(f"  ⚠️ Sitemap error: {e}")

        queue: deque[Tuple[str, int]] = deque()
        queue.append((url, 0))
        
        # فقط N صفحه اول sitemap را اضافه کن
        sitemap_limit = min(len(sitemap_urls), max_pages)
        for su in sitemap_urls[:sitemap_limit]:
            norm = _normalize_url(su, url)
            if norm and _should_crawl(norm) and _same_domain(norm, base_domain):
                queue.append((norm, 1))

        queue_size = len(queue)
        semaphore = asyncio.Semaphore(concurrency)

        async def _process_one(page_url: str, depth: int) -> bool:
            """برگرداند True اگر باید ادامه داد، False اگر timeout شده."""
            nonlocal visited, discovered, errors, queue_size
            
            # بررسی timeout
            if time.time() > deadline:
                return False
            
            async with semaphore:
                url_hash = _url_hash(page_url)
                if url_hash in visited:
                    return True
                visited.add(url_hash)

                if len(discovered) >= max_pages:
                    return True

                if not _should_crawl(page_url):
                    return True

                try:
                    html = await asyncio.wait_for(
                        _fetch_page(page_url, client),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    errors.append(f"Timeout fetching: {page_url}")
                    return True
                except Exception as e:
                    errors.append(f"Error fetching {page_url}: {str(e)[:50]}")
                    return True

                if not html:
                    errors.append(f"Failed to fetch: {page_url}")
                    return True

                title = _quick_title_from_html(html)
                discovered.append({
                    "url": page_url,
                    "title": title,
                    "depth": depth,
                })
                
                # محاسبه تخمینی زمان باقی‌مانده
                elapsed = time.time() - started_at
                if len(discovered) > 1:
                    avg_time_per_page = elapsed / len(discovered)
                    remaining_pages = min(queue_size, max_pages - len(discovered))
                    estimated_remaining = max(0, int(avg_time_per_page * remaining_pages))
                else:
                    estimated_remaining = None
                
                # محاسبه progress بهتر
                progress = min(95.0, len(discovered) / max(max_pages, 1) * 90)
                
                # incremental update - هر 5 صفحه یا آخرین صفحه
                should_update = (len(discovered) % 5 == 0) or (len(discovered) == max_pages)
                if should_update:
                    _update_job(
                        job_id,
                        pages_crawled=len(discovered),
                        discovered_pages=list(discovered),
                        progress_pct=progress,
                        queue_size=queue_size,
                        estimated_remaining_seconds=estimated_remaining,
                    )

                # فقط اگر depth کمتر از max باشد لینک‌ها را استخراج کن
                if depth < max_depth:
                    links = _extract_links(html, page_url, base_domain)
                    new_links = 0
                    for link in links[:50]:  # حداکثر 50 لینک از هر صفحه
                        if _url_hash(link) not in visited and _should_crawl(link):
                            queue.append((link, depth + 1))
                            new_links += 1
                    queue_size += new_links

                if delay > 0:
                    await asyncio.sleep(delay)
                    
                return True

        # حلقه اصلی با بررسی timeout
        while queue and len(discovered) < max_pages:
            # بررسی timeout
            if time.time() > deadline:
                timeout_reached = True
                logger.warning(f"  ⏱️ Discover timeout reached after {timeout_seconds}s")
                break
                
            batch: List[Tuple[str, int]] = []
            while queue and len(batch) < concurrency * 2:
                batch.append(queue.popleft())
            
            if batch:
                queue_size = max(0, queue_size - len(batch))
                results = await asyncio.gather(
                    *[_process_one(u, d) for u, d in batch],
                    return_exceptions=True
                )
                # اگر هر کدام False برگرداند، یعنی timeout
                for r in results:
                    if r is False:
                        timeout_reached = True
                        break
                if timeout_reached:
                    break

    elapsed_total = time.time() - started_at
    final_status = "completed" if not timeout_reached else "completed"
    
    _update_job(
        job_id,
        errors=errors,
        pages_crawled=len(discovered),
        pages_failed=len(errors),
        queue_size=0,
    )
    
    if not discovered:
        msg = "هیچ صفحه HTML قابل دسترسی پیدا نشد."
        _update_job(
            job_id,
            status="failed",
            error=msg,
            discovered_pages=[],
            completed_at=datetime.utcnow().isoformat(),
        )
        return {"success": False, "error": msg, "discovered_pages": []}

    _update_job(
        job_id,
        status=final_status,
        discovered_pages=discovered,
        progress_pct=100.0,
        completed_at=datetime.utcnow().isoformat(),
        estimated_remaining_seconds=0,
    )
    logger.info(
        f"🔎 [Job {job_id[:8]}] Discover done: {len(discovered)} pages "
        f"in {elapsed_total:.1f}s ({len(errors)} errors)"
        + (" [TIMEOUT]" if timeout_reached else "")
    )
    return {"success": True, "discovered_pages": discovered, "count": len(discovered)}


# ──────────────────────────────────────────────────────────────────────────────
# Main Crawler Service
# ──────────────────────────────────────────────────────────────────────────────

class WebCrawlerService:
    """
    سرویس اصلی crawl وبسایت.

    جریان:
    1. شروع از URL پایه
    2. کشف URL ها از sitemap + BFS
    3. استخراج محتوای تمیز از هر صفحه
    4. ارسال به WebContentProcessor برای chunking + embedding + ذخیره
    """

    MIN_CONTENT_LENGTH = 100  # حداقل طول محتوا برای indexing

    def __init__(
        self,
        max_depth: int = 3,
        max_pages: int = 200,
        concurrency: int = 5,
        delay_between_requests: float = 0.3,
    ) -> None:
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.delay = delay_between_requests

    async def crawl_and_index(
        self,
        job_id: str,
        url: str,
        collection_name: str,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        collection_type: str = "general",
        domain_keywords: Optional[List[str]] = None,
        out_of_scope_response: Optional[str] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        crawl کن و به collection تبدیل کن.
        این متد به صورت background task اجرا می‌شود.
        """
        _update_job(job_id, status="running", started_at=datetime.utcnow().isoformat())
        logger.info(f"🕷️ [Job {job_id[:8]}] Starting crawl: {url} → {collection_name}")

        exclude_patterns = exclude_patterns or []
        include_patterns = include_patterns or []
        domain_keywords = domain_keywords or []

        parsed_base = urlparse(url)
        base_domain = parsed_base.netloc.lower().lstrip("www.")

        # Compile exclude/include patterns
        compiled_exclude = [re.compile(p, re.IGNORECASE) for p in exclude_patterns]
        compiled_include = [re.compile(p, re.IGNORECASE) for p in include_patterns]

        def _should_crawl(u: str) -> bool:
            for pat in compiled_exclude:
                if pat.search(u):
                    return False
            if compiled_include:
                for pat in compiled_include:
                    if pat.search(u):
                        return True
                return False
            return True

        visited: Set[str] = set()
        all_pages: List[Dict[str, Any]] = []  # {url, content, metadata, depth}
        errors: List[str] = []

        limits = httpx.Limits(max_connections=self.concurrency, max_keepalive_connections=5)
        async with httpx.AsyncClient(limits=limits) as client:
            # مرحله ۱: کشف URL های اولیه از sitemap
            sitemap_urls = await _fetch_sitemap_urls(url, client)
            logger.info(f"  📍 Found {len(sitemap_urls)} URLs from sitemap")

            # صف BFS: (url, depth)
            queue: deque[Tuple[str, int]] = deque()
            queue.append((url, 0))
            # اضافه کردن sitemap URLs با depth=1
            for su in sitemap_urls[:self.max_pages]:
                norm = _normalize_url(su, url)
                if norm and _should_crawl(norm) and _same_domain(norm, base_domain):
                    queue.append((norm, 1))

            semaphore = asyncio.Semaphore(self.concurrency)

            async def _process_one(page_url: str, depth: int) -> None:
                nonlocal visited, all_pages, errors
                async with semaphore:
                    url_hash = _url_hash(page_url)
                    if url_hash in visited:
                        return
                    visited.add(url_hash)

                    if len(all_pages) >= self.max_pages:
                        return

                    if not _should_crawl(page_url):
                        return

                    html = await _fetch_page(page_url, client)
                    if not html:
                        errors.append(f"Failed to fetch: {page_url}")
                        _update_job(
                            job_id,
                            pages_crawled=len(visited),
                            pages_failed=_crawler_jobs[job_id]["pages_failed"] + 1,
                        )
                        return

                    content, meta = _html_to_markdown(html, page_url, base_domain)
                    if len(content) >= self.MIN_CONTENT_LENGTH:
                        page_meta = {
                            "source_url": page_url,
                            "depth": depth,
                            "title": meta.get("title", ""),
                            "description": meta.get("description", ""),
                            "site_name": meta.get("site_name", ""),
                            "crawl_date": datetime.utcnow().isoformat(),
                            "source_type": "web",
                            "collection": collection_name,
                        }
                        # استخراج اطلاعات محصول از صفحات محصول
                        page_product_meta = _extract_page_product_meta(html, page_url)
                        if page_product_meta and page_product_meta.get("title"):
                            page_meta["page_product_title"] = page_product_meta["title"]
                            if page_product_meta.get("price"):
                                page_meta["page_product_price"] = page_product_meta["price"]
                            if page_product_meta.get("description"):
                                page_meta["page_product_description"] = page_product_meta["description"][:300]
                            if page_product_meta.get("image"):
                                page_meta["page_product_image"] = page_product_meta["image"]

                        # لینک‌های داخلی و آیتم‌های ساختاریافته
                        internal_links = meta.get("internal_links") or []
                        structured_items = meta.get("structured_items") or []

                        # اگر صفحه یک محصول است و structured_items ندارد،
                        # آیتم را از page_product_meta بساز
                        if page_product_meta and page_product_meta.get("title") and not structured_items:
                            structured_items = [page_product_meta]

                        if internal_links:
                            page_meta["internal_links"] = ",".join(
                                lnk["url"] for lnk in internal_links[:20]
                            )
                            # ذخیره متن لینک‌ها برای context بهتر
                            link_texts = []
                            for lnk in internal_links[:20]:
                                txt = lnk.get("text", "")
                                url_str = lnk["url"]
                                if txt and txt != url_str:
                                    link_texts.append(f"{txt} → {url_str}")
                                else:
                                    link_texts.append(url_str)
                            page_meta["internal_links_with_text"] = " | ".join(link_texts)
                            page_meta["internal_link_count"] = len(internal_links)
                        if structured_items:
                            page_meta["structured_items_json"] = json.dumps(
                                structured_items[:10], ensure_ascii=False
                            )
                            page_meta["structured_item_count"] = len(structured_items)
                        all_pages.append({
                            "url": page_url,
                            "content": content,
                            "metadata": page_meta,
                            "_internal_links": internal_links,
                            "_structured_items": structured_items,
                        })
                        _update_job(
                            job_id,
                            pages_crawled=len(all_pages),
                            progress_pct=min(95.0, len(all_pages) / max(self.max_pages, 1) * 90),
                        )
                        logger.info(
                            f"  ✅ [{len(all_pages)}/{self.max_pages}] "
                            f"Crawled (depth={depth}): {page_url[:80]}"
                        )
                    else:
                        logger.debug(f"  ⏭ Skipped (too short): {page_url}")

                    # لینک‌ها را برای depth بعدی اضافه کن
                    if depth < self.max_depth:
                        links = _extract_links(html, page_url, base_domain)
                        for link in links:
                            if _url_hash(link) not in visited and _should_crawl(link):
                                queue.append((link, depth + 1))

                    await asyncio.sleep(self.delay)

            # BFS با concurrency کنترل‌شده
            while queue and len(all_pages) < self.max_pages:
                batch: List[Tuple[str, int]] = []
                while queue and len(batch) < self.concurrency * 2:
                    batch.append(queue.popleft())
                if batch:
                    await asyncio.gather(*[_process_one(u, d) for u, d in batch])

        logger.info(f"  📊 Crawled {len(all_pages)} pages, {len(errors)} errors")

        # ── Smart API/Structured Data Extraction ──────────────────────────────────
        # اگر سایت شناخته شده است یا محصولات یافت نشده، تلاش برای extraction هوشمند
        if _is_product_site(url) or not any(p.get('_structured_items') for p in all_pages):
            logger.info(
                f"  🛍️ [Job {job_id[:8]}] Attempting smart structured data extraction for {url}"
            )
            _update_job(job_id, progress_pct=65.0)
            
            try:
                from services.smart_structured_extractor import get_smart_extractor
                extractor = get_smart_extractor()
                smart_items, smart_meta = await extractor.extract_site_wide(
                    seed_url=url,
                    max_pages=self.max_pages,
                    max_items=min(1000, self.max_pages * 10),
                )
                
                if smart_items:
                    # تبدیل items به pages format
                    smart_pages = []
                    for item in smart_items[:500]:
                        title = item.get('title', '').strip()
                        if not title:
                            continue
                        
                        price = item.get('price', '').strip()
                        link = item.get('link', '').strip()
                        desc = item.get('description', '').strip()
                        
                        # ساخت content
                        content_parts = [title]
                        if price:
                            content_parts.append(f"قیمت: {price}")
                        if desc:
                            content_parts.append(desc[:200])
                        content = " — ".join(content_parts)
                        
                        smart_pages.append({
                            'url': link or url,
                            'content': content,
                            'metadata': {
                                'title': title,
                                'page_product_title': title,
                                'page_product_price': price,
                                'page_product_description': desc[:300],
                                'source_type': smart_meta.get('sources', {}).get('site_api') and 'api' or 'smart_extract',
                            },
                            '_structured_items': [item],
                            '_internal_links': [],
                        })
                    
                    if smart_pages:
                        all_pages = smart_pages
                        errors = []
                        logger.info(
                            f"  ✅ Smart extraction: {len(smart_pages)} items "
                            f"(method: {smart_meta.get('sources', {})})"
                        )
                        _update_job(
                            job_id, pages_crawled=len(all_pages), progress_pct=75.0
                        )
            except Exception as exc:
                logger.warning(f"  ⚠️ Smart extraction failed: {exc}")

        _update_job(job_id, pages_crawled=len(all_pages), errors=errors)

        if not all_pages:
            msg = "هیچ صفحه‌ای با محتوای کافی پیدا نشد."
            _update_job(job_id, status="failed", error=msg, completed_at=datetime.utcnow().isoformat())
            return {"success": False, "error": msg}

        # مرحله ۲: پردازش محتوا و ذخیره در ChromaDB
        try:
            from processors.web_content_processor import WebContentProcessor
            processor = WebContentProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            result = processor.process_and_index(
                pages=all_pages,
                collection_name=collection_name,
                overwrite=overwrite,
            )
            total_chunks = result.get("total_chunks", 0)
            logger.info(f"  💾 Indexed {total_chunks} chunks into '{collection_name}'")
        except Exception as e:
            logger.error(f"  ❌ Processing failed: {e}", exc_info=True)
            _update_job(
                job_id,
                status="failed",
                error=str(e),
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"success": False, "error": str(e)}

        # مرحله ۳: ذخیره تنظیمات collection
        try:
            from config.dynamic_collection_store import save_collection_config, get_collection_config
            
            # Merge existing source_types
            existing_cfg = get_collection_config(collection_name) or {}
            existing_types = existing_cfg.get("source_types", [])
            if isinstance(existing_types, str):
                existing_types = [existing_types] if existing_types else []
            if "web_crawl" not in existing_types:
                existing_types.append("web_crawl")
            
            crawled_urls = [
                str(p.get("url") or "").strip()
                for p in all_pages
                if isinstance(p, dict) and str(p.get("url") or "").strip()
            ]

            # جمع‌آوری لینک‌ها و آیتم‌های ساختاریافته از همه صفحات
            aggregated_links: Dict[str, Dict[str, str]] = {}
            all_structured_items: List[Dict[str, Any]] = []
            for p in all_pages:
                for lnk in (p.get("_internal_links") or []):
                    u = lnk.get("url", "")
                    if u and u not in aggregated_links:
                        aggregated_links[u] = lnk
                for item in (p.get("_structured_items") or []):
                    if item.get("title"):
                        all_structured_items.append(item)

            save_collection_config(
                collection_name=collection_name,
                system_prompt=system_prompt,
                display_name=display_name or collection_name,
                description=description or f"وبسایت crawl شده: {url}",
                collection_type=collection_type,
                domain_keywords=domain_keywords,
                out_of_scope_response=out_of_scope_response,
                extra={
                    "source_url": url,
                    "source_type": "web_crawl",  # backward compatibility
                    "source_types": existing_types,  # merged
                    "crawl_mode": "full",
                    "requested_urls": crawled_urls,
                    "pages_crawled": len(all_pages),
                    "total_chunks": total_chunks,
                    "crawl_date": datetime.utcnow().isoformat(),
                    "max_depth": self.max_depth,
                    "max_pages": self.max_pages,
                    "extracted_links": list(aggregated_links.values())[:100],
                    "structured_items": all_structured_items[:50],
                },
            )
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to save collection config: {e}")

        # مرحله ۴: ثبت در heydary_collections
        try:
            import ultimate_rag_system as urs
            for attr in ("heydary_collections", "heydary_collection_names"):
                obj = getattr(urs, attr, None)
                if obj is not None and hasattr(obj, "add"):
                    obj.add(collection_name)
        except Exception:
            pass

        _update_job(
            job_id,
            status="completed",
            pages_indexed=len(all_pages),
            total_chunks=total_chunks,
            progress_pct=100.0,
            completed_at=datetime.utcnow().isoformat(),
        )

        logger.info(
            f"🎉 [Job {job_id[:8]}] Done: {len(all_pages)} pages, "
            f"{total_chunks} chunks → '{collection_name}'"
        )
        return {
            "success": True,
            "pages_crawled": len(all_pages),
            "total_chunks": total_chunks,
            "collection_name": collection_name,
        }

    async def crawl_and_index_urls(
        self,
        job_id: str,
        urls: List[str],
        collection_name: str,
        seed_url: Optional[str] = None,
        restrict_to_seed_domain: bool = True,
        system_prompt: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        collection_type: str = "general",
        domain_keywords: Optional[List[str]] = None,
        out_of_scope_response: Optional[str] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        فقط URLهای داده‌شده را fetch و ایندکس می‌کند (بدون BFS).
        """
        _update_job(job_id, status="running", started_at=datetime.utcnow().isoformat())
        domain_keywords = domain_keywords or []

        seen: Set[str] = set()
        ordered: List[str] = []
        for u in urls:
            u = (u or "").strip()
            if not u or u in seen:
                continue
            if not u.startswith(("http://", "https://")):
                continue
            seen.add(u)
            ordered.append(u)

        if not ordered:
            msg = "لیست URL خالی یا نامعتبر است."
            _update_job(
                job_id,
                status="failed",
                error=msg,
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"success": False, "error": msg}

        base_for_domain = seed_url or ordered[0]
        parsed_seed = urlparse(base_for_domain)
        base_domain = parsed_seed.netloc.lower().lstrip("www.")

        if restrict_to_seed_domain:
            for u in ordered:
                if not _same_domain(u, base_domain):
                    msg = f"URL خارج از دامنه مجاز: {u}"
                    _update_job(
                        job_id,
                        status="failed",
                        error=msg,
                        completed_at=datetime.utcnow().isoformat(),
                    )
                    return {"success": False, "error": msg}

        logger.info(
            f"🕷️ [Job {job_id[:8]}] Selected crawl: {len(ordered)} URLs → {collection_name}"
        )

        all_pages: List[Dict[str, Any]] = []
        errors: List[str] = []

        limits = httpx.Limits(
            max_connections=self.concurrency,
            max_keepalive_connections=5,
        )
        async with httpx.AsyncClient(limits=limits) as client:
            semaphore = asyncio.Semaphore(self.concurrency)

            async def _fetch_one(page_url: str, idx: int) -> None:
                async with semaphore:
                    html = await _fetch_page(page_url, client)
                    if not html:
                        errors.append(f"Failed to fetch: {page_url}")
                        return
                    content, meta = _html_to_markdown(html, page_url, base_domain)
                    if len(content) >= self.MIN_CONTENT_LENGTH:
                        page_meta = {
                            "source_url": page_url,
                            "depth": 0,
                            "title": meta.get("title", ""),
                            "description": meta.get("description", ""),
                            "site_name": meta.get("site_name", ""),
                            "crawl_date": datetime.utcnow().isoformat(),
                            "source_type": "web",
                            "collection": collection_name,
                            "user_selected": True,
                            "selection_index": idx,
                        }
                        # استخراج اطلاعات محصول از صفحه
                        page_product_meta = _extract_page_product_meta(html, page_url)
                        if page_product_meta and page_product_meta.get("title"):
                            page_meta["page_product_title"] = page_product_meta["title"]
                            if page_product_meta.get("price"):
                                page_meta["page_product_price"] = page_product_meta["price"]
                            if page_product_meta.get("description"):
                                page_meta["page_product_description"] = page_product_meta["description"][:300]

                        internal_links = meta.get("internal_links") or []
                        structured_items = meta.get("structured_items") or []

                        # اگر page_product_meta وجود دارد و structured_items خالی است
                        if page_product_meta and page_product_meta.get("title") and not structured_items:
                            structured_items = [page_product_meta]

                        if internal_links:
                            page_meta["internal_links"] = ",".join(
                                lnk["url"] for lnk in internal_links[:20]
                            )
                            # ذخیره متن لینک‌ها برای context بهتر
                            link_texts = []
                            for lnk in internal_links[:20]:
                                txt = lnk.get("text", "")
                                url_str = lnk["url"]
                                if txt and txt != url_str:
                                    link_texts.append(f"{txt} → {url_str}")
                                else:
                                    link_texts.append(url_str)
                            page_meta["internal_links_with_text"] = " | ".join(link_texts)
                            page_meta["internal_link_count"] = len(internal_links)
                        if structured_items:
                            page_meta["structured_items_json"] = str(structured_items[:10])
                            page_meta["structured_item_count"] = len(structured_items)
                        all_pages.append({
                            "url": page_url,
                            "content": content,
                            "metadata": page_meta,
                            "_internal_links": internal_links,
                            "_structured_items": structured_items,
                        })
                        _update_job(
                            job_id,
                            pages_crawled=len(all_pages),
                            progress_pct=min(
                                95.0,
                                len(all_pages) / max(len(ordered), 1) * 90,
                            ),
                        )
                    else:
                        logger.debug(f"  ⏭ Skipped (too short): {page_url}")
                    await asyncio.sleep(self.delay)

            await asyncio.gather(*[_fetch_one(u, i) for i, u in enumerate(ordered)])

        # ── Smart API/Structured Data Extraction (selected URL mode) ──────────────
        _seed = seed_url or (ordered[0] if ordered else "")
        if _seed and _is_product_site(_seed):
            logger.info(
                f"  🛍️ [Job {job_id[:8]}] Product site detected (selected) "
                f"— attempting smart extraction"
            )
            try:
                from services.smart_structured_extractor import get_smart_extractor
                extractor = get_smart_extractor()
                smart_items, smart_meta = await extractor.extract_site_wide(
                    seed_url=_seed,
                    max_pages=len(ordered),
                    max_items=min(1000, len(ordered) * 20),
                )
                
                if smart_items:
                    smart_pages = []
                    for item in smart_items[:500]:
                        title = item.get('title', '').strip()
                        if not title:
                            continue
                        
                        price = item.get('price', '').strip()
                        link = item.get('link', '').strip()
                        desc = item.get('description', '').strip()
                        
                        content_parts = [title]
                        if price:
                            content_parts.append(f"قیمت: {price}")
                        if desc:
                            content_parts.append(desc[:200])
                        content = " — ".join(content_parts)
                        
                        smart_pages.append({
                            'url': link or _seed,
                            'content': content,
                            'metadata': {
                                'title': title,
                                'page_product_title': title,
                                'page_product_price': price,
                                'page_product_description': desc[:300],
                                'source_type': 'smart_extract',
                            },
                            '_structured_items': [item],
                            '_internal_links': [],
                        })
                    
                    if smart_pages:
                        all_pages = smart_pages
                        errors = []
                        logger.info(
                            f"  🛍️ {len(smart_pages)} items extracted via smart extraction"
                        )
            except Exception as exc:
                logger.warning(f"  ⚠️ Smart extraction failed: {exc}")

        _update_job(
            job_id,
            pages_crawled=len(all_pages),
            errors=errors,
            pages_failed=len(errors),
        )

        if not all_pages:
            msg = "هیچ صفحه‌ای با محتوای کافی برای ایندکس پیدا نشد."
            _update_job(
                job_id,
                status="failed",
                error=msg,
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"success": False, "error": msg}

        try:
            from processors.web_content_processor import WebContentProcessor
            processor = WebContentProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            result = processor.process_and_index(
                pages=all_pages,
                collection_name=collection_name,
                overwrite=overwrite,
            )
            total_chunks = result.get("total_chunks", 0)
        except Exception as e:
            logger.error(f"  ❌ Processing failed: {e}", exc_info=True)
            _update_job(
                job_id,
                status="failed",
                error=str(e),
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"success": False, "error": str(e)}

        src_note = f"{len(ordered)} URL انتخاب‌شده توسط کاربر"
        try:
            from config.dynamic_collection_store import save_collection_config, get_collection_config
            
            # Merge existing source_types
            existing_cfg = get_collection_config(collection_name) or {}
            existing_types = existing_cfg.get("source_types", [])
            if isinstance(existing_types, str):
                existing_types = [existing_types] if existing_types else []
            if "web_crawl" not in existing_types:
                existing_types.append("web_crawl")
            
            save_collection_config(
                collection_name=collection_name,
                system_prompt=system_prompt,
                display_name=display_name or collection_name,
                description=description or f"وب crawl انتخابی: {src_note}",
                collection_type=collection_type,
                domain_keywords=domain_keywords,
                out_of_scope_response=out_of_scope_response,
                extra={
                    "source_url": base_for_domain,
                    "source_type": "web_crawl",  # backward compatibility
                    "source_types": existing_types,  # merged
                    "crawl_mode": "selected_urls",
                    "requested_urls": ordered,
                    "pages_crawled": len(all_pages),
                    "total_chunks": total_chunks,
                    "crawl_date": datetime.utcnow().isoformat(),
                    "extracted_links": _aggregated_links_list(all_pages),
                    "structured_items": _aggregated_items_list(all_pages),
                },
            )
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to save collection config: {e}")

        try:
            import ultimate_rag_system as urs
            for attr in ("heydary_collections", "heydary_collection_names"):
                obj = getattr(urs, attr, None)
                if obj is not None and hasattr(obj, "add"):
                    obj.add(collection_name)
        except Exception:
            pass

        _update_job(
            job_id,
            status="completed",
            pages_indexed=len(all_pages),
            total_chunks=total_chunks,
            progress_pct=100.0,
            completed_at=datetime.utcnow().isoformat(),
        )
        logger.info(
            f"🎉 [Job {job_id[:8]}] Selected crawl done: {len(all_pages)} pages, "
            f"{total_chunks} chunks → '{collection_name}'"
        )
        return {
            "success": True,
            "pages_crawled": len(all_pages),
            "total_chunks": total_chunks,
            "collection_name": collection_name,
        }
