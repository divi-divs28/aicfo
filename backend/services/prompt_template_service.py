"""
Prompt Template Service with Caching.
Manages prompt templates from database with in-memory caching for performance.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.admin import PromptTemplate

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Service for managing prompt templates with caching."""
    
    def __init__(self):
        self._cache: Dict[str, PromptTemplate] = {}
        self._cache_loaded: bool = False
        self._cache_timestamp: Optional[datetime] = None
    
    async def get_prompt_by_use_case(self, db: AsyncSession, use_case: str) -> Optional[PromptTemplate]:
        """
        Get prompt template by use case.
        Uses cache if available, otherwise loads from database.
        
        Args:
            db: Database session
            use_case: Use case identifier (e.g., 'semantic_analysis', 'report_generation')
        
        Returns:
            PromptTemplate object or None if not found
        """
        # Load cache if not loaded
        if not self._cache_loaded:
            await self.load_all_templates(db)
        
        # Try to get from cache
        template = self._cache.get(use_case)
        
        if template:
            logger.info(f"Prompt template cache hit for use_case: {use_case}")
            return template
        
        # Cache miss - reload and try again
        logger.warning(f"Prompt template cache miss for use_case: {use_case}, reloading cache")
        await self.load_all_templates(db)
        
        return self._cache.get(use_case)
    
    async def load_all_templates(self, db: AsyncSession) -> None:
        """
        Load all active templates from database into cache.
        
        Args:
            db: Database session
        """
        try:
            result = await db.execute(
                select(PromptTemplate).where(PromptTemplate.is_active == True)
            )
            templates = result.scalars().all()
            
            # Clear existing cache
            self._cache.clear()
            
            # Load templates into cache by use_case
            for template in templates:
                if template.use_case:
                    self._cache[template.use_case] = template
                    logger.debug(f"Cached template: {template.name} (use_case: {template.use_case})")
            
            self._cache_loaded = True
            self._cache_timestamp = datetime.utcnow()
            
            logger.info(f"Loaded {len(self._cache)} prompt templates into cache")
            
        except Exception as e:
            logger.error(f"Error loading prompt templates: {str(e)}")
            # Don't raise - allow service to continue with empty cache
    
    def clear_cache(self) -> None:
        """
        Clear the cache.
        Called when templates are created, updated, or deleted.
        """
        self._cache.clear()
        self._cache_loaded = False
        self._cache_timestamp = None
        logger.info("Prompt template cache cleared")
    
    def get_cache_info(self) -> Dict:
        """
        Get cache information for debugging.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'cached_templates': len(self._cache),
            'use_cases': list(self._cache.keys()),
            'cache_loaded': self._cache_loaded,
            'cache_timestamp': self._cache_timestamp.isoformat() if self._cache_timestamp else None
        }


# Singleton instance
prompt_template_service = PromptTemplateService()
