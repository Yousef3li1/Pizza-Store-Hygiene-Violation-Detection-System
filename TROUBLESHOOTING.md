# 🔧 Troubleshooting Guide

Common issues and their solutions for the Pizza Store Violation Detection System.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Kafka Issues](#kafka-issues)
- [Video Processing Issues](#video-processing-issues)
- [Detection Issues](#detection-issues)
- [Frontend Issues](#frontend-issues)
- [Performance Issues](#performance-issues)
- [Database Issues](#database-issues)

---

## Installation Issues

### Python Version Error

**Problem**: "Python 3.8 or higher is required"

**Solution**:
1. Check your Python version: `python --version`
2. If too old, download Python 3.8+ from python.org
3. Make sure Python is in your PATH

### Pip Install Fails

**Problem**: `pip install -r requirements.txt` fails

**Solutions**:

**For PyTorch installation issues**:
```powershell
# Install PyTorch separately first
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Then install other requirements
pip install -r requirements.txt
```

**For ultralytics issues**:
```powershell
pip install ultralytics --no-deps
pip install -r requirements.txt
```

**For general issues**:
```powershell
# Update pip first
python -m pip install --upgrade pip

# Clear pip cache
pip cache purge

# Try installing again
pip install -r requirements.txt
```

### Virtual Environment Activation Fails

**Problem**: `.\venv\Scripts\activate` not working

**Solution**:

**PowerShell Execution Policy**:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.\venv\Scripts\activate
```

**Alternative activation**:
```powershell
# Use activate.bat instead
.\venv\Scripts\activate.bat
```

---

## Kafka Issues

### Cannot Connect to Kafka

**Problem**: "Connection refused" or "Kafka not available"

**Solutions**:

**1. Check if Kafka is running**:
```powershell
# Test Kafka connection
python test_kafka.py
```

**2. Start Kafka services**:

Terminal 1 - Zookeeper:
```powershell
cd C:\kafka
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

Terminal 2 - Kafka:
```powershell
cd C:\kafka
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

**3. Check ports**:
- Zookeeper: Port 2181
- Kafka: Port 9092

```powershell
# Check if ports are in use
netstat -ano | findstr "2181"
netstat -ano | findstr "9092"
```

**4. Firewall issues**:
- Allow Java through Windows Firewall
- Allow ports 2181 and 9092

### Kafka Timeout Errors

**Problem**: "Request timeout" or "Future timeout"

**Solutions**:

1. **Increase timeouts** in config:
```python
# config/settings.py
KAFKA_REQUEST_TIMEOUT = 30000  # 30 seconds
```

2. **Check Kafka logs**:
```powershell
# In Kafka directory
type logs\server.log
```

3. **Restart Kafka**:
- Stop Kafka server
- Stop Zookeeper
- Start Zookeeper
- Start Kafka server

### Message Too Large Error

**Problem**: "Message size too large"

**Solution**:

Increase Kafka message size in `config/server.properties`:
```properties
message.max.bytes=10485760
replica.fetch.max.bytes=10485760
```

Restart Kafka after changing config.

---

## Video Processing Issues

### Video File Not Found

**Problem**: "Cannot open video: [path]"

**Solutions**:

1. **Check file path**:
```powershell
# Verify file exists
Test-Path "C:\commmmm\Sah w b3dha ghalt (2).mp4"
```

2. **Use absolute path**:
```python
# config/settings.py
VIDEO_PATH = r'C:\commmmm\Sah w b3dha ghalt (2).mp4'
```

3. **Check file permissions**:
- Right-click file → Properties → Security
- Ensure your user has Read permission

### Video Won't Play / Black Screen

**Problem**: Video file exists but won't play

**Solutions**:

1. **Check video codec**:
```powershell
# Install VLC or MediaInfo to check codec
```

2. **Re-encode video** (if needed):
```powershell
# Using ffmpeg
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

3. **Try different video**:
- Use a simpler codec (H.264)
- Lower resolution
- Shorter duration

### Frame Rate Too Low

**Problem**: Video processing is very slow

**Solutions**:

1. **Adjust frame rate**:
```python
# config/settings.py
FRAME_RATE = 2  # Process 2 fps instead of 5
```

2. **Check system resources**:
- Close other applications
- Check CPU usage in Task Manager

---

## Detection Issues

### Model Loading Failed

**Problem**: "Failed to load YOLO model"

**Solutions**:

1. **Verify model file exists**:
```powershell
Test-Path "C:\commmmm\yolo12m-v2 (1).pt"
```

2. **Check model file size**:
- Should be several hundred MB
- If too small, file may be corrupted

3. **Re-download model** (if available)

4. **Check ultralytics version**:
```powershell
pip install ultralytics --upgrade
```

### No Objects Detected

**Problem**: System runs but detects no objects

**Solutions**:

1. **Lower confidence threshold**:
```python
# config/settings.py
CONFIDENCE_THRESHOLD = 0.3  # Lower from 0.4
```

2. **Check model classes**:
```python
# In Detection Service, add logging
print(f"Model classes: {self.model.names}")
```

3. **Test with sample image**:
```python
from ultralytics import YOLO
model = YOLO(r'C:\commmmm\yolo12m-v2 (1).pt')
results = model('test_image.jpg')
print(results[0].boxes)
```

### No Violations Detected

**Problem**: Objects detected but no violations

**Solutions**:

1. **Adjust ROI coordinates**:
```python
# config/settings.py
DEFAULT_ROIS = [
    {
        "name": "Protein Container",
        "coords": [100, 100, 400, 400],  # Adjust these
        "color": (0, 255, 0)
    }
]
```

2. **Lower thresholds**:
```python
# config/settings.py
HAND_IN_ROI_THRESHOLD = 0.2  # Lower from 0.3
SCOOPER_NEAR_HAND_THRESHOLD = 150  # Increase from 100
```

3. **Enable debug logging**:
```python
# config/settings.py
LOG_LEVEL = 'DEBUG'
```

4. **Check hand tracking**:
- Review logs for hand state changes
- Verify hands are being tracked

### False Positives

**Problem**: Too many incorrect violations

**Solutions**:

1. **Increase confidence threshold**:
```python
CONFIDENCE_THRESHOLD = 0.5  # Increase from 0.4
```

2. **Adjust tracking history**:
```python
TRACKING_HISTORY_FRAMES = 50  # Increase from 30
```

3. **Tighten ROI intersection**:
```python
HAND_IN_ROI_THRESHOLD = 0.4  # Increase from 0.3
```

---

## Frontend Issues

### Page Won't Load

**Problem**: http://localhost:3000 doesn't load

**Solutions**:

1. **Check if frontend server is running**:
```powershell
netstat -ano | findstr "3000"
```

2. **Start frontend server**:
```powershell
cd frontend
python -m http.server 3000
```

3. **Try different port**:
```powershell
python -m http.server 8080
# Then access: http://localhost:8080
```

4. **Check firewall**:
- Allow port 3000 in Windows Firewall

### Video Stream Not Showing

**Problem**: Web page loads but no video

**Solutions**:

1. **Check Streaming Service**:
```powershell
# Visit directly
curl http://localhost:8000/api/status
```

2. **Check browser console**:
- Press F12
- Look for errors in Console tab
- Check Network tab for failed requests

3. **Verify services are running**:
- Frame Reader Service
- Detection Service
- Streaming Service

4. **Clear browser cache**:
- Ctrl + Shift + Delete
- Clear cached images and files

5. **Try different browser**:
- Chrome
- Firefox
- Edge

### WebSocket Connection Failed

**Problem**: "WebSocket disconnected" in console

**Solutions**:

1. **Check Streaming Service logs**:
- Look for WebSocket connection errors

2. **Check WebSocket URL**:
```javascript
// In frontend/index.html
ws://localhost:8000/ws/detections
```

3. **Firewall blocking WebSocket**:
- Allow port 8000 in firewall

4. **Try polling instead** (modify frontend):
```javascript
// Replace WebSocket with periodic polling
setInterval(loadLatestFrame, 1000);
```

### CORS Errors

**Problem**: "CORS policy" errors in browser console

**Solution**:

Already configured in Streaming Service, but if issues persist:

```python
# services/streaming/streaming_service.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Performance Issues

### High CPU Usage

**Problem**: CPU at 100%

**Solutions**:

1. **Reduce frame rate**:
```python
FRAME_RATE = 2  # Lower value
```

2. **Use smaller model**:
- YOLO nano instead of medium (if available)

3. **Increase frame skip**:
```python
# Process every 10th frame instead of every 6th
```

4. **Limit Kafka batch size**:
```python
max_poll_records=1
```

### High Memory Usage

**Problem**: Memory keeps growing

**Solutions**:

1. **Reduce queue sizes**:
```python
# In streaming service
frame_queue = Queue(maxsize=10)  # Reduce from 30
```

2. **Limit tracking history**:
```python
TRACKING_HISTORY_FRAMES = 15  # Reduce from 30
```

3. **Clear old data**:
```python
# Periodically clear violations
# Via API: DELETE /api/violations/clear
```

4. **Restart services periodically**:
- For long-running operations

### Slow Detection

**Problem**: Detection is laggy

**Solutions**:

1. **GPU acceleration** (if available):
```python
# YOLO will automatically use GPU if available
# Ensure CUDA is installed
```

2. **Reduce image resolution**:
```python
# Resize frames before detection
frame = cv2.resize(frame, (640, 480))
```

3. **Optimize YOLO settings**:
```python
# Use smaller input size
results = model(frame, imgsz=640)  # Default is 640
```

---

## Database Issues

### Database Locked

**Problem**: "Database is locked"

**Solutions**:

1. **Close other connections**:
- Stop all services
- Delete `violations.db` file
- Restart services

2. **Increase timeout**:
```python
# utils/database.py
conn = sqlite3.connect(self.db_path, timeout=30.0)
```

### Database File Not Created

**Problem**: `violations.db` not appearing

**Solutions**:

1. **Check permissions**:
- Ensure write permission in `database/` folder

2. **Create directory manually**:
```powershell
New-Item -ItemType Directory -Path "database" -Force
```

3. **Check database path**:
```python
# config/settings.py
DB_PATH = r'C:\commmmm\database\violations.db'
```

### Cannot Read Violation Images

**Problem**: Saved violation frames not accessible

**Solutions**:

1. **Check directory exists**:
```powershell
Test-Path "database\violation_frames"
```

2. **Create directory**:
```powershell
New-Item -ItemType Directory -Path "database\violation_frames" -Force
```

3. **Check disk space**:
- Ensure enough space for images

---

## General Debugging Tips

### Enable Debug Logging

```python
# config/settings.py
LOG_LEVEL = 'DEBUG'
```

### Check Service Logs

Each service prints logs to its terminal. Look for:
- ERROR messages (red)
- WARNING messages (yellow)
- Exception tracebacks

### Test Individual Components

1. **Test Kafka**:
```powershell
python test_kafka.py
```

2. **Test Setup**:
```powershell
python check_setup.py
```

3. **Test Model**:
```python
from ultralytics import YOLO
model = YOLO('yolo12m-v2 (1).pt')
print(model.names)
```

### Clean Start

If all else fails:

1. Stop all services
2. Delete `database/violations.db`
3. Restart Kafka
4. Clear Kafka topics:
   ```powershell
   # In Kafka directory
   .\bin\windows\kafka-topics.bat --delete --topic video-frames --bootstrap-server localhost:9092
   .\bin\windows\kafka-topics.bat --delete --topic detections --bootstrap-server localhost:9092
   ```
5. Restart all services

---

## Getting More Help

If issues persist:

1. Check the logs for specific error messages
2. Review the [README.md](README.md) for setup instructions
3. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for system understanding
4. Check GitHub Issues (if applicable)
5. Search for specific error messages online

---

**Remember**: Most issues are due to:
- Kafka not running
- Incorrect file paths
- Missing dependencies
- Firewall blocking ports

Always check these first! 🔍




