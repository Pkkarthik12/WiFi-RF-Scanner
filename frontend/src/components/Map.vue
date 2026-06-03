<template>
  <div class="map-container" @wheel="handleZoom" @mousedown="startPan" @mousemove="pan" @mouseup="endPan" @mouseleave="endPan">
    <!-- Status Bar -->
    <div class="status-bar">
      <span :class="{'connected': isConnected, 'disconnected': !isConnected}">
        {{ isConnected ? '🟢 Connected' : '🔴 Disconnected' }}
      </span>
      <span>Active Devices: {{ devices.length }}</span>
    </div>

    <!-- Map Canvas -->
    <div class="map-view" :style="{ transform: `scale(${viewport.zoom}) translate(${viewport.panX}px, ${viewport.panY}px)` }">
      <svg :width="floorplan.width * scaleFactor" :height="floorplan.height * scaleFactor" class="floorplan-svg">
        
        <!-- Zones -->
        <g v-for="zone in floorplan.zones" :key="zone.id">
          <rect 
            :x="zone.coords[0][0] * scaleFactor" 
            :y="zone.coords[0][1] * scaleFactor"
            :width="(zone.coords[1][0] - zone.coords[0][0]) * scaleFactor" 
            :height="(zone.coords[1][1] - zone.coords[0][1]) * scaleFactor"
            :fill="getZoneColor(zone.id)"
            class="zone-rect"
            @mouseover="hoveredZone = zone.id"
            @mouseleave="hoveredZone = null"
          />
          <text 
            :x="(zone.coords[0][0] + (zone.coords[1][0] - zone.coords[0][0])/2) * scaleFactor"
            :y="(zone.coords[0][1] + (zone.coords[1][1] - zone.coords[0][1])/2) * scaleFactor"
            class="zone-label"
          >{{ zone.name }}</text>
        </g>

        <!-- Devices -->
        <g v-for="device in devices" :key="device.id" 
           @click.stop="selectDevice(device)"
           class="device-marker"
           :class="{'selected': selectedDevice?.id === device.id}">
          
          <!-- Signal Aura -->
          <circle 
            :cx="device.x * scaleFactor" 
            :cy="device.y * scaleFactor" 
            r="15" 
            class="signal-aura" 
          />
          
          <!-- Device Icon (simplified as circle) -->
          <circle 
            :cx="device.x * scaleFactor" 
            :cy="device.y * scaleFactor" 
            r="6" 
            :fill="getDeviceColor(device.type)" 
          />
          
          <!-- Tooltip Hint -->
          <title>{{ device.name || device.mac }}</title>
        </g>
      </svg>
    </div>

    <!-- Info Panel -->
    <div v-if="selectedDevice" class="info-panel">
      <div class="panel-header">
        <h3>Device Info</h3>
        <button @click="selectedDevice = null">✕</button>
      </div>
      <div class="panel-body">
        <p><strong>Name:</strong> {{ selectedDevice.name }}</p>
        <p><strong>Type:</strong> {{ selectedDevice.type }}</p>
        <p><strong>Position:</strong> ({{ selectedDevice.x.toFixed(2) }}, {{ selectedDevice.y.toFixed(2) }})</p>
        <p><strong>Last Seen:</strong> {{ new Date(selectedDevice.last_seen).toLocaleTimeString() }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';

// State
const isConnected = ref(false);
const devices = ref([]);
const floorplan = ref({ width: 20, height: 15, zones: [] });
const selectedDevice = ref(null);
const hoveredZone = ref(null);
const scaleFactor = 40; // Pixels per meter

const viewport = reactive({
  zoom: 1.0,
  panX: 0,
  panY: 0,
  isPanning: false,
  startX: 0,
  startY: 0
});

// Mock Data Load
onMounted(() => {
  // Simulate API fetch
  floorplan.value.zones = [
    { id: '1', name: 'Living Room', coords: [[0, 0], [10, 10]] },
    { id: '2', name: 'Kitchen', coords: [[10, 0], [20, 10]] }
  ];
  
  devices.value = [
    { id: 'a1', name: 'John Phone', type: 'phone', x: 5, y: 5, last_seen: Date.now() },
    { id: 'b2', name: 'Smart TV', type: 'iot', x: 8, y: 2, last_seen: Date.now() }
  ];

  isConnected.value = true;
});

// Interaction Methods
const handleZoom = (e) => {
  e.preventDefault();
  const zoomSpeed = 0.1;
  if (e.deltaY < 0) viewport.zoom = Math.min(viewport.zoom + zoomSpeed, 5.0);
  else viewport.zoom = Math.max(viewport.zoom - zoomSpeed, 0.5);
};

const startPan = (e) => {
  if (e.button !== 0) return; // Only left click
  viewport.isPanning = true;
  viewport.startX = e.clientX - viewport.panX;
  viewport.startY = e.clientY - viewport.panY;
};

const pan = (e) => {
  if (!viewport.isPanning) return;
  viewport.panX = e.clientX - viewport.startX;
  viewport.panY = e.clientY - viewport.startY;
};

const endPan = () => {
  viewport.isPanning = false;
};

const selectDevice = (device) => {
  selectedDevice.value = device;
};

const getDeviceColor = (type) => {
  const colors = { phone: '#3498db', laptop: '#e74c3c', iot: '#f1c40f', unknown: '#95a5a6' };
  return colors[type] || colors.unknown;
};

const getZoneColor = (zoneId) => {
  if (hoveredZone.value === zoneId) return 'rgba(52, 152, 219, 0.3)';
  return 'rgba(236, 240, 241, 0.8)';
};
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background-color: #2c3e50;
  cursor: grab;
}
.map-container:active { cursor: grabbing; }

.status-bar {
  position: absolute;
  top: 10px; left: 10px;
  background: rgba(0,0,0,0.7); color: white;
  padding: 8px 15px; border-radius: 5px;
  z-index: 10; display: flex; gap: 15px;
}

.connected { color: #2ecc71; }
.disconnected { color: #e74c3c; }

.map-view {
  transform-origin: 0 0;
  transition: transform 0.1s ease-out;
}

.floorplan-svg { background: white; box-shadow: 0 0 20px rgba(0,0,0,0.5); margin: 50px; }

.zone-rect { stroke: #bdc3c7; stroke-width: 2; transition: fill 0.2s; }
.zone-label { fill: #7f8c8d; font-family: sans-serif; font-size: 14px; text-anchor: middle; pointer-events: none; }

.device-marker { cursor: pointer; transition: transform 0.3s; }
.device-marker:hover { transform: scale(1.2); }
.device-marker.selected circle:last-child { stroke: #e74c3c; stroke-width: 3; }

.signal-aura { fill: rgba(52, 152, 219, 0.2); animation: pulse 2s infinite; pointer-events: none; }

@keyframes pulse {
  0% { r: 10; opacity: 0.8; }
  100% { r: 25; opacity: 0; }
}

.info-panel {
  position: absolute; top: 10px; right: 10px;
  background: white; border-radius: 8px;
  width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
  z-index: 20;
}
.panel-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 15px; background: #34495e; color: white; border-radius: 8px 8px 0 0;
}
.panel-header h3 { margin: 0; font-size: 16px; }
.panel-header button { background: none; border: none; color: white; cursor: pointer; }
.panel-body { padding: 15px; font-size: 14px; }
.panel-body p { margin: 5px 0; }
</style>
