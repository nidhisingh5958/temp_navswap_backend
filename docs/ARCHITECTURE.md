# NavSwap Backend - System Architecture

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Consumer │  │  Staff   │  │Transporter│  │    Admin     │  │
│  │   App    │  │   App    │  │    App    │  │  Dashboard   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
└───────┼─────────────┼──────────────┼────────────────┼──────────┘
        │             │              │                │
        └─────────────┴──────────────┴────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │      FASTAPI BACKEND (PORT 8000)    │
        │  ┌────────────────────────────────┐ │
        │  │     Route Layer (REST APIs)    │ │
        │  │  - Queue Routes                │ │
        │  │  - QR Routes                   │ │
        │  │  - Swap Routes                 │ │
        │  │  - Transport Routes            │ │
        │  │  - Staff Routes                │ │
        │  │  - Admin Routes                │ │
        │  │  - AI Prediction Routes        │ │
        │  │  - Recommendation Routes       │ │
        │  └────────────┬───────────────────┘ │
        │               │                      │
        │  ┌────────────▼───────────────────┐ │
        │  │     Service Layer              │ │
        │  │  - AI Service (13 Models)     │ │
        │  │  - Queue Service              │ │
        │  │  - QR Service                 │ │
        │  │  - Location Service           │ │
        │  │  - Logistics Service          │ │
        │  │  - Staff Service              │ │
        │  │  - Fault Service              │ │
        │  └────────────┬───────────────────┘ │
        └───────────────┼──────────────────────┘
                        │
        ┌───────────────┼──────────────────────┐
        │        DATA PERSISTENCE LAYER        │
        │                                      │
        │  ┌──────────┐  ┌─────────┐  ┌──────┐│
        │  │ MongoDB  │  │  Redis  │  │Kafka ││
        │  │ (Primary)│  │ (Cache) │  │Events││
        │  └──────────┘  └─────────┘  └──────┘│
        └──────────────────────────────────────┘
```

---

## 📦 Component Details

### 1. API Layer (FastAPI)

**Queue Management APIs**
- `POST /queue/confirm` - Reserve queue slot
- `GET /queue/status/{station_id}` - Get queue status
- `GET /queue/available-slots/{station_id}` - Check availability

**QR Operations**
- `POST /qr/verify` - Verify QR token
- `GET /qr/generate-image/{token}` - Generate QR image

**Swap Operations**
- `POST /swap/complete` - Complete battery swap
- `GET /swap/{swap_id}` - Get swap details
- `GET /swap/user/{user_id}` - User swap history

**Station APIs**
- `GET /station/{station_id}/status` - Station details
- `GET /station/list` - List all stations
- `GET /station/nearest` - Find nearest stations

**Transport & Logistics**
- `POST /transport/job/accept` - Accept transport job
- `POST /transport/job/{id}/complete` - Complete job
- `GET /transport/jobs/available` - Available jobs
- `GET /transport/history/{transporter_id}` - Job history

**Staff Management**
- `GET /staff/assignments/{staff_id}` - Staff assignments
- `POST /staff/diversion` - Divert staff between stations
- `GET /staff/station/{station_id}` - Station staff list

**Admin Dashboard**
- `GET /admin/live` - Real-time dashboard
- `GET /admin/logistics` - Logistics overview
- `GET /admin/traffic` - Traffic analysis
- `GET /admin/stations/overview` - All stations overview

**AI Predictions (13 Models)**
- `POST /ai/predict-load` - Load prediction
- `POST /ai/predict-fault` - Fault prediction
- `POST /ai/predict-action` - Action recommendation
- `POST /ai/forecast-traffic` - Traffic forecast
- `POST /ai/predict-rebalancing` - Battery rebalancing
- `GET /ai/model-status` - Model health check
- _+ 7 more model endpoints_

**Recommendations**
- `POST /recommend` - Get station recommendations
- `GET /recommend/optimal` - Get optimal station

---

### 2. Service Layer

**AI Service** (`ai_service.py`)
- Loads 13 ML models at startup
- Provides predictions with fallback heuristics
- Model registry and health monitoring

**Queue Service** (`queue_service.py`)
- Queue position management
- Wait time calculations
- Redis-based real-time tracking
- Queue capacity enforcement

**QR Service** (`qr_service.py`)
- QR token generation with signatures
- Time-bound token validation
- QR image generation
- Token expiry management

**Location Service** (`location_service.py`)
- GPS tracking and history
- Geofencing (500m/1000m radius)
- Distance calculations (Haversine)
- Travel time estimation
- Nearest station finder

**Logistics Service** (`logistics_service.py`)
- Transport job creation
- Transporter assignment
- Credit calculation and rewards
- Battery location tracking

**Staff Service** (`staff_service.py`)
- Staff assignment to stations
- AI-driven staff diversion
- Shift management

**Fault Service** (`fault_service.py`)
- 3-level fault hierarchy
  - Level 1: Automated recovery
  - Level 2: AI analysis
  - Level 3: Human escalation
- Ticket creation and management

---

### 3. Data Layer

**MongoDB Collections**
- `users` - All user types with roles
- `stations` - Station master data
- `queues` - Active queue entries
- `swaps` - Swap transactions
- `batteries` - Battery inventory and health
- `transport_jobs` - Logistics operations
- `staff_assignments` - Staff allocation
- `tickets` - Fault tickets
- `credits` - Credit transactions
- `gps_logs` - Location history
- `partner_shops` - Partner storage facilities
- `qr_tokens` - QR token audit log

**Redis Keys**
- `queue:{station_id}` - Live queue list
- `location:{user_id}` - Real-time location
- `qr_token:{token}` - QR token cache
- `prediction:{model}:{id}` - AI prediction cache

**Kafka Topics**
- `location_updates` - GPS location stream
- `swap_events` - Swap lifecycle events
- `logistics_events` - Transport job events
- `alert_events` - System alerts

---

## 🔄 Key Workflows

### Consumer Swap Flow

```
1. User opens app
   ↓
