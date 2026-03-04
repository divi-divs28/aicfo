"""
Train Vanna with database schema (DDL).
Extracts schema information and trains the semantic layer.
"""
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import VANNA_DB_NAME
from services.semantic_layer.vanna_client import get_vanna_client, initialize_vanna
from services.semantic_layer.training_data import DDL_STATEMENTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def train_schema(connect_db: bool = True) -> bool:
    """
    Train Vanna with database DDL schema.
    
    Args:
        connect_db: Whether to connect to database first
        
    Returns:
        True if training successful
    """
    logger.info("Starting schema training...")
    
    # Get Vanna client
    vn = await get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized. Check VANNA_ENABLED setting.")
        return False
    
    # Connect to database if requested
    if connect_db:
        logger.info("Connecting to database...")
        if not vn._is_db_connected:
            success = vn.connect_to_mysql_ssl()
            if not success:
                logger.error("Failed to connect to database")
                return False
    
    # Train with DDL statements
    trained_count = 0
    for i, ddl in enumerate(DDL_STATEMENTS, 1):
        try:
            # Extract table name for logging
            table_name = "unknown"
            if "CREATE TABLE" in ddl.upper():
                parts = ddl.upper().split("CREATE TABLE")
                if len(parts) > 1:
                    table_name = parts[1].strip().split()[0].strip('(').lower()
            
            logger.info(f"Training DDL {i}/{len(DDL_STATEMENTS)}: {table_name}")
            vn.train(ddl=ddl)
            trained_count += 1
            logger.info(f"  ✓ Successfully trained {table_name}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to train DDL {i}: {e}")
    
    logger.info(f"Schema training complete. Trained {trained_count}/{len(DDL_STATEMENTS)} DDL statements.")
    return trained_count == len(DDL_STATEMENTS)


async def train_schema_from_database() -> bool:
    """
    Extract DDL directly from database and train.
    Alternative method that reads live schema.
    
    Returns:
        True if training successful
    """
    logger.info("Extracting schema from live database...")
    
    vn = await get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized")
        return False
    
    # Connect to database
    if not vn._is_db_connected:
        success = vn.connect_to_mysql_ssl()
        if not success:
            logger.error("Failed to connect to database")
            return False
    
    try:
        # Get table information
        tables_query = f"""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = '{VANNA_DB_NAME}' 
            AND TABLE_NAME IN ('industries', 'company', 'accounts')
        """
        tables_df = vn.run_sql(tables_query)
        
        trained_count = 0
        for _, row in tables_df.iterrows():
            table_name = row['TABLE_NAME']
            
            # Get column information
            columns_query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{VANNA_DB_NAME}'
                AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """
            columns_df = vn.run_sql(columns_query)
            
            # Build DDL
            ddl_lines = [f"CREATE TABLE {table_name} ("]
            for idx, col in columns_df.iterrows():
                col_name = col['COLUMN_NAME']
                col_type = col['DATA_TYPE'].upper()
                nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                comment = col['COLUMN_COMMENT'] if col['COLUMN_COMMENT'] else ''
                
                line = f"    {col_name} {col_type} {nullable}"
                if comment:
                    line += f" COMMENT '{comment}'"
                
                if idx < len(columns_df) - 1:
                    line += ","
                ddl_lines.append(line)
            
            ddl_lines.append(");")
            ddl = "\n".join(ddl_lines)
            
            logger.info(f"Training extracted DDL for {table_name}")
            vn.train(ddl=ddl)
            trained_count += 1
            logger.info(f"  ✓ Successfully trained {table_name}")
        
        logger.info(f"Live schema training complete. Trained {trained_count} tables.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to extract and train schema: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Vanna with database schema")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-connect", action="store_true")
    args = parser.parse_args()

    if args.live:
        success = asyncio.run(train_schema_from_database())
    else:
        success = asyncio.run(train_schema(connect_db=not args.no_connect))

    sys.exit(0 if success else 1)
