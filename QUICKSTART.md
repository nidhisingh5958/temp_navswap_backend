# NavSwap Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

- Docker Desktop installed
- Git installed
- 8GB RAM minimum

---

## Step 1: Clone & Setup

```bash
cd /Volumes/DevSSD/Developer/test_navswap

# Copy environment file
cp .env.example .env

# (Optional) Edit .env if you want to customize settings
# nano .env
```

---

## Step 2: Start All Services

```bash
# Start MongoDB, Redis, Kafka, Zookeeper, and FastAPI backend
docker-compose up -d

# This will:
# - Pull Docker images (first time only, ~2-3 minutes)
# - Start all containers
# - Initialize databases
```

**Wait 30-60 seconds** for all services to be healthy.

---

## Step 3: Verify Services

```bash
# Check if all containers are running
docker-compose ps

# Should see 5 containers: backend, mongo, redis, kafka, zookeeper
# All should have status: "Up"

# Test health endpoint
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:00:00Z",
  "models_loaded": "0/13",
  "database": "connected"
}
```

> **Note**: `models_loaded` will be `0/13` until you add model files to `/models/` directory.

---

## Step 4: Seed Database

```bash
# Populate database with mock data
docker-compose exec backend python scripts/seed_data.py

# This creates:
# - 98 users (consumers, staff, transporters, admins)
# - 25 stations across major cities
# - 10 partner shops
# - 500+ batteries
# - 200 historical swaps
# - 50 transport jobs
# - 30 tickets
# - 200 GPS logs
```

---

## Step 5: Explore API

### Option A: Swagger UI (Recommended)

Open browser: **http://localhost:8000/docs**

Interactive API documentation with "Try it out" buttons!

### Option B: cURL Examples

```bash
# 1. Get station recommendations
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "consumer_001",
    "current_location": {
      "latitude": 40.7128,
      "longitude": -74.0060
    }
  }'

# 2. Check station status
curl http://localhost:8000/station/station_001/status

# 3. Get live dashboard
curl http://localhost:8000/admin/live

# 4. Check AI model status
curl http://localhost:8000/ai/model-status
```

---

## Step 6: Add ML Models (Optional)

```bash
# Place your .pkl model files in the models/ directory
# The models should match the names in .env:

models/
├── load_prediction.pkl
├── fault_prediction.pkl
├── action_recommendation.pkl
├── traffic_forecast.pkl
├── micro_area_traffic.pkl
├── customer_arrival.pkl
├── battery_usage_trend.pkl
├── battery_rebalancing.pkl
├── staff_diversion.pkl
├── battery_stock_order.pkl
├── partner_storage_allocation.pkl
├── energy_stability.pkl
└── station_reliability.pkl

# Restart backend to load models
docker-compose restart backend

# Verify models loaded
curl http://localhost:8000/ai/model-status
```

---

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Last 50 lines
docker-compose logs --tail=50 backend
```

### Stop Services

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (deletes database)
docker-compose down -v
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart backend only
docker-compose restart backend
```

### Access Database

```bash
# MongoDB shell
docker-compose exec mongo mongosh navswap

# Redis CLI
docker-compose exec redis redis-cli
```

---

## Test Complete Flow

### Consumer Swap Flow

```bash
# 1. Get recommendations
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "consumer_001",
    "current_location": {"latitude": 40.7128, "longitude": -74.0060}
  }' | jq '.recommended_stations[0]'

# 2. Confirm queue (use station_id from step 1)
curl -X POST http://localhost:8000/queue/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "station_001",
    "user_id": "consumer_001",
    "current_location": {"latitude": 40.7128, "longitude": -74.0060}
  }' | jq '.'

# Copy the qr_token and swap_id from response

# 3. Staff verifies QR
curl -X POST http://localhost:8000/qr/verify \
  -H "Content-Type: application/json" \
  -d '{
    "qr_token": "PASTE_QR_TOKEN_HERE",
    "station_id": "station_001",
    "staff_id": "staff_001"
  }' | jq '.'

# 4. Complete swap
curl -X POST http://localhost:8000/swap/complete \
  -H "Content-Type: application/json" \
  -d '{
    "swap_id": "PASTE_SWAP_ID_HERE",
    "staff_id": "staff_001",
    "old_battery_id": "BAT-00001",
    "new_battery_id": "BAT-00002",
    "old_battery_health": "healthy"
  }' | jq '.'
```

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process or change port in docker-compose.yml
```

### Container Not Starting

```bash
# Check logs
docker-compose logs [service_name]

# Common fixes:
docker-compose down
docker system prune -a
docker-compose up -d
```

### Database Connection Failed

```bash
# Wait for MongoDB to be ready
docker-compose logs mongo

# Restart backend after MongoDB is ready
docker-compose restart backend
```

---

## Next Steps

1. **Frontend Integration**: See [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md)
2. **Deployment**: See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
3. **API Reference**: Visit http://localhost:8000/docs

---

## Support

- **Issues**: Create GitHub issue
- **Questions**: Email dev@navswap.com

---

## Quick Links

- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health
- Admin Dashboard API: http://localhost:8000/admin/live

---

**Happy Coding! 🚀**
