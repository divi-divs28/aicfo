"""
Semantic Layer Module.
Provides Vanna AI integration for natural language to SQL conversion.
"""

# Lazy imports to avoid circular dependencies
async def get_vanna_client(db_session=None):
    from .vanna_client import get_vanna_client as _get_vanna_client
    return await _get_vanna_client(db_session)

async def is_vanna_ready(db_session=None):
    from .vanna_client import is_vanna_ready as _is_vanna_ready
    return await _is_vanna_ready(db_session)

async def initialize_vanna(db_session=None):
    from .vanna_client import initialize_vanna as _initialize_vanna
    return await _initialize_vanna(db_session)

# Direct imports for classes/singletons
from .sql_validator import sql_validator, SQLValidator
from .result_formatter import result_formatter, ResultFormatter
from .query_router import query_router, QueryRouter, QueryType
from .flow_logger import flow_logger, SemanticFlowLogger

__all__ = [
    # Vanna client
    'get_vanna_client',
    'is_vanna_ready',
    'initialize_vanna',
    # SQL validation
    'sql_validator',
    'SQLValidator',
    # Result formatting
    'result_formatter',
    'ResultFormatter',
    # Query routing
    'query_router',
    'QueryRouter',
    'QueryType',
    # Flow logging
    'flow_logger',
    'SemanticFlowLogger',
]
