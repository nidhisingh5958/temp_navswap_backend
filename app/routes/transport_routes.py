"""
Transport and Logistics Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.models import TransportJobResponse, TransportJobAccept
from app.services.business_services import logistics_service
from app.database import get_database

router = APIRouter()


@router.post("/job/accept", status_code=status.HTTP_200_OK)
async def accept_transport_job(request: TransportJobAccept):
    """Transporter accepts a job (Uber-style notification)"""
    try:
        success = await logistics_service.assign_transporter(
            job_id=request.job_id,
            transporter_id=request.transporter_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Job already assigned or not found")
        
        return {
            "success": True,
            "message": "Job accepted successfully",
            "job_id": request.job_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job/{job_id}/complete", status_code=status.HTTP_200_OK)
async def complete_transport_job(job_id: str, transporter_id: str):
    """Mark transport job as complete and earn rewards"""
    try:
        result = await logistics_service.complete_transport_job(
            job_id=job_id,
            transporter_id=transporter_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/available")
async def get_available_jobs(transporter_id: str, max_distance_km: float = 50):
    """Get available transport jobs for a transporter"""
    try:
        jobs = await logistics_service.get_available_jobs(
            transporter_id=transporter_id,
            max_distance_km=max_distance_km
        )
        
        return {
            "transporter_id": transporter_id,
            "available_jobs": jobs,
            "count": len(jobs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{transporter_id}")
async def get_transporter_history(transporter_id: str, limit: int = 20):
    """Get transporter's job history"""
    try:
        db = get_database()
        
        cursor = db.transport_jobs.find({
            "assigned_transporter_id": transporter_id
        }).sort("created_at", -1).limit(limit)
        
        jobs = await cursor.to_list(length=limit)
        
        total_credits = sum(job.get("credits_earned", 0) for job in jobs if job.get("credits_earned"))
        
        for job in jobs:
            job["_id"] = str(job["_id"])
        
        return {
            "transporter_id": transporter_id,
            "total_jobs": len(jobs),
            "total_credits_earned": total_credits,
            "jobs": jobs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
