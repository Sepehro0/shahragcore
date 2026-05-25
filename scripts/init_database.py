# -*- coding: utf-8 -*-
"""
Database Initialization Script
اسکریپت راه‌اندازی پایگاه داده PostgreSQL
"""

import sys
import os
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Change to parent directory to fix imports
os.chdir(parent_dir)

from services.database_service import DatabaseService
from config.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """تابع اصلی"""
    logger.info("🗄️ Initializing PostgreSQL database...")
    
    try:
        # Load settings
        settings = Settings()
        
        # Create database service
        db_service = DatabaseService(settings)
        
        # Test connection
        if not db_service.test_connection():
            logger.error("❌ Database connection failed!")
            logger.info("Please ensure PostgreSQL is running and credentials are correct.")
            return False
        
        # Create tables
        logger.info("Creating database tables...")
        db_service.create_tables()
        
        logger.info("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

