# NavSwap Frontend Integration Guide

## Overview

This guide helps frontend developers integrate with the NavSwap backend API.

---

## Base URL

```
Development: http://localhost:8000
Production: https://api.navswap.com
```

---

## Authentication

Currently using JWT tokens (future enhancement).

For now, pass `user_id` in requests.

---

## Core User Flows

### 1. Consumer Flow: Find Station & Reserve Queue

#### Step 1: Get Recommendations

```http
POST /recommend
Content-Type: application/json

{
  "user_id": "consumer_001",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "battery_level": 15.5
}
```

**Response:**
```json
{
  "recommended_stations": [
    {
      "station_id": "station_001",
      "station_name": "New York Station A",
      "distance_km": 2.5,
      "estimated_travel_minutes": 8,
      "current_queue_length": 3,
      "estimated_wait_minutes": 15,
      "total_time_minutes": 23,
      "recommendation_score": 0.92
    }
  ],
  "optimal_station_id": "station_001"
}
```

#### Step 2: Confirm Queue Reservation

```http
POST /queue/confirm
Content-Type: application/json

{
  "station_id": "station_001",
  "user_id": "consumer_001",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

**Response:**
```json
{
  "queue_position": 4,
  "estimated_wait_minutes": 20,
  "qr_token": "1234567890:consumer_001:station_001:swap_001:randomstring:signature",
  "qr_expiry": "2026-01-31T15:30:00Z",
  "station_name": "New York Station A",
  "station_location": {
    "latitude": 40.7150,
    "longitude": -74.0080
  }
}
```

#### Step 3: Generate QR Code Image

```http
GET /qr/generate-image/{qr_token}
```

**Response:**
```json
{
  "qr_token": "1234567890:...",
  "qr_image": "data:image/png;base64,iVBORw0KG..."
}
```

Display this QR code to the user.

#### Step 4: Check Queue Status (Polling)

```http
GET /queue/status/{station_id}?user_id=consumer_001
```

**Response:**
```json
{
  "station_id": "station_001",
  "total_in_queue": 5,
  "current_position": 3,
  "estimated_wait_minutes": 12,
  "queue_entries": [...]
}
```

Poll this endpoint every 30 seconds to update UI.

---

### 2. Staff Flow: Verify QR & Complete Swap

#### Step 1: Scan QR Code

Staff scans user's QR code using mobile scanner.

#### Step 2: Verify QR Token

```http
POST /qr/verify
Content-Type: application/json

{
  "qr_token": "1234567890:consumer_001:station_001:swap_001:randomstring:signature",
  "station_id": "station_001",
  "staff_id": "staff_005"
}
```

**Response (Success):**
```json
{
  "valid": true,
  "swap_id": "swap_001",
  "user_name": "John Doe",
  "message": "QR verified successfully. Swap started."
}
```

**Response (Failure):**
```json
{
  "valid": false,
  "message": "QR token has expired"
}
```

#### Step 3: Complete Swap

After physically swapping the battery:

```http
POST /swap/complete
Content-Type: application/json

{
  "swap_id": "swap_001",
  "staff_id": "staff_005",
  "old_battery_id": "BAT-00123",
  "new_battery_id": "BAT-00456",
  "old_battery_health": "healthy",
  "notes": "Battery in good condition"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Swap completed successfully",
  "swap_id": "swap_001",
  "credits_earned": 10
}
```

---

### 3. Transporter Flow: Accept & Complete Jobs

#### Step 1: Get Available Jobs

```http
GET /transport/jobs/available?transporter_id=transporter_003&max_distance_km=50
```

**Response:**
```json
{
  "transporter_id": "transporter_003",
  "available_jobs": [
    {
      "_id": "transport_001",
      "from_location": "station_005",
      "to_location": "station_012",
      "battery_count": 3,
      "priority": 4,
      "distance_km": 12.5,
      "created_at": "2026-01-31T10:00:00Z"
    }
  ],
  "count": 1
}
```

#### Step 2: Accept Job

```http
POST /transport/job/accept
Content-Type: application/json

{
  "job_id": "transport_001",
  "transporter_id": "transporter_003",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Job accepted successfully",
  "job_id": "transport_001"
}
```

#### Step 3: Complete Job

```http
POST /transport/job/transport_001/complete?transporter_id=transporter_003
```

**Response:**
```json
{
  "success": true,
  "credits_earned": 285,
  "message": "Job completed! Earned 285 credits"
}
```

---

### 4. Admin Dashboard

#### Live Dashboard

```http
GET /admin/live
```

**Response:**
```json
{
  "timestamp": "2026-01-31T12:00:00Z",
  "total_stations": 25,
  "active_swaps": 12,
  "total_queue_length": 45,
  "active_transporters": 8,
  "pending_transport_jobs": 5,
  "open_tickets": 3,
  "system_health_score": 0.95
}
```

#### Logistics Overview

```http
GET /admin/logistics
```

**Response:**
```json
{
  "total_batteries": 500,
  "batteries_in_transit": 15,
  "batteries_at_stations": 420,
  "batteries_at_partners": 55,
  "faulty_batteries": 10,
  "pending_rebalancing_jobs": 3
}
```

#### Traffic Analysis

```http
GET /admin/traffic
```

---

## Real-Time Updates

### WebSocket (Future Enhancement)

Currently, use polling:

- **Queue status**: Poll every 30 seconds
- **Swap status**: Poll every 10 seconds during active swap
- **Job status**: Poll every 60 seconds

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message",
  "error": "Technical details"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found
- `500` - Internal Server Error

---

## Rate Limiting

- **Per minute**: 60 requests
- **Per hour**: 1000 requests

Exceeded? You'll get `429 Too Many Requests`.

---

## Best Practices

### 1. Location Updates

Send user location updates during navigation:

```http
POST /location/update (to be implemented)
{
  "user_id": "consumer_001",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-31T12:00:00Z"
}
```

### 2. QR Code Display

- Display QR code prominently
- Show expiry timer (15 minutes from generation)
- Refresh QR if expired

### 3. Queue Updates

- Poll queue status every 30 seconds
- Show position, estimated wait time
- Alert user when position <= 2

### 4. Error Recovery

- If QR expired, allow user to regenerate
- If station full, suggest alternatives from recommendations
- Gracefully handle network errors

---

## Testing

### Mock Data Available

After running seed script:
- 50 consumers
- 25 stations
- 10 partner shops
- 30 staff members
- 15 transporters

Test user IDs:
- Consumer: `consumer_001` to `consumer_050`
- Staff: `staff_001` to `staff_030`
- Transporter: `transporter_001` to `transporter_015`

---

## Interactive API Documentation

Visit: `http://localhost:8000/docs`

Try out all endpoints with built-in Swagger UI.

---

## Support

For integration issues, contact: `dev@navswap.com`
