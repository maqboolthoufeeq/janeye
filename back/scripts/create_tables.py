#!/usr/bin/env python
"""
Script to create database tables for JanEye application
"""

# Standard library imports
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Third-party imports
from sqlalchemy import text

# Local application imports
from app.core.db import get_async_session
from app.core.db.create_async_engine import async_engine

# Import all models to register them with Base
from app.models.base import Base


async def create_tables():
    """Create all tables in the database"""
    print("Creating database tables...")

    try:
        # Create all tables
        async with async_engine.begin() as conn:
            # Drop existing tables if needed (BE CAREFUL IN PRODUCTION!)
            # await conn.run_sync(Base.metadata.drop_all)

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        print("✅ All tables created successfully!")

        # Verify tables were created
        async for db in get_async_session():
            result = await db.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
                )
            )
            tables = result.fetchall()

            print("\nCreated tables:")
            for table in tables:
                print(f"  - {table[0]}")
            break

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_tables())
