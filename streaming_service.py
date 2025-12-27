"""
Streaming Service
Provides REST API and WebSocket streaming for detection results
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import json
import asyncio
import base64
import logging
from kafka import KafkaConsumer
from threading import Thread
from queue import Queue
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_DETECTIONS,
    STREAMING_HOST,
    STREAMING_PORT,
    LOG_LEVEL
)
from utils.database import ViolationDatabase

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Pizza Violation Detection Streaming Service")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
latest_frame = None
latest_detections = None
frame_queue = Queue(maxsize=30)
websocket_clients: List[WebSocket] = []
kafka_consumer = None
consumer_thread = None


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


manager = ConnectionManager()


def kafka_consumer_thread():
    """Background thread to consume Kafka messages"""
    global latest_frame, latest_detections, kafka_consumer
    
    try:
        kafka_consumer = KafkaConsumer(
            KAFKA_TOPIC_DETECTIONS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id='streaming-service',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000
        )
        
        logger.info("Kafka consumer started in streaming service")
        
        for message in kafka_consumer:
            data = message.value
            
            # Update latest data
            latest_frame = data.get('annotated_frame')
            latest_detections = data
            
            # Add to queue (for MJPEG stream)
            if not frame_queue.full():
                frame_queue.put(data)
            else:
                # Remove oldest frame if queue is full
                try:
                    frame_queue.get_nowait()
                    frame_queue.put(data)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"Error in Kafka consumer thread: {e}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """Start Kafka consumer thread on startup"""
    global consumer_thread
    
    consumer_thread = Thread(target=kafka_consumer_thread, daemon=True)
    consumer_thread.start()
    logger.info("Streaming service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_consumer
    
    if kafka_consumer:
        kafka_consumer.close()
    
    logger.info("Streaming service shutdown")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Pizza Violation Detection Streaming Service",
        "version": "1.0",
        "endpoints": {
            "/api/violations": "Get violation statistics",
            "/api/violations/list": "Get list of violations",
            "/api/status": "Get service status",
            "/ws/detections": "WebSocket for real-time detections",
            "/stream/video": "MJPEG video stream"
        }
    }


@app.get("/api/status")
async def get_status():
    """Get service status"""
    db = ViolationDatabase()
    total_violations = db.get_violation_count()
    
    return {
        "status": "running",
        "connected_clients": len(manager.active_connections),
        "total_violations": total_violations,
        "latest_frame_available": latest_frame is not None
    }


@app.get("/api/violations")
async def get_violations():
    """Get violation statistics"""
    db = ViolationDatabase()
    total_violations = db.get_violation_count()
    recent_violations = db.get_violations(limit=10)
    
    return {
        "total_violations": total_violations,
        "recent_violations": recent_violations
    }


@app.get("/api/violations/list")
async def get_violations_list(limit: int = 50):
    """Get list of violations"""
    db = ViolationDatabase()
    violations = db.get_violations(limit=limit)
    
    return {
        "violations": violations,
        "count": len(violations)
    }


@app.delete("/api/violations/clear")
async def clear_violations():
    """Clear all violations (for testing)"""
    db = ViolationDatabase()
    db.clear_violations()
    
    return {"message": "Violations cleared successfully"}


@app.websocket("/ws/detections")
async def websocket_detections(websocket: WebSocket):
    """
    WebSocket endpoint for real-time detection streaming
    Sends detection results and annotated frames
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for new detections
            if latest_detections:
                # Send latest detection data
                message = {
                    "type": "detection",
                    "data": latest_detections
                }
                await websocket.send_json(message)
            
            # Small delay
            await asyncio.sleep(0.1)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/stream/video")
async def stream_video():
    """
    MJPEG video stream endpoint
    Streams annotated video frames
    """
    
    def generate_frames():
        """Generator function for MJPEG stream"""
        while True:
            try:
                # Get frame from queue (blocking with timeout)
                data = frame_queue.get(timeout=1)
                
                # Get annotated frame
                frame_base64 = data.get('annotated_frame')
                
                if frame_base64:
                    # Decode base64 to bytes
                    frame_bytes = base64.b64decode(frame_base64)
                    
                    # Yield MJPEG frame
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            except Exception as e:
                # On timeout or error, continue waiting
                continue
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/latest-frame")
async def get_latest_frame():
    """Get the latest annotated frame as JSON"""
    if latest_detections:
        return latest_detections
    else:
        return JSONResponse(
            status_code=404,
            content={"message": "No frame available yet"}
        )


def main():
    """Main entry point"""
    import uvicorn
    
    logger.info(f"Starting streaming service on {STREAMING_HOST}:{STREAMING_PORT}")
    
    uvicorn.run(
        app,
        host=STREAMING_HOST,
        port=STREAMING_PORT,
        log_level=LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()




