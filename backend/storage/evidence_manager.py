"""
Evidence Storage Manager
Handles saving and organizing detection evidence (images, videos, metadata)
"""
import os
import cv2
import json
import asyncio
import aiofiles
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class EvidenceRecord:
    """Metadata for a single evidence file"""
    id: str
    weapon_type: str
    confidence: float
    timestamp: str
    location: str
    image_path: str
    bbox: tuple
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceManager:
    """
    Manages evidence storage with automatic cleanup and metadata tracking
    """
    
    def __init__(
        self,
        base_path: str = "data/evidence",
        max_files: int = 1000,
        save_annotated: bool = True
    ):
        """
        Initialize Evidence Manager
        
        Args:
            base_path: Base directory for evidence storage
            max_files: Maximum number of evidence files to retain
            save_annotated: Whether to save annotated frames
        """
        self.base_path = Path(base_path)
        self.max_files = max_files
        self.save_annotated = save_annotated
        
        # Evidence tracking
        self._evidence_records: List[EvidenceRecord] = []
        self._metadata_file = self.base_path / "metadata.json"
        
        # Create directories
        self._init_storage()
        
    def _init_storage(self):
        """Initialize storage directories"""
        # Create main directories
        (self.base_path / "images").mkdir(parents=True, exist_ok=True)
        (self.base_path / "annotated").mkdir(parents=True, exist_ok=True)
        (self.base_path / "clips").mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self._load_metadata()
        
        print(f"📁 Evidence storage initialized at: {self.base_path.absolute()}")
    
    def _load_metadata(self):
        """Load existing metadata from file"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    data = json.load(f)
                    self._evidence_records = [
                        EvidenceRecord(**record) for record in data
                    ]
                print(f"📚 Loaded {len(self._evidence_records)} evidence records")
            except Exception as e:
                print(f"⚠️ Could not load metadata: {e}")
                self._evidence_records = []
    
    async def _save_metadata(self):
        """Save metadata to file"""
        try:
            data = [record.to_dict() for record in self._evidence_records]
            async with aiofiles.open(self._metadata_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            print(f"❌ Failed to save metadata: {e}")
    
    def _generate_id(self) -> str:
        """Generate unique evidence ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"EVD_{timestamp}"
    
    async def save_detection(
        self,
        frame: np.ndarray,
        annotated_frame: Optional[np.ndarray],
        weapon_type: str,
        confidence: float,
        bbox: tuple,
        location: str = "Camera 1"
    ) -> Optional[str]:
        """
        Save detection evidence
        
        Args:
            frame: Original frame
            annotated_frame: Frame with detection annotations
            weapon_type: Type of weapon detected
            confidence: Detection confidence
            bbox: Bounding box (x1, y1, x2, y2)
            location: Camera/location identifier
            
        Returns:
            Evidence ID if saved successfully
        """
        evidence_id = self._generate_id()
        timestamp = datetime.now()
        
        # File paths
        image_filename = f"{evidence_id}.jpg"
        image_path = self.base_path / "images" / image_filename
        
        try:
            # Save original frame
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: cv2.imwrite(str(image_path), frame)
            )
            
            # Save annotated frame if enabled
            annotated_path = None
            if self.save_annotated and annotated_frame is not None:
                annotated_filename = f"{evidence_id}_annotated.jpg"
                annotated_path = self.base_path / "annotated" / annotated_filename
                await loop.run_in_executor(
                    None,
                    lambda: cv2.imwrite(str(annotated_path), annotated_frame)
                )
            
            # Create evidence record
            record = EvidenceRecord(
                id=evidence_id,
                weapon_type=weapon_type,
                confidence=round(confidence, 3),
                timestamp=timestamp.isoformat(),
                location=location,
                image_path=str(image_path),
                bbox=bbox
            )
            
            self._evidence_records.append(record)
            
            # Save metadata
            await self._save_metadata()
            
            # Cleanup if needed
            await self._cleanup_old_evidence()
            
            print(f"💾 Evidence saved: {evidence_id}")
            return evidence_id
            
        except Exception as e:
            print(f"❌ Failed to save evidence: {e}")
            return None
    
    async def _cleanup_old_evidence(self):
        """Remove oldest evidence if exceeding max_files"""
        while len(self._evidence_records) > self.max_files:
            oldest = self._evidence_records.pop(0)
            
            # Delete files
            try:
                image_path = Path(oldest.image_path)
                if image_path.exists():
                    image_path.unlink()
                
                # Delete annotated version if exists
                annotated_path = self.base_path / "annotated" / f"{oldest.id}_annotated.jpg"
                if annotated_path.exists():
                    annotated_path.unlink()
                    
                print(f"🗑️ Cleaned up old evidence: {oldest.id}")
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")
        
        await self._save_metadata()
    
    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Get evidence record by ID"""
        for record in self._evidence_records:
            if record.id == evidence_id:
                return record
        return None
    
    def get_recent_evidence(
        self,
        limit: int = 20,
        weapon_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent evidence records
        
        Args:
            limit: Maximum records to return
            weapon_type: Optional filter by weapon type
        """
        records = self._evidence_records
        
        if weapon_type:
            records = [r for r in records if r.weapon_type == weapon_type]
        
        return [r.to_dict() for r in records[-limit:]][::-1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get evidence storage statistics"""
        stats = {
            "total_evidence": len(self._evidence_records),
            "storage_path": str(self.base_path.absolute()),
            "max_files": self.max_files,
            "by_weapon_type": {}
        }
        
        # Count by weapon type
        for record in self._evidence_records:
            weapon = record.weapon_type
            stats["by_weapon_type"][weapon] = stats["by_weapon_type"].get(weapon, 0) + 1
        
        # Calculate storage size
        total_size = 0
        for path in self.base_path.rglob("*.jpg"):
            total_size += path.stat().st_size
        stats["storage_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return stats
    
    def get_evidence_image(self, evidence_id: str, annotated: bool = False) -> Optional[bytes]:
        """
        Get evidence image bytes
        
        Args:
            evidence_id: Evidence ID
            annotated: Whether to return annotated version
        """
        record = self.get_evidence(evidence_id)
        if not record:
            return None
        
        if annotated:
            path = self.base_path / "annotated" / f"{evidence_id}_annotated.jpg"
        else:
            path = Path(record.image_path)
        
        if path.exists():
            with open(path, 'rb') as f:
                return f.read()
        
        return None
    
    async def clear_all(self) -> int:
        """Clear all evidence (use with caution)"""
        count = len(self._evidence_records)
        
        # Delete all files
        for record in self._evidence_records:
            try:
                Path(record.image_path).unlink(missing_ok=True)
                annotated = self.base_path / "annotated" / f"{record.id}_annotated.jpg"
                annotated.unlink(missing_ok=True)
            except:
                pass
        
        self._evidence_records.clear()
        await self._save_metadata()
        
        print(f"🗑️ Cleared {count} evidence records")
        return count
