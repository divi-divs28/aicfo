"""
Chat-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class CreateSessionRequest(BaseModel):
    user_id: int


class CreateSessionResponse(BaseModel):
    session_id: str
    session_title: str


class ChatQuery(BaseModel):
    message: str
    user_id: int = 1
    session_id: Optional[str] = None


class ChartData(BaseModel):
    data: List[Dict[str, Any]]
    type: str
    title: str
    description: Optional[str] = None


class TableData(BaseModel):
    headers: List[str]
    rows: List[List[Any]]  # Display rows (limited to 10)
    title: str
    description: Optional[str] = None
    full_data: Optional[List[List[Any]]] = None  # All rows for Excel export
    total_rows: Optional[int] = None  # Total number of rows before limiting
    is_truncated: Optional[bool] = False  # Whether data was truncated for display
    sql_query: Optional[str] = None  # SQL query for fetching full data for Excel export
    
    class Config:
        # Allow mutation of model fields
        validate_assignment = True


class KPICard(BaseModel):
    label: str
    value: Any
    unit: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    charts: List[ChartData] = []
    tables: List[TableData] = []
    summary_points: List[str] = []
    kpi_cards: List[KPICard] = []


# Question Category schemas
class QuestionCategoryCreate(BaseModel):
    title: str
    color: str = 'bg-blue-50 border-blue-100'
    icon_bg: str = 'bg-blue-500'
    text_color: str = 'text-blue-700'
    icon_type: str = 'chart'
    order_index: int = 0


class QuestionCategoryUpdate(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    icon_bg: Optional[str] = None
    text_color: Optional[str] = None
    icon_type: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class QuestionCategoryResponse(BaseModel):
    id: str
    title: str
    color: str
    icon_bg: str
    text_color: str
    icon_type: str
    order_index: int
    is_active: bool
    created_at: datetime


# Suggested Question schemas
class SuggestedQuestionCreate(BaseModel):
    category_id: str
    question_text: str
    order_index: int = 0


class SuggestedQuestionUpdate(BaseModel):
    category_id: Optional[str] = None
    question_text: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class SuggestedQuestionResponse(BaseModel):
    id: str
    category_id: str
    question_text: str
    order_index: int
    is_active: bool
    created_at: datetime


# Dashboard Card schemas
class DashboardCardCreate(BaseModel):
    title: str
    icon: str
    description: str
    gradient: str
    bg_color: str
    text_color: str
    query_type: str
    order_index: int = 0


class DashboardCardUpdate(BaseModel):
    title: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    gradient: Optional[str] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    query_type: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class DashboardCardResponse(BaseModel):
    id: str
    title: str
    icon: str
    description: str
    gradient: str
    bg_color: str
    text_color: str
    query_type: str
    order_index: int
    is_active: bool
    created_at: datetime
