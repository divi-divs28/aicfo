"""
Analytics Service.
Handles data aggregation, KPI calculations, and portfolio analysis.
Integrates with Vanna semantic layer for ad-hoc SQL queries.
"""
import logging
import time
import traceback
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from models.financial import LoanAccount, DepositAccount
from schemas.chat import ChatResponse
from services.llm_service import LLMService
from config import VANNA_ENABLED


class AnalyticsService:
    """Service for financial data analytics."""
    
    def __init__(self):
        self.llm_service = LLMService()
        self._vanna_initialized = False
        self._query_router = None
        self._sql_validator = None
        self._result_formatter = None
        self._flow_logger = None
    
    def _init_semantic_layer(self):
        """Lazily initialize semantic layer components."""
        if self._vanna_initialized:
            return
        
        if not VANNA_ENABLED:
            self._vanna_initialized = True
            return
        
        try:
            from services.semantic_layer import (
                query_router,
                sql_validator,
                result_formatter,
                is_vanna_ready,
            )
            from services.semantic_layer.flow_logger import flow_logger
            
            self._query_router = query_router
            self._sql_validator = sql_validator
            self._result_formatter = result_formatter
            self._is_vanna_ready = is_vanna_ready
            self._flow_logger = flow_logger
            self._vanna_initialized = True
            logging.info("Semantic layer components initialized")
        except Exception as e:
            logging.error(f"Failed to initialize semantic layer: {e}")
            self._vanna_initialized = True

    async def analyze_data(self, query: str, db: AsyncSession, conversation_history: List[Dict[str, str]] = None) -> ChatResponse:
        """Main entry point for data analysis - Vanna semantic analysis only."""
        start_time = time.time()
        request_id = None
        
        try:
            if conversation_history is None:
                conversation_history = []
            
            # Initialize semantic layer if needed
            self._init_semantic_layer()
            
            # Start logging
            if self._flow_logger:
                request_id = self._flow_logger.log_query_start(query)
            
            # Always use Vanna semantic analysis
            semantic_result = None
            
            if not VANNA_ENABLED:
                logging.warning("Vanna is disabled. Cannot process query.")
                return ChatResponse(
                    response="Vanna semantic layer is disabled. Please enable VANNA_ENABLED to process queries.",
                    charts=[],
                    tables=[],
                    summary_points=[]
                )
            
            if not self._query_router or not hasattr(self, '_is_vanna_ready'):
                logging.error("Semantic layer components not initialized")
                return ChatResponse(
                    response="Semantic layer is not properly initialized. Please check the configuration.",
                    charts=[],
                    tables=[],
                    summary_points=[]
                )
            
            try:
                # is_vanna_ready is now async
                vanna_ready = await self._is_vanna_ready(db)
                if not vanna_ready:
                    logging.warning("Vanna is not ready (not trained or not connected)")
                    if self._flow_logger:
                        self._flow_logger.log_fallback(request_id, "Vanna is not ready (not trained or not connected)")
                    return ChatResponse(
                        response="Vanna semantic layer is not ready. Please ensure it is trained and connected to the database.",
                        charts=[],
                        tables=[],
                        summary_points=[]
                    )
                
                # ============================================
                # QUERY REFINEMENT STEP
                # Extract last 5 user messages from conversation history (oldest to newest)
                # ============================================
                user_messages = []
                for msg in conversation_history:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')
                        # Extract the actual question from "User asked: ..." format
                        if content.startswith('User asked: '):
                            content = content[len('User asked: '):]
                        user_messages.append(content)
                
                # Take last 5 user messages (they are already in oldest to newest order)
                last_5_user_messages = user_messages[-5:] if len(user_messages) > 5 else user_messages
                
                # Refine the query using LLM
                refined_query = await self.llm_service.refine_query_with_context(
                    current_question=query,
                    conversation_history=last_5_user_messages,
                    db=db
                )
                
                # Log the refinement
                if self._flow_logger:
                    self._flow_logger.log_query_refinement(request_id, query, refined_query, last_5_user_messages)
                
                logging.info(f"Original query: {query}")
                logging.info(f"Refined query: {refined_query}")
                
                # ============================================
                # END QUERY REFINEMENT
                # ============================================
                
                # Log routing info for debugging (use refined query)
                routing_info = self._query_router.get_routing_info(refined_query)
                if self._flow_logger:
                    self._flow_logger.log_routing_decision(request_id, routing_info)
                
                # Execute semantic query with REFINED query
                semantic_result = await self._execute_semantic_query(refined_query, request_id, db)
                
                if semantic_result and semantic_result.get('success'):
                    if self._flow_logger:
                        self._flow_logger.log_result_formatting(request_id, semantic_result)
                else:
                    error_msg = semantic_result.get('error', 'Unknown error') if semantic_result else 'No result'
                    if self._flow_logger:
                        self._flow_logger.log_error(request_id, "Semantic Query", error_msg)
                    return ChatResponse(
                        response="We couldn't process your request right now. Please try again or rephrase your question.",
                        charts=[],
                        tables=[],
                        summary_points=[]
                    )
                    
            except Exception as e:
                if self._flow_logger:
                    self._flow_logger.log_error(request_id, "Semantic Routing", str(e), traceback.format_exc())
                return ChatResponse(
                    response="We couldn't process your request right now. Please try again or rephrase your question.",
                    charts=[],
                    tables=[],
                    summary_points=[]
                )
            
            # Get semantic response
            response = await self._get_semantic_response(
                query, 
                semantic_result, 
                db, 
                conversation_history,
                request_id
            )
            
            # Log completion
            duration_ms = (time.time() - start_time) * 1000
            if self._flow_logger:
                self._flow_logger.log_query_complete(request_id, True, duration_ms)
            
            return response
            
        except Exception as e:
            logging.error(f"Error in analyze_data: {str(e)}")
            if self._flow_logger and request_id:
                self._flow_logger.log_error(request_id, "analyze_data", str(e), traceback.format_exc())
                duration_ms = (time.time() - start_time) * 1000
                self._flow_logger.log_query_complete(request_id, False, duration_ms)
            
            return ChatResponse(
                response="We couldn't process your request right now. Please try again or rephrase your question.",
                charts=[],
                tables=[],
                summary_points=[]
            )

    async def _execute_semantic_query(self, question: str, request_id: str = None, db: AsyncSession = None) -> Dict[str, Any]:
        """
        Execute a semantic query using Vanna.
        
        Args:
            question: Natural language question
            request_id: Request ID for logging
            db: Database session for LLM config lookup
            
        Returns:
            Dictionary with success status, SQL, and data
        """
        try:
            from services.semantic_layer import get_vanna_client
            
            if self._flow_logger:
                self._flow_logger.log_vanna_sql_generation_start(request_id, question)
            
            vn = await get_vanna_client(db)
            if vn is None:
                return {'success': False, 'error': 'Vanna client not available'}
            
            # Generate SQL
            sql_result = vn.generate_sql_safe(question)
            
            if not sql_result.get('success'):
                if self._flow_logger:
                    self._flow_logger.log_vanna_sql_generated(request_id, "", False, sql_result.get('error'))
                return {
                    'success': False,
                    'error': sql_result.get('error', 'Failed to generate SQL'),
                }
            
            sql = sql_result.get('sql')
            
            # Log generated SQL
            if self._flow_logger:
                self._flow_logger.log_vanna_sql_generated(request_id, sql, True)
            
            # Validate SQL
            is_valid, sanitized_sql, error = self._sql_validator.validate_and_sanitize(sql)
            
            # Log validation
            if self._flow_logger:
                self._flow_logger.log_sql_validation(request_id, is_valid, sanitized_sql if is_valid else None, error)
            
            if not is_valid:
                return {
                    'success': False,
                    'error': f'SQL validation failed: {error}',
                    'sql': sql,
                }
            
            # Execute SQL
            try:
                if self._flow_logger:
                    self._flow_logger.log_sql_execution_start(request_id, sanitized_sql)
                
                df = vn.run_sql(sanitized_sql)
                
                # Log execution result
                if self._flow_logger:
                    sample_data = df.head(3).to_dict(orient='records') if len(df) > 0 else []
                    self._flow_logger.log_sql_execution_result(
                        request_id, True, len(df), list(df.columns), sample_data
                    )
                
                # Format results
                formatted = self._result_formatter.format_for_llm(df, sanitized_sql, question)
                
                return {
                    'success': True,
                    'sql': sanitized_sql,
                    'original_sql': sql,
                    'data': formatted.get('data', []),
                    'columns': formatted.get('columns', []),
                    'row_count': formatted.get('row_count', 0),
                    'summary': formatted.get('summary', ''),
                    'chart_suggestion': formatted.get('chart_suggestion'),
                    'truncated': formatted.get('truncated', False),
                }
                
            except Exception as e:
                if self._flow_logger:
                    self._flow_logger.log_sql_execution_result(request_id, False, error=str(e))
                return {
                    'success': False,
                    'error': f'SQL execution failed: {str(e)}',
                    'sql': sanitized_sql,
                }
                
        except Exception as e:
            if self._flow_logger:
                self._flow_logger.log_error(request_id, "Semantic Query", str(e), traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
            }

    async def _get_semantic_response(
        self,
        question: str,
        semantic_result: Dict[str, Any],
        db: AsyncSession,
        conversation_history: List[Dict[str, str]],
        request_id: str = None,
    ) -> ChatResponse:
        """
        Get LLM response for semantic query results.
        
        Args:
            question: Original question
            semantic_result: Results from Vanna query
            db: Database session
            conversation_history: Chat history
            request_id: Request ID for logging
            
        Returns:
            ChatResponse with AI interpretation
        """
        # Log prompt building
        if self._flow_logger:
            self._flow_logger.log_llm_prompt_start(request_id, "semantic_analysis")
        
        # Build semantic-specific prompts using dynamic templates from database
        system_prompt, user_prompt = await self.llm_service.create_semantic_prompt_dynamic(
            question,
            semantic_result,
            db,  # Pass db session for dynamic prompt fetching
        )
        
        # Log the prompts
        if self._flow_logger:
            self._flow_logger.log_llm_prompt(request_id, f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}")
        
        # Get AI response
        response = await self.llm_service.get_ai_response(
            user_prompt,
            db,
            conversation_history,
            user_question=question,
            request_id=request_id,
            system_prompt=system_prompt,
        )
        
        # Inject raw SQL data into table's full_data for Excel export
        # The LLM only returns top 10, but we have all the data from the SQL query
        raw_data = semantic_result.get('data', [])
        raw_columns = semantic_result.get('columns', [])
        # Get the true original row count from semantic_result (set by vanna_client before truncation)
        original_row_count = semantic_result.get('row_count', len(raw_data))
        
        # Convert single-value tables to KPI cards
        tables_to_keep = []
        for table in response.tables:
            # Check if this is a single value result (1 row, 1-2 columns)
            if (table.rows and len(table.rows) == 1 and 
                table.headers and len(table.headers) <= 2 and
                len(table.rows[0]) <= 2):
                
                # Convert to KPI card
                from schemas.chat import KPICard
                
                # Single column result (e.g., just a count)
                if len(table.headers) == 1:
                    label = table.title or table.headers[0]
                    value = table.rows[0][0]
                    response.kpi_cards.append(KPICard(
                        label=label,
                        value=value,
                        unit=None
                    ))
                # Two column result (e.g., label and value)
                elif len(table.headers) == 2:
                    # Try to determine which is label and which is value
                    val1, val2 = table.rows[0][0], table.rows[0][1]
                    # If first value is numeric, use table title as label
                    if isinstance(val1, (int, float)) or (isinstance(val1, str) and val1.replace(',', '').replace('.', '').isdigit()):
                        label = table.title or table.headers[0]
                        value = val1
                    else:
                        label = table.title or table.headers[0]
                        value = val2
                    
                    response.kpi_cards.append(KPICard(
                        label=label,
                        value=value,
                        unit=None
                    ))
                
                logging.info(f"Converted single-value table '{table.title}' to KPI card")
            else:
                tables_to_keep.append(table)
        
        # Replace tables list with filtered list
        response.tables = tables_to_keep
        
        if raw_data and raw_columns and response.tables:
            # Convert raw data (list of dicts) to rows format (list of lists)
            full_rows = []
            for row_dict in raw_data:
                row_values = [row_dict.get(col, '') for col in raw_columns]
                full_rows.append(row_values)
            
            # Update the first table with full data
            # (typically semantic queries produce one main result table)
            for table in response.tables:
                # Check if table headers match the SQL columns
                if table.headers and len(table.headers) > 0:
                    # Try to match headers with columns
                    header_match = all(
                        any(col.lower() in h.lower() or h.lower() in col.lower() 
                            for col in raw_columns)
                        for h in table.headers[:3]  # Check first 3 headers
                    ) if len(raw_columns) >= 3 else True
                    
                    if header_match or len(response.tables) == 1:
                        # Use raw columns as headers and raw data as full_data
                        table.full_data = full_rows
                        # Use the original row count from the database query (before any truncation)
                        table.total_rows = original_row_count
                        table.is_truncated = original_row_count > 10
                        # Store the SQL for potential full data export
                        table.sql_query = semantic_result.get('sql', '')
                        break
        
        return response

# Singleton instance
analytics_service = AnalyticsService()
