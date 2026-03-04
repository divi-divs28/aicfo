"""
Train Vanna with verified SQL examples.
Question-SQL pairs help Vanna learn query patterns.
"""
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.semantic_layer.vanna_client import get_vanna_client
from services.semantic_layer.training_data import SQL_TRAINING_EXAMPLES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def train_sql_examples(verify_sql: bool = False) -> bool:
    """
    Train Vanna with SQL examples.
    Static examples are empty; use SQL Training upload for question-SQL pairs.
    
    Args:
        verify_sql: Whether to verify SQL executes successfully before training
        
    Returns:
        True if training successful (or nothing to train)
    """
    logger.info("Starting SQL examples training...")
    
    if not SQL_TRAINING_EXAMPLES:
        logger.info("No static SQL examples to train. Use SQL Training upload for question-SQL pairs.")
        return True
    
    # Get Vanna client
    vn = get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized. Check VANNA_ENABLED setting.")
        return False
    
    # Connect to database if verification requested
    if verify_sql and not vn._is_db_connected:
        logger.info("Connecting to database for SQL verification...")
        success = vn.connect_to_mysql_ssl()
        if not success:
            logger.warning("Database connection failed. Proceeding without verification.")
            verify_sql = False
    
    # Train with SQL examples
    trained_count = 0
    skipped_count = 0
    
    for i, example in enumerate(SQL_TRAINING_EXAMPLES, 1):
        question = example.get('question', '')
        sql = example.get('sql', '')
        
        if not question or not sql:
            logger.warning(f"Skipping example {i}: missing question or SQL")
            skipped_count += 1
            continue
        
        try:
            # Verify SQL if requested
            if verify_sql:
                try:
                    # Add LIMIT 1 for verification to avoid large result sets
                    verify_sql_stmt = sql.strip().rstrip(';')
                    if 'LIMIT' not in verify_sql_stmt.upper():
                        verify_sql_stmt += ' LIMIT 1'
                    vn.run_sql(verify_sql_stmt)
                    logger.debug(f"  SQL verified: {question[:40]}...")
                except Exception as e:
                    logger.warning(f"  SQL verification failed for '{question[:40]}...': {e}")
                    skipped_count += 1
                    continue
            
            # Train the example
            logger.info(f"Training SQL {i}/{len(SQL_TRAINING_EXAMPLES)}: {question[:50]}...")
            vn.train(question=question, sql=sql)
            trained_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Failed to train SQL example {i}: {e}")
            skipped_count += 1
    
    logger.info(f"SQL training complete. Trained: {trained_count}, Skipped: {skipped_count}")
    return trained_count > 0


def train_custom_sql_examples(examples: list, verify: bool = False) -> bool:
    """
    Train Vanna with custom SQL examples.
    
    Args:
        examples: List of dicts with 'question' and 'sql' keys
        verify: Whether to verify SQL before training
        
    Returns:
        True if training successful
    """
    logger.info(f"Training {len(examples)} custom SQL examples...")
    
    vn = get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized")
        return False
    
    trained_count = 0
    for i, example in enumerate(examples, 1):
        try:
            question = example.get('question', '')
            sql = example.get('sql', '')
            
            if not question or not sql:
                continue
            
            if verify and vn._is_db_connected:
                try:
                    verify_sql = sql.strip().rstrip(';')
                    if 'LIMIT' not in verify_sql.upper():
                        verify_sql += ' LIMIT 1'
                    vn.run_sql(verify_sql)
                except Exception:
                    logger.warning(f"Skipping unverified SQL: {question[:40]}...")
                    continue
            
            vn.train(question=question, sql=sql)
            trained_count += 1
            
        except Exception as e:
            logger.error(f"Failed to train custom SQL {i}: {e}")
    
    logger.info(f"Custom SQL training complete. Trained {trained_count}/{len(examples)} examples.")
    return trained_count > 0


