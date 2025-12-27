"""
Configuration settings for the Pizza Store Violation Detection System
"""
import os

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC_FRAMES = 'video-frames'
KAFKA_TOPIC_DETECTIONS = 'detections'
KAFKA_GROUP_ID = 'detection-service'

# Video Configuration
VIDEO_PATH = os.getenv('VIDEO_PATH', r'C:\commmmm\Sah w b3dha ghalt (2).mp4')
FRAME_RATE = int(os.getenv('FRAME_RATE', '5'))  # Process 5 frames per second
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720

# Model Configuration
MODEL_PATH = os.getenv('MODEL_PATH', r'C:\commmmm\yolo12m-v2 (1).pt')
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.4'))
IOU_THRESHOLD = float(os.getenv('IOU_THRESHOLD', '0.5'))

# Detection Classes
CLASSES = {
    'hand': 0,
    'person': 1,
    'pizza': 2,
    'scooper': 3
}

# Database Configuration
DB_PATH = os.getenv('DB_PATH', r'C:\commmmm\database\violations.db')

# Streaming Service Configuration
STREAMING_HOST = os.getenv('STREAMING_HOST', '0.0.0.0')
STREAMING_PORT = int(os.getenv('STREAMING_PORT', '8000'))

# ROI Configuration (Region of Interest for protein container)
# Format: [(x1, y1, x2, y2), ...] - can be configured per video
# These are example ROIs - should be adjustable via UI
DEFAULT_ROIS = [
    # ROI for protein container - user adjusted coordinates
    {"name": "Protein Container", "coords": [400, 250, 515, 590], "color": (0, 255, 0)}
]

# Violation Detection Parameters
HAND_IN_ROI_THRESHOLD = 0.3  # Minimum IoU between hand and ROI to consider it "in ROI"
SCOOPER_NEAR_HAND_THRESHOLD = 100  # Maximum distance in pixels between hand and scooper
TRACKING_HISTORY_FRAMES = 30  # Number of frames to keep in tracking history
MIN_VIOLATION_CONFIDENCE = 0.6  # Minimum confidence to flag a violation

# Frontend Configuration
FRONTEND_PORT = 3000

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
