"""
Alert Manager - Coordinates all alert channels with cooldown logic
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

from .sms_handler import SMSHandler
from .email_handler import EmailHandler
from .telegram_handler import TelegramHandler
from .whatsapp_handler import WhatsAppHandler


@dataclass
class AlertRecord:
    """Record of a sent alert"""
    weapon_type: str
    confidence: float
    location: str
    timestamp: datetime
    channels: List[str]
    evidence_path: Optional[str] = None


class AlertManager:
    """
    Manages alert dispatching across multiple channels with cooldown logic
    to prevent alert fatigue.
    """
    
    def __init__(
        self,
        cooldown_seconds: int = 60,
        enabled: bool = True
    ):
        """
        Initialize Alert Manager
        
        Args:
            cooldown_seconds: Minimum time between alerts for same detection type
            enabled: Master switch for alerts
        """
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        
        self.sms_handler: Optional[SMSHandler] = None
        self.email_handler: Optional[EmailHandler] = None
        self.telegram_handler: Optional[TelegramHandler] = None
        self.whatsapp_handler: Optional[WhatsAppHandler] = None
        
        # Track last alert times by weapon type
        self._last_alerts: Dict[str, datetime] = {}
        
        # Alert history
        self._alert_history: List[AlertRecord] = []
        self._max_history = 100
        
    def configure_sms(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: List[str]
    ):
        """Configure SMS alerts"""
        self.sms_handler = SMSHandler(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            to_numbers=to_numbers
        )
        self.sms_handler.initialize()
        
    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipients: List[str],
        use_tls: bool = True
    ):
        """Configure email alerts"""
        self.email_handler = EmailHandler(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_email=sender_email,
            sender_password=sender_password,
            recipients=recipients,
            use_tls=use_tls
        )
        self.email_handler.initialize()
    
    def configure_telegram(
        self,
        bot_token: str,
        chat_ids: List[str]
    ):
        """Configure Telegram alerts (FREE & UNLIMITED)"""
        self.telegram_handler = TelegramHandler(
            bot_token=bot_token,
            chat_ids=chat_ids
        )
        self.telegram_handler.initialize()
    
    def configure_whatsapp(
        self,
        instance_id: str,
        token: str,
        phone_numbers: List[str]
    ):
        """Configure WhatsApp alerts (UltraMsg API)"""
        self.whatsapp_handler = WhatsAppHandler(
            instance_id=instance_id,
            token=token,
            phone_numbers=phone_numbers
        )
        self.whatsapp_handler.initialize()
    
    def _check_cooldown(self, weapon_type: str) -> bool:
        """
        Check if cooldown period has passed for weapon type
        
        Returns:
            True if alert can be sent, False if in cooldown
        """
        last_alert = self._last_alerts.get(weapon_type)
        
        if last_alert is None:
            return True
            
        elapsed = (datetime.now() - last_alert).total_seconds()
        return elapsed >= self.cooldown_seconds
    
    def _record_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str,
        channels: List[str],
        evidence_path: Optional[str] = None
    ):
        """Record an alert in history and update cooldown"""
        now = datetime.now()
        self._last_alerts[weapon_type] = now
        
        record = AlertRecord(
            weapon_type=weapon_type,
            confidence=confidence,
            location=location,
            timestamp=now,
            channels=channels,
            evidence_path=evidence_path
        )
        
        self._alert_history.append(record)
        
        # Trim history
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
    
    async def trigger_alert(
        self,
        weapon_type: str,
        confidence: float,
        location: str = "Camera 1",
        evidence_path: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger alerts across all configured channels
        
        Args:
            weapon_type: Type of weapon detected
            confidence: Detection confidence score
            location: Camera/location identifier
            evidence_path: Path to evidence image
            force: Bypass cooldown check
            
        Returns:
            Dict with alert status for each channel
        """
        result = {
            "triggered": False,
            "channels": {},
            "reason": None
        }
        
        if not self.enabled:
            result["reason"] = "alerts_disabled"
            return result
        
        # Check cooldown
        if not force and not self._check_cooldown(weapon_type):
            remaining = self.cooldown_seconds - (
                datetime.now() - self._last_alerts[weapon_type]
            ).total_seconds()
            result["reason"] = f"cooldown_active_{int(remaining)}s_remaining"
            return result
        
        successful_channels = []
        
        # Dispatch to all channels concurrently
        tasks = []
        
        if self.sms_handler and self.sms_handler._initialized:
            tasks.append(("sms", self.sms_handler.send_alert(
                weapon_type=weapon_type,
                confidence=confidence,
                location=location
            )))
        
        if self.email_handler and self.email_handler._initialized:
            tasks.append(("email", self.email_handler.send_alert(
                weapon_type=weapon_type,
                confidence=confidence,
                location=location,
                evidence_path=evidence_path
            )))
        
        if self.telegram_handler and self.telegram_handler._initialized:
            tasks.append(("telegram", self.telegram_handler.send_alert(
                weapon_type=weapon_type,
                confidence=confidence,
                location=location,
                evidence_path=evidence_path
            )))
        
        if self.whatsapp_handler and self.whatsapp_handler._initialized:
            tasks.append(("whatsapp", self.whatsapp_handler.send_alert(
                weapon_type=weapon_type,
                confidence=confidence,
                location=location,
                evidence_path=evidence_path
            )))
        
        # Execute all alerts
        for channel, task in tasks:
            try:
                success = await task
                result["channels"][channel] = success
                if success:
                    successful_channels.append(channel)
            except Exception as e:
                result["channels"][channel] = False
                print(f"❌ {channel} alert failed: {e}")
        
        # Always record the alert in history (even if no channels configured)
        result["triggered"] = True
        channels_used = successful_channels if successful_channels else ["log"]
        self._record_alert(
            weapon_type=weapon_type,
            confidence=confidence,
            location=location,
            channels=channels_used,
            evidence_path=evidence_path
        )
        
        if successful_channels:
            print(f"🚨 Alert triggered via: {', '.join(successful_channels)}")
        else:
            print(f"📝 Alert logged: {weapon_type} at {location}")
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get alert system status"""
        return {
            "enabled": self.enabled,
            "cooldown_seconds": self.cooldown_seconds,
            "sms": self.sms_handler.get_status() if self.sms_handler else {"enabled": False},
            "email": self.email_handler.get_status() if self.email_handler else {"enabled": False},
            "telegram": self.telegram_handler.get_status() if self.telegram_handler else {"enabled": False},
            "whatsapp": self.whatsapp_handler.get_status() if self.whatsapp_handler else {"enabled": False},
            "alert_count": len(self._alert_history)
        }
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        alerts = self._alert_history[-limit:]
        return [
            {
                "weapon_type": a.weapon_type,
                "confidence": a.confidence,
                "location": a.location,
                "timestamp": a.timestamp.isoformat(),
                "channels": a.channels,
                "evidence_path": a.evidence_path
            }
            for a in reversed(alerts)
        ]
    
    def reset_cooldown(self, weapon_type: Optional[str] = None):
        """Reset cooldown for specific weapon type or all"""
        if weapon_type:
            self._last_alerts.pop(weapon_type, None)
        else:
            self._last_alerts.clear()
        print(f"🔄 Alert cooldown reset for: {weapon_type or 'all'}")
