"""
Swap Operation Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.models import SwapCompleteRequest, SwapResponse, BatteryStatus
from app.services.queue_service import queue_service
from app.services.business_services import fault_service
from app.database import get_database
from datetime import datetime

router = APIRouter()


@router.post("/complete", status_code=status.HTTP_200_OK)
async def complete_swap(request: SwapCompleteRequest):
    """
    Staff marks swap as complete
    Updates inventory, removes from queue, handles faulty batteries
    """
    try:
        db = get_database()
        
        # Get swap record
        swap = await db.swaps.find_one({"_id": request.swap_id})
        if not swap:
            raise HTTPException(status_code=404, detail="Swap not found")
        
        if swap["status"] != "active":
            raise HTTPException(status_code=400, detail="Swap is not active")
        
        # Update swap record
        await db.swaps.update_one(
            {"_id": request.swap_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "old_battery_id": request.old_battery_id,
                    "new_battery_id": request.new_battery_id,
                    "notes": request.notes
                }
            }
        )
        
        # Update battery records
        await db.batteries.update_one(
            {"battery_id": request.old_battery_id},
            {
                "$set": {
                    "status": request.old_battery_health.value,
                    "current_location": swap["station_id"],
                    "last_swap_date": datetime.utcnow()
                }
            }
        )
        
        await db.batteries.update_one(
            {"battery_id": request.new_battery_id},
            {
                "$set": {
                    "current_location": f"vehicle_{swap['user_id']}",
                    "last_swap_date": datetime.utcnow()
                },
                "$inc": {"swap_count": 1}
            }
        )
        
        # Update station inventory
        await db.stations.update_one(
            {"_id": swap["station_id"]},
            {
                "$inc": {
                    "inventory.total_batteries": 0,  # Net zero (one in, one out)
                    "inventory.healthy_batteries": -1,  # One healthy removed
                    "inventory.faulty_batteries": 1 if request.old_battery_health == BatteryStatus.FAULTY else 0
                }
            }
        )
        
        # Remove from queue
        await queue_service.remove_from_queue(
            station_id=swap["station_id"],
            user_id=swap["user_id"],
            reason="completed"
        )
        
        # Award credits to user
        await db.users.update_one(
            {"_id": swap["user_id"]},
            {"$inc": {"credits": db.config.get("SWAP_COMPLETION_CREDITS", 10)}}
        )
        
        # Handle faulty battery
        if request.old_battery_health == BatteryStatus.FAULTY:
            await fault_service.create_ticket(
                entity_type="battery",
                entity_id=request.old_battery_id,
                fault_level="level_3",
                title="Faulty battery detected during swap",
                description=f"Battery {request.old_battery_id} flagged as faulty. Notes: {request.notes}",
                priority=4
            )
        
        return {
            "success": True,
            "message": "Swap completed successfully",
            "swap_id": request.swap_id,
            "credits_earned": 10
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing swap: {str(e)}")


@router.get("/{swap_id}", response_model=SwapResponse)
async def get_swap_details(swap_id: str):
    """Get swap details"""
    try:
        db = get_database()
        swap = await db.swaps.find_one({"_id": swap_id})
        
        if not swap:
            raise HTTPException(status_code=404, detail="Swap not found")
        
        swap["_id"] = str(swap["_id"])
        return SwapResponse(**swap)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_swap_history(user_id: str, limit: int = 20):
    """Get user's swap history"""
    try:
        db = get_database()
        
        cursor = db.swaps.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        swaps = await cursor.to_list(length=limit)
        
        for swap in swaps:
            swap["_id"] = str(swap["_id"])
        
        return {
            "user_id": user_id,
            "total_swaps": len(swaps),
            "swaps": swaps
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
