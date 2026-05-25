# -*- coding: utf-8 -*-
"""
بازسازی کامل کالکشن budget_financial با embedding function صحیح
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from core.refactored_rag_system import RefactoredRAGSystem
from services.database_service import DatabaseService
from services.persian_embedding_service import PersianEmbeddingService
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def rebuild_budget_collection():
    """بازسازی کامل کالکشن budget_financial"""
    
    collection_name = "budget_financial"
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🚀 بازسازی کامل کالکشن budget_financial با embedding صحیح")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 1: حذف کالکشن قبلی
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📋 مرحله 1: حذف کالکشن قبلی")
    
    rag_system = RefactoredRAGSystem()
    
    try:
        rag_system.chroma_client.delete_collection(collection_name)
        logger.info(f"✅ کالکشن قبلی {collection_name} حذف شد")
    except Exception as e:
        logger.info(f"ℹ️ کالکشن قبلی وجود نداشت: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 2: ساخت embedding function
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n🔧 مرحله 2: ساخت embedding function")
    
    # استفاده از Persian Embedding Service
    persian_embedding = PersianEmbeddingService()
    
    # تست embedding
    test_text = "تست embedding"
    test_embedding = persian_embedding.generate_embeddings([test_text])
    embedding_dim = len(test_embedding[0])
    
    logger.info(f"✅ Embedding function آماده است")
    logger.info(f"   - Dimension: {embedding_dim}")
    logger.info(f"   - Model: Persian SentenceTransformer")
    
    # ساخت embedding function برای ChromaDB
    class PersianEmbeddingFunction:
        def __init__(self, persian_embedding):
            self.persian_embedding = persian_embedding
        
        def __call__(self, input):
            """ChromaDB embedding function interface"""
            if isinstance(input, str):
                input = [input]
            return self.persian_embedding.generate_embeddings(input)
        
        def embed_query(self, input):
            """ChromaDB query embedding interface"""
            if isinstance(input, str):
                input = [input]
            return self.persian_embedding.generate_embeddings(input)
        
        def embed_documents(self, input):
            """ChromaDB documents embedding interface"""
            if isinstance(input, str):
                input = [input]
            return self.persian_embedding.generate_embeddings(input)
    
    embedding_function = PersianEmbeddingFunction(persian_embedding)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 3: ساخت کالکشن جدید با embedding function صحیح
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n🗂️ مرحله 3: ساخت کالکشن جدید")
    
    collection = rag_system.chroma_client.create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={
            "description": "بودجه مالی کشور - منابع و مصارف",
            "domain": "financial",
            "type": "database",
            "embedding_model": "jina-persian",
            "embedding_dim": str(embedding_dim)
        }
    )
    
    logger.info(f"✅ کالکشن {collection_name} با embedding صحیح ایجاد شد")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 4: استخراج sample documents از دیتابیس
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📊 مرحله 4: استخراج sample documents از دیتابیس")
    
    db_service = DatabaseService()
    
    # Sample 1: مصارف (masaref2_sheet1)
    logger.info("   📄 استخراج نمونه‌های مصارف...")
    
    query_masaref = text("""
        SELECT 
            عنوان_دستگاه_اصلي,
            عنوان_دستگاه_اجرايي,
            براورد_اعتبارات_هزینه_ای_عمومی,
            برآورد_اعتبارات_هزینه_ای_متفرقه,
            براورد_اعتبارات_هزینه_ای_اختصاصی,
            جمع_براورد_اعتبارات_هزینه_ای,
            براورد_تملك_دارايي_هاي_سرمايه_اي_ع,
            براورد_تملك_دارايي_هاي_سرمايه_اي_م,
            براورد_تملك_دارايي_هاي_سرمايه_اي_ا,
            جمع_برآورد_تملك_دارايي_هاي_سرمايه_,
            جمع_كل,
            سال
        FROM masaref2_sheet1
        WHERE CAST(سال AS INTEGER) = 1403
        LIMIT 200
    """)
    
    with db_service.engine.connect() as conn:
        result = conn.execute(query_masaref)
        rows_masaref = result.fetchall()
    
    logger.info(f"   ✅ {len(rows_masaref)} سطر از مصارف استخراج شد")
    
    # Sample 2: منابع (manabe_sheet1)
    logger.info("   📄 استخراج نمونه‌های منابع...")
    
    query_manabe = text("""
        SELECT 
            عنوان_دستگاه_اجرایی,
            عنوان_دستگاه_اصلی,
            در_آمد_عمومي_ملي,
            در_آمد_عمومي_استاني,
            جمع_در_آمد_عمومي,
            در_آمد_اختصاصي_ملي,
            در_آمد_اختصاصي_استاني,
            جمع_در_آمد_اختصاصي,
            جمع_کل_ملي,
            جمع_کل_استاني,
            جمع_کل,
            سال
        FROM manabe_sheet1
        WHERE CAST(سال AS INTEGER) IN (1401, 1402, 1403)
        LIMIT 200
    """)
    
    with db_service.engine.connect() as conn:
        result = conn.execute(query_manabe)
        rows_manabe = result.fetchall()
    
    logger.info(f"   ✅ {len(rows_manabe)} سطر از منابع استخراج شد")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 5: ساخت documents و اضافه کردن به کالکشن
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📝 مرحله 5: ساخت documents و embedding")
    
    documents = []
    metadatas = []
    ids = []
    
    # Documents از مصارف
    for idx, row in enumerate(rows_masaref):
        # تبدیل None به 0
        values = [0 if v is None else v for v in row]
        
        doc_text = f"""دستگاه: {values[0]} - {values[1]}
