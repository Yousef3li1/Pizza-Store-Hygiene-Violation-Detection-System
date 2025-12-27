# 🏗️ System Architecture

## Overview

The Pizza Store Violation Detection System is built using a **microservices architecture** with event-driven communication via Apache Kafka. This design provides scalability, maintainability, and fault tolerance.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         VIDEO SOURCE                            │
│                  (Camera / Video File / RTSP)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRAME READER SERVICE                         │
│  • Reads video frames (OpenCV)                                  │
│  • Encodes frames to base64                                     │
│  • Frame rate control (default: 5 fps)                          │
│  • Publishes to Kafka topic: "video-frames"                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KAFKA MESSAGE BROKER                       │
│  Topic: "video-frames"                                          │
│  • Message buffering                                            │
│  • GZIP compression                                             │
│  • Guarantees message delivery                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DETECTION SERVICE                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Consumes frames from Kafka                           │   │
│  │ 2. Decodes base64 frames                                │   │
│  │ 3. Runs YOLO v12 object detection                       │   │
│  │    - Detects: Hand, Person, Pizza, Scooper              │   │
│  │ 4. Hand Tracking & State Management                     │   │
│  │    - Tracks each hand across frames                     │   │
│  │    - Maintains state history                            │   │
│  │ 5. ROI Intersection Detection                           │   │
│  │    - Checks if hand enters ROI                          │   │
│  │    - Detects scooper presence                           │   │
│  │ 6. Violation Detection Logic                            │   │
│  │    - Pattern: ROI (no scooper) → Pizza = VIOLATION     │   │
│  │ 7. Draws annotations on frames                          │   │
│  │ 8. Saves violations to database                         │   │
│  │ 9. Publishes results to Kafka: "detections"            │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KAFKA MESSAGE BROKER                       │
│  Topic: "detections"                                            │
│  • Detection results + annotated frames                         │
│  • Violation events                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMING SERVICE                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ FastAPI Backend                                         │   │
│  │                                                         │   │
│  │ 1. Consumes from Kafka "detections" topic              │   │
│  │ 2. Maintains latest frame state                        │   │
│  │ 3. REST API Endpoints:                                 │   │
│  │    • GET  /api/status                                  │   │
│  │    • GET  /api/violations                              │   │
│  │    • GET  /api/violations/list                         │   │
│  │    • DELETE /api/violations/clear                      │   │
│  │    • GET  /stream/video (MJPEG)                        │   │
│  │ 4. WebSocket Endpoint:                                 │   │
│  │    • ws://host/ws/detections                           │   │
│  │    • Real-time detection streaming                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────┬──────────────────────────┬───────────────────────────┘
           │                          │
           │ REST API                 │ WebSocket
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND UI                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ HTML/CSS/JavaScript Web Interface                       │   │
│  │                                                         │   │
│  │ • Video Stream Display (MJPEG)                         │   │
│  │ • WebSocket connection for real-time updates           │   │
│  │ • Statistics dashboard                                 │   │
│  │ • Violation alerts                                     │   │
│  │ • Current detections display                           │   │
│  │ • Control buttons (refresh, clear)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

                             ⇅
┌─────────────────────────────────────────────────────────────────┐
│                       DATABASE (SQLite)                         │
│  • Violations table                                             │
│  • Violation frames (saved as images)                           │
│  • Metadata and timestamps                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frame Reader Service

**Technology**: Python, OpenCV, Kafka Producer

**Responsibilities**:
- Read video frames from file or RTSP stream
- Control frame rate (process N frames per second)
- Encode frames to base64 for Kafka transmission
- Publish frames to Kafka topic

**Key Features**:
- Frame skip logic to reduce processing load
- JPEG compression for efficient transmission
- Automatic reconnection on Kafka failures
- Progress logging

**Configuration**:
- `VIDEO_PATH`: Input video source
- `FRAME_RATE`: Target frames per second
- `KAFKA_TOPIC_FRAMES`: Output topic

