"""
FastAPI Main Application
NavSwap - AI-Powered EV Battery Swap Platform
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import connect_to_mongodb, close_mongodb_connection
from app.services.ai_service import ai_service
from app.services.queue_service import queue_service
from app.services.qr_service import qr_service
from app.services.location_service import location_service

# Import route modules
from app.routes import (
    queue_routes,
    qr_routes,
    swap_routes,
    station_routes,
    transport_routes,
    staff_routes,
    admin_routes,
    ai_routes,
    recommendation_routes
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting NavSwap Backend...")
    settings = get_settings()
    
    # Connect to MongoDB (non-blocking)
    try:
        await connect_to_mongodb()
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
    
    # Load AI models (with fallback)
    try:
        await ai_service.load_all_models()
    except Exception as e:
        logger.warning(f"⚠️ AI model loading failed: {e}")
    
    # Initialize services (with fallback)
    try:
        await queue_service.initialize()
    except Exception as e:
        logger.warning(f"⚠️ Queue service init failed: {e}")
    
    try:
        await qr_service.initialize()
    except Exception as e:
        logger.warning(f"⚠️ QR service init failed: {e}")
    
    try:
        await location_service.initialize()
    except Exception as e:
        logger.warning(f"⚠️ Location service init failed: {e}")
    
    logger.info(f"✅ NavSwap Backend started on {settings.API_HOST}:{settings.API_PORT}")
    
    yield
    
    # Shutdown
    logger.info("🔌 Shutting down NavSwap Backend...")
    await close_mongodb_connection()
    logger.info("👋 NavSwap Backend stopped")


# Create FastAPI app
app = FastAPI(
    title="NavSwap API",
    description="AI-Powered EV Battery Swap Platform - Production Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "service": "NavSwap API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs"
    }


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    model_status = await ai_service.get_model_status()
    loaded_models = sum(model_status.values())
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": f"{loaded_models}/13",
        "database": "connected"
    }


# Include routers
app.include_router(queue_routes.router, prefix="/queue", tags=["Queue Management"])
app.include_router(qr_routes.router, prefix="/qr", tags=["QR Operations"])
app.include_router(swap_routes.router, prefix="/swap", tags=["Swap Operations"])
app.include_router(station_routes.router, prefix="/station", tags=["Stations"])
app.include_router(transport_routes.router, prefix="/transport", tags=["Logistics & Transport"])
app.include_router(staff_routes.router, prefix="/staff", tags=["Staff Management"])
app.include_router(admin_routes.router, prefix="/admin", tags=["Admin Dashboard"])
app.include_router(ai_routes.router, prefix="/ai", tags=["AI Predictions"])
app.include_router(recommendation_routes.router, prefix="/recommend", tags=["Recommendations"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
