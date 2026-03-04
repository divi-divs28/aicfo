"""
Train Vanna with asset management documentation.
Provides context about KPIs, terminology, and business rules.
"""
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.semantic_layer.vanna_client import get_vanna_client
from services.semantic_layer.training_data import ASSET_DOCUMENTATION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def train_documentation() -> bool:
    """
    Train Vanna with real estate domain documentation.
    Static documentation is empty; use Business Context upload for documentation.
    
    Returns:
        True if training successful (or nothing to train)
    """
    logger.info("Starting documentation training...")
    
    if not ASSET_DOCUMENTATION:
        logger.info("No static documentation to train. Use Business Context upload for documentation.")
        return True
    
    # Get Vanna client
    vn = get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized. Check VANNA_ENABLED setting.")
        return False
    
    # Train with documentation
    trained_count = 0
    for i, doc in enumerate(ASSET_DOCUMENTATION, 1):
        try:
            # Extract title for logging (first line or first 50 chars)
            title = doc.strip().split('\n')[0][:50].strip()
            
            logger.info(f"Training documentation {i}/{len(ASSET_DOCUMENTATION)}: {title}...")
            vn.train(documentation=doc)
            trained_count += 1
            logger.info(f"  ✓ Successfully trained")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to train documentation {i}: {e}")
    
    logger.info(f"Documentation training complete. Trained {trained_count}/{len(ASSET_DOCUMENTATION)} entries.")
    return trained_count == len(ASSET_DOCUMENTATION)


def train_custom_documentation(docs: list) -> bool:
    """
    Train Vanna with custom documentation.
    
    Args:
        docs: List of documentation strings
        
    Returns:
        True if training successful
    """
    logger.info(f"Training {len(docs)} custom documentation entries...")
    
    vn = get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized")
        return False
    
    trained_count = 0
    for i, doc in enumerate(docs, 1):
        try:
            vn.train(documentation=doc)
            trained_count += 1
        except Exception as e:
            logger.error(f"Failed to train custom doc {i}: {e}")
    
    logger.info(f"Custom documentation training complete. Trained {trained_count}/{len(docs)} entries.")
    return trained_count == len(docs)


# Additional domain-specific documentation
ADDITIONAL_DOCUMENTATION = [
    """
    CONCENTRATION RISK:
    - Top 10 borrowers should not exceed 20% of total advances
    - Single borrower exposure limit as per RBI norms
    - Use GROUP BY customer to calculate exposure
    - Query: SELECT customer, SUM(outstanding) as exposure, exposure/total*100 as percent
    """,
    
    """
    LIQUIDITY ANALYSIS:
    - Deposits maturing in 0-30 days: High liquidity risk
    - Use days_to_maturity field for maturity buckets
    - CASA deposits have no fixed maturity (days_to_maturity is NULL)
    - Term deposits (TDA) have defined maturity
    """,
    
    """
    CROSS-SELL ANALYSIS:
    - Join loan_accounts and deposit_accounts on customer ID
    - loan_accounts.i_customer_id = deposit_accounts.customer_number
    - Net position = deposits - loans (positive = net depositor)
    - Opportunity: Loan-only customers for deposit mobilization
    """,
    
    """
    BRANCH PERFORMANCE METRICS:
    - Loan mobilization: SUM(i_outstanding_principal) by branch
    - Deposit mobilization: SUM(ledger_balance) by branch
    - Branch NPA ratio: NPA amount / Total advances per branch
    - Use i_branch_code/branch_code for grouping
    """,
    
    """
    DEMOGRAPHIC ANALYSIS:
    - Gender: i_gender (loans), gender_code (deposits) - M/F values
    - Religion: d_religion_name field in loan_accounts
    - Caste: d_caste_name field in loan_accounts
    - Occupation: d_occupation_name field in loan_accounts
    - Use for segment analysis and regulatory reporting
    """,
    
    """
    OVERDUE ANALYSIS:
    - i_overdue_amt: Total overdue amount
    - i_overdue_principal: Principal portion of overdue
    - i_overdue_interest: Interest portion of overdue
    - d_overdue_dpd: Days past due count
    - Account becomes NPA when DPD > 90
    """,
    
    """
    SECURED vs UNSECURED LOANS:
    - i_securedunsecured: Flag for secured/unsecured
    - i_security_value: Collateral value
    - d_secured_amt: Secured portion of loan
    - d_un_secured_amt: Unsecured portion
    - Higher provision required for unsecured NPAs
    """,
    
    """
    INTEREST RATE ANALYSIS:
    - i_rate_of_interest: Loan interest rate (percentage)
    - nominal_interest_rate: Deposit interest rate
    - d_tagging: FIXED or FLOATING rate indicator
    - Spread = Lending rate - Cost of deposits
    """,
]


def train_additional_documentation() -> bool:
    """
    Train Vanna with additional domain documentation.
    
    Returns:
        True if training successful
    """
    logger.info("Training additional domain documentation...")
    return train_custom_documentation(ADDITIONAL_DOCUMENTATION)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Vanna with real estate documentation")
    parser.add_argument("--additional", action="store_true", help="Include additional documentation")
    args = parser.parse_args()
    
    success = train_documentation()
    
    if args.additional and success:
        success = train_additional_documentation()
    
    sys.exit(0 if success else 1)
