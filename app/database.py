"""
Database connection and initialization
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Global database client and database instance
mongodb_client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None
is_connected: bool = False


async def connect_to_mongodb():
    """Connect to MongoDB"""
    global mongodb_client, database, is_connected
    
    settings = get_settings()
    
    try:
        mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        database = mongodb_client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await database.command("ping")
        is_connected = True
        logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.warning(f"⚠️ MongoDB not available: {e}")
        logger.warning("⚠️ Running in degraded mode without database")
        is_connected = False


async def close_mongodb_connection():
    """Close MongoDB connection"""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("🔌 MongoDB connection closed")


async def create_indexes():
    """Create database indexes for performance"""
    global database
    
    try:
        # Users
        await database.users.create_index("email", unique=True)
        await database.users.create_index("role")
        
        # Stations
        await database.stations.create_index([("location.latitude", 1), ("location.longitude", 1)])
        await database.stations.create_index("is_active")
        
        # Queues
        await database.queues.create_index([("station_id", 1), ("status", 1)])
        await database.queues.create_index("user_id")
        await database.queues.create_index("created_at")
        
        # Swaps
        await database.swaps.create_index("user_id")
        await database.swaps.create_index("station_id")
        await database.swaps.create_index("status")
        await database.swaps.create_index("qr_token", unique=True, sparse=True)
        
        # Transport Jobs
        await database.transport_jobs.create_index("status")
        await database.transport_jobs.create_index("assigned_transporter_id")
        await database.transport_jobs.create_index("created_at")
        
        # Staff Assignments
        await database.staff_assignments.create_index([("staff_id", 1), ("shift_start", 1)])
        await database.staff_assignments.create_index("station_id")
        
        # Tickets
        await database.tickets.create_index("status")
        await database.tickets.create_index([("related_entity_type", 1), ("related_entity_id", 1)])
        await database.tickets.create_index("priority")
        
        # GPS Logs
        await database.gps_logs.create_index([("user_id", 1), ("timestamp", -1)])
        await database.gps_logs.create_index("timestamp")
        
        # Credits
        await database.credits.create_index("user_id")
        await database.credits.create_index("created_at")
        
        # Partner Shops
        await database.partner_shops.create_index([("location.latitude", 1), ("location.longitude", 1)])
        
        # Batteries
        await database.batteries.create_index("battery_id", unique=True)
        await database.batteries.create_index("status")
        await database.batteries.create_index("current_location")
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return database
