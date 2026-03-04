# PostgreSQL to MySQL Migration Guide

This guide will help you migrate your data from PostgreSQL to MySQL without any data loss.

---

## Prerequisites

1. **Access to both databases**
   - PostgreSQL (source database with production data)
   - MySQL RDS (target database)

2. **Install migration dependencies**
   ```bash
   cd backend
   pip install -r requirements-dev.txt
   ```

---

## Step 1: Configure Environment Variables

You need to set up connection strings for both databases. Create or update your `backend/.env` file:

```env
# Source: PostgreSQL (Production)
POSTGRES_URL=postgresql+psycopg2://username:password@host:port/database

# Or configure using components:
POSTGRES_HOST=your-postgres-host.com
POSTGRES_PORT=5432
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database_name

# Target: MySQL RDS
DATABASE_URL=mysql+pymysql://username:password@host:port/database

# Or configure using components:
DB_HOST=dev-qa-rds.czndytgw4opr.us-east-1.rds.amazonaws.com
DB_PORT=56898
DB_USER=accelerator-assetmanager
DB_PASSWORD=vMSJ49v1vZehtS05
DB_NAME=accelerator-assetmanager
```

### Example for your setup:

Based on your error message, your MySQL configuration should be:

```env
# PostgreSQL (Source) - UPDATE THESE VALUES
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_USER=your-postgres-user
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_DB=your-postgres-database

# MySQL RDS (Target) - Already working
DATABASE_URL=mysql+pymysql://accelerator-assetmanager:vMSJ49v1vZehtS05@dev-qa-rds.czndytgw4opr.us-east-1.rds.amazonaws.com:56898/accelerator-assetmanager
```

---

## Step 2: Test Connections (Dry Run)

Before migrating, test that both databases are accessible:

```bash
# Dry run - doesn't actually migrate data, just tests connections
python backend/scripts/migrate_postgres_to_mysql.py --dry-run
```

This will:
- ✅ Connect to PostgreSQL
- ✅ Connect to MySQL
- ✅ Show how many records would be migrated
- ❌ NOT actually migrate any data

---

## Step 3: Run the Migration

Once the dry run succeeds, perform the actual migration:

```bash
# Full migration
python backend/scripts/migrate_postgres_to_mysql.py
```

### Migration Options

**Migrate specific tables only:**
```bash
python backend/scripts/migrate_postgres_to_mysql.py --tables users,properties,auctions
```

**Skip certain tables:**
```bash
python backend/scripts/migrate_postgres_to_mysql.py --skip-tables chat_messages
```

**Dry run for specific tables:**
```bash
python backend/scripts/migrate_postgres_to_mysql.py --dry-run --tables users
```

---

## Step 4: Verify the Migration

After migration, verify your data in MySQL:

### Option A: Using Python Script
```python
# backend/scripts/verify_migration.py
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL').replace('+aiomysql', '+pymysql')
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    tables = ['users', 'properties', 'auctions', 'bids', 'chat_messages']
    for table in tables:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"✅ {table}: {count} records")
```

### Option B: Using MySQL Client
```bash
mysql -h dev-qa-rds.czndytgw4opr.us-east-1.rds.amazonaws.com \
      -P 56898 \
      -u accelerator-assetmanager \
      -p \
      accelerator-assetmanager

# Then in MySQL:
USE accelerator-assetmanager;
SHOW TABLES;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM properties;
SELECT COUNT(*) FROM auctions;
SELECT COUNT(*) FROM bids;
```

---

## Migrated Tables

The script will migrate the following tables:

1. **users** - User/investor information
2. **properties** - Real estate properties
3. **auctions** - Property auctions
4. **bids** - Bidding history
5. **chat_messages** - AI chat history
6. **question_categories** - Admin question categories
7. **suggested_questions** - Admin suggested questions
8. **dashboard_cards** - Admin dashboard cards

---

## Troubleshooting

### Error: "Connection refused" (PostgreSQL)

**Problem:** Can't connect to PostgreSQL database

**Solutions:**
1. Check that PostgreSQL is running
2. Verify host/port/credentials in `.env`
3. Ensure PostgreSQL allows connections from your IP
4. Check firewall settings

### Error: "Access denied" (MySQL)

**Problem:** MySQL credentials are incorrect

**Solutions:**
1. Verify MySQL credentials in `.env`
2. Check that user has write permissions
3. Test connection manually with MySQL client

### Error: "Table already exists"

**Solution:** This is normal! The script uses `merge()` which will:
- Insert new records
- Update existing records
- Skip duplicates

Running the script multiple times is safe.

### Error: Data type mismatch

**Problem:** PostgreSQL and MySQL have different data types

**Solution:** The script handles most conversions automatically. If you encounter issues, please report the specific error.

---

## Docker/CI-CD Considerations

If you're running this in Docker (based on your error traceback):

1. **Ensure the container can reach both databases:**
   ```yaml
   # docker-compose.yml or similar
   environment:
     - POSTGRES_HOST=postgres-host
     - DATABASE_URL=mysql+pymysql://...
   ```

2. **Network connectivity:**
   - PostgreSQL must be accessible from Docker container
   - Use service names in Docker Compose
   - Or use external IPs/domains

3. **Run migration as part of deployment:**
   ```bash
   # In your CI/CD pipeline or Dockerfile
   python backend/scripts/migrate_postgres_to_mysql.py
   ```

---

## After Migration

Once migration is complete:

1. ✅ Verify all data is in MySQL
2. ✅ Update application configuration to use MySQL
3. ✅ Test your application thoroughly
4. ✅ Keep PostgreSQL backup until you're confident
5. ✅ Run seed script if needed for admin data:
   ```bash
   python backend/scripts/seed_admin_data.py
   ```

---

## Support

If you encounter issues:

1. Run with `--dry-run` first to test
2. Check database connection strings
3. Verify credentials and permissions
4. Review the error messages carefully
5. Test connecting to each database separately

---

## Safety Features

The migration script is designed to be safe:

- ✅ **Idempotent**: Can run multiple times safely
- ✅ **Dry run mode**: Test before migrating
- ✅ **Per-table commits**: Failure in one table doesn't affect others
- ✅ **Merge strategy**: Updates existing records, inserts new ones
- ✅ **Error handling**: Continues even if individual records fail
- ✅ **Detailed logging**: Shows progress and any issues

---

**Good luck with your migration! 🚀**

