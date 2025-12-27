"""
Simple Standalone Demo - No Kafka Required
Processes video and shows results directly
"""
import cv2
import time
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent))

try:
    from ultralytics import YOLO
    print("✓ YOLO imported successfully")
except ImportError:
    print("✗ Error: ultralytics not installed")
    print("Run: pip install ultralytics")
    sys.exit(1)

# Configuration
VIDEO_PATH = r'C:\commmmm\Sah w b3dha ghalt (2).mp4'
MODEL_PATH = r'C:\commmmm\yolo12m-v2 (1).pt'
OUTPUT_PATH = r'C:\commmmm\output_demo.mp4'

# ROI (Region of Interest) - adjust these coordinates based on your video
ROI = {
    "name": "Protein Container",
    "coords": [400, 300, 700, 500],  # [x1, y1, x2, y2]
    "color": (0, 255, 0)  # Green
}

print("=" * 60)
print("Pizza Store Violation Detection - Simple Demo")
print("=" * 60)

# Check video file
print(f"\n1. Checking video file...")
if not Path(VIDEO_PATH).exists():
    print(f"   ✗ Video not found: {VIDEO_PATH}")
    print("   Please check the video path in the script")
    sys.exit(1)
print(f"   ✓ Video found: {VIDEO_PATH}")

# Check model file
print(f"\n2. Checking model file...")
if not Path(MODEL_PATH).exists():
    print(f"   ✗ Model not found: {MODEL_PATH}")
    print("   Please check the model path")
    sys.exit(1)
print(f"   ✓ Model found: {MODEL_PATH}")

# Load YOLO model
print(f"\n3. Loading YOLO model (this may take 10-20 seconds)...")
try:
    model = YOLO(MODEL_PATH)
    print(f"   ✓ Model loaded successfully")
    print(f"   Model classes: {model.names}")
except Exception as e:
    print(f"   ✗ Error loading model: {e}")
    sys.exit(1)

# Open video
print(f"\n4. Opening video...")
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"   ✗ Cannot open video: {VIDEO_PATH}")
    sys.exit(1)

fps = int(cap.get(cv2.CAP_PROP_FPS))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"   ✓ Video opened")
print(f"   Resolution: {width}x{height}")
print(f"   FPS: {fps}")
print(f"   Total frames: {total_frames}")

# Video writer for output
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

print(f"\n5. Processing video...")
print(f"   Output will be saved to: {OUTPUT_PATH}")
print(f"   Press 'q' to quit, 's' to skip to next frame")
print(f"   Processing every 5th frame for speed...")

violation_count = 0
frame_count = 0
processed_count = 0

try:
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("\n   ✓ Video processing complete!")
            break
        
        frame_count += 1
        
        # Process every 5th frame for speed
        if frame_count % 5 != 0:
            continue
        
        processed_count += 1
        
        # Run detection
        results = model(frame, conf=0.4, verbose=False)
        
        # Draw ROI
        x1, y1, x2, y2 = ROI['coords']
        cv2.rectangle(frame, (x1, y1), (x2, y2), ROI['color'], 2)
        cv2.putText(frame, ROI['name'], (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, ROI['color'], 2)
        
        # Parse detections
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            
            hands = []
            scoopers = []
            pizzas = []
            
            for box, conf, cls_id in zip(boxes, confidences, class_ids):
                x1_obj, y1_obj, x2_obj, y2_obj = map(int, box)
                class_name = model.names[cls_id].lower()
                
                # Determine color and label
                if 'hand' in class_name:
                    color = (0, 255, 255)  # Yellow
                    label = f"Hand {conf:.2f}"
                    hands.append((x1_obj, y1_obj, x2_obj, y2_obj))
                elif 'scooper' in class_name or 'scoop' in class_name:
                    color = (0, 0, 255)  # Red
                    label = f"Scooper {conf:.2f}"
                    scoopers.append((x1_obj, y1_obj, x2_obj, y2_obj))
                elif 'pizza' in class_name:
                    color = (255, 0, 0)  # Blue
                    label = f"Pizza {conf:.2f}"
                    pizzas.append((x1_obj, y1_obj, x2_obj, y2_obj))
                else:
                    color = (128, 128, 128)  # Gray
                    label = f"{class_name} {conf:.2f}"
                
                # Draw detection
                cv2.rectangle(frame, (x1_obj, y1_obj), (x2_obj, y2_obj), color, 2)
                cv2.putText(frame, label, (x1_obj, y1_obj-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Simple violation detection: hand in ROI without scooper
            for hand in hands:
                hx1, hy1, hx2, hy2 = hand
                # Check if hand is in ROI
                roi_x1, roi_y1, roi_x2, roi_y2 = ROI['coords']
                
                # Calculate overlap
                overlap_x = max(0, min(hx2, roi_x2) - max(hx1, roi_x1))
                overlap_y = max(0, min(hy2, roi_y2) - max(hy1, roi_y1))
                overlap_area = overlap_x * overlap_y
                hand_area = (hx2 - hx1) * (hy2 - hy1)
                
                if hand_area > 0 and overlap_area / hand_area > 0.3:
                    # Hand is in ROI - check if scooper nearby
                    has_scooper = False
                    for scooper in scoopers:
                        sx1, sy1, sx2, sy2 = scooper
                        # Simple distance check
                        hand_cx = (hx1 + hx2) / 2
                        hand_cy = (hy1 + hy2) / 2
                        scoop_cx = (sx1 + sx2) / 2
                        scoop_cy = (sy1 + sy2) / 2
                        
                        dist = ((hand_cx - scoop_cx)**2 + (hand_cy - scoop_cy)**2)**0.5
                        
                        if dist < 150:  # Pixels threshold
                            has_scooper = True
                            break
                    
                    if not has_scooper:
                        # Potential violation
                        cv2.putText(frame, "WARNING: No Scooper!", (50, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Add info overlay
        cv2.putText(frame, f"Frame: {frame_count}/{total_frames}", (10, height-60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Violations: {violation_count}", (10, height-30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Write to output
        out.write(frame)
        
        # Display frame
        cv2.imshow('Pizza Violation Detection', frame)
        
        # Progress
        if processed_count % 10 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames})")
        
        # Handle key press
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n   Stopped by user")
            break
        elif key == ord('s'):
            continue

except KeyboardInterrupt:
    print("\n   Interrupted by user")

finally:
    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total frames: {total_frames}")
    print(f"  Processed frames: {processed_count}")
    print(f"  Violations detected: {violation_count}")
    print(f"  Output saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")
    print(f"\nYou can play the output video with:")
    print(f"  {OUTPUT_PATH}")




