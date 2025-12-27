"""
Detection Service
Consumes frames from Kafka, performs object detection, and detects violations
"""
import cv2
import json
import base64
import numpy as np
import time
import logging
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_FRAMES,
    KAFKA_TOPIC_DETECTIONS,
    KAFKA_GROUP_ID,
    MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    IOU_THRESHOLD,
    CLASSES,
    DEFAULT_ROIS,
    HAND_IN_ROI_THRESHOLD,
    SCOOPER_NEAR_HAND_THRESHOLD,
    LOG_LEVEL
)
from utils.database import ViolationDatabase
from utils.roi_manager import ROIManager
from utils.tracker import HandTracker

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DetectionService:
    """
    Object detection and violation detection service
    """
    
    def __init__(self):
        """Initialize detection service"""
        self.kafka_servers = KAFKA_BOOTSTRAP_SERVERS
        self.topic_frames = KAFKA_TOPIC_FRAMES
        self.topic_detections = KAFKA_TOPIC_DETECTIONS
        self.group_id = KAFKA_GROUP_ID
        
        # Initialize components
        self.consumer = None
        self.producer = None
        self.model = None
        self.db = ViolationDatabase()
        self.roi_manager = ROIManager(DEFAULT_ROIS)
        self.hand_tracker = HandTracker()
        
        # Statistics
        self.total_frames_processed = 0
        self.total_violations = 0
        
        # Initialize
        self.init_kafka()
        self.load_model()
    
    def init_kafka(self):
        """Initialize Kafka consumer and producer"""
        # Consumer
        try:
            self.consumer = KafkaConsumer(
                self.topic_frames,
                bootstrap_servers=self.kafka_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                max_poll_records=1,
                consumer_timeout_ms=60000  # 60 seconds timeout
            )
            logger.info(f"Kafka consumer connected to topic: {self.topic_frames}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
        
        # Producer
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_request_size=10485760,
                compression_type='gzip'
            )
            logger.info(f"Kafka producer connected")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def load_model(self):
        """Load YOLO model"""
        try:
            from ultralytics import YOLO
            self.model = YOLO(MODEL_PATH)
            logger.info(f"YOLO model loaded from {MODEL_PATH}")
            
            # Print model info
            logger.info(f"Model classes: {self.model.names}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def decode_frame(self, frame_base64):
        """
        Decode base64 frame to OpenCV image
        
        Args:
            frame_base64: Base64 encoded frame
        
        Returns:
            OpenCV image (numpy array)
        """
        # Decode base64
        frame_bytes = base64.b64decode(frame_base64)
        
        # Convert to numpy array
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        
        # Decode image
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        return frame
    
    def run_detection(self, frame):
        """
        Run YOLO detection on frame
        
        Args:
            frame: OpenCV image
        
        Returns:
            Detection results
        """
        results = self.model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            verbose=False
        )
        
        return results[0]
    
    def parse_detections(self, results):
        """
        Parse YOLO results into structured format
        
        Args:
            results: YOLO detection results
        
        Returns:
            Dict of detections by class
        """
        detections = {
            'hands': [],
            'persons': [],
            'pizzas': [],
            'scoopers': []
        }
        
        if results.boxes is None or len(results.boxes) == 0:
            return detections
        
        boxes = results.boxes.xyxy.cpu().numpy()
        confidences = results.boxes.conf.cpu().numpy()
        class_ids = results.boxes.cls.cpu().numpy().astype(int)
        
        for box, conf, cls_id in zip(boxes, confidences, class_ids):
            x1, y1, x2, y2 = box
            bbox = [int(x1), int(y1), int(x2), int(y2)]
            
            detection = {
                'bbox': bbox,
                'confidence': float(conf),
                'class_id': int(cls_id)
            }
            
            # Map to class name (assuming YOLO model has classes: hand, person, pizza, scooper)
            class_name = self.model.names[cls_id].lower()
            
            if 'hand' in class_name:
                detections['hands'].append(detection)
            elif 'person' in class_name:
                detections['persons'].append(detection)
            elif 'pizza' in class_name:
                detections['pizzas'].append(detection)
            elif 'scooper' in class_name or 'scoop' in class_name:
                detections['scoopers'].append(detection)
        
        return detections
    
    def check_scooper_near_hand(self, hand_bbox, scoopers):
        """
        Check if any scooper is near the hand
        
        Args:
            hand_bbox: Hand bounding box
            scoopers: List of scooper detections
        
        Returns:
            Boolean
        """
        if not scoopers:
            return False
        
        hand_center = [
            (hand_bbox[0] + hand_bbox[2]) / 2,
            (hand_bbox[1] + hand_bbox[3]) / 2
        ]
        
        for scooper in scoopers:
            scooper_bbox = scooper['bbox']
            scooper_center = [
                (scooper_bbox[0] + scooper_bbox[2]) / 2,
                (scooper_bbox[1] + scooper_bbox[3]) / 2
            ]
            
            # Calculate distance
            distance = np.sqrt(
                (hand_center[0] - scooper_center[0])**2 +
                (hand_center[1] - scooper_center[1])**2
            )
            
            if distance < SCOOPER_NEAR_HAND_THRESHOLD:
                return True
        
        return False
    
    def check_hand_near_pizza(self, hand_bbox, pizzas):
        """
        Check if hand is near any pizza
        
        Args:
            hand_bbox: Hand bounding box
            pizzas: List of pizza detections
        
        Returns:
            Boolean and pizza bbox if near
        """
        if not pizzas:
            return False, None
        
        for pizza in pizzas:
            pizza_bbox = pizza['bbox']
            
            # Calculate IoU or distance
            iou = self.roi_manager.calculate_iou(hand_bbox, pizza_bbox)
            
            if iou > 0.1:  # Threshold for "near" pizza
                return True, pizza_bbox
        
        return False, None
    
    def detect_violations(self, detections, frame_number):
        """
        Detect violations based on hand tracking
        
        Args:
            detections: Parsed detections
            frame_number: Current frame number
        
        Returns:
            List of violations detected
        """
        violations = []
        
        hands = detections['hands']
        scoopers = detections['scoopers']
        pizzas = detections['pizzas']
        
        if not hands:
            return violations
        
        # Match hands to tracked hands
        hand_bboxes = [h['bbox'] for h in hands]
        matched_hands = self.hand_tracker.match_hands(hand_bboxes)
        
        # Process each hand
        for hand_id, hand_bbox in matched_hands.items():
            # Check if hand is in any ROI
            intersecting_rois = self.roi_manager.get_hand_roi_intersections(
                hand_bbox, 
                threshold=HAND_IN_ROI_THRESHOLD
            )
            
            in_roi = len(intersecting_rois) > 0
            roi_name = intersecting_rois[0]['name'] if in_roi else None
            
            # Check if scooper is near hand
            has_scooper = self.check_scooper_near_hand(hand_bbox, scoopers)
            
            # Check if hand is near pizza
            near_pizza, pizza_bbox = self.check_hand_near_pizza(hand_bbox, pizzas)
            
            # Update hand state
            self.hand_tracker.update_hand_state(
                hand_id=hand_id,
                hand_bbox=hand_bbox,
                in_roi=in_roi,
                roi_name=roi_name,
                has_scooper=has_scooper,
                near_pizza=near_pizza,
                frame_number=frame_number
            )
            
            # Check for violation
            violation = self.hand_tracker.detect_violation(hand_id)
            
            if violation:
                violations.append(violation)
                logger.warning(f"Violation detected: {violation}")
        
        # Cleanup inactive hands
        self.hand_tracker.cleanup_inactive_hands(set(matched_hands.keys()))
        
        return violations
    
    def save_violation(self, violation, frame_number, frame):
        """
        Save violation to database and optionally save frame
        
        Args:
            violation: Violation data
            frame_number: Frame number
            frame: OpenCV frame
        """
        # Save frame (optional)
        frame_path = None
        try:
            violations_dir = Path('database/violation_frames')
            violations_dir.mkdir(parents=True, exist_ok=True)
            
            frame_filename = f"violation_{int(time.time())}_{frame_number}.jpg"
            frame_path = violations_dir / frame_filename
            
            # Draw violation on frame
            frame_copy = frame.copy()
            hand_bbox = violation['hand_bbox']
            cv2.rectangle(
                frame_copy,
                (hand_bbox[0], hand_bbox[1]),
                (hand_bbox[2], hand_bbox[3]),
                (0, 0, 255),
                3
            )
            cv2.putText(
                frame_copy,
                "VIOLATION: No Scooper",
                (hand_bbox[0], hand_bbox[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            
            cv2.imwrite(str(frame_path), frame_copy)
        except Exception as e:
            logger.error(f"Failed to save violation frame: {e}")
        
        # Save to database
        violation_data = {
            'timestamp': datetime.now().isoformat(),
            'frame_number': frame_number,
            'frame_path': str(frame_path) if frame_path else '',
            'violation_type': violation.get('violation_type', 'no_scooper'),
            'roi_name': violation.get('roi_name', ''),
            'hand_bbox': violation.get('hand_bbox', []),
            'pizza_bbox': [],
            'scooper_detected': 0,
            'confidence': violation.get('confidence', 0.0),
            'metadata': violation
        }
        
        self.db.insert_violation(violation_data)
        self.total_violations += 1
    
    def draw_detections(self, frame, detections, violations):
        """
        Draw detections and violations on frame
        
        Args:
            frame: OpenCV frame
            detections: Parsed detections
            violations: List of violations
        
        Returns:
            Annotated frame
        """
        frame_copy = frame.copy()
        
        # Draw ROIs
        frame_copy = self.roi_manager.draw_rois(frame_copy)
        
        # Draw hands (green if with scooper, yellow otherwise)
        for hand in detections['hands']:
            bbox = hand['bbox']
            has_scooper = self.check_scooper_near_hand(bbox, detections['scoopers'])
            color = (0, 255, 0) if has_scooper else (0, 255, 255)
            
            cv2.rectangle(frame_copy, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            cv2.putText(
                frame_copy,
                f"Hand {hand['confidence']:.2f}",
                (bbox[0], bbox[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
        
        # Draw pizzas
        for pizza in detections['pizzas']:
            bbox = pizza['bbox']
            cv2.rectangle(frame_copy, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
            cv2.putText(
                frame_copy,
                f"Pizza {pizza['confidence']:.2f}",
                (bbox[0], bbox[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2
            )
        
        # Draw scoopers
        for scooper in detections['scoopers']:
            bbox = scooper['bbox']
            cv2.rectangle(frame_copy, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 2)
            cv2.putText(
                frame_copy,
                f"Scooper {scooper['confidence']:.2f}",
                (bbox[0], bbox[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2
            )
        
        # Draw violation markers
        if violations:
            cv2.putText(
                frame_copy,
                f"VIOLATION DETECTED!",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3
            )
        
        # Draw statistics
        cv2.putText(
            frame_copy,
            f"Total Violations: {self.total_violations}",
            (50, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )
        
        return frame_copy
    
    def process_frame(self, message):
        """
        Process a single frame from Kafka
        
        Args:
            message: Kafka message containing frame data
        """
        try:
            # Extract frame data
            frame_number = message['frame_number']
            timestamp = message['timestamp']
            frame_data = message['frame_data']
            
            # Decode frame
            frame = self.decode_frame(frame_data)
            
            if frame is None:
                logger.error(f"Failed to decode frame {frame_number}")
                return
            
            # Run detection
            results = self.run_detection(frame)
            
            # Parse detections
            detections = self.parse_detections(results)
            
            # Detect violations
            violations = self.detect_violations(detections, frame_number)
            
            # Save violations
            for violation in violations:
                self.save_violation(violation, frame_number, frame)
            
            # Draw detections
            annotated_frame = self.draw_detections(frame, detections, violations)
            
            # Encode annotated frame
            annotated_frame_encoded = base64.b64encode(
                cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])[1]
            ).decode('utf-8')
            
            # Publish results
            result_message = {
                'frame_number': frame_number,
                'timestamp': timestamp,
                'detections': detections,
                'violations': violations,
                'total_violations': self.total_violations,
                'annotated_frame': annotated_frame_encoded
            }
            
            self.producer.send(self.topic_detections, value=result_message)
            
            self.total_frames_processed += 1
            
            if self.total_frames_processed % 10 == 0:
                logger.info(f"Processed {self.total_frames_processed} frames, "
                           f"Violations: {self.total_violations}")
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
    
    def run(self):
        """Main service loop"""
        logger.info("Starting Detection Service")
        logger.info(f"Listening to topic: {self.topic_frames}")
        logger.info(f"Publishing to topic: {self.topic_detections}")
        
        try:
            for message in self.consumer:
                self.process_frame(message.value)
        
        except KeyboardInterrupt:
            logger.info("Detection service interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in detection service: {e}", exc_info=True)
        
        finally:
            self.cleanup()
        
        logger.info(f"Detection Service completed. "
                   f"Total frames: {self.total_frames_processed}, "
                   f"Total violations: {self.total_violations}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info("Resources cleaned up")


def main():
    """Main entry point"""
    service = DetectionService()
    service.run()


if __name__ == '__main__':
    main()




