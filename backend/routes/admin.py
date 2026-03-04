"""
Admin routes.
CRUD for question categories, suggested questions, dashboard cards.
SMTP, LLM, Prompt Templates, System Logs, and System Preferences configuration.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import logging

from database import get_db
from models.chat import QuestionCategory, SuggestedQuestion, DashboardCard
from models.admin import SmtpConfiguration, LlmConfiguration, PromptTemplate, SystemLog, SystemPreference
from schemas.chat import (
    QuestionCategoryCreate, QuestionCategoryUpdate, QuestionCategoryResponse,
    SuggestedQuestionCreate, SuggestedQuestionUpdate, SuggestedQuestionResponse,
    DashboardCardCreate, DashboardCardUpdate, DashboardCardResponse
)
from schemas.email import SmtpConfigRequest, SmtpConfigResponse, SmtpTestRequest, SmtpTestResponse
from schemas.admin import (
    LlmConfigRequest, LlmConfigResponse, LlmTestRequest, LlmTestResponse, LlmModelsResponse,
    PromptTemplateRequest, PromptTemplateResponse,
    SystemLogResponse,
    SystemPreferenceRequest, SystemPreferenceResponse, BulkPreferenceRequest
)
from services.email_service import email_service
from services.prompt_template_service import prompt_template_service

router = APIRouter(prefix="/admin")


# =============================================================================
# QUESTION CATEGORIES CRUD
# =============================================================================

@router.get("/question-categories", response_model=List[QuestionCategoryResponse])
async def get_question_categories(db: AsyncSession = Depends(get_db)):
    """Get all question categories."""
    result = await db.execute(select(QuestionCategory).order_by(QuestionCategory.order_index))
    return result.scalars().all()


@router.post("/question-categories", response_model=QuestionCategoryResponse)
async def create_question_category(category: QuestionCategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new question category."""
    new_category = QuestionCategory(
        id=str(uuid.uuid4()),
        title=category.title,
        color=category.color,
        icon_bg=category.icon_bg,
        text_color=category.text_color,
        icon_type=category.icon_type,
        order_index=category.order_index
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category


@router.put("/question-categories/{category_id}", response_model=QuestionCategoryResponse)
async def update_question_category(category_id: str, category: QuestionCategoryUpdate, db: AsyncSession = Depends(get_db)):
    """Update a question category."""
    result = await db.execute(select(QuestionCategory).where(QuestionCategory.id == category_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(existing, key, value)
    
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/question-categories/{category_id}")
async def delete_question_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a question category."""
    result = await db.execute(select(QuestionCategory).where(QuestionCategory.id == category_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await db.execute(select(SuggestedQuestion).where(SuggestedQuestion.category_id == category_id))
    await db.delete(existing)
    await db.commit()
    return {"message": "Category deleted successfully"}


# =============================================================================
# SUGGESTED QUESTIONS CRUD
# =============================================================================

@router.get("/suggested-questions", response_model=List[SuggestedQuestionResponse])
async def get_suggested_questions(db: AsyncSession = Depends(get_db)):
    """Get all suggested questions."""
    result = await db.execute(select(SuggestedQuestion).order_by(SuggestedQuestion.category_id, SuggestedQuestion.order_index))
    return result.scalars().all()


@router.post("/suggested-questions", response_model=SuggestedQuestionResponse)
async def create_suggested_question(question: SuggestedQuestionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new suggested question."""
    new_question = SuggestedQuestion(
        id=str(uuid.uuid4()),
        category_id=question.category_id,
        question_text=question.question_text,
        order_index=question.order_index
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)
    return new_question


@router.put("/suggested-questions/{question_id}", response_model=SuggestedQuestionResponse)
async def update_suggested_question(question_id: str, question: SuggestedQuestionUpdate, db: AsyncSession = Depends(get_db)):
    """Update a suggested question."""
    result = await db.execute(select(SuggestedQuestion).where(SuggestedQuestion.id == question_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
    
    update_data = question.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(existing, key, value)
    
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/suggested-questions/{question_id}")
async def delete_suggested_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a suggested question."""
    result = await db.execute(select(SuggestedQuestion).where(SuggestedQuestion.id == question_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
    
    await db.delete(existing)
    await db.commit()
    return {"message": "Question deleted successfully"}


# =============================================================================
# DASHBOARD CARDS CRUD
# =============================================================================

@router.get("/dashboard-cards", response_model=List[DashboardCardResponse])
async def get_dashboard_cards(db: AsyncSession = Depends(get_db)):
    """Get all dashboard cards."""
    result = await db.execute(select(DashboardCard).order_by(DashboardCard.order_index))
    return result.scalars().all()


@router.post("/dashboard-cards", response_model=DashboardCardResponse)
async def create_dashboard_card(card: DashboardCardCreate, db: AsyncSession = Depends(get_db)):
    """Create a new dashboard card."""
    new_card = DashboardCard(
        id=str(uuid.uuid4()),
        title=card.title,
        icon=card.icon,
        description=card.description,
        gradient=card.gradient,
        bg_color=card.bg_color,
        text_color=card.text_color,
        query_type=card.query_type,
        order_index=card.order_index
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    return new_card


@router.put("/dashboard-cards/{card_id}", response_model=DashboardCardResponse)
async def update_dashboard_card(card_id: str, card: DashboardCardUpdate, db: AsyncSession = Depends(get_db)):
    """Update a dashboard card."""
    result = await db.execute(select(DashboardCard).where(DashboardCard.id == card_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    
    update_data = card.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(existing, key, value)
    
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/dashboard-cards/{card_id}")
async def delete_dashboard_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a dashboard card."""
    result = await db.execute(select(DashboardCard).where(DashboardCard.id == card_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    
    await db.delete(existing)
    await db.commit()
    return {"message": "Card deleted successfully"}


@router.get("/available-query-types")
async def get_available_query_types():
    """Get available query types for dashboard cards."""
    return {
        'tables': ['users', 'loan_accounts', 'deposit_accounts'],
        'query_types': [
            {'value': 'total_users', 'label': 'Total Users', 'description': 'Count of all users'},
            {'value': 'total_loans', 'label': 'Total Loans', 'description': 'Count of all loan accounts'},
            {'value': 'total_deposits', 'label': 'Total Deposits', 'description': 'Count of all deposit accounts'},
            {'value': 'total_outstanding', 'label': 'Total Outstanding', 'description': 'Sum of outstanding principal'},
            {'value': 'total_deposit_balance', 'label': 'Total Deposit Balance', 'description': 'Sum of deposit balances'},
            {'value': 'npa_count', 'label': 'NPA Count', 'description': 'Count of NPA accounts'},
        ]
    }


# =============================================================================
# SMTP CONFIGURATION
# =============================================================================

@router.get("/smtp-config", response_model=Optional[SmtpConfigResponse])
async def get_smtp_config(db: AsyncSession = Depends(get_db)):
    """Get current active SMTP configuration."""
    try:
        result = await db.execute(
            select(SmtpConfiguration).where(SmtpConfiguration.is_active == True).limit(1)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return None
        
        return SmtpConfigResponse(
            id=config.id,
            provider=config.provider,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            username=config.username,
            use_tls=config.use_tls,
            use_ssl=config.use_ssl,
            from_name=config.from_name,
            from_email=config.from_email,
            is_active=config.is_active,
            is_verified=config.is_verified,
            last_tested_at=config.last_tested_at,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    except Exception as e:
        logging.error(f"Error getting SMTP config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get SMTP configuration: {str(e)}")


@router.post("/smtp-config", response_model=SmtpConfigResponse)
async def save_smtp_config(request: SmtpConfigRequest, db: AsyncSession = Depends(get_db)):
    """Save or update SMTP configuration."""
    try:
        await db.execute(text("UPDATE smtp_configurations SET is_active = FALSE"))
        
        result = await db.execute(
            select(SmtpConfiguration).where(SmtpConfiguration.provider == request.provider).limit(1)
        )
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            existing_config.smtp_host = request.smtp_host
            existing_config.smtp_port = request.smtp_port
            existing_config.username = request.username
            existing_config.password = request.password
            existing_config.use_tls = request.use_tls
            existing_config.use_ssl = request.use_ssl
            existing_config.from_name = request.from_name
            existing_config.from_email = request.from_email
            existing_config.is_active = True
            existing_config.is_verified = False
            existing_config.updated_at = datetime.now(timezone.utc)
            config = existing_config
        else:
            config = SmtpConfiguration(
                id=str(uuid.uuid4()),
                provider=request.provider,
                smtp_host=request.smtp_host,
                smtp_port=request.smtp_port,
                username=request.username,
                password=request.password,
                use_tls=request.use_tls,
                use_ssl=request.use_ssl,
                from_name=request.from_name,
                from_email=request.from_email,
                is_active=True,
                is_verified=False
            )
            db.add(config)
        
        await db.commit()
        await db.refresh(config)
        
        logging.info(f"SMTP configuration saved for provider: {request.provider}")
        
        return SmtpConfigResponse(
            id=config.id,
            provider=config.provider,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            username=config.username,
            use_tls=config.use_tls,
            use_ssl=config.use_ssl,
            from_name=config.from_name,
            from_email=config.from_email,
            is_active=config.is_active,
            is_verified=config.is_verified,
            last_tested_at=config.last_tested_at,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    except Exception as e:
        await db.rollback()
        logging.error(f"Error saving SMTP config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save SMTP configuration: {str(e)}")


@router.post("/smtp-config/test", response_model=SmtpTestResponse)
async def test_smtp_config(request: SmtpTestRequest, db: AsyncSession = Depends(get_db)):
    """Test SMTP configuration by sending a test email."""
    try:
        result = await db.execute(
            select(SmtpConfiguration).where(SmtpConfiguration.is_active == True).limit(1)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="No active SMTP configuration found. Please save configuration first.")
        
        test_result = await email_service.test_smtp_connection(db, request.test_email)
        
        if test_result["success"]:
            config.is_verified = True
            config.last_tested_at = datetime.now(timezone.utc)
            await db.commit()
            
            return SmtpTestResponse(
                success=True,
                message=f"Test email sent successfully to {request.test_email}. Configuration verified!"
            )
        else:
            return SmtpTestResponse(success=False, message=test_result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error testing SMTP config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test SMTP configuration: {str(e)}")


@router.delete("/smtp-config/{config_id}")
async def delete_smtp_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Delete SMTP configuration."""
    try:
        result = await db.execute(select(SmtpConfiguration).where(SmtpConfiguration.id == config_id))
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="SMTP configuration not found")
        
        await db.delete(config)
        await db.commit()
        
        return {"success": True, "message": "SMTP configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting SMTP config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete SMTP configuration: {str(e)}")


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

class LlmService:
    """Service for managing LLM integrations."""
    
    OPENAI_MODELS = {
        'gpt-4o': {'name': 'GPT-4o', 'description': 'Most capable model, best for complex tasks', 'context': '128K'},
        'gpt-4o-mini': {'name': 'GPT-4o Mini', 'description': 'Fast and efficient for simpler tasks', 'context': '128K'},
        'gpt-4-turbo': {'name': 'GPT-4 Turbo', 'description': 'Latest GPT-4 with vision capabilities', 'context': '128K'},
        'gpt-4': {'name': 'GPT-4', 'description': 'High intelligence model', 'context': '8K'},
        'gpt-3.5-turbo': {'name': 'GPT-3.5 Turbo', 'description': 'Fast and cost-effective', 'context': '16K'},
        'gpt-3.5-turbo-16k': {'name': 'GPT-3.5 Turbo 16K', 'description': 'Extended context window', 'context': '16K'},
    }
    
    @staticmethod
    async def fetch_openai_models(api_key: str) -> dict:
        """Fetch available models from OpenAI API."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    return {"success": False, "models": [], "message": "Invalid API key"}
                elif response.status_code != 200:
                    return {"success": False, "models": [], "message": f"API error: {response.status_code}"}
                
                data = response.json()
                chat_models = []
                for model in data.get('data', []):
                    model_id = model.get('id', '')
                    if model_id.startswith(('gpt-4', 'gpt-3.5')) and 'instruct' not in model_id:
                        model_info = LlmService.OPENAI_MODELS.get(model_id, {})
                        chat_models.append({
                            'id': model_id,
                            'name': model_info.get('name', model_id),
                            'description': model_info.get('description', 'OpenAI model'),
                            'context': model_info.get('context', 'N/A'),
                            'owned_by': model.get('owned_by', 'openai')
                        })
                
                chat_models.sort(key=lambda x: (
                    0 if 'gpt-4o' in x['id'] and 'mini' not in x['id'] else
                    1 if 'gpt-4o-mini' in x['id'] else
                    2 if 'gpt-4-turbo' in x['id'] else
                    3 if x['id'] == 'gpt-4' else
                    4 if 'gpt-3.5' in x['id'] else 5
                ))
                
                return {"success": True, "models": chat_models, "message": None}
                
        except Exception as e:
            logging.error(f"Error fetching OpenAI models: {str(e)}")
            return {"success": False, "models": [], "message": str(e)}
    
    @staticmethod
    async def test_openai_connection(api_key: str, model: str, prompt: str = "Say hello in one sentence.") -> dict:
        """Test OpenAI API connection."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 100, "temperature": 0.7},
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    return {"success": False, "message": "Invalid API key", "response": None}
                elif response.status_code == 404:
                    return {"success": False, "message": f"Model '{model}' not found", "response": None}
                elif response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f"API error: {response.status_code}")
                    return {"success": False, "message": error_msg, "response": None}
                
                data = response.json()
                ai_response = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return {"success": True, "message": "Connection successful!", "response": ai_response}
                
        except Exception as e:
            logging.error(f"Error testing OpenAI connection: {str(e)}")
            return {"success": False, "message": str(e), "response": None}

    @staticmethod
    async def test_local_llm_connection(url: str, model: str, stream: bool, prompt: str = "Say hello in one sentence.") -> dict:
        """Test Local LLM API connection with a sample ping message."""
        try:
            import httpx
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": stream,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 401:
                    return {"success": False, "message": "Unauthorized", "response": None}
                if response.status_code == 404:
                    return {"success": False, "message": "Endpoint not found", "response": None}
                if response.status_code != 200:
                    try:
                        err = response.json()
                        msg = err.get("error", err.get("message", response.text)) or f"HTTP {response.status_code}"
                    except Exception:
                        msg = response.text or f"HTTP {response.status_code}"
                    return {"success": False, "message": msg, "response": None}
                result = response.json()
                ai_response = (
                    result.get("message", {}).get("content")
                    or (result.get("choices", [{}]) or [{}])[0].get("message", {}).get("content")
                    or result.get("response")
                )
                if isinstance(ai_response, str):
                    pass
                else:
                    ai_response = str(ai_response) if ai_response else ""
                return {"success": True, "message": "Connection successful!", "response": ai_response or "OK"}
        except httpx.ConnectError as e:
            logging.error(f"Error testing Local LLM connection (connect): {str(e)}")
            return {"success": False, "message": "Could not reach the server. Check URL and network.", "response": None}
        except Exception as e:
            logging.error(f"Error testing Local LLM connection: {str(e)}")
            return {"success": False, "message": str(e), "response": None}

    @staticmethod
    async def test_anthropic_connection(api_key: str, model: str, prompt: str = "Say hello in one sentence.") -> dict:
        """Test Anthropic Claude API connection."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100
                    },
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    return {"success": False, "message": "Invalid API key", "response": None}
                elif response.status_code == 404:
                    return {"success": False, "message": f"Model '{model}' not found", "response": None}
                elif response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f"API error: {response.status_code}")
                    return {"success": False, "message": error_msg, "response": None}
                
                data = response.json()
                ai_response = data.get('content', [{}])[0].get('text', '')
                return {"success": True, "message": "Connection successful!", "response": ai_response}
                
        except Exception as e:
            logging.error(f"Error testing Anthropic connection: {str(e)}")
            return {"success": False, "message": str(e), "response": None}

    @staticmethod
    async def test_google_connection(api_key: str, model: str, prompt: str = "Say hello in one sentence.") -> dict:
        """Test Google Gemini API connection."""
        try:
            import httpx
            # Gemini uses a different API structure
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 401 or response.status_code == 403:
                    return {"success": False, "message": "Invalid API key", "response": None}
                elif response.status_code == 404:
                    return {"success": False, "message": f"Model '{model}' not found", "response": None}
                elif response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f"API error: {response.status_code}")
                    return {"success": False, "message": error_msg, "response": None}
                
                data = response.json()
                ai_response = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return {"success": True, "message": "Connection successful!", "response": ai_response}
                
        except Exception as e:
            logging.error(f"Error testing Google connection: {str(e)}")
            return {"success": False, "message": str(e), "response": None}


llm_admin_service = LlmService()


@router.get("/llm-config", response_model=Optional[LlmConfigResponse])
async def get_llm_config(db: AsyncSession = Depends(get_db)):
    """Get current active LLM configuration."""
    try:
        result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.is_active == True).limit(1))
        config = result.scalar_one_or_none()
        
        if not config:
            return None
        
        return LlmConfigResponse(
            id=config.id, provider=config.provider, api_key=config.api_key, model=config.model,
            temperature=config.temperature, max_tokens=config.max_tokens,
            local_llm_url=config.local_llm_url, local_llm_stream=config.local_llm_stream,
            is_active=config.is_active, is_verified=config.is_verified,
            last_tested_at=config.last_tested_at, created_at=config.created_at, updated_at=config.updated_at
        )
    except Exception as e:
        logging.error(f"Error getting LLM config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get LLM configuration: {str(e)}")


@router.get("/llm-config/all")
async def get_all_llm_configs(db: AsyncSession = Depends(get_db)):
    """Get all LLM configurations for all providers."""
    try:
        result = await db.execute(select(LlmConfiguration))
        configs = result.scalars().all()
        
        config_list = []
        for config in configs:
            config_list.append({
                'id': config.id,
                'provider': config.provider,
                'api_key': config.api_key,
                'model': config.model,
                'temperature': config.temperature,
                'max_tokens': config.max_tokens,
                'local_llm_url': config.local_llm_url,
                'local_llm_stream': config.local_llm_stream,
                'is_active': config.is_active,
                'is_verified': config.is_verified,
                'last_tested_at': config.last_tested_at,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            })
        
        return {'success': True, 'configs': config_list}
    except Exception as e:
        logging.error(f"Error getting all LLM configs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get all LLM configurations: {str(e)}")


@router.post("/llm-config", response_model=LlmConfigResponse)
async def save_llm_config(request: LlmConfigRequest, db: AsyncSession = Depends(get_db)):
    """Save or update LLM configuration. If activate=True, this config becomes active for chat."""
    try:
        # Only deactivate other configs if we're activating this one
        if request.activate:
            await db.execute(text("UPDATE llm_configurations SET is_active = FALSE"))
        
        result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == request.provider).limit(1))
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            if request.api_key and request.api_key != '***KEEP_EXISTING***':
                existing_config.api_key = request.api_key
            existing_config.model = request.model
            existing_config.temperature = request.temperature
            existing_config.max_tokens = request.max_tokens
            existing_config.local_llm_url = request.local_llm_url
            existing_config.local_llm_stream = request.local_llm_stream
            if request.activate:
                existing_config.is_active = True
            existing_config.is_verified = False
            existing_config.updated_at = datetime.now(timezone.utc)
            config = existing_config
        else:
            config = LlmConfiguration(
                id=str(uuid.uuid4()), provider=request.provider, api_key=request.api_key or '',
                model=request.model, temperature=request.temperature, max_tokens=request.max_tokens,
                local_llm_url=request.local_llm_url, local_llm_stream=request.local_llm_stream,
                is_active=request.activate, is_verified=False
            )
            db.add(config)
        
        await db.commit()
        await db.refresh(config)
        
        return LlmConfigResponse(
            id=config.id, provider=config.provider, api_key=config.api_key, model=config.model,
            temperature=config.temperature, max_tokens=config.max_tokens,
            local_llm_url=config.local_llm_url, local_llm_stream=config.local_llm_stream,
            is_active=config.is_active, is_verified=config.is_verified,
            last_tested_at=config.last_tested_at, created_at=config.created_at, updated_at=config.updated_at
        )
    except Exception as e:
        await db.rollback()
        logging.error(f"Error saving LLM config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save LLM configuration: {str(e)}")


class ActivateProviderRequest(BaseModel):
    provider: str


@router.post("/llm-config/activate")
async def activate_llm_provider(request: ActivateProviderRequest, db: AsyncSession = Depends(get_db)):
    """Activate a LLM provider for chat. Uses STATIC configurations defined in code."""
    try:
        valid_providers = ['openai', 'local_llm']
        if request.provider not in valid_providers:
            raise HTTPException(status_code=400, detail=f"Invalid provider. Valid options: {valid_providers}")
        
        # Deactivate all configs
        await db.execute(text("UPDATE llm_configurations SET is_active = FALSE"))
        
        # Check if provider config exists, if not create a minimal one
        result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == request.provider).limit(1))
        config = result.scalar_one_or_none()
        
        if not config:
            # Create minimal config entry to track active provider
            config = LlmConfiguration(
                id=str(uuid.uuid4()),
                provider=request.provider,
                api_key='',  # Not used - static config in code
                model='static',  # Not used - static config in code
                is_active=True,
                is_verified=True
            )
            db.add(config)
        else:
            config.is_active = True
            config.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        provider_name = 'Local LLM' if request.provider == 'local_llm' else 'OpenAI'
        return {
            "success": True,
            "message": f"{provider_name} is now active for chat",
            "provider": request.provider
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error activating LLM provider: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to activate LLM provider: {str(e)}")


@router.post("/llm-config/models", response_model=LlmModelsResponse)
async def fetch_llm_models(api_key: str = None, provider: str = "openai", db: AsyncSession = Depends(get_db)):
    """Fetch available models from the LLM provider."""
    try:
        if not api_key:
            result = await db.execute(
                select(LlmConfiguration).where(LlmConfiguration.provider == provider, LlmConfiguration.is_active == True).limit(1)
            )
            config = result.scalar_one_or_none()
            if config:
                api_key = config.api_key
        
        if not api_key:
            default_models = [{'id': model_id, **info} for model_id, info in LlmService.OPENAI_MODELS.items()]
            return LlmModelsResponse(success=True, models=default_models, message="Using default model list")
        
        if provider == "openai":
            result = await llm_admin_service.fetch_openai_models(api_key)
            return LlmModelsResponse(**result)
        else:
            return LlmModelsResponse(success=False, models=[], message=f"Provider '{provider}' not supported yet")
            
    except Exception as e:
        logging.error(f"Error fetching LLM models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.post("/llm-config/test", response_model=LlmTestResponse)
async def test_llm_config(request: LlmTestRequest = None, db: AsyncSession = Depends(get_db)):
    """Test LLM configuration. Uses request credentials if provider/model/url/api_key are provided; otherwise uses active DB config."""
    try:
        req = request or LlmTestRequest()
        prompt = req.prompt or "Say hello in one sentence."

        # Test with credentials from request (current form values) when provided
        if req.provider:
            if req.provider == "openai":
                api_key = req.api_key
                if not api_key or api_key == "***KEEP_EXISTING***":
                    result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == "openai").limit(1))
                    existing = result.scalar_one_or_none()
                    api_key = existing.api_key if existing and existing.api_key else None
                if not api_key:
                    raise HTTPException(status_code=400, detail="API key is required to test OpenAI.")
                if not req.model:
                    raise HTTPException(status_code=400, detail="Model is required to test OpenAI.")
                test_result = await llm_admin_service.test_openai_connection(api_key, req.model, prompt)
            elif req.provider == "anthropic":
                api_key = req.api_key
                if not api_key or api_key == "***KEEP_EXISTING***":
                    result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == "anthropic").limit(1))
                    existing = result.scalar_one_or_none()
                    api_key = existing.api_key if existing and existing.api_key else None
                if not api_key:
                    raise HTTPException(status_code=400, detail="API key is required to test Anthropic.")
                if not req.model:
                    raise HTTPException(status_code=400, detail="Model is required to test Anthropic.")
                test_result = await llm_admin_service.test_anthropic_connection(api_key, req.model, prompt)
            elif req.provider == "google":
                api_key = req.api_key
                if not api_key or api_key == "***KEEP_EXISTING***":
                    result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == "google").limit(1))
                    existing = result.scalar_one_or_none()
                    api_key = existing.api_key if existing and existing.api_key else None
                if not api_key:
                    raise HTTPException(status_code=400, detail="API key is required to test Google.")
                if not req.model:
                    raise HTTPException(status_code=400, detail="Model is required to test Google.")
                test_result = await llm_admin_service.test_google_connection(api_key, req.model, prompt)
            elif req.provider == "local_llm":
                if not req.local_llm_url:
                    raise HTTPException(status_code=400, detail="Local LLM URL is required to test.")
                if not req.model:
                    raise HTTPException(status_code=400, detail="Model is required to test Local LLM.")
                test_result = await llm_admin_service.test_local_llm_connection(
                    req.local_llm_url, req.model, req.local_llm_stream, prompt
                )
            else:
                return LlmTestResponse(success=False, message=f"Provider '{req.provider}' test not supported yet")
            
            # Update DB config if test successful and provider exists
            if test_result["success"]:
                result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.provider == req.provider).limit(1))
                config = result.scalar_one_or_none()
                if config:
                    config.is_verified = True
                    config.last_tested_at = datetime.now(timezone.utc)
                    await db.commit()
            
            return LlmTestResponse(**test_result)

        # Fallback: use active config from DB
        result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.is_active == True).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="No active LLM configuration found. Save and activate a provider, or provide credentials in the test request.")

        if config.provider == "openai":
            if not config.api_key:
                raise HTTPException(status_code=400, detail="Active OpenAI config has no API key. Enter one and save, or test with credentials in the form.")
            test_result = await llm_admin_service.test_openai_connection(config.api_key, config.model, prompt)
        elif config.provider == "anthropic":
            if not config.api_key:
                raise HTTPException(status_code=400, detail="Active Anthropic config has no API key. Enter one and save, or test with credentials in the form.")
            test_result = await llm_admin_service.test_anthropic_connection(config.api_key, config.model, prompt)
        elif config.provider == "google":
            if not config.api_key:
                raise HTTPException(status_code=400, detail="Active Google config has no API key. Enter one and save, or test with credentials in the form.")
            test_result = await llm_admin_service.test_google_connection(config.api_key, config.model, prompt)
        elif config.provider == "local_llm":
            if not config.local_llm_url:
                raise HTTPException(status_code=400, detail="Active Local LLM config has no URL. Enter one and save, or test with credentials in the form.")
            test_result = await llm_admin_service.test_local_llm_connection(
                config.local_llm_url, config.model, config.local_llm_stream or False, prompt
            )
        else:
            return LlmTestResponse(success=False, message=f"Provider '{config.provider}' not supported yet")

        if test_result["success"]:
            config.is_verified = True
            config.last_tested_at = datetime.now(timezone.utc)
            await db.commit()

        return LlmTestResponse(**test_result)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error testing LLM config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test LLM configuration: {str(e)}")


