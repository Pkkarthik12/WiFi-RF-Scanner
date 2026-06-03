import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from scapy.all import sniff, Dot11, Dot11Beacon, Dot11ProbeReq, RadioTap
except ImportError:
    logging.warning("scapy not installed. Please install with: pip install scapy")

try:
    import redis
except ImportError:
    logging.warning("redis not installed. Please install with: pip install redis")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WiFiScanner:
    """
    Captures WiFi packets using scapy, extracts RSSI, MAC, SSID, etc.
    and publishes raw signal data to a Redis queue.
    """
    
    def __init__(self, interface: str = 'wlan0', redis_host: str = 'localhost', redis_port: int = 6379):
        """
        Initialize the WiFi Scanner.
        
        Args:
            interface (str): The network interface to sniff on (must be in monitor mode).
            redis_host (str): Redis server hostname.
            redis_port (int): Redis server port.
        """
        self.interface = interface
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        self.is_running = False
        self._capture_thread: Optional[threading.Thread] = None
        
        # Redis Connection Pooling
        try:
            self.redis_pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=0, decode_responses=True)
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

        self.allowed_bands = ['2.4GHz', '5GHz']
        self.rssi_threshold = -90 # Ignore signals weaker than this
        
    def start_capture(self) -> None:
        """Starts the packet capture in a separate thread."""
        if self.is_running:
            logger.warning("Capture is already running.")
            return
            
        self.is_running = True
        self._capture_thread = threading.Thread(target=self._sniff_packets, daemon=True)
        self._capture_thread.start()
        logger.info(f"Started WiFi capture on interface {self.interface}")

    def stop_capture(self) -> None:
        """Gracefully stops the packet capture."""
        self.is_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
        logger.info("Stopped WiFi capture.")

    def _sniff_packets(self) -> None:
        """Internal sniffing loop using scapy."""
        try:
            # We use a stop_filter to gracefully exit sniff
            sniff(iface=self.interface, prn=self.process_packet, store=False, 
                  stop_filter=lambda x: not self.is_running)
        except Exception as e:
            logger.error(f"Error during packet sniffing: {e}")
            # Retry logic could go here
            if self.is_running:
                time.sleep(5)
                self._sniff_packets()

    def process_packet(self, packet) -> None:
        """
        Process an individual packet captured by scapy.
        """
        if not self.is_running:
            return

        try:
            data = self.extract_signal_data(packet)
            if data:
                self.publish_to_redis(data)
        except Exception as e:
            logger.error(f"Error processing packet: {e}")

    def extract_signal_data(self, packet) -> Optional[Dict[str, Any]]:
        """
        Extracts relevant information from a RadioTap/Dot11 packet.
        """
        if packet.haslayer(Dot11):
            # Extract basic MAC info
            addr1 = packet.addr1 # Destination
            addr2 = packet.addr2 # Source/Transmitter
            addr3 = packet.addr3 # BSSID
            
            if not addr2:
                return None

            rssi = None
            if packet.haslayer(RadioTap):
                # dBm_AntSignal is typical for RSSI in RadioTap
                try:
                    rssi = packet[RadioTap].dBm_AntSignal
                except AttributeError:
                    pass

            if rssi is None or rssi < self.rssi_threshold:
                return None

            ssid = ""
            channel = None
            frequency = None
            
            # Extract SSID from Beacons
            if packet.haslayer(Dot11Beacon):
                try:
                    if packet.info:
                        ssid = packet.info.decode('utf-8', errors='ignore')
                except Exception:
                    pass
                    
            # Simplistic frequency mapping (scapy RadioTap channel freq)
            if packet.haslayer(RadioTap):
                try:
                    frequency = packet[RadioTap].Channel
                    # Very rough channel calculation
                    if frequency:
                        if frequency == 2484:
                            channel = 14
                        elif frequency < 2484:
                            channel = (frequency - 2407) // 5
                        elif frequency >= 5000:
                            channel = (frequency - 5000) // 5
                except AttributeError:
                    pass

            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Format according to spec
            payload = {
                "timestamp": timestamp,
                "access_point": {
                    "mac": addr3 if addr3 else "UNKNOWN", 
                    "ssid": ssid
                },
                "devices": [
                    {
                        "mac": addr2,
                        "rssi": rssi,
                        "channel": channel,
                        "frequency": frequency
                    }
                ]
            }
            return payload
            
        return None

    def publish_to_redis(self, data: Dict[str, Any]) -> None:
        """
        Publishes the extracted data to Redis.
        """
        if not self.redis_client:
            return
            
        try:
            json_data = json.dumps(data)
            self.redis_client.publish('raw_signals', json_data)
            logger.debug(f"Published to Redis: {json_data[:100]}...")
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")

if __name__ == "__main__":
    scanner = WiFiScanner(interface='wlan0mon')
    try:
        scanner.start_capture()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scanner.stop_capture()
