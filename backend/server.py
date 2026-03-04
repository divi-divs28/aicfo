"""
Asset Manager - Asset Management and Auction Platform
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from database import Base, engine
from config import VANNA_ENABLED

# Import routers
from routes.base import router as base_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.dashboard import router as dashboard_router
from routes.dashboard_analytics import router as dashboard_analytics_router
from routes.dashboard_assets import router as dashboard_assets_router
from routes.admin import router as admin_router
from routes.email import router as email_router
from routes.excel_export import router as excel_export_router
from routes.training import router as training_router
from routes.test_llm import router as test_llm_router
from routes.users import router as users_router

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AICFO API...")
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("MySQL database connected and tables created")
    
    # Initialize Vanna Semantic Layer
    if VANNA_ENABLED:
        try:
            from services.semantic_layer import initialize_vanna, get_vanna_client
            
            logger.info("Initializing Vanna semantic layer...")
            success = await initialize_vanna()
            
            if success:
                vn = await get_vanna_client()
                if vn:
                    status = vn.get_training_status()
                    logger.info(f"Vanna semantic layer initialized successfully")
                    logger.info(f"  - Training status: {status.get('is_trained', False)}")
                    logger.info(f"  - Total entries: {status.get('total_entries', 0)}")
                    logger.info(f"  - DDL: {status.get('ddl_count', 0)}, Docs: {status.get('documentation_count', 0)}, SQL: {status.get('sql_count', 0)}")
                    
                    if not status.get('is_trained'):
                        logger.warning("Vanna is not trained. Run: python scripts/vanna/train_all.py")
            else:
                logger.warning("Vanna initialization failed - semantic queries will fall back to rule-based")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vanna: {e}")
            logger.warning("Continuing without semantic layer - queries will use rule-based analytics")
    else:
        logger.info("Vanna semantic layer is disabled (VANNA_ENABLED=false)")
    
    logger.info("Analytics service initialized")
    logger.info("AICFO API is ready!")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down Asset Manager API...")
    await engine.dispose()
    logger.info("Database connection closed")


# Create the main app with lifespan
app = FastAPI(
    title="AICFO API",
    description="Invoice Management and Analytics API for AICFO platform",
    version="1.0.0",
    lifespan=lifespan
)

# Include all routers with /api prefix
app.include_router(base_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(dashboard_analytics_router, prefix="/api")
app.include_router(dashboard_assets_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(email_router, prefix="/api")
app.include_router(excel_export_router)
app.include_router(training_router)
app.include_router(test_llm_router)
app.include_router(users_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
