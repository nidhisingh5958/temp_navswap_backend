# NavSwap API Testing Guide

Complete guide for testing all API endpoints with realistic scenarios.

## Quick Start

```bash
# Base URL
BASE_URL="http://localhost:8000"

# Test health endpoint
curl $BASE_URL/health | jq '.'
```

## 📋 Complete Test Flows

### 1. Consumer Swap Flow (End-to-End)

```bash
# Step 1: Find nearest station
curl -X GET "$BASE_URL/station/nearest?latitude=28.6139&longitude=77.2090&max_distance_km=10" | jq '.'

# Step 2: Check available slots
STATION_ID="67a4b8c9d1e2f3g4h5i6j7k8"
curl -X GET "$BASE_URL/queue/available-slots/$STATION_ID" | jq '.'

# Step 3: Confirm queue reservation
curl -X POST "$BASE_URL/queue/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "battery_soh_min": 85.0,
    "preferred_time": "2024-01-20T14:30:00"
  }' | jq '.'

# Capture QR token from response
QR_TOKEN="YOUR_QR_TOKEN_FROM_RESPONSE"

# Step 4: Update location (approaching station)
curl -X POST "$BASE_URL/location/update" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "latitude": 28.6140,
    "longitude": 77.2091,
    "accuracy": 5.0,
    "speed": 15.0
  }' | jq '.'

# Step 5: Verify QR at station
curl -X POST "$BASE_URL/qr/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "'$QR_TOKEN'",
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "user_id": "507f1f77bcf86cd799439011"
  }' | jq '.'

# Capture swap_id from response
SWAP_ID="YOUR_SWAP_ID_FROM_RESPONSE"

# Step 6: Complete swap
curl -X POST "$BASE_URL/swap/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "swap_id": "'$SWAP_ID'",
    "old_battery_id": "bat_12345678",
    "new_battery_id": "bat_87654321",
    "staff_id": "507f1f77bcf86cd799439012",
    "faulty_battery": false,
    "swap_duration_seconds": 180
  }' | jq '.'

# Step 7: View swap history
curl -X GET "$BASE_URL/swap/user/507f1f77bcf86cd799439011" | jq '.'
```

### 2. Transporter Job Flow

```bash
# Step 1: View available jobs
curl -X GET "$BASE_URL/transport/jobs/available?transporter_id=507f1f77bcf86cd799439015" | jq '.'

# Step 2: Accept a job
JOB_ID="67a4b8c9d1e2f3g4h5i6j7k9"
curl -X POST "$BASE_URL/transport/job/accept" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "'$JOB_ID'",
    "transporter_id": "507f1f77bcf86cd799439015"
  }' | jq '.'

# Step 3: Update location during transit
curl -X POST "$BASE_URL/location/update" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439015",
    "latitude": 28.6150,
    "longitude": 77.2100,
    "accuracy": 8.0,
    "speed": 35.0
  }' | jq '.'

# Step 4: Complete delivery
curl -X POST "$BASE_URL/transport/job/$JOB_ID/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "transporter_id": "507f1f77bcf86cd799439015",
    "notes": "Delivered 5 batteries in good condition"
  }' | jq '.'

# Step 5: View earning history
curl -X GET "$BASE_URL/transport/history/507f1f77bcf86cd799439015" | jq '.'
```

### 3. Station Staff Operations

```bash
# View staff assignments
STAFF_ID="507f1f77bcf86cd799439012"
curl -X GET "$BASE_URL/staff/assignments/$STAFF_ID" | jq '.'

# View all staff at station
STATION_ID="67a4b8c9d1e2f3g4h5i6j7k8"
curl -X GET "$BASE_URL/staff/station/$STATION_ID" | jq '.'

# AI-triggered staff diversion
curl -X POST "$BASE_URL/staff/diversion" \
  -H "Content-Type: application/json" \
  -d '{
    "staff_id": "'$STAFF_ID'",
    "from_station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "to_station_id": "67a4b8c9d1e2f3g4h5i6j7k9",
    "reason": "high_traffic_predicted",
    "duration_minutes": 120,
    "priority": "high"
  }' | jq '.'
```

### 4. Admin Dashboard & Analytics

```bash
# Live dashboard (7 key metrics)
curl -X GET "$BASE_URL/admin/live" | jq '.'

# Logistics overview
curl -X GET "$BASE_URL/admin/logistics" | jq '.'

# Traffic analysis with predictions
curl -X GET "$BASE_URL/admin/traffic?time_window_hours=24" | jq '.'

# Station overview
curl -X GET "$BASE_URL/admin/stations/overview" | jq '.'
```

