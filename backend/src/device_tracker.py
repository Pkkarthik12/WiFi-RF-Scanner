import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging

from .triangulation import Position
from .signal_processor import KalmanFilter, SignalReading

logger = logging.getLogger(__name__)

@dataclass
class ActivityEvent:
    device_id: str
    event_type: str  # entered, exited, stationary, moving
    location: Position
    zone_id: str
    timestamp: datetime
    duration: float = 0.0

@dataclass
class Device:
    id: str
    mac_address: str
    name: str = "Unknown Device"
    device_type: str = "unknown"
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    current_position: Optional[Position] = None
    position_history: List[Position] = field(default_factory=list)
    
    # Tracking state
    kalman_filter_x: KalmanFilter = field(default_factory=lambda: KalmanFilter(process_noise=1e-3, measurement_noise=1e-1))
    kalman_filter_y: KalmanFilter = field(default_factory=lambda: KalmanFilter(process_noise=1e-3, measurement_noise=1e-1))
    
    confidence_history: List[float] = field(default_factory=list)
    velocity: Tuple[float, float] = (0.0, 0.0)
    current_zone_id: Optional[str] = None


class DeviceTracker:
    """
    Manages active devices, tracking their state and position over time.
    """
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.mac_to_id: Dict[str, str] = {}
        self.activity_log: List[ActivityEvent] = []
        
        # Configuration
        self.stale_timeout_seconds = 300 # 5 minutes

    def detect_new_device(self, mac_address: str) -> Device:
        """Registers a new device or returns an existing one based on MAC."""
        if mac_address in self.mac_to_id:
            device_id = self.mac_to_id[mac_address]
            device = self.devices[device_id]
            device.is_active = True
            device.last_seen = datetime.now()
            return device
            
        device_id = str(uuid.uuid4())
        new_device = Device(
            id=device_id,
            mac_address=mac_address,
        )
        # Simple inference based on OUI could go here for device_type
        
        self.devices[device_id] = new_device
        self.mac_to_id[mac_address] = device_id
        logger.info(f"Detected new device: {mac_address} -> {device_id}")
        return new_device

    def update_device_position(self, device_id: str, new_position: Position):
        """Updates the device position using Kalman filtering to smooth the path."""
        if device_id not in self.devices:
            logger.warning(f"Attempted to update unknown device: {device_id}")
            return
            
        device = self.devices[device_id]
        
        # Time delta since last update
        dt = 1.0
        if device.current_position:
            dt_seconds = (new_position.timestamp - device.current_position.timestamp).total_seconds()
            dt = max(0.1, dt_seconds)
            
            # Predict
            device.kalman_filter_x.predict(dt=dt)
            device.kalman_filter_y.predict(dt=dt)
            
        # Update filter with measurement
        device.kalman_filter_x.update(new_position.x)
        device.kalman_filter_y.update(new_position.y)
        
        # Get smoothed state
        smoothed_x = device.kalman_filter_x.get_state()
        smoothed_y = device.kalman_filter_y.get_state()
        
        # Calculate velocity
        if device.current_position:
            vx = (smoothed_x - device.current_position.x) / dt
            vy = (smoothed_y - device.current_position.y) / dt
            device.velocity = (vx, vy)
            
            # Activity detection (stationary vs moving)
            speed = (vx**2 + vy**2)**0.5
            event_type = "moving" if speed > 0.5 else "stationary"
            
            # Simplified event logging (could be optimized)
            if not self.activity_log or self.activity_log[-1].event_type != event_type or self.activity_log[-1].device_id != device_id:
                self.activity_log.append(ActivityEvent(
                    device_id=device_id,
                    event_type=event_type,
                    location=new_position,
                    zone_id=device.current_zone_id or "unknown",
                    timestamp=datetime.now()
                ))

        smoothed_pos = Position(
            x=smoothed_x,
            y=smoothed_y,
            z=new_position.z,
            timestamp=new_position.timestamp,
            confidence=new_position.confidence,
            error_estimate=new_position.error_estimate
        )
        
        device.current_position = smoothed_pos
        device.position_history.append(smoothed_pos)
        device.confidence_history.append(new_position.confidence)
        device.last_seen = datetime.now()
        
        # Keep history bounded
        if len(device.position_history) > 1000:
            device.position_history = device.position_history[-1000:]
            
    def track_device(self, device_id: str, position: Position, rssi_readings: List[SignalReading]) -> Optional[Device]:
        """Main entry point to update tracking state with new measurements."""
        if device_id not in self.devices:
            return None
            
        self.update_device_position(device_id, position)
        return self.devices[device_id]

    def remove_stale_device(self, device_id: str, timeout_seconds: int = 300):
        """Marks a device as inactive if not seen recently."""
        if device_id in self.devices:
            device = self.devices[device_id]
            time_since_last_seen = (datetime.now() - device.last_seen).total_seconds()
            if time_since_last_seen > timeout_seconds:
                device.is_active = False
                logger.info(f"Device {device_id} marked as stale.")

    def get_active_devices(self) -> List[Device]:
        """Returns all currently active devices."""
        # Run cleanup first
        for dev_id in list(self.devices.keys()):
            self.remove_stale_device(dev_id, self.stale_timeout_seconds)
            
        return [d for d in self.devices.values() if d.is_active]

    def get_device_trajectory(self, device_id: str, time_window: timedelta) -> List[Position]:
        """Gets position history within a time window."""
        if device_id not in self.devices:
            return []
            
        device = self.devices[device_id]
        cutoff_time = datetime.now() - time_window
        return [p for p in device.position_history if p.timestamp >= cutoff_time]