@router.delete("/llm-config/{config_id}")
async def delete_llm_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Delete LLM configuration."""
    try:
        result = await db.execute(select(LlmConfiguration).where(LlmConfiguration.id == config_id))
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        await db.delete(config)
        await db.commit()
        
        return {"success": True, "message": "LLM configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting LLM config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete LLM configuration: {str(e)}")


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

@router.get("/prompt-templates")
async def get_prompt_templates(db: AsyncSession = Depends(get_db)):
    """Get all prompt templates."""
    try:
        result = await db.execute(select(PromptTemplate).order_by(PromptTemplate.created_at.desc()))
        templates = result.scalars().all()
        return [
            PromptTemplateResponse(
                id=t.id, name=t.name, description=t.description, 
                system_prompt=t.system_prompt, user_prompt=t.user_prompt,
                use_case=t.use_case, agent_role=t.agent_role, is_active=t.is_active,
                created_at=t.created_at, updated_at=t.updated_at
            ) for t in templates
        ]
    except Exception as e:
        logging.error(f"Error fetching prompt templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompt templates: {str(e)}")


@router.post("/prompt-templates", response_model=PromptTemplateResponse)
async def create_prompt_template(request: PromptTemplateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new prompt template."""
    try:
        template = PromptTemplate(
            name=request.name, description=request.description, system_prompt=request.system_prompt,
            user_prompt=request.user_prompt, use_case=request.use_case, agent_role=request.agent_role,
            is_active=request.is_active
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        await log_system_action(db, None, None, "create_prompt_template", "admin", f"Created prompt template: {template.name}")
        
        # Clear cache so new template is available immediately
        prompt_template_service.clear_cache()
        logging.info(f"Prompt template cache cleared after creating: {template.name}")
        
        return PromptTemplateResponse(
            id=template.id, name=template.name, description=template.description,
            system_prompt=template.system_prompt, user_prompt=template.user_prompt,
            use_case=template.use_case, agent_role=template.agent_role, is_active=template.is_active,
            created_at=template.created_at, updated_at=template.updated_at
        )
    except Exception as e:
        await db.rollback()
        logging.error(f"Error creating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create prompt template: {str(e)}")


@router.put("/prompt-templates/{template_id}", response_model=PromptTemplateResponse)
async def update_prompt_template(template_id: str, request: PromptTemplateRequest, db: AsyncSession = Depends(get_db)):
    """Update a prompt template."""
    try:
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
        template.name = request.name
        template.description = request.description
        template.system_prompt = request.system_prompt
        template.user_prompt = request.user_prompt
        template.use_case = request.use_case
        template.agent_role = request.agent_role
        template.is_active = request.is_active
        template.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(template)
        
        await log_system_action(db, None, None, "update_prompt_template", "admin", f"Updated prompt template: {template.name}")
        
        # Clear cache so updated template is available immediately
        prompt_template_service.clear_cache()
        logging.info(f"Prompt template cache cleared after updating: {template.name}")
        
        return PromptTemplateResponse(
            id=template.id, name=template.name, description=template.description,
            system_prompt=template.system_prompt, user_prompt=template.user_prompt,
            use_case=template.use_case, agent_role=template.agent_role, is_active=template.is_active,
            created_at=template.created_at, updated_at=template.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error updating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update prompt template: {str(e)}")


@router.delete("/prompt-templates/{template_id}")
async def delete_prompt_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a prompt template."""
    try:
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
        template_name = template.name
        await db.delete(template)
        await db.commit()
        
        await log_system_action(db, None, None, "delete_prompt_template", "admin", f"Deleted prompt template: {template_name}")
        
        # Clear cache so deleted template is removed immediately
        prompt_template_service.clear_cache()
        logging.info(f"Prompt template cache cleared after deleting: {template_name}")
        
        return {"success": True, "message": "Prompt template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete prompt template: {str(e)}")


@router.get("/prompt-templates/use-cases")
async def get_prompt_use_cases():
    """Get available use cases for prompt templates."""
    return [
        {"id": "report", "name": "Report Generation", "description": "Templates for generating reports"},
        {"id": "analysis", "name": "Data Analysis", "description": "Templates for analyzing data"},
        {"id": "summary", "name": "Summary", "description": "Templates for creating summaries"},
        {"id": "insights", "name": "Insights", "description": "Templates for extracting insights"},
        {"id": "custom", "name": "Custom", "description": "Custom use case templates"}
    ]


@router.get("/prompt-templates/cache-status")
async def get_prompt_template_cache_status():
    """Get prompt template cache status for debugging."""
    return prompt_template_service.get_cache_info()


# =============================================================================
# SYSTEM LOGS
# =============================================================================

async def log_system_action(db: AsyncSession, user_id: str = None, user_email: str = None, 
                           action: str = None, module: str = None, details: str = None,
                           ip_address: str = None, status: str = "success"):
    """Helper function to log system actions."""
    try:
        log = SystemLog(user_id=user_id, user_email=user_email, action=action, module=module, details=details, ip_address=ip_address, status=status)
        db.add(log)
        await db.commit()
    except Exception as e:
        logging.error(f"Error logging system action: {str(e)}")


@router.get("/system-logs")
async def get_system_logs(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    user_email: Optional[str] = None, action: Optional[str] = None,
    module: Optional[str] = None, status: Optional[str] = None,
    page: int = 1, page_size: int = 50, db: AsyncSession = Depends(get_db)
):
    """Get system logs with filtering."""
    try:
        query = select(SystemLog).order_by(SystemLog.created_at.desc())
        
        if start_date:
            query = query.where(SystemLog.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.where(SystemLog.created_at <= datetime.fromisoformat(end_date))
        if user_email:
            query = query.where(SystemLog.user_email.like(f"%{user_email}%"))
        if action:
            query = query.where(SystemLog.action == action)
        if module:
            query = query.where(SystemLog.module == module)
        if status:
            query = query.where(SystemLog.status == status)
        
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return {
            "logs": [
                SystemLogResponse(
                    id=log.id, user_id=log.user_id, user_email=log.user_email,
                    action=log.action, module=log.module, details=log.details,
                    ip_address=log.ip_address, status=log.status, created_at=log.created_at
                ) for log in logs
            ],
            "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except Exception as e:
        logging.error(f"Error fetching system logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system logs: {str(e)}")


@router.get("/system-logs/actions")
async def get_log_actions(db: AsyncSession = Depends(get_db)):
    """Get unique action types from logs."""
    try:
        result = await db.execute(select(SystemLog.action).distinct().where(SystemLog.action.isnot(None)))
        actions = [row[0] for row in result.all() if row[0]]
        return actions if actions else ["login", "logout", "chat", "config_update", "create", "update", "delete"]
    except Exception as e:
        logging.error(f"Error fetching log actions: {str(e)}")
        return ["login", "logout", "chat", "config_update", "create", "update", "delete"]


@router.get("/system-logs/modules")
async def get_log_modules(db: AsyncSession = Depends(get_db)):
    """Get unique modules from logs."""
    try:
        result = await db.execute(select(SystemLog.module).distinct().where(SystemLog.module.isnot(None)))
        modules = [row[0] for row in result.all() if row[0]]
        return modules if modules else ["auth", "chat", "admin", "smtp", "llm", "system"]
    except Exception as e:
        logging.error(f"Error fetching log modules: {str(e)}")
        return ["auth", "chat", "admin", "smtp", "llm", "system"]


@router.get("/system-logs/stats")
async def get_log_stats(db: AsyncSession = Depends(get_db)):
    """Get log statistics."""
    try:
        total = (await db.execute(select(func.count(SystemLog.id)))).scalar()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = (await db.execute(select(func.count(SystemLog.id)).where(SystemLog.created_at >= today))).scalar()
        success_count = (await db.execute(select(func.count(SystemLog.id)).where(SystemLog.status == "success"))).scalar()
        failure_count = (await db.execute(select(func.count(SystemLog.id)).where(SystemLog.status == "failure"))).scalar()
        
        return {"total_logs": total, "logs_today": today_count, "success_count": success_count, "failure_count": failure_count}
    except Exception as e:
        logging.error(f"Error fetching log stats: {str(e)}")
        return {"total_logs": 0, "logs_today": 0, "success_count": 0, "failure_count": 0}


# =============================================================================
# SYSTEM PREFERENCES
# =============================================================================

@router.get("/system-preferences")
async def get_system_preferences(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Get all system preferences."""
    try:
        query = select(SystemPreference).order_by(SystemPreference.category, SystemPreference.key)
        if category:
            query = query.where(SystemPreference.category == category)
        
        result = await db.execute(query)
        prefs = result.scalars().all()
        
        return [
            SystemPreferenceResponse(
                id=p.id, key=p.key, value=p.value, data_type=p.data_type,
                category=p.category, description=p.description,
                created_at=p.created_at, updated_at=p.updated_at
            ) for p in prefs
        ]
    except Exception as e:
        logging.error(f"Error fetching system preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system preferences: {str(e)}")


@router.post("/system-preferences", response_model=SystemPreferenceResponse)
async def create_or_update_preference(request: SystemPreferenceRequest, db: AsyncSession = Depends(get_db)):
    """Create or update a system preference."""
    try:
        result = await db.execute(select(SystemPreference).where(SystemPreference.key == request.key))
        pref = result.scalar_one_or_none()
        
        if pref:
            pref.value = request.value
            pref.data_type = request.data_type
            pref.category = request.category
            pref.description = request.description
            pref.updated_at = datetime.utcnow()
        else:
            pref = SystemPreference(
                key=request.key, value=request.value, data_type=request.data_type,
                category=request.category, description=request.description
            )
            db.add(pref)
        
        await db.commit()
        await db.refresh(pref)
        
        await log_system_action(db, None, None, "update_preference", "system", f"Updated preference: {request.key}")
        
        return SystemPreferenceResponse(
            id=pref.id, key=pref.key, value=pref.value, data_type=pref.data_type,
            category=pref.category, description=pref.description,
            created_at=pref.created_at, updated_at=pref.updated_at
        )
    except Exception as e:
        await db.rollback()
        logging.error(f"Error saving system preference: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save system preference: {str(e)}")


@router.post("/system-preferences/bulk")
async def bulk_update_preferences(request: BulkPreferenceRequest, db: AsyncSession = Depends(get_db)):
    """Bulk update system preferences."""
    try:
        updated = []
        for pref_req in request.preferences:
            result = await db.execute(select(SystemPreference).where(SystemPreference.key == pref_req.key))
            pref = result.scalar_one_or_none()
            
            if pref:
                pref.value = pref_req.value
                pref.data_type = pref_req.data_type
                pref.category = pref_req.category
                pref.description = pref_req.description
                pref.updated_at = datetime.utcnow()
            else:
                pref = SystemPreference(
                    key=pref_req.key, value=pref_req.value, data_type=pref_req.data_type,
                    category=pref_req.category, description=pref_req.description
                )
                db.add(pref)
            
            updated.append(pref_req.key)
        
        await db.commit()
        await log_system_action(db, None, None, "bulk_update_preferences", "system", f"Updated {len(updated)} preferences")
        
        return {"success": True, "message": f"Updated {len(updated)} preferences", "updated_keys": updated}
    except Exception as e:
        await db.rollback()
        logging.error(f"Error bulk updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk update preferences: {str(e)}")


@router.delete("/system-preferences/{pref_key}")
async def delete_preference(pref_key: str, db: AsyncSession = Depends(get_db)):
    """Delete a system preference."""
    try:
        result = await db.execute(select(SystemPreference).where(SystemPreference.key == pref_key))
        pref = result.scalar_one_or_none()
        
        if not pref:
            raise HTTPException(status_code=404, detail="Preference not found")
        
        await db.delete(pref)
        await db.commit()
        
        return {"success": True, "message": "Preference deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting preference: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete preference: {str(e)}")


@router.get("/system-preferences/categories")
async def get_preference_categories():
    """Get available preference categories."""
    return [
        {"id": "general", "name": "General", "description": "General system settings"},
        {"id": "chat", "name": "Chat", "description": "Chat and AI settings"},
        {"id": "reports", "name": "Reports", "description": "Report generation settings"},
        {"id": "notifications", "name": "Notifications", "description": "Notification settings"},
        {"id": "security", "name": "Security", "description": "Security and access settings"},
        {"id": "appearance", "name": "Appearance", "description": "UI and appearance settings"}
    ]


@router.post("/system-preferences/initialize")
async def initialize_default_preferences(db: AsyncSession = Depends(get_db)):
    """Initialize default system preferences."""
    default_prefs = [
        {"key": "app_name", "value": "Reporting Agent", "data_type": "string", "category": "general", "description": "Application name displayed in UI"},
        {"key": "maintenance_mode", "value": "false", "data_type": "boolean", "category": "general", "description": "Enable maintenance mode"},
        {"key": "max_chat_history", "value": "100", "data_type": "number", "category": "chat", "description": "Maximum chat messages to retain"},
        {"key": "enable_chat_export", "value": "true", "data_type": "boolean", "category": "chat", "description": "Allow users to export chat history"},
        {"key": "default_report_format", "value": "pdf", "data_type": "string", "category": "reports", "description": "Default report export format"},
        {"key": "enable_email_notifications", "value": "true", "data_type": "boolean", "category": "notifications", "description": "Enable email notifications"},
        {"key": "session_timeout", "value": "60", "data_type": "number", "category": "security", "description": "Session timeout in minutes"},
        {"key": "enable_dark_mode", "value": "false", "data_type": "boolean", "category": "appearance", "description": "Enable dark mode by default"},
    ]
    
    try:
        created = 0
        for pref_data in default_prefs:
            result = await db.execute(select(SystemPreference).where(SystemPreference.key == pref_data["key"]))
            existing = result.scalar_one_or_none()
            
            if not existing:
                pref = SystemPreference(**pref_data)
                db.add(pref)
                created += 1
        
        await db.commit()
        return {"success": True, "message": f"Initialized {created} default preferences"}
    except Exception as e:
        await db.rollback()
        logging.error(f"Error initializing preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize preferences: {str(e)}")


# =============================================================================
# SEMANTIC LAYER (VANNA) MANAGEMENT
# =============================================================================

@router.get("/semantic-layer/status")
async def get_semantic_layer_status():
    """Get Vanna semantic layer status and training info."""
    try:
        from config import VANNA_ENABLED
        
        if not VANNA_ENABLED:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Vanna semantic layer is disabled (VANNA_ENABLED=false)",
                "training_status": None
            }
        
        from services.semantic_layer import get_vanna_client, is_vanna_ready
        
        vn = await get_vanna_client()
        if vn is None:
            return {
                "enabled": True,
                "status": "not_initialized",
                "message": "Vanna client not initialized",
                "training_status": None
            }
        
        is_ready = await is_vanna_ready()
        training_status = vn.get_training_status()
        
        return {
            "enabled": True,
            "status": "ready" if is_ready else "not_trained",
            "message": "Semantic layer is ready" if is_ready else "Semantic layer needs training",
            "is_db_connected": training_status.get('is_db_connected', False),
            "training_status": {
                "is_trained": training_status.get('is_trained', False),
                "total_entries": training_status.get('total_entries', 0),
                "ddl_count": training_status.get('ddl_count', 0),
                "documentation_count": training_status.get('documentation_count', 0),
                "sql_count": training_status.get('sql_count', 0),
            }
        }
    except Exception as e:
        logging.error(f"Error getting semantic layer status: {e}")
        return {
            "enabled": True,
            "status": "error",
            "message": str(e),
            "training_status": None
        }


@router.post("/semantic-layer/test")
async def test_semantic_query(question: str):
    """Test a semantic query without affecting chat."""
    try:
        from config import VANNA_ENABLED
        
        if not VANNA_ENABLED:
            raise HTTPException(status_code=400, detail="Vanna semantic layer is disabled")
        
        from services.semantic_layer import (
            get_vanna_client, 
            is_vanna_ready,
            sql_validator,
            result_formatter,
            query_router,
        )
        
        if not await is_vanna_ready():
            raise HTTPException(status_code=400, detail="Vanna is not trained. Run training scripts first.")
        
        vn = await get_vanna_client()
        
        # Get routing info
        routing_info = query_router.get_routing_info(question)
        
        # Generate SQL
        sql_result = vn.generate_sql_safe(question)
        
        if not sql_result.get('success'):
            return {
                "success": False,
                "question": question,
                "routing": routing_info,
                "error": sql_result.get('error'),
                "sql": None,
                "data": None
            }
        
        sql = sql_result.get('sql')
        
        # Validate SQL
        is_valid, sanitized_sql, error = sql_validator.validate_and_sanitize(sql)
        
        if not is_valid:
            return {
                "success": False,
                "question": question,
                "routing": routing_info,
                "error": f"SQL validation failed: {error}",
                "sql": sql,
                "sanitized_sql": None,
                "data": None
            }
        
        # Execute SQL
        try:
            df = vn.run_sql(sanitized_sql)
            formatted = result_formatter.format_for_llm(df, sanitized_sql, question)
            
            return {
                "success": True,
                "question": question,
                "routing": routing_info,
                "sql": sql,
                "sanitized_sql": sanitized_sql,
                "row_count": len(df),
                "columns": list(df.columns),
                "data_preview": df.head(20).to_dict(orient='records'),
                "summary": formatted.get('summary'),
                "chart_suggestion": formatted.get('chart_suggestion'),
            }
        except Exception as e:
            return {
                "success": False,
                "question": question,
                "routing": routing_info,
                "error": f"SQL execution failed: {str(e)}",
                "sql": sql,
                "sanitized_sql": sanitized_sql,
                "data": None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error testing semantic query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic-layer/routing-test")
async def test_query_routing(question: str):
    """Test query routing classification without executing."""
    try:
        from config import VANNA_ENABLED
        
        if not VANNA_ENABLED:
            raise HTTPException(status_code=400, detail="Vanna semantic layer is disabled")
        
        from services.semantic_layer import query_router
        
        routing_info = query_router.get_routing_info(question)
        
        return {
            "question": question,
            "routing": routing_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error testing query routing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