### 2. Detection Service

**Technology**: Python, YOLO v12, Kafka Consumer/Producer, OpenCV

**Responsibilities**:
- Consume frames from Kafka
- Run object detection (YOLO)
- Track hands across frames
- Detect violations based on business logic
- Save violations to database
- Publish detection results

**Key Components**:

#### a. Object Detector
- YOLO v12 Medium model
- Detects 4 classes: Hand, Person, Pizza, Scooper
- Confidence filtering

#### b. Hand Tracker (`utils/tracker.py`)
- Assigns unique IDs to hands
- Tracks hand state across frames:
  - `in_roi`: Hand in region of interest
  - `has_scooper`: Scooper detected near hand
  - `near_pizza`: Hand near pizza
- Maintains state history (configurable frames)
- IoU-based matching between frames

#### c. ROI Manager (`utils/roi_manager.py`)
- Manages Regions of Interest
- Calculates intersections (IoU)
- Configurable ROIs via JSON

#### d. Violation Detection Logic
```
For each hand:
  1. Track hand position
  2. Check if hand enters ROI
  3. Check if scooper is near hand (within threshold)
  4. Check if hand moves to pizza
  5. If (in_ROI without scooper) → (to pizza):
     → FLAG VIOLATION
```

**Configuration**:
- `MODEL_PATH`: YOLO model file
- `CONFIDENCE_THRESHOLD`: Detection confidence
- `HAND_IN_ROI_THRESHOLD`: IoU threshold for ROI intersection
- `SCOOPER_NEAR_HAND_THRESHOLD`: Distance in pixels

### 3. Streaming Service

**Technology**: FastAPI, Uvicorn, Kafka Consumer, WebSocket

**Responsibilities**:
- Consume detection results from Kafka
- Provide REST API for querying data
- Stream video via MJPEG
- WebSocket for real-time updates
- CORS enabled for web access

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Service status and stats |
| `/api/violations` | GET | Violation statistics |
| `/api/violations/list` | GET | List violations |
| `/api/violations/clear` | DELETE | Clear all violations |
| `/stream/video` | GET | MJPEG video stream |
| `/ws/detections` | WS | Real-time WebSocket stream |

**Features**:
- Connection pooling for WebSocket clients
- Frame queue management
- Automatic client cleanup on disconnect

### 4. Frontend UI

**Technology**: HTML, CSS, JavaScript (Vanilla)

**Features**:
- **Live Video Stream**: MJPEG stream display
- **Real-time Updates**: WebSocket connection
- **Statistics Dashboard**: 
  - Total violations counter
  - Active detections counter
- **Current Detections**: Shows detected objects
- **Violation List**: Recent violations with details
- **Controls**: Refresh stream, clear violations
- **Responsive Design**: Works on desktop and mobile

**Design**:
- Modern gradient background
- Card-based layout
- Color-coded elements:
  - Green: Normal operations
  - Red: Violations
  - Blue: Information

### 5. Message Broker (Kafka)

**Topics**:

| Topic | Producer | Consumer | Message Type |
|-------|----------|----------|--------------|
| `video-frames` | Frame Reader | Detection Service | Encoded frames |
| `detections` | Detection Service | Streaming Service | Detection results |

**Configuration**:
- Compression: GZIP
- Max message size: 10MB
- Auto-offset reset: earliest/latest

### 6. Database (SQLite)

**Schema**:

```sql
-- Violations table
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    frame_number INTEGER NOT NULL,
    frame_path TEXT,
    violation_type TEXT NOT NULL,
    roi_name TEXT,
    hand_bbox TEXT,  -- JSON
    pizza_bbox TEXT,  -- JSON
    scooper_detected INTEGER DEFAULT 0,
    confidence REAL,
    metadata TEXT,  -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table (for future use)
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    total_violations INTEGER DEFAULT 0,
    total_frames INTEGER DEFAULT 0,
    metadata TEXT
);
```