سال: {values[11]}

اعتبارات هزینه‌ای:
- عمومی: {float(values[2]):,.0f} میلیون ریال
- متفرقه: {float(values[3]):,.0f} میلیون ریال
- اختصاصی: {float(values[4]):,.0f} میلیون ریال
- جمع: {float(values[5]):,.0f} میلیون ریال

تملک دارایی سرمایه‌ای:
- عمومی: {float(values[6]):,.0f} میلیون ریال
- متفرقه: {float(values[7]):,.0f} میلیون ریال
- اختصاصی: {float(values[8]):,.0f} میلیون ریال
- جمع: {float(values[9]):,.0f} میلیون ریال

جمع کل بودجه: {float(values[10]):,.0f} میلیون ریال
"""
        
        documents.append(doc_text)
        metadatas.append({
            "type": "budget_sample",
            "table": "masaref2_sheet1",
            "دستگاه_اصلی": str(values[0]),
            "دستگاه_اجرایی": str(values[1]),
            "سال": str(values[11]),
            "جمع_کل": str(values[10]),
            "source": "database"
        })
        ids.append(f"masaref_{idx}")
    
    # Documents از منابع
    for idx, row in enumerate(rows_manabe):
        # تبدیل None به 0
        values = [0 if v is None else v for v in row]
        
        doc_text = f"""دستگاه: {values[1]} - {values[0]}
سال: {values[11]}

درآمد عمومی:
- ملی: {float(values[2]):,.0f} میلیون ریال
- استانی: {float(values[3]):,.0f} میلیون ریال
- جمع: {float(values[4]):,.0f} میلیون ریال

درآمد اختصاصی:
- ملی: {float(values[5]):,.0f} میلیون ریال
- استانی: {float(values[6]):,.0f} میلیون ریال
- جمع: {float(values[7]):,.0f} میلیون ریال

جمع کل درآمد:
- ملی: {float(values[8]):,.0f} میلیون ریال
- استانی: {float(values[9]):,.0f} میلیون ریال
- کل: {float(values[10]):,.0f} میلیون ریال
"""
        
        documents.append(doc_text)
        metadatas.append({
            "type": "budget_sample",
            "table": "manabe_sheet1",
            "دستگاه_اصلی": str(values[1]),
            "دستگاه_اجرایی": str(values[0]),
            "سال": str(values[11]),
            "جمع_کل": str(values[10]),
            "source": "database"
        })
        ids.append(f"manabe_{idx}")
    
    # اضافه کردن metadata documents برای جداول
    documents.append("""جدول مصارف (masaref2_sheet1):
این جدول شامل اطلاعات مصارف بودجه کشور است.
ستون‌ها: اعتبارات هزینه‌ای (عمومی، متفرقه، اختصاصی)، تملک دارایی سرمایه‌ای (عمومی، متفرقه، اختصاصی)
تعداد سطرها: 5,318
سال‌های موجود: 1403
""")
    metadatas.append({
        "type": "table_metadata",
        "table": "masaref2_sheet1",
        "source": "database"
    })
    ids.append("table_meta_masaref")
    
    documents.append("""جدول منابع (manabe_sheet1):
این جدول شامل اطلاعات منابع و درآمدهای بودجه کشور است.
ستون‌ها: درآمد عمومی (ملی، استانی)، درآمد اختصاصی (ملی، استانی)
تعداد سطرها: 8,581
سال‌های موجود: 1401، 1402، 1403
""")
    metadatas.append({
        "type": "table_metadata",
        "table": "manabe_sheet1",
        "source": "database"
    })
    ids.append("table_meta_manabe")
    
    logger.info(f"   📊 تعداد documents: {len(documents)}")
    logger.info(f"   🔄 در حال ساخت embeddings...")
    
    # اضافه کردن به کالکشن (با batch processing)
    batch_size = 50
    total_added = 0
    
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
        
        total_added += len(batch_docs)
        logger.info(f"   ✅ {total_added}/{len(documents)} documents اضافه شد")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 6: تست کالکشن
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n🧪 مرحله 6: تست کالکشن")
    
    # تست query
    test_query = "نهاد ریاست جمهوری"
    logger.info(f"   🔍 تست query: '{test_query}'")
    
    results = collection.query(
        query_texts=[test_query],
        n_results=3
    )
    
    logger.info(f"   ✅ تعداد نتایج: {len(results['documents'][0])}")
    
    if results['documents'][0]:
        logger.info(f"   📋 اولین نتیجه:")
        logger.info(f"      {results['documents'][0][0][:200]}...")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # خلاصه نهایی
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("✅ بازسازی کامل budget_financial با موفقیت انجام شد!")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"\n📊 خلاصه:")
    logger.info(f"   - کالکشن: {collection_name}")
    logger.info(f"   - تعداد documents: {len(documents)}")
    logger.info(f"   - Embedding dimension: {embedding_dim}")
    logger.info(f"   - Embedding model: Jina (Persian)")
    logger.info(f"   - جداول دیتابیس: masaref2_sheet1 (5,318 rows), manabe_sheet1 (8,581 rows)")
    logger.info(f"\n🚀 سیستم آماده پاسخگویی به سوالات مالی است!")
    
    return {
        "success": True,
        "collection_name": collection_name,
        "documents_count": len(documents),
        "embedding_dim": embedding_dim
    }


if __name__ == "__main__":
    result = asyncio.run(rebuild_budget_collection())
    
    if result.get("success"):
        print("\n✅ بازسازی با موفقیت کامل شد!")
    else:
        print(f"\n❌ بازسازی با خطا مواجه شد")

