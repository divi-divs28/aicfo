"""
Run all Vanna training scripts.
Master script to train the complete semantic layer.
"""
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_full_training(
    include_additional: bool = True,
    verify_sql: bool = False,
    validate_after: bool = True,
) -> bool:
    """
    Run complete Vanna training pipeline.
    
    Args:
        include_additional: Include additional documentation and SQL examples
        verify_sql: Verify SQL examples against database before training
        validate_after: Run validation after training
        
    Returns:
        True if training successful
    """
    from services.semantic_layer.vanna_client import get_vanna_client, initialize_vanna
    
    logger.info("="*60)
    logger.info("VANNA SEMANTIC LAYER - FULL TRAINING")
    logger.info("="*60)
    
    # Initialize Vanna
    logger.info("\n>>> Initializing Vanna client...")
    vn = get_vanna_client()
    if vn is None:
        logger.error("Failed to get Vanna client. Check VANNA_ENABLED setting.")
        return False
    
    # Connect to database
    logger.info("\n>>> Connecting to database...")
    if not vn._is_db_connected:
        success = vn.connect_to_mysql_ssl()
        if not success:
            logger.error("Failed to connect to database")
            return False
    logger.info("Database connected successfully")
    
    # Phase 1: Schema Training
    logger.info("\n" + "="*60)
    logger.info("PHASE 1: SCHEMA TRAINING")
    logger.info("="*60)
    
    from scripts.vanna.train_schema import train_schema
    if not train_schema(connect_db=False):  # Already connected
        logger.error("Schema training failed")
        return False
    
    # Phase 2: Documentation Training
    logger.info("\n" + "="*60)
    logger.info("PHASE 2: DOCUMENTATION TRAINING")
    logger.info("="*60)
    
    from scripts.vanna.train_documentation import train_documentation, train_additional_documentation
    if not train_documentation():
        logger.error("Documentation training failed")
        return False
    
    if include_additional:
        train_additional_documentation()
    
    # Phase 3: SQL Examples Training
    logger.info("\n" + "="*60)
    logger.info("PHASE 3: SQL EXAMPLES TRAINING")
    logger.info("="*60)
    
    from scripts.vanna.train_sql_examples import train_sql_examples, train_additional_sql_examples
    if not train_sql_examples(verify_sql=verify_sql):
        logger.error("SQL examples training failed")
        return False
    
    if include_additional:
        train_additional_sql_examples(verify=verify_sql)
    
    # Get training status
    logger.info("\n" + "="*60)
    logger.info("TRAINING COMPLETE")
    logger.info("="*60)
    
    status = vn.get_training_status()
    logger.info(f"Training Status:")
    logger.info(f"  - DDL entries: {status.get('ddl_count', 0)}")
    logger.info(f"  - Documentation entries: {status.get('documentation_count', 0)}")
    logger.info(f"  - SQL examples: {status.get('sql_count', 0)}")
    logger.info(f"  - Total entries: {status.get('total_entries', 0)}")
    
    # Phase 4: Validation (optional)
    if validate_after:
        logger.info("\n" + "="*60)
        logger.info("PHASE 4: VALIDATION")
        logger.info("="*60)
        
        from scripts.vanna.validate_training import validate_training
        report = validate_training(execute_sql=False, save_report=True)
        
        pass_rate = report.get('summary', {}).get('pass_rate', 0)
        if pass_rate < 0.7:
            logger.warning(f"Validation pass rate ({pass_rate:.0%}) below threshold (70%)")
        else:
            logger.info(f"Validation passed with {pass_rate:.0%} success rate")
    
    logger.info("\n" + "="*60)
    logger.info("FULL TRAINING PIPELINE COMPLETE")
    logger.info("="*60)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run full Vanna training pipeline")
    parser.add_argument("--no-additional", action="store_true", help="Skip additional training data")
    parser.add_argument("--verify-sql", action="store_true", help="Verify SQL against database")
    parser.add_argument("--no-validate", action="store_true", help="Skip validation after training")
    args = parser.parse_args()
    
    success = run_full_training(
        include_additional=not args.no_additional,
        verify_sql=args.verify_sql,
        validate_after=not args.no_validate,
    )
    
    sys.exit(0 if success else 1)