### 5. AI Model Testing

```bash
# Load prediction for station
curl -X POST "$BASE_URL/ai/predict-load" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "time_window_hours": 2
  }' | jq '.'

# Fault prediction for battery
curl -X POST "$BASE_URL/ai/predict-fault" \
  -H "Content-Type: application/json" \
  -d '{
    "battery_id": "bat_12345678",
    "cycles": 450,
    "soh": 87.5,
    "temperature": 32.0,
    "voltage": 51.8
  }' | jq '.'

# Recommend action for traffic spike
curl -X POST "$BASE_URL/ai/predict-action" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "current_queue_length": 8,
    "available_batteries": 12,
    "staff_count": 3
  }' | jq '.'

# Traffic forecast (micro-area)
curl -X POST "$BASE_URL/ai/forecast-traffic" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "hours_ahead": 4,
    "include_events": true
  }' | jq '.'

# Battery rebalancing recommendations
curl -X POST "$BASE_URL/ai/predict-rebalancing" \
  -H "Content-Type: application/json" \
  -d '{
    "region": "delhi_ncr",
    "time_horizon_hours": 6
  }' | jq '.'

# Staff diversion suggestions
curl -X POST "$BASE_URL/ai/predict-diversion" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
    "current_staff_count": 2,
    "predicted_load": 15
  }' | jq '.'

# Check all model status
curl -X GET "$BASE_URL/ai/model-status" | jq '.'
```

### 6. Station Recommendations

```bash
# Get recommendations with scoring
curl -X POST "$BASE_URL/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_location": {
      "latitude": 28.6139,
      "longitude": 77.2090
    },
    "battery_soh_min": 85.0,
    "max_distance_km": 15.0,
    "preferred_time": "2024-01-20T14:30:00"
  }' | jq '.'

# Get single optimal station
curl -X POST "$BASE_URL/recommend/optimal" \
  -H "Content-Type: application/json" \
  -d '{
    "user_location": {
      "latitude": 28.6139,
      "longitude": 77.2090
    },
    "battery_soh_min": 85.0,
    "max_distance_km": 10.0
  }' | jq '.'
```

## 🧪 Advanced Test Scenarios

### Fault Resolution Flow (3-Level Hierarchy)

```bash
# Level 1: Automated handling
curl -X POST "$BASE_URL/swap/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "swap_id": "swap_12345",
    "old_battery_id": "bat_faulty_001",
    "new_battery_id": "bat_87654321",
    "staff_id": "507f1f77bcf86cd799439012",
    "faulty_battery": true,
    "swap_duration_seconds": 180
  }' | jq '.'
# System auto-creates fault ticket if battery fails health check

# Level 2: AI analysis required (for recurring faults)
# AI service analyzes patterns and suggests fixes

# Level 3: Human intervention (critical faults)
# Ticket escalated to support team
```

### Geofence Trigger Test

```bash
# Simulate approaching station (1000m trigger)
curl -X POST "$BASE_URL/location/update" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "latitude": 28.6140,
    "longitude": 77.2091,
    "accuracy": 5.0
  }' | jq '.'
# Check swap status changes to "on_way"

# Simulate arrival (500m trigger)
curl -X POST "$BASE_URL/location/update" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "latitude": 28.6145,
    "longitude": 77.2095,
    "accuracy": 3.0
  }' | jq '.'
# Check swap status changes to "approaching"
```

### Load Balancing Test

```bash
# Create high load at one station
for i in {1..10}; do
  curl -X POST "$BASE_URL/queue/confirm" \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "user_'$i'",
      "station_id": "67a4b8c9d1e2f3g4h5i6j7k8",
      "battery_soh_min": 85.0
    }'
done

# Check AI recommendation for alternate station
curl -X POST "$BASE_URL/recommend/optimal" \
  -H "Content-Type: application/json" \
  -d '{
    "user_location": {"latitude": 28.6139, "longitude": 77.2090},
    "battery_soh_min": 85.0,
    "max_distance_km": 15.0
  }' | jq '.'
# Should suggest less crowded nearby station
```

## 📊 Monitoring & Debugging

### Check Queue Status
```bash
STATION_ID="67a4b8c9d1e2f3g4h5i6j7k8"
curl -X GET "$BASE_URL/queue/status/$STATION_ID" | jq '.'
```

