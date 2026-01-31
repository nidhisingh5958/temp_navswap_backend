"""
Queue Management Service
Handles queue operations, reservations, and wait time calculations
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.database import get_database
from app.config import get_settings
from app.models import SwapStatus, QueueEntry
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class QueueService:
    """Manages station queues and reservations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ QueueService: Redis connected")
        except Exception as e:
            logger.error(f"❌ QueueService: Redis connection failed: {e}")
    
    async def get_queue_length(self, station_id: str) -> int:
        """Get current queue length for a station"""
        try:
            # Try Redis first (real-time)
            if self.redis_client:
                length = await self.redis_client.llen(f"queue:{station_id}")
                return length
            
            # Fallback to MongoDB
            db = get_database()
            count = await db.queues.count_documents({
                "station_id": station_id,
                "status": {"$in": ["confirmed", "approaching", "active"]}
            })
            return count
        
        except Exception as e:
            logger.error(f"Error getting queue length: {e}")
            return 0
    
    async def add_to_queue(
        self,
        station_id: str,
        user_id: str,
        qr_token: str
    ) -> Dict[str, Any]:
        """Add user to station queue"""
        try:
            db = get_database()
            
            # Check if user already in queue at this station
            existing = await db.queues.find_one({
                "station_id": station_id,
                "user_id": user_id,
                "status": {"$in": ["confirmed", "approaching"]}
            })
            
            if existing:
                return {
                    "success": False,
                    "message": "User already in queue at this station",
                    "position": existing.get("position", 0)
                }
            
            # Get current queue length
            current_length = await self.get_queue_length(station_id)
            
            # Check capacity
            if current_length >= self.settings.QUEUE_MAX_CAPACITY:
                return {
                    "success": False,
                    "message": "Queue is full. Please try another station.",
                    "position": None
                }
            
            # Calculate position and estimated wait
            position = current_length + 1
            estimated_wait_minutes = self._calculate_wait_time(position)
            
            # Create queue entry
            queue_entry = {
                "station_id": station_id,
                "user_id": user_id,
                "position": position,
                "status": "confirmed",
                "qr_token": qr_token,
                "estimated_wait_minutes": estimated_wait_minutes,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.queues.insert_one(queue_entry)
            
            # Add to Redis for real-time tracking
            if self.redis_client:
                await self.redis_client.rpush(f"queue:{station_id}", user_id)
                await self.redis_client.setex(
                    f"queue:entry:{user_id}:{station_id}",
                    3600,  # 1 hour TTL
                    str(result.inserted_id)
                )
            
            logger.info(f"✅ User {user_id} added to queue at station {station_id}, position {position}")
            
            return {
                "success": True,
                "queue_id": str(result.inserted_id),
                "position": position,
                "estimated_wait_minutes": estimated_wait_minutes
            }
        
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "position": None
            }
    
    async def update_queue_status(
        self,
        station_id: str,
        user_id: str,
        new_status: str
    ) -> bool:
        """Update user's queue status (approaching, active, completed)"""
        try:
            db = get_database()
            
            result = await db.queues.update_one(
                {
                    "station_id": station_id,
                    "user_id": user_id,
                    "status": {"$nin": ["completed", "cancelled"]}
                },
                {
                    "$set": {
                        "status": new_status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error updating queue status: {e}")
            return False
    
    async def remove_from_queue(
        self,
        station_id: str,
        user_id: str,
        reason: str = "completed"
    ) -> bool:
        """Remove user from queue and reorder remaining entries"""
        try:
            db = get_database()
            
            # Find the user's position
            queue_entry = await db.queues.find_one({
                "station_id": station_id,
                "user_id": user_id,
                "status": {"$nin": ["completed", "cancelled"]}
            })
            
            if not queue_entry:
                return False
            
            removed_position = queue_entry["position"]
            
            # Mark as completed/cancelled
            await db.queues.update_one(
                {"_id": queue_entry["_id"]},
                {
                    "$set": {
                        "status": reason,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Reorder queue - decrement positions for users after this one
            await db.queues.update_many(
                {
                    "station_id": station_id,
                    "position": {"$gt": removed_position},
                    "status": {"$in": ["confirmed", "approaching"]}
                },
                {
                    "$inc": {"position": -1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.lrem(f"queue:{station_id}", 1, user_id)
                await self.redis_client.delete(f"queue:entry:{user_id}:{station_id}")
            
            logger.info(f"✅ User {user_id} removed from queue at station {station_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error removing from queue: {e}")
            return False
    
    async def get_queue_status(
        self,
        station_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current queue status for a station"""
        try:
            db = get_database()
            
            # Get all active queue entries
            cursor = db.queues.find({
                "station_id": station_id,
                "status": {"$in": ["confirmed", "approaching", "active"]}
            }).sort("position", 1)
            
            entries = await cursor.to_list(length=100)
            
            queue_entries = []
            user_position = None
            user_wait_time = None
            
            for entry in entries:
                # Get user details
                user = await db.users.find_one({"_id": entry["user_id"]})
                
                queue_entry = QueueEntry(
                    position=entry["position"],
                    user_id=entry["user_id"],
                    user_name=user["name"] if user else "Unknown",
                    estimated_wait_minutes=entry.get("estimated_wait_minutes", 0),
                    qr_token=entry.get("qr_token")
                )
                queue_entries.append(queue_entry)
                
                # Track specific user's position
                if user_id and entry["user_id"] == user_id:
                    user_position = entry["position"]
                    user_wait_time = entry.get("estimated_wait_minutes", 0)
            
            return {
                "station_id": station_id,
                "total_in_queue": len(queue_entries),
                "current_position": user_position,
                "estimated_wait_minutes": user_wait_time,
                "queue_entries": [entry.dict() for entry in queue_entries]
            }
        
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {
                "station_id": station_id,
                "total_in_queue": 0,
                "queue_entries": []
            }
    
    def _calculate_wait_time(self, position: int) -> int:
        """Calculate estimated wait time based on queue position"""
        # Assume average swap time of 5 minutes + buffer
        avg_swap_minutes = 5
        buffer_minutes = 2
        
        estimated_minutes = (position - 1) * (avg_swap_minutes + buffer_minutes)
        
        # Add some randomness for realism (±20%)
        import random
        variance = random.uniform(0.8, 1.2)
        
        return max(1, int(estimated_minutes * variance))
    
    async def get_available_slots(self, station_id: str) -> int:
        """Get number of available queue slots"""
        current_length = await self.get_queue_length(station_id)
        available = self.settings.QUEUE_MAX_CAPACITY - current_length
        return max(0, available)
    
    async def cleanup_expired_queues(self):
        """Clean up expired queue entries (scheduled task)"""
        try:
            db = get_database()
            
            # Remove entries older than 2 hours that are still in confirmed status
            cutoff_time = datetime.utcnow() - timedelta(hours=2)
            
            result = await db.queues.update_many(
                {
                    "status": "confirmed",
                    "created_at": {"$lt": cutoff_time}
                },
                {
                    "$set": {
                        "status": "expired",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"🧹 Cleaned up {result.modified_count} expired queue entries")
        
        except Exception as e:
            logger.error(f"Error cleaning up queues: {e}")


# Global instance
queue_service = QueueService()
