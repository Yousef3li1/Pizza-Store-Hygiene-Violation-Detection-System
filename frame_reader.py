"""
Frame Reader Service
Reads video frames and publishes them to Kafka
"""
import cv2
import json
import base64
import time
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_FRAMES,
    VIDEO_PATH,
    FRAME_RATE,
    LOG_LEVEL
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrameReader:
    """
    Reads video frames and publishes to Kafka
    """
    
    def __init__(self, video_path=None, kafka_servers=None, topic=None, frame_rate=None):
        """
        Initialize Frame Reader
        
        Args:
            video_path: Path to video file or RTSP stream
            kafka_servers: Kafka bootstrap servers
            topic: Kafka topic to publish frames
            frame_rate: Frames per second to process
        """
        self.video_path = video_path or VIDEO_PATH
        self.kafka_servers = kafka_servers or KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or KAFKA_TOPIC_FRAMES
        self.frame_rate = frame_rate or FRAME_RATE
        
        # Initialize Kafka producer
        self.producer = None
        self.init_kafka_producer()
        
        # Video capture
        self.cap = None
        self.frame_number = 0
        self.video_fps = 30
        
    def init_kafka_producer(self):
        """Initialize Kafka producer with retry logic"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    max_request_size=10485760,  # 10MB
                    buffer_memory=33554432,  # 32MB
                    compression_type='gzip',
                    acks=1
                )
                logger.info(f"Successfully connected to Kafka at {self.kafka_servers}")
                return
            except KafkaError as e:
                retry_count += 1
                logger.warning(f"Failed to connect to Kafka (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    logger.error("Failed to connect to Kafka after maximum retries")
                    raise
    
    def open_video(self):
        """Open video file or stream"""
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        # Get video properties
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Video opened: {self.video_path}")
        logger.info(f"Properties - FPS: {self.video_fps}, Frames: {total_frames}, "
                   f"Resolution: {width}x{height}")
        
        return True
    
    def encode_frame(self, frame):
        """
        Encode frame to base64 for Kafka transmission
        
        Args:
            frame: OpenCV frame (numpy array)
        
        Returns:
            Base64 encoded string
        """
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # Convert to base64
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return frame_base64
    
    def publish_frame(self, frame, frame_number, timestamp):
        """
        Publish frame to Kafka
        
        Args:
            frame: OpenCV frame
            frame_number: Frame sequence number
            timestamp: Frame timestamp
        """
        # Encode frame
        frame_encoded = self.encode_frame(frame)
        
        # Create message
        message = {
            'frame_number': frame_number,
            'timestamp': timestamp,
            'frame_data': frame_encoded,
            'width': frame.shape[1],
            'height': frame.shape[0],
            'video_path': self.video_path
        }
        
        # Send to Kafka
        try:
            future = self.producer.send(self.topic, value=message)
            future.get(timeout=10)  # Wait for confirmation
            logger.debug(f"Published frame {frame_number} to Kafka")
        except Exception as e:
            logger.error(f"Failed to publish frame {frame_number}: {e}")
    
    def run(self):
        """
        Main loop - read frames and publish to Kafka
        """
        logger.info("Starting Frame Reader Service")
        
        # Open video
        self.open_video()
        
        # Calculate frame skip based on desired frame rate
        # If video is 30 FPS and we want 5 FPS, skip every 6 frames
        frame_skip = max(1, int(self.video_fps / self.frame_rate))
        
        logger.info(f"Processing every {frame_skip} frames "
                   f"({self.frame_rate} FPS from {self.video_fps} FPS video)")
        
        frame_count = 0
        processed_count = 0
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.info("End of video reached")
                    break
                
                frame_count += 1
                
                # Skip frames based on frame_skip
                if frame_count % frame_skip != 0:
                    continue
                
                processed_count += 1
                timestamp = time.time()
                
                # Publish frame
                self.publish_frame(frame, processed_count, timestamp)
                
                # Log progress every 30 frames
                if processed_count % 30 == 0:
                    logger.info(f"Processed {processed_count} frames "
                               f"(total read: {frame_count})")
                
                # Small delay to avoid overwhelming Kafka
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("Frame reader interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in frame reader: {e}", exc_info=True)
        
        finally:
            self.cleanup()
        
        logger.info(f"Frame Reader completed. Total frames processed: {processed_count}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info("Resources cleaned up")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Frame Reader Service')
    parser.add_argument('--video', type=str, help='Path to video file')
    parser.add_argument('--kafka', type=str, help='Kafka bootstrap servers')
    parser.add_argument('--fps', type=int, help='Frames per second to process')
    
    args = parser.parse_args()
    
    # Create and run frame reader
    frame_reader = FrameReader(
        video_path=args.video,
        kafka_servers=args.kafka,
        frame_rate=args.fps
    )
    
    frame_reader.run()


if __name__ == '__main__':
    main()




