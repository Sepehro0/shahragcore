# -*- coding: utf-8 -*-
"""
Complete rebuild of budget_financial collection with ALL data
"""

import chromadb
import pandas as pd
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

print("🚀 Starting COMPLETE rebuild of budget_financial collection...")

# 1. Delete existing collection
print("\n1️⃣ Deleting existing collection...")
client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
try:
    client.delete_collection("budget_financial")
    print("   ✅ Deleted budget_financial collection")
except Exception as e:
    print(f"   ⚠️ Could not delete: {e}")

# 2. Create new collection
print("\n2️⃣ Creating new collection...")
collection = client.create_collection(
    name="budget_financial",
    metadata={"description": "Budget Financial Data - Masaref3 and Manabe3 (Full)"}
)
print(f"   ✅ Created new collection")

# 3. Load and process files
print("\n3️⃣ Loading Excel files...")
df_masaref = pd.read_excel("archive/data_files/masaref3.xlsx")
df_manabe = pd.read_excel("archive/data_files/manabe3.xlsx")
print(f"   - masaref3.xlsx: {len(df_masaref)} rows")
print(f"   - manabe3.xlsx: {len(df_manabe)} rows")

# Helper functions
def clean_value(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()

def format_currency(value):
    try:
        if pd.isna(value) or value is None or value == "":
            return "0"
        if isinstance(value, str):
            value = float(value.replace(',', ''))
        return f"{int(value):,}"
    except:
        return "0"

def get_col(row, names, default=""):
    for name in names:
        if name in row.index:
            val = row.get(name)
            if not pd.isna(val):
                return val
    return default

# 4. Process masaref documents
print("\n4️⃣ Processing masaref3.xlsx documents...")
masaref_docs = []
masaref_ids = []
masaref_metas = []

for idx, row in df_masaref.iterrows():
    main_org = clean_value(get_col(row, ['عنوان دستگاه اصلي', 'عنوان_دستگاه_اصلي']))
    exec_org = clean_value(get_col(row, ['عنوان دستگاه اجرايي ', 'عنوان_دستگاه_اجرايي']))
    exec_code = clean_value(get_col(row, ['کد دستگاه اجرايي ', 'کد_دستگاه_اجرايي']))
    year = clean_value(get_col(row, ['سال ', 'سال']))
    
    expense_total = get_col(row, ['جمع براورد اعتبارات هزینه ای', 'جمع_براورد_اعتبارات_هزینه_ای'], 0)
    capital_total = get_col(row, ['جمع برآورد تملك دارايي هاي سرمايه اي', 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_اي'], 0)
    grand_total = get_col(row, ['جمع كل ', 'جمع_كل', 'جمع کل'], 0)
    
    text = f"""دستگاه اصلی: {main_org}
دستگاه اجرایی: {exec_org}
کد دستگاه: {exec_code}
سال: {year}

اعتبارات هزینه‌ای: {format_currency(expense_total)} میلیون ریال
تملک دارایی‌های سرمایه‌ای: {format_currency(capital_total)} میلیون ریال
جمع کل بودجه: {format_currency(grand_total)} میلیون ریال"""
    
    masaref_docs.append(text)
    masaref_ids.append(f"masaref_{idx}")
    masaref_metas.append({
        "source": "masaref3.xlsx",
        "doc_type": "masaref",
        "main_org": main_org,
        "exec_org": exec_org,
        "year": str(year)
    })

print(f"   - Processed {len(masaref_docs)} masaref documents")

# 5. Process manabe documents
print("\n5️⃣ Processing manabe3.xlsx documents...")
manabe_docs = []
manabe_ids = []
manabe_metas = []

for idx, row in df_manabe.iterrows():
    section_title = clean_value(get_col(row, ['عنوان قسمت ', 'عنوان_قسمت']))
    part_title = clean_value(get_col(row, ['عنوان بخش ', 'عنوان_بخش']))
    item_title = clean_value(get_col(row, ['عنوان بند', 'عنوان_بند']))
    sub_title = clean_value(get_col(row, ['عنوان جزء ', 'عنوان_جزء']))
    exec_org = clean_value(get_col(row, ['عنوان دستگاه اجرایی', 'عنوان_دستگاه_اجرایی']))
    main_org = clean_value(get_col(row, ['عنوان دستگاه اصلی', 'عنوان_دستگاه_اصلی']))
    year = clean_value(get_col(row, ['سال', 'سال ']))
    
    grand_total = get_col(row, ['جمع کل', 'جمع_کل'], 0)
    
    text = f"""قسمت: {section_title}
بخش: {part_title}
بند: {item_title}
جزء: {sub_title}
دستگاه اجرایی: {exec_org}
دستگاه اصلی: {main_org}
سال: {year}

جمع کل: {format_currency(grand_total)} میلیون ریال"""
    
    manabe_docs.append(text)
    manabe_ids.append(f"manabe_{idx}")
    manabe_metas.append({
        "source": "manabe3.xlsx",
        "doc_type": "manabe",
        "main_org": main_org,
        "exec_org": exec_org,
        "year": str(year)
    })

print(f"   - Processed {len(manabe_docs)} manabe documents")

# 6. Upload to ChromaDB in batches
print("\n6️⃣ Uploading to ChromaDB...")
all_docs = masaref_docs + manabe_docs
all_ids = masaref_ids + manabe_ids
all_metas = masaref_metas + manabe_metas

batch_size = 1000
total = len(all_docs)

for i in range(0, total, batch_size):
    batch_docs = all_docs[i:i+batch_size]
    batch_ids = all_ids[i:i+batch_size]
    batch_metas = all_metas[i:i+batch_size]
    
    collection.add(
        documents=batch_docs,
        ids=batch_ids,
        metadatas=batch_metas
    )
    
    uploaded = min(i + batch_size, total)
    print(f"   - Uploaded {uploaded}/{total} documents...")

# 7. Verify
print("\n7️⃣ Verifying...")
final_count = collection.count()
print(f"   ✅ Collection now has {final_count} documents")
print(f"   Expected: {total}")

if final_count == total:
    print("\n🎉 SUCCESS! All documents uploaded correctly!")
else:
    print(f"\n⚠️ WARNING: Count mismatch! Expected {total}, got {final_count}")

# 8. Now rebuild database tables
print("\n8️⃣ Rebuilding database tables...")
from services.database_service import DatabaseService
db_service = DatabaseService()

# Normalize column names for masaref
df_masaref.columns = [col.strip().replace(' ', '_').replace('ي', 'ی').replace('ك', 'ک') for col in df_masaref.columns]
print(f"   - Creating masaref_sheet1 table...")
try:
    result = db_service.create_table_from_dataframe(
        collection_name="budget_financial",
        table_name="masaref_sheet1",
        sheet_name="Sheet1",
        source_file="masaref3.xlsx",
        dataframe=df_masaref
    )
    print(f"   ✅ Created masaref_sheet1")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Normalize column names for manabe
df_manabe.columns = [col.strip().replace(' ', '_').replace('ي', 'ی').replace('ك', 'ک') for col in df_manabe.columns]
print(f"   - Creating manabe_sheet1 table...")
try:
    result = db_service.create_table_from_dataframe(
        collection_name="budget_financial",
        table_name="manabe_sheet1",
        sheet_name="Sheet1",
        source_file="manabe3.xlsx",
        dataframe=df_manabe
    )
    print(f"   ✅ Created manabe_sheet1")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n✅ COMPLETE REBUILD DONE!")

