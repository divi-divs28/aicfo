"""
Dashboard routes.
Sample questions and dashboard statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, update
from datetime import datetime, timedelta
import logging

from database import get_db
from models.base import User
from models.financial import LoanAccount, DepositAccount
from models.asset import Property, Auction, Bid
from models.chat import QuestionCategory, SuggestedQuestion, DashboardCard

router = APIRouter()


async def _financial_overview_from_aicfo(db: AsyncSession):
    """Build financial overview from aicfo models (Company, Invoice)."""
    from models.aicfo import Company, Invoice

    # KPIs
    total_revenue = await db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0)).select_from(Invoice)) or 0
    outstanding = await db.scalar(select(func.coalesce(func.sum(Invoice.balance_amount), 0)).select_from(Invoice)) or 0
    overdue_count = await db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.status == 'overdue')
    ) or 0
    active_companies = await db.scalar(select(func.count()).select_from(Company)) or 0

    # Monthly revenue (last 6 months)
    six_months_ago = datetime.utcnow().date() - timedelta(days=180)
    monthly_q = (
        select(
            func.extract('year', Invoice.invoice_date).label('y'),
            func.extract('month', Invoice.invoice_date).label('m'),
            func.coalesce(func.sum(Invoice.invoice_amount), 0).label('billed'),
            func.coalesce(func.sum(Invoice.paid_amount), 0).label('collected'),
        )
        .where(Invoice.invoice_date >= six_months_ago)
        .group_by(func.extract('year', Invoice.invoice_date), func.extract('month', Invoice.invoice_date))
        .order_by(func.extract('year', Invoice.invoice_date), func.extract('month', Invoice.invoice_date))
    )
    monthly_result = await db.execute(monthly_q)
    monthly_rows = monthly_result.fetchall()
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_revenue = [
        {"month": month_names[int(r[1]) - 1] if r[1] else "", "billed": float(r[2] or 0), "collected": float(r[3] or 0)}
        for r in (monthly_rows[-6:] if len(monthly_rows) > 6 else monthly_rows)
    ]

    # Status breakdown
    status_q = (
        select(Invoice.status, func.coalesce(func.sum(Invoice.invoice_amount), 0))
        .where(Invoice.status.isnot(None))
        .group_by(Invoice.status)
    )
    status_result = await db.execute(status_q)
    status_rows = status_result.fetchall()
    status_breakdown = [{"name": (s[0] or "unpaid").capitalize(), "value": float(s[1] or 0)} for s in status_rows]

    # Top companies
    companies_result = await db.execute(select(Company).order_by(Company.id).limit(50))
    companies = companies_result.scalars().all()
    top_companies = []
    for c in companies[:7]:
        recv = await db.scalar(
            select(func.coalesce(func.sum(Invoice.balance_amount), 0)).where(Invoice.invoice_from_company == c.id)
        ) or 0
        pay = await db.scalar(
            select(func.coalesce(func.sum(Invoice.balance_amount), 0)).where(Invoice.invoice_to_company == c.id)
        ) or 0
        top_companies.append({
            "id": c.id,
            "name": c.company_name,
            "industry": "",
            "receivable": float(recv),
            "payable": float(pay),
            "status": "Active",
        })
    top_companies.sort(key=lambda x: x["receivable"], reverse=True)
    top_companies = top_companies[:7]

    # Recent invoices
    inv_result = await db.execute(select(Invoice).order_by(Invoice.invoice_date.desc()).limit(8))
    recent_inv = inv_result.scalars().all()
    recent_invoices = [
        {
            "id": f"INV-{inv.invoice_id}",
            "amount": float(inv.invoice_amount or 0),
            "currency": inv.currency or "INR",
            "due": inv.due_date.isoformat() if inv.due_date else "",
            "status": inv.status or "unpaid",
        }
        for inv in recent_inv
    ]

    total_receivable = sum(t["receivable"] for t in top_companies)
    total_payable = sum(t["payable"] for t in top_companies)
    net_position = total_receivable - total_payable

    return {
        "kpis": {
            "total_revenue": float(total_revenue),
            "outstanding_balance": float(outstanding),
            "overdue_count": int(overdue_count),
            "active_companies": int(active_companies),
        },
        "monthly_revenue": monthly_revenue,
        "status_breakdown": status_breakdown,
        "top_companies": top_companies,
        "recent_invoices": recent_invoices,
        "stat_strip": {
            "total_receivable": total_receivable,
            "total_payable": total_payable,
            "net_position": net_position,
        },
    }


def _empty_financial_overview():
    """Return empty overview when aicfo tables are missing."""
    return {
        "kpis": {"total_revenue": 0, "outstanding_balance": 0, "overdue_count": 0, "active_companies": 0},
        "monthly_revenue": [],
        "status_breakdown": [],
        "top_companies": [],
        "recent_invoices": [],
        "stat_strip": {"total_receivable": 0, "total_payable": 0, "net_position": 0},
    }


@router.get("/financial-overview")
async def get_financial_overview(db: AsyncSession = Depends(get_db)):
    """Get financial dashboard overview from aicfo DB (companies, invoices). Returns empty data if tables missing."""
    try:
        return await _financial_overview_from_aicfo(db)
    except Exception as e:
        logging.warning(f"Financial overview unavailable (aicfo tables may be missing): {e}")
        return _empty_financial_overview()


@router.get("/industries")
async def list_industries(db: AsyncSession = Depends(get_db)):
    """List all industries for filter dropdown. Returns empty if table missing."""
    try:
        from models.aicfo import Industry
        r = await db.execute(select(Industry).order_by(Industry.industry_name))
        rows = r.scalars().all()
        return {"data": [{"id": i.id, "name": i.industry_name} for i in rows]}
    except Exception as e:
        logging.warning(f"List industries unavailable: {e}")
        return {"data": []}


@router.get("/regions")
async def list_regions(db: AsyncSession = Depends(get_db)):
    """List distinct regions from company for filter dropdown."""
    try:
        from models.aicfo import Company
        r = await db.execute(
            select(Company.region).where(Company.region.isnot(None), Company.region != "").distinct().order_by(Company.region)
        )
        rows = r.fetchall()
        return {"data": [{"name": row[0]} for row in rows if row[0]]}
    except Exception as e:
        logging.warning(f"List regions unavailable: {e}")
        return {"data": []}


@router.get("/companies")
async def list_companies(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    industry_id: int = None,
    region: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List companies with industry, city, state, gst_no, receivable, payable, invoice_count. Paginated."""
    try:
        from models.aicfo import Company, Invoice, Industry

        count_base = select(func.count()).select_from(Company)
        if search and search.strip():
            q = f"%{search.strip()}%"
            count_base = count_base.where(
                (Company.company_name.ilike(q)) | (Company.city.ilike(q)) | (Company.state.ilike(q))
            )
        if industry_id is not None:
            count_base = count_base.where(Company.industry_id == industry_id)
        if region and region.strip():
            count_base = count_base.where(Company.region == region.strip())

        total = await db.scalar(count_base) or 0
        offset = (max(1, page) - 1) * max(1, min(page_size, 100))
        limit = max(1, min(page_size, 100))

        base = (
            select(Company, Industry.industry_name)
            .select_from(Company)
            .outerjoin(Industry, Company.industry_id == Industry.id)
        )
        if search and search.strip():
            q = f"%{search.strip()}%"
            base = base.where(
                (Company.company_name.ilike(q)) | (Company.city.ilike(q)) | (Company.state.ilike(q))
            )
        if industry_id is not None:
            base = base.where(Company.industry_id == industry_id)
        if region and region.strip():
            base = base.where(Company.region == region.strip())

        companies_result = await db.execute(
            base.order_by(Company.company_name).offset(offset).limit(limit)
        )
        rows = companies_result.fetchall()

        if not rows:
            return {"data": [], "total": total, "page": page, "page_size": limit}

        companies = [r[0] for r in rows]
        industry_names = [r[1] if len(r) > 1 else "" for r in rows]
        ids = [c.id for c in companies]
        recv_q = (
            select(Invoice.invoice_from_company, func.coalesce(func.sum(Invoice.balance_amount), 0))
            .where(Invoice.invoice_from_company.in_(ids))
            .group_by(Invoice.invoice_from_company)
        )
        pay_q = (
            select(Invoice.invoice_to_company, func.coalesce(func.sum(Invoice.balance_amount), 0))
            .where(Invoice.invoice_to_company.in_(ids))
            .group_by(Invoice.invoice_to_company)
        )
        from_cnt_q = (
            select(Invoice.invoice_from_company, func.count())
            .where(Invoice.invoice_from_company.in_(ids))
            .group_by(Invoice.invoice_from_company)
        )
        to_cnt_q = (
            select(Invoice.invoice_to_company, func.count())
            .where(Invoice.invoice_to_company.in_(ids))
            .group_by(Invoice.invoice_to_company)
        )
        recv_rows = (await db.execute(recv_q)).fetchall()
        pay_rows = (await db.execute(pay_q)).fetchall()
        from_cnt_rows = (await db.execute(from_cnt_q)).fetchall()
        to_cnt_rows = (await db.execute(to_cnt_q)).fetchall()
        receivables = {r[0]: float(r[1]) for r in recv_rows}
        payables = {r[0]: float(r[1]) for r in pay_rows}
        from_counts = {r[0]: r[1] for r in from_cnt_rows}
        to_counts = {r[0]: r[1] for r in to_cnt_rows}

        out = []
        for i, c in enumerate(companies):
            industry_name = (industry_names[i] or "") if i < len(industry_names) else ""
            inv_count = from_counts.get(c.id, 0) + to_counts.get(c.id, 0)
            out.append({
                "id": c.id,
                "name": c.company_name,
                "industry": industry_name or "",
                "city": (c.city or "") or "",
                "state": (c.state or "") or "",
                "region": (c.region or "") or "",
                "gst_no": (c.gst_no or "") or "",
                "receivable": receivables.get(c.id, 0.0),
                "payable": payables.get(c.id, 0.0),
                "invoice_count": int(inv_count),
                "status": "Active",
            })

        return {"data": out, "total": total, "page": page, "page_size": limit}
    except Exception as e:
        logging.warning(f"List companies unavailable: {e}")
        return {"data": [], "total": 0, "page": 1, "page_size": page_size}


