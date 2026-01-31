"""
Configuration management for NavSwap Backend
Loads environment variables and provides application settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "NavSwap"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "navswap"
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_MIN_POOL_SIZE: int = 10
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_LOCATION: str = "location_updates"
    KAFKA_TOPIC_SWAPS: str = "swap_events"
    KAFKA_TOPIC_LOGISTICS: str = "logistics_events"
    KAFKA_TOPIC_ALERTS: str = "alert_events"
    
    # Security
    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    
    # AI Models - Local Paths
    MODEL_BASE_PATH: str = "/app/models"
    MODEL_LOAD_PREDICTION: str = ""
    MODEL_FAULT_PREDICTION: str = ""
    MODEL_ACTION_RECOMMENDATION: str = ""
    MODEL_TRAFFIC_FORECAST: str = ""
    MODEL_MICRO_AREA_TRAFFIC: str = ""
    MODEL_CUSTOMER_ARRIVAL: str = ""
    MODEL_BATTERY_USAGE_TREND: str = ""
    MODEL_BATTERY_REBALANCING: str = ""
    MODEL_STAFF_DIVERSION: str = ""
    MODEL_BATTERY_STOCK_ORDER: str = ""
    MODEL_PARTNER_STORAGE_ALLOCATION: str = ""
    MODEL_ENERGY_STABILITY: str = ""
    MODEL_STATION_RELIABILITY: str = ""
    
    # Geofencing
    GEOFENCE_RADIUS_METERS: int = 500
    APPROACHING_RADIUS_METERS: int = 1000
    
    # Queue Management
    QUEUE_BUFFER_SLOTS: int = 3
    QUEUE_MAX_CAPACITY: int = 20
    QR_TOKEN_EXPIRY_MINUTES: int = 15
    
    # Credits & Rewards
    TRANSPORT_BASE_CREDITS: int = 100
    TRANSPORT_DISTANCE_MULTIPLIER: float = 2.5
    SWAP_COMPLETION_CREDITS: int = 10
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/var/log/navswap/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