**Storage**:
- Database file: `database/violations.db`
- Violation images: `database/violation_frames/`

## Data Flow

### Frame Processing Flow

```
1. Frame Reader reads frame at timestamp T
2. Frame encoded to base64
3. Published to Kafka "video-frames" topic
4. Detection Service receives frame
5. Decodes frame
6. Runs YOLO detection
7. Parses detections (hands, pizzas, scoopers)
8. Updates hand tracker states
9. Checks for violations
10. If violation: Save to database + capture image
11. Draws annotations on frame
12. Encodes annotated frame
13. Publishes to "detections" topic
14. Streaming Service receives results
15. Updates latest frame state
16. Broadcasts to WebSocket clients
17. Adds to MJPEG stream queue
18. Frontend displays results
```

### Violation Detection Flow

```
State Machine for Each Hand:

IDLE → IN_ROI (no scooper) → NEAR_PIZZA → VIOLATION!
  ↓         ↓                     ↓
  └─────────┴─────────────────────┘
        (reset after violation)

If scooper detected in IN_ROI state:
  → No violation (safe workflow)
```

## Scalability Considerations

### Current Setup (Single Machine)
- All services on one machine
- Kafka on localhost
- SQLite database

### Scaling Options

1. **Horizontal Scaling**:
   - Multiple Detection Service instances
   - Kafka consumer groups for load balancing
   - Shared database (migrate to PostgreSQL/MySQL)

2. **Multi-Camera Support**:
   - Multiple Frame Reader instances (one per camera)
   - Partition Kafka topics by camera ID
   - Detection Service processes all cameras

3. **Cloud Deployment**:
   - Deploy each service as container (Docker)
   - Use managed Kafka (AWS MSK, Confluent Cloud)
   - Use cloud database (RDS, Cloud SQL)
   - Load balancer for Streaming Service

4. **Performance Optimization**:
   - GPU acceleration for YOLO
   - Frame batching in Detection Service
   - Redis for caching statistics
   - CDN for video streaming

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Object Detection | YOLO v12 | Hand, pizza, scooper detection |
| Video Processing | OpenCV | Frame reading and manipulation |
| Message Broker | Apache Kafka | Inter-service communication |
| Web Framework | FastAPI | REST API and WebSocket |
| Web Server | Uvicorn | ASGI server for FastAPI |
| Frontend | HTML/CSS/JS | User interface |
| Database | SQLite | Violation storage |
| Language | Python 3.8+ | All services |

## Security Considerations

### Current Implementation
- No authentication (suitable for internal/demo use)
- CORS enabled for all origins
- SQLite file-based database

### Production Recommendations
1. Add API authentication (JWT tokens)
2. Use HTTPS/WSS for encrypted communication
3. Secure Kafka with SSL/SASL
4. Implement rate limiting
5. Add user roles and permissions
6. Use environment variables for secrets
7. Input validation and sanitization
8. Database access control

## Monitoring and Logging

### Current Logging
- Each service logs to console
- Log level configurable (DEBUG, INFO, WARNING, ERROR)
- Structured logging with timestamps

### Production Monitoring
- Centralized logging (ELK stack, CloudWatch)
- Metrics collection (Prometheus, Grafana)
- Health check endpoints
- Alerting on violations threshold
- Performance metrics (FPS, latency, CPU, memory)

## Future Enhancements

1. **Advanced Analytics**:
   - Violation trends over time
   - Worker-specific analytics
   - Shift-based reports

2. **Machine Learning Improvements**:
   - Fine-tune YOLO on store-specific data
   - Action recognition (not just object detection)
   - Anomaly detection

3. **User Features**:
   - Email/SMS alerts on violations
   - Export reports (PDF, CSV)
   - Video clip extraction
   - ROI configuration via UI

4. **System Features**:
   - Multi-store support
   - Historical video playback
   - Integration with POS systems
   - Mobile app for managers

## License

This architecture documentation is part of the Pizza Store Violation Detection System.




