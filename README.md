# 🏠 WiFi RF Signal Scanner - Complete Project Package

## ⚡ What You're Getting

A **complete, production-ready source code package** for building a WiFi-based indoor positioning and home monitoring system that:

- 📍 Detects and tracks all WiFi devices in your home in real-time
- 🗺️ Creates an interactive map showing where people/devices are located
- 📊 Provides analytics on occupancy patterns and device activity
- 🔄 Uses WiFi RF signals (which are always transmitting) to determine locations without special hardware
- 🎯 Accurate to within 1-3 meters indoors using trilateration

---



---

## 💡 How This Project Works (High Level)

```
┌─────────────────────────────────────────────────────────┐
│     WiFi Access Points (Already in your home)           │
│  Broadcasting signals continuously on 2.4GHz/5GHz       │
└──────────────────────┬──────────────────────────────────┘
                       │ (Omnidirectional RF signals)
                       │
┌──────────────────────▼──────────────────────────────────┐
│         WiFi Scanner (Raspberry Pi / Linux PC)          │
│  • Captures WiFi packets in monitor mode                │
│  • Extracts RSSI (signal strength) from each AP         │
│  • Streams data to backend                             │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│          Backend Processing (Python/FastAPI)            │
│  • Signal filtering & smoothing (Kalman filter)        │
│  • Trilateration (3+ access points → position)         │
│  • Device tracking (movement over time)                │
│  • House map generation (zone assignment)              │
│  • REST API + WebSocket (real-time updates)            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│        Frontend Dashboard (Vue 3 / Web Browser)         │
│  • Interactive house map with device positions         │
│  • Real-time updates via WebSocket                     │
│  • Occupancy analytics and heatmaps                    │
│  • Device activity timeline                            │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Technology Stack

**Backend:**
- Python 3.11 + FastAPI (REST API)
- Scapy (WiFi packet capture)
- NumPy/SciPy (Signal processing)
- PostgreSQL (Data storage)
- Redis (Caching & real-time)
- Scikit-learn (ML models)

**Frontend:**
- Vue 3 (User interface)
- Pinia (State management)
- Leaflet/D3.js (Map visualization)
- WebSocket (Real-time updates)

**Deployment:**
- Docker (Containerization)
- Docker Compose (Local development)
- Kubernetes (Cloud deployment - optional)
- Nginx (Reverse proxy)

---

## 📊 Key Features

✅ **Real-time Location Tracking**
- Track devices/people in your home with 1-3 meter accuracy
- No special hardware needed (uses existing WiFi)

✅ **Interactive House Map**
- Draw your floor plan
- Define rooms/zones
- See live positions of all devices
- Heatmaps showing where people spend time

✅ **Activity Analytics**
- Occupancy timeline (how many people, when)
- Device activity logs (who did what, when)
- Movement patterns (common routes)
- Recurring schedules

✅ **Multi-Device Support**
- Track phones, laptops, tablets, IoT devices
- Identify device types automatically
- Device history and statistics

✅ **Production Ready**
- Fully containerized (Docker)
- Scalable architecture
- Monitoring and alerting
- Automatic backups
- CI/CD pipeline included

Open for contributions
