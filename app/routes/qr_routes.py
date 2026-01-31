"""
QR Code Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.models import QRVerifyRequest, QRVerifyResponse
from app.services.qr_service import qr_service
from app.services.queue_service import queue_service
from app.database import get_database
from datetime import datetime

router = APIRouter()


@router.post("/verify", response_model=QRVerifyResponse)
async def verify_qr_code(request: QRVerifyRequest):
    """
    Verify QR token when user arrives at station
    Staff scans QR code to start swap
    """
    try:
        # Verify QR token
        verification = await qr_service.verify_qr_token(
            qr_token=request.qr_token,
            station_id=request.station_id
        )
        
        if not verification["valid"]:
            return QRVerifyResponse(
                valid=False,
                message=verification["message"]
            )
        
        # Mark token as used
        await qr_service.mark_token_used(request.qr_token)
        
        # Update swap status to active
        db = get_database()
        await db.swaps.update_one(
            {"_id": verification["swap_id"]},
            {
                "$set": {
                    "status": "active",
                    "started_at": datetime.utcnow(),
                    "staff_id": request.staff_id
                }
            }
        )
        
        # Update queue status
        await queue_service.update_queue_status(
            station_id=request.station_id,
            user_id=verification["user_id"],
            new_status="active"
        )
        
        return QRVerifyResponse(
            valid=True,
            swap_id=verification["swap_id"],
            user_name=verification["user_name"],
            message="QR verified successfully. Swap started."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR verification error: {str(e)}")


@router.get("/generate-image/{qr_token}")
async def get_qr_image(qr_token: str):
    """Generate QR code image from token"""
    try:
        image_base64 = qr_service.generate_qr_image(qr_token)
        
        if not image_base64:
            raise HTTPException(status_code=500, detail="Failed to generate QR image")
        
        return {
            "qr_token": qr_token,
            "qr_image": image_base64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
