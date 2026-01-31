"""
Recommendation Routes
"""
from fastapi import APIRouter, HTTPException
from app.models import (
    RecommendationRequest,
    RecommendationResponse,
    StationRecommendation
)
from app.services.location_service import location_service
from app.services.queue_service import queue_service
from app.services.ai_service import ai_service
from app.database import get_database

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get AI-powered station recommendations based on:
    - Distance
    - Queue length
    - Traffic conditions
    - Predicted wait time
    """
    try:
        # Find nearest stations
        nearest_stations = await location_service.find_nearest_stations(
            latitude=request.current_location.latitude,
            longitude=request.current_location.longitude,
            max_distance_km=15,
            limit=10
        )
        
        if not nearest_stations:
            raise HTTPException(status_code=404, detail="No stations found nearby")
        
        recommendations = []
        
        for station in nearest_stations:
            station_id = station["station_id"]
            
            # Get current queue
            queue_length = await queue_service.get_queue_length(station_id)
            
            # Estimate travel time with traffic
            travel_time = await location_service.estimate_travel_time(
                from_lat=request.current_location.latitude,
                from_lon=request.current_location.longitude,
                to_lat=station["location"]["latitude"],
                to_lon=station["location"]["longitude"],
                traffic_factor=1.2  # Would come from traffic AI model
            )
            
            # Estimate wait time at station
            wait_time = queue_length * 5  # 5 min per swap
            
            total_time = travel_time + wait_time
            
            # Calculate recommendation score (0-1)
            # Lower distance = better
            # Lower queue = better
            # Lower total time = better
            distance_score = max(0, 1 - (station["distance_km"] / 15))
            queue_score = max(0, 1 - (queue_length / 20))
            time_score = max(0, 1 - (total_time / 60))
            
            recommendation_score = (distance_score * 0.3 + 
                                   queue_score * 0.4 + 
                                   time_score * 0.3)
            
            recommendations.append(
                StationRecommendation(
                    station_id=station_id,
                    station_name=station["name"],
                    distance_km=station["distance_km"],
                    estimated_travel_minutes=travel_time,
                    current_queue_length=queue_length,
                    estimated_wait_minutes=wait_time,
                    total_time_minutes=total_time,
                    recommendation_score=round(recommendation_score, 2)
                )
            )
        
        # Sort by recommendation score (highest first)
        recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        # Get optimal station
        optimal_station_id = recommendations[0].station_id if recommendations else None
        
        # Traffic alerts (would come from AI traffic model)
        traffic_alerts = [
            "Heavy traffic on Route 95. Add 10-15 minutes to travel time.",
            "Recommended: Take alternate route via Station C."
        ] if any(r.estimated_travel_minutes > 20 for r in recommendations) else []
        
        return RecommendationResponse(
            recommended_stations=recommendations[:5],  # Top 5
            traffic_alerts=traffic_alerts,
            optimal_station_id=optimal_station_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")


@router.get("/optimal")
async def get_optimal_station(
    latitude: float,
    longitude: float,
    battery_level: float = None
):
    """Get single optimal station recommendation"""
    try:
        request = RecommendationRequest(
            user_id="guest",
            current_location={"latitude": latitude, "longitude": longitude},
            battery_level=battery_level
        )
        
        response = await get_recommendations(request)
        
        if not response.recommended_stations:
            raise HTTPException(status_code=404, detail="No stations available")
        
        optimal = response.recommended_stations[0]
        
        return {
            "optimal_station": optimal.dict(),
            "reasoning": f"Best balance of distance ({optimal.distance_km}km), "
                        f"queue ({optimal.current_queue_length}), "
                        f"and total time ({optimal.total_time_minutes}min)"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
