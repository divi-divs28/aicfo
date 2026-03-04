"""
Vanna Client - FAISS Vector Store + Dynamic LLM
Provides semantic SQL generation for Asset Manager.
Uses active LLM configuration from database - NO static/hardcoded values.
Supports multiple LLM providers: OpenAI, Anthropic, Google, Local LLM.

Key Design: FAISS is initialized ONCE and persists. LLM can be swapped dynamically.
"""
import os
import ssl
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

from config import (
    VANNA_ENABLED,
    VANNA_FAISS_PATH,
    VANNA_DB_HOST,
    VANNA_DB_PORT,
    VANNA_DB_NAME,
    VANNA_DB_USER,
    VANNA_DB_PASSWORD,
    VANNA_MAX_RESULTS,
    VANNA_QUERY_TIMEOUT,
    DATABASE_URL,
)

logger = logging.getLogger(__name__)

# Singleton client - FAISS persists, LLM swaps dynamically
_vanna_client: Optional[Any] = None
_vanna_initialized: bool = False
_current_llm_config: Optional[Dict[str, Any]] = None


def _fetch_llm_config_sync() -> Optional[Dict[str, Any]]:
    """
    Fetch active LLM configuration from database SYNCHRONOUSLY.
    This avoids event loop conflicts when called from async context.
    """
    try:
        # Use synchronous SQLAlchemy for this specific query
        from sqlalchemy import create_engine, text
        from config import ssl_context
        
        # Convert async URL to sync URL
        sync_url = DATABASE_URL.replace("mysql+aiomysql://", "mysql+pymysql://")
        
        sync_engine = create_engine(
            sync_url,
            connect_args={"ssl": ssl_context},
            pool_pre_ping=True
        )
        
        with sync_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT provider, api_key, model, local_llm_url FROM llm_configurations WHERE is_active = 1 LIMIT 1"
            ))
            row = result.fetchone()
            
            if row:
                config = {
                    'provider': row[0],
                    'api_key': row[1],
                    'model': row[2],
                    'local_llm_url': row[3],
                }
                logger.info(f"Fetched active LLM config (sync): provider={config['provider']}, model={config['model']}")
                return config
            else:
                logger.error("No active LLM configuration found in database.")
                return None
                
    except Exception as e:
        logger.error(f"Failed to fetch LLM config (sync): {e}")
        return None


def _fetch_prompt_template_sync(use_case: str) -> Optional[str]:
    """
    Fetch prompt template by use_case from database SYNCHRONOUSLY.
    
    Args:
        use_case: The use case key (e.g., 'sql_generation')
    
    Returns:
        The system_prompt string or None if not found
    """
    try:
        from sqlalchemy import create_engine, text
        from config import ssl_context
        
        sync_url = DATABASE_URL.replace("mysql+aiomysql://", "mysql+pymysql://")
        
        sync_engine = create_engine(
            sync_url,
            connect_args={"ssl": ssl_context},
            pool_pre_ping=True
        )
        
        with sync_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT system_prompt FROM prompt_templates WHERE use_case = :use_case AND is_active = 1 LIMIT 1"
            ), {"use_case": use_case})
            row = result.fetchone()
            
            if row and row[0]:
                logger.info(f"Fetched prompt template for use_case: {use_case}")
                return row[0]
            else:
                logger.warning(f"No active prompt template found for use_case: {use_case}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to fetch prompt template (sync): {e}")
        return None

