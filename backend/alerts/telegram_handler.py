"""
Telegram Alert Handler - Free unlimited alerts via Telegram Bot
"""
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class TelegramHandler:
    """
    Send alerts via Telegram Bot API (FREE & UNLIMITED)
    
    Setup:
    1. Open Telegram and search for @BotFather
    2. Send /newbot and follow prompts
    3. Copy the API token
    4. Start chat with your bot and send any message
    5. Get chat ID from: https://api.telegram.org/bot<TOKEN>/getUpdates
    """
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(
        self,
        bot_token: str,
        chat_ids: List[str]
    ):
        """
        Initialize Telegram handler
        
        Args:
            bot_token: Telegram Bot API token from @BotFather
            chat_ids: List of chat IDs to send alerts to
        """
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self._initialized = False
        self._send_count = 0
        
    def initialize(self) -> bool:
        """Initialize the handler"""
        if self.bot_token and self.chat_ids:
            self._initialized = True
            print("✅ Telegram alerts initialized")
            return True
        print("⚠️ Telegram not configured (missing token or chat_ids)")
        return False
    
    async def send_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str = "Camera 1",
        evidence_path: Optional[str] = None
    ) -> bool:
        """
        Send alert message via Telegram
        
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
            f"🚨 <b>WEAPON DETECTED!</b> 🚨\n\n"
            f"⚠️ <b>Type:</b> {weapon_type.upper()}\n"
            f"📊 <b>Confidence:</b> {confidence*100:.1f}%\n"
            f"📍 <b>Location:</b> {location}\n"
            f"🕐 <b>Time:</b> {timestamp}\n\n"
            f"<i>Smart Surveillance System Alert</i>"
        )
        
        success = True
        
        async with aiohttp.ClientSession() as session:
            for chat_id in self.chat_ids:
                try:
                    # Send text message first
                    url = f"{self.BASE_URL}{self.bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }
                    
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            error = await response.text()
                            print(f"❌ Telegram error: {error}")
                            success = False
                            continue
                    
                    # Send image if available
                    if evidence_path and Path(evidence_path).exists():
                        await self._send_photo(session, chat_id, evidence_path)
                    
                    self._send_count += 1
                    print(f"✅ Telegram alert sent to {chat_id}")
                    
                except Exception as e:
                    print(f"❌ Telegram send failed: {e}")
                    success = False
        
        return success
    
    async def _send_photo(
        self,
        session: aiohttp.ClientSession,
        chat_id: str,
        photo_path: str
    ) -> bool:
        """Send photo to Telegram"""
        try:
            url = f"{self.BASE_URL}{self.bot_token}/sendPhoto"
            
            with open(photo_path, 'rb') as photo:
                data = aiohttp.FormData()
                data.add_field('chat_id', chat_id)
                data.add_field('photo', photo, filename='evidence.jpg')
                data.add_field('caption', '📷 Detection Evidence')
                
                async with session.post(url, data=data) as response:
                    return response.status == 200
                    
        except Exception as e:
            print(f"❌ Failed to send photo: {e}")
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
            "chat_count": len(self.chat_ids) if self.chat_ids else 0
        }