def _demo_period_days(period: str | None) -> int:
    """Return number of days for demo period: 7d, 1m, 3m. Default 7."""
    if not period:
        return 7
    p = period.lower().strip()
    if p in ("7d", "7"):
        return 7
    if p in ("1m", "30", "1"):
        return 30
    if p in ("3m", "90", "3"):
        return 90
    return 7


@router.get("/invoices")
async def list_invoices(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List invoices for datatable with from/to company names. Paginated and searchable."""
    try:
        from models.aicfo import Invoice, Company

        count_base = select(func.count()).select_from(Invoice)
        if search and search.strip():
            q = f"%{search.strip()}%"
            from_sq = select(Invoice.invoice_id).join(Company, Invoice.invoice_from_company == Company.id).where(Company.company_name.like(q))
            to_sq = select(Invoice.invoice_id).join(Company, Invoice.invoice_to_company == Company.id).where(Company.company_name.like(q))
            count_base = select(func.count()).select_from(Invoice).where(
                (Invoice.invoice_id.in_(from_sq)) | (Invoice.invoice_id.in_(to_sq))
            )
        total = await db.scalar(count_base) or 0
        offset = (max(1, page) - 1) * max(1, min(page_size, 100))
        limit = max(1, min(page_size, 100))

        base = (
            select(Invoice, Company.company_name.label("from_name"))
            .select_from(Invoice)
            .outerjoin(Company, Invoice.invoice_from_company == Company.id)
        )
        if search and search.strip():
            q = f"%{search.strip()}%"
            from_match = select(Invoice.invoice_id).join(Company, Invoice.invoice_from_company == Company.id).where(Company.company_name.like(q))
            to_match = select(Invoice.invoice_id).join(Company, Invoice.invoice_to_company == Company.id).where(Company.company_name.like(q))
            base = base.where(
                (Invoice.invoice_id.in_(from_match)) | (Invoice.invoice_id.in_(to_match))
            )
        inv_result = await db.execute(
            base.order_by(Invoice.invoice_date.desc()).offset(offset).limit(limit)
        )
        rows = inv_result.fetchall()
        to_ids = [r[0].invoice_to_company for r in rows]
        to_names = {}
        if to_ids:
            to_result = await db.execute(
                select(Company.id, Company.company_name).where(Company.id.in_(to_ids))
            )
            to_names = {r[0]: r[1] for r in to_result.fetchall()}

        out = []
        for r in rows:
            inv, from_name = r[0], r[1] if len(r) > 1 else ""
            to_name = to_names.get(inv.invoice_to_company, "")
            out.append({
                "id": f"INV-{inv.invoice_id}",
                "invoice_id": inv.invoice_id,
                "from_company_name": from_name or "",
                "to_company_name": to_name or "",
                "amount": float(inv.invoice_amount or 0),
                "paid": float(inv.paid_amount or 0),
                "balance": float(inv.balance_amount or 0),
                "currency": inv.currency or "INR",
                "due": inv.due_date.isoformat() if inv.due_date else "",
                "status": inv.status or "unpaid",
            })
        return {"data": out, "total": total, "page": page, "page_size": limit}
    except Exception as e:
        logging.warning(f"List invoices unavailable: {e}")
        return {"data": [], "total": 0, "page": 1, "page_size": page_size}


@router.post("/invoices/update-demo-records")
async def update_demo_records(
    period: str = "7d",
    limit: int = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Update accounts: shift invoice_date/due_date/created_at into the selected period (7d, 1m, 3m),
    then recompute status so mapping is correct after the new due_dates.
    - period: 7d | 1m | 3m (window to spread dates into).
    - limit: optional max number of records to shift (e.g. 100). If omitted, all records are updated.
      Status is always recomputed for the entire table after date shifts.
    """
    try:
        from models.aicfo import Invoice

        days_back = _demo_period_days(period)
        today = datetime.utcnow().date()
        start = today - timedelta(days=days_back)

        # 1) Shift invoice_date/due_date/created_at into selected period (optional limit)
        q = (
            select(Invoice.invoice_id, Invoice.invoice_date, Invoice.due_date)
            .order_by(Invoice.invoice_id)
        )
        if limit is not None and limit > 0:
            q = q.limit(limit)
        result = await db.execute(q)
        rows = result.fetchall()

        for i, (invoice_id, old_inv_date, old_due_date) in enumerate(rows):
            day_index = i % max(1, days_back)
            new_invoice_date = start + timedelta(days=min(day_index, days_back - 1))
            if new_invoice_date > today:
                new_invoice_date = today
            try:
                offset_days = (old_due_date - old_inv_date).days
            except Exception:
                offset_days = 30
            new_due_date = new_invoice_date + timedelta(days=offset_days)
            new_created_at = datetime.combine(new_invoice_date, datetime.min.time())
            await db.execute(
                update(Invoice)
                .where(Invoice.invoice_id == invoice_id)
                .values(
                    invoice_date=new_invoice_date,
                    due_date=new_due_date,
                    created_at=new_created_at,
                    updated_at=datetime.utcnow(),
                )
            )

        # 2) Recompute status after date updates (correct mapping from new due_date)
        await db.execute(text("""
            UPDATE accounts
            SET status = CASE
                WHEN paid_amount >= invoice_amount THEN 'paid'
                WHEN paid_amount > 0 AND paid_amount < invoice_amount AND due_date < CURDATE() THEN 'overdue'
                WHEN paid_amount > 0 AND paid_amount < invoice_amount THEN 'partial'
                WHEN paid_amount = 0 AND due_date < CURDATE() THEN 'overdue'
                ELSE 'unpaid'
            END
        """))
        await db.commit()
        return {
            "ok": True,
            "updated": len(rows),
            "period": period,
            "limit": limit,
            "message": f"Shifted {len(rows)} record(s) into period={period}, then recomputed status for all accounts.",
        }
    except Exception as e:
        await db.rollback()
        logging.exception("update-demo-records failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sample-questions")
async def sample_questions(db: AsyncSession = Depends(get_db)):
    """Get sample questions organized by category."""
    try:
        categories_result = await db.execute(
            select(QuestionCategory)
            .where(QuestionCategory.is_active == True)
            .order_by(QuestionCategory.order_index)
        )
        categories = categories_result.scalars().all()
        
        result = []
        for category in categories:
            questions_result = await db.execute(
                select(SuggestedQuestion)
                .where(SuggestedQuestion.category_id == category.id, SuggestedQuestion.is_active == True)
                .order_by(SuggestedQuestion.order_index)
            )
            questions = questions_result.scalars().all()
            
            if questions:
                result.append({
                    "id": category.id,
                    "title": category.title,
                    "color": category.color,
                    "icon_bg": category.icon_bg,
                    "text_color": category.text_color,
                    "icon_type": category.icon_type,
                    "questions": [q.question_text for q in questions]
                })
        
        if not result:
            return {"categories": [{
                "id": "fallback",
                "title": "Portfolio Analysis",
                "color": "bg-blue-50 border-blue-100",
                "icon_bg": "bg-blue-500",
                "text_color": "text-blue-700",
                "icon_type": "chart",
                "questions": [
                    "Give me a portfolio overview",
                    "What is the current NPA ratio?",
                    "Show me the top loan exposures"
                ]
            }]}
        
        return {"categories": result}
    except Exception as e:
        logging.error(f"Error fetching sample questions: {e}")
        return {"categories": []}


@router.get("/dashboard-stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics based on configured cards."""
    try:
        cards_result = await db.execute(
            select(DashboardCard)
            .where(DashboardCard.is_active == True)
            .order_by(DashboardCard.order_index)
        )
        card_configs = cards_result.scalars().all()
        
        stats = {}
        
        for card in card_configs:
            query_type = card.query_type
            
            try:
                if query_type == "total_users":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(User)) or 0
                
                elif query_type == "total_loans":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(LoanAccount)) or 0
                
                elif query_type == "total_deposits":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(DepositAccount)) or 0
                
                elif query_type == "total_outstanding":
                    stats[query_type] = await db.scalar(
                        select(func.sum(LoanAccount.i_outstanding_principal))
                    ) or 0
                
                elif query_type == "total_deposit_balance":
                    stats[query_type] = await db.scalar(
                        select(func.sum(DepositAccount.ledger_balance))
                    ) or 0
                
                elif query_type == "npa_count":
                    stats[query_type] = await db.scalar(
                        select(func.count()).select_from(LoanAccount)
                        .where(LoanAccount.d_asset_class.in_(['DB1', 'DB2', 'DB3']))
                    ) or 0
                
                elif query_type == "total_properties":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(Property)) or 0
                
                elif query_type == "total_auctions":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(Auction)) or 0
                
                elif query_type == "total_bids":
                    stats[query_type] = await db.scalar(select(func.count()).select_from(Bid)) or 0
                
                elif query_type == "live_auctions":
                    stats[query_type] = await db.scalar(
                        select(func.count()).select_from(Auction).where(Auction.status == 'live')
                    ) or 0
                
                elif query_type == "upcoming_auctions":
                    stats[query_type] = await db.scalar(
                        select(func.count()).select_from(Auction).where(Auction.status == 'upcoming')
                    ) or 0
                
                else:
                    stats[query_type] = 0
                    
            except Exception as e:
                logging.error(f"Error calculating stat for {query_type}: {e}")
                stats[query_type] = 0
        
        cards_data = []
        for card in card_configs:
            cards_data.append({
                "id": card.id,
                "title": card.title,
                "icon": card.icon,
                "description": card.description,
                "gradient": card.gradient,
                "bg_color": card.bg_color,
                "text_color": card.text_color,
                "value": stats.get(card.query_type, 0),
                "query_type": card.query_type
            })
        
        return {"cards": cards_data, "stats": stats}
    
    except Exception as e:
        logging.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
