"""
Station Routes
"""
from fastapi import APIRouter, HTTPException
from app.models import StationResponse
from app.database import get_database

router = APIRouter()


@router.get("/{station_id}/status", response_model=StationResponse)
async def get_station_status(station_id: str):
    """Get detailed station status"""
    try:
        db = get_database()
        
        station = await db.stations.find_one({"_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Get current queue length
        from app.services.queue_service import queue_service
        queue_length = await queue_service.get_queue_length(station_id)
        
        station["_id"] = str(station["_id"])
        station["current_queue_length"] = queue_length
        
        return StationResponse(**station)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_stations(active_only: bool = True, limit: int = 50):
    """List all stations"""
    try:
        db = get_database()
        
        query = {"is_active": True} if active_only else {}
        
        cursor = db.stations.find(query).limit(limit)
        stations = await cursor.to_list(length=limit)
        
        for station in stations:
            station["_id"] = str(station["_id"])
        
        return {
            "total": len(stations),
            "stations": stations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nearest")
async def find_nearest_stations(latitude: float, longitude: float, max_distance_km: float = 10):
    """Find nearest stations to a location"""
    try:
        from app.services.location_service import location_service
        
        stations = await location_service.find_nearest_stations(
            latitude=latitude,
            longitude=longitude,
            max_distance_km=max_distance_km,
            limit=5
        )
        
        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "nearest_stations": stations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
