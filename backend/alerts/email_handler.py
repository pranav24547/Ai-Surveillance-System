"""
Email Alert Handler using aiosmtplib
"""
import asyncio
from typing import Optional, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


class EmailHandler:
    """Handles Email notifications via SMTP"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipients: List[str],
        use_tls: bool = True
    ):
        """
        Initialize Email handler
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_password: Sender email password/app password
            recipients: List of recipient email addresses
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipients = recipients
        self.use_tls = use_tls
        self._initialized = False
        
    def initialize(self) -> bool:
        """Validate email configuration"""
        if not self.sender_email or not self.sender_password:
            print("⚠️ Email: Credentials not configured")
            return False
            
        if not self.recipients:
            print("⚠️ Email: No recipients configured")
            return False
            
        try:
            import aiosmtplib
            self._initialized = True
            print("✅ Email handler initialized")
            return True
        except ImportError:
            print("❌ aiosmtplib not installed. Run: pip install aiosmtplib")
            return False
    
    async def send_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str = "Camera 1",
        timestamp: Optional[datetime] = None,
        evidence_path: Optional[str] = None
    ) -> bool:
        """
        Send email alert for weapon detection
        
        Args:
            weapon_type: Type of weapon detected
            confidence: Detection confidence score
            location: Camera/location identifier
            timestamp: Detection timestamp
            evidence_path: Optional path to evidence image
            
        Returns:
            True if email sent successfully
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        import aiosmtplib
        
        timestamp = timestamp or datetime.now()
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(self.recipients)
        msg['Subject'] = f"🚨 SECURITY ALERT: {weapon_type.upper()} Detected"
        
        # HTML body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ff4444, #cc0000); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">🚨 SECURITY ALERT</h1>
                <p style="margin: 10px 0 0 0;">Immediate Attention Required</p>
            </div>
            
            <div style="padding: 20px; background: #f9f9f9; border: 1px solid #ddd;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold; width: 40%;">Weapon Type:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; color: #cc0000; font-weight: bold;">{weapon_type.upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Confidence:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{confidence:.1%}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">Location:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{location}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Timestamp:</td>
                        <td style="padding: 10px;">{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #333; color: white; padding: 15px; text-align: center; border-radius: 0 0 10px 10px;">
                <p style="margin: 0; font-size: 12px;">Smart Surveillance System - Automated Alert</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach evidence image if provided
        if evidence_path:
            evidence_file = Path(evidence_path)
            if evidence_file.exists():
                try:
                    with open(evidence_file, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{evidence_file.name}"'
                        )
                        msg.attach(part)
                except Exception as e:
                    print(f"⚠️ Could not attach evidence: {e}")
        
        try:
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=self.use_tls,
                username=self.sender_email,
                password=self.sender_password
            )
            print(f"📧 Email alert sent to {len(self.recipients)} recipient(s)")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get email handler status"""
        return {
            "enabled": self._initialized,
            "smtp_server": self.smtp_server,
            "sender": self.sender_email,
            "recipient_count": len(self.recipients)
        }
