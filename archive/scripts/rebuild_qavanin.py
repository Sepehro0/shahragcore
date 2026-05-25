#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild qavanin collection with correct embedding model
"""

import sys
import chromadb
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from services.persian_embedding_service import get_current_embedding_dim

def main():
    print("🔧 Rebuilding qavanin collection...")
    
    # Check current embedding dimension
    current_dim = get_current_embedding_dim()
    print(f"✅ Current embedding dimension: {current_dim}")
    
    # Connect to database
    client = chromadb.PersistentClient(path='./chroma_db')
    
    # Check if qavanin exists
    collections = [col.name for col in client.list_collections()]
    
    if 'qavanin' in collections:
        print(f"⚠️  qavanin collection exists, checking dimension...")
        
        try:
            col = client.get_collection('qavanin')
            sample = col.get(limit=1, include=['embeddings'])
            
            if sample and 'embeddings' in sample and len(sample['embeddings']) > 0:
                old_dim = len(sample['embeddings'][0])
                print(f"   Old dimension: {old_dim}")
                
                if old_dim != current_dim:
                    print(f"❌ Dimension mismatch! ({old_dim} != {current_dim})")
                    print(f"🗑️  Deleting old collection...")
                    client.delete_collection('qavanin')
                    print(f"✅ Deleted!")
                else:
                    print(f"✅ Dimension matches, no need to rebuild")
                    return 0
            else:
                print(f"⚠️  Empty collection, deleting...")
                client.delete_collection('qavanin')
                
        except Exception as e:
            print(f"⚠️  Error checking collection: {e}")
            print(f"🗑️  Deleting collection...")
            client.delete_collection('qavanin')
    
    print(f"\n✅ Ready to recreate qavanin collection")
    print(f"📌 Run: python3 scripts/create_qavanin_collection.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
