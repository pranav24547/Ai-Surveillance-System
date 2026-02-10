"""
WhatsApp Alert Handler - Send alerts via WhatsApp using UltraMsg API

Setup Instructions:
1. Go to https://ultramsg.com and sign up (free tier: 500 messages)
2. Create an instance and link your WhatsApp
3. Get your Instance ID and Token from the dashboard
4. Add recipient phone numbers (with country code, e.g., 919876543210)
"""
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class WhatsAppHandler:
    """
    Send alerts via WhatsApp using UltraMsg API
    
    Free tier: 500 messages
    Sign up at: https://ultramsg.com
    """
    
    def __init__(
        self,
        instance_id: str,
        token: str,
        phone_numbers: List[str]
    ):
        """
        Initialize WhatsApp handler
        
        Args:
            instance_id: UltraMsg instance ID
            token: UltraMsg API token
            phone_numbers: List of phone numbers with country code (e.g., "919876543210")
        """
        self.instance_id = instance_id
        self.token = token
        self.phone_numbers = phone_numbers
        self._initialized = False
        self._send_count = 0
        self.base_url = f"https://api.ultramsg.com/{instance_id}"
        
    def initialize(self) -> bool:
        """Initialize the handler"""
        if self.instance_id and self.token and self.phone_numbers:
            self._initialized = True
            print("✅ WhatsApp alerts initialized (UltraMsg)")
            return True
        print("⚠️ WhatsApp not configured (missing instance_id, token, or phone_numbers)")
        return False
    
    async def send_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str = "Camera 1",
        evidence_path: Optional[str] = None
    ) -> bool:
        """
        Send alert message via WhatsApp
        
        Args:
            weapon_type: Type of weapon detected
            confidence: Detection confidence score
            location: Camera/location identifier
            evidence_path: Optional path to evidence image
            
        Returns:
            True if sent successfully
        """
        if not self._initialized:
            return False
        
        # Create alert message with emojis
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"🚨 *WEAPON DETECTED!* 🚨\n\n"
            f"⚠️ *Type:* {weapon_type.upper()}\n"
            f"📊 *Confidence:* {confidence*100:.1f}%\n"
            f"📍 *Location:* {location}\n"
            f"🕐 *Time:* {timestamp}\n\n"
            f"_Smart Surveillance System Alert_"
        )
        
        success = True
        
        async with aiohttp.ClientSession() as session:
            for phone in self.phone_numbers:
                try:
                    url = f"{self.base_url}/messages/chat"
                    payload = {
                        "token": self.token,
                        "to": phone,
                        "body": message
                    }
                    
                    async with session.post(url, data=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("sent") == "true" or result.get("sent") == True:
                                self._send_count += 1
                                print(f"✅ WhatsApp alert sent to {phone}")
                            else:
                                print(f"⚠️ WhatsApp response: {result}")
                                success = False
                        else:
                            error = await response.text()
                            print(f"❌ WhatsApp error ({response.status}): {error}")
                            success = False
                    
                    # Send image if available
                    if evidence_path and Path(evidence_path).exists() and success:
                        await self._send_image(session, phone, evidence_path)
                    
                except Exception as e:
                    print(f"❌ WhatsApp send failed: {e}")
                    success = False
        
        return success
    
    async def _send_image(
        self,
        session: aiohttp.ClientSession,
        phone: str,
        image_path: str
    ) -> bool:
        """Send image to WhatsApp"""
        try:
            url = f"{self.base_url}/messages/image"
            
            # Read image and send as base64 or file URL
            # UltraMsg prefers URLs, but we'll use the caption for now
            payload = {
                "token": self.token,
                "to": phone,
                "caption": "📷 Detection Evidence"
            }
            
            # For local files, UltraMsg needs the image uploaded
            # This is a simplified version - in production, upload to cloud first
            async with session.post(url, data=payload) as response:
                return response.status == 200
                    
        except Exception as e:
            print(f"❌ Failed to send image: {e}")
            return False
    
    async def send_test(self) -> bool:
        """Send a test message"""
        return await self.send_alert(
            weapon_type="TEST",
            confidence=0.99,
            location="Test Location"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get handler status"""
        return {
            "enabled": self._initialized,
            "send_count": self._send_count,
            "phone_count": len(self.phone_numbers) if self.phone_numbers else 0
        }
