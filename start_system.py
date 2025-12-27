"""
System Startup Helper Script
Starts all microservices in separate processes
"""
import subprocess
import sys
import time
import os
from pathlib import Path

# Set working directory
os.chdir(Path(__file__).parent)

def start_service(name, command, wait=2):
    """
    Start a service in a new PowerShell window
    
    Args:
        name: Service name
        command: Command to run
        wait: Seconds to wait before starting next service
    """
    print(f"Starting {name}...")
    
    # PowerShell command to start service in new window
    ps_command = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd {os.getcwd()}; .\\venv\\Scripts\\activate; {command}"'
    
    subprocess.Popen(
        ['powershell', '-Command', ps_command],
        shell=True
    )
    
    print(f"{name} started in new window")
    time.sleep(wait)


def check_kafka():
    """Check if Kafka is running"""
    print("Checking Kafka connection...")
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(bootstrap_servers='localhost:9092')
        producer.close()
        print("✓ Kafka is running")
        return True
    except Exception as e:
        print(f"✗ Kafka is not running: {e}")
        print("\nPlease start Kafka before running the system:")
        print("1. Start Zookeeper: .\\bin\\windows\\zookeeper-server-start.bat .\\config\\zookeeper.properties")
        print("2. Start Kafka: .\\bin\\windows\\kafka-server-start.bat .\\config\\server.properties")
        return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("🍕 Pizza Store Violation Detection System - Startup")
    print("=" * 60)
    print()
    
    # Check Kafka
    if not check_kafka():
        print("\nPlease start Kafka first, then run this script again.")
        input("Press Enter to exit...")
        return
    
    print("\nStarting all microservices...")
    print("-" * 60)
    
    # Start services
    services = [
        ("Frame Reader Service", "python services/frame_reader/frame_reader.py"),
        ("Detection Service", "python services/detection/detection_service.py"),
        ("Streaming Service", "python services/streaming/streaming_service.py"),
        ("Frontend Server", "cd frontend; python -m http.server 3000"),
    ]
    
    for name, command in services:
        start_service(name, command, wait=2)
    
    print("-" * 60)
    print("\n✓ All services started!")
    print("\nAccess the web interface at: http://localhost:3000")
    print("\nTo stop all services, close the PowerShell windows.")
    print("\nPress Ctrl+C to exit this script.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutdown initiated. Please close the service windows manually.")


if __name__ == "__main__":
    main()




