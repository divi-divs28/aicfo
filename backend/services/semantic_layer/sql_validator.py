"""
SQL Validator - Safety checks for generated SQL.
Ensures only safe, read-only queries are executed.
"""
import re
import logging
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)

# Forbidden SQL keywords that could modify data
FORBIDDEN_KEYWORDS = [
    'DELETE',
    'UPDATE',
    'INSERT',
    'DROP',
    'ALTER',
    'TRUNCATE',
    'CREATE',
    'GRANT',
    'REVOKE',
    'EXECUTE',
    'CALL',
    'MERGE',
    'REPLACE',
    'LOAD',
    'RENAME',
    'SET',  # Except in SELECT context
]

# Allowed tables for queries
ALLOWED_TABLES = [
    'accounts',
    'company',
    'industries',
    'users'
]

# Maximum allowed result limit
MAX_RESULT_LIMIT = 10000
DEFAULT_RESULT_LIMIT = 1000


class SQLValidator:
    """Validates and sanitizes SQL queries for safety."""
    
    def __init__(
        self,
        allowed_tables: List[str] = None,
        forbidden_keywords: List[str] = None,
        max_limit: int = MAX_RESULT_LIMIT,
        default_limit: int = DEFAULT_RESULT_LIMIT,
    ):
        """
        Initialize SQL validator.
        
        Args:
            allowed_tables: List of allowed table names
            forbidden_keywords: List of forbidden SQL keywords
            max_limit: Maximum allowed LIMIT value
            default_limit: Default LIMIT to add if none specified
        """
        self.allowed_tables = allowed_tables or ALLOWED_TABLES
        self.forbidden_keywords = forbidden_keywords or FORBIDDEN_KEYWORDS
        self.max_limit = max_limit
        self.default_limit = default_limit
    
    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"
        
        sql_upper = sql.upper()
        
        # Check for forbidden keywords
        forbidden_check = self._check_forbidden_keywords(sql_upper)
        if forbidden_check:
            return False, forbidden_check
        
        # Check for allowed tables only
        tables_check = self._check_allowed_tables(sql_upper)
        if tables_check:
            return False, tables_check
        
        # Check for SQL injection patterns
        injection_check = self._check_sql_injection(sql)
        if injection_check:
            return False, injection_check
        
        # Must be a SELECT query
        if not self._is_select_query(sql_upper):
            return False, "Only SELECT queries are allowed"
        
        return True, None
    
    def _check_forbidden_keywords(self, sql_upper: str) -> Optional[str]:
        """Check for forbidden SQL keywords."""
        for keyword in self.forbidden_keywords:
            # Use word boundary to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                # Special case: SET is allowed in SELECT context (e.g., result sets)
                if keyword == 'SET':
                    # Check if it's actually a SET statement (not in SELECT)
                    if sql_upper.strip().startswith('SET'):
                        return f"Forbidden keyword detected: {keyword}"
                else:
                    return f"Forbidden keyword detected: {keyword}"
        return None
    
    def _check_allowed_tables(self, sql_upper: str) -> Optional[str]:
        """Check that only allowed tables are referenced."""
        # Extract table names from FROM and JOIN clauses
        from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        tables_found = set()
        
        for match in re.finditer(from_pattern, sql_upper):
            tables_found.add(match.group(1).lower())
        
        for match in re.finditer(join_pattern, sql_upper):
            tables_found.add(match.group(1).lower())
        
        allowed_lower = [t.lower() for t in self.allowed_tables]
        
        for table in tables_found:
            if table not in allowed_lower:
                return f"Table not allowed: {table}. Allowed tables: {', '.join(self.allowed_tables)}"
        
        return None
    
    def _check_sql_injection(self, sql: str) -> Optional[str]:
        """Check for common SQL injection patterns."""
        dangerous_patterns = [
            r';\s*--',           # Statement termination with comment
            r';\s*SELECT',       # Multiple statements
            r';\s*DROP',         # Multiple statements with DROP
            r'UNION\s+ALL\s+SELECT.*FROM\s+information_schema',  # Schema enumeration
            r'INTO\s+OUTFILE',   # File writes
            r'INTO\s+DUMPFILE',  # File writes
            r'LOAD_FILE',        # File reads
            r'@@version',        # Version disclosure
            r'BENCHMARK\s*\(',   # Time-based attacks
            r'SLEEP\s*\(',       # Time-based attacks
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return f"Potentially dangerous SQL pattern detected"
        
        return None
    
    def _is_select_query(self, sql_upper: str) -> bool:
        """Check if query is a SELECT statement."""
        # Remove leading whitespace and comments
        cleaned = re.sub(r'/\*.*?\*/', '', sql_upper)  # Remove block comments
        cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)  # Remove line comments
        cleaned = cleaned.strip()
        
        return cleaned.startswith('SELECT') or cleaned.startswith('WITH')
    
    def sanitize(self, sql: str) -> str:
        """
        Sanitize SQL query by adding safety measures.
        
        Args:
            sql: SQL query to sanitize
            
        Returns:
            Sanitized SQL query
        """
        sql = sql.strip()
        
        # Remove any trailing semicolons (prevent statement chaining)
        sql = sql.rstrip(';')
        
        # Add or adjust LIMIT
        # sql = self._ensure_limit(sql)
        
        return sql
    
    def _ensure_limit(self, sql: str) -> str:
        """Ensure query has a reasonable LIMIT clause."""
        sql_upper = sql.upper()
        
        # Check if LIMIT already exists
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql_upper)
        
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit > self.max_limit:
                # Replace with max limit
                sql = re.sub(
                    r'\bLIMIT\s+\d+',
                    f'LIMIT {self.max_limit}',
                    sql,
                    flags=re.IGNORECASE
                )
                logger.warning(f"Reduced LIMIT from {current_limit} to {self.max_limit}")
        else:
            # Add default limit
            # Handle ORDER BY if present
            if 'ORDER BY' in sql_upper:
                # Find the end of ORDER BY clause
                order_match = re.search(r'\bORDER\s+BY\s+.+$', sql, re.IGNORECASE)
                if order_match:
                    sql = sql + f' LIMIT {self.default_limit}'
            else:
                sql = sql + f' LIMIT {self.default_limit}'
        
        return sql
    
    def validate_and_sanitize(self, sql: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and sanitize SQL in one step.
        
        Args:
            sql: SQL query to process
            
        Returns:
            Tuple of (is_valid, sanitized_sql, error_message)
        """
        is_valid, error = self.validate(sql)
        
        if not is_valid:
            return False, sql, error
        
        sanitized = self.sanitize(sql)
        return True, sanitized, None


# Singleton instance
sql_validator = SQLValidator()
