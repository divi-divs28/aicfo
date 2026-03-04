"""
Application configuration settings.
Loads environment variables and provides centralized config access.
All values should be defined in .env file.
"""
import os
import ssl
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

# SSL Context for secure database connection
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT')) if os.environ.get('SMTP_PORT') else None
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL')
MAIL_ENCRYPTION = os.environ.get('MAIL_ENCRYPTION')

# Logging paths
CHAT_LOG_FILE = ROOT_DIR / 'chat_flow.log'
ERROR_LOG_FILE = ROOT_DIR / 'chat_error.log'

# Vanna Semantic Layer Configuration
VANNA_ENABLED = os.environ.get('VANNA_ENABLED', 'false').lower() == 'true'
VANNA_FAISS_PATH = os.environ.get('VANNA_FAISS_PATH', str(ROOT_DIR / 'data/vanna/faiss_index'))
VANNA_MODEL = os.environ.get('VANNA_MODEL')
VANNA_MAX_RESULTS = int(os.environ.get('VANNA_MAX_RESULTS')) if os.environ.get('VANNA_MAX_RESULTS') else None
VANNA_QUERY_TIMEOUT = int(os.environ.get('VANNA_QUERY_TIMEOUT')) if os.environ.get('VANNA_QUERY_TIMEOUT') else None

# Vanna Database Configuration
VANNA_DB_HOST = os.environ.get('VANNA_DB_HOST')
VANNA_DB_PORT = int(os.environ.get('VANNA_DB_PORT')) if os.environ.get('VANNA_DB_PORT') else None
VANNA_DB_NAME = os.environ.get('VANNA_DB_NAME')
VANNA_DB_USER = os.environ.get('VANNA_DB_USER')
VANNA_DB_PASSWORD = os.environ.get('VANNA_DB_PASSWORD') if os.environ.get('VANNA_DB_PASSWORD') else None
