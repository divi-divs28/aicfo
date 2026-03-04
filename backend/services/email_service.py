"""
Email Service.
Handles email sending functionality via SMTP.
"""
import os
import logging
import smtplib
import base64
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.admin import SmtpConfiguration
from config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.default_smtp_host = SMTP_HOST
        self.default_smtp_port = SMTP_PORT
        self.default_smtp_username = SMTP_USERNAME
        self.default_smtp_password = SMTP_PASSWORD
        self.default_from_email = SMTP_FROM_EMAIL
    
    async def get_smtp_config(self, db: AsyncSession) -> Optional[SmtpConfiguration]:
        """Get active SMTP configuration from database."""
        try:
            result = await db.execute(
                select(SmtpConfiguration)
                .where(SmtpConfiguration.is_active == True)
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"Error fetching SMTP config: {str(e)}")
            return None
    
    def _get_smtp_settings(self, smtp_config: Optional[SmtpConfiguration] = None) -> dict:
        """Get SMTP settings from config or environment."""
        if smtp_config:
            return {
                'host': smtp_config.smtp_host,
                'port': smtp_config.smtp_port,
                'username': smtp_config.username,
                'password': smtp_config.password,
                'from_email': smtp_config.from_email,
                'from_name': smtp_config.from_name,
                'use_tls': smtp_config.use_tls,
                'use_ssl': smtp_config.use_ssl
            }
        else:
            return {
                'host': self.default_smtp_host,
                'port': self.default_smtp_port,
                'username': self.default_smtp_username,
                'password': self.default_smtp_password,
                'from_email': self.default_from_email,
                'from_name': None,
                'use_tls': True,
                'use_ssl': False
            }
    
    async def send_email(
        self, 
        db: AsyncSession,
        to_email: str, 
        subject: str, 
        body: str,
        attachment_filename: Optional[str] = None
    ) -> dict:
        """Send a plain text email."""
        try:
            smtp_config = await self.get_smtp_config(db)
            settings = self._get_smtp_settings(smtp_config)
            
            if not settings['username'] or not settings['password']:
                return {"success": False, "message": "SMTP not configured. Please configure email settings in Admin Panel."}
            
            msg = MIMEMultipart()
            msg['From'] = f"{settings['from_name']} <{settings['from_email']}>" if settings['from_name'] else settings['from_email']
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(settings['host'], settings['port']) as server:
                if settings['use_tls']:
                    server.starttls()
                server.login(settings['username'], settings['password'])
                server.send_message(msg)
            
            return {"success": True, "message": f"Email sent successfully to {to_email}"}
            
        except Exception as e:
            logging.error(f"Error sending email: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_email_with_pdf(
        self, 
        db: AsyncSession,
        to_email: str, 
        subject: str, 
        body: str,
        pdf_base64: str,
        pdf_filename: str
    ) -> dict:
        """Send an email with PDF attachment."""
        try:
            smtp_config = await self.get_smtp_config(db)
            settings = self._get_smtp_settings(smtp_config)
            
            if not settings['username'] or not settings['password']:
                return {"success": False, "message": "SMTP not configured. Please configure email settings in Admin Panel."}
            
            msg = MIMEMultipart()
            msg['From'] = f"{settings['from_name']} <{settings['from_email']}>" if settings['from_name'] else settings['from_email']
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Decode and attach PDF
            pdf_data = base64.b64decode(pdf_base64)
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(pdf_data)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
            msg.attach(attachment)
            
            with smtplib.SMTP(settings['host'], settings['port']) as server:
                if settings['use_tls']:
                    server.starttls()
                server.login(settings['username'], settings['password'])
                server.send_message(msg)
            
            return {"success": True, "message": f"Email with attachment sent successfully to {to_email}"}
            
        except Exception as e:
            logging.error(f"Error sending email with PDF: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def test_smtp_connection(
        self, 
        db: AsyncSession,
        test_email: str
    ) -> dict:
        """Test SMTP connection by sending a test email."""
        return await self.send_email(
            db=db,
            to_email=test_email,
            subject="Asset Manager - SMTP Test",
            body="This is a test email from Asset Manager to verify your SMTP configuration is working correctly."
        )


# Singleton instance
email_service = EmailService()
