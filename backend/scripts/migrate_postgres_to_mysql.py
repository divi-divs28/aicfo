#!/usr/bin/env python3
"""
Migration script: copy data from PostgreSQL to MySQL

Usage:
  # Set environment variables for both databases
  # POSTGRES_URL - Source PostgreSQL database
  # DATABASE_URL - Target MySQL database
  
  pip install psycopg2-binary pymysql sqlalchemy python-dotenv
  python backend/scripts/migrate_postgres_to_mysql.py

Notes:
 - The script reads POSTGRES_URL (source) and DATABASE_URL (target MySQL).
 - It will create missing tables in MySQL via SQLAlchemy `Base.metadata.create_all`.
 - It merges records by id (so running it multiple times is safe / idempotent).
 - Handles data type conversions between PostgreSQL and MySQL.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Source: PostgreSQL (Production)
# Check for PostgreSQL-specific variables first, then fall back to DATABASE_URL
POSTGRES_URL = os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL_POSTGRES')

# If not explicitly set, check if DATABASE_URL is PostgreSQL
if not POSTGRES_URL:
    database_url = os.getenv('DATABASE_URL', '')
    # If DATABASE_URL looks like PostgreSQL, use it as source
    if 'postgres' in database_url.lower():
        POSTGRES_URL = database_url
        print("📌 Using DATABASE_URL as PostgreSQL source")

# If still not set, try to construct from components
if not POSTGRES_URL:
    pg_host = os.getenv('POSTGRES_HOST', 'localhost')
    pg_port = os.getenv('POSTGRES_PORT', '5432')
    pg_user = os.getenv('POSTGRES_USER', 'postgres')
    pg_password = os.getenv('POSTGRES_PASSWORD', '')
    pg_database = os.getenv('POSTGRES_DB', 'reporting_manager')
    
    if pg_password:
        POSTGRES_URL = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    else:
        POSTGRES_URL = f"postgresql+psycopg2://{pg_user}@{pg_host}:{pg_port}/{pg_database}"

# Target: MySQL RDS
# Must be explicitly set as MYSQL_URL or MYSQL_DATABASE_URL
MYSQL_URL = os.getenv('MYSQL_URL') or os.getenv('MYSQL_DATABASE_URL') or os.getenv('DATABASE_URL_MYSQL')

if not MYSQL_URL:
    # Try to assemble from DB_HOST/DB_PORT/DB_USER/DB_PASSWORD
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'reporting_manager')
    if db_password:
        MYSQL_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        MYSQL_URL = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"

# Validate that both URLs are set
if not POSTGRES_URL:
    print("❌ ERROR: PostgreSQL source database not configured!", file=sys.stderr)
    print("   Set DATABASE_URL (if PostgreSQL) or POSTGRES_URL in your .env file", file=sys.stderr)
    sys.exit(1)

if not MYSQL_URL:
    print("❌ ERROR: MySQL target database not configured!", file=sys.stderr)
    print("   Set MYSQL_URL or MYSQL_DATABASE_URL in your .env file", file=sys.stderr)
    sys.exit(1)

# Convert async drivers to sync for this script
sync_postgres_url = POSTGRES_URL.replace('+asyncpg', '+psycopg2').replace('+psycopg', '+psycopg2')
sync_mysql_url = MYSQL_URL.replace('+aiomysql', '+pymysql')

# Check they're different databases
if sync_postgres_url == sync_mysql_url:
    print("❌ ERROR: Source and target databases are the same!", file=sys.stderr)
    print("   PostgreSQL and MySQL URLs must be different", file=sys.stderr)
    sys.exit(1)


def to_datetime(value: Any) -> datetime | None:
    """Convert various datetime formats to Python datetime"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle string dates
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        try:
            return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Migrate PostgreSQL data to MySQL')
    parser.add_argument('--dry-run', action='store_true', help='Do not commit changes to MySQL; show what would be done')
    parser.add_argument('--tables', type=str, help='Comma-separated list of tables to migrate (default: all)')
    parser.add_argument('--skip-tables', type=str, help='Comma-separated list of tables to skip')
    args = parser.parse_args()

    dry_run = args.dry_run
    selected_tables = None
    skip_tables = set()
    
    if args.tables:
        selected_tables = {t.strip() for t in args.tables.split(',') if t.strip()}
    if args.skip_tables:
        skip_tables = {t.strip() for t in args.skip_tables.split(',') if t.strip()}

    # Check dependencies
    try:
        import psycopg2
    except ImportError:
        print("Missing dependency 'psycopg2-binary'. Install with: pip install psycopg2-binary", file=sys.stderr)
        return 2

    try:
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import Session
        # Import models and Base from the project
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from database import Base, User, Property, Auction, Bid, ChatMessage, QuestionCategory, SuggestedQuestion, DashboardCard
    except Exception as e:
        print(f"Error importing SQLAlchemy or models: {e}", file=sys.stderr)
        return 3

    print(f"🔍 Connecting to PostgreSQL (source) at {sync_postgres_url.split('@')[1] if '@' in sync_postgres_url else 'database'}")
    try:
        postgres_engine = create_engine(sync_postgres_url, pool_pre_ping=True)
        # Test connection
        with postgres_engine.connect() as conn:
            print("✅ PostgreSQL connection successful")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}", file=sys.stderr)
        return 4

    print(f"\n🔍 Connecting to MySQL (target) at {sync_mysql_url.split('@')[1] if '@' in sync_mysql_url else 'database'}")
    try:
        mysql_engine = create_engine(sync_mysql_url, pool_pre_ping=True)
        # Test connection
        with mysql_engine.connect() as conn:
            print("✅ MySQL connection successful")
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}", file=sys.stderr)
        return 5

    # Ensure MySQL tables exist
    print("\n📋 Ensuring MySQL tables exist (create if missing)...")
    try:
        Base.metadata.create_all(mysql_engine)
        print("✅ MySQL tables ready")
    except Exception as e:
        print(f"❌ Failed to create MySQL tables: {e}", file=sys.stderr)
        return 6

    # Get list of tables from PostgreSQL
    inspector = inspect(postgres_engine)
    available_tables = inspector.get_table_names()
    
    print(f"\n📊 Found {len(available_tables)} tables in PostgreSQL: {', '.join(available_tables)}")

    # Tables to migrate with their corresponding SQLAlchemy models
    table_model_map = {
        'users': User,
        'properties': Property,
        'auctions': Auction,
        'bids': Bid,
        'chat_messages': ChatMessage,
        'question_categories': QuestionCategory,
        'suggested_questions': SuggestedQuestion,
        'dashboard_cards': DashboardCard,
    }

    total_migrated = 0

    with Session(postgres_engine) as pg_session, Session(mysql_engine) as mysql_session:
        for table_name, Model in table_model_map.items():
            # Check if table should be processed
            if selected_tables and table_name not in selected_tables:
                print(f"\n⏭️  Skipping {table_name} (not selected)")
                continue
            
            if table_name in skip_tables:
                print(f"\n⏭️  Skipping {table_name} (explicitly skipped)")
                continue
                
            if table_name not in available_tables:
                print(f"\n⚠️  Table {table_name} not found in PostgreSQL, skipping")
                continue

            print(f"\n🔄 Migrating table: {table_name}")
            
            try:
                # Query all records from PostgreSQL
                records = pg_session.query(Model).all()
                print(f"   📦 Found {len(records)} records in PostgreSQL")

                if len(records) == 0:
                    print(f"   ℹ️  No records to migrate")
                    continue

                # Migrate each record
                migrated_count = 0
                error_count = 0
                
                for record in records:
                    try:
                        # Convert SQLAlchemy object to dict
                        record_dict = {
                            column.name: getattr(record, column.name)
                            for column in Model.__table__.columns
                        }
                        
                        # Create new instance for MySQL
                        new_record = Model(**record_dict)
                        
                        # Merge (insert or update) into MySQL
                        mysql_session.merge(new_record)
                        migrated_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        print(f"   ⚠️  Failed to migrate record {getattr(record, 'id', '?')}: {e}")

                # Commit per table
                if dry_run:
                    print(f"   🔍 DRY RUN: Would migrate {migrated_count} records (rolling back)")
                    mysql_session.rollback()
                else:
                    try:
                        mysql_session.commit()
                        print(f"   ✅ Successfully migrated {migrated_count} records")
                        total_migrated += migrated_count
                        
                        if error_count > 0:
                            print(f"   ⚠️  {error_count} records failed")
                    except Exception as e:
                        print(f"   ❌ Commit failed for {table_name}: {e}")
                        mysql_session.rollback()

            except Exception as e:
                print(f"   ❌ Error migrating {table_name}: {e}")
                mysql_session.rollback()

    print("\n" + "="*60)
    if dry_run:
        print("🔍 DRY RUN COMPLETED - No data was actually migrated")
    else:
        print(f"✅ MIGRATION COMPLETED - {total_migrated} total records migrated")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

