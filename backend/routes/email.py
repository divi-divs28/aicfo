"""
Email routes.
Send emails with optional PDF attachments.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from schemas.email import SendEmailRequest, SendEmailWithPdfRequest, SendEmailResponse
from services.email_service import email_service

router = APIRouter()


@router.post("/send-email", response_model=SendEmailResponse)
async def send_email_endpoint(request: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    """
    Send email with optional PDF attachment.
    
    - to_email: Recipient email address
    - subject: Email subject
    - body: Email body (plain text)
    - attachment_filename: Optional PDF filename
    """
    try:
        logging.info(f"Sending email to: {request.to_email}, Subject: {request.subject}")
        
        result = await email_service.send_email(
            db=db,
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            attachment_filename=request.attachment_filename
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return SendEmailResponse(success=True, message=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in send_email_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/send-email-with-pdf", response_model=SendEmailResponse)
async def send_email_with_pdf_endpoint(request: SendEmailWithPdfRequest, db: AsyncSession = Depends(get_db)):
    """
    Send email with base64 encoded PDF attachment.
    Uses database SMTP config if available, otherwise falls back to environment variables.
    """
    try:
        logging.info(f"Sending email with PDF to: {request.to_email}, Subject: {request.subject}, Filename: {request.pdf_filename}")
        
        result = await email_service.send_email_with_pdf(
            db=db,
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            pdf_base64=request.pdf_base64,
            pdf_filename=request.pdf_filename
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return SendEmailResponse(success=True, message=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in send_email_with_pdf_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
