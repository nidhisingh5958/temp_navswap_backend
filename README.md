# 🚀 NavSwap - AI-Powered EV Battery Swap Platform

## Production-Grade Backend System

NavSwap is an intelligent EV battery swap and station operations platform powered by **13 ML models**, managing queue operations, logistics, staff diversion, and real-time tracking.

---

## 🧠 AI Architecture

All AI inference runs **locally** using 13 pre-trained models stored in `/models/`:

1. Load Prediction
2. Fault Prediction
3. Action Recommendation
4. Traffic Forecast
5. Micro-Area Traffic
6. Customer Arrival
7. Battery Usage Trend
8. Battery Rebalancing
9. Staff Diversion
10. Battery Stock Order
11. Partner Storage Allocation
12. Energy Stability
13. Station Reliability

---

## 🧩 Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: MongoDB
- **Cache**: Redis
- **Streaming**: Apache Kafka
- **Containerization**: Docker + docker-compose
- **Target Deployment**: AWS EC2

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
cd test_navswap
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Seed Database

```bash
docker-compose exec backend python scripts/seed_data.py
```

### 4. Access API

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📁 Project Structure

```
test_navswap/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration management
│   ├── models/                 # Pydantic models
│   ├── schemas/                # MongoDB schemas
│   ├── services/               # Business logic
│   │   ├── ai_service.py      # AI model loading & inference
│   │   ├── queue_service.py   # Queue management
│   │   ├── qr_service.py      # QR generation & verification
│   │   ├── location_service.py # GPS tracking
│   │   ├── logistics_service.py # Battery logistics
│   │   ├── staff_service.py   # Staff diversion
│   │   └── fault_service.py   # Fault resolution
│   ├── routes/                 # API endpoints
│   └── utils/                  # Helper functions
├── models/                     # ML model files (.pkl, .h5, etc.)
├── scripts/
│   └── seed_data.py           # Database seeding
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── docs/                       # Documentation
```

---

## 🔑 Key Features

### Queue + QR Swap System
- Reserve queue slots with time-bound QR tokens
- GPS-based geofencing (500m radius)
- Real-time queue status tracking
- Dynamic buffer management

### Battery Logistics
- Partner shop integration
- AI-driven rebalancing
- Transporter rewards system
- Uber-style job notifications

### Staff Management
- AI-powered staff diversion
- Load-based reassignment
- Real-time assignment tracking

### Fault Resolution
- **Level 1**: Automated recovery
- **Level 2**: AI analysis
- **Level 3**: Human escalation with ticketing

### Live Tracking
- Consumer location tracking
- Staff movement monitoring
- Transporter real-time updates
- Traffic congestion analysis

---

## 🌐 API Endpoints

### Consumer APIs
- `POST /queue/confirm` - Reserve queue slot
- `POST /qr/verify` - Verify QR token
- `GET /recommend` - Get AI recommendations

### Staff APIs
- `POST /swap/complete` - Mark swap complete
- `GET /staff/assignments` - View assignments

### Transporter APIs
- `POST /transport/job/accept` - Accept transport job
- `GET /transporter/history` - View job history

### Admin APIs
- `GET /admin/live` - Live dashboard data
- `GET /admin/logistics` - Logistics overview
- `GET /admin/traffic` - Traffic analysis
- `GET /station/{id}/status` - Station status

### AI Prediction APIs
- `POST /ai/predict-load` - Load prediction
- `POST /ai/predict-fault` - Fault prediction
- `POST /ai/predict-action` - Action recommendation
- _+ 10 more model endpoints_

---

## 🐳 Docker Services

- **backend**: FastAPI application
- **mongo**: MongoDB database
- **redis**: Redis cache
- **kafka**: Apache Kafka
- **zookeeper**: Kafka dependency

---

## 📊 Database Collections

- `stations` - Station master data
- `queues` - Queue management
- `swaps` - Swap transactions
- `transport_jobs` - Logistics jobs
- `staff_assignments` - Staff allocation
- `tickets` - Fault tickets
- `credits` - Reward credits
- `gps_logs` - Location history
- `partner_shops` - Partner storage
- `users` - User accounts

---

## 🔒 Security

- JWT-based authentication
- Role-based access control (RBAC)
- API rate limiting
- Environment-based configuration

---

## 📈 Monitoring

- Prometheus metrics endpoint: `/metrics`
- Structured logging with correlation IDs
- Real-time event streaming via Kafka

---

## 🚢 Production Deployment

See [docs/deployment_guide.md](docs/deployment_guide.md) for AWS EC2 deployment instructions.

---

## 📝 License

Proprietary - All rights reserved

---

## 🤝 Support

For technical support, contact the NavSwap engineering team.
# temp_navswap_backend
