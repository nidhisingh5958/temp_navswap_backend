"""
Admin Dashboard Routes
"""
from fastapi import APIRouter, HTTPException
from app.models import LiveDashboardResponse, LogisticsOverview, TrafficAnalysis
from app.database import get_database
from datetime import datetime, timedelta
from app.services.queue_service import queue_service

router = APIRouter()


@router.get("/live", response_model=LiveDashboardResponse)
async def get_live_dashboard():
    """Get real-time dashboard data"""
    try:
        db = get_database()
        
        # Count active stations
        total_stations = await db.stations.count_documents({"is_active": True})
        
        # Count active swaps
        active_swaps = await db.swaps.count_documents({
            "status": {"$in": ["confirmed", "approaching", "active"]}
        })
        
        # Total queue length across all stations
        total_queue = await db.queues.count_documents({
            "status": {"$in": ["confirmed", "approaching"]}
        })
        
        # Active transporters (with jobs in last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        active_transporters = await db.transport_jobs.distinct(
            "assigned_transporter_id",
            {
                "status": {"$in": ["assigned", "in_transit"]},
                "accepted_at": {"$gte": one_hour_ago}
            }
        )
        
        # Pending transport jobs
        pending_jobs = await db.transport_jobs.count_documents({
            "status": "pending"
        })
        
        # Open tickets
        open_tickets = await db.tickets.count_documents({
            "status": {"$in": ["open", "in_progress"]}
        })
        
        # Calculate system health score (0-1)
        system_health = 0.95  # Simplified - could be based on multiple metrics
        
        return LiveDashboardResponse(
            timestamp=datetime.utcnow(),
            total_stations=total_stations,
            active_swaps=active_swaps,
            total_queue_length=total_queue,
            active_transporters=len(active_transporters),
            pending_transport_jobs=pending_jobs,
            open_tickets=open_tickets,
            system_health_score=system_health
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logistics", response_model=LogisticsOverview)
async def get_logistics_overview():
    """Get logistics and battery inventory overview"""
    try:
        db = get_database()
        
        # Count batteries by location
        total_batteries = await db.batteries.count_documents({})
        
        batteries_in_transit = await db.transport_jobs.count_documents({
            "status": "in_transit"
        })
        
        # Aggregate batteries at stations
        station_batteries = await db.batteries.count_documents({
            "current_location": {"$regex": "^station_"}
        })
        
        # Batteries at partner shops
        partner_batteries = await db.batteries.count_documents({
            "current_location": {"$regex": "^partner_"}
        })
        
        # Faulty batteries
        faulty_batteries = await db.batteries.count_documents({
            "status": "faulty"
        })
        
        # Pending rebalancing jobs
        pending_rebalancing = await db.transport_jobs.count_documents({
            "status": "pending",
            "priority": {"$gte": 3}
        })
        
        return LogisticsOverview(
            total_batteries=total_batteries,
            batteries_in_transit=batteries_in_transit,
            batteries_at_stations=station_batteries,
            batteries_at_partners=partner_batteries,
            faulty_batteries=faulty_batteries,
            pending_rebalancing_jobs=pending_rebalancing
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traffic", response_model=TrafficAnalysis)
async def get_traffic_analysis():
    """Get traffic congestion analysis"""
    try:
        # This would integrate with AI traffic model
        # Simplified version here
        
        return TrafficAnalysis(
            high_congestion_areas=["downtown", "airport_zone"],
            affected_stations=["station_001", "station_015"],
            average_delay_minutes=12.5,
            recommendations=[
                "Divert users to Station 003 and Station 008",
                "Increase buffer time estimates by 15%",
                "Consider deploying mobile swap units"
            ]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stations/overview")
async def get_stations_overview():
    """Get overview of all stations with key metrics"""
    try:
        db = get_database()
        
        cursor = db.stations.find({"is_active": True})
        stations = await cursor.to_list(length=100)
        
        enriched_stations = []
        
        for station in stations:
            station_id = str(station["_id"])
            queue_length = await queue_service.get_queue_length(station_id)
            
            enriched_stations.append({
                "station_id": station_id,
                "name": station["name"],
                "location": station["location"],
                "capacity": station["capacity"],
                "inventory": station["inventory"],
                "current_queue_length": queue_length,
                "utilization": (queue_length / station["capacity"]) * 100
            })
        
        return {
            "total_stations": len(enriched_stations),
            "stations": enriched_stations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
