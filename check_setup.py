"""
Setup Verification Script
Checks if all dependencies and resources are available
"""
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8 or higher is required")
        return False
    
    print("✓ Python version OK")
    return True


def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} installed")
        return True
    except ImportError:
        print(f"✗ {package_name} not installed")
        return False


def check_packages():
    """Check all required packages"""
    print("\nChecking Python packages...")
    print("-" * 60)
    
    packages = [
        ('ultralytics', 'ultralytics'),
        ('opencv-python', 'cv2'),
        ('kafka-python', 'kafka'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('torch', 'torch'),
        ('numpy', 'numpy'),
    ]
    
    all_ok = True
    for package_name, import_name in packages:
        if not check_package(package_name, import_name):
            all_ok = False
    
    return all_ok


def check_files():
    """Check if required files exist"""
    print("\nChecking required files...")
    print("-" * 60)
    
    files = [
        (r'yolo12m-v2 (1).pt', 'YOLO Model'),
        (r'Sah w b3dha ghalt (2).mp4', 'Sample Video'),
    ]
    
    all_ok = True
    for file_path, description in files:
        path = Path(file_path)
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"✓ {description}: {file_path} ({size_mb:.1f} MB)")
        else:
            print(f"✗ {description} not found: {file_path}")
            all_ok = False
    
    return all_ok


def check_kafka():
    """Check if Kafka is accessible"""
    print("\nChecking Kafka...")
    print("-" * 60)
    
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            request_timeout_ms=5000
        )
        producer.close()
        print("✓ Kafka is running on localhost:9092")
        return True
    except Exception as e:
        print(f"✗ Cannot connect to Kafka: {e}")
        print("\nTo start Kafka:")
        print("1. Start Zookeeper:")
        print("   .\\bin\\windows\\zookeeper-server-start.bat .\\config\\zookeeper.properties")
        print("2. Start Kafka:")
        print("   .\\bin\\windows\\kafka-server-start.bat .\\config\\server.properties")
        return False


def check_structure():
    """Check project structure"""
    print("\nChecking project structure...")
    print("-" * 60)
    
    directories = [
        'config',
        'services/frame_reader',
        'services/detection',
        'services/streaming',
        'frontend',
        'utils',
        'database'
    ]
    
    all_ok = True
    for directory in directories:
        path = Path(directory)
        if path.exists() and path.is_dir():
            print(f"✓ {directory}/")
        else:
            print(f"✗ {directory}/ missing")
            all_ok = False
    
    return all_ok


def main():
    """Main verification"""
    print("=" * 60)
    print("🍕 Pizza Store Violation Detection System - Setup Check")
    print("=" * 60)
    
    results = []
    
    # Check Python version
    results.append(("Python Version", check_python_version()))
    
    # Check project structure
    results.append(("Project Structure", check_structure()))
    
    # Check files
    results.append(("Required Files", check_files()))
    
    # Check packages
    results.append(("Python Packages", check_packages()))
    
    # Check Kafka
    results.append(("Kafka Connection", check_kafka()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, status in results:
        status_str = "✓ OK" if status else "✗ FAILED"
        print(f"{name:.<40} {status_str}")
    
    all_ok = all(status for _, status in results)
    
    print("=" * 60)
    
    if all_ok:
        print("\n✓ All checks passed! System is ready to run.")
        print("\nTo start the system:")
        print("  python start_system.py")
        print("\nOr start services manually (see README.md)")
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        print("\nTo install missing packages:")
        print("  pip install -r requirements.txt")
    
    print()


if __name__ == "__main__":
    main()




