"""
LLM Response parsing and normalization utilities.
Handles various LLM output formats and converts them to standard structures.
"""
import json
import logging
import traceback
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from pathlib import Path

from schemas.chat import ChartData, TableData, ChatResponse, KPICard

ROOT_DIR = Path(__file__).parent.parent


def clean_llm_response(content: str) -> str:
    """Remove markdown code blocks, comments, and clean up the response."""
    import re
    cleaned_content = content.strip()
    
    # Check if response is in Markdown table format instead of JSON
    if cleaned_content.startswith('###') or '|' in cleaned_content[:100]:
        # LLM returned Markdown instead of JSON - convert it
        return convert_markdown_to_json(cleaned_content)
    
    if cleaned_content.startswith('```json'):
        cleaned_content = cleaned_content[7:]
    elif cleaned_content.startswith('```'):
        cleaned_content = cleaned_content[3:]
    if cleaned_content.endswith('```'):
        cleaned_content = cleaned_content[:-3]
    
    # Remove JavaScript-style comments that LLM might add (// comments)
    # Only remove comments that appear after a value (not inside strings)
    cleaned_content = re.sub(r',?\s*//[^\n]*', '', cleaned_content)
    
    return cleaned_content.strip()


def convert_markdown_to_json(markdown_content: str) -> str:
    """Convert Markdown table response to JSON format."""
    import re
    
    lines = markdown_content.strip().split('\n')
    
    # Extract title/response from ### headers
    response_text = ""
    table_started = False
    headers = []
    rows = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('###'):
            # Extract response text from header
            response_text = line.replace('###', '').strip()
        elif line.startswith('|') and not table_started:
            # First table row - headers
            headers = [h.strip() for h in line.split('|')[1:-1]]
            table_started = True
        elif line.startswith('|') and table_started and not line.startswith('|---'):
            # Data row
            row_data = [cell.strip() for cell in line.split('|')[1:-1]]
            rows.append(row_data)
        elif not line.startswith('|') and line and not line.startswith('-'):
            # Additional response text
            if response_text:
                response_text += " " + line
            else:
                response_text = line
    
    # Build JSON response
    json_response = {
        "response": response_text if response_text else "Here are the results from your query.",
        "tables": [],
        "charts": [],
        "summary_points": [],
        "kpi_cards": []
    }
    
    if headers and rows:
        json_response["tables"].append({
            "title": "Query Results",
            "description": "Results from your query",
            "headers": headers,
            "rows": rows
        })
        
        # Add summary point
        json_response["summary_points"].append(f"Found {len(rows)} records")
    
    return json.dumps(json_response)


def clean_text_for_output(text: str) -> str:
    """Clean text by removing invisible characters and normalizing."""
    if not text:
        return ''
    import unicodedata
    # Remove zero-width characters and other invisible chars
    cleaned = ''.join(
        char for char in text 
        if unicodedata.category(char) not in ('Cc', 'Cf') or char in ('\n', '\t', ' ')
    )
    # Replace multiple spaces with single space
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()


def normalize_summary_points(raw_summary_points: List[Any]) -> List[str]:
    """Normalize summary points from various formats to list of strings."""
    normalized = []
    for point in raw_summary_points:
        if isinstance(point, str):
            normalized.append(clean_text_for_output(point))
        elif isinstance(point, dict):
            if 'title' in point and 'value' in point:
                normalized.append(clean_text_for_output(f"{point['title']}: {point['value']}"))
            elif 'point' in point:
                normalized.append(clean_text_for_output(point['point']))
            elif 'text' in point:
                normalized.append(clean_text_for_output(point['text']))
            elif 'insight' in point:
                normalized.append(clean_text_for_output(point['insight']))
            else:
                normalized.append(clean_text_for_output(", ".join([f"{k}: {v}" for k, v in point.items()])))
        else:
            normalized.append(clean_text_for_output(str(point)))
    return normalized


def normalize_response_text(raw_response: Any) -> str:
    """Convert various response formats to readable string."""
    if isinstance(raw_response, dict):
        response_parts = []
        for key, value in raw_response.items():
            if isinstance(value, dict):
                response_parts.append(f"\n**{key.replace('_', ' ').title()}:**")
                for k, v in value.items():
                    response_parts.append(f"  - {k.replace('_', ' ').title()}: {v}")
            else:
                response_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        return clean_text_for_output("\n".join(response_parts))
    elif isinstance(raw_response, str):
        return clean_text_for_output(raw_response)
    else:
        return clean_text_for_output(str(raw_response))


def convert_raw_data_to_response(parsed_response: Dict[str, Any]) -> str:
    """Convert raw data without expected structure to readable format."""
    response_parts = []
    for key, value in parsed_response.items():
        if isinstance(value, list):
            if len(value) > 0 and isinstance(value[0], dict):
                response_parts.append(f"\n**{key.replace('_', ' ').title()}:**")
                for i, item in enumerate(value[:10], 1):
                    item_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
                    response_parts.append(f"  {i}. {item_str}")
            else:
                response_parts.append(f"**{key.replace('_', ' ').title()}:** {', '.join(map(str, value))}")
        elif isinstance(value, dict):
            response_parts.append(f"\n**{key.replace('_', ' ').title()}:**")
            for k, v in value.items():
                response_parts.append(f"  - {k.replace('_', ' ').title()}: {v}")
        else:
            if isinstance(value, (int, float)) and value > 1000:
                formatted_value = f"₹{value:,.2f}" if value > 10000 else f"{value:,}"
            else:
                formatted_value = value
            response_parts.append(f"**{key.replace('_', ' ').title()}:** {formatted_value}")
    return "\n".join(response_parts)


