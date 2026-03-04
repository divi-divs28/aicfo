"""
Admin/Configuration Pydantic schemas.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# LLM Configuration schemas
class LlmConfigRequest(BaseModel):
    provider: str  # openai, anthropic, google, local_llm, etc.
    api_key: Optional[str] = None
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    # Local LLM specific fields
    local_llm_url: Optional[str] = None
    local_llm_stream: bool = False
    # Activation flag - if True, this config will be used for chat
    activate: bool = True


class LlmConfigResponse(BaseModel):
    id: str
    provider: str
    api_key: Optional[str] = None  # Include for form prefilling
    model: str
    temperature: float
    max_tokens: int
    local_llm_url: Optional[str] = None
    local_llm_stream: Optional[bool] = False
    is_active: bool
    is_verified: bool
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class LlmTestRequest(BaseModel):
    prompt: str = "Say hello in one sentence."
    # Optional: test with these credentials instead of active DB config
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    local_llm_url: Optional[str] = None
    local_llm_stream: bool = False


class LlmTestResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None


class LlmModelsResponse(BaseModel):
    success: bool
    models: List[dict]
    message: Optional[str] = None


# Prompt Template schemas
class PromptTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt: Optional[str] = None
    use_case: Optional[str] = "custom"
    agent_role: Optional[str] = None
    is_active: bool = True


class PromptTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    user_prompt: Optional[str]
    use_case: Optional[str]
    agent_role: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# System Log schemas
class SystemLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    module: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime


class LogFilterRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    user_email: Optional[str] = None
    action: Optional[str] = None
    module: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 50


# System Preference schemas
class SystemPreferenceRequest(BaseModel):
    key: str
    value: str
    data_type: str = "string"
    category: str = "general"
    description: Optional[str] = None


class SystemPreferenceResponse(BaseModel):
    id: str
    key: str
    value: Optional[str]
    data_type: str
    category: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class BulkPreferenceRequest(BaseModel):
    preferences: List[SystemPreferenceRequest]
