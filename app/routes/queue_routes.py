"""
Queue Management Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.models import QueueConfirmRequest, QueueConfirmResponse, QueueStatusResponse
from app.services.queue_service import queue_service
from app.services.qr_service import qr_service
from app.services.location_service import location_service
from app.database import get_database
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/confirm", response_model=QueueConfirmResponse, status_code=status.HTTP_201_CREATED)
async def confirm_queue_arrival(request: QueueConfirmRequest):
    """
    Consumer confirms arrival - reserve queue slot and generate QR token
    """
    try:
        db = get_database()
        
        # Validate station
        station = await db.stations.find_one({"_id": request.station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        if not station.get("is_active", False):
            raise HTTPException(status_code=400, detail="Station is not active")
        
        # Validate user
        user = await db.users.find_one({"_id": request.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create swap record
        swap = {
            "user_id": request.user_id,
            "station_id": request.station_id,
            "status": "confirmed",
            "qr_token": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        swap_result = await db.swaps.insert_one(swap)
        swap_id = str(swap_result.inserted_id)
        
        # Generate QR token
        qr_token = qr_service.generate_qr_token(
            user_id=request.user_id,
            station_id=request.station_id,
            swap_id=swap_id
        )
        
        # Store QR token
        await qr_service.store_qr_token(
            qr_token=qr_token,
            swap_id=swap_id,
            user_id=request.user_id,
            station_id=request.station_id
        )
        
        # Update swap with QR token
        await db.swaps.update_one(
            {"_id": swap_id},
            {"$set": {"qr_token": qr_token}}
        )
        
        # Add to queue
        queue_result = await queue_service.add_to_queue(
            station_id=request.station_id,
            user_id=request.user_id,
            qr_token=qr_token
        )
        
        if not queue_result["success"]:
            raise HTTPException(status_code=400, detail=queue_result["message"])
        
        # Update user location
        await location_service.update_location(
            user_id=request.user_id,
            latitude=request.current_location.latitude,
            longitude=request.current_location.longitude
        )
        
        # Calculate estimated wait time
        qr_expiry = datetime.utcnow() + timedelta(minutes=qr_service.settings.QR_TOKEN_EXPIRY_MINUTES)
        
        return QueueConfirmResponse(
            queue_position=queue_result["position"],
            estimated_wait_minutes=queue_result["estimated_wait_minutes"],
            qr_token=qr_token,
            qr_expiry=qr_expiry,
            station_name=station["name"],
            station_location=station["location"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming queue: {str(e)}")


@router.get("/status/{station_id}", response_model=QueueStatusResponse)
async def get_queue_status(station_id: str, user_id: str = None):
    """Get current queue status for a station"""
    try:
        status_data = await queue_service.get_queue_status(station_id, user_id)
        return QueueStatusResponse(**status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting queue status: {str(e)}")


@router.get("/available-slots/{station_id}")
async def get_available_slots(station_id: str):
    """Get number of available queue slots"""
    try:
        available = await queue_service.get_available_slots(station_id)
        current_length = await queue_service.get_queue_length(station_id)
        
        return {
            "station_id": station_id,
            "available_slots": available,
            "current_queue_length": current_length,
            "max_capacity": queue_service.settings.QUEUE_MAX_CAPACITY
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
