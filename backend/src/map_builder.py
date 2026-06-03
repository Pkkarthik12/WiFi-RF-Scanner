import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Avoid circular imports by locally redefining or using typing where necessary
# Assume Device and Position are structurally compatible with device_tracker
from .triangulation import Position

@dataclass
class AccessPointDef:
    name: str
    x: float
    y: float
    floor: int

@dataclass
class Zone:
    id: str
    name: str
    zone_type: str
    coordinates: List[Tuple[float, float]] # e.g., [(xmin, ymin), (xmax, ymax)] for rectangle
    parent_zone: Optional[str] = None
    occupancy: List[str] = field(default_factory=list) # List of device IDs
    properties: Dict = field(default_factory=dict)

    def contains_point(self, x: float, y: float) -> bool:
        """Basic rectangular bounds check. Can be expanded to polygon ray-casting."""
        if len(self.coordinates) == 2:
            x_min, y_min = self.coordinates[0]
            x_max, y_max = self.coordinates[1]
            return x_min <= x <= x_max and y_min <= y <= y_max
        return False

@dataclass
class FloorPlan:
    id: str
    name: str
    width: float
    height: float
    unit: str = "meters"
    zones: Dict[str, Zone] = field(default_factory=dict)
    access_points: List[AccessPointDef] = field(default_factory=list)

class HouseMapBuilder:
    """
    Manages the spatial representation of the area, zones, and occupancy.
    """
    def __init__(self):
        self.floorplan: Optional[FloorPlan] = None
        
    def create_floorplan(self, width: float, height: float, unit: str = "meters", name: str = "Main Floor") -> FloorPlan:
        import uuid
        self.floorplan = FloorPlan(id=str(uuid.uuid4()), name=name, width=width, height=height, unit=unit)
        return self.floorplan

    def add_zone(self, name: str, x_min: float, y_min: float, x_max: float, y_max: float, zone_type: str = "room") -> Zone:
        if not self.floorplan:
            raise ValueError("Floorplan not created yet")
            
        import uuid
        zone_id = str(uuid.uuid4())
        zone = Zone(
            id=zone_id,
            name=name,
            zone_type=zone_type,
            coordinates=[(x_min, y_min), (x_max, y_max)]
        )
        self.floorplan.zones[zone_id] = zone
        return zone

    def add_access_point(self, name: str, x: float, y: float, floor: int = 1) -> AccessPointDef:
        if not self.floorplan:
            raise ValueError("Floorplan not created yet")
            
        ap = AccessPointDef(name=name, x=x, y=y, floor=floor)
        self.floorplan.access_points.append(ap)
        return ap

    def assign_device_to_zone(self, device_id: str, position: Position) -> Optional[str]:
        """Finds which zone the device is in and updates occupancy."""
        if not self.floorplan:
            return None
            
        target_zone_id = None
        for z_id, zone in self.floorplan.zones.items():
            if zone.contains_point(position.x, position.y):
                target_zone_id = z_id
                break
                
        # Update occupancy states
        for z_id, zone in self.floorplan.zones.items():
            if z_id == target_zone_id:
                if device_id not in zone.occupancy:
                    zone.occupancy.append(device_id)
            else:
                if device_id in zone.occupancy:
                    zone.occupancy.remove(device_id)
                    
        return target_zone_id

    def generate_occupancy_map(self) -> Dict[str, int]:
        """Returns a count of devices per zone."""
        if not self.floorplan:
            return {}
        return {z_id: len(z.occupancy) for z_id, z in self.floorplan.zones.items()}

    def get_zone_occupancy(self, zone_id: str) -> List[str]:
        if not self.floorplan or zone_id not in self.floorplan.zones:
            return []
        return self.floorplan.zones[zone_id].occupancy

    def generate_heatmap(self, positions: List[Position], resolution: float = 0.5) -> np.ndarray:
        """
        Generates a 2D density heatmap based on a list of positions.
        """
        if not self.floorplan or not positions:
            return np.array([])
            
        grid_w = int(self.floorplan.width / resolution)
        grid_h = int(self.floorplan.height / resolution)
        
        heatmap = np.zeros((grid_h, grid_w))
        
        for p in positions:
            x_idx = int(p.x / resolution)
            y_idx = int(p.y / resolution)
            
            if 0 <= x_idx < grid_w and 0 <= y_idx < grid_h:
                heatmap[y_idx, x_idx] += 1
                
        # Simple smoothing (could use gaussian filter)
        return heatmap

    def detect_movement_pattern(self, device_id: str, trajectory: List[Position]) -> str:
        """Very basic pattern detection placeholder."""
        if len(trajectory) < 10:
            return "stationary"
            
        start = trajectory[0]
        end = trajectory[-1]
        
        dist = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5
        if dist > 2.0:
            return "moving_transit"
        return "loitering"
