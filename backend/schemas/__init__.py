"""
Pydantic schemas package.
Import all schemas here for easy access.
"""
from .base import UserResponse
from .chat import (
    ChatQuery, ChartData, TableData, ChatResponse,
    QuestionCategoryCreate, QuestionCategoryUpdate, QuestionCategoryResponse,
    SuggestedQuestionCreate, SuggestedQuestionUpdate, SuggestedQuestionResponse,
    DashboardCardCreate, DashboardCardUpdate, DashboardCardResponse
)
from .auth import LoginRequest
from .email import (
    SendEmailRequest, SendEmailWithPdfRequest, SendEmailResponse,
    SmtpConfigRequest, SmtpConfigResponse, SmtpTestRequest, SmtpTestResponse
)
from .admin import (
    LlmConfigRequest, LlmConfigResponse, LlmTestRequest, LlmTestResponse, LlmModelsResponse,
    PromptTemplateRequest, PromptTemplateResponse,
    SystemLogResponse, LogFilterRequest,
    SystemPreferenceRequest, SystemPreferenceResponse, BulkPreferenceRequest
)
