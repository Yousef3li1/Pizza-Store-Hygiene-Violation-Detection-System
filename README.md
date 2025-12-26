# 🍕 Pizza Store Hygiene Violation Detection System

A real-time Computer Vision system built with microservices architecture to monitor and detect hygiene protocol violations in pizza stores. The system uses YOLO object detection to identify when workers pick up ingredients without using a scooper.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production-brightgreen.svg)
## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This system monitors pizza store workers in real-time to ensure compliance with hygiene protocols. It detects when workers pick up ingredients (proteins) from designated containers without using a scooper, flagging such actions as violations.

### Key Technologies

- **YOLO v12** - Object detection (Hand, Person, Pizza, Scooper)
- **Apache Kafka** - Message broker for microservices communication
- **FastAPI** - REST API and WebSocket streaming
- **OpenCV** - Video processing
- **SQLite** - Violation storage
- **Python 3.8+** - Core programming language

## ✨ Features

- ✅ **Real-time Video Processing** - Live video stream analysis
- ✅ **YOLO Object Detection** - Accurate detection of hands, persons, pizzas, and scoopers
- ✅ **Hand Tracking** - Multi-hand tracking across frames with state management
- ✅ **ROI-based Detection** - Configurable Regions of Interest for ingredient containers
- ✅ **Violation Detection Logic** - Smart detection of scooper usage violations
- ✅ **Database Logging** - SQLite database for violation records
- ✅ **Live Video Streaming** - MJPEG stream with real-time annotations
- ✅ **WebSocket Updates** - Real-time detection updates via WebSocket
- ✅ **REST API** - Complete API for statistics and violation management
- ✅ **Modern Web Interface** - Dark green and white themed UI
- ✅ **Multi-worker Support** - Handles multiple workers simultaneously
- ✅ **Frame Export** - Automatic export of violation frames

## 🏗️ Architecture

The system follows a **microservices architecture** with event-driven communication:

```
Video Source → Frame Reader → Kafka → Detection Service → Kafka → Streaming Service → Frontend
                                                                    ↓
                                                              SQLite Database
```

### Components

1. **Frame Reader Service** - Reads video frames and publishes to Kafka
2. **Detection Service** - YOLO detection, hand tracking, and violation logic
3. **Streaming Service** - REST API, WebSocket, and video streaming
4. **Kafka Message Broker** - Asynchronous message passing
5. **Frontend UI** - Web interface for monitoring
📦 Prerequisites

- Python 3.8 or higher
- Apache Kafka (for microservices mode)
- YOLO model file (`yolo12m-v2 (1).pt`)
- Video file for processing
- 4GB+ RAM recommended
- GPU optional but recommended for faster processing

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd commmmm
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Kafka (Optional - for microservices mode)

If using the full microservices architecture:

1. Download and install Apache Kafka
2. Start Zookeeper:
   ```bash
   bin\windows\zookeeper-server-start.bat config\zookeeper.properties
   ```
3. Start Kafka:
   ```bash
   bin\windows\kafka-server-start.bat config\server.properties
   ```

### 4. Configure Settings

Edit `config/settings.py` to set:
- Video path
- Model path
- ROI coordinates
- Detection thresholds

## 💻 Usage

### Quick Start (Simplified Mode - No Kafka)

The easiest way to run the system:

```bash
python run_web_demo.py
```

Then open your browser to: `http://localhost:3000`

### Full Microservices Mode

1. Start Kafka (Zookeeper + Kafka server)
2. Run all services:
   ```bash
   # Windows
   run_all_services.bat
   
   # Or manually:
   python services/frame_reader/frame_reader.py
   python services/detection/detection_service.py
   python services/streaming/streaming_service.py
   ```

### Web Interface

Access the web interface at `http://localhost:3000` to:
- View live video stream with annotations
- See real-time detection statistics
- Monitor violations
- View violation history

## ⚙️ Configuration

### ROI (Region of Interest) Configuration

Edit `config/settings.py` or `run_web_demo.py`:

```python
ROI = {
    "name": "Protein Container",
    "coords": [400, 250, 515, 590],  # [x1, y1, x2, y2]
    "color": (0, 255, 0)
}
```

### Detection Parameters

```python
# Detection thresholds
MIN_CONSECUTIVE_FRAMES = 3          # Hand must be in ROI for N frames
OVERLAP_RATIO_THRESHOLD = 0.25      # Minimum IoU between hand and ROI
MIN_OVERLAP_AREA = 1500             # Minimum pixel overlap area
SCOOPER_IOU_THRESHOLD = 0.2         # Scooper-hand overlap threshold
VIOLATION_COOLDOWN_FRAMES = 20      # Cooldown between violations
```

## 📡 API Documentation

### REST Endpoints

#### Get System Status
```http
GET /api/status
```

#### Get Violation Statistics
```http
GET /api/violations
```

Response:
```json
{
  "total_violations": 5,
  "last_violation": "2025-01-24T19:30:00"
}
```

#### List Violations
```http
GET /api/violations/list?limit=10
```

#### Clear All Violations
```http
DELETE /api/violations/clear
```

#### Video Stream
```http
GET /stream/video
```
Returns MJPEG video stream

### WebSocket Endpoint

```javascript
const ws = new WebSocket('ws://localhost:3000/ws/detections');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle detection updates
};
```

## 📁 Project Structure

```
commmmm/
├── config/
│   ├── settings.py          # Configuration settings
│   └── roi_config.json      # ROI configurations
├── services/
│   ├── frame_reader/        # Frame reading service
│   ├── detection/           # Detection service
│   └── streaming/           # Streaming service
├── utils/
│   ├── database.py          # Database operations
│   ├── roi_manager.py       # ROI management
│   └── tracker.py           # Object tracking
├── frontend/
│   └── index.html           # Web interface
├── database/
│   ├── violations.db        # SQLite database
│   └── violation_frames/     # Exported violation frames
├── run_web_demo.py          # Simplified standalone runner
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🔍 How It Works

### Detection Flow

1. **Frame Capture** - Video frames are read at configurable frame rate
2. **Object Detection** - YOLO detects hands, persons, pizzas, and scoopers
3. **Hand Tracking** - Each hand is tracked across frames with unique IDs
4. **ROI Intersection** - System checks if hands enter the ROI (protein container)
5. **Scooper Detection** - Checks if a scooper is present with the hand (IoU overlap)
6. **Violation Logic** - If hand in ROI for N consecutive frames without scooper → Violation
7. **Logging** - Violations are saved to database and frames are exported

### Violation Detection Criteria

A violation is triggered when:
- Hand enters ROI (protein container)
- Hand remains in ROI for ≥3 consecutive frames
- No scooper detected with the hand (IoU < 0.2)
- Cooldown period has passed

## 🛠️ Troubleshooting

### Common Issues

**Video not displaying:**
- Wait 10-15 seconds for YOLO model to load
- Check if all services are running
- Verify video path in configuration

**No violations detected:**
- Adjust ROI coordinates to match video
- Lower detection thresholds in settings
- Check if hands are being detected (view console output)

**High CPU usage:**
- Reduce frame rate in settings
- Use GPU if available
- Lower video resolution



## 📊 Performance

- **Processing Speed**: ~5 FPS (configurable)
- **Detection Accuracy**: High (tuned thresholds)
- **Latency**: <1 second for real-time display
- **Memory Usage**: ~2-4GB depending on video resolution

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- YOLO by Ultralytics for object detection
- Apache Kafka for message brokering
- FastAPI for the web framework
- OpenCV for video processing

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Made with ❤️ for pizza store hygiene compliance**

