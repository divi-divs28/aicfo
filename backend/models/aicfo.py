"""
AICFO domain models - industries, company, and invoices (accounts table).
Schema aligned with training_data.py DDL (aicfo_db).
"""
from sqlalchemy import Column, String, Integer, BigInteger, Text, Date, DateTime, Numeric, ForeignKey
from datetime import datetime

from database import Base


class Industry(Base):
    """Industries lookup table."""
    __tablename__ = 'industries'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry_name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Company(Base):
    """Company master - links to industry."""
    __tablename__ = 'company'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    billing_details = Column(Text, nullable=True)
    zipcode = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    gst_no = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    industry_id = Column(Integer, ForeignKey('industries.id', ondelete='SET NULL'), nullable=True)


class Invoice(Base):
    """
    Invoices / accounts - from company to company with amount and status.
    Table name is 'accounts' in the database.
    """
    __tablename__ = 'accounts'
    __table_args__ = {'extend_existing': True}

    invoice_id = Column(BigInteger, primary_key=True, autoincrement=True)
    invoice_from_company = Column(BigInteger, ForeignKey('company.id', ondelete='CASCADE'), nullable=False)
    invoice_to_company = Column(BigInteger, ForeignKey('company.id', ondelete='CASCADE'), nullable=False)
    invoice_amount = Column(Numeric(15, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(15, 2), nullable=False, default=0)
    balance_amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), nullable=True)  # paid | partial | unpaid | overdue
