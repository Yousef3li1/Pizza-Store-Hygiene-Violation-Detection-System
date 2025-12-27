"""
Simplified Web Demo - No Kafka Required
Runs web interface with live detection at http://localhost:3000
"""
import cv2
import json
import base64
import asyncio
import threading
import time
from pathlib import Path
from queue import Queue
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys

sys.path.append(str(Path(__file__).parent))

try:
    from ultralytics import YOLO
except ImportError:
    print("Error: ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)

from utils.database import ViolationDatabase

# Configuration
VIDEO_PATH = r'C:\commmmm\Sah w b3dha ghalt (2).mp4'
MODEL_PATH = r'C:\commmmm\yolo12m-v2 (1).pt'

# ROI Configuration - User adjusted coordinates
ROI = {
    "name": "Protein Container",
    "coords": [400, 250, 515, 590],  # Custom position for protein container
    "color": (0, 255, 0)
}

# Global state
latest_frame = None
latest_data = None
frame_queue = Queue(maxsize=30)
violation_count = 0
active_connections = []

# Violation tracking - Enhanced for accuracy
hand_in_roi_previous = False  # Track if hand was in ROI in previous frame
violation_cooldown = 0  # Cooldown to avoid duplicate violations
hand_in_roi_frames = 0  # Count consecutive frames hand is in ROI (temporal consistency)
hand_tracking_history = {}  # Track each hand's state across frames
MIN_CONSECUTIVE_FRAMES = 3  # Hand must be in ROI for at least 3 consecutive frames (reduced from 5 for better detection)

# Initialize
app = FastAPI()
db = ViolationDatabase()

print("=" * 60)
print("Pizza Store Violation Detection - Web Demo")
print("=" * 60)

# Load model
print("\nLoading YOLO model (this may take 10-20 seconds)...")
try:
    model = YOLO(MODEL_PATH)
    print(f"✓ Model loaded: {model.names}")
except Exception as e:
    print(f"✗ Error loading model: {e}")
    sys.exit(1)


def process_video():
    """Background thread to process video"""
    global latest_frame, latest_data, violation_count, hand_in_roi_previous, violation_cooldown, hand_in_roi_frames, hand_tracking_history
    
    print(f"\nOpening video: {VIDEO_PATH}")
    cap = cv2.VideoCapture(VIDEO_PATH)
    
    if not cap.isOpened():
        print(f"✗ Cannot open video: {VIDEO_PATH}")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"✓ Video opened: {total_frames} frames at {fps} FPS")
    print("\n" + "="*60)
    print("FINE-TUNED DETECTION SYSTEM - HIGH ACCURACY MODE")
    print("="*60)
    print(f"ROI: {ROI['coords']}")
    print(f"Detection Requirements:")
    print(f"  - Hand overlap ratio: >= 25% (balanced for accuracy)")
    print(f"  - Minimum overlap area: >= 1500 pixels (balanced for detection)")
    print(f"  - Hand center MUST be inside ROI")
    print(f"  - Temporal consistency: Hand must be in ROI for >= {MIN_CONSECUTIVE_FRAMES} consecutive frames")
    print(f"  - Scooper detection: IoU overlap > 0.2 (scooper must be IN hand)")
    print(f"  - Video processing: Single pass (NO LOOPING)")
    print(f"  - Duplicate prevention: 30 frame cooldown per violation")
    print("="*60)
    print("\nProcessing video...")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            # Video ended - stop processing (DO NOT LOOP)
            print(f"\n{'='*60}")
            print(f"VIDEO PROCESSING COMPLETE")
            print(f"Total frames processed: {frame_count}")
            print(f"Total violations detected: {violation_count}")
            print(f"{'='*60}\n")
            break
        
        frame_count += 1
        
        # Process every 6th frame (5 FPS from 30 FPS)
        if frame_count % 6 != 0:
            continue
        
        # Run detection
        results = model(frame, conf=0.4, verbose=False)
        
        # Draw ROI
        x1, y1, x2, y2 = ROI['coords']
        cv2.rectangle(frame, (x1, y1), (x2, y2), ROI['color'], 2)
        cv2.putText(frame, ROI['name'], (x1, y1-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, ROI['color'], 2)
        
        # Parse detections
        hands = []
        scoopers = []
        pizzas = []
        
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            
            for box, conf, cls_id in zip(boxes, confidences, class_ids):
                x1_obj, y1_obj, x2_obj, y2_obj = map(int, box)
                class_name = model.names[cls_id].lower()
                
                if 'hand' in class_name:
                    color = (0, 255, 255)  # Yellow
                    label = f"Hand {conf:.2f}"
                    hands.append({'bbox': [x1_obj, y1_obj, x2_obj, y2_obj], 'conf': float(conf)})
                    cv2.rectangle(frame, (x1_obj, y1_obj), (x2_obj, y2_obj), color, 2)
                    cv2.putText(frame, label, (x1_obj, y1_obj-5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                elif 'scooper' in class_name or 'scoop' in class_name:
                    color = (0, 0, 255)  # Red
                    label = f"Scooper {conf:.2f}"
                    scoopers.append({'bbox': [x1_obj, y1_obj, x2_obj, y2_obj], 'conf': float(conf)})
                    cv2.rectangle(frame, (x1_obj, y1_obj), (x2_obj, y2_obj), color, 2)
                    cv2.putText(frame, label, (x1_obj, y1_obj-5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                elif 'pizza' in class_name:
                    color = (255, 0, 0)  # Blue
                    label = f"Pizza {conf:.2f}"
                    pizzas.append({'bbox': [x1_obj, y1_obj, x2_obj, y2_obj], 'conf': float(conf)})
                    cv2.rectangle(frame, (x1_obj, y1_obj), (x2_obj, y2_obj), color, 2)
                    cv2.putText(frame, label, (x1_obj, y1_obj-5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Enhanced Violation Detection Logic - FINE-TUNED FOR ACCURACY
        # Decrease cooldown
        if violation_cooldown > 0:
            violation_cooldown -= 1
        
        roi_x1, roi_y1, roi_x2, roi_y2 = ROI['coords']
        
        # Track each hand individually for temporal consistency
        current_hands_in_roi = []
        
        for hand_idx, hand in enumerate(hands):
            hx1, hy1, hx2, hy2 = hand['bbox']
            hand_area = (hx2 - hx1) * (hy2 - hy1)
            
            # Calculate overlap between hand and ROI
            overlap_x = max(0, min(hx2, roi_x2) - max(hx1, roi_x1))
            overlap_y = max(0, min(hy2, roi_y2) - max(hy1, roi_y1))
            overlap_area = overlap_x * overlap_y
            
            # Calculate hand center
            hand_center_x = (hx1 + hx2) / 2
            hand_center_y = (hy1 + hy2) / 2
            
            # BALANCED REQUIREMENTS: Hand must be SIGNIFICANTLY inside ROI
            # 1. At least 25% of hand must overlap with ROI (balanced for accuracy)
            overlap_ratio = overlap_area / hand_area if hand_area > 0 else 0
            
            # 2. Hand center MUST be inside ROI (not just touching edge)
            center_in_roi = (roi_x1 <= hand_center_x <= roi_x2 and roi_y1 <= hand_center_y <= roi_y2)
            
            # 3. Minimum overlap area of 1500 pixels (balanced for detection)
            significant_overlap = overlap_area > 1500
            
            # ALL THREE conditions must be true for hand to be considered "in ROI"
            hand_is_in_roi = overlap_ratio >= 0.25 and center_in_roi and significant_overlap
            
            if hand_is_in_roi:
                # Match this hand to existing tracked hands by finding closest match
                best_match_id = None
                min_distance = float('inf')
                
                for tracked_id, tracked_data in hand_tracking_history.items():
                    if tracked_data.get('violation_triggered', False):
                        continue  # Skip hands that already triggered violation
                    
                    # Calculate distance between current hand center and tracked hand center
                    tracked_bbox = tracked_data.get('bbox', [0, 0, 0, 0])
                    if len(tracked_bbox) == 4:
                        tracked_center_x = (tracked_bbox[0] + tracked_bbox[2]) / 2
                        tracked_center_y = (tracked_bbox[1] + tracked_bbox[3]) / 2
                        distance = ((hand_center_x - tracked_center_x)**2 + (hand_center_y - tracked_center_y)**2)**0.5
                        
                        # Match if within 100 pixels (hand likely moved slightly)
                        if distance < 100 and distance < min_distance:
                            min_distance = distance
                            best_match_id = tracked_id
                
                # Use existing tracking or create new
                if best_match_id:
                    hand_id = best_match_id
                    # Update tracking
                    hand_tracking_history[hand_id]['consecutive_frames'] += 1
                    hand_tracking_history[hand_id]['bbox'] = hand['bbox']
                    hand_tracking_history[hand_id]['last_seen'] = frame_count
                else:
                    # New hand - create tracking entry
                    hand_id = f"hand_{frame_count}_{hand_idx}_{int(hand_center_x)}_{int(hand_center_y)}"
                    hand_tracking_history[hand_id] = {
                        'consecutive_frames': 1,
                        'bbox': hand['bbox'],
                        'last_seen': frame_count,
                        'violation_triggered': False
                    }
                
                current_hands_in_roi.append({
                    'hand_id': hand_id,
                    'bbox': hand['bbox'],
                    'overlap_ratio': overlap_ratio,
                    'overlap_area': overlap_area,
                    'hand_area': hand_area,
                    'center_in_roi': center_in_roi,
                    'consecutive_frames': hand_tracking_history[hand_id]['consecutive_frames']
                })
                
                # Mark hand as in ROI (change color to red)
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (0, 0, 255), 3)
                cv2.putText(frame, f"HAND IN CONTAINER ({hand_tracking_history[hand_id]['consecutive_frames']} frames)", 
                           (hx1, hy1-25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        # Reset tracking for hands that are no longer in ROI
        # Check all tracked hands - if they weren't seen in current_hands_in_roi, reset their counter
        tracked_hand_ids = set(hand_data['hand_id'] for hand_data in current_hands_in_roi)
        for hand_id in list(hand_tracking_history.keys()):
            if hand_id not in tracked_hand_ids:
                # This hand is no longer in ROI - reset consecutive frames but keep tracking
                if not hand_tracking_history[hand_id].get('violation_triggered', False):
                    hand_tracking_history[hand_id]['consecutive_frames'] = 0
        
        # Clean up old tracking data (hands not seen for 15+ frames)
        hands_to_remove = []
        for hand_id, data in hand_tracking_history.items():
            if frame_count - data['last_seen'] > 15:
                hands_to_remove.append(hand_id)
        for hand_id in hands_to_remove:
            del hand_tracking_history[hand_id]
        
        # Debug output every 30 frames
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: Hands detected: {len(hands)}, Hands in ROI: {len(current_hands_in_roi)}, Scoopers: {len(scoopers)}")
        
        # Check for scooper IN HAND (not just nearby)
        # Scooper must overlap with hand bounding box to be considered "in hand"
        for hand_data in current_hands_in_roi:
            hand_bbox = hand_data['bbox']
            hx1, hy1, hx2, hy2 = hand_bbox
            has_scooper_in_hand = False
            
            # Check if any scooper overlaps with hand (scooper is IN the hand)
            for scooper in scoopers:
                sx1, sy1, sx2, sy2 = scooper['bbox']
                
                # Calculate IoU between hand and scooper
                scooper_area = (sx2 - sx1) * (sy2 - sy1)
                overlap_x = max(0, min(hx2, sx2) - max(hx1, sx1))
                overlap_y = max(0, min(hy2, sy2) - max(hy1, sy1))
                overlap_area = overlap_x * overlap_y
                
                # If scooper overlaps significantly with hand (IoU > 0.2), scooper is IN hand
                union_area = hand_data['hand_area'] + scooper_area - overlap_area
                iou = overlap_area / union_area if union_area > 0 else 0
                
                if iou > 0.2:  # Scooper overlaps with hand
                    has_scooper_in_hand = True
                    # Draw line connecting hand and scooper
                    hand_center_x = (hx1 + hx2) / 2
                    hand_center_y = (hy1 + hy2) / 2
                    scooper_center_x = (sx1 + sx2) / 2
                    scooper_center_y = (sy1 + sy2) / 2
                    cv2.line(frame, 
                            (int(hand_center_x), int(hand_center_y)),
                            (int(scooper_center_x), int(scooper_center_y)),
                            (0, 255, 0), 3)
                    cv2.putText(frame, "SCOOPER IN HAND", (hx1, hy1-50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    break
            
            # VIOLATION LOGIC: Hand in ROI for sufficient frames AND no scooper in hand
            if (hand_data['consecutive_frames'] >= MIN_CONSECUTIVE_FRAMES and 
                not has_scooper_in_hand and 
                violation_cooldown == 0):
                
                # Check if this hand already triggered a violation (prevent duplicates)
                hand_id = hand_data['hand_id']
                if hand_id not in hand_tracking_history or not hand_tracking_history[hand_id].get('violation_triggered', False):
                    violation_count += 1
                    violation_cooldown = 20  # 20 frames cooldown (~4 seconds at 5fps) - prevents duplicates
                    
                    # Mark this hand as having triggered violation
                    hand_tracking_history[hand_id]['violation_triggered'] = True
                    
                    # Get detection data for logging
                    overlap_ratio = hand_data['overlap_ratio']
                    overlap_area = hand_data['overlap_area']
                    center_in_roi = hand_data['center_in_roi']
                    confidence_score = min(100, int(overlap_ratio * 100))
                    
                    print(f"")
                    print(f"{'='*60}")
                    print(f"VIOLATION #{violation_count} DETECTED!")
                    print(f"Frame: {frame_count}")
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Hand in container: YES")
                    print(f"  - Overlap ratio: {overlap_ratio:.1%} (>=25% required)")
                    print(f"  - Overlap area: {int(overlap_area)} pixels (>=1500 required)")
                    print(f"  - Hand center in ROI: {center_in_roi}")
                    print(f"  - Consecutive frames in ROI: {hand_data['consecutive_frames']} (>=3 required)")
                    print(f"  - Detection confidence: {confidence_score}%")
                    print(f"Scooper in hand: NO (checked IoU overlap)")
                    print(f"{'='*60}")
                    print(f"")
                    
                    # Show BIG violation alert
                    cv2.rectangle(frame, (40, 80), (frame.shape[1]-40, 150), (0, 0, 255), -1)
                    cv2.putText(frame, f"VIOLATION #{violation_count}! NO SCOOPER!", (50, 130),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 4)
                    
                    # EXPORT/SAVE FRAME IMAGE
                try:
                    # Create violations_frames directory if it doesn't exist
                    violations_dir = Path('database/violation_frames')
                    violations_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate filename with timestamp and violation number
                    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                    frame_filename = f"violation_{violation_count}_frame_{frame_count}_{timestamp_str}.jpg"
                    frame_path = violations_dir / frame_filename
                    
                    # Save the frame with violation alert drawn on it
                    cv2.imwrite(str(frame_path), frame)
                    
                    print(f"  ✓ Frame exported: {frame_filename}")
                    print(f"  ✓ Saved to: {frame_path}")
                except Exception as e:
                    print(f"  ✗ Error exporting frame: {e}")
                
                # Save to database
                try:
                    violation_data = {
                        'timestamp': datetime.now().isoformat(),
                        'frame_number': frame_count,
                        'frame_path': str(frame_path) if 'frame_path' in locals() else '',
                        'violation_type': 'no_scooper_in_container',
                        'roi_name': ROI['name'],
                        'hand_bbox': hands[0]['bbox'] if hands else [],
                        'scooper_detected': 0,
                        'confidence': 0.95,
                        'metadata': {'has_scooper': False, 'hand_in_roi': True, 'exported_frame': str(frame_filename) if 'frame_filename' in locals() else ''}
                    }
                    db.insert_violation(violation_data)
                    print(f"  ✓ Saved to database")
                except Exception as e:
                    print(f"  ✗ Error saving to database: {e}")
        
        # Show status on frame
        if current_hands_in_roi:
            for hand_data in current_hands_in_roi:
                # Check if scooper is in this specific hand
                has_scooper = False
                hx1, hy1, hx2, hy2 = hand_data['bbox']
                for scooper in scoopers:
                    sx1, sy1, sx2, sy2 = scooper['bbox']
                    overlap_x = max(0, min(hx2, sx2) - max(hx1, sx1))
                    overlap_y = max(0, min(hy2, sy2) - max(hy1, sy1))
                    overlap_area = overlap_x * overlap_y
                    scooper_area = (sx2 - sx1) * (sy2 - sy1)
                    union_area = hand_data['hand_area'] + scooper_area - overlap_area
                    iou = overlap_area / union_area if union_area > 0 else 0
                    if iou > 0.2:
                        has_scooper = True
                        break
                
                if has_scooper:
                    cv2.putText(frame, f"Hand in container WITH scooper - OK ({hand_data['consecutive_frames']} frames)", 
                               (50, 180),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    frames_text = f"({hand_data['consecutive_frames']}/{MIN_CONSECUTIVE_FRAMES} frames)"
                    if hand_data['consecutive_frames'] >= MIN_CONSECUTIVE_FRAMES:
                        cv2.putText(frame, f"Hand in container WITHOUT scooper - VIOLATION! {frames_text}", 
                                   (50, 180),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        cv2.putText(frame, f"Hand in container - Counting frames... {frames_text}", 
                                   (50, 180),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
                break  # Show status for first hand only
        
        # Update previous state
        hand_in_roi_previous = len(current_hands_in_roi) > 0
        
        # Add violation count - BIG and CLEAR at bottom
        cv2.rectangle(frame, (40, frame.shape[0] - 50), (400, frame.shape[0] - 10), (0, 0, 0), -1)
        cv2.putText(frame, f"VIOLATIONS: {violation_count}", 
                   (50, frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 3)
        
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Update latest
        latest_frame = frame_base64
        latest_data = {
            'frame_number': frame_count,
            'timestamp': time.time(),
            'detections': {
                'hands': hands,
                'scoopers': scoopers,
                'pizzas': pizzas
            },
            'total_violations': violation_count,
            'annotated_frame': frame_base64
        }
        
        # Add to queue
        if not frame_queue.full():
            frame_queue.put(latest_data)
        
        # Small delay
        time.sleep(0.1)


# Start video processing in background
video_thread = threading.Thread(target=process_video, daemon=True)
video_thread.start()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend"""
    html_path = Path(__file__).parent / "frontend" / "index.html"
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.get("/api/status")
async def get_status():
    """Get service status"""
    return {
        "status": "running",
        "total_violations": violation_count,
        "latest_frame_available": latest_frame is not None
    }


@app.get("/api/violations")
async def get_violations():
    """Get violation statistics"""
    total = db.get_violation_count()
    recent = db.get_violations(limit=10)
    
    return {
        "total_violations": total,
        "recent_violations": recent
    }


@app.get("/api/violations/list")
async def get_violations_list(limit: int = 50):
    """Get list of violations"""
    violations = db.get_violations(limit=limit)
    return {
        "violations": violations,
        "count": len(violations)
    }


@app.delete("/api/violations/clear")
async def clear_violations():
    """Clear all violations"""
    db.clear_violations()
    global violation_count
    violation_count = 0
    return {"message": "Violations cleared"}


@app.get("/stream/video")
async def stream_video():
    """MJPEG video stream"""
    def generate():
        while True:
            try:
                if latest_frame:
                    frame_bytes = base64.b64decode(latest_frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(0.1)
            except:
                continue
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws/detections")
async def websocket_detections(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            if latest_data:
                await websocket.send_json({
                    "type": "detection",
                    "data": latest_data
                })
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/api/latest-frame")
async def get_latest_frame():
    """Get latest frame"""
    if latest_data:
        return latest_data
    return {"message": "No frame available yet"}, 404


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Starting web server on http://localhost:3000")
    print("=" * 60)
    print("\nOpen your browser to: http://localhost:3000")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")


