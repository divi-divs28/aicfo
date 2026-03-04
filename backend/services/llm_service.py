"""
LLM Service.
Handles LLM configuration, prompt building, and AI response generation.
Uses active LLM configuration from database instead of hardcoded values.
Supports dynamic prompt templates from database with caching.
"""
import json
import logging
import httpx
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from openai import AsyncOpenAI

from schemas.chat import ChatResponse, ChartData, TableData
from utils.logging_config import chat_logger
from utils.response_parser import parse_llm_response, log_error_to_file
from models.admin import LlmConfiguration
from services.prompt_template_service import prompt_template_service

ROOT_DIR = Path(__file__).parent.parent


class LLMService:
    """Service for LLM interactions using database configurations."""
    
    async def get_active_llm_config(self, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Get the currently active LLM configuration from database.
        
        Returns:
            Dictionary with provider, api_key, model, temperature, max_tokens, local_llm_url, local_llm_stream
            or None if no active configuration found
        """
        try:
            result = await db.execute(
                select(LlmConfiguration).where(LlmConfiguration.is_active == True).limit(1)
            )
            config = result.scalar_one_or_none()
            
            if config:
                return {
                    'provider': config.provider,
                    'api_key': config.api_key,
                    'model': config.model,
                    'temperature': config.temperature if config.temperature is not None else 0.7,
                    'max_tokens': config.max_tokens if config.max_tokens is not None else 2000,
                    'local_llm_url': config.local_llm_url,
                    'local_llm_stream': config.local_llm_stream if config.local_llm_stream is not None else False,
                }
            
            # No fallback - require database configuration
            logging.error("No active LLM configuration found in database. Please configure an LLM in Admin > LLM Settings.")
            return None
            
        except Exception as e:
            logging.error(f"Error fetching active LLM config: {str(e)}")
            return None
    
    async def get_active_provider(self, db: AsyncSession) -> str:
        """Get the currently active LLM provider from database."""
        config = await self.get_active_llm_config(db)
        if not config:
            raise ValueError("No active LLM configuration found in database. Please configure an LLM in Admin > LLM Settings.")
        return config['provider']
    
    async def get_dynamic_prompt(self, db: AsyncSession, use_case: str) -> Optional[Dict[str, str]]:
        """
        Get dynamic prompt template from database by use case.
        
        Args:
            db: Database session
            use_case: Use case identifier (e.g., 'semantic_analysis', 'query_refinement')
        
        Returns:
            Dictionary with 'system_prompt', 'user_prompt', and 'agent_role' if found, None otherwise
        """
        try:
            template = await prompt_template_service.get_prompt_by_use_case(db, use_case)
            if template:
                logging.info(f"Using dynamic prompt template '{template.name}' for use_case: {use_case}")
                return {
                    'system_prompt': template.system_prompt,
                    'user_prompt': template.user_prompt,
                    'agent_role': template.agent_role
                }
            logging.debug(f"No dynamic prompt template found for use_case: {use_case}, using default")
            return None
        except Exception as e:
            logging.error(f"Error fetching dynamic prompt for use_case {use_case}: {str(e)}")
            return None
    
    async def create_semantic_prompt_dynamic(
        self,
        question: str,
        semantic_result: Dict[str, Any],
        db: AsyncSession,
    ) -> tuple:
        """
        Build system prompt and user prompt for Vanna-generated SQL results.
        Uses dynamic prompts from database. Raises error if not found.
        
        Args:
            question: Original user question
            semantic_result: Results from Vanna semantic query
            db: Database session for fetching dynamic prompts
            
        Returns:
            Tuple of (system_prompt, user_prompt)
            
        Raises:
            ValueError: If no prompt template found for 'semantic_analysis' use case
        """
        # Get dynamic prompts from database - no fallback
        dynamic_prompts = await self.get_dynamic_prompt(db, 'semantic_analysis')
        
        if not dynamic_prompts:
            error_msg = "No prompt template found for use_case 'semantic_analysis'. Please create one in Admin > Prompt Templates."
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        logging.info("Using dynamic prompts for semantic_analysis from database")
        return self._build_semantic_prompts_from_template(
            question, 
            semantic_result, 
            dynamic_prompts['system_prompt'],
            dynamic_prompts.get('user_prompt', ''),
            dynamic_prompts.get('agent_role')
        )
    
    def _build_semantic_prompts_from_template(
        self,
        question: str,
        semantic_result: Dict[str, Any],
        system_prompt_template: str,
        user_prompt_template: str,
        template_agent_role: str = None,
    ) -> tuple:
        """
        Build semantic prompts from database templates with variable substitution.
        
        Args:
            question: Original user question
            semantic_result: Results from Vanna semantic query
            system_prompt_template: System prompt template from database
            user_prompt_template: User prompt template from database
            template_agent_role: Agent role from the prompt template (takes priority)
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Use agent_role from template - no hardcoded fallback
        agent_role = template_agent_role if template_agent_role else ''
        
        if not agent_role:
            logging.warning("No agent_role defined in prompt template. Using empty value.")
        
        sql = semantic_result.get('sql', 'N/A')
        data = semantic_result.get('data', [])
        columns = semantic_result.get('columns', [])
        row_count = semantic_result.get('row_count', 0)
        summary = semantic_result.get('summary', '')
        truncated = semantic_result.get('truncated', False)
        chart_suggestion = semantic_result.get('chart_suggestion', {})
        
        # Format data for prompt (limit to first 50 rows for context)
        data_preview = data[:50] if len(data) > 50 else data
        data_json = json.dumps(data_preview, indent=2, default=str)
        
        # Truncate if too long
        if len(data_json) > 6000:
            data_json = data_json[:6000] + "\n... [truncated for brevity]"
        
        # Build chart hint
        chart_hint = ""
        if chart_suggestion and chart_suggestion.get('type'):
            chart_hint = f"""
CHART SUGGESTION:
- Recommended type: {chart_suggestion.get('type')}
- Reason: {chart_suggestion.get('reason', 'Based on data structure')}
- Category column: {chart_suggestion.get('category_column', 'N/A')}
- Value column: {chart_suggestion.get('value_column', 'N/A')}
"""
        
        truncated_note = '(Results truncated to first 50 rows for display)' if truncated or len(data) > 50 else ''
        
        # Apply variable substitution to system prompt template
        try:
            final_system_prompt = system_prompt_template.format(
                agent_role=agent_role,
                question=question,
                sql=sql,
                columns=json.dumps(columns),
                row_count=row_count,
                summary=summary,
                chart_hint=chart_hint,
                data_json=data_json,
                truncated_note=truncated_note
            )
        except KeyError as e:
            logging.warning(f"System prompt template missing placeholder {e}, using template as-is")
            final_system_prompt = system_prompt_template
        
        # Apply variable substitution to user prompt template
        try:
            final_user_prompt = user_prompt_template.format(
                question=question,
                sql=sql,
                columns=json.dumps(columns),
                row_count=row_count,
                truncated_note=truncated_note,
                summary=summary,
                chart_hint=chart_hint,
                data_json=data_json,
                agent_role=agent_role
            )
        except KeyError as e:
            logging.warning(f"User prompt template missing placeholder {e}, using template as-is")
            final_user_prompt = user_prompt_template

        return (final_system_prompt, final_user_prompt)

    async def get_ai_response(
        self, 
        prompt: str, 
        db: AsyncSession, 
        conversation_history: List[Dict[str, str]] = None, 
        user_question: str = "",
        request_id: str = None,
        system_prompt: str = None
    ) -> ChatResponse:
        """Get AI response from configured LLM using active database configuration."""
        # Import flow logger
        flow_logger = None
        try:
            from services.semantic_layer.flow_logger import flow_logger as fl
            flow_logger = fl
        except Exception:
            pass
        
        try:
            if conversation_history is None:
                conversation_history = []
            
            # Log user question
            chat_logger.info(f"\n{'='*80}")
            chat_logger.info(f"USER QUESTION: {user_question}")
            chat_logger.info(f"SESSION HISTORY COUNT: {len(conversation_history)} messages")
            
            # Get active LLM configuration from database
            llm_config = await self.get_active_llm_config(db)
            active_provider = llm_config['provider']
            logging.info(f"Active LLM provider: {active_provider}, model: {llm_config['model']}")
            
            # Use provided system_prompt if available, otherwise use default
            if system_prompt:
                system_message = system_prompt
            else:
                # No hardcoded agent_role - this path should only be used when system_prompt is provided
                system_message = """You are an AI Assistant. Always respond with valid JSON.

IMPORTANT: You have access to conversation history. When the user asks follow-up questions like "what is his email?" or "tell me more about them", you MUST use the context from previous messages to understand who/what they are referring to. Pay close attention to names, entities, and topics discussed in the conversation history."""

            # Build messages array
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history
            # if conversation_history:
            #     for hist_msg in conversation_history:
            #         messages.append(hist_msg)
            
            # Add current user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Log the FULL context being sent to LLM
            chat_logger.info(f"\n{'='*80}")
            chat_logger.info("FULL LLM CONTEXT - START")
            chat_logger.info(f"{'='*80}")
            chat_logger.info(f"TOTAL MESSAGES: {len(messages)}")
            chat_logger.info(f"ACTIVE PROVIDER: {active_provider}")
            chat_logger.info(f"ACTIVE MODEL: {llm_config['model']}")
            for idx, msg in enumerate(messages):
                chat_logger.info(f"\n--- MESSAGE {idx + 1} [{msg['role'].upper()}] ---")
                chat_logger.info(msg['content'])
            chat_logger.info(f"\n{'='*80}")
            chat_logger.info("FULL LLM CONTEXT - END")
            chat_logger.info(f"{'='*80}")
            
            # ============================================
            # USE DATABASE CONFIGURATIONS
            # ============================================
            
            if active_provider == 'local_llm':
                # Use LLM Configuration from database
                local_llm_url = llm_config['local_llm_url']
                local_llm_model = llm_config['model']
                local_llm_stream = llm_config['local_llm_stream']
                
                logging.info(f"Using Local LLM from DB: url={local_llm_url}, model={local_llm_model}")
                chat_logger.info(f"USING LOCAL LLM (DB CONFIG): {local_llm_url} with model {local_llm_model}")
                
                # Log to semantic flow logger
                if flow_logger and request_id:
                    flow_logger.log_llm_request(request_id, local_llm_model, llm_config['temperature'], llm_config['max_tokens'])
                
                # Call Local LLM API with DB config
                payload = {
                    "model": local_llm_model,
                    "messages": messages,
                    "stream": local_llm_stream
                }
                
                # Log API call details to chat_logger
                chat_logger.info(f"\n{'='*80}")
                chat_logger.info("LOCAL LLM API CALL")
                chat_logger.info(f"{'='*80}")
                chat_logger.info(f"API URL: {local_llm_url}")
                chat_logger.info("PAYLOAD SENT TO LOCAL LLM:")
                chat_logger.info(json.dumps(payload, indent=2, default=str))
                chat_logger.info(f"{'='*80}")
                
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        local_llm_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    result = response.json()
                
                # Log raw response to chat_logger
                chat_logger.info(f"\n{'='*80}")
                chat_logger.info("LOCAL LLM RAW RESPONSE")
                chat_logger.info(f"{'='*80}")
                chat_logger.info(f"Status Code: {response.status_code}")
                chat_logger.info(f"Response Keys: {list(result.keys())}")
                chat_logger.info("RAW RESPONSE:")
                chat_logger.info(json.dumps(result, indent=2, default=str))
                chat_logger.info(f"{'='*80}")
                
                # Console logs for received response
                logging.info(f"{'='*60}")
                logging.info("LOCAL LLM RESPONSE RECEIVED")
                logging.info(f"{'='*60}")
                logging.info(f"Status Code: {response.status_code}")
                logging.info(f"Raw Response Keys: {list(result.keys())}")
                logging.info(f"Full Raw Response: {json.dumps(result, indent=2, default=str)[:3000]}")
                
                # Extract content from response - check multiple possible structures
                content = ""
                
                # Structure 1: result.message.content (Local LLM / Ollama format)
                if not content:
                    content = result.get("message", {}).get("content", "")
                
                # Structure 2: result.choices[0].message.content (OpenAI format)
                if not content:
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Structure 3: result.response.content (alternative format)
                if not content and isinstance(result.get("response"), dict):
                    content = result.get("response", {}).get("content", "")
                
                # Structure 4: result.response as string (fallback)
                if not content and isinstance(result.get("response"), str):
                    content = result.get("response", "")
                
                tokens_used = result.get("eval_count", None) or result.get("usage", {}).get("total_tokens", None)
                
                logging.info(f"Content Length: {len(content)} characters")
                logging.info(f"Tokens Used: {tokens_used}")
                
            else:
                # Use OpenAI/Anthropic/Google Configuration from database
                api_key = llm_config['api_key']
                model = llm_config['model']
                temperature = llm_config['temperature']
                max_tokens = llm_config['max_tokens']
                
                logging.info(f"Using {active_provider.upper()} from DB: model={model}")
                chat_logger.info(f"USING {active_provider.upper()} (DB CONFIG): model={model}")
                
                # Log to semantic flow logger
                if flow_logger and request_id:
                    flow_logger.log_llm_request(request_id, model, temperature, max_tokens)
                
                # Create OpenAI client with API key from database
                openai_client = AsyncOpenAI(api_key=api_key)
                
                # Build payload for logging
                openai_payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Log API call details to chat_logger
                chat_logger.info(f"\n{'='*80}")
                chat_logger.info(f"{active_provider.upper()} API CALL")
                chat_logger.info(f"{'='*80}")
                chat_logger.info("API URL: https://api.openai.com/v1/chat/completions")
                chat_logger.info(f"PAYLOAD SENT TO {active_provider.upper()}:")
                chat_logger.info(json.dumps(openai_payload, indent=2, default=str))
                chat_logger.info(f"{'='*80}")

                response = await openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else None
            
            chat_logger.info("LLM RAW RESPONSE:")
            chat_logger.info(f"{content[:1500]}...")
            
            # Log to semantic flow logger
            if flow_logger and request_id:
                flow_logger.log_llm_response(request_id, content, tokens_used)
            
            # Parse response
            final_response = parse_llm_response(content, chat_logger)
            
            # Log parsed response
            if flow_logger and request_id:
                flow_logger.log_response_parsing(request_id, {
                    'response': final_response.response,
                    'charts': [{'type': c.type, 'title': c.title, 'data': c.data} for c in final_response.charts],
                    'tables': [{'title': t.title, 'rows': t.rows} for t in final_response.tables],
                    'summary_points': final_response.summary_points,
                })
            
            chat_logger.info(f"FINAL RESPONSE TO USER: {final_response.response[:500]}...")
            chat_logger.info(f"{'='*80}\n")
            
            return final_response
                
        except Exception as e:
            error_msg = f"Error getting AI response: {str(e) or repr(e)}"
            logging.error(error_msg)
            chat_logger.info(f"ERROR: {error_msg}")
            log_error_to_file("AI Response Error", error_msg, user_question, exception=e)
            
            if flow_logger and request_id:
                flow_logger.log_error(request_id, "LLM Response", error_msg)
            
            return ChatResponse(
                response="We couldn't process your request right now. Please try again or rephrase your question.",
                charts=[],
                tables=[],
                summary_points=[]
            )

    async def refine_query_with_context(
        self,
        current_question: str,
        conversation_history: List[str],
        db: AsyncSession
    ) -> str:
        """
        Refine the user query using conversation history context.
        Uses the active LLM from database to produce a standalone analytics question.
        Requires dynamic prompt template from database - no hardcoded fallback.
        
        Args:
            current_question: The current user question
            conversation_history: List of previous user messages (oldest to newest, max 5)
            db: Database session for getting active LLM config
            
        Returns:
            Refined query string
            
        Raises:
            ValueError: If no prompt template found for 'query_refinement' use case
        """
        try:
            # If no history, return original question
            if not conversation_history:
                logging.info(f"No conversation history, using original query: {current_question}")
                return current_question
            
            # Format conversation history
            history_text = "\n".join([f"- {q}" for q in conversation_history])
            
            # Get dynamic prompts from database - no fallback
            dynamic_prompts = await self.get_dynamic_prompt(db, 'query_refinement')
            
            if not dynamic_prompts or not dynamic_prompts.get('system_prompt'):
                error_msg = "No prompt template found for use_case 'query_refinement'. Please create one in Admin > Prompt Templates."
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            logging.info("Using dynamic prompts for query_refinement from database")
            
            # Get agent_role from template
            agent_role = dynamic_prompts.get('agent_role', 'Query Refinement Assistant')
            
            # Apply variable substitution to system prompt
            try:
                system_prompt = dynamic_prompts['system_prompt'].format(
                    history_text=history_text,
                    current_question=current_question,
                    agent_role=agent_role
                )
            except KeyError:
                # If format fails, use the prompt as-is
                system_prompt = dynamic_prompts['system_prompt']
            
            # Apply variable substitution to user prompt
            if dynamic_prompts.get('user_prompt'):
                try:
                    user_prompt = dynamic_prompts['user_prompt'].format(
                        history_text=history_text,
                        current_question=current_question,
                        agent_role=agent_role
                    )
                except KeyError:
                    user_prompt = dynamic_prompts['user_prompt']
            else:
                # Default user prompt structure if not provided in template
                user_prompt = f"""Conversation History (oldest to newest):
{history_text}

Current Question:
{current_question}

Final Output:"""

            # Get active LLM config from database
            llm_config = await self.get_active_llm_config(db)
            active_provider = llm_config['provider']
            logging.info(f"Query refinement using provider: {active_provider}, model: {llm_config['model']}")
            
            # Call LLM for refinement
            if active_provider == 'local_llm':
                # Use Local LLM from database
                payload = {
                    "model": llm_config['model'],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False
                }
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        llm_config['local_llm_url'],
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    result = response.json()
                
                # Extract content from response
                refined_query = ""
                if not refined_query:
                    refined_query = result.get("message", {}).get("content", "")
                if not refined_query:
                    refined_query = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not refined_query and isinstance(result.get("response"), str):
                    refined_query = result.get("response", "")
                    
            else:
                # Use OpenAI/Anthropic/Google from database
                openai_client = AsyncOpenAI(api_key=llm_config['api_key'])
                response = await openai_client.chat.completions.create(
                    model=llm_config['model'],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more deterministic output
                    max_tokens=500
                )
                refined_query = response.choices[0].message.content
            
            # Clean up the refined query
            refined_query = refined_query.strip()
            
            # Remove any quotes that might wrap the output
            if refined_query.startswith('"') and refined_query.endswith('"'):
                refined_query = refined_query[1:-1]
            if refined_query.startswith("'") and refined_query.endswith("'"):
                refined_query = refined_query[1:-1]
            
            # If refinement failed or returned empty, use original
            if not refined_query:
                logging.warning("Query refinement returned empty, using original query")
                return current_question
            
            logging.info(f"Query refined: '{current_question}' -> '{refined_query}'")
            chat_logger.info("QUERY REFINEMENT:")
            chat_logger.info(f"  Original: {current_question}")
            chat_logger.info(f"  History: {conversation_history}")
            chat_logger.info(f"  Refined: {refined_query}")
            
            return refined_query
            
        except Exception as e:
            logging.error(f"Error refining query: {str(e)}")
            # On error, return original question
            return current_question

    async def warmup_llm(self, db: AsyncSession) -> bool:
        """
        Warm up the LLM connection with a minimal request. Call on new session creation
        so the first user query does not hit a cold connection (avoids ConnectError).
        Does not store anything in chat history or display on UI.
        """
        try:
            chat_logger.info(f"\n{'='*80}")
            chat_logger.info("LLM WARMUP - START (new session)")
            chat_logger.info(f"{'='*80}")

            # Get active LLM config from database
            llm_config = await self.get_active_llm_config(db)
            active_provider = llm_config['provider']
            chat_logger.info(f"LLM WARMUP - Active provider: {active_provider}, model: {llm_config['model']}")

            messages = [
                {"role": "system", "content": "You are a test. Reply with exactly: OK"},
                {"role": "user", "content": "Reply with exactly: OK"}
            ]

            if active_provider == 'local_llm':
                chat_logger.info(f"LLM WARMUP - Calling Local LLM: {llm_config['local_llm_url']}")
                payload = {
                    "model": llm_config['model'],
                    "messages": messages,
                    "stream": llm_config['local_llm_stream']
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        llm_config['local_llm_url'],
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                chat_logger.info("LLM WARMUP - SUCCESS (Local LLM responded)")
            else:
                chat_logger.info(f"LLM WARMUP - Calling {active_provider.upper()}")
                openai_client = AsyncOpenAI(api_key=llm_config['api_key'])
                await openai_client.chat.completions.create(
                    model=llm_config['model'],
                    messages=messages,
                    temperature=0,
                    max_tokens=10
                )
                chat_logger.info(f"LLM WARMUP - SUCCESS ({active_provider.upper()} responded)")

            chat_logger.info("LLM WARMUP - END")
            chat_logger.info(f"{'='*80}\n")
            return True
        except Exception as e:
            chat_logger.info(f"LLM WARMUP - FAILED: {str(e)}")
            chat_logger.info("LLM WARMUP - END (error)")
            chat_logger.info(f"{'='*80}\n")
            logging.warning(f"LLM warmup failed (non-fatal): {e}")
            return False


# Singleton instance
llm_service = LLMService()
