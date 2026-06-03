import asyncio
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# Import internal modules (simulated here)
# In production, these would be proper imports linked to state singletons
from .device_tracker import DeviceTracker
from .map_builder import HouseMapBuilder

app = FastAPI(title="WiFi Positioning API", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulated Singletons
tracker = DeviceTracker()
map_builder = HouseMapBuilder()

# Pre-populate some map data
map_builder.create_floorplan(20.0, 15.0)
map_builder.add_zone("Living Room", 0, 0, 10, 10)
map_builder.add_zone("Kitchen", 10, 0, 20, 10)

class NameUpdateRequest(BaseModel):
    name: str

class ZoneCreateRequest(BaseModel):
    name: str
    zone_type: str
    coordinates: List[List[float]]
    parent_zone: str = None

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "uptime": "10h",
        "active_devices": len(tracker.get_active_devices())
    }

@app.get("/api/devices")
async def get_devices(active_only: bool = True):
    devices = tracker.get_active_devices() if active_only else list(tracker.devices.values())
    
    response = []
    for d in devices:
        response.append({
            "id": d.id,
            "mac": d.mac_address,
            "name": d.name,
            "type": d.device_type,
            "is_active": d.is_active,
            "last_seen": d.last_seen.isoformat(),
            "position": {"x": d.current_position.x, "y": d.current_position.y} if d.current_position else None
        })
    return {"devices": response, "total": len(response)}

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    if device_id not in tracker.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    d = tracker.devices[device_id]
    return {
        "id": d.id,
        "mac": d.mac_address,
        "name": d.name,
        "position": {"x": d.current_position.x, "y": d.current_position.y} if d.current_position else None,
        "zone": d.current_zone_id
    }

@app.post("/api/devices/{device_id}/update_name")
async def update_device_name(device_id: str, request: NameUpdateRequest):
    if device_id not in tracker.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    tracker.devices[device_id].name = request.name
    return {"status": "success"}

@app.get("/api/zones")
async def get_zones():
    zones = []
    if map_builder.floorplan:
        for z in map_builder.floorplan.zones.values():
            zones.append({
                "id": z.id,
                "name": z.name,
                "type": z.zone_type,
                "coordinates": z.coordinates
            })
    return {"zones": zones}

@app.get("/api/map")
async def get_map_state():
    fp = map_builder.floorplan
    if not fp:
        return {"error": "No map configured"}
        
    return {
        "floorplan": {
            "width": fp.width,
            "height": fp.height
        },
        "zones": [{"id": z.id, "name": z.name, "coords": z.coordinates} for z in fp.zones.values()],
        "devices": [{"id": d.id, "x": d.current_position.x, "y": d.current_position.y} for d in tracker.get_active_devices() if d.current_position]
    }

# --- WebSocket for real-time updates ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client pings
            data = await websocket.receive_text()
            # In a real app, a background task would broadcast position updates here
    except WebSocketDisconnect:
        manager.disconnect(websocket)