def _get_llm_client(provider: str, api_key: str, model: str, local_llm_url: str = None):
    """
    Create an LLM client instance for the given provider.
    
    Args:
        provider: LLM provider name
        api_key: API key (for cloud providers)
        model: Model name
        local_llm_url: Base URL for local LLM (from database)
        
    Returns:
        Dict with client type, client instance, and model
    """
    provider_lower = provider.lower() if provider else 'openai'
    
    logger.info(f"Creating LLM client for provider: {provider_lower}, model: {model}")
    
    if provider_lower in ['openai', 'azure_openai']:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        return {'type': 'openai', 'client': client, 'model': model}
    
    elif provider_lower in ['anthropic', 'claude']:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            return {'type': 'anthropic', 'client': client, 'model': model}
        except ImportError:
            logger.warning("Anthropic not available, falling back to OpenAI")
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            return {'type': 'openai', 'client': client, 'model': model}
    
    elif provider_lower in ['google', 'gemini']:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return {'type': 'google', 'client': genai, 'model': model}
        except ImportError:
            logger.warning("Google GenAI not available, falling back to OpenAI")
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            return {'type': 'openai', 'client': client, 'model': model}
    
    elif provider_lower in ['local_llm', 'ollama', 'local']:
        # Ollama uses native /api/chat endpoint - URL from local_llm_url column
        if not local_llm_url or not local_llm_url.startswith('http'):
            raise ValueError("Local LLM requires a valid base URL in the local_llm_url field (e.g., https://your-ollama-server.com)")
        host = local_llm_url.rstrip('/')
        logger.info(f"Creating Ollama client with host: {host}, model: {model}")
        return {'type': 'ollama', 'client': host, 'model': model}
    
    else:
        # Default to OpenAI
        logger.warning(f"Unknown provider '{provider_lower}', defaulting to OpenAI")
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        return {'type': 'openai', 'client': client, 'model': model}


def _call_llm(llm_client: Dict, prompt: str, system_prompt: str = None) -> str:
    """
    Call the LLM with the given prompt.
    
    Args:
        llm_client: LLM client dict from _get_llm_client
        prompt: User prompt
        system_prompt: Optional system prompt
        
    Returns:
        LLM response text
    """
    client_type = llm_client['type']
    client = llm_client['client']
    model = llm_client['model']
    
    logger.info(f"Calling LLM: type={client_type}, model={model}")
    
    if client_type == 'openai':
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0
        )
        return response.choices[0].message.content
    
    elif client_type == 'ollama':
        # Use native Ollama /api/chat endpoint
        import requests
        
        host = client  # client is the host URL for ollama
        
        # Handle case where host already contains /api/chat
        if host.endswith('/api/chat'):
            url = host
        else:
            url = f"{host}/api/chat"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0
            }
        }
        
        logger.info(f"Calling Ollama API at: {url}")
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result.get('message', {}).get('content', '')
    
    elif client_type == 'anthropic':
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt or "You are a SQL expert.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    elif client_type == 'google':
        gen_model = client.GenerativeModel(model)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = gen_model.generate_content(full_prompt)
        return response.text
    
    else:
        raise ValueError(f"Unknown LLM client type: {client_type}")


