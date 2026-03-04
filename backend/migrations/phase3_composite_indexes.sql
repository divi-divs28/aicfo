-- =====================================================
-- Phase 3: Composite Indexes Migration
-- Asset Manager - Advanced Performance Optimization
-- Date: December 2025
-- =====================================================

-- LOAN_ACCOUNTS Composite Indexes
-- -------------------------------

-- Composite index for NPA filtering + SUM(outstanding)
-- Optimizes: WHERE d_asset_class IN ('DB1','DB2','DB3') + SUM(i_outstanding_principal)
CREATE INDEX idx_loan_asset_outstanding ON loan_accounts(d_asset_class, i_outstanding_principal);

-- Composite index for top loan exposures query
-- Optimizes: GROUP BY i_customer_id + ORDER BY SUM(outstanding) DESC
CREATE INDEX idx_loan_customer_outstanding ON loan_accounts(i_customer_id, i_outstanding_principal);

-- Composite index for DPD bucket analysis
-- Optimizes: WHERE d_overdue_dpd BETWEEN x AND y + SUM(outstanding)
CREATE INDEX idx_loan_dpd_outstanding ON loan_accounts(d_overdue_dpd, i_outstanding_principal);

-- Composite index for PSL ratio calculation
-- Optimizes: WHERE psl_non_psl = 'PSL' + SUM(outstanding)
CREATE INDEX idx_loan_psl_outstanding ON loan_accounts(psl_non_psl, i_outstanding_principal);


-- DEPOSIT_ACCOUNTS Composite Indexes
-- ----------------------------------

-- Composite index for CASA calculation
-- Optimizes: WHERE account_product_group IN ('SBA','CAA') + SUM(ledger_balance)
CREATE INDEX idx_deposit_product_balance ON deposit_accounts(account_product_group, ledger_balance);

-- Composite index for top depositors query
-- Optimizes: GROUP BY customer_number + ORDER BY SUM(balance) DESC
CREATE INDEX idx_deposit_customer_balance ON deposit_accounts(customer_number, ledger_balance);

-- Composite index for branch analysis
-- Optimizes: GROUP BY branch_code, branch_name + SUM(balance)
CREATE INDEX idx_deposit_branch_balance ON deposit_accounts(branch_code, branch_name, ledger_balance);

-- Composite index for maturity bucket analysis
-- Optimizes: WHERE days_to_maturity BETWEEN x AND y + SUM(balance)
CREATE INDEX idx_deposit_maturity_balance ON deposit_accounts(days_to_maturity, ledger_balance);
