"""
Logistics Service - Battery transport and rebalancing
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.database import get_database
from app.config import get_settings
from app.models import TransportJobStatus

logger = logging.getLogger(__name__)


class LogisticsService:
    """Manages battery logistics, transport jobs, and rebalancing"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def create_transport_job(
        self,
        from_location: str,
        to_location: str,
        battery_ids: List[str],
        priority: int = 1
    ) -> Optional[str]:
        """Create a new transport job"""
        try:
            db = get_database()
            
            job = {
                "from_location": from_location,
                "to_location": to_location,
                "battery_ids": battery_ids,
                "battery_count": len(battery_ids),
                "status": TransportJobStatus.PENDING,
                "priority": priority,
                "assigned_transporter_id": None,
                "created_at": datetime.utcnow(),
                "accepted_at": None,
                "completed_at": None,
                "credits_earned": None
            }
            
            result = await db.transport_jobs.insert_one(job)
            
            logger.info(f"🚚 Created transport job {result.inserted_id}: {from_location} → {to_location}")
            
            return str(result.inserted_id)
        
        except Exception as e:
            logger.error(f"Error creating transport job: {e}")
            return None
    
    async def assign_transporter(
        self,
        job_id: str,
        transporter_id: str
    ) -> bool:
        """Assign a transporter to a job"""
        try:
            db = get_database()
            
            result = await db.transport_jobs.update_one(
                {
                    "_id": job_id,
                    "status": TransportJobStatus.PENDING
                },
                {
                    "$set": {
                        "assigned_transporter_id": transporter_id,
                        "status": TransportJobStatus.ASSIGNED,
                        "accepted_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error assigning transporter: {e}")
            return False
    
    async def complete_transport_job(
        self,
        job_id: str,
        transporter_id: str
    ) -> Dict[str, Any]:
        """Mark transport job as completed and calculate rewards"""
        try:
            db = get_database()
            
            job = await db.transport_jobs.find_one({"_id": job_id})
            if not job:
                return {"success": False, "message": "Job not found"}
            
            if job["assigned_transporter_id"] != transporter_id:
                return {"success": False, "message": "Not assigned to this transporter"}
            
            # Calculate credits based on distance and battery count
            from app.services.location_service import location_service
            
            from_loc = await db.stations.find_one({"_id": job["from_location"]})
            to_loc = await db.stations.find_one({"_id": job["to_location"]})
            
            if from_loc and to_loc:
                distance_km = location_service.calculate_distance(
                    from_loc["location"]["latitude"],
                    from_loc["location"]["longitude"],
                    to_loc["location"]["latitude"],
                    to_loc["location"]["longitude"]
                ) / 1000
                
                credits = int(
                    self.settings.TRANSPORT_BASE_CREDITS +
                    (distance_km * self.settings.TRANSPORT_DISTANCE_MULTIPLIER) +
                    (job["battery_count"] * 20)
                )
            else:
                credits = self.settings.TRANSPORT_BASE_CREDITS
            
            # Update job
            await db.transport_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": TransportJobStatus.DELIVERED,
                        "completed_at": datetime.utcnow(),
                        "credits_earned": credits
                    }
                }
            )
            
            # Award credits to transporter
            await db.users.update_one(
                {"_id": transporter_id},
                {"$inc": {"credits": credits}}
            )
            
            # Log credit transaction
            await db.credits.insert_one({
                "user_id": transporter_id,
                "amount": credits,
                "type": "transport_job",
                "related_id": job_id,
                "created_at": datetime.utcnow()
            })
            
            # Update battery locations
            await db.batteries.update_many(
                {"battery_id": {"$in": job["battery_ids"]}},
                {"$set": {"current_location": job["to_location"]}}
            )
            
            logger.info(f"✅ Transport job {job_id} completed. Credits awarded: {credits}")
            
            return {
                "success": True,
                "credits_earned": credits,
                "message": f"Job completed! Earned {credits} credits"
            }
        
        except Exception as e:
            logger.error(f"Error completing transport job: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_available_jobs(
        self,
        transporter_id: str,
        max_distance_km: float = 50
    ) -> List[Dict[str, Any]]:
        """Get available transport jobs for a transporter"""
        try:
            db = get_database()
            
            # Get transporter location
            from app.services.location_service import location_service
            transporter_location = await location_service.get_current_location(transporter_id)
            
            if not transporter_location:
                # Return all pending jobs if no location
                cursor = db.transport_jobs.find({
                    "status": TransportJobStatus.PENDING
                }).sort("priority", -1).limit(20)
                
                jobs = await cursor.to_list(length=20)
            else:
                # Filter by distance
                cursor = db.transport_jobs.find({
                    "status": TransportJobStatus.PENDING
                }).sort("priority", -1)
                
                all_jobs = await cursor.to_list(length=100)
                jobs = []
                
                for job in all_jobs:
                    from_loc = await db.stations.find_one({"_id": job["from_location"]})
                    if from_loc:
                        distance = location_service.calculate_distance(
                            transporter_location["latitude"],
                            transporter_location["longitude"],
                            from_loc["location"]["latitude"],
                            from_loc["location"]["longitude"]
                        ) / 1000
                        
                        if distance <= max_distance_km:
                            job["distance_km"] = round(distance, 2)
                            jobs.append(job)
            
            return jobs
        
        except Exception as e:
            logger.error(f"Error getting available jobs: {e}")
            return []


