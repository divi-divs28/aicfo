"""
Reset Vanna training data.
Clears all training and optionally rebuilds from scratch.
"""
import sys
import logging
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import VANNA_FAISS_PATH

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_training(confirm: bool = False) -> bool:
    """
    Reset all Vanna training data by clearing FAISS index.
    
    Args:
        confirm: Must be True to actually reset
        
    Returns:
        True if reset successful
    """
    if not confirm:
        logger.warning("Reset not confirmed. Pass confirm=True to reset training data.")
        logger.warning("This will delete all trained DDL, documentation, and SQL examples.")
        return False
    
    logger.info("Resetting Vanna training data...")
    
    faiss_path = Path(VANNA_FAISS_PATH)
    
    if not faiss_path.exists():
        logger.info("FAISS directory does not exist. Nothing to reset.")
        return True
    
    try:
        # Remove all files in FAISS directory
        for item in faiss_path.iterdir():
            if item.is_file():
                item.unlink()
                logger.info(f"  Deleted: {item.name}")
            elif item.is_dir():
                shutil.rmtree(item)
                logger.info(f"  Deleted directory: {item.name}")
        
        logger.info("Training data reset complete.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset training data: {e}")
        return False


def rebuild_training() -> bool:
    """
    Reset and rebuild all training data.
    
    Returns:
        True if rebuild successful
    """
    logger.info("Starting full training rebuild...")
    
    # Reset existing training
    if not reset_training(confirm=True):
        logger.error("Failed to reset training")
        return False
    
    # Import training functions
    from scripts.vanna.train_schema import train_schema
    from scripts.vanna.train_documentation import train_documentation, train_additional_documentation
    from scripts.vanna.train_sql_examples import train_sql_examples, train_additional_sql_examples
    
    # Train schema
    logger.info("\n=== Phase 1: Training Schema ===")
    if not train_schema(connect_db=True):
        logger.error("Schema training failed")
        return False
    
    # Train documentation
    logger.info("\n=== Phase 2: Training Documentation ===")
    if not train_documentation():
        logger.error("Documentation training failed")
        return False
    
    if not train_additional_documentation():
        logger.warning("Additional documentation training failed (non-critical)")
    
    # Train SQL examples
    logger.info("\n=== Phase 3: Training SQL Examples ===")
    if not train_sql_examples(verify_sql=False):
        logger.error("SQL examples training failed")
        return False
    
    if not train_additional_sql_examples(verify=False):
        logger.warning("Additional SQL examples training failed (non-critical)")
    
    logger.info("\n=== Training Rebuild Complete ===")
    
    # Get final status
    from services.semantic_layer.vanna_client import get_vanna_client
    vn = get_vanna_client()
    if vn:
        status = vn.get_training_status()
        logger.info(f"Final training status: {status}")
    
    return True


def get_training_info() -> dict:
    """
    Get information about current training data.
    
    Returns:
        Dictionary with training info
    """
    from services.semantic_layer.vanna_client import get_vanna_client
    
    vn = get_vanna_client()
    if vn is None:
        return {"error": "Vanna not initialized"}
    
    return vn.get_training_status()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset Vanna training data")
    parser.add_argument("--confirm", action="store_true", help="Confirm reset (required)")
    parser.add_argument("--rebuild", action="store_true", help="Reset and rebuild all training")
    parser.add_argument("--info", action="store_true", help="Show current training info")
    args = parser.parse_args()
    
    if args.info:
        import json
        info = get_training_info()
        print(json.dumps(info, indent=2))
    elif args.rebuild:
        success = rebuild_training()
        sys.exit(0 if success else 1)
    else:
        success = reset_training(confirm=args.confirm)
        sys.exit(0 if success else 1)
