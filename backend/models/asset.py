"""
Asset manager domain SQLAlchemy models.
Properties, Auctions, and Bids tables.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Date, Text, BigInteger
from datetime import datetime

from database import Base


class Property(Base):
    """Property/asset listing."""
    __tablename__ = 'properties'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    description = Column(Text)
    location = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    county = Column(String(100))
    property_type = Column(String(50))
    size_sqft = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    estimated_value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Auction(Base):
    """Auction event linked to a property."""
    __tablename__ = 'auctions'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String(100))
    title = Column(String(255))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(50))  # upcoming, live, closed
    starting_bid = Column(Float)
    current_bid = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bid(Base):
    """Bid placed on an auction."""
    __tablename__ = 'bids'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    auction_id = Column(String(100))
    property_id = Column(String(100))
    investor_id = Column(String(100))
    bid_amount = Column(Float)
    bid_time = Column(DateTime)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
