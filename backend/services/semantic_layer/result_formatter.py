"""
Result Formatter - Formats SQL results for LLM and frontend.
Converts DataFrames to structured context for AI analysis.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Currency columns that should be formatted with ₹
CURRENCY_COLUMNS = [
    'outstanding', 'balance', 'amount', 'principal', 'provision',
    'total_outstanding', 'total_balance', 'total_exposure', 'total_amount',
    'ledger_balance', 'i_outstanding_principal', 'i_sanctioned_limit',
    'd_total_provision', 'i_overdue_amt', 'exposure', 'net_position',
    'total_loan_outstanding', 'total_deposit_balance',
]

# Percentage columns
PERCENTAGE_COLUMNS = [
    'ratio', 'percent', 'percentage', 'rate', 'pct',
]


class ResultFormatter:
    """Formats SQL query results for LLM consumption and frontend display."""
    
    def __init__(
        self,
        max_rows: int = 100,
        max_context_chars: int = 8000,
        currency_symbol: str = '₹',
    ):
        """
        Initialize result formatter.
        
        Args:
            max_rows: Maximum rows to include in context
            max_context_chars: Maximum characters for LLM context
            currency_symbol: Currency symbol for formatting
        """
        self.max_rows = max_rows
        self.max_context_chars = max_context_chars
        self.currency_symbol = currency_symbol
    
    def format_for_llm(
        self,
        df: pd.DataFrame,
        sql: str,
        question: str = None,
    ) -> Dict[str, Any]:
        """
        Format DataFrame results for LLM context.
        
        Args:
            df: Query results DataFrame
            sql: SQL query that was executed
            question: Original natural language question
            
        Returns:
            Dictionary with formatted context for LLM
        """
        if df is None or df.empty:
            return {
                'source': 'semantic_layer',
                'sql': sql,
                'question': question,
                'has_data': False,
                'row_count': 0,
                'columns': [],
                'data': [],
                'summary': 'No data returned from query.',
            }
        
        # Use original count from DataFrame attrs if available (set by vanna_client before truncation)
        # Otherwise fall back to current length
        original_count = df.attrs.get('original_count', len(df))
        
        # Truncate if needed for LLM context
        if len(df) > self.max_rows:
            df = df.head(self.max_rows)
            truncated = True
        else:
            # Also check if data was already truncated upstream
            truncated = original_count > len(df)
        
        # Convert to records
        records = self._dataframe_to_records(df)
        
        # Generate summary statistics
        summary = self._generate_summary(df, original_count, truncated)
        
        # Detect suggested visualization
        chart_suggestion = self._suggest_chart_type(df)
        
        return {
            'source': 'semantic_layer',
            'sql': sql,
            'question': question,
            'has_data': True,
            'row_count': original_count,
            'displayed_rows': len(df),
            'truncated': truncated,
            'columns': list(df.columns),
            'column_types': {col: str(df[col].dtype) for col in df.columns},
            'data': records,
            'summary': summary,
            'chart_suggestion': chart_suggestion,
        }
    
    def _dataframe_to_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert DataFrame to list of dictionaries with proper type handling."""
        records = []
        
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                record[col] = self._convert_value(value, col)
            records.append(record)
        
        return records
    
    def _convert_value(self, value: Any, column_name: str = '') -> Any:
        """Convert a value to JSON-serializable format."""
        if pd.isna(value):
            return None
        
        if isinstance(value, Decimal):
            value = float(value)
        
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        
        if isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
            return value.isoformat()
        
        if hasattr(value, 'item'):  # numpy types
            value = value.item()
        
        # Format currency columns
        col_lower = column_name.lower()
        if isinstance(value, (int, float)):
            if any(curr in col_lower for curr in CURRENCY_COLUMNS):
                # Keep as number for charts, but note it's currency
                pass
        
        return value
    
    def _generate_summary(
        self,
        df: pd.DataFrame,
        original_count: int,
        truncated: bool,
    ) -> str:
        """Generate a text summary of the results."""
        parts = []
        
        parts.append(f"Query returned {original_count} rows")
        
        if truncated:
            parts.append(f"(showing first {len(df)})")
        
        parts.append(f"with {len(df.columns)} columns: {', '.join(df.columns[:5])}")
        
        if len(df.columns) > 5:
            parts.append(f"and {len(df.columns) - 5} more")
        
        # Add numeric column summaries
        numeric_cols = df.select_dtypes(include=['number']).columns[:3]
        for col in numeric_cols:
            col_lower = col.lower()
            is_currency = any(curr in col_lower for curr in CURRENCY_COLUMNS)
            
            total = df[col].sum()
            if is_currency:
                parts.append(f"| Total {col}: {self.currency_symbol}{total:,.2f}")
            else:
                parts.append(f"| {col} range: {df[col].min():.2f} - {df[col].max():.2f}")
        
        return ' '.join(parts)
    
    def _suggest_chart_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Suggest appropriate chart type based on data shape."""
        if df.empty:
            return {'type': None, 'reason': 'No data'}
        
        num_rows = len(df)
        num_cols = len(df.columns)
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        string_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        # Single value - no chart needed
        if num_rows == 1 and num_cols == 1:
            return {'type': None, 'reason': 'Single value result'}
        
        # Few categories with numeric values - bar or pie chart
        if num_rows <= 10 and len(string_cols) >= 1 and len(numeric_cols) >= 1:
            if num_rows <= 5:
                return {
                    'type': 'pie',
                    'reason': 'Few categories with numeric values',
                    'category_column': string_cols[0],
                    'value_column': numeric_cols[0],
                }
            else:
                return {
                    'type': 'bar',
                    'reason': 'Categories with numeric values',
                    'category_column': string_cols[0],
                    'value_column': numeric_cols[0],
                }
        
        # Many rows with categories - horizontal bar
        if 10 < num_rows <= 20 and len(string_cols) >= 1 and len(numeric_cols) >= 1:
            return {
                'type': 'bar',
                'reason': 'Multiple categories',
                'category_column': string_cols[0],
                'value_column': numeric_cols[0],
            }
        
        # Time series data
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if date_cols and len(numeric_cols) >= 1:
            return {
                'type': 'line',
                'reason': 'Time series data',
                'x_column': date_cols[0],
                'y_column': numeric_cols[0],
            }
        
        # Default to table for complex data
        return {
            'type': 'table',
            'reason': 'Complex data structure',
        }
    
    def format_for_response(
        self,
        df: pd.DataFrame,
        sql: str,
        question: str = None,
    ) -> Dict[str, Any]:
        """
        Format results for direct API response.
        
        Args:
            df: Query results DataFrame
            sql: SQL query executed
            question: Original question
            
        Returns:
            Dictionary formatted for frontend consumption
        """
        llm_context = self.format_for_llm(df, sql, question)
        
        # Build table structure for frontend
        if df is not None and not df.empty:
            table = {
                'title': 'Query Results',
                'description': f'Results for: {question}' if question else 'SQL Query Results',
                'headers': list(df.columns),
                'rows': [
                    [self._format_cell_value(row[col], col) for col in df.columns]
                    for _, row in df.head(self.max_rows).iterrows()
                ],
            }
        else:
            table = None
        
        # Build chart if suggested
        chart = None
        suggestion = llm_context.get('chart_suggestion', {})
        if suggestion.get('type') in ['bar', 'pie', 'line'] and df is not None:
            chart = self._build_chart_data(df, suggestion)
        
        return {
            'sql': sql,
            'question': question,
            'table': table,
            'chart': chart,
            'summary': llm_context.get('summary'),
            'row_count': llm_context.get('row_count'),
            'truncated': llm_context.get('truncated', False),
        }
    
    def _format_cell_value(self, value: Any, column_name: str) -> str:
        """Format a cell value for display."""
        if pd.isna(value):
            return '-'
        
        col_lower = column_name.lower()
        
        # Currency formatting
        if isinstance(value, (int, float)):
            if any(curr in col_lower for curr in CURRENCY_COLUMNS):
                return f"{self.currency_symbol}{value:,.2f}"
            if any(pct in col_lower for pct in PERCENTAGE_COLUMNS):
                return f"{value:.2f}%"
            if isinstance(value, float):
                return f"{value:,.2f}"
            return f"{value:,}"
        
        return str(value)
    
    def _build_chart_data(
        self,
        df: pd.DataFrame,
        suggestion: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Build chart data structure from DataFrame."""
        chart_type = suggestion.get('type')
        
        if chart_type in ['bar', 'pie']:
            cat_col = suggestion.get('category_column')
            val_col = suggestion.get('value_column')
            
            if cat_col and val_col and cat_col in df.columns and val_col in df.columns:
                data = [
                    {'name': str(row[cat_col]), 'value': float(row[val_col]) if pd.notna(row[val_col]) else 0}
                    for _, row in df.head(20).iterrows()
                ]
                
                return {
                    'type': chart_type if chart_type != 'pie' else 'donut',
                    'title': f'{val_col} by {cat_col}',
                    'description': suggestion.get('reason', ''),
                    'data': data,
                }
        
        elif chart_type == 'line':
            x_col = suggestion.get('x_column')
            y_col = suggestion.get('y_column')
            
            if x_col and y_col and x_col in df.columns and y_col in df.columns:
                data = [
                    {'name': str(row[x_col]), 'value': float(row[y_col]) if pd.notna(row[y_col]) else 0}
                    for _, row in df.iterrows()
                ]
                
                return {
                    'type': 'line',
                    'title': f'{y_col} over {x_col}',
                    'description': suggestion.get('reason', ''),
                    'data': data,
                }
        
        return None


# Singleton instance
result_formatter = ResultFormatter()
