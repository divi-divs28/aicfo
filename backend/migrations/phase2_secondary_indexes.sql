-- =====================================================
-- Phase 2: Secondary Indexes Migration
-- Asset Manager - Performance Optimization
-- Date: December 2025
-- =====================================================

-- LOAN_ACCOUNTS Indexes
-- ---------------------

-- Index for product type GROUP BY breakdown
CREATE INDEX idx_loan_product_type ON loan_accounts(d_loan_product_type);

-- Index for product code GROUP BY breakdown
CREATE INDEX idx_loan_product_code ON loan_accounts(i_product_code);

-- Index for gender GROUP BY breakdown
CREATE INDEX idx_loan_gender ON loan_accounts(i_gender);

-- Index for sector GROUP BY breakdown
CREATE INDEX idx_loan_sector ON loan_accounts(final_sector_bifurcation);


-- DEPOSIT_ACCOUNTS Indexes
-- ------------------------

-- Index for account status GROUP BY breakdown
CREATE INDEX idx_deposit_status ON deposit_accounts(account_status);

-- Index for gender GROUP BY breakdown
CREATE INDEX idx_deposit_gender ON deposit_accounts(gender_code);