### View Station Details
```bash
curl -X GET "$BASE_URL/station/$STATION_ID/status" | jq '.'
```

### Check Swap Details
```bash
SWAP_ID="swap_12345"
curl -X GET "$BASE_URL/swap/$SWAP_ID" | jq '.'
```

### System Health Check
```bash
curl -X GET "$BASE_URL/health" | jq '.'
```

## 🔧 Troubleshooting

### Common Issues

**1. QR Verification Failed**
```bash
# Check QR token expiry (15 minutes)
# Verify station_id matches
# Ensure token hasn't been used already
```

**2. Geofence Not Triggering**
```bash
# Verify GPS coordinates are within 500m/1000m
# Check location update frequency
curl -X GET "$BASE_URL/queue/status/$STATION_ID"
```

**3. AI Model Not Available**
```bash
# Check model status
curl -X GET "$BASE_URL/ai/model-status" | jq '.'
# Verify model files in /models/ directory
# System uses fallback heuristics if model missing
```

**4. Transport Job Not Appearing**
```bash
# Check job status
# Verify transporter location proximity
# Ensure transporter is eligible (role check)
```

## 📈 Performance Testing

### Load Test Queue System
```bash
# Use Apache Bench or k6
ab -n 1000 -c 50 -p queue_request.json -T application/json \
  http://localhost:8000/queue/confirm
```

### Test Redis Caching
```bash
# First request (cache miss)
time curl -X GET "$BASE_URL/station/list"

# Second request (cache hit - should be faster)
time curl -X GET "$BASE_URL/station/list"
```

## 🎯 Integration Testing

### Full User Journey Test Script

```bash
#!/bin/bash
# test_user_journey.sh

BASE_URL="http://localhost:8000"
USER_ID="507f1f77bcf86cd799439011"

echo "1. Finding nearest station..."
STATION=$(curl -s "$BASE_URL/station/nearest?latitude=28.6139&longitude=77.2090" | jq -r '.stations[0].id')
echo "   Station: $STATION"

echo "2. Confirming queue..."
QR_RESPONSE=$(curl -s -X POST "$BASE_URL/queue/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "station_id": "'$STATION'",
    "battery_soh_min": 85.0
  }')
QR_TOKEN=$(echo $QR_RESPONSE | jq -r '.qr_token')
echo "   QR Token: $QR_TOKEN"

echo "3. Updating location..."
curl -s -X POST "$BASE_URL/location/update" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "'$USER_ID'", "latitude": 28.6145, "longitude": 77.2095}' > /dev/null

echo "4. Verifying QR..."
VERIFY=$(curl -s -X POST "$BASE_URL/qr/verify" \
  -H "Content-Type: application/json" \
  -d '{"token": "'$QR_TOKEN'", "station_id": "'$STATION'", "user_id": "'$USER_ID'"}')
SWAP_ID=$(echo $VERIFY | jq -r '.swap_id')
echo "   Swap ID: $SWAP_ID"

echo "5. Completing swap..."
curl -s -X POST "$BASE_URL/swap/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "swap_id": "'$SWAP_ID'",
    "old_battery_id": "bat_old",
    "new_battery_id": "bat_new",
    "staff_id": "507f1f77bcf86cd799439012",
    "faulty_battery": false,
    "swap_duration_seconds": 180
  }' | jq '.'

echo "✅ Journey complete!"
```

## 📱 Mobile App Testing Tips

1. **Location Updates**: Send every 10-30 seconds during active swap
2. **QR Display**: Show QR code full-screen for scanner
3. **Error Handling**: Handle network failures gracefully
4. **Cache**: Cache station list for offline access
5. **Push Notifications**: Implement for queue position updates

## 🔐 Security Testing

```bash
# Test invalid QR token
curl -X POST "$BASE_URL/qr/verify" \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid_token", "station_id": "test", "user_id": "test"}'

# Test expired token (generate token, wait 16 minutes)

# Test station mismatch
# Generate QR for station A, verify at station B
```

## 📊 Expected Response Times

- `/health`: < 50ms
- `/station/list`: < 100ms (Redis cached)
- `/queue/confirm`: < 200ms
- `/qr/verify`: < 150ms
- `/swap/complete`: < 300ms
- AI predictions: < 500ms (with model) or < 100ms (fallback)

---

**Pro Tips**:
- Use `jq` for JSON formatting
- Save common IDs as environment variables
- Test during peak vs off-peak scenarios
- Monitor Redis cache hit rates
- Check MongoDB query performance with indexes
