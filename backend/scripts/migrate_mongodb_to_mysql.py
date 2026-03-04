#!/usr/bin/env python3
"""
Migration script: copy data from MongoDB to MySQL

Usage:
  # Ensure env vars are set (or a backend/.env file exists)
  pip install pymongo pymysql sqlalchemy python-dotenv
  python backend/scripts/migrate_mongodb_to_mysql.py

Notes:
 - The script reads MONGO_URL and DB_NAME (or DB_NAME/DB_NAME from .env), and DATABASE_URL.
 - If DATABASE_URL uses aiomysql (async), the script will replace it with pymysql for the sync engine.
 - It will create missing tables via SQLAlchemy `Base.metadata.create_all` before inserting.
 - It merges records by id (so running it multiple times is safe / idempotent).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'test_database')
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_URL_SQL')

if not DATABASE_URL:
    # Try to assemble from DB_HOST/DB_PORT/DB_USER/DB_PASSWORD
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'reporting_manager')
    if db_password:
        DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        DATABASE_URL = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"

# If DATABASE_URL contains aiomysql (async), switch to pymysql for sync engine
sync_db_url = DATABASE_URL.replace('+aiomysql', '+pymysql')


def to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Mongo may store datetimes as strings
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            # try parsing common formats
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Migrate MongoDB collections to MySQL')
    parser.add_argument('--dry-run', action='store_true', help='Do not commit changes to MySQL; show what would be done')
    parser.add_argument('--collections', type=str, help='Comma-separated list of collections to migrate (default: all)')
    args = parser.parse_args()

    dry_run = args.dry_run
    selected_collections = None
    if args.collections:
        selected_collections = {c.strip() for c in args.collections.split(',') if c.strip()}
    try:
        from pymongo import MongoClient
    except Exception as e:
        print("Missing dependency 'pymongo'. Install with: pip install pymongo", file=sys.stderr)
        return 2

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        # Import models and Base from the project
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from database import Base, User, Property, Auction, Bid, ChatMessage
    except Exception as e:
        print(f"Error importing SQLAlchemy or models: {e}", file=sys.stderr)
        return 3

    print(f"Connecting to MongoDB at {MONGO_URL}, DB: {DB_NAME}")
    mongo = MongoClient(MONGO_URL)
    mdb = mongo[DB_NAME]

    print(f"Connecting to MySQL at {sync_db_url}")
    engine = create_engine(sync_db_url, pool_pre_ping=True)

    # Ensure tables exist
    print("Ensuring SQL tables exist (create if missing)...")
    Base.metadata.create_all(engine)

    # Collections to migrate
    collections = [
        ('users', User),
        ('properties', Property),
        ('auctions', Auction),
        ('bids', Bid),
        ('chat_messages', ChatMessage),
    ]

    with Session(engine) as session:
        for coll_name, Model in collections:
            if selected_collections and coll_name not in selected_collections:
                print(f"Skipping {coll_name} (not selected)")
                continue
            print(f"Migrating collection: {coll_name}")
            coll = mdb.get_collection(coll_name)
            if coll is None:
                print(f"  - collection {coll_name} not found, skipping")
                continue

            docs = list(coll.find({}))
            print(f"  - found {len(docs)} documents")

            for doc in docs:
                # convert Mongo _id to string id
                record = doc.copy()
                if '_id' in record:
                    record_id = str(record.pop('_id'))
                else:
                    record_id = record.get('id') or record.get('uid') or None

                # Map fields generically; prefer explicit mapping per model
                kwargs: Dict[str, Any] = {}
                # Common fields mapping
                if hasattr(Model, 'id'):
                    kwargs['id'] = record_id

                # Users
                if coll_name == 'users':
                    kwargs['email'] = record.get('email')
                    kwargs['name'] = record.get('name') or record.get('full_name') or 'Unknown'
                    kwargs['location'] = record.get('location') or record.get('city') or 'Unknown'
                    kwargs['profile_verified'] = bool(record.get('profile_verified', False))
                    kwargs['created_at'] = to_datetime(record.get('created_at')) or to_datetime(record.get('created'))

                if coll_name == 'properties':
                    kwargs['title'] = record.get('title') or record.get('name')
                    kwargs['description'] = record.get('description') or ''
                    kwargs['location'] = record.get('location') or ''
                    kwargs['city'] = record.get('city') or ''
                    kwargs['state'] = record.get('state') or ''
                    kwargs['county'] = record.get('county') or None
                    kwargs['property_type'] = record.get('property_type') or record.get('type') or 'residential'
                    kwargs['size_sqft'] = record.get('size_sqft') or record.get('size')
                    kwargs['bedrooms'] = record.get('bedrooms')
                    kwargs['bathrooms'] = record.get('bathrooms')
                    kwargs['estimated_value'] = record.get('estimated_value')
                    kwargs['created_at'] = to_datetime(record.get('created_at'))

                if coll_name == 'auctions':
                    kwargs['property_id'] = str(record.get('property_id') or record.get('property'))
                    kwargs['title'] = record.get('title') or ''
                    kwargs['start_time'] = to_datetime(record.get('start_time'))
                    kwargs['end_time'] = to_datetime(record.get('end_time'))
                    kwargs['status'] = record.get('status') or 'upcoming'
                    kwargs['starting_bid'] = record.get('starting_bid') or 0.0
                    kwargs['current_bid'] = record.get('current_bid')
                    kwargs['created_at'] = to_datetime(record.get('created_at'))

                if coll_name == 'bids':
                    kwargs['auction_id'] = str(record.get('auction_id') or record.get('auction'))
                    kwargs['property_id'] = str(record.get('property_id') or record.get('property'))
                    kwargs['investor_id'] = str(record.get('investor_id') or record.get('user_id'))
                    kwargs['bid_amount'] = record.get('bid_amount') or record.get('amount') or 0.0
                    kwargs['bid_time'] = to_datetime(record.get('bid_time') or record.get('created_at') or record.get('time'))
                    kwargs['status'] = record.get('status') or 'placed'
                    kwargs['created_at'] = to_datetime(record.get('created_at'))

                if coll_name == 'chat_messages':
                    kwargs['user_id'] = str(record.get('user_id') or record.get('user'))
                    kwargs['message'] = record.get('message') or ''
                    kwargs['response'] = record.get('response') or ''
                    # store charts/tables/summary as json strings if present
                    import json as _json

                    charts = record.get('charts')
                    tables = record.get('tables')
                    summary = record.get('summary_points') or record.get('summary')
                    kwargs['charts'] = _json.dumps(charts) if charts is not None else None
                    kwargs['tables'] = _json.dumps(tables) if tables is not None else None
                    kwargs['summary_points'] = _json.dumps(summary) if summary is not None else None
                    kwargs['created_at'] = to_datetime(record.get('created_at'))

                # Remove None-only kwargs to avoid inserting nulls not allowed by schema
                # Create model instance and merge
                try:
                    instance = Model(**{k: v for k, v in kwargs.items() if v is not None})
                except Exception as e:
                    print(f"  - failed to construct {Model.__name__} for doc {record_id}: {e}")
                    continue

                try:
                    session.merge(instance)
                except Exception as e:
                    print(f"  - failed to merge record {record_id}: {e}")

            # commit per collection
            if dry_run:
                print(f"  - dry-run enabled: rolling back changes for {coll_name}")
                session.rollback()
            else:
                try:
                    session.commit()
                    print(f"  - committed {coll_name}")
                except Exception as e:
                    print(f"  - commit failed for {coll_name}: {e}")
                    session.rollback()

    print("Migration complete")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
