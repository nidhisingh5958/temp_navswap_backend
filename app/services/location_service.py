"""
Location Tracking Service
Handles GPS tracking, geofencing, and location-based operations
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from app.database import get_database
from app.config import get_settings
from app.models import Location
import math
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class LocationService:
    """Manages real-time location tracking and geofencing"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection for real-time location"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ LocationService: Redis connected")
        except Exception as e:
            logger.error(f"❌ LocationService: Redis connection failed: {e}")
    
    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    async def update_location(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        speed: Optional[float] = None,
        heading: Optional[float] = None
    ) -> bool:
        """Update user's current location"""
        try:
            timestamp = datetime.utcnow()
            
            # Store in Redis for real-time access
            if self.redis_client:
                location_data = f"{latitude},{longitude},{timestamp.isoformat()}"
                await self.redis_client.setex(
                    f"location:{user_id}",
                    300,  # 5 minutes TTL
                    location_data
                )
            
            # Store in MongoDB for history
            db = get_database()
            await db.gps_logs.insert_one({
                "user_id": user_id,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "speed": speed,
                "heading": heading,
                "timestamp": timestamp
            })
            
            # Check geofencing for any active swaps
            await self._check_geofence(user_id, latitude, longitude)
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating location: {e}")
            return False
    
    async def get_current_location(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current location"""
        try:
            # Try Redis first
            if self.redis_client:
                location_data = await self.redis_client.get(f"location:{user_id}")
                if location_data:
                    lat, lon, timestamp_str = location_data.split(",")
                    return {
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "timestamp": timestamp_str
                    }
            
            # Fallback to MongoDB (latest entry)
            db = get_database()
            latest = await db.gps_logs.find_one(
                {"user_id": user_id},
                sort=[("timestamp", -1)]
            )
            
            if latest:
                return {
                    "latitude": latest["location"]["latitude"],
                    "longitude": latest["location"]["longitude"],
                    "timestamp": latest["timestamp"].isoformat()
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting location: {e}")
            return None
    
    async def _check_geofence(
        self,
        user_id: str,
        latitude: float,
        longitude: float
    ):
        """Check if user entered geofence of their destination station"""
        try:
            db = get_database()
            
            # Find active swap for this user
            swap = await db.swaps.find_one({
                "user_id": user_id,
                "status": {"$in": ["confirmed", "approaching"]}
            })
            
            if not swap:
                return
            
            station_id = swap["station_id"]
            
            # Get station location
            station = await db.stations.find_one({"_id": station_id})
            if not station:
                return
            
            station_lat = station["location"]["latitude"]
            station_lon = station["location"]["longitude"]
            
            # Calculate distance
            distance = self.calculate_distance(
                latitude, longitude,
                station_lat, station_lon
            )
            
            # Update status based on distance
            if distance <= self.settings.GEOFENCE_RADIUS_METERS:
                # Within 500m - user has arrived
                if swap["status"] != "active":
                    await db.swaps.update_one(
                        {"_id": swap["_id"]},
                        {
                            "$set": {
                                "status": "approaching",
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    # Update queue status
                    from app.services.queue_service import queue_service
                    await queue_service.update_queue_status(
                        station_id, user_id, "approaching"
                    )
                    
                    logger.info(f"📍 User {user_id} approaching station {station_id}")
            
            elif distance <= self.settings.APPROACHING_RADIUS_METERS:
                # Within 1km - user is on the way
                if swap["status"] == "confirmed":
                    logger.info(f"📍 User {user_id} within 1km of station {station_id}")
        
        except Exception as e:
            logger.error(f"Error in geofence check: {e}")
    
    async def find_nearest_stations(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 10,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find nearest stations to a location"""
        try:
            db = get_database()
            
            # Get all active stations
            cursor = db.stations.find({"is_active": True})
            stations = await cursor.to_list(length=100)
            
            # Calculate distances and filter
            stations_with_distance = []
            
            for station in stations:
                station_lat = station["location"]["latitude"]
                station_lon = station["location"]["longitude"]
                
                distance_meters = self.calculate_distance(
                    latitude, longitude,
                    station_lat, station_lon
                )
                
                distance_km = distance_meters / 1000
                
                if distance_km <= max_distance_km:
                    stations_with_distance.append({
                        "station_id": str(station["_id"]),
                        "name": station["name"],
                        "distance_km": round(distance_km, 2),
                        "distance_meters": round(distance_meters),
                        "location": station["location"],
                        "capacity": station["capacity"],
                        "inventory": station["inventory"]
                    })
            
            # Sort by distance
            stations_with_distance.sort(key=lambda x: x["distance_km"])
            
            return stations_with_distance[:limit]
        
        except Exception as e:
            logger.error(f"Error finding nearest stations: {e}")
            return []
    
    async def estimate_travel_time(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        traffic_factor: float = 1.0
    ) -> int:
        """
        Estimate travel time in minutes
        Simple estimation: distance / average speed (40 km/h in city)
        """
        distance_km = self.calculate_distance(
            from_lat, from_lon, to_lat, to_lon
        ) / 1000
        
        average_speed_kmh = 40  # City driving
        
        # Apply traffic factor (1.0 = normal, 1.5 = heavy traffic)
        travel_time_hours = (distance_km / average_speed_kmh) * traffic_factor
        travel_time_minutes = int(travel_time_hours * 60)
        
        return max(1, travel_time_minutes)  # Minimum 1 minute
    
    async def get_location_history(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get user's location history"""
        try:
            db = get_database()
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = db.gps_logs.find({
                "user_id": user_id,
                "timestamp": {"$gte": cutoff_time}
            }).sort("timestamp", -1).limit(100)
            
            logs = await cursor.to_list(length=100)
            
            return [
                {
                    "latitude": log["location"]["latitude"],
                    "longitude": log["location"]["longitude"],
                    "timestamp": log["timestamp"].isoformat(),
                    "speed": log.get("speed"),
                    "heading": log.get("heading")
                }
                for log in logs
            ]
        
        except Exception as e:
            logger.error(f"Error getting location history: {e}")
            return []
    
    async def get_active_users_near_station(
        self,
        station_id: str,
        radius_meters: int = 5000
    ) -> List[Dict[str, Any]]:
        """Get list of users currently near a station"""
        try:
            db = get_database()
            
            # Get station location
            station = await db.stations.find_one({"_id": station_id})
            if not station:
                return []
            
            station_lat = station["location"]["latitude"]
            station_lon = station["location"]["longitude"]
            
            # Get recent GPS logs (last 10 minutes)
            cutoff_time = datetime.utcnow() - timedelta(minutes=10)
            
            cursor = db.gps_logs.find({
                "timestamp": {"$gte": cutoff_time}
            })
            
            recent_logs = await cursor.to_list(length=1000)
            
            # Filter by distance
            nearby_users = []
            
            for log in recent_logs:
                distance = self.calculate_distance(
                    log["location"]["latitude"],
                    log["location"]["longitude"],
                    station_lat,
                    station_lon
                )
                
                if distance <= radius_meters:
                    # Get user details
                    user = await db.users.find_one({"_id": log["user_id"]})
                    
                    if user:
                        nearby_users.append({
                            "user_id": log["user_id"],
                            "user_name": user["name"],
                            "distance_meters": round(distance),
                            "location": log["location"],
                            "timestamp": log["timestamp"].isoformat()
                        })
            
            return nearby_users
        
        except Exception as e:
            logger.error(f"Error getting nearby users: {e}")
            return []
    
    async def track_transporter(
        self,
        transporter_id: str,
        job_id: str,
        latitude: float,
        longitude: float
    ) -> bool:
        """Track transporter during active job"""
        try:
            # Update location
            await self.update_location(transporter_id, latitude, longitude)
            
            # Update job with current location
            db = get_database()
            await db.transport_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "transporter_current_location": {
                            "latitude": latitude,
                            "longitude": longitude
                        },
                        "last_location_update": datetime.utcnow()
                    }
                }
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error tracking transporter: {e}")
            return False


# Global instance
location_service = LocationService()
