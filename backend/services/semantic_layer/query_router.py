"""
Query Router - Routes queries to Vanna or existing analytics.
Classifies questions to determine the best processing path.
"""
import re
import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Classification of query types."""
    SEMANTIC = "semantic"      # Use Vanna for ad-hoc SQL generation
    RULE_BASED = "rule_based"  # Use existing analytics (KPIs, ratios)
    HYBRID = "hybrid"          # Use both and merge results


# Patterns that should use EXISTING analytics (rule-based)
# These are pre-computed KPIs and ratios that existing code handles well
RULE_BASED_PATTERNS = [
    # KPI queries
    r'gross\s*npa\s*ratio',
    r'provision\s*coverage\s*ratio',
    r'pcr\s*ratio',
    r'casa\s*ratio',
    r'psl\s*ratio',
    r'priority\s*sector.*ratio',
    r'credit.?deposit\s*ratio',
    r'cd\s*ratio',
    
    # Portfolio summary queries
    r'portfolio\s*(summary|overview|snapshot)',
    r'overall\s*(summary|overview|snapshot)',
    r'key\s*(ratios|metrics|kpis|indicators)',
    r'all\s*ratios',
    r'dashboard\s*(summary|data|overview)',
    
    # Standard breakdowns already computed
    r'asset\s*class\s*(breakdown|distribution|split)',
    r'dpd\s*bucket\s*(breakdown|distribution|analysis)',
    r'product\s*(group|type)\s*(breakdown|distribution)',
]

# Patterns that should use VANNA (semantic SQL generation)
# These are ad-hoc, exploratory queries that need dynamic SQL
SEMANTIC_PATTERNS = [
    # Explicit list/show requests
    r'^show\s+(me\s+)?(all|top|bottom|the)',
    r'^list\s+(all|top|bottom|the)',
    r'^find\s+(all|the|customers?|accounts?|loans?|deposits?)',
    r'^get\s+(all|the|me)',
    
    # Specific entity queries
    r'which\s+(customers?|accounts?|branches?|products?)',
    r'who\s+(has|have|are|is)',
    r'what\s+(are|is)\s+the\s+(names?|details?|accounts?)',
    
    # Filter/condition queries
    r'where\s+',
    r'filter\s*(by|for|where)',
    r'with\s+(dpd|npa|balance|outstanding)',
    r'greater\s*than',
    r'less\s*than',
    r'more\s*than',
    r'between\s+\d+',
    r'above\s+\d+',
    r'below\s+\d+',
    
    # Comparison queries
    r'compare\s+',
    r'difference\s+between',
    r'vs\.?\s+',
    
    # Aggregation with grouping
    r'group\s*by',
    r'grouped\s+by',
    r'by\s+(branch|product|gender|caste|religion|occupation)',
    r'per\s+(branch|product|customer)',
    
    # Specific data requests
    r'(top|bottom)\s+\d+',
    r'highest\s+\d*',
    r'lowest\s+\d*',
    r'largest\s+\d*',
    r'smallest\s+\d*',
    
    # Customer-specific queries
    r'customer\s+(id|name|number)\s*[=:]\s*',
    r'account\s+(id|number)\s*[=:]\s*',
    r'branch\s+(code|name)\s*[=:]\s*',
    
    # Time-based queries
    r'maturing\s+(in|within)',
    r'due\s+(in|within)',
    r'opened\s+(in|before|after)',
    r'(last|past|next)\s+\d+\s+(days?|months?|years?)',
    
    # Complex analytical queries
    r'concentration',
    r'exposure\s+to',
    r'cross.?sell',
    r'relationship\s+(analysis|between)',
]

# Patterns that benefit from HYBRID approach
# These need both KPIs and detailed data
HYBRID_PATTERNS = [
    r'explain.*ratio',
    r'why\s+is\s+(the\s+)?(npa|casa|psl)',
    r'breakdown.*and.*ratio',
    r'details?\s+(of|about|on)\s+(npa|psl|casa)',
    r'drill\s*down',
]


class QueryRouter:
    """Routes natural language queries to appropriate processing path."""
    
    def __init__(self):
        """Initialize query router with compiled patterns."""
        self.rule_based_patterns = [
            re.compile(p, re.IGNORECASE) for p in RULE_BASED_PATTERNS
        ]
        self.semantic_patterns = [
            re.compile(p, re.IGNORECASE) for p in SEMANTIC_PATTERNS
        ]
        self.hybrid_patterns = [
            re.compile(p, re.IGNORECASE) for p in HYBRID_PATTERNS
        ]
    
    def classify(self, question: str) -> QueryType:
        """
        Classify a question to determine processing path.
        
        Args:
            question: Natural language question
            
        Returns:
            QueryType enum value
        """
        if not question or not question.strip():
            return QueryType.RULE_BASED
        
        question = question.strip()
        
        # Check hybrid patterns first (most specific)
        for pattern in self.hybrid_patterns:
            if pattern.search(question):
                logger.debug(f"Query classified as HYBRID: {question[:50]}")
                return QueryType.HYBRID
        
        # Check rule-based patterns
        rule_based_score = sum(
            1 for pattern in self.rule_based_patterns
            if pattern.search(question)
        )
        
        # Check semantic patterns
        semantic_score = sum(
            1 for pattern in self.semantic_patterns
            if pattern.search(question)
        )
        
        logger.debug(
            f"Query scores - rule_based: {rule_based_score}, semantic: {semantic_score}"
        )
        
        # Decision logic
        if rule_based_score > 0 and semantic_score == 0:
            return QueryType.RULE_BASED
        
        if semantic_score > 0 and rule_based_score == 0:
            return QueryType.SEMANTIC
        
        if semantic_score > rule_based_score:
            return QueryType.SEMANTIC
        
        if rule_based_score > semantic_score:
            return QueryType.RULE_BASED
        
        # Default to rule-based for safety (existing tested code)
        return QueryType.RULE_BASED
    
    def should_use_vanna(self, question: str) -> bool:
        """
        Quick check if Vanna should be used.
        
        Args:
            question: Natural language question
            
        Returns:
            True if Vanna should handle the query
        """
        query_type = self.classify(question)
        return query_type in (QueryType.SEMANTIC, QueryType.HYBRID)
    
    def get_routing_info(self, question: str) -> Dict[str, Any]:
        """
        Get detailed routing information for a question.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with routing details
        """
        query_type = self.classify(question)
        
        # Find matching patterns for explanation
        matched_rule_based = [
            p.pattern for p in self.rule_based_patterns
            if p.search(question)
        ]
        matched_semantic = [
            p.pattern for p in self.semantic_patterns
            if p.search(question)
        ]
        matched_hybrid = [
            p.pattern for p in self.hybrid_patterns
            if p.search(question)
        ]
        
        return {
            'question': question,
            'query_type': query_type.value,
            'use_vanna': query_type in (QueryType.SEMANTIC, QueryType.HYBRID),
            'use_existing_analytics': query_type in (QueryType.RULE_BASED, QueryType.HYBRID),
            'matched_patterns': {
                'rule_based': matched_rule_based[:3],  # Limit for readability
                'semantic': matched_semantic[:3],
                'hybrid': matched_hybrid[:3],
            },
            'confidence': self._calculate_confidence(
                len(matched_rule_based),
                len(matched_semantic),
                len(matched_hybrid),
            ),
        }
    
    def _calculate_confidence(
        self,
        rule_count: int,
        semantic_count: int,
        hybrid_count: int,
    ) -> str:
        """Calculate confidence level in routing decision."""
        total = rule_count + semantic_count + hybrid_count
        
        if total == 0:
            return 'low'
        
        if hybrid_count > 0:
            return 'high'
        
        max_count = max(rule_count, semantic_count)
        
        if max_count >= 2 and max_count > (total - max_count):
            return 'high'
        
        if max_count >= 1:
            return 'medium'
        
        return 'low'


# Singleton instance
query_router = QueryRouter()
