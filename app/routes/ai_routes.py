"""
AI Prediction Routes - All 13 Models
"""
from fastapi import APIRouter, HTTPException, status
from app.models import (
    LoadPredictionRequest, LoadPredictionResponse,
    FaultPredictionRequest, FaultPredictionResponse,
    ActionRecommendationRequest, ActionRecommendationResponse,
    TrafficForecastRequest, TrafficForecastResponse,
    BatteryRebalancingRequest, BatteryRebalancingResponse
)
from app.services.ai_service import ai_service

router = APIRouter()


@router.post("/predict-load", response_model=LoadPredictionResponse)
async def predict_load(request: LoadPredictionRequest):
    """AI Model 1: Load Prediction"""
    try:
        result = await ai_service.predict_load(
            station_id=request.station_id,
            timestamp=request.timestamp,
            day_of_week=request.day_of_week,
            hour=request.hour,
            historical_avg_load=request.historical_avg_load
        )
        
        return LoadPredictionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load prediction error: {str(e)}")


@router.post("/predict-fault", response_model=FaultPredictionResponse)
async def predict_fault(request: FaultPredictionRequest):
    """AI Model 2: Fault Prediction"""
    try:
        result = await ai_service.predict_fault(
            entity_id=request.station_id or request.battery_id,
            age_days=request.age_days,
            swap_count=request.swap_count,
            charge_cycles=request.charge_cycles,
            health_percentage=request.health_percentage,
            recent_error_count=request.recent_error_count
        )
        
        return FaultPredictionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fault prediction error: {str(e)}")


@router.post("/predict-action", response_model=ActionRecommendationResponse)
async def predict_action(request: ActionRecommendationRequest):
    """AI Model 3: Action Recommendation"""
    try:
        result = await ai_service.recommend_action(
            station_id=request.station_id,
            current_queue_length=request.current_queue_length,
            available_batteries=request.available_batteries,
            predicted_demand=request.predicted_demand,
            current_staff_count=request.current_staff_count
        )
        
        return ActionRecommendationResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action recommendation error: {str(e)}")


@router.post("/forecast-traffic", response_model=TrafficForecastResponse)
async def forecast_traffic(request: TrafficForecastRequest):
    """AI Model 4: Traffic Forecast"""
    try:
        result = await ai_service.forecast_traffic(
            area_id=request.area_id,
            timestamp=request.timestamp,
            historical_data=request.historical_data
        )
        
        return TrafficForecastResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Traffic forecast error: {str(e)}")


@router.post("/predict-rebalancing", response_model=BatteryRebalancingResponse)
async def predict_rebalancing(request: BatteryRebalancingRequest):
    """AI Model 8: Battery Rebalancing"""
    try:
        result = await ai_service.predict_battery_rebalancing(
            station_inventories=request.station_inventories,
            predicted_demands=request.predicted_demands,
            partner_shop_inventories=request.partner_shop_inventories
        )
        
        return BatteryRebalancingResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebalancing prediction error: {str(e)}")


@router.get("/model-status")
async def get_model_status():
    """Get status of all 13 AI models"""
    try:
        status = await ai_service.get_model_status()
        
        loaded_count = sum(status.values())
        
        return {
            "total_models": 13,
            "models_loaded": loaded_count,
            "models_status": status,
            "health": "healthy" if loaded_count >= 10 else "degraded"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Additional model endpoints (5-7, 9-13) can be added similarly
@router.post("/predict-customer-arrival")
async def predict_customer_arrival(station_id: str):
    """AI Model 6: Customer Arrival Prediction"""
    result = await ai_service.predict_customer_arrival(station_id, {})
    return {"station_id": station_id, "estimated_arrival_minutes": result}


@router.post("/predict-staff-diversion")
async def predict_staff_diversion(from_station: str, to_station: str, load_diff: float):
    """AI Model 9: Staff Diversion"""
    should_divert = await ai_service.predict_staff_diversion(from_station, to_station, load_diff)
    return {
        "from_station": from_station,
        "to_station": to_station,
        "should_divert": should_divert,
        "load_differential": load_diff
    }
