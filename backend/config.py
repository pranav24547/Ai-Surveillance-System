"""
Configuration management for Smart Surveillance System
"""
import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional


class DetectionConfig(BaseModel):
    model_path: str = "models/yolov8n.pt"
    confidence_threshold: float = 0.70
    classes: List[str] = ["gun", "knife", "rifle", "pistol"]


class VideoConfig(BaseModel):
    source: str | int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps: int = 30


class SMSConfig(BaseModel):
    enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    from_number: str = ""
    to_numbers: List[str] = []


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    sender_email: str = ""
    sender_password: str = ""
    recipients: List[str] = []


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_ids: List[str] = []


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    instance_id: str = ""
    token: str = ""
    phone_numbers: List[str] = []


class AlertsConfig(BaseModel):
    enabled: bool = True
    cooldown_seconds: int = 60
    sms: SMSConfig = SMSConfig()
    email: EmailConfig = EmailConfig()
    telegram: TelegramConfig = TelegramConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()


class StorageConfig(BaseModel):
    evidence_path: str = "data/evidence"
    max_evidence_files: int = 1000
    save_annotated_frames: bool = True


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class Config(BaseModel):
    detection: DetectionConfig = DetectionConfig()
    video: VideoConfig = VideoConfig()
    alerts: AlertsConfig = AlertsConfig()
    storage: StorageConfig = StorageConfig()
    server: ServerConfig = ServerConfig()


def load_config(config_path: str = None) -> Config:
    """Load configuration from YAML file"""
    # Try multiple paths
    possible_paths = [
        config_path,
        "config.yaml",
        "../config.yaml",  # When running from backend/
        Path(__file__).parent.parent / "config.yaml",  # Relative to this file
    ]
    
    for path in possible_paths:
        if path is None:
            continue
        config_file = Path(path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            print(f"📄 Loaded config from: {config_file.absolute()}")
            return Config(**config_data)
    
    print("⚠️ No config.yaml found, using defaults")
    return Config()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: str = "config.yaml") -> Config:
    """Reload configuration from file"""
    global _config
    _config = load_config(config_path)
    return _config
