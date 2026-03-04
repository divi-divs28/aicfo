#!/usr/bin/env python3
"""
Verification script: Check data counts in both PostgreSQL and MySQL after migration

Usage:
  python backend/scripts/verify_migration.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

# Get database URLs
POSTGRES_URL = os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL_POSTGRES')
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

MYSQL_URL = os.getenv('DATABASE_URL') or os.getenv('MYSQL_URL')
if not MYSQL_URL:
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'reporting_manager')
    if db_password:
        MYSQL_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        MYSQL_URL = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"

# Convert to sync
sync_postgres_url = POSTGRES_URL.replace('+asyncpg', '+psycopg2').replace('+psycopg', '+psycopg2')
sync_mysql_url = MYSQL_URL.replace('+aiomysql', '+pymysql')


def get_table_count(engine, table_name):
    """Get count of records in a table"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
    except Exception as e:
        return f"ERROR: {e}"


def main():
    print("=" * 80)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 80)
    
    # Connect to databases
    print("\n🔍 Connecting to databases...")
    
    try:
        print(f"   PostgreSQL: {sync_postgres_url.split('@')[1] if '@' in sync_postgres_url else 'connecting...'}")
        pg_engine = create_engine(sync_postgres_url, pool_pre_ping=True)
        with pg_engine.connect():
            print("   ✅ PostgreSQL connected")
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        pg_engine = None
    
    try:
        print(f"   MySQL: {sync_mysql_url.split('@')[1] if '@' in sync_mysql_url else 'connecting...'}")
        mysql_engine = create_engine(sync_mysql_url, pool_pre_ping=True)
        with mysql_engine.connect():
            print("   ✅ MySQL connected")
    except Exception as e:
        print(f"   ❌ MySQL connection failed: {e}")
        mysql_engine = None
    
    if not pg_engine or not mysql_engine:
        print("\n❌ Could not connect to both databases. Please check your configuration.")
        return 1
    
    # Get tables
    pg_inspector = inspect(pg_engine)
    pg_tables = set(pg_inspector.get_table_names())
    
    mysql_inspector = inspect(mysql_engine)
    mysql_tables = set(mysql_inspector.get_table_names())
    
    # Tables to check
    expected_tables = [
        'users',
        'properties', 
        'auctions',
        'bids',
        'chat_messages',
        'question_categories',
        'suggested_questions',
        'dashboard_cards'
    ]
    
    print("\n" + "=" * 80)
    print("RECORD COUNT COMPARISON")
    print("=" * 80)
    print(f"\n{'Table':<25} {'PostgreSQL':<15} {'MySQL':<15} {'Status':<15}")
    print("-" * 80)
    
    total_pg = 0
    total_mysql = 0
    all_match = True
    
    for table in expected_tables:
        pg_count = get_table_count(pg_engine, table) if table in pg_tables else "N/A"
        mysql_count = get_table_count(mysql_engine, table) if table in mysql_tables else "N/A"
        
        # Update totals
        if isinstance(pg_count, int):
            total_pg += pg_count
        if isinstance(mysql_count, int):
            total_mysql += mysql_count
        
        # Determine status
        if pg_count == mysql_count:
            status = "✅ MATCH"
        elif pg_count == "N/A" and mysql_count == 0:
            status = "⚠️  EMPTY"
        elif pg_count == "N/A":
            status = "⚠️  PG MISSING"
        elif mysql_count == "N/A":
            status = "⚠️  MYSQL MISSING"
        else:
            status = "❌ MISMATCH"
            all_match = False
        
        print(f"{table:<25} {str(pg_count):<15} {str(mysql_count):<15} {status:<15}")
    
    print("-" * 80)
    print(f"{'TOTAL':<25} {total_pg:<15} {total_mysql:<15}")
    
    print("\n" + "=" * 80)
    if all_match and total_mysql > 0:
        print("✅ SUCCESS: All tables migrated successfully!")
        print(f"   Total records in MySQL: {total_mysql}")
    elif total_mysql == 0:
        print("⚠️  WARNING: No data found in MySQL. Migration may not have run yet.")
    else:
        print("❌ WARNING: Some tables have mismatched counts.")
        print("   This could be normal if data changed during migration.")
        print("   Review the counts above to ensure important data migrated.")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

