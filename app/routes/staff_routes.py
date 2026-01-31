"""
Staff Management Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.models import StaffDiversionRequest
from app.services.business_services import staff_service
from app.database import get_database

router = APIRouter()


@router.get("/assignments/{staff_id}")
async def get_staff_assignments(staff_id: str):
    """Get staff member's current and past assignments"""
    try:
        db = get_database()
        
        # Get current assignment
        current = await db.staff_assignments.find_one({
            "staff_id": staff_id,
            "is_active": True
        })
        
        # Get assignment history
        cursor = db.staff_assignments.find({
            "staff_id": staff_id
        }).sort("shift_start", -1).limit(10)
        
        history = await cursor.to_list(length=10)
        
        for assignment in history:
            assignment["_id"] = str(assignment["_id"])
        
        if current:
            current["_id"] = str(current["_id"])
        
        return {
            "staff_id": staff_id,
            "current_assignment": current,
            "assignment_history": history
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diversion", status_code=status.HTTP_200_OK)
async def divert_staff(request: StaffDiversionRequest):
    """Divert staff from one station to another (AI-triggered)"""
    try:
        success = await staff_service.divert_staff(
            from_station_id=request.from_station_id,
            to_station_id=request.to_station_id,
            staff_ids=request.staff_ids,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to divert staff")
        
        return {
            "success": True,
            "message": f"Successfully diverted {len(request.staff_ids)} staff members",
            "from_station": request.from_station_id,
            "to_station": request.to_station_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/station/{station_id}")
async def get_station_staff(station_id: str):
    """Get all staff currently assigned to a station"""
    try:
        db = get_database()
        
        cursor = db.staff_assignments.find({
            "station_id": station_id,
            "is_active": True
        })
        
        assignments = await cursor.to_list(length=50)
        
        # Get staff details
        staff_ids = [a["staff_id"] for a in assignments]
        staff_cursor = db.users.find({
            "_id": {"$in": staff_ids},
            "role": "staff"
        })
        
        staff_members = await staff_cursor.to_list(length=50)
        
        return {
            "station_id": station_id,
            "total_staff": len(staff_members),
            "staff": staff_members
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
