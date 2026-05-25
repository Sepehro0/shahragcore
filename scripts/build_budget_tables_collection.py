# -*- coding: utf-8 -*-
"""
Build `budget_tables` collection from:
  - archive/data_files/tables 1-4-budget.xlsx  (tree + amounts per year)
  - archive/data_files/tree-chart-budget-guide.pdf (visual tree)

Each node of the budget tree (resource/expense) becomes a document per year,
carrying both the node's own amount (if leaf) and the computed aggregate
for that node at that year. Aggregates follow the business rule that
"کسر می شود ارقامی که دوبار منظور شده است" items are subtracted.

Embeddings: heydariAI/persian-embeddings (1024d), compatible with the rest
of the system (qavanin/zabete_qa/…).
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import pandas as pd
from chromadb.config import Settings as ChromaSettings

BASE_DIR = "/home/user01/qwen-api/enhanced_rag_system_dev"
sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "budget_tables"
DB_PATH = f"{BASE_DIR}/chroma_db"
XLSX_PATH = f"{BASE_DIR}/archive/data_files/tables 1-4-budget.xlsx"
PDF_PATH = f"{BASE_DIR}/archive/data_files/tree-chart-budget-guide.pdf"

EMBEDDING_DIM = 1024
AVAILABLE_YEARS = [1398, 1399, 1400, 1401, 1402, 1403]
DEFAULT_YEAR = 1403


# ==============================================================
# Tree model
# ==============================================================

class Node:
    """یک گره از درخت بودجه (title یا item)."""

    def __init__(
        self,
        uid: str,
        name: str,
        node_type: str,  # 'title' or 'item'
        raw_id: int,
        parent_uid: Optional[str],
        category: str,  # 'manabe' or 'masaref'
    ) -> None:
        self.uid = uid
        self.name = name.strip()
        self.node_type = node_type
        self.raw_id = raw_id
        self.parent_uid = parent_uid
        self.category = category
        self.children: List["Node"] = []
        # year → raw amount (only for item nodes that actually carry a number)
        self.amounts: Dict[int, float] = {}

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def is_deduction(self) -> bool:
        return "کسر" in self.name and "دوبار" in self.name


def _load_category_sheet(xlsx: pd.ExcelFile, sheet: str, category: str) -> Dict[str, Node]:
    """Parse one sheet (منابع/مصارف) into a flat dict of Node objects keyed by uid."""
    df = pd.read_excel(xlsx, sheet_name=sheet)
    df.columns = [c.strip() for c in df.columns]

    nodes: Dict[str, Node] = {}

    # 1. Titles (internal nodes)
    title_rows = (
        df[["title id", "title", "parent-id"]]
        .dropna(subset=["title id"])
        .drop_duplicates("title id")
        .sort_values("title id")
    )
    for _, r in title_rows.iterrows():
        tid = int(r["title id"])
        pid = int(r["parent-id"]) if not pd.isna(r["parent-id"]) else 0
        parent_uid = f"{category}:t{pid}" if pid != 0 else None
        nodes[f"{category}:t{tid}"] = Node(
            uid=f"{category}:t{tid}",
            name=str(r["title"]).strip(),
            node_type="title",
            raw_id=tid,
            parent_uid=parent_uid,
            category=category,
        )

    # 2. Items (leaf definitions, only present in first year rows)
    item_def_rows = (
        df[["item id", "item", "parent-id (title id)"]]
        .dropna(subset=["item id"])
        .drop_duplicates("item id")
        .sort_values("item id")
    )
    for _, r in item_def_rows.iterrows():
        iid = int(r["item id"])
        parent_tid = int(r["parent-id (title id)"])
        parent_uid = f"{category}:t{parent_tid}"
        nodes[f"{category}:i{iid}"] = Node(
            uid=f"{category}:i{iid}",
            name=str(r["item"]).strip(),
            node_type="item",
            raw_id=iid,
            parent_uid=parent_uid,
            category=category,
        )

    # 3. Amounts per (year, item id)
    amount_rows = df.dropna(subset=["year", "item id.1", "amount"])
    for _, r in amount_rows.iterrows():
        iid = int(r["item id.1"])
        year = int(r["year"])
        amt = float(r["amount"])
        key = f"{category}:i{iid}"
        if key in nodes:
            nodes[key].amounts[year] = amt

    # 4. Link children to parents
    for n in nodes.values():
        if n.parent_uid and n.parent_uid in nodes:
            nodes[n.parent_uid].children.append(n)

    return nodes


def build_tree() -> Tuple[Dict[str, Node], Dict[str, Node]]:
    """Return (nodes_by_uid, roots_by_category)."""
    xlsx = pd.ExcelFile(XLSX_PATH)
    all_nodes: Dict[str, Node] = {}
    roots: Dict[str, Node] = {}

    for sheet, category in [("منابع", "manabe"), ("مصارف", "masaref")]:
        nodes = _load_category_sheet(xlsx, sheet, category)
        all_nodes.update(nodes)
        root = next(n for n in nodes.values() if n.node_type == "title" and n.parent_uid is None)
        roots[category] = root

    return all_nodes, roots


# ==============================================================
# Aggregation
# ==============================================================

def compute_node_value(node: Node, year: int) -> float:
    """
    مقدار گره در سال مشخص:
      • برگ (item): amount خام (اگر «کسر می‌شود» باشد علامت منفی)
      • داخلی (title): جمع مقدار فرزندان (با در نظر گرفتن علامت منفی deductions)
    این تابع علامت منفی را روی برگ کسری اعمال می‌کند تا در sum بالاتر به‌طور طبیعی کم شود.
    """
    if node.is_leaf:
        raw = node.amounts.get(year, 0.0)
        return -raw if node.is_deduction else raw

    total = 0.0
    for child in node.children:
        total += compute_node_value(child, year)
    return total


def node_path(node: Node, nodes: Dict[str, Node]) -> List[str]:
    """Full path from root to node (names)."""
    parts = [node.name]
    cur = node
    while cur.parent_uid and cur.parent_uid in nodes:
        cur = nodes[cur.parent_uid]
        parts.append(cur.name)
    return list(reversed(parts))


def node_depth(node: Node, nodes: Dict[str, Node]) -> int:
    d = 0
    cur = node
    while cur.parent_uid and cur.parent_uid in nodes:
        d += 1
        cur = nodes[cur.parent_uid]
    return d


# ==============================================================
# Document building
# ==============================================================

CATEGORY_FA = {"manabe": "منابع", "masaref": "مصارف"}


def _format_amount(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{int(round(abs(value))):,}"


def _children_summary(node: Node, year: int) -> str:
    """یک متن کوتاه از زیرمجموعه‌های مستقیم + مقدار هر کدام در همان سال."""
    if not node.children:
        return ""
    lines: List[str] = []
    for child in node.children:
        v = compute_node_value(child, year)
        lines.append(f"  - {child.name}: {_format_amount(v)} میلیون ریال")
    return "\n".join(lines)


def build_node_documents(nodes: Dict[str, Node]) -> List[Dict[str, Any]]:
    """یک سند برای هر (گره × سال). متن سند همه اطلاعات لازم برای پاسخ دقیق را دارد."""
    docs: List[Dict[str, Any]] = []

    for node in nodes.values():
        path = node_path(node, nodes)
        path_str = " ← ".join(reversed(path))  # leaf → root reads nicely in Persian
        root_name = path[0]
        cat_fa = CATEGORY_FA[node.category]
        depth = node_depth(node, nodes)

        parent_name = nodes[node.parent_uid].name if node.parent_uid else ""
        direct_children = [c.name for c in node.children]

        for year in AVAILABLE_YEARS:
            value = compute_node_value(node, year)
            raw_amount = node.amounts.get(year, 0.0) if node.is_leaf else 0.0

            header = (
                f"عنوان: {node.name}\n"
                f"دسته: {cat_fa}\n"
                f"سال: {year}\n"
                f"نوع گره: {'برگ' if node.is_leaf else 'گره داخلی (parent)'}"
                f"{' | کسری (منفی)' if node.is_deduction else ''}\n"
                f"مسیر کامل در درخت: {path_str}\n"
            )

            if node.is_leaf:
                body = (
                    f"مقدار ثبت‌شده این آیتم در سال {year}: "
                    f"{_format_amount(raw_amount)} میلیون ریال"
                )
                if node.is_deduction:
                    body += (
                        "\nتوجه: این آیتم «کسر می‌شود» است و در محاسبه والد باید «منها» شود."
                    )
            else:
                cs = _children_summary(node, year)
                body = (
                    f"مقدار محاسبه‌شده این گره در سال {year} "
                    f"(جمع زیرمجموعه‌ها با در نظر گرفتن موارد کسری): "
                    f"{_format_amount(value)} میلیون ریال\n\n"
                    f"زیرمجموعه‌های مستقیم:\n{cs}"
                )

            text = f"[{cat_fa} - سال {year}] {node.name}\n\n{header}\n{body}"

            metadata: Dict[str, Any] = {
                "doc_type": "budget_node",
                "node_uid": node.uid,
                "node_name": node.name,
                "node_type": node.node_type,
                "category": node.category,
                "category_fa": cat_fa,
                "year": year,
                "depth": depth,
                "is_leaf": node.is_leaf,
                "is_deduction": node.is_deduction,
                "parent_uid": node.parent_uid or "",
                "parent_name": parent_name,
                "path": " > ".join(path),
                "root": root_name,
                "raw_amount": raw_amount,
                "computed_value": value,
                "has_children": len(node.children) > 0,
                "children_names": " | ".join(direct_children) if direct_children else "",
            }
            docs.append({"text": text, "metadata": metadata})

    return docs


def build_root_summary_documents(roots: Dict[str, Node], nodes: Dict[str, Node]) -> List[Dict[str, Any]]:
    """برای هر سال، یک سند خلاصه از محاسبه کامل ریشه‌های منابع و مصارف."""
    docs: List[Dict[str, Any]] = []

    for category, root in roots.items():
        cat_fa = CATEGORY_FA[category]
        for year in AVAILABLE_YEARS:
            total = compute_node_value(root, year)
            parts: List[str] = [
                f"محاسبه کامل «{root.name}» برای سال {year}:",
                "",
                "ترکیب محاسبه (زیرمجموعه‌های مستقیم):",
            ]
            for child in root.children:
                v = compute_node_value(child, year)
                sign = "−" if v < 0 else "+"
                parts.append(
                    f"  {sign} {child.name}: {_format_amount(abs(v))} میلیون ریال"
                    + (" (کسر می‌شود)" if child.is_deduction else "")
                )
            parts += [
                "",
                f"مقدار نهایی {root.name} در سال {year} = "
                f"{_format_amount(total)} میلیون ریال",
            ]
            text = "\n".join(parts)
            docs.append(
                {
                    "text": text,
                    "metadata": {
                        "doc_type": "budget_root_summary",
                        "category": category,
                        "category_fa": cat_fa,
                        "year": year,
                        "node_uid": root.uid,
                        "node_name": root.name,
                        "root": root.name,
                        "computed_value": total,
                        "path": root.name,
                    },
                }
            )

    return docs


def build_guide_documents() -> List[Dict[str, Any]]:
    """
    متن راهنمای ساختار درختی (توضیحی) که همیشه می‌تواند context مفیدی بدهد.
    منبع: tree-chart-budget-guide.pdf (ساختار بصری) + دستورالعمل تجمیع.
    """
    guide_chunks = [
        {
            "title": "راهنمای کلی ساختار جداول ۱ تا ۴ بودجه",
            "text": (
                "جداول ۱ تا ۴ کتاب بودجه، جداول کلان منابع و مصارف هستند و ساختار درختی دارند. "
                "هر گره یا یک «عنوان» (title/internal node) است که مقدارش از جمع زیرمجموعه‌هایش "
                "به دست می‌آید، یا یک «آیتم» (item/برگ) است که مقدار عددی مستقیم دارد. "
                "مقادیر به واحد میلیون ریال و برای سال‌های ۱۳۹۸ تا ۱۴۰۳ ذخیره شده‌اند. "
                "آیتم «کسر می‌شود ارقامی که دوبار منظور شده است» استثنا است و باید از جمع والد «کم» شود، نه اضافه."
            ),
        },
        {
            "title": "فرمول ریشه منابع",
            "text": (
                "منابع بودجه کل کشور = منابع شرکت‌های دولتی، موسسات انتفاعی وابسته به دولت و بانک‌ها "
                "+ منابع بودجه عمومی دولت − «کسر می‌شود ارقامی که دوبار منظور شده است ‑ منابع». "
                "منابع بودجه عمومی دولت = درآمدهای اختصاصی دولت + جمع منابع عمومی دولت. "
                "جمع منابع عمومی دولت = درآمدها + واگذاری دارایی‌های سرمایه‌ای + واگذاری دارایی‌های مالی."
            ),
        },
        {
            "title": "فرمول ریشه مصارف",
            "text": (
                "مصارف بودجه کل کشور = مصارف شرکت‌های دولتی، موسسات انتفاعی وابسته به دولت و بانک‌ها "
                "+ مصارف بودجه عمومی دولت − «کسر می‌شود ارقامی که دوبار منظور شده است ‑ مصارف». "
                "مصارف بودجه عمومی دولت = جمع مصارف عمومی دولت + مصارف از محل درآمدهای اختصاصی دولت. "
                "جمع مصارف عمومی دولت = هزینه‌ها + تملک دارایی‌های سرمایه‌ای + تملک دارایی‌های مالی."
            ),
        },
        {
            "title": "قانون محاسبه هر گره",
            "text": (
                "۱) اگر گره برگ باشد: مقدار نهایی = amount همان آیتم در سال مورد نظر. "
                "۲) اگر گره والد باشد: مقدار نهایی = جمع مقادیر تمام زیرمجموعه‌ها "
                "(با رعایت علامت منفی برای آیتم‌های «کسر می‌شود»). "
                "۳) اگر زیرمجموعه‌ای خودش فرزند داشته باشد، اول آن محاسبه می‌شود و سپس به جمع والد افزوده می‌شود. "
                "۴) اگر سال ذکر نشده باشد، سال پیش‌فرض ۱۴۰۳ است و در پاسخ باید این موضوع تصریح شود."
            ),
        },
        {
            "title": "فصول هزینه‌ها (جدول مصارف)",
            "text": (
                "زیرمجموعه «هزینه‌ها» شامل این فصول است: فصل اول: جبران خدمت کارکنان | "
                "فصل دوم: استفاده از کالاها و خدمات | فصل سوم: هزینه‌های اموال و دارایی | "
                "فصل چهارم: یارانه‌ها | فصل پنجم: کمک‌های بلاعوض | فصل ششم: رفاه اجتماعی | "
                "فصل هفتم: سایر هزینه‌ها."
            ),
        },
        {
            "title": "فصول تملک دارایی‌های سرمایه‌ای (جدول مصارف)",
            "text": (
                "زیرمجموعه «تملک دارایی‌های سرمایه‌ای» شامل: فصل اول: ساختمان و سایر مستحدثات | "
                "فصل دوم: ماشین‌آلات و تجهیزات | فصل سوم: سایر دارایی‌های ثابت | "
                "فصل چهارم: استفاده از موجودی انبار | فصل پنجم: اقلام گران‌بها | "
                "فصل ششم: زمین | فصل هفتم: سایر دارایی‌های تولیدنشده."
            ),
        },
        {
            "title": "اجزای تملک دارایی‌های مالی (جدول مصارف)",
            "text": (
                "شامل: اعتبارات موضوع واگذاری سهام | بازپرداخت اصل اوراق بدهی | "
                "بازپرداخت اصل تسهیلات بانکی | تعهدات پرداخت‌نشده سال‌های قبل | "
                "بازپرداخت اصل وام‌های خارجی و تعهدات | واگذاری طرح‌های تملک دارایی‌های سرمایه‌ای | "
                "سرمایه‌گذاری و کمک‌های فرهنگی و اقتصادی بین‌المللی."
            ),
        },
        {
            "title": "بخش‌های درآمدها (جدول منابع)",
            "text": (
                "بخش اول: درآمدهای مالیاتی | بخش دوم: درآمدهای ناشی از کمک‌های اختصاصی | "
                "بخش سوم: درآمدهای حاصل از مالکیت دولت | بخش چهارم: درآمدهای حاصل از فروش کالا و خدمات | "
                "بخش پنجم: درآمدهای حاصل از جرایم و خسارات | بخش ششم: درآمدهای متفرقه."
            ),
        },
        {
            "title": "بندهای واگذاری دارایی‌های سرمایه‌ای (جدول منابع)",
            "text": (
                "بند اول: منابع حاصل از نفت و فرآورده‌های نفتی | "
                "بند دوم: منابع حاصل از فروش و واگذاری اموال منقول و غیر منقول | "
                "بند سوم: منابع حاصل از واگذاری طرح تملک دارایی‌های سرمایه‌ای."
            ),
        },
        {
            "title": "بندهای واگذاری دارایی‌های مالی (جدول منابع)",
            "text": (
                "بند اول: منابع حاصل از فروش و واگذاری انواع اوراق مالی و اسلامی | "
                "بند دوم: منابع حاصل از استفاده از تسهیلات خارجی | "
                "بند سوم: منابع حاصل از استفاده از موجودی حساب ذخیره ارزی | "
                "بند چهارم: منابع حاصل از دریافت اصل وام‌ها | "
                "بند پنجم: منابع حاصل از واگذاری شرکت‌های دولتی | "
                "بند ششم: منابع حاصل از برگشتی سال‌های قبل | "
                "بند هفتم: منابع حاصل از استفاده از صندوق توسعه ملی | "
                "بند هشتم: منابع حاصل از سایر واگذاری‌ها | "
                "بند نهم: انتشار اوراق صکوک اجاره به منظور تسویه مطالبات قطعی اشخاص حقیقی و حقوقی."
            ),
        },
    ]

    docs: List[Dict[str, Any]] = []
    for i, ch in enumerate(guide_chunks):
        docs.append(
            {
                "text": f"{ch['title']}\n\n{ch['text']}",
                "metadata": {
                    "doc_type": "budget_guide",
                    "section": ch["title"],
                    "category": "both",
                    "category_fa": "راهنما",
                    "order": i + 1,
                },
            }
        )
    return docs


# ==============================================================
# ChromaDB upload
# ==============================================================

def upload_to_chromadb(chunks: List[Dict[str, Any]]) -> None:
    client = chromadb.PersistentClient(
        path=DB_PATH,
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
    )

    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"🗑️  Deleted existing collection: {COLLECTION_NAME}")
    except Exception as e:
        logger.info(f"ℹ️  No existing collection to delete ({e})")

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "description": (
                "جداول ۱ تا ۴ کتاب بودجه (منابع و مصارف) با ساختار درختی و "
                "مقادیر تجمیع‌شده به‌ازای سال ۱۳۹۸ تا ۱۴۰۳."
            ),
            "source_files": "tables 1-4-budget.xlsx, tree-chart-budget-guide.pdf",
            "years": ",".join(str(y) for y in AVAILABLE_YEARS),
            "default_year": str(DEFAULT_YEAR),
            "total_chunks": len(chunks),
            "embedding_model": "heydariAI/persian-embeddings",
            "embedding_dim": EMBEDDING_DIM,
            "created_at": datetime.now().isoformat(),
            "version": "1",
        },
    )

    from services.persian_embedding_service import get_heydari_model
    logger.info("🔄 Loading heydariAI/persian-embeddings model…")
    model = get_heydari_model()
    logger.info("✅ Embedding model ready")

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids: List[str] = []
    for i, c in enumerate(chunks):
        key = f"{c['metadata'].get('doc_type','x')}|{c['metadata'].get('node_uid','')}|{c['metadata'].get('year','')}|{i}"
        ids.append(f"{COLLECTION_NAME}_{i}_{hashlib.md5(key.encode()).hexdigest()[:10]}")

    batch_size = 32
    for start in range(0, len(texts), batch_size):
        batch_texts = texts[start : start + batch_size]
        batch_meta = metadatas[start : start + batch_size]
        batch_ids = ids[start : start + batch_size]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        collection.add(
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        logger.info(f"  ✓ Added {min(start + batch_size, len(texts))}/{len(texts)} chunks")

    logger.info(f"\n✅ Collection '{COLLECTION_NAME}' ready with {collection.count()} documents")


# ==============================================================
# Main
# ==============================================================

def main() -> None:
    logger.info("=" * 80)
    logger.info("🚀 Building budget_tables collection")
    logger.info("=" * 80)

    nodes, roots = build_tree()
    logger.info(f"🌳 Built tree: {len(nodes)} nodes total "
                f"(منابع={sum(1 for n in nodes.values() if n.category=='manabe')}, "
                f"مصارف={sum(1 for n in nodes.values() if n.category=='masaref')})")

    # Sanity check: 1403 totals should match user's example numbers
    for cat, root in roots.items():
        v = compute_node_value(root, 1403)
        logger.info(f"  • {CATEGORY_FA[cat]} — {root.name} (1403): {_format_amount(v)} میلیون ریال")

    node_docs = build_node_documents(nodes)
    summary_docs = build_root_summary_documents(roots, nodes)
    guide_docs = build_guide_documents()

    all_chunks = node_docs + summary_docs + guide_docs
    logger.info(
        f"📦 Prepared {len(all_chunks)} chunks "
        f"(nodes={len(node_docs)}, summaries={len(summary_docs)}, guide={len(guide_docs)})"
    )

    upload_to_chromadb(all_chunks)

    logger.info("\n" + "=" * 80)
    logger.info("✅ budget_tables build COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
