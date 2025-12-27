# 🚀 Quick Start Guide

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] Apache Kafka running (Zookeeper + Kafka server)
- [ ] Model file: `yolo12m-v2 (1).pt` in project root
- [ ] Video file: `Sah w b3dha ghalt (2).mp4` in project root

## Step 1: Install Dependencies

```powershell
cd C:\commmmm
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Start Kafka

### Terminal 1 - Zookeeper
```powershell
cd C:\kafka
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

### Terminal 2 - Kafka Server
```powershell
cd C:\kafka
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

## Step 3: Verify Setup

```powershell
cd C:\commmmm
.\venv\Scripts\activate
python check_setup.py
```

Make sure all checks pass! ✓

## Step 4: Start the System

### Option A: Automated (Recommended)
```powershell
python start_system.py
```

This will open all services in separate windows.

### Option B: Manual

**Terminal 3 - Frame Reader**
```powershell
cd C:\commmmm
.\venv\Scripts\activate
python services/frame_reader/frame_reader.py
```

**Terminal 4 - Detection Service**
```powershell
cd C:\commmmm
.\venv\Scripts\activate
python services/detection/detection_service.py
```

**Terminal 5 - Streaming Service**
```powershell
cd C:\commmmm
.\venv\Scripts\activate
python services/streaming/streaming_service.py
```

**Terminal 6 - Frontend**
```powershell
cd C:\commmmm\frontend
python -m http.server 3000
```

## Step 5: Access the Web Interface

Open your browser to: **http://localhost:3000**

You should see:
- Live video feed with detections
- Real-time violation count
- List of recent violations
- Object detection statistics

## 🎯 What to Expect

1. **Video Stream**: Shows annotated video with bounding boxes
   - 🟢 Green boxes = Hands with scooper
   - 🟡 Yellow boxes = Hands without scooper
   - 🔵 Blue boxes = Pizzas
   - 🔴 Red boxes = Scoopers
   - 🟢 Green rectangles = ROIs (Regions of Interest)

2. **Violations**: System will detect when:
   - Hand enters ROI (protein container) WITHOUT scooper
   - Then hand moves to pizza
   - → **VIOLATION LOGGED**

3. **Statistics**: Real-time updates on:
   - Total violations count
   - Currently detected objects
   - Violation history

## 🔧 Troubleshooting

### Video not showing?
- Wait 10-15 seconds for services to initialize
- Click "Refresh Stream" button
- Check all services are running without errors

### No detections?
- Verify model path is correct
- Check video file is playing (check Frame Reader logs)
- Lower confidence threshold in `config/settings.py`

### Kafka errors?
- Ensure both Zookeeper AND Kafka are running
- Check ports 2181 (Zookeeper) and 9092 (Kafka) are not in use
- Try restarting Kafka services

### High CPU usage?
- Reduce FRAME_RATE in config/settings.py (default: 5 fps)
- Close unnecessary programs
- Use a shorter video for testing

## 📊 Testing with Sample Video

The included video `Sah w b3dha ghalt (2).mp4` has **2 real violations**.

Watch the system detect them!

## 🎨 Customization

### Change ROI (Region of Interest)

Edit `config/settings.py`:
```python
DEFAULT_ROIS = [
    {
        "name": "Protein Container",
        "coords": [400, 300, 700, 500],  # Adjust these coordinates
        "color": (0, 255, 0)
    }
]
```

### Use Different Video

```powershell
$env:VIDEO_PATH = "C:\path\to\your\video.mp4"
python services/frame_reader/frame_reader.py
```

### Adjust Detection Sensitivity

Edit `config/settings.py`:
```python
CONFIDENCE_THRESHOLD = 0.4  # Lower = more detections
HAND_IN_ROI_THRESHOLD = 0.3  # Lower = easier to trigger ROI
SCOOPER_NEAR_HAND_THRESHOLD = 100  # Pixels distance
```

## 📝 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Check violation images in `database/violation_frames/`
- Review SQLite database: `database/violations.db`

## 🛑 Stopping the System

1. Press `Ctrl+C` in each terminal
2. Or close the PowerShell windows
3. Kafka can keep running in the background

## 📞 Need Help?

Check the logs in each service terminal for error messages.

Common solutions:
1. Restart Kafka
2. Delete `database/violations.db` and restart
3. Verify all file paths in config/settings.py
4. Run `python check_setup.py` again

---

**Enjoy monitoring your pizza store! 🍕**




