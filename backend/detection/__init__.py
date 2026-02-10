"""
Detection module initialization
"""
from .detector import WeaponDetector, Detection
from .processor import VideoProcessor, FrameData, frame_to_jpeg, frame_to_base64

__all__ = [
    "WeaponDetector",
    "Detection", 
    "VideoProcessor",
    "FrameData",
    "frame_to_jpeg",
    "frame_to_base64"
]