2. POST /recommend (Get station recommendations)
   ↓
3. User selects station
   ↓
4. POST /queue/confirm (Reserve queue slot + generate QR)
   ↓
5. Location tracking begins (geofencing)
   ↓
6. User arrives at station
   ↓
7. Staff: POST /qr/verify (Scan QR, start swap)
   ↓
8. Physical battery swap occurs
   ↓
9. POST /swap/complete (Finish transaction)
   ↓
10. User dequeued, credits awarded
```

### Battery Logistics Flow

```
1. AI detects battery imbalance
   ↓
2. POST /ai/predict-rebalancing
   ↓
3. System creates transport job
   ↓
4. Transporter: GET /transport/jobs/available
   ↓
5. POST /transport/job/accept (Uber-style acceptance)
   ↓
6. GPS tracking during transport
   ↓
7. POST /transport/job/{id}/complete
   ↓
8. Credits awarded, inventory updated
```

### Staff Diversion Flow

```
1. AI detects load spike at Station A
   ↓
2. POST /ai/predict-staff-diversion
   ↓
3. POST /staff/diversion (Reassign staff)
   ↓
4. Staff notified to move to Station B
   ↓
5. Staff assignments updated in DB
```

---

## 🧠 AI Model Integration

### Model Loading Process

```python
# At startup (app.main.py)
await ai_service.load_all_models()

# Models loaded from paths in .env:
# - /app/models/load_prediction.pkl
# - /app/models/fault_prediction.pkl
# - ... (11 more)

# Fallback: If model not found, use heuristic
```

### Model Usage Pattern

```python
# All models follow this pattern:
result = await ai_service.predict_load(
    station_id="station_001",
    features={...}
)

# Returns:
{
    "predicted_value": 12.5,
    "confidence": 0.85,
    "recommendation": "Action required"
}
```

---

## 🔒 Security Features

1. **JWT Authentication** (configured, to be enforced)
2. **QR Token Signatures** (HMAC-SHA256)
3. **Role-Based Access Control** (RBAC ready)
4. **Rate Limiting** (60/min, 1000/hour)
5. **Environment-based Configuration**

---

## 📊 Performance Characteristics

- **Queue Operations**: O(1) with Redis
- **Location Queries**: O(log n) with MongoDB indexes
- **AI Predictions**: < 100ms per call
- **QR Verification**: < 50ms
- **Concurrent Users**: 1000+ (with t3.large)

---

## 🔧 Configuration Points

All configurable via `.env`:

**Business Logic**
- `QUEUE_MAX_CAPACITY` - Max queue size
- `GEOFENCE_RADIUS_METERS` - Arrival detection
- `QR_TOKEN_EXPIRY_MINUTES` - Token lifetime
- `TRANSPORT_BASE_CREDITS` - Reward base

**Infrastructure**
- `MONGODB_URI` - Database connection
- `REDIS_HOST` - Cache server
- `KAFKA_BOOTSTRAP_SERVERS` - Event streaming

**AI Models**
- `MODEL_BASE_PATH` - Models directory
- Individual model paths for easy switching

---

## 📈 Scalability Considerations

**Current Setup (Single Server)**
- Good for: 1,000-5,000 concurrent users
- Bottleneck: MongoDB, single instance

**Production Scale**
- Load balancer + multiple backend instances
- MongoDB replica set
- Redis cluster
- Kafka cluster
- CDN for static assets

---

## 🐳 Docker Compose Services

1. **backend** - FastAPI app (Python 3.11)
2. **mongo** - MongoDB 7.0
3. **redis** - Redis 7 Alpine
4. **kafka** - Confluent Kafka 7.5
5. **zookeeper** - Kafka dependency

All connected via `navswap-network` bridge.

---

## 📝 Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Debug Mode | `True` | `False` |
| Log Level | `DEBUG` | `INFO` |
| JWT Secret | Simple | Complex |
| CORS | `*` | Specific origins |
| SSL | No | Required |
| Monitoring | Logs | CloudWatch/Datadog |

---

## 🎯 Success Metrics

- **API Uptime**: 99.9%
- **Average Response Time**: < 200ms
- **Queue Processing**: < 5 min per swap
- **ML Model Accuracy**: > 85%
- **GPS Update Frequency**: Every 30 seconds

---

This architecture supports:
✅ High concurrency
✅ Real-time operations
✅ AI-driven decisions
✅ Horizontal scaling
✅ Fault tolerance
✅ Production deployment
