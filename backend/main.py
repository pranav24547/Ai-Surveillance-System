"""
Smart Surveillance System - FastAPI Backend Server
Main entry point with WebSocket streaming and REST API
"""
import asyncio
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import get_config, reload_config
from detection import WeaponDetector
from detection.processor import VideoProcessor, frame_to_jpeg, add_timestamp_overlay
from alerts import AlertManager
from storage import EvidenceManager


# ============================================================================
# Pydantic Models
# ============================================================================

class ConfigUpdate(BaseModel):
    confidence_threshold: Optional[float] = None
    alerts_enabled: Optional[bool] = None
    cooldown_seconds: Optional[int] = None

class AlertTestRequest(BaseModel):
    weapon_type: str = "gun"
    test_sms: bool = False
    test_email: bool = False


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Global application state"""
    def __init__(self):
        self.detector: Optional[WeaponDetector] = None
        self.processor: Optional[VideoProcessor] = None
        self.alert_manager: Optional[AlertManager] = None
        self.evidence_manager: Optional[EvidenceManager] = None
        self.is_streaming = False
        self.connected_clients: List[WebSocket] = []
        self.detection_count = 0
        self.start_time: Optional[datetime] = None

state = AppState()


# ============================================================================
# Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("\n" + "="*60)
    print("🚀 Starting Smart Surveillance System")
    print("="*60 + "\n")
    
    config = get_config()
    state.start_time = datetime.now()
    
    # Initialize detector
    state.detector = WeaponDetector(
        model_path=config.detection.model_path,
        confidence_threshold=config.detection.confidence_threshold,
        target_classes=config.detection.classes
    )
    state.detector.load_model()
    
    # Initialize video processor
    state.processor = VideoProcessor(
        source=config.video.source,
        frame_width=config.video.frame_width,
        frame_height=config.video.frame_height,
        target_fps=config.video.fps
    )
    
    # Initialize alert manager
    state.alert_manager = AlertManager(
        cooldown_seconds=config.alerts.cooldown_seconds,
        enabled=config.alerts.enabled
    )
    
    if config.alerts.sms.enabled:
        state.alert_manager.configure_sms(
            account_sid=config.alerts.sms.twilio_account_sid,
            auth_token=config.alerts.sms.twilio_auth_token,
            from_number=config.alerts.sms.from_number,
            to_numbers=config.alerts.sms.to_numbers
        )
    
    if config.alerts.email.enabled:
        state.alert_manager.configure_email(
            smtp_server=config.alerts.email.smtp_server,
            smtp_port=config.alerts.email.smtp_port,
            sender_email=config.alerts.email.sender_email,
            sender_password=config.alerts.email.sender_password,
            recipients=config.alerts.email.recipients,
            use_tls=config.alerts.email.use_tls
        )
    
    # Configure Telegram (FREE & UNLIMITED!)
    if hasattr(config.alerts, 'telegram') and config.alerts.telegram.enabled:
        state.alert_manager.configure_telegram(
            bot_token=config.alerts.telegram.bot_token,
            chat_ids=config.alerts.telegram.chat_ids
        )
    
    # Configure WhatsApp (UltraMsg API - 500 free messages)
    if hasattr(config.alerts, 'whatsapp') and config.alerts.whatsapp.enabled:
        state.alert_manager.configure_whatsapp(
            instance_id=config.alerts.whatsapp.instance_id,
            token=config.alerts.whatsapp.token,
            phone_numbers=config.alerts.whatsapp.phone_numbers
        )
    
    # Initialize evidence manager
    state.evidence_manager = EvidenceManager(
        base_path=config.storage.evidence_path,
        max_files=config.storage.max_evidence_files,
        save_annotated=config.storage.save_annotated_frames
    )
    
    print("\n✅ All systems initialized successfully!\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down...")
    if state.processor:
        state.processor.close()
    print("👋 Goodbye!\n")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Smart Surveillance System",
    description="AI-powered weapon detection surveillance system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for live video streaming with detection overlays"""
    await websocket.accept()
    state.connected_clients.append(websocket)
    
    print(f"📡 Client connected. Total clients: {len(state.connected_clients)}")
    
    try:
        # Open video source if not already
        if not state.processor.cap or not state.processor.cap.isOpened():
            if not state.processor.open():
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to open video source"
                })
                return
        
        state.is_streaming = True
        
        async for frame_data in state.processor.stream_frames():
            if not state.is_streaming:
                break
            
            frame = frame_data.frame
            
            # Run detection
            detections = state.detector.detect(frame)
            
            # Annotate frame
            annotated_frame = state.detector.annotate_frame(frame, detections)
            annotated_frame = add_timestamp_overlay(annotated_frame)
            
            # Handle detections
            if detections:
                state.detection_count += len(detections)
                
                for detection in detections:
                    # Save evidence
                    evidence_id = await state.evidence_manager.save_detection(
                        frame=frame,
                        annotated_frame=annotated_frame,
                        weapon_type=detection.class_name,
                        confidence=detection.confidence,
                        bbox=detection.bbox,
                        location="Camera 1"
                    )
                    
                    # Trigger alert
                    if evidence_id:
                        evidence_path = str(
                            Path(state.evidence_manager.base_path) / 
                            "annotated" / f"{evidence_id}_annotated.jpg"
                        )
                        await state.alert_manager.trigger_alert(
                            weapon_type=detection.class_name,
                            confidence=detection.confidence,
                            location="Camera 1",
                            evidence_path=evidence_path
                        )
                    
                    # Send detection event
                    await websocket.send_json({
                        "type": "detection",
                        "data": detection.to_dict()
                    })
            
            # Send frame
            jpeg_bytes = frame_to_jpeg(annotated_frame, quality=80)
            await websocket.send_bytes(jpeg_bytes)
            
            # Check for control messages
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=0.001
                )
                if message.get("action") == "stop":
                    break
            except asyncio.TimeoutError:
                pass
            except:
                pass
                
    except WebSocketDisconnect:
        print("📡 Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        state.connected_clients.remove(websocket)
        if not state.connected_clients:
            state.is_streaming = False
        print(f"📡 Remaining clients: {len(state.connected_clients)}")


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Get system status"""
    config = get_config()
    uptime = None
    if state.start_time:
        uptime = str(datetime.now() - state.start_time).split('.')[0]
    
    return {
        "status": "running",
        "uptime": uptime,
        "detection_count": state.detection_count,
        "connected_clients": len(state.connected_clients),
        "is_streaming": state.is_streaming,
        "video": state.processor.get_status() if state.processor else None,
        "alerts": state.alert_manager.get_status() if state.alert_manager else None,
        "storage": state.evidence_manager.get_statistics() if state.evidence_manager else None,
        "config": {
            "confidence_threshold": config.detection.confidence_threshold,
            "target_classes": config.detection.classes
        }
    }


@app.get("/api/detections")
async def get_detections(
    limit: int = Query(20, ge=1, le=100),
    weapon_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get recent detections"""
    if not state.evidence_manager:
        raise HTTPException(status_code=503, detail="Evidence manager not initialized")
    
    evidence = state.evidence_manager.get_recent_evidence(limit, weapon_type)
    
    return {
        "count": len(evidence),
        "detections": evidence
    }


@app.get("/api/alerts")
async def get_alerts(limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    """Get recent alerts"""
    if not state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    return {
        "alerts": state.alert_manager.get_recent_alerts(limit),
        "status": state.alert_manager.get_status()
    }


@app.get("/api/evidence/{evidence_id}")
async def get_evidence(evidence_id: str, annotated: bool = False):
    """Get evidence image by ID"""
    if not state.evidence_manager:
        raise HTTPException(status_code=503, detail="Evidence manager not initialized")
    
    image_bytes = state.evidence_manager.get_evidence_image(evidence_id, annotated)
    
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return Response(
        content=image_bytes,
        media_type="image/jpeg"
    )


@app.post("/api/config")
async def update_config(update: ConfigUpdate) -> Dict[str, Any]:
    """Update runtime configuration"""
    changes = {}
    
    if update.confidence_threshold is not None:
        if state.detector:
            state.detector.update_threshold(update.confidence_threshold)
            changes["confidence_threshold"] = update.confidence_threshold
    
    if update.alerts_enabled is not None:
        if state.alert_manager:
            state.alert_manager.enabled = update.alerts_enabled
            changes["alerts_enabled"] = update.alerts_enabled
    
    if update.cooldown_seconds is not None:
        if state.alert_manager:
            state.alert_manager.cooldown_seconds = update.cooldown_seconds
            changes["cooldown_seconds"] = update.cooldown_seconds
    
    return {"updated": changes}


@app.post("/api/alerts/test")
async def test_alerts(request: AlertTestRequest) -> Dict[str, Any]:
    """Send test alert"""
    if not state.alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    result = await state.alert_manager.trigger_alert(
        weapon_type=request.weapon_type,
        confidence=0.95,
        location="Test Location",
        force=True
    )
    
    return result


@app.post("/api/alerts/reset-cooldown")
async def reset_alert_cooldown(weapon_type: Optional[str] = None) -> Dict[str, str]:
    """Reset alert cooldown"""
    if state.alert_manager:
        state.alert_manager.reset_cooldown(weapon_type)
    return {"status": "cooldown_reset"}


@app.delete("/api/evidence")
async def clear_evidence() -> Dict[str, Any]:
    """Clear all evidence (admin only)"""
    if not state.evidence_manager:
        raise HTTPException(status_code=503, detail="Evidence manager not initialized")
    
    count = await state.evidence_manager.clear_all()
    return {"cleared": count}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Smart Surveillance System",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "/api/status"
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug
    )