# Additional SQL examples for edge cases
ADDITIONAL_SQL_EXAMPLES = [
    {
        "question": "Show loans with outstanding between 1 lakh and 5 lakh",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, d_loan_product_type, d_asset_class
                  FROM loan_accounts
                  WHERE i_outstanding_principal BETWEEN 100000 AND 500000
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Find female borrowers with NPA loans",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, d_asset_class, d_overdue_dpd
                  FROM loan_accounts
                  WHERE i_gender = 'F'
                    AND d_asset_class IN ('DB1', 'DB2', 'DB3')
                  ORDER BY i_outstanding_principal DESC"""
    },
    {
        "question": "Show agriculture sector loans",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, final_sector_bifurcation,
                         psl_non_psl, d_psl_tagging
                  FROM loan_accounts
                  WHERE final_sector_bifurcation = 'Agriculture'
                     OR d_psl_tagging LIKE '%Agriculture%'
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Show microfinance loans (JLG product type)",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, d_loan_product_type, d_asset_class
                  FROM loan_accounts
                  WHERE d_loan_product_type = 'JLG'
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Show secured vs unsecured loan breakdown",
        "sql": """SELECT i_securedunsecured as loan_type,
                         COUNT(*) as account_count,
                         SUM(i_outstanding_principal) as total_outstanding,
                         SUM(d_total_provision) as total_provision
                  FROM loan_accounts
                  GROUP BY i_securedunsecured"""
    },
    {
        "question": "Show average loan size by product type",
        "sql": """SELECT d_loan_product_type,
                         COUNT(*) as account_count,
                         AVG(i_outstanding_principal) as avg_outstanding,
                         AVG(i_sanctioned_limit) as avg_sanctioned
                  FROM loan_accounts
                  GROUP BY d_loan_product_type
                  ORDER BY avg_outstanding DESC"""
    },
    {
        "question": "List high value term deposits above 10 lakh",
        "sql": """SELECT account_number, customer_number, account_title,
                         ledger_balance, nominal_interest_rate,
                         days_to_maturity, branch_name
                  FROM deposit_accounts
                  WHERE account_product_group = 'TDA'
                    AND ledger_balance > 1000000
                  ORDER BY ledger_balance DESC
                  LIMIT 50"""
    },
    {
        "question": "Show customers with multiple loan accounts",
        "sql": """SELECT i_customer_id, i_customer_name,
                         COUNT(*) as loan_count,
                         SUM(i_outstanding_principal) as total_outstanding
                  FROM loan_accounts
                  GROUP BY i_customer_id, i_customer_name
                  HAVING COUNT(*) > 1
                  ORDER BY loan_count DESC
                  LIMIT 50"""
    },
    {
        "question": "Show restructured loans",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, d_restructure_tagging,
                         d_asset_class, d_overdue_dpd
                  FROM loan_accounts
                  WHERE d_restructure_tagging IS NOT NULL
                    AND d_restructure_tagging != ''
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Show SMA (Special Mention Account) loans",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, d_sma_tagging,
                         d_overdue_dpd, d_asset_class
                  FROM loan_accounts
                  WHERE d_sma_tagging IS NOT NULL
                    AND d_sma_tagging != ''
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Compare loan and deposit by branch",
        "sql": """SELECT 
                    COALESCE(l.i_branch_name, d.branch_name) as branch_name,
                    COALESCE(l.total_loans, 0) as total_loans,
                    COALESCE(d.total_deposits, 0) as total_deposits,
                    COALESCE(d.total_deposits, 0) - COALESCE(l.total_loans, 0) as net_position
                  FROM (
                    SELECT i_branch_name, SUM(i_outstanding_principal) as total_loans
                    FROM loan_accounts
                    GROUP BY i_branch_name
                  ) l
                  FULL OUTER JOIN (
                    SELECT branch_name, SUM(ledger_balance) as total_deposits
                    FROM deposit_accounts
                    GROUP BY branch_name
                  ) d ON l.i_branch_name = d.branch_name
                  ORDER BY total_deposits DESC
                  LIMIT 20"""
    },
    {
        "question": "Show loans by religion breakdown",
        "sql": """SELECT d_religion_name as religion,
                         COUNT(*) as account_count,
                         SUM(i_outstanding_principal) as total_outstanding
                  FROM loan_accounts
                  WHERE d_religion_name IS NOT NULL
                  GROUP BY d_religion_name
                  ORDER BY total_outstanding DESC"""
    },
    {
        "question": "Show loans by caste breakdown",
        "sql": """SELECT d_caste_name as caste,
                         COUNT(*) as account_count,
                         SUM(i_outstanding_principal) as total_outstanding
                  FROM loan_accounts
                  WHERE d_caste_name IS NOT NULL
                  GROUP BY d_caste_name
                  ORDER BY total_outstanding DESC"""
    },
    {
        "question": "Show ECLGS (Emergency Credit Line) loans",
        "sql": """SELECT i_customer_id, i_customer_name, i_accountid_for_acid,
                         i_outstanding_principal, i_eclgs_tagging,
                         d_guaranteed_portion, d_asset_class
                  FROM loan_accounts
                  WHERE i_eclgs_tagging IS NOT NULL
                    AND i_eclgs_tagging != ''
                  ORDER BY i_outstanding_principal DESC
                  LIMIT 100"""
    },
    {
        "question": "Show total interest accrued on deposits",
        "sql": """SELECT account_product_group,
                         COUNT(*) as account_count,
                         SUM(ledger_balance) as total_balance,
                         SUM(cumulative_accrued_interest) as total_accrued_interest,
                         AVG(nominal_interest_rate) as avg_interest_rate
                  FROM deposit_accounts
                  GROUP BY account_product_group
                  ORDER BY total_balance DESC"""
    },
]


def train_additional_sql_examples(verify: bool = False) -> bool:
    """
    Train Vanna with additional SQL examples.
    
    Args:
        verify: Whether to verify SQL before training
        
    Returns:
        True if training successful
    """
    logger.info("Training additional SQL examples...")
    return train_custom_sql_examples(ADDITIONAL_SQL_EXAMPLES, verify=verify)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Vanna with SQL examples")
    parser.add_argument("--verify", action="store_true", help="Verify SQL before training")
    parser.add_argument("--additional", action="store_true", help="Include additional examples")
    args = parser.parse_args()
    
    success = train_sql_examples(verify_sql=args.verify)
    
    if args.additional and success:
        success = train_additional_sql_examples(verify=args.verify)
    
    sys.exit(0 if success else 1)
