-- =====================================================
-- Phase 1: Critical Indexes Migration
-- Asset Manager - Performance Optimization
-- Date: December 2025
-- =====================================================

-- LOAN_ACCOUNTS Indexes
-- ---------------------

-- Index for JOIN with deposits, GROUP BY customer, DISTINCT customer
CREATE INDEX idx_loan_customer ON loan_accounts(i_customer_id);

-- Index for NPA filtering (WHERE d_asset_class IN ('DB1','DB2','DB3')) and GROUP BY
CREATE INDEX idx_loan_asset_class ON loan_accounts(d_asset_class);

-- Index for DPD range queries (0, 1-30, 31-60, 61-90, 90+)
CREATE INDEX idx_loan_dpd ON loan_accounts(d_overdue_dpd);

-- Index for PSL filtering and GROUP BY
CREATE INDEX idx_loan_psl ON loan_accounts(psl_non_psl);


-- DEPOSIT_ACCOUNTS Indexes
-- ------------------------

-- Index for JOIN with loans, GROUP BY customer, DISTINCT customer
CREATE INDEX idx_deposit_customer ON deposit_accounts(customer_number);

-- Index for CASA filtering (WHERE account_product_group IN ('SBA','CAA')) and GROUP BY
CREATE INDEX idx_deposit_product_group ON deposit_accounts(account_product_group);

-- Index for maturity bucket range queries
CREATE INDEX idx_deposit_maturity ON deposit_accounts(days_to_maturity);

-- Index for branch analysis GROUP BY
CREATE INDEX idx_deposit_branch ON deposit_accounts(branch_code);
