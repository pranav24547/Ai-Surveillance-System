"""
SMS Alert Handler using Twilio
"""
import asyncio
from typing import Optional, List
from datetime import datetime


class SMSHandler:
    """Handles SMS notifications via Twilio"""
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: List[str]
    ):
        """
        Initialize SMS handler
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Sender phone number
            to_numbers: List of recipient phone numbers
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_numbers = to_numbers
        self.client = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize Twilio client"""
        if not self.account_sid or not self.auth_token:
            print("⚠️ SMS: Twilio credentials not configured")
            return False
            
        try:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            self._initialized = True
            print("✅ SMS handler initialized")
            return True
        except ImportError:
            print("❌ Twilio library not installed. Run: pip install twilio")
            return False
        except Exception as e:
            print(f"❌ SMS initialization error: {e}")
            return False
    
    async def send_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str = "Camera 1",
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Send SMS alert for weapon detection
        
        Args:
            weapon_type: Type of weapon detected
            confidence: Detection confidence score
            location: Camera/location identifier
            timestamp: Detection timestamp
            
        Returns:
            True if all messages sent successfully
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        timestamp = timestamp or datetime.now()
        
        message_body = (
            f"🚨 SECURITY ALERT 🚨\n"
            f"Weapon Detected: {weapon_type.upper()}\n"
            f"Confidence: {confidence:.1%}\n"
            f"Location: {location}\n"
            f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Immediate action required!"
        )
        
        success = True
        
        for to_number in self.to_numbers:
            try:
                # Run in executor to not block async loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.client.messages.create(
                        body=message_body,
                        from_=self.from_number,
                        to=to_number
                    )
                )
                print(f"📱 SMS sent to {to_number}")
            except Exception as e:
                print(f"❌ Failed to send SMS to {to_number}: {e}")
                success = False
        
        return success
    
    def get_status(self) -> dict:
        """Get SMS handler status"""
        return {
            "enabled": self._initialized,
            "from_number": self.from_number,
            "recipient_count": len(self.to_numbers)
        }
