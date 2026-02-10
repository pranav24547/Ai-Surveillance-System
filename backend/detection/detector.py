"""
YOLOv8 Weapon Detection Module
"""
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ultralytics import YOLO


@dataclass
class Detection:
    """Represents a single weapon detection"""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    timestamp: datetime
    frame_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox,
            "timestamp": self.timestamp.isoformat(),
            "frame_id": self.frame_id
        }


class WeaponDetector:
    """YOLOv8-based weapon detection system"""
    
    # Class mapping for weapon detection
    WEAPON_CLASSES = {
        0: "gun",
        1: "knife", 
        2: "rifle",
        3: "pistol"
    }
    
    def __init__(
        self,
        model_path: str = "models/yolov8n.pt",
        confidence_threshold: float = 0.70,
        target_classes: Optional[List[str]] = None,
        detection_cooldown: int = 30  # Frames between alerts (30 frames = ~1 sec at 30fps)
    ):
        """
        Initialize the weapon detector
        
        Args:
            model_path: Path to YOLOv8 model weights
            confidence_threshold: Minimum confidence for detections
            target_classes: List of class names to detect
            detection_cooldown: Frames to wait between detections of same class
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.target_classes = target_classes or list(self.WEAPON_CLASSES.values())
        self.model: Optional[YOLO] = None
        self.frame_count = 0
        self.detection_cooldown = detection_cooldown
        self.last_detection_frame: Dict[str, int] = {}  # Track last detection per class
        
    def load_model(self) -> bool:
        """Load the YOLOv8 model"""
        try:
            model_file = Path(self.model_path)
            
            if model_file.exists():
                # Load custom trained model
                self.model = YOLO(str(model_file))
                print(f"✅ Loaded custom model from {self.model_path}")
            else:
                # Use pre-trained YOLOv8 model (will detect general objects)
                # For weapon detection, you'd train on weapon dataset
                self.model = YOLO("yolov8n.pt")
                print("⚠️ Custom model not found, using pre-trained YOLOv8n")
                print("   For weapon detection, train on a weapon dataset")
                
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect weapons in a frame
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            List of Detection objects
        """
        if self.model is None:
            if not self.load_model():
                return []
        
        self.frame_count += 1
        detections = []
        
        # Run inference
        results = self.model(frame, verbose=False)
        
        for result in results:
            boxes = result.boxes
            
            if boxes is None:
                continue
                
            for box in boxes:
                confidence = float(box.conf[0])
                
                # Check confidence threshold
                if confidence < self.confidence_threshold:
                    continue
                
                class_id = int(box.cls[0])
                class_name = result.names.get(class_id, "unknown")
                
                # For demo purposes, map common objects to weapons
                # In production, use a model trained on weapon dataset
                weapon_mapping = {
                    "cell phone": "gun",  # Demo mapping
                    "remote": "gun",
                    "scissors": "knife",
                    "knife": "knife",
                    "baseball bat": "rifle",
                    "sports ball": "gun",  # Demo
                    "bottle": "gun",  # Demo - elongated objects
                    "umbrella": "rifle",  # Demo
                    "handbag": "gun",  # Demo  
                    "suitcase": "gun",  # Demo
                }
                
                # Also detect persons - useful for surveillance
                # In a real system, you'd combine person + weapon detection
                person_alert = False
                if class_name == "person" and confidence > 0.5:
                    # Flag any high-confidence person detection
                    person_alert = True
                
                # Check if it's a known weapon or mapped class
                if class_name in self.target_classes:
                    detected_class = class_name
                elif class_name in weapon_mapping:
                    detected_class = weapon_mapping[class_name]
                elif person_alert:
                    detected_class = "person_detected"
                else:
                    continue
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                detection = Detection(
                    class_name=detected_class,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    timestamp=datetime.now(),
                    frame_id=self.frame_count
                )
                detections.append(detection)
        
        # Apply cooldown at batch level - only return detections if cooldown expired
        if detections:
            last_alert_frame = self.last_detection_frame.get("_any_", 0)
            if self.frame_count - last_alert_frame >= self.detection_cooldown:
                self.last_detection_frame["_any_"] = self.frame_count
                return detections  # Return all detections
            else:
                return []  # In cooldown, return empty
        
        return detections
    
    def annotate_frame(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        Draw detection boxes and labels on frame
        
        Args:
            frame: Original frame
            detections: List of detections to draw
            show_confidence: Whether to show confidence scores
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Color scheme for different weapons
        colors = {
            "gun": (0, 0, 255),      # Red
            "knife": (0, 165, 255),   # Orange
            "rifle": (0, 0, 200),     # Dark Red
            "pistol": (0, 100, 255),  # Red-Orange
        }
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = colors.get(det.class_name, (0, 255, 0))
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            
            # Prepare label
            label = f"⚠️ {det.class_name.upper()}"
            if show_confidence:
                label += f" {det.confidence:.1%}"
            
            # Draw label background
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
            )
            cv2.rectangle(
                annotated,
                (x1, y1 - label_h - 10),
                (x1 + label_w + 10, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
            
            # Add warning overlay
            overlay = annotated.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.1, annotated, 0.9, 0, annotated)
        
        # Add detection count if any weapons found
        if detections:
            warning_text = f"🚨 WEAPON DETECTED: {len(detections)}"
            cv2.putText(
                annotated,
                warning_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )
        
        return annotated
    
    def update_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        print(f"📊 Confidence threshold updated to {self.confidence_threshold:.0%}")
