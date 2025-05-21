#!/usr/bin/env python3
"""
Apply performance optimizations to WiseFlow.

This script applies all performance optimizations to the WiseFlow project.
"""

import os
import sys
import asyncio
import logging
import argparse
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Apply performance optimizations to WiseFlow")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmarks after applying optimizations")
    parser.add_argument("--patch-only", action="store_true", help="Only patch modules without applying optimizations")
    args = parser.parse_args()
    
    try:
        # Import optimization modules
        from optimizations.apply_optimizations import apply_all_optimizations, patch_modules
        from optimizations.benchmark import run_benchmarks
        
        # Apply optimizations
        if not args.patch_only:
            logger.info("Applying performance optimizations...")
            await apply_all_optimizations()
            logger.info("Performance optimizations applied successfully")
        
        # Patch modules
        logger.info("Patching modules...")
        patch_modules()
        logger.info("Modules patched successfully")
        
        # Run benchmarks if requested
        if args.benchmark:
            logger.info("Running benchmarks...")
            await run_benchmarks()
            logger.info("Benchmarks completed")
        
        logger.info("All operations completed successfully")
    except Exception as e:
        logger.error(f"Error applying optimizations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

