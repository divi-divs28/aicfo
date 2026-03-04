"""
Dashboard Analytics routes.
API endpoints for dashboard tabs with real data from loan_accounts and deposit_accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text
from typing import Optional
import logging

from database import get_db
from models.financial import LoanAccount, DepositAccount

router = APIRouter(prefix="/dashboard")


# =============================================================================
# TAB 1: PORTFOLIO OVERVIEW
# =============================================================================

@router.get("/portfolio-overview")
async def get_portfolio_overview(
    as_on_date: Optional[str] = None,
    branch: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Portfolio Overview tab data - executive summary of total book size, composition, and health."""
    try:
        # Base filters
        loan_filters = []
        deposit_filters = []
        if branch:
            loan_filters.append(LoanAccount.i_branch_code == int(branch))
            deposit_filters.append(DepositAccount.branch_code == int(branch))

        # Chart 1: Loan Portfolio by Product Type (Donut)
        product_type_query = select(
            LoanAccount.d_loan_product_type,
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.d_loan_product_type)
        
        if loan_filters:
            for f in loan_filters:
                product_type_query = product_type_query.where(f)
        
        product_type_result = await db.execute(product_type_query)
        loan_by_product = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in product_type_result.fetchall()
        ]

        # Chart 2: Secured vs Unsecured Split (Donut)
        secured_query = select(
            func.sum(LoanAccount.d_secured_amt).label('secured'),
            func.sum(LoanAccount.d_un_secured_amt).label('unsecured')
        )
        if loan_filters:
            for f in loan_filters:
                secured_query = secured_query.where(f)
        
        secured_result = await db.execute(secured_query)
        secured_row = secured_result.fetchone()
        secured_unsecured = [
            {"name": "Secured", "value": round(float(secured_row[0] or 0), 2)},
            {"name": "Unsecured", "value": round(float(secured_row[1] or 0), 2)}
        ]

        # Chart 3: Loan vs Deposit Comparison (Horizontal Bar)
        total_loans = await db.scalar(select(func.sum(LoanAccount.i_outstanding_principal)))
        total_deposits = await db.scalar(select(func.sum(DepositAccount.ledger_balance)))
        loan_vs_deposit = [
            {"name": "Total Loans", "value": round(float(total_loans or 0), 2)},
            {"name": "Total Deposits", "value": round(float(total_deposits or 0), 2)}
        ]

        # Chart 4: Sector-wise Loan Distribution (Bar)
        sector_query = select(
            LoanAccount.final_sector_bifurcation,
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.final_sector_bifurcation)
        
        if loan_filters:
            for f in loan_filters:
                sector_query = sector_query.where(f)
        
        sector_result = await db.execute(sector_query)
        loan_by_sector = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in sector_result.fetchall()
        ]

        # Summary KPIs
        loan_count = await db.scalar(select(func.count()).select_from(LoanAccount)) or 0
        deposit_count = await db.scalar(select(func.count()).select_from(DepositAccount)) or 0

        return {
            "charts": {
                "loan_by_product": loan_by_product,
                "secured_unsecured": secured_unsecured,
                "loan_vs_deposit": loan_vs_deposit,
                "loan_by_sector": loan_by_sector
            },
            "summary": {
                "total_loans": round(float(total_loans or 0), 2),
                "total_deposits": round(float(total_deposits or 0), 2),
                "loan_accounts": loan_count,
                "deposit_accounts": deposit_count
            }
        }
    except Exception as e:
        logging.error(f"Error in portfolio overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TAB 2: RISK & ASSET QUALITY
# =============================================================================

@router.get("/risk-asset-quality")
async def get_risk_asset_quality(
    as_on_date: Optional[str] = None,
    branch: Optional[str] = None,
    asset_class: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Risk & Asset Quality tab data - credit risk, delinquency, NPA trends, and provisioning."""
    try:
        # Chart 1: Asset Classification Distribution (Stacked Bar)
        asset_class_query = select(
            LoanAccount.d_asset_class,
            func.count(LoanAccount.id).label('count'),
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.d_asset_class)
        
        asset_class_result = await db.execute(asset_class_query)
        asset_classification = [
            {"name": row[0] or "Unknown", "count": row[1], "value": round(float(row[2] or 0), 2)}
            for row in asset_class_result.fetchall()
        ]

        # Chart 2: DPD Bucket Analysis (Bar) - Using d_overdue_dpd
        dpd_buckets = []
        bucket_definitions = [
            ("0 DPD", LoanAccount.d_overdue_dpd == 0),
            ("1-30 DPD", LoanAccount.d_overdue_dpd.between(1, 30)),
            ("31-60 DPD", LoanAccount.d_overdue_dpd.between(31, 60)),
            ("61-90 DPD", LoanAccount.d_overdue_dpd.between(61, 90)),
            ("90+ DPD", LoanAccount.d_overdue_dpd > 90),
        ]
        
        for bucket_name, condition in bucket_definitions:
            count = await db.scalar(select(func.count()).select_from(LoanAccount).where(condition)) or 0
            amount = await db.scalar(select(func.sum(LoanAccount.i_outstanding_principal)).where(condition)) or 0
            dpd_buckets.append({
                "name": bucket_name,
                "count": count,
                "value": round(float(amount), 2)
            })

        # Chart 3: NPA vs Provision Coverage (Combo)
        # Group by asset class for NPA classes
        npa_provision_query = select(
            LoanAccount.d_asset_class,
            func.sum(LoanAccount.i_outstanding_principal).label('outstanding'),
            func.sum(LoanAccount.d_total_provision).label('provision')
        ).where(LoanAccount.d_asset_class.in_(['DB1', 'DB2', 'DB3'])).group_by(LoanAccount.d_asset_class)
        
        npa_provision_result = await db.execute(npa_provision_query)
        npa_provision = []
        for row in npa_provision_result.fetchall():
            outstanding = float(row[1] or 0)
            provision = float(row[2] or 0)
            coverage = (provision / outstanding * 100) if outstanding > 0 else 0
            npa_provision.append({
                "name": row[0],
                "npa_amount": round(outstanding, 2),
                "provision": round(provision, 2),
                "coverage_percent": round(coverage, 2)
            })

        # Chart 4: Overdue Amount by Product (Horizontal Bar) - Using i_overdue_amt
        overdue_by_product_query = select(
            LoanAccount.d_loan_product_type,
            func.sum(LoanAccount.i_overdue_amt).label('overdue_amount')
        ).where(
            LoanAccount.i_overdue_amt > 0
        ).group_by(LoanAccount.d_loan_product_type).order_by(func.sum(LoanAccount.i_overdue_amt).desc()).limit(10)
        
        overdue_by_product_result = await db.execute(overdue_by_product_query)
        overdue_by_product = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in overdue_by_product_result.fetchall()
        ]

        # Summary KPIs
        total_outstanding = await db.scalar(select(func.sum(LoanAccount.i_outstanding_principal))) or 0
        total_npa = await db.scalar(
            select(func.sum(LoanAccount.i_outstanding_principal))
            .where(LoanAccount.d_asset_class.in_(['DB1', 'DB2', 'DB3']))
        ) or 0
        total_provision = await db.scalar(select(func.sum(LoanAccount.d_total_provision))) or 0
        total_overdue = await db.scalar(select(func.sum(LoanAccount.i_overdue_amt))) or 0
        
        gnpa_ratio = (float(total_npa) / float(total_outstanding) * 100) if total_outstanding > 0 else 0
        pcr = (float(total_provision) / float(total_npa) * 100) if total_npa > 0 else 0

        return {
            "charts": {
                "asset_classification": asset_classification,
                "dpd_buckets": dpd_buckets,
                "npa_provision": npa_provision,
                "overdue_by_product": overdue_by_product
            },
            "summary": {
                "total_outstanding": round(float(total_outstanding), 2),
                "gross_npa": round(float(total_npa), 2),
                "gnpa_ratio": round(gnpa_ratio, 2),
                "provision_coverage": round(pcr, 2),
                "total_overdue": round(float(total_overdue), 2)
            }
        }
    except Exception as e:
        logging.error(f"Error in risk asset quality: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TAB 3: DEPOSITS & LIQUIDITY
# =============================================================================

@router.get("/deposits-liquidity")
async def get_deposits_liquidity(
    as_on_date: Optional[str] = None,
    branch: Optional[str] = None,
    product_group: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Deposits & Liquidity tab data - deposit composition, maturity concentration, cost efficiency."""
    try:
        # Chart 1: CASA vs Term Deposits (Donut)
        product_group_query = select(
            LoanAccount.d_loan_product_type,  # Using correct column
            func.sum(DepositAccount.ledger_balance).label('total')
        ).select_from(DepositAccount).group_by(DepositAccount.account_product_group)
        
        # Simplified query
        casa_query = select(
            DepositAccount.account_product_group,
            func.sum(DepositAccount.ledger_balance).label('total')
        ).group_by(DepositAccount.account_product_group)
        
        casa_result = await db.execute(casa_query)
        deposits_by_type = []
        casa_total = 0
        term_total = 0
        for row in casa_result.fetchall():
            product = row[0] or "Unknown"
            amount = float(row[1] or 0)
            deposits_by_type.append({"name": product, "value": round(amount, 2)})
            if product in ['SBA', 'CAA']:
                casa_total += amount
            elif product == 'TDA':
                term_total += amount

        casa_vs_term = [
            {"name": "CASA (SBA+CAA)", "value": round(casa_total, 2)},
            {"name": "Term Deposits (TDA)", "value": round(term_total, 2)}
        ]

        # Chart 2: Deposit Maturity Profile (Stacked Bar)
        maturity_buckets = []
        maturity_definitions = [
            ("0-30 days", DepositAccount.days_to_maturity.between(0, 30)),
            ("31-90 days", DepositAccount.days_to_maturity.between(31, 90)),
            ("91-180 days", DepositAccount.days_to_maturity.between(91, 180)),
            ("181-365 days", DepositAccount.days_to_maturity.between(181, 365)),
            (">365 days", DepositAccount.days_to_maturity > 365),
        ]
        
        for bucket_name, condition in maturity_definitions:
            count = await db.scalar(select(func.count()).select_from(DepositAccount).where(condition)) or 0
            amount = await db.scalar(select(func.sum(DepositAccount.ledger_balance)).where(condition)) or 0
            maturity_buckets.append({
                "name": bucket_name,
                "count": count,
                "value": round(float(amount or 0), 2)
            })

        # Chart 3: Account Status Distribution (Donut)
        status_query = select(
            DepositAccount.account_status,
            func.count(DepositAccount.id).label('count'),
            func.sum(DepositAccount.ledger_balance).label('total')
        ).group_by(DepositAccount.account_status)
        
        status_result = await db.execute(status_query)
        status_labels = {'A': 'Active', 'D': 'Dormant', 'I': 'Inactive'}
        account_status = [
            {
                "name": status_labels.get(row[0], row[0] or "Unknown"),
                "count": row[1],
                "value": round(float(row[2] or 0), 2)
            }
            for row in status_result.fetchall()
        ]

        # Chart 4: Top Deposit Products by Balance (Horizontal Bar)
        top_products_query = select(
            DepositAccount.gl_description,
            func.sum(DepositAccount.ledger_balance).label('total')
        ).group_by(DepositAccount.gl_description).order_by(func.sum(DepositAccount.ledger_balance).desc()).limit(10)
        
        top_products_result = await db.execute(top_products_query)
        top_products = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in top_products_result.fetchall()
        ]

        # Summary KPIs
        total_deposits = await db.scalar(select(func.sum(DepositAccount.ledger_balance))) or 0
        total_accounts = await db.scalar(select(func.count()).select_from(DepositAccount)) or 0
        casa_ratio = (casa_total / float(total_deposits) * 100) if total_deposits > 0 else 0

        return {
            "charts": {
                "casa_vs_term": casa_vs_term,
                "maturity_buckets": maturity_buckets,
                "account_status": account_status,
                "top_products": top_products
            },
            "summary": {
                "total_deposits": round(float(total_deposits), 2),
                "total_accounts": total_accounts,
                "casa_ratio": round(casa_ratio, 2),
                "casa_amount": round(casa_total, 2)
            }
        }
    except Exception as e:
        logging.error(f"Error in deposits liquidity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TAB 4: PSL & REGULATORY
# =============================================================================

@router.get("/psl-regulatory")
async def get_psl_regulatory(
    as_on_date: Optional[str] = None,
    branch: Optional[str] = None,
    psl_category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get PSL & Regulatory tab data - Priority Sector Lending compliance and regulatory metrics."""
    try:
        # Chart 1: PSL vs Non-PSL Distribution (Donut)
        psl_query = select(
            LoanAccount.psl_non_psl,
            func.count(LoanAccount.id).label('count'),
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.psl_non_psl)
        
        psl_result = await db.execute(psl_query)
        psl_distribution = [
            {"name": row[0] or "Unknown", "count": row[1], "value": round(float(row[2] or 0), 2)}
            for row in psl_result.fetchall()
        ]

        # Chart 2: PSL by Sector (Bar)
        psl_sector_query = select(
            LoanAccount.final_sector_bifurcation,
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).where(LoanAccount.psl_non_psl == 'PSL').group_by(LoanAccount.final_sector_bifurcation)
        
        psl_sector_result = await db.execute(psl_sector_query)
        psl_by_sector = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in psl_sector_result.fetchall()
        ]

        # Chart 3: Gender-wise Lending (Donut)
        gender_query = select(
            LoanAccount.i_gender,
            func.count(LoanAccount.id).label('count'),
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.i_gender)
        
        gender_result = await db.execute(gender_query)
        gender_labels = {'M': 'Male', 'F': 'Female'}
        gender_distribution = [
            {
                "name": gender_labels.get(row[0], row[0] or "Unknown"),
                "count": row[1],
                "value": round(float(row[2] or 0), 2)
            }
            for row in gender_result.fetchall()
        ]

        # Chart 4: PSL by Product Type (Stacked Bar)
        psl_product_query = select(
            LoanAccount.d_loan_product_type,
            LoanAccount.psl_non_psl,
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.d_loan_product_type, LoanAccount.psl_non_psl)
        
        psl_product_result = await db.execute(psl_product_query)
        
        # Restructure for stacked bar chart
        product_psl_map = {}
        for row in psl_product_result.fetchall():
            product = row[0] or "Unknown"
            psl_type = row[1] or "Unknown"
            amount = round(float(row[2] or 0), 2)
            
            if product not in product_psl_map:
                product_psl_map[product] = {"name": product, "PSL": 0, "Non-PSL": 0}
            
            if psl_type == "PSL":
                product_psl_map[product]["PSL"] = amount
            else:
                product_psl_map[product]["Non-PSL"] = amount
        
        psl_by_product = list(product_psl_map.values())

        # Summary KPIs
        total_outstanding = await db.scalar(select(func.sum(LoanAccount.i_outstanding_principal))) or 0
        total_psl = await db.scalar(
            select(func.sum(LoanAccount.i_outstanding_principal))
            .where(LoanAccount.psl_non_psl == 'PSL')
        ) or 0
        psl_ratio = (float(total_psl) / float(total_outstanding) * 100) if total_outstanding > 0 else 0

        return {
            "charts": {
                "psl_distribution": psl_distribution,
                "psl_by_sector": psl_by_sector,
                "gender_distribution": gender_distribution,
                "psl_by_product": psl_by_product
            },
            "summary": {
                "total_outstanding": round(float(total_outstanding), 2),
                "total_psl": round(float(total_psl), 2),
                "psl_ratio": round(psl_ratio, 2)
            }
        }
    except Exception as e:
        logging.error(f"Error in psl regulatory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TAB 5: CUSTOMER INSIGHTS
# =============================================================================

@router.get("/customer-insights")
async def get_customer_insights(
    as_on_date: Optional[str] = None,
    branch: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get Customer Insights tab data - customer concentration, cross-sell, demographics."""
    try:
        # Chart 1: Top 10 Borrowers (Horizontal Bar)
        top_borrowers_query = select(
            LoanAccount.i_customer_name,
            func.sum(LoanAccount.i_outstanding_principal).label('total')
        ).group_by(LoanAccount.i_customer_id, LoanAccount.i_customer_name).order_by(
            func.sum(LoanAccount.i_outstanding_principal).desc()
        ).limit(10)
        
        top_borrowers_result = await db.execute(top_borrowers_query)
        top_borrowers = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in top_borrowers_result.fetchall()
        ]

        # Chart 2: Top 10 Depositors (Horizontal Bar)
        top_depositors_query = select(
            DepositAccount.account_title,
            func.sum(DepositAccount.ledger_balance).label('total')
        ).group_by(DepositAccount.customer_number, DepositAccount.account_title).order_by(
            func.sum(DepositAccount.ledger_balance).desc()
        ).limit(10)
        
        top_depositors_result = await db.execute(top_depositors_query)
        top_depositors = [
            {"name": row[0] or "Unknown", "value": round(float(row[1] or 0), 2)}
            for row in top_depositors_result.fetchall()
        ]

        # Chart 3: Customers with Both Products (KPI)
        cross_sell_query = text("""
            SELECT COUNT(DISTINCT l.i_customer_id)
            FROM loan_accounts l
            INNER JOIN deposit_accounts d ON l.i_customer_id = d.customer_number
        """)
        cross_sell_result = await db.execute(cross_sell_query)
        customers_with_both = cross_sell_result.scalar() or 0

        # Chart 4: Customer Net Position Distribution (Bar)
        # Get customers with both products and calculate net position
        net_position_query = text("""
            SELECT 
                CASE 
                    WHEN (COALESCE(d.total_deposits, 0) - COALESCE(l.total_loans, 0)) < -100000 THEN 'Net Borrower (>1L)'
                    WHEN (COALESCE(d.total_deposits, 0) - COALESCE(l.total_loans, 0)) < 0 THEN 'Net Borrower (<1L)'
                    WHEN (COALESCE(d.total_deposits, 0) - COALESCE(l.total_loans, 0)) < 100000 THEN 'Net Depositor (<1L)'
                    ELSE 'Net Depositor (>1L)'
                END as position_bucket,
                COUNT(*) as customer_count
            FROM (
                SELECT i_customer_id, SUM(i_outstanding_principal) as total_loans
                FROM loan_accounts
                GROUP BY i_customer_id
            ) l
            LEFT JOIN (
                SELECT customer_number, SUM(ledger_balance) as total_deposits
                FROM deposit_accounts
                GROUP BY customer_number
            ) d ON l.i_customer_id = d.customer_number
            GROUP BY position_bucket
            ORDER BY customer_count DESC
        """)
        
        try:
            net_position_result = await db.execute(net_position_query)
            net_position = [
                {"name": row[0], "value": row[1]}
                for row in net_position_result.fetchall()
            ]
        except:
            net_position = []

        # Summary KPIs
        unique_loan_customers = await db.scalar(select(func.count(func.distinct(LoanAccount.i_customer_id)))) or 0
        unique_deposit_customers = await db.scalar(select(func.count(func.distinct(DepositAccount.customer_number)))) or 0
        
        # Calculate concentration
        total_outstanding = await db.scalar(select(func.sum(LoanAccount.i_outstanding_principal))) or 0
        top_10_exposure = sum([b["value"] for b in top_borrowers[:10]])
        concentration_ratio = (top_10_exposure / float(total_outstanding) * 100) if total_outstanding > 0 else 0

        return {
            "charts": {
                "top_borrowers": top_borrowers,
                "top_depositors": top_depositors,
                "net_position": net_position
            },
            "summary": {
                "unique_loan_customers": unique_loan_customers,
                "unique_deposit_customers": unique_deposit_customers,
                "customers_with_both": customers_with_both,
                "top_10_concentration": round(concentration_ratio, 2)
            }
        }
    except Exception as e:
        logging.error(f"Error in customer insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
