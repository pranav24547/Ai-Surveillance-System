"""
Video Frame Processing Pipeline
"""
import cv2
import time
import asyncio
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, AsyncGenerator, Tuple
from dataclasses import dataclass
import threading
from queue import Queue


@dataclass
class FrameData:
    """Container for processed frame data"""
    frame: np.ndarray
    timestamp: datetime
    frame_id: int
    fps: float


class VideoProcessor:
    """Handles video input from various sources"""
    
    def __init__(
        self,
        source: str | int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        target_fps: int = 30
    ):
        """
        Initialize video processor
        
        Args:
            source: Video source (0 for webcam, path for file, URL for RTSP)
            frame_width: Target frame width
            frame_height: Target frame height
            target_fps: Target frames per second
        """
        self.source = source
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_count = 0
        self.start_time: Optional[float] = None
        self.current_fps = 0.0
        
        # Threading for async frame reading
        self.frame_queue: Queue = Queue(maxsize=10)
        self.read_thread: Optional[threading.Thread] = None
        
    def open(self) -> bool:
        """Open the video source"""
        try:
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                print(f"❌ Failed to open video source: {self.source}")
                return False
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # Get actual properties
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"📹 Video source opened: {self.source}")
            print(f"   Resolution: {actual_width}x{actual_height}")
            print(f"   FPS: {actual_fps}")
            
            self.is_running = True
            self.start_time = time.time()
            return True
            
        except Exception as e:
            print(f"❌ Error opening video source: {e}")
            return False
    
    def close(self):
        """Close the video source"""
        self.is_running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        
        if self.cap:
            self.cap.release()
            self.cap = None
            
        print("📹 Video source closed")
    
    def read_frame(self) -> Optional[FrameData]:
        """Read a single frame from the video source"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        self.frame_count += 1
        
        # Calculate FPS
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.current_fps = self.frame_count / elapsed
        
        # Resize if needed
        if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        return FrameData(
            frame=frame,
            timestamp=datetime.now(),
            frame_id=self.frame_count,
            fps=self.current_fps
        )
    
    def _frame_reader_thread(self):
        """Background thread for reading frames"""
        while self.is_running:
            frame_data = self.read_frame()
            
            if frame_data is None:
                # End of video or error
                break
            
            # Put frame in queue (drop oldest if full)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            
            self.frame_queue.put(frame_data)
            
            # Control frame rate
            time.sleep(1.0 / self.target_fps)
    
    def start_async_reading(self):
        """Start reading frames in background thread"""
        if not self.cap:
            self.open()
        
        self.read_thread = threading.Thread(target=self._frame_reader_thread)
        self.read_thread.daemon = True
        self.read_thread.start()
    
    def get_frame_async(self) -> Optional[FrameData]:
        """Get the latest frame from the queue"""
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
    
    async def stream_frames(self) -> AsyncGenerator[FrameData, None]:
        """Async generator for streaming frames"""
        if not self.cap:
            if not self.open():
                return
        
        frame_interval = 1.0 / self.target_fps
        
        while self.is_running:
            frame_data = self.read_frame()
            
            if frame_data is None:
                # For video files, optionally loop
                if isinstance(self.source, str):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.frame_count = 0
                    continue
                else:
                    break
            
            yield frame_data
            
            # Maintain frame rate
            await asyncio.sleep(frame_interval)
    
    def get_status(self) -> dict:
        """Get current processor status"""
        return {
            "source": str(self.source),
            "is_running": self.is_running,
            "frame_count": self.frame_count,
            "current_fps": round(self.current_fps, 1),
            "resolution": f"{self.frame_width}x{self.frame_height}"
        }


def frame_to_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    """Convert frame to JPEG bytes"""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    return buffer.tobytes()


def frame_to_base64(frame: np.ndarray, quality: int = 85) -> str:
    """Convert frame to base64 encoded JPEG"""
    import base64
    jpeg_bytes = frame_to_jpeg(frame, quality)
    return base64.b64encode(jpeg_bytes).decode('utf-8')


def add_timestamp_overlay(frame: np.ndarray) -> np.ndarray:
    """Add timestamp overlay to frame"""
    annotated = frame.copy()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add semi-transparent background
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, frame.shape[0] - 40), (250, frame.shape[0] - 10), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, annotated, 0.5, 0, annotated)
    
    # Add timestamp text
    cv2.putText(
        annotated,
        timestamp,
        (15, frame.shape[0] - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1
    )
    
    return annotated