class DynamicVanna:
    """
    Custom Vanna implementation for Asset Manager.
    FAISS vector store is initialized ONCE and persists.
    LLM provider can be swapped dynamically without losing FAISS data or DB connection.
    
    Key Design: Uses Vanna's native generate_sql method which leverages the trained
    vector store (DDL, docs, SQL examples) to build context-aware prompts.
    The LLM client is injected dynamically and used via submit_prompt.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with FAISS only. LLM is configured separately."""
        from vanna.legacy.faiss import FAISS
        
        if config is None:
            config = {}
        
        # Ensure FAISS directory exists
        faiss_path = config.get('faiss_path', VANNA_FAISS_PATH)
        Path(faiss_path).mkdir(parents=True, exist_ok=True)
        
        # Store reference to parent for LLM access
        parent_ref = self
        
        # Initialize FAISS for vector storage
        faiss_config = {
            'path': faiss_path,
            'client': 'persistent',
        }
        
        # Create a FAISS class that delegates LLM calls to our dynamic client
        class DynamicFAISS(FAISS):
            def __init__(self, config):
                FAISS.__init__(self, config=config)
                self._parent = parent_ref
            
            def submit_prompt(self, prompt, **kwargs):
                """
                Submit prompt to the dynamically configured LLM.
                This is called by Vanna's generate_sql method.
                """
                if self._parent._llm_client is None:
                    raise RuntimeError("LLM not configured. Call update_llm_config() first.")
                
                # Extract system message from prompt if it's a list of messages
                system_prompt = None
                user_prompt = ""
                
                if isinstance(prompt, list):
                    # Vanna sends a list of message dicts
                    for msg in prompt:
                        role = msg.get('role', '')
                        content = msg.get('content', '')
                        if role == 'system':
                            system_prompt = content
                        elif role == 'user':
                            user_prompt = content
                else:
                    # String prompt
                    user_prompt = str(prompt)
                
                # Use dynamic system prompt from database if not provided
                if not system_prompt:
                    system_prompt = _fetch_prompt_template_sync("sql_generation")
                    if not system_prompt:
                        raise ValueError("No active prompt template found for use_case 'sql_generation'. Please configure it in Admin > Prompt Templates.")
                
                logger.info(f"submit_prompt called with dynamic LLM: {self._parent.provider}/{self._parent.model}")
                
                # Call our dynamic LLM client
                return _call_llm(self._parent._llm_client, user_prompt, system_prompt)
            
            def system_message(self, message: str) -> any:
                return {"role": "system", "content": message}
            
            def user_message(self, message: str) -> any:
                return {"role": "user", "content": message}
            
            def assistant_message(self, message: str) -> any:
                return {"role": "assistant", "content": message}
        
        self._faiss = DynamicFAISS(config=faiss_config)
        
        # LLM client - can be swapped dynamically
        self._llm_client = None
        self._llm_config = None
        
        # Database connection state
        self._is_db_connected = False
        self._db_config = None
        self._max_results = config.get('max_results', VANNA_MAX_RESULTS or 1000)
        self._query_timeout = config.get('query_timeout', VANNA_QUERY_TIMEOUT or 30)
        
        logger.info(f"DynamicVanna initialized with FAISS at: {faiss_path}")
    
    def update_llm_config(self, provider: str, api_key: str, model: str, local_llm_url: str = None):
        """
        Update the LLM configuration. FAISS and DB connection remain intact.
        """
        new_config = {'provider': provider, 'api_key': api_key, 'model': model, 'local_llm_url': local_llm_url}
        
        # Check if config actually changed
        if self._llm_config == new_config:
            logger.debug("LLM config unchanged, skipping update")
            return
        
        logger.info(f"Updating LLM config: provider={provider}, model={model}")
        
        try:
            self._llm_client = _get_llm_client(provider, api_key, model, local_llm_url)
            self._llm_config = new_config
            logger.info(f"LLM client updated successfully: {provider}/{model}")
        except Exception as e:
            logger.error(f"Failed to update LLM client: {e}")
            raise
    
    @property
    def model(self) -> str:
        return self._llm_config.get('model') if self._llm_config else None
    
    @property
    def provider(self) -> str:
        return self._llm_config.get('provider') if self._llm_config else None
    
    def connect_to_mysql_ssl(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
    ) -> bool:
        """Establish SSL MySQL connection for Aiven."""
        import pymysql
        
        host = host or VANNA_DB_HOST
        port = port or VANNA_DB_PORT
        database = database or VANNA_DB_NAME
        user = user or VANNA_DB_USER
        password = password or VANNA_DB_PASSWORD
        
        if not all([host, port, database, user, password]):
            logger.error("Missing database connection parameters")
            return False
        
        try:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            
            self._db_config = {
                'host': host,
                'port': port,
                'database': database,
                'user': user,
                'password': password,
                'ssl': ssl_ctx,
                'connect_timeout': self._query_timeout,
            }
            
            conn = pymysql.connect(**self._db_config)
            conn.close()
            
            self._is_db_connected = True
            logger.info(f"Connected to MySQL: {host}:{port}/{database}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            self._is_db_connected = False
            return False
    
    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        import pymysql
        
        if not self._is_db_connected or not self._db_config:
            raise RuntimeError("Database not connected. Call connect_to_mysql_ssl() first.")
        
        try:
            conn = pymysql.connect(**self._db_config)
            df = pd.read_sql(sql, conn)
            conn.close()
            
            original_count = len(df)
            
            if len(df) > self._max_results:
                logger.warning(f"Truncating results from {original_count} to {self._max_results} rows")
                df = df.head(self._max_results)
            
            df.attrs['original_count'] = original_count
            return df
            
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if Vanna is trained, connected, and has LLM configured."""
        if not self._is_db_connected:
            logger.debug("Vanna not ready: DB not connected")
            return False
        
        if not self._llm_client:
            logger.debug("Vanna not ready: LLM not configured")
            return False
        
        try:
            import json
            faiss_path = Path(VANNA_FAISS_PATH)
            
            sql_meta = faiss_path / 'sql_metadata.json'
            if sql_meta.exists():
                with open(sql_meta) as f:
                    data = json.load(f)
                    if len(data) > 0:
                        return True
            
            training_data = self.get_training_data()
            return training_data is not None and len(training_data) > 0
        except Exception as e:
            logger.warning(f"Error checking training status: {e}")
            return False
    
    def get_training_status(self) -> Dict[str, Any]:
        """Return training statistics."""
        try:
            import json
            faiss_path = Path(VANNA_FAISS_PATH)
            
            ddl_count = 0
            doc_count = 0
            sql_count = 0
            
            for name, var in [('ddl_metadata.json', 'ddl_count'), 
                              ('doc_metadata.json', 'doc_count'),
                              ('sql_metadata.json', 'sql_count')]:
                meta_file = faiss_path / name
                if meta_file.exists():
                    with open(meta_file) as f:
                        if var == 'ddl_count':
                            ddl_count = len(json.load(f))
                        elif var == 'doc_count':
                            doc_count = len(json.load(f))
                        else:
                            sql_count = len(json.load(f))
            
            total = ddl_count + doc_count + sql_count
            
            return {
                'is_trained': total > 0,
                'total_entries': total,
                'ddl_count': ddl_count,
                'documentation_count': doc_count,
                'sql_count': sql_count,
                'is_db_connected': self._is_db_connected,
                'llm_configured': self._llm_client is not None,
                'current_provider': self.provider,
                'current_model': self.model,
            }
            
        except Exception as e:
            logger.error(f"Error getting training status: {e}")
            return {
                'is_trained': False,
                'error': str(e),
                'is_db_connected': self._is_db_connected,
            }
    
    # Delegate FAISS methods
    def get_training_data(self):
        return self._faiss.get_training_data()
    
    def train(self, **kwargs):
        return self._faiss.train(**kwargs)
    
    def add_ddl(self, ddl: str):
        return self._faiss.add_ddl(ddl)
    
    def add_documentation(self, doc: str):
        return self._faiss.add_documentation(doc)
    
    def add_question_sql(self, question: str, sql: str):
        return self._faiss.add_question_sql(question=question, sql=sql)
    
    def get_similar_question_sql(self, question: str, **kwargs):
        return self._faiss.get_similar_question_sql(question, **kwargs)
    
    def get_related_ddl(self, question: str, **kwargs):
        return self._faiss.get_related_ddl(question, **kwargs)
    
    def get_related_documentation(self, question: str, **kwargs):
        return self._faiss.get_related_documentation(question, **kwargs)
    
    def remove_collection(self, collection_name: str):
        """Remove a collection from FAISS."""
        return self._faiss.remove_collection(collection_name)
    
    def generate_sql(self, question: str) -> str:
        """
        Generate SQL using Vanna's native method with the dynamic LLM.
        
        This delegates to Vanna's FAISS-based generate_sql which:
        1. Retrieves relevant DDL, documentation, and similar SQL examples from FAISS
        2. Builds a context-aware prompt
        3. Calls submit_prompt() which uses our dynamically configured LLM
        
        The system prompt is injected dynamically from the database (use_case: sql_generation)
        via the submit_prompt method in DynamicFAISS.
        """
        if not self._llm_client:
            raise RuntimeError("LLM not configured. Call update_llm_config() first.")
        
        logger.info(f"Generating SQL with Vanna using {self.provider}/{self.model} for: {question[:50]}...")
        
        # Use Vanna's native generate_sql which leverages the trained FAISS context
        # The submit_prompt method in DynamicFAISS handles the actual LLM call
        sql = self._faiss.generate_sql(question)
        
        # Clean up response - remove markdown code blocks if present
        if sql:
            sql = sql.strip()
            if sql.startswith("```sql"):
                sql = sql[6:]
            elif sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            sql = sql.strip()
        
        logger.info(f"Generated SQL via Vanna: {sql[:100] if sql else 'None'}...")
        return sql
    
    def generate_sql_safe(self, question: str) -> Dict[str, Any]:
        """Generate SQL with error handling."""
        import re
        
        try:
            sql = self.generate_sql(question)
            
            if sql is None or sql.strip() == '':
                return {'success': False, 'sql': None, 'error': 'No SQL generated'}
            
            # Remove LIMIT clause
            original_sql = sql
            sql = re.sub(r'\s+LIMIT\s+\d+\s*;?\s*$', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\s+LIMIT\s+\d+\s*$', '', sql, flags=re.IGNORECASE)
            
            if original_sql != sql:
                logger.info(f"Removed LIMIT clause from generated SQL")
            
            return {'success': True, 'sql': sql, 'error': None}
            
        except Exception as e:
            logger.error(f"Error generating SQL for '{question}': {e}")
            return {'success': False, 'sql': None, 'error': str(e)}


def get_vanna_client_sync() -> Optional['DynamicVanna']:
    """
    Get or create Vanna client singleton - SYNCHRONOUS version.
    FAISS persists. LLM config is updated dynamically if changed.
    """
    global _vanna_client, _vanna_initialized, _current_llm_config
    
    if not VANNA_ENABLED:
        logger.debug("Vanna is disabled")
        return None
    
    # Fetch current LLM config from database (SYNCHRONOUSLY)
    llm_config = _fetch_llm_config_sync()
    
    if llm_config is None:
        return None
    
    # Create client if not exists (FAISS initialized once)
    if _vanna_client is None:
        try:
            logger.info("Creating new DynamicVanna client with FAISS...")
            _vanna_client = DynamicVanna()
            _vanna_initialized = True
            logger.info("DynamicVanna client created successfully")
        except Exception as e:
            logger.error(f"Failed to create Vanna client: {e}")
            return None
    
    # Update LLM config if changed (FAISS untouched)
    if _current_llm_config != llm_config:
        logger.info(f"LLM config changed from {_current_llm_config} to {llm_config}")
        try:
            _vanna_client.update_llm_config(
                provider=llm_config['provider'],
                api_key=llm_config['api_key'],
                model=llm_config['model'],
                local_llm_url=llm_config.get('local_llm_url')
            )
            _current_llm_config = llm_config.copy()
        except Exception as e:
            logger.error(f"Failed to update LLM config: {e}")
    
    # Ensure MySQL connection
    if not _vanna_client._is_db_connected:
        logger.info("Connecting Vanna to MySQL...")
        _vanna_client.connect_to_mysql_ssl()
    
    return _vanna_client


async def get_vanna_client(db_session=None) -> Optional['DynamicVanna']:
    """
    Get or create Vanna client singleton - ASYNC wrapper.
    Internally uses sync version to avoid event loop conflicts.
    """
    # Use the sync version to avoid event loop issues
    return get_vanna_client_sync()


def is_vanna_ready_sync() -> bool:
    """Check if Vanna is ready - SYNCHRONOUS version."""
    if not VANNA_ENABLED:
        return False
    
    client = get_vanna_client_sync()
    if client is None:
        return False
    
    return client.is_ready()


async def is_vanna_ready(db_session=None) -> bool:
    """Check if Vanna is ready - ASYNC wrapper."""
    return is_vanna_ready_sync()


def initialize_vanna_sync() -> bool:
    """Initialize Vanna client - SYNCHRONOUS version."""
    if not VANNA_ENABLED:
        logger.info("Vanna is disabled, skipping initialization")
        return False
    
    client = get_vanna_client_sync()
    if client is None:
        logger.error("Failed to get Vanna client")
        return False
    
    status = client.get_training_status()
    logger.info(f"Vanna training status: {status}")
    
    if not status.get('is_trained'):
        logger.warning("Vanna is not trained. Run training scripts to enable semantic queries.")
    
    return True


async def initialize_vanna(db_session=None) -> bool:
    """Initialize Vanna client - ASYNC wrapper."""
    return initialize_vanna_sync()
