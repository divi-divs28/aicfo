"""
Semantic Layer Logger.
Dedicated logging for Vanna semantic layer flow tracing.
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Semantic layer log file
SEMANTIC_LOG_FILE = LOGS_DIR / 'semantic_layer.log'

# Create dedicated logger
semantic_logger = logging.getLogger('semantic_layer')
semantic_logger.setLevel(logging.DEBUG)

# Prevent propagation to root logger
semantic_logger.propagate = False

# File handler with detailed formatting
file_handler = logging.FileHandler(SEMANTIC_LOG_FILE, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# Console handler for important messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s | SEMANTIC | %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)

# Add handlers
if not semantic_logger.handlers:
    semantic_logger.addHandler(file_handler)
    semantic_logger.addHandler(console_handler)


def truncate_str(s: str, max_len: int = 500) -> str:
    """Truncate string for logging."""
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"... [truncated, total {len(s)} chars]"


def format_dict(d: Dict[str, Any], max_depth: int = 2) -> str:
    """Format dictionary for logging."""
    try:
        return json.dumps(d, indent=2, default=str)[:2000]
    except Exception:
        return str(d)[:2000]


class SemanticFlowLogger:
    """
    Logger for tracing semantic layer query flow.
    Provides structured logging for debugging and monitoring.
    """
    
    def __init__(self):
        self.logger = semantic_logger
        self._request_counter = 0
    
    def _get_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_counter += 1
        return f"REQ-{datetime.now().strftime('%H%M%S')}-{self._request_counter:04d}"
    
    def log_separator(self, char: str = "=", length: int = 80):
        """Log a separator line."""
        self.logger.info(char * length)
    
    def log_query_start(self, question: str) -> str:
        """Log the start of a new query. Returns request ID."""
        request_id = self._get_request_id()
        self.log_separator()
        self.logger.info(f"[{request_id}] NEW QUERY RECEIVED")
        self.log_separator()
        self.logger.info(f"[{request_id}] USER QUESTION: {question}")
        self.logger.info(f"[{request_id}] TIMESTAMP: {datetime.now().isoformat()}")
        return request_id
    
    def log_routing_decision(self, request_id: str, routing_info: Dict[str, Any]):
        """Log query routing decision - minimal logging."""
        # Routing logs removed as per user request
        pass
    
    def log_vanna_sql_generation_start(self, request_id: str, question: str):
        """Log start of Vanna SQL generation."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] VANNA SQL GENERATION")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Generating SQL for: {truncate_str(question, 200)}")
    
    def log_vanna_sql_generated(self, request_id: str, sql: str, success: bool, error: Optional[str] = None):
        """Log generated SQL."""
        if success:
            self.logger.info(f"[{request_id}] SQL Generation: SUCCESS")
            self.logger.info(f"[{request_id}] Generated SQL:")
            for line in sql.strip().split('\n'):
                self.logger.info(f"[{request_id}]   {line}")
        else:
            self.logger.warning(f"[{request_id}] SQL Generation: FAILED")
            self.logger.warning(f"[{request_id}] Error: {error}")
    
    def log_sql_validation(self, request_id: str, is_valid: bool, sanitized_sql: Optional[str] = None, error: Optional[str] = None):
        """Log SQL validation results."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] SQL VALIDATION")
        self.log_separator("-", 60)
        
        if is_valid:
            self.logger.info(f"[{request_id}] Validation: PASSED")
            if sanitized_sql:
                self.logger.info(f"[{request_id}] Sanitized SQL:")
                for line in sanitized_sql.strip().split('\n'):
                    self.logger.info(f"[{request_id}]   {line}")
        else:
            self.logger.warning(f"[{request_id}] Validation: FAILED")
            self.logger.warning(f"[{request_id}] Reason: {error}")
    
    def log_sql_execution_start(self, request_id: str, sql: str):
        """Log SQL execution start."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] SQL EXECUTION")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Executing SQL against database...")
    
    def log_sql_execution_result(self, request_id: str, success: bool, row_count: int = 0, 
                                  columns: list = None, sample_data: list = None, error: Optional[str] = None):
        """Log SQL execution results."""
        if success:
            self.logger.info(f"[{request_id}] Execution: SUCCESS")
            self.logger.info(f"[{request_id}] Rows Returned: {row_count}")
            if columns:
                self.logger.info(f"[{request_id}] Columns: {columns}")
            if sample_data:
                self.logger.debug(f"[{request_id}] Sample Data (first 3 rows):")
                for i, row in enumerate(sample_data[:3]):
                    self.logger.debug(f"[{request_id}]   Row {i+1}: {truncate_str(str(row), 300)}")
        else:
            self.logger.error(f"[{request_id}] Execution: FAILED")
            self.logger.error(f"[{request_id}] Error: {error}")
    
    def log_result_formatting(self, request_id: str, formatted_data: Dict[str, Any]):
        """Log result formatting."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] RESULT FORMATTING")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Data Source: {formatted_data.get('source', 'unknown')}")
        self.logger.info(f"[{request_id}] Row Count: {formatted_data.get('row_count', 0)}")
        self.logger.info(f"[{request_id}] Truncated: {formatted_data.get('truncated', False)}")
        self.logger.info(f"[{request_id}] Summary: {truncate_str(formatted_data.get('summary', ''), 300)}")
        
        chart_suggestion = formatted_data.get('chart_suggestion', {})
        if chart_suggestion:
            self.logger.info(f"[{request_id}] Chart Suggestion: {chart_suggestion.get('type', 'none')} - {chart_suggestion.get('reason', '')}")
    
    def log_rule_based_path(self, request_id: str):
        """Log when using rule-based analytics path."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] RULE-BASED ANALYTICS PATH")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Using existing aggregation logic (not Vanna)")
    
    def log_llm_prompt_start(self, request_id: str, prompt_type: str):
        """Log LLM prompt building start."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] LLM PROMPT BUILDING")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Prompt Type: {prompt_type}")
    
    def log_llm_prompt(self, request_id: str, prompt: str):
        """Log the full LLM prompt."""
        self.logger.debug(f"[{request_id}] Full Prompt ({len(prompt)} chars):")
        # Log first and last parts of prompt
        if len(prompt) > 2000:
            self.logger.debug(f"[{request_id}] Prompt Start:\n{prompt[:1000]}")
            self.logger.debug(f"[{request_id}] ... [middle truncated] ...")
            self.logger.debug(f"[{request_id}] Prompt End:\n{prompt[-500:]}")
        else:
            for line in prompt.split('\n')[:50]:
                self.logger.debug(f"[{request_id}]   {line}")
    
    def log_llm_request(self, request_id: str, model: str, temperature: float, max_tokens: int):
        """Log LLM API request."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] LLM API REQUEST")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Model: {model}")
        self.logger.info(f"[{request_id}] Temperature: {temperature}")
        self.logger.info(f"[{request_id}] Max Tokens: {max_tokens}")
        self.logger.info(f"[{request_id}] Sending request to OpenAI...")
    
    def log_llm_response(self, request_id: str, response: str, tokens_used: Optional[int] = None):
        """Log LLM response."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] LLM RESPONSE RECEIVED")
        self.log_separator("-", 60)
        if tokens_used:
            self.logger.info(f"[{request_id}] Tokens Used: {tokens_used}")
        self.logger.info(f"[{request_id}] Response Length: {len(response)} chars")
        self.logger.debug(f"[{request_id}] Raw Response:")
        self.logger.debug(f"[{request_id}] {truncate_str(response, 1500)}")
    
    def log_response_parsing(self, request_id: str, parsed: Dict[str, Any]):
        """Log response parsing."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] RESPONSE PARSING")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Response Text: {truncate_str(parsed.get('response', ''), 300)}")
        self.logger.info(f"[{request_id}] Charts Count: {len(parsed.get('charts', []))}")
        self.logger.info(f"[{request_id}] Tables Count: {len(parsed.get('tables', []))}")
        self.logger.info(f"[{request_id}] Summary Points: {len(parsed.get('summary_points', []))}")
        
        # Log chart details
        for i, chart in enumerate(parsed.get('charts', [])[:3]):
            self.logger.debug(f"[{request_id}] Chart {i+1}: type={chart.get('type')}, title={chart.get('title')}, data_points={len(chart.get('data', []))}")
        
        # Log table details
        for i, table in enumerate(parsed.get('tables', [])[:3]):
            self.logger.debug(f"[{request_id}] Table {i+1}: title={table.get('title')}, rows={len(table.get('rows', []))}")
    
    def log_query_complete(self, request_id: str, success: bool, duration_ms: Optional[float] = None):
        """Log query completion."""
        self.log_separator("=")
        if success:
            self.logger.info(f"[{request_id}] QUERY COMPLETED SUCCESSFULLY")
        else:
            self.logger.warning(f"[{request_id}] QUERY COMPLETED WITH ERRORS")
        if duration_ms:
            self.logger.info(f"[{request_id}] Total Duration: {duration_ms:.2f}ms")
        self.log_separator("=")
        self.logger.info("")  # Empty line for readability
    
    def log_error(self, request_id: str, stage: str, error: str, traceback: Optional[str] = None):
        """Log error at any stage."""
        self.logger.error(f"[{request_id}] ERROR at {stage}: {error}")
        if traceback:
            self.logger.debug(f"[{request_id}] Traceback:\n{traceback}")
    
    def log_fallback(self, request_id: str, reason: str):
        """Log fallback to rule-based path."""
        self.logger.warning(f"[{request_id}] FALLBACK: {reason}")
        self.logger.info(f"[{request_id}] Switching to rule-based analytics path")
    
    def log_query_refinement(self, request_id: str, original_query: str, refined_query: str, history: list):
        """Log query refinement step."""
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] QUERY REFINEMENT")
        self.log_separator("-", 60)
        self.logger.info(f"[{request_id}] Original Query: {truncate_str(original_query, 200)}")
        self.logger.info(f"[{request_id}] Conversation History ({len(history)} messages):")
        for i, msg in enumerate(history):
            self.logger.info(f"[{request_id}]   {i+1}. {truncate_str(msg, 150)}")
        self.logger.info(f"[{request_id}] Refined Query: {truncate_str(refined_query, 200)}")
        if original_query != refined_query:
            self.logger.info(f"[{request_id}] Query was modified by refinement")
        else:
            self.logger.info(f"[{request_id}] Query unchanged (no context dependency)")


# Singleton instance
flow_logger = SemanticFlowLogger()
