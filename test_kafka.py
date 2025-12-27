"""
Test Kafka Connection
Simple script to verify Kafka is accessible
"""
import sys

def test_kafka_connection():
    """Test Kafka connection"""
    print("Testing Kafka connection...")
    print("-" * 60)
    
    try:
        from kafka import KafkaProducer, KafkaConsumer
        from kafka.errors import KafkaError
        import time
        
        # Test Producer
        print("\n1. Testing Kafka Producer...")
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            request_timeout_ms=5000
        )
        
        # Send test message
        print("   Sending test message...")
        future = producer.send('test-topic', b'test message')
        
        try:
            record_metadata = future.get(timeout=10)
            print(f"   ✓ Message sent successfully")
            print(f"   Topic: {record_metadata.topic}")
            print(f"   Partition: {record_metadata.partition}")
            print(f"   Offset: {record_metadata.offset}")
        except Exception as e:
            print(f"   ✗ Failed to send message: {e}")
            producer.close()
            return False
        
        producer.flush()
        producer.close()
        print("   ✓ Producer test passed")
        
        # Test Consumer
        print("\n2. Testing Kafka Consumer...")
        consumer = KafkaConsumer(
            'test-topic',
            bootstrap_servers='localhost:9092',
            auto_offset_reset='latest',
            consumer_timeout_ms=2000,
            group_id='test-group'
        )
        
        print("   ✓ Consumer created successfully")
        consumer.close()
        print("   ✓ Consumer test passed")
        
        print("\n" + "=" * 60)
        print("✓ Kafka connection successful!")
        print("=" * 60)
        
        return True
        
    except ImportError:
        print("✗ kafka-python package not installed")
        print("\nInstall it with:")
        print("  pip install kafka-python")
        return False
    
    except KafkaError as e:
        print(f"\n✗ Kafka connection failed: {e}")
        print("\nMake sure Kafka is running:")
        print("1. Start Zookeeper:")
        print("   .\\bin\\windows\\zookeeper-server-start.bat .\\config\\zookeeper.properties")
        print("2. Start Kafka:")
        print("   .\\bin\\windows\\kafka-server-start.bat .\\config\\server.properties")
        return False
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("Kafka Connection Test")
    print("=" * 60)
    
    success = test_kafka_connection()
    
    if success:
        sys.exit(0)
    else:
        print("\nPlease fix the issues and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()




