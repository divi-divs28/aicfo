"""
Dashboard Asset Manager routes.
API endpoints for dashboard tabs with data from properties, auctions, and bids.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
from datetime import datetime

from database import get_db
from models.asset import Property, Auction, Bid

router = APIRouter(prefix="/dashboard")


# =============================================================================
# PROPERTIES OVERVIEW
# =============================================================================

@router.get("/properties-overview")
async def get_properties_overview(db: AsyncSession = Depends(get_db)):
    """Get Properties overview: counts by type, location, and value distribution."""
    try:
        # Total properties
        total = await db.scalar(select(func.count()).select_from(Property)) or 0

        # By property type (donut)
        type_query = select(
            Property.property_type,
            func.count(Property.id).label('count')
        ).group_by(Property.property_type)
        type_result = await db.execute(type_query)
        by_type = [
            {"name": row[0] or "Unknown", "value": row[1]}
            for row in type_result.fetchall()
        ]

        # By state/region (bar)
        region_query = select(
            Property.state,
            func.count(Property.id).label('count')
        ).where(Property.state.isnot(None), Property.state != '').group_by(Property.state).order_by(
            func.count(Property.id).desc()
        ).limit(10)
        region_result = await db.execute(region_query)
        by_region = [
            {"name": row[0] or "Unknown", "value": row[1]}
            for row in region_result.fetchall()
        ]

        # Total estimated value
        total_value = await db.scalar(select(func.sum(Property.estimated_value)).where(
            Property.estimated_value.isnot(None)
        )) or 0

        return {
            "charts": {
                "by_type": by_type,
                "by_region": by_region,
            },
            "summary": {
                "total_properties": total,
                "total_estimated_value": round(float(total_value), 2),
            }
        }
    except Exception as e:
        logging.error(f"Error in properties overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AUCTIONS OVERVIEW
# =============================================================================

@router.get("/auctions-overview")
async def get_auctions_overview(db: AsyncSession = Depends(get_db)):
    """Get Auctions overview: status distribution, timeline, bid activity."""
    try:
        total = await db.scalar(select(func.count()).select_from(Auction)) or 0

        # By status (donut)
        status_query = select(
            Auction.status,
            func.count(Auction.id).label('count')
        ).group_by(Auction.status)
        status_result = await db.execute(status_query)
        by_status = [
            {"name": (row[0] or "unknown").capitalize(), "value": row[1]}
            for row in status_result.fetchall()
        ]

        # Total starting bid vs current bid (bar)
        total_starting = await db.scalar(select(func.sum(Auction.starting_bid)).where(
            Auction.starting_bid.isnot(None)
        )) or 0
        total_current = await db.scalar(select(func.sum(Auction.current_bid)).where(
            Auction.current_bid.isnot(None)
        )) or 0
        bid_comparison = [
            {"name": "Total Starting Bid", "value": round(float(total_starting), 2)},
            {"name": "Total Current Bid", "value": round(float(total_current), 2)},
        ]

        # Live and upcoming counts
        live = await db.scalar(
            select(func.count()).select_from(Auction).where(Auction.status == 'live')
        ) or 0
        upcoming = await db.scalar(
            select(func.count()).select_from(Auction).where(Auction.status == 'upcoming')
        ) or 0
        closed = await db.scalar(
            select(func.count()).select_from(Auction).where(Auction.status == 'closed')
        ) or 0

        return {
            "charts": {
                "by_status": by_status,
                "bid_comparison": bid_comparison,
            },
            "summary": {
                "total_auctions": total,
                "live_auctions": live,
                "upcoming_auctions": upcoming,
                "closed_auctions": closed,
            }
        }
    except Exception as e:
        logging.error(f"Error in auctions overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BIDS OVERVIEW
# =============================================================================

@router.get("/bids-overview")
async def get_bids_overview(db: AsyncSession = Depends(get_db)):
    """Get Bids overview: total bids, amount distribution, activity."""
    try:
        total = await db.scalar(select(func.count()).select_from(Bid)) or 0
        total_amount = await db.scalar(select(func.sum(Bid.bid_amount)).where(
            Bid.bid_amount.isnot(None)
        )) or 0

        # By status (donut)
        status_query = select(
            Bid.status,
            func.count(Bid.id).label('count')
        ).group_by(Bid.status)
        status_result = await db.execute(status_query)
        by_status = [
            {"name": (row[0] or "unknown").capitalize(), "value": row[1]}
            for row in status_result.fetchall()
        ]

        # Average bid amount (for summary)
        avg_bid = await db.scalar(
            select(func.avg(Bid.bid_amount)).where(Bid.bid_amount.isnot(None), Bid.bid_amount > 0)
        ) or 0

        return {
            "charts": {
                "by_status": by_status,
            },
            "summary": {
                "total_bids": total,
                "total_bid_amount": round(float(total_amount), 2),
                "average_bid": round(float(avg_bid), 2),
            }
        }
    except Exception as e:
        logging.error(f"Error in bids overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ASSET MANAGER KPI STRIP (single endpoint for header KPIs)
# =============================================================================

@router.get("/asset-kpis")
async def get_asset_kpis(db: AsyncSession = Depends(get_db)):
    """Get KPI values for the dashboard strip: total properties, auctions, bids, live/upcoming."""
    try:
        total_properties = await db.scalar(select(func.count()).select_from(Property)) or 0
        total_auctions = await db.scalar(select(func.count()).select_from(Auction)) or 0
        total_bids = await db.scalar(select(func.count()).select_from(Bid)) or 0
        live_auctions = await db.scalar(
            select(func.count()).select_from(Auction).where(Auction.status == 'live')
        ) or 0
        upcoming_auctions = await db.scalar(
            select(func.count()).select_from(Auction).where(Auction.status == 'upcoming')
        ) or 0
        total_bid_value = await db.scalar(
            select(func.sum(Bid.bid_amount)).where(Bid.bid_amount.isnot(None))
        ) or 0

        return {
            "total_properties": total_properties,
            "total_auctions": total_auctions,
            "total_bids": total_bids,
            "live_auctions": live_auctions,
            "upcoming_auctions": upcoming_auctions,
            "total_bid_value": round(float(total_bid_value), 2),
        }
    except Exception as e:
        logging.error(f"Error fetching asset KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
