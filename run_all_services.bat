@echo off
REM Batch script to start all microservices in separate windows
REM Make sure Kafka is running before executing this script

echo ========================================
echo Pizza Store Violation Detection System
echo ========================================
echo.
echo Starting all microservices...
echo.

REM Check if venv exists
if not exist "venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: .\venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Start Frame Reader Service
echo Starting Frame Reader Service...
start "Frame Reader Service" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python services\frame_reader\frame_reader.py"
timeout /t 2 /nobreak >nul

REM Start Detection Service
echo Starting Detection Service...
start "Detection Service" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python services\detection\detection_service.py"
timeout /t 2 /nobreak >nul

REM Start Streaming Service
echo Starting Streaming Service...
start "Streaming Service" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python services\streaming\streaming_service.py"
timeout /t 2 /nobreak >nul

REM Start Frontend Server
echo Starting Frontend Server...
start "Frontend Server" cmd /k "cd /d %~dp0\frontend && python -m http.server 3000"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Access the web interface at:
echo http://localhost:3000
echo.
echo To stop services, close the command windows
echo.
pause