def parse_llm_response(content: str, chat_logger=None) -> ChatResponse:
    """
    Parse LLM response content and return a ChatResponse object.
    Handles various formats and error cases.
    """
    cleaned_content = clean_llm_response(content)
    
    try:
        parsed_response = json.loads(cleaned_content)
        
        # Check if LLM returned expected format or raw data
        has_expected_format = "response" in parsed_response or "summary_points" in parsed_response or "charts" in parsed_response or "kpi_cards" in parsed_response
        
        if not has_expected_format:
            # LLM returned raw data without expected structure
            if chat_logger:
                chat_logger.info("LLM returned non-standard format, converting to readable response")
            
            normalized_response = convert_raw_data_to_response(parsed_response)
            return ChatResponse(
                response=normalized_response,
                charts=[],
                tables=[],
                summary_points=[],
                kpi_cards=[]
            )
        
        # Standard format - extract fields
        raw_response = parsed_response.get("response", "")
        normalized_response = normalize_response_text(raw_response)
        
        # Normalize summary_points
        raw_summary_points = parsed_response.get("summary_points", [])
        normalized_summary_points = normalize_summary_points(raw_summary_points)
        
        # Parse charts and tables
        charts = []
        for chart in parsed_response.get("charts", []):
            try:
                charts.append(ChartData(**chart))
            except Exception as e:
                logging.warning(f"Failed to parse chart: {e}")
        
        tables = []
        for table in parsed_response.get("tables", []):
            try:
                # Get all rows
                all_rows = table.get("rows", [])
                total_rows = len(all_rows)
                
                # Limit display rows to 10, but always keep full data for export
                display_rows = all_rows[:10] if total_rows > 10 else all_rows
                is_truncated = total_rows > 10
                
                table_data = TableData(
                    headers=table.get("headers", []),
                    rows=display_rows,
                    title=table.get("title", ""),
                    description=table.get("description"),
                    full_data=all_rows,  # Always include all rows for Excel export
                    total_rows=total_rows,
                    is_truncated=is_truncated
                )
                tables.append(table_data)
            except Exception as e:
                logging.warning(f"Failed to parse table: {e}")
        
        # Parse KPI cards
        kpi_cards = []
        for kpi in parsed_response.get("kpi_cards", []):
            try:
                kpi_cards.append(KPICard(**kpi))
            except Exception as e:
                logging.warning(f"Failed to parse KPI card: {e}")
        
        # Ensure meaningful response
        placeholder_responses = ["analysis", "your analysis here", "your detailed analysis here", ""]
        if not normalized_response or normalized_response.strip().lower() in placeholder_responses:
            if normalized_summary_points:
                formatted_points = [f"• {p}" for p in normalized_summary_points[:5]]
                normalized_response = "Here are the key findings from the analysis:\n\n" + "\n".join(formatted_points)
            else:
                normalized_response = "Here is the analysis based on your query."
        
        return ChatResponse(
            response=normalized_response,
            charts=charts,
            tables=tables,
            summary_points=normalized_summary_points,
            kpi_cards=kpi_cards
        )
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
        logging.error(error_msg)
        logging.error(f"Raw content: {content[:500]}")
        
        # Log to error file with full exception
        log_error_to_file("JSON Parse Error", error_msg, content[:1000], exception=e)
        
        # Show polite generic message instead of raw error or content
        return ChatResponse(
            response="We couldn't process your request right now. Please try again or rephrase your question.",
            charts=[],
            tables=[],
            summary_points=[],
            kpi_cards=[]
        )


def log_error_to_file(
    error_type: str,
    error_msg: str,
    additional_info: str = "",
    exception: Optional[BaseException] = None,
):
    """Log error to dedicated error file, including real exception and full traceback."""
    try:
        with open(ROOT_DIR / 'chat_error.log', 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {datetime.utcnow().isoformat()}\n")
            f.write(f"ERROR TYPE: {error_type}\n")
            f.write(f"ERROR: {error_msg}\n")
            if additional_info:
                f.write(f"ADDITIONAL INFO: {additional_info}\n")
            if exception is not None:
                exc_type = type(exception).__name__
                exc_msg = str(exception).strip() or repr(exception)
                f.write(f"EXCEPTION TYPE: {exc_type}\n")
                f.write(f"EXCEPTION MESSAGE: {exc_msg}\n")
                f.write("TRACEBACK:\n")
                tb_lines = traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
                f.write("".join(tb_lines))
            f.write(f"{'='*80}\n")
    except Exception as e:
        logging.error(f"Failed to write to error log: {e}")
