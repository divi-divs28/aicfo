"""
Email-related Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    attachment_filename: Optional[str] = None


class SendEmailWithPdfRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    pdf_base64: str
    pdf_filename: str


class SendEmailResponse(BaseModel):
    success: bool
    message: str


# SMTP Configuration schemas
class SmtpConfigRequest(BaseModel):
    provider: str  # gmail, outlook, office365, custom
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_name: Optional[str] = None
    from_email: str


class SmtpConfigResponse(BaseModel):
    id: str
    provider: str
    smtp_host: str
    smtp_port: int
    username: str
    use_tls: bool
    use_ssl: bool
    from_name: Optional[str]
    from_email: str
    is_active: bool
    is_verified: bool
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SmtpTestRequest(BaseModel):
    test_email: str


class SmtpTestResponse(BaseModel):
    success: bool
    message: str
