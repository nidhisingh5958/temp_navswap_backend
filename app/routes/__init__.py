"""
Route modules initialization
"""
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

__all__ = [
    "queue_routes",
    "qr_routes",
    "swap_routes",
    "station_routes",
    "transport_routes",
    "staff_routes",
    "admin_routes",
    "ai_routes",
    "recommendation_routes"
]