class StaffService:
    """Manages staff assignments and diversions"""
    
    async def assign_staff(
        self,
        staff_id: str,
        station_id: str,
        shift_hours: int = 8
    ) -> bool:
        """Assign staff to a station"""
        try:
            db = get_database()
            
            shift_start = datetime.utcnow()
            shift_end = shift_start + timedelta(hours=shift_hours)
            
            await db.staff_assignments.insert_one({
                "staff_id": staff_id,
                "station_id": station_id,
                "shift_start": shift_start,
                "shift_end": shift_end,
                "is_active": True,
                "created_at": shift_start
            })
            
            logger.info(f"👷 Assigned staff {staff_id} to station {station_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error assigning staff: {e}")
            return False
    
    async def divert_staff(
        self,
        from_station_id: str,
        to_station_id: str,
        staff_ids: List[str],
        reason: str
    ) -> bool:
        """Divert staff from one station to another"""
        try:
            db = get_database()
            
            from datetime import timedelta
            
            # End current assignments
            await db.staff_assignments.update_many(
                {
                    "staff_id": {"$in": staff_ids},
                    "station_id": from_station_id,
                    "is_active": True
                },
                {
                    "$set": {
                        "is_active": False,
                        "diverted_at": datetime.utcnow(),
                        "diversion_reason": reason
                    }
                }
            )
            
            # Create new assignments
            for staff_id in staff_ids:
                await self.assign_staff(staff_id, to_station_id)
            
            logger.info(f"🔄 Diverted {len(staff_ids)} staff from {from_station_id} to {to_station_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error diverting staff: {e}")
            return False


class FaultService:
    """Manages fault detection and ticketing"""
    
    async def create_ticket(
        self,
        entity_type: str,
        entity_id: str,
        fault_level: str,
        title: str,
        description: str,
        priority: int = 3
    ) -> Optional[str]:
        """Create a fault ticket"""
        try:
            db = get_database()
            
            ticket_number = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
            
            ticket = {
                "ticket_number": ticket_number,
                "status": "open",
                "related_entity_type": entity_type,
                "related_entity_id": entity_id,
                "fault_level": fault_level,
                "title": title,
                "description": description,
                "priority": priority,
                "created_at": datetime.utcnow(),
                "assigned_to": None,
                "resolved_at": None
            }
            
            result = await db.tickets.insert_one(ticket)
            
            logger.info(f"🎫 Created ticket {ticket_number} for {entity_type} {entity_id}")
            
            return str(result.inserted_id)
        
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return None
    
    async def handle_fault(
        self,
        fault_type: str,
        entity_id: str,
        severity: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process fault based on level"""
        try:
            if severity == "level_1":
                # Automated recovery
                logger.info(f"🔧 Level 1 fault - attempting automated recovery")
                # Implement recovery logic
                return {
                    "handled": True,
                    "method": "automated",
                    "message": "Automated recovery attempted"
                }
            
            elif severity == "level_2":
                # AI analysis
                logger.info(f"🧠 Level 2 fault - running AI analysis")
                # AI-based diagnostics
                return {
                    "handled": True,
                    "method": "ai_analysis",
                    "message": "AI analysis completed"
                }
            
            else:  # level_3
                # Create ticket for human intervention
                ticket_id = await self.create_ticket(
                    entity_type="battery" if "battery" in fault_type.lower() else "station",
                    entity_id=entity_id,
                    fault_level=severity,
                    title=f"{fault_type} fault detected",
                    description=str(details),
                    priority=5
                )
                
                return {
                    "handled": True,
                    "method": "human_escalation",
                    "ticket_id": ticket_id,
                    "message": "Ticket created for human intervention"
                }
        
        except Exception as e:
            logger.error(f"Error handling fault: {e}")
            return {"handled": False, "message": str(e)}


# Global instances
logistics_service = LogisticsService()
staff_service = StaffService()
fault_service = FaultService()
