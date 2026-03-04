"""
Financial domain SQLAlchemy models.
Loan and Deposit account tables.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Date
from decimal import Decimal

from database import Base


class LoanAccount(Base):
    """
    Loan Portfolio Master Table - Account-level snapshot of all credit/advance accounts.
    Business Purpose: Loan origination, asset quality monitoring, provisioning, PSL reporting.
    Grain: One row per loan account per snapshot date.
    """
    __tablename__ = 'loan_accounts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    i_source_system_name = Column(String(50))  # Source system: BR.NET, FINACLE, VegaPay
    d_state_name = Column(String(50))  # State where loan is booked
    i_branch_code = Column(Integer)  # Branch identifier
    i_branch_name = Column(String(50))  # Branch name
    i_loan_sourced_by_branch_code = Column(Integer)  # Loan sourced by branch code
    i_gl_code = Column(Integer)  # GL code
    i_gl_name = Column(String(50))  # GL name
    i_product_code = Column(String(50))  # Product code
    d_product_name = Column(String(100))  # Product description
    d_product_group = Column(String(50))  # SECURED / UNSECURED
    d_loan_product_type = Column(String(50))  # JLG, IL, OD, etc.
    d_tl_cc_od_tagging = Column(String(50))  # TL/CC/OD tagging
    d_managed_owned = Column(String(50))  # Managed/Owned
    i_securitization_code = Column(Integer)  # Securitization code
    i_customer_id = Column(Integer)  # Customer unique identifier
    i_customer_name = Column(String(50))  # Customer name
    i_accountid_for_acid = Column(String(50))  # Loan account ID (natural key)
    i_loan_series = Column(Integer)  # Loan series
    i_sanctioned_limit = Column(Integer)  # Sanctioned loan amount
    i_sanction_date = Column(Date)  # Date of sanction
    i_first_disbursed_date = Column(Date)  # First disbursement date
    i_disbursed_amount = Column(Integer)  # Amount disbursed
    i_current_limit = Column(Integer)  # Current limit
    i_loan_maturity_date = Column(Date)  # Loan maturity date
    d_tagging = Column(String(50))  # FIXED / FLOATING
    i_rate_of_interest = Column(Float)  # Interest rate
    d_sub_sector_description = Column(String(50))  # Sub-sector description
    i_purpose_code = Column(Integer)  # Purpose code
    i_purpose_category_code = Column(Integer)  # Purpose category code
    i_sector = Column(String(50))  # Sector
    i_sub_sector = Column(String(50))  # Sub-sector
    i_occu_code = Column(Integer)  # Occupation code
    i_gender = Column(String(50))  # Borrower gender (M/F)
    i_t_loan_purpose_description = Column(String(50))  # Loan purpose description
    i_t_loan_purpose_category_description = Column(String(50))  # Loan purpose category description
    i_sector_desc = Column(String(50))  # Sector description
    i_sub_sector_desc = Column(String(50))  # Sub-sector description
    i_acct_locn_code = Column(Integer)  # Account location code
    d_loan_purpose_name = Column(String(100))  # Loan purpose name
    d_constitution_name = Column(String(50))  # Customer constitution
    d_caste_name = Column(String(50))  # Customer caste classification
    d_religion_name = Column(String(50))  # Customer religion
    d_occupation_name = Column(String(50))  # Customer occupation
    d_bank_non_bank_tagging = Column(String(50))  # Bank/Non-bank tagging
    psl_non_psl = Column(String(50))  # PSL / Non PSL classification
    d_psl_tagging = Column(String(100))  # PSL sub-category
    d_bkspi_tagging = Column(String(50))  # BKSPI tagging
    d_more_than_less_than_25lacs = Column(String(50))  # More/less than 25 lacs
    i_emi_amount = Column(Integer)  # EMI amount
    i_outstanding_principal = Column(Float)  # Current outstanding principal
    i_advance_emi_amount = Column(Float)  # Advance EMI amount
    i_int_accrued_due = Column(Float)  # Interest accrued due
    d_final_pos_balance = Column(Float)  # Final position balance
    i_securedunsecured = Column(String(50))  # Secured/Unsecured flag
    i_security_value = Column(Integer)  # Security/collateral value
    d_used_security = Column(Float)  # Used security
    d_secured_amt = Column(Float)  # Secured portion
    d_un_secured_amt = Column(Float)  # Unsecured portion
    d_net_balance_for_provision = Column(Float)  # Net balance for provision
    d_asset_class = Column(String(50))  # Asset classification (STD, SMA, DB1, DB2, DB3)
    d_npa_date = Column(Date)  # NPA date
    d_npa_reason = Column(String(50))  # NPA reason
    i_overdue_since_dt = Column(Date)  # Overdue since date
    i_overdue_amt = Column(Float)  # Overdue amount
    i_overdue_principal = Column(Float)  # Overdue principal
    i_overdue_interest = Column(Float)  # Overdue interest
    i_review_due_dt = Column(Date)  # Review due date
    id_lastcr_dt = Column(Date)  # Last credit date
    d_overdue_dpd = Column(Integer)  # Days past due (overdue DPD)
    d_reviewdue_dpd = Column(Integer)  # Review due DPD
    d_over_drawn_since_dpd = Column(Integer)  # Over drawn since DPD
    d_stockst_dpd = Column(Integer)  # Stock statement DPD
    id_last_cr_date_dpd = Column(Integer)  # Last credit date DPD
    d_accountmax_financial_dpd = Column(Integer)  # Account max financial DPD
    d_accountmax_non_financial_dpd = Column(Integer)  # Account max non-financial DPD
    d_customermax_financial_dpd = Column(Integer)  # Customer max financial DPD
    d_customermax_non_financial_dpd = Column(Integer)  # Customer max non-financial DPD
    d_restructure_tagging = Column(String(50))  # Restructure tagging
    i_eclgs_tagging = Column(String(50))  # ECLGS tagging
    d_npa_prov_percent = Column(Float)  # NPA provision percent
    d_npa_prov_amt = Column(Float)  # NPA provision amount
    i_restructure_prov_percent = Column(Integer)  # Restructure provision percent
    d_restructure_prov_amt = Column(Integer)  # Restructure provision amount
    d_total_provision = Column(Float)  # Total provision amount
    d_final_provision_per = Column(Float)  # Final provision percent
    d_prov_per_secured = Column(Float)  # Provision percent secured
    d_prov_secured = Column(Float)  # Provision secured
    d_prov_per_unsecured = Column(Float)  # Provision percent unsecured
    d_prov_unsecured = Column(Float)  # Provision unsecured
    d_sma_tagging = Column(String(50))  # SMA classification
    d_sma_dt = Column(Date)  # SMA date
    d_provision_std_percent = Column(Float)  # Standard provision percent
    d_provision_std_amt = Column(Float)  # Standard provision amount
    d_90_days_credit = Column(Integer)  # 90 days credit amount
    d_90days_interest = Column(Integer)  # 90 days interest
    date_of_data = Column(Date)  # Data extraction date
    incremental_prov_amt = Column(Float)  # Incremental provision amount
    d_bsr1code = Column(Integer)  # BSR1 code
    i_original_outstanding_principal = Column(Float)  # Original outstanding principal
    fk_id = Column(Integer)  # Foreign key ID
    as_on_dt = Column(Date)  # Snapshot date
    final_sector_bifurcation = Column(String(50))  # Sector: Micro Finance, Agriculture, Others
    product_sub_category = Column(String(50))  # Product sub-category
    d_psl_tagging_final = Column(String(100))  # Final PSL tagging
    ps_non_psl_final = Column(String(50))  # Final PSL/Non-PSL
    i_loan_type = Column(String(50))  # Loan type
    i_sourceassetclass = Column(String(50))  # Source asset class


class DepositAccount(Base):
    """
    Deposit Portfolio Master Table - Account-level snapshot of all deposit/liability accounts.
    Business Purpose: Deposit mobilization, interest expense, liquidity management, maturity analysis.
    Grain: One row per deposit account per snapshot date.
    """
    __tablename__ = 'deposit_accounts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(Integer)  # Deposit account number (natural key)
    product_type = Column(Integer)  # Product type code
    gl_set_code = Column(Integer)  # GL set code
    account_open_date = Column(Date)  # Account opening date
    original_amount = Column(Integer)  # Original deposit amount
    customer_number = Column(Integer)  # Customer unique identifier
    gender_code = Column(String(50))  # Depositor gender (M/F)
    branch_code = Column(Integer)  # Branch identifier
    branch_name = Column(String(50))  # Branch name
    account_status = Column(String(50))  # A=Active, D=Dormant, I=Inactive
    cost_center = Column(Integer)  # Cost center
    customer_constitution = Column(Integer)  # Customer constitution code
    customer_const_desc = Column(String(50))  # Customer constitution description
    currency_code = Column(String(50))  # Currency code
    account_product_group = Column(String(50))  # SBA, TDA, CAA, ODA, TUA
    account_title = Column(String(50))  # Account holder name
    ledger_balance = Column(Float)  # Current ledger balance
    maturity_date = Column(Date)  # Maturity date for term deposits
    days_to_maturity = Column(Integer)  # Days remaining to maturity
    deposit_term = Column(Integer)  # Term in days
    cumulative_accrued_interest = Column(Float)  # Total accrued interest
    gl_number = Column(Integer)  # GL number
    gl_description = Column(String(50))  # GL account description
    cdr_account_open_date = Column(Date)  # CDR account open date
    closing_ledger_balance = Column(Integer)  # Closing balance
    account_close_date = Column(Date)  # Account close date
    overdraft_limit = Column(Integer)  # Overdraft limit
    interest_paid_ytd = Column(Float)  # Interest paid year-to-date
    interest_paid_last_date = Column(Date)  # Last interest paid date
    positive_accrued_interest = Column(Float)  # Positive accrued interest
    interest_paid_account_id = Column(Integer)  # Interest paid account ID
    interest_paid_account_name = Column(String(50))  # Interest paid account name
    residual_maturity_days = Column(Integer)  # Residual maturity
    customer_date_of_birth = Column(Date)  # Customer DOB
    interest_calculation_method = Column(String(50))  # Interest calculation method
    base_amount_indicator = Column(String(50))  # Base amount indicator
    compounding_period = Column(Integer)  # Compounding period
    compounding_base = Column(Integer)  # Compounding base
    broken_period_interest_method = Column(String(50))  # Broken period interest method
    flow_code = Column(String(50))  # Flow code
    flow_frequency_months = Column(Integer)  # Flow frequency in months
    joint_holder_1 = Column(Integer)  # Joint holder 1
    joint_holder_2 = Column(Integer)  # Joint holder 2
    fk_id = Column(Integer)  # Foreign key ID
    as_on_date = Column(Date)  # Snapshot date
    channel_id = Column(String(50))  # Origination channel
    nominal_interest_rate = Column(Float)  # Interest rate
