"""
Excel Export API Routes.
Handles Excel report generation and download.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import io
from datetime import datetime

from services.excel_service import ExcelReportGenerator


router = APIRouter(prefix="/api/export", tags=["export"])


class ChartDataModel(BaseModel):
    """Model for chart data."""
    type: Optional[str] = "bar"
    title: Optional[str] = "Chart"
    description: Optional[str] = None
    data: Any = None


class TableDataModel(BaseModel):
    """Model for table data."""
    headers: List[str] = []
    rows: List[List[Any]] = []
    full_data: Optional[List[List[Any]]] = None
    title: Optional[str] = "Table"
    description: Optional[str] = None


class ExcelReportRequest(BaseModel):
    """Request model for Excel report generation."""
    summary_points: Optional[List[str]] = []
    content: Optional[str] = ""
    charts: Optional[List[ChartDataModel]] = []
    tables: Optional[List[TableDataModel]] = []


class SingleTableExportRequest(BaseModel):
    """Request model for single table Excel export."""
    headers: List[str] = []
    rows: List[List[Any]] = []
    full_data: Optional[List[List[Any]]] = None
    title: Optional[str] = "Table"
    description: Optional[str] = None
    sql_query: Optional[str] = None  # SQL query to fetch full data


@router.post("/excel")
async def generate_excel_report(request: ExcelReportRequest):
    """
    Generate an Excel report from the provided data.
    
    Returns the Excel file as a downloadable attachment.
    """
    try:
        # Convert Pydantic models to dicts
        report_data = {
            "summary_points": request.summary_points or [],
            "content": request.content or "",
            "charts": [chart.model_dump() for chart in (request.charts or [])],
            "tables": [table.model_dump() for table in (request.tables or [])]
        }
        
        # Generate Excel report
        excel_generator = ExcelReportGenerator()
        excel_bytes = excel_generator.generate_report(report_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"FinSight_Report_{timestamp}.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    
    except Exception as e:
        print(f"Error generating Excel report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel report: {str(e)}")


@router.post("/excel/table")
async def export_single_table(request: SingleTableExportRequest):
    """
    Export a single table to Excel with formatting.
    If sql_query is provided, fetches full data from database.
    
    Returns the Excel file as a downloadable attachment.
    """
    try:
        export_rows = request.full_data or request.rows
        export_headers = request.headers
        
        # If SQL query is provided, fetch full data from database
        if request.sql_query:
            try:
                import pandas as pd
                import pymysql
                import ssl
                from config import (
                    VANNA_DB_HOST,
                    VANNA_DB_PORT,
                    VANNA_DB_NAME,
                    VANNA_DB_USER,
                    VANNA_DB_PASSWORD,
                )
                
                # Create SSL context
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Connect directly to database
                conn = pymysql.connect(
                    host=VANNA_DB_HOST,
                    port=VANNA_DB_PORT,
                    database=VANNA_DB_NAME,
                    user=VANNA_DB_USER,
                    password=VANNA_DB_PASSWORD,
                    ssl=ssl_context,
                    connect_timeout=60,
                )
                
                df = pd.read_sql(request.sql_query, conn)
                conn.close()
                
                # Convert DataFrame to rows format
                export_headers = list(df.columns)
                export_rows = df.values.tolist()
                print(f"Excel export: Fetched {len(export_rows)} rows from database")
                
            except Exception as e:
                print(f"Warning: Could not fetch full data via SQL, using cached data: {e}")
                import traceback
                traceback.print_exc()
                # Fall back to cached data
        
        # Generate Excel for single table
        excel_generator = ExcelReportGenerator()
        excel_bytes = excel_generator.generate_single_table_export(
            headers=export_headers,
            rows=export_rows,
            title=request.title,
            description=request.description
        )
        
        # Clean filename - remove "Top X" patterns
        clean_title = request.title or "Table"
        import re
        clean_title = re.sub(r'top\s*\d+\s*', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'first\s*\d+\s*', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'bottom\s*\d+\s*', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'^\d+\s+', '', clean_title)
        clean_title = clean_title.strip().replace(' ', '_')
        clean_title = re.sub(r'[^\w\-]', '', clean_title)
        
        if not clean_title:
            clean_title = "Table"
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{clean_title}_{timestamp}.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    
    except Exception as e:
        print(f"Error exporting table to Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export table: {str(e)}")
