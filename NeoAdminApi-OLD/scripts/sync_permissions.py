#!/usr/bin/env python
"""
Script to manually sync permissions from code to database.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import create_app
from src.common.database.connection import init_database, close_database
from src.common.cache.client import init_cache, close_cache
from src.features.auth.services.permission_manager import PermissionSyncManager
from loguru import logger


async def main(dry_run: bool = False, force_update: bool = False):
    """
    Sync permissions from code to database.
    
    Args:
        dry_run: If True, preview changes without applying
        force_update: If True, update existing permissions
    """
    try:
        # Initialize connections
        logger.info("Initializing database and cache connections...")
        await init_database()
        await init_cache()
        
        # Create app to scan endpoints
        logger.info("Creating FastAPI app to scan endpoints...")
        app = create_app()
        
        # Run permission sync
        logger.info(f"Starting permission sync (dry_run={dry_run}, force_update={force_update})...")
        sync_manager = PermissionSyncManager()
        result = await sync_manager.sync_permissions(
            app=app,
            dry_run=dry_run,
            force_update=force_update
        )
        
        # Print results
        if result['success']:
            print("\n" + "=" * 80)
            print("PERMISSION SYNC SUCCESSFUL")
            print("=" * 80)
            print(f"\nStatistics:")
            print(f"  Added: {result['stats']['added']}")
            print(f"  Updated: {result['stats']['updated']}")
            print(f"  Skipped: {result['stats']['skipped']}")
            print(f"  Errors: {result['stats']['errors']}")
            
            if 'report' in result:
                print("\nDetailed Report:")
                print(result['report'])
        else:
            print("\n" + "=" * 80)
            print("PERMISSION SYNC FAILED")
            print("=" * 80)
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Permission sync failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await close_database()
        await close_cache()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync permissions from code to database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update existing permissions"
    )
    
    args = parser.parse_args()
    
    # Run the sync
    asyncio.run(main(dry_run=args.dry_run, force_update=args.force_update))