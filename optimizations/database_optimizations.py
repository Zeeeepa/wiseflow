"""
Database optimization utilities for WiseFlow.

This module provides functions to optimize database operations in WiseFlow.
"""

import os
import aiosqlite
import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

async def add_indexes(db_path: str) -> None:
    """
    Add indexes to frequently queried fields in the database.
    
    Args:
        db_path: Path to the SQLite database
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            # Check if tables exist
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='crawled_data'"
            ) as cursor:
                if not await cursor.fetchone():
                    logger.warning("crawled_data table does not exist")
                    return
            
            # Check if indexes exist
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_crawled_data_url'"
            ) as cursor:
                if await cursor.fetchone():
                    logger.info("URL index already exists")
                else:
                    # Add index on URL
                    await db.execute("CREATE INDEX idx_crawled_data_url ON crawled_data(url)")
                    logger.info("Created index on URL")
            
            # Add index on hash if it exists
            async with db.execute(
                "PRAGMA table_info(crawled_data)"
            ) as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'hash' in column_names:
                    async with db.execute(
                        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_crawled_data_hash'"
                    ) as cursor:
                        if await cursor.fetchone():
                            logger.info("Hash index already exists")
                        else:
                            await db.execute("CREATE INDEX idx_crawled_data_hash ON crawled_data(hash)")
                            logger.info("Created index on hash")
            
            # Add index on timestamp if it exists
            if 'timestamp' in column_names:
                async with db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_crawled_data_timestamp'"
                ) as cursor:
                    if await cursor.fetchone():
                        logger.info("Timestamp index already exists")
                    else:
                        await db.execute("CREATE INDEX idx_crawled_data_timestamp ON crawled_data(timestamp)")
                        logger.info("Created index on timestamp")
            
            await db.commit()
            logger.info("Database indexes added successfully")
    except Exception as e:
        logger.error(f"Error adding database indexes: {e}")
        raise

async def optimize_database(db_path: str) -> None:
    """
    Optimize the database by running VACUUM and ANALYZE.
    
    Args:
        db_path: Path to the SQLite database
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode to NORMAL for better performance
            await db.execute("PRAGMA synchronous = NORMAL")
            
            # Set cache size to 10000 pages (about 40MB)
            await db.execute("PRAGMA cache_size = 10000")
            
            # Run ANALYZE to update statistics
            await db.execute("ANALYZE")
            
            # Run VACUUM to defragment the database
            await db.execute("VACUUM")
            
            logger.info("Database optimized successfully")
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        raise

async def check_query_performance(db_path: str) -> Dict[str, float]:
    """
    Check the performance of common queries.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Dictionary with query names and execution times
    """
    results = {}
    
    try:
        async with aiosqlite.connect(db_path) as db:
            # Enable query timing
            await db.execute("PRAGMA query_only = ON")
            
            # Test URL lookup
            start_time = asyncio.get_event_loop().time()
            await db.execute("EXPLAIN QUERY PLAN SELECT * FROM crawled_data WHERE url = ?", ("https://example.com",))
            results["url_lookup"] = asyncio.get_event_loop().time() - start_time
            
            # Test count query
            start_time = asyncio.get_event_loop().time()
            await db.execute("EXPLAIN QUERY PLAN SELECT COUNT(*) FROM crawled_data")
            results["count_query"] = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Query performance check results: {results}")
            return results
    except Exception as e:
        logger.error(f"Error checking query performance: {e}")
        raise

async def optimize_all_databases() -> None:
    """
    Optimize all databases used by WiseFlow.
    """
    # Main crawl4ai database
    crawl4ai_db_path = os.path.join(
        os.getenv("PROJECT_DIR", ""), ".crawl4ai", "crawl4ai.db"
    )
    
    if os.path.exists(crawl4ai_db_path):
        logger.info(f"Optimizing database: {crawl4ai_db_path}")
        await add_indexes(crawl4ai_db_path)
        await optimize_database(crawl4ai_db_path)
        await check_query_performance(crawl4ai_db_path)
    else:
        logger.warning(f"Database not found: {crawl4ai_db_path}")
    
    # Add other databases as needed

