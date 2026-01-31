"""
AI Service - Loads and manages 13 ML models for predictions
All models are loaded from local storage (no external APIs)
"""
import os
import pickle
import logging
from typing import Dict, Any, Optional
import numpy as np
from datetime import datetime
from app.config import get_settings

logger = logging.getLogger(__name__)


class AIService:
    """
    Central AI service managing all 13 ML models
    Models are loaded at application startup and kept in memory
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.models: Dict[str, Any] = {}
        self.model_loaded: Dict[str, bool] = {}
        
        # Model registry with paths from env
        self.model_registry = {
            "load_prediction": self.settings.MODEL_LOAD_PREDICTION,
            "fault_prediction": self.settings.MODEL_FAULT_PREDICTION,
            "action_recommendation": self.settings.MODEL_ACTION_RECOMMENDATION,
            "traffic_forecast": self.settings.MODEL_TRAFFIC_FORECAST,
            "micro_area_traffic": self.settings.MODEL_MICRO_AREA_TRAFFIC,
            "customer_arrival": self.settings.MODEL_CUSTOMER_ARRIVAL,
            "battery_usage_trend": self.settings.MODEL_BATTERY_USAGE_TREND,
            "battery_rebalancing": self.settings.MODEL_BATTERY_REBALANCING,
            "staff_diversion": self.settings.MODEL_STAFF_DIVERSION,
            "battery_stock_order": self.settings.MODEL_BATTERY_STOCK_ORDER,
            "partner_storage_allocation": self.settings.MODEL_PARTNER_STORAGE_ALLOCATION,
            "energy_stability": self.settings.MODEL_ENERGY_STABILITY,
            "station_reliability": self.settings.MODEL_STATION_RELIABILITY,
        }
    
    async def load_all_models(self):
        """Load all ML models from disk"""
        logger.info("🧠 Loading AI models...")
        
        for model_name, model_path in self.model_registry.items():
            try:
                if model_path and os.path.exists(model_path):
                    self.models[model_name] = self._load_model(model_path)
                    self.model_loaded[model_name] = True
                    logger.info(f"✅ Loaded model: {model_name}")
                else:
                    self.model_loaded[model_name] = False
                    logger.warning(f"⚠️  Model not found: {model_name} at {model_path}")
            except Exception as e:
                self.model_loaded[model_name] = False
                logger.error(f"❌ Failed to load model {model_name}: {e}")
        
        loaded_count = sum(self.model_loaded.values())
        logger.info(f"🧠 Loaded {loaded_count}/13 models successfully")
    
    def _load_model(self, model_path: str) -> Any:
        """Load a single model from disk (supports .pkl, .joblib)"""
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            logger.error(f"Error loading model from {model_path}: {e}")
            raise
    
    def _is_model_available(self, model_name: str) -> bool:
        """Check if model is loaded and available"""
        return self.model_loaded.get(model_name, False)
    
    # ============= 1. LOAD PREDICTION =============
    
    async def predict_load(
        self,
        station_id: str,
        timestamp: datetime,
        day_of_week: int,
        hour: int,
        historical_avg_load: float
    ) -> Dict[str, Any]:
        """
        Predict station load for a given time
        Returns predicted number of swaps and confidence score
        """
        if not self._is_model_available("load_prediction"):
            # Fallback to heuristic
            return self._fallback_load_prediction(historical_avg_load, hour, day_of_week)
        
        try:
            model = self.models["load_prediction"]
            
            # Feature engineering
            features = np.array([[
                day_of_week,
                hour,
                historical_avg_load,
                1 if day_of_week >= 5 else 0,  # is_weekend
                1 if 7 <= hour <= 9 or 17 <= hour <= 19 else 0  # is_rush_hour
            ]])
            
            predicted_load = float(model.predict(features)[0])
            confidence = 0.85  # Could get from model if it supports predict_proba
            
            # Generate recommendation
            if predicted_load > historical_avg_load * 1.5:
                recommendation = "High demand expected. Consider staff reinforcement."
            elif predicted_load < historical_avg_load * 0.5:
                recommendation = "Low demand expected. Can reduce staff."
            else:
                recommendation = "Normal operations expected."
            
            return {
                "station_id": station_id,
                "predicted_load": predicted_load,
                "confidence": confidence,
                "recommendation": recommendation
            }
        
        except Exception as e:
            logger.error(f"Load prediction error: {e}")
            return self._fallback_load_prediction(historical_avg_load, hour, day_of_week)
    
    def _fallback_load_prediction(self, historical_avg: float, hour: int, day_of_week: int) -> Dict[str, Any]:
        """Fallback heuristic when model is not available"""
        # Simple time-based heuristic
        multiplier = 1.0
        
        # Rush hour boost
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            multiplier = 1.5
        # Late night reduction
        elif 22 <= hour or hour <= 6:
            multiplier = 0.4
        # Weekend boost
        if day_of_week >= 5:
            multiplier *= 1.2
        
        predicted_load = historical_avg * multiplier
        
        return {
            "predicted_load": predicted_load,
            "confidence": 0.6,
            "recommendation": "Using heuristic-based prediction (model not loaded)"
        }
    
    # ============= 2. FAULT PREDICTION =============
    
    async def predict_fault(
        self,
        entity_id: str,
        age_days: int,
        swap_count: int,
        charge_cycles: int,
        health_percentage: float,
        recent_error_count: int = 0
    ) -> Dict[str, Any]:
        """
        Predict fault probability for battery or station
        """
        if not self._is_model_available("fault_prediction"):
            return self._fallback_fault_prediction(
                age_days, health_percentage, recent_error_count
            )
        
        try:
            model = self.models["fault_prediction"]
            
            features = np.array([[
                age_days,
                swap_count,
                charge_cycles,
                health_percentage,
                recent_error_count
            ]])
            
            fault_probability = float(model.predict_proba(features)[0][1])
            
            # Determine risk level
            if fault_probability >= 0.7:
                risk_level = "high"
                action = "Immediate maintenance required. Flag for inspection."
            elif fault_probability >= 0.4:
                risk_level = "medium"
                action = "Schedule preventive maintenance soon."
            else:
                risk_level = "low"
                action = "Continue monitoring. No immediate action needed."
            
            return {
                "entity_id": entity_id,
                "fault_probability": fault_probability,
                "risk_level": risk_level,
                "recommended_action": action
            }
        
        except Exception as e:
            logger.error(f"Fault prediction error: {e}")
            return self._fallback_fault_prediction(age_days, health_percentage, recent_error_count)
    
    def _fallback_fault_prediction(self, age_days: int, health: float, errors: int) -> Dict[str, Any]:
        """Fallback heuristic for fault prediction"""
        # Simple rule-based scoring
        fault_score = 0.0
        
        if health < 70:
            fault_score += 0.3
        if age_days > 730:  # 2 years
            fault_score += 0.2
        if errors > 5:
            fault_score += 0.4
        
        fault_score = min(fault_score, 1.0)
        
        risk_level = "high" if fault_score >= 0.7 else "medium" if fault_score >= 0.4 else "low"
        
        return {
            "fault_probability": fault_score,
            "risk_level": risk_level,
            "recommended_action": f"Risk level: {risk_level} (heuristic-based)"
        }
    
    # ============= 3. ACTION RECOMMENDATION =============
    
    async def recommend_action(
        self,
        station_id: str,
        current_queue_length: int,
        available_batteries: int,
        predicted_demand: float,
        current_staff_count: int
    ) -> Dict[str, Any]:
        """
        Recommend operational actions based on current state
        """
        if not self._is_model_available("action_recommendation"):
            return self._fallback_action_recommendation(
                current_queue_length, available_batteries, predicted_demand, current_staff_count
            )
        
        try:
            model = self.models["action_recommendation"]
            
            features = np.array([[
                current_queue_length,
                available_batteries,
                predicted_demand,
                current_staff_count
            ]])
            
            # Model returns action priorities (0-1 scores for different actions)
            action_scores = model.predict(features)[0]
            
            # Map scores to actions
            recommended_actions = []
            
            if available_batteries < predicted_demand * 0.5:
                recommended_actions.append("🔋 Request battery rebalancing urgently")
            
            if current_queue_length > 10:
                recommended_actions.append("👥 Deploy additional staff")
            
            if current_queue_length > 15:
                recommended_actions.append("🚨 Activate diversion to nearby stations")
            
            if available_batteries < 5:
                recommended_actions.append("📦 Order batteries from partner shops")
            
            if not recommended_actions:
                recommended_actions.append("✅ Operations normal - no action needed")
            
            priority_score = float(np.mean(action_scores))
            
            return {
                "station_id": station_id,
                "recommended_actions": recommended_actions,
                "priority_score": priority_score,
                "reasoning": f"Queue: {current_queue_length}, Batteries: {available_batteries}, Demand: {predicted_demand:.1f}"
            }
        
        except Exception as e:
            logger.error(f"Action recommendation error: {e}")
            return self._fallback_action_recommendation(
                current_queue_length, available_batteries, predicted_demand, current_staff_count
            )
    
    def _fallback_action_recommendation(
        self, queue: int, batteries: int, demand: float, staff: int
    ) -> Dict[str, Any]:
        """Fallback rule-based action recommendations"""
        actions = []
        
        if batteries < demand * 0.5:
            actions.append("🔋 Request battery rebalancing")
        if queue > 10 and staff < 3:
            actions.append("👥 Deploy additional staff")
        if batteries < 5:
            actions.append("📦 Order batteries from partners")
        if not actions:
            actions.append("✅ Operations normal")
        
        return {
            "recommended_actions": actions,
            "priority_score": min(queue / 20.0, 1.0),
            "reasoning": "Rule-based recommendation (model not loaded)"
        }
    
    # ============= 4. TRAFFIC FORECAST =============
    
    async def forecast_traffic(
        self,
        area_id: str,
        timestamp: datetime,
        historical_data: list
    ) -> Dict[str, Any]:
        """Forecast traffic congestion in area"""
        if not self._is_model_available("traffic_forecast"):
            return self._fallback_traffic_forecast(area_id, timestamp.hour)
        
        try:
            model = self.models["traffic_forecast"]
            
            # Process historical data into features
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            
            features = np.array([[hour, day_of_week, len(historical_data)]])
            
            congestion_level = float(model.predict(features)[0])
            
            return {
                "area_id": area_id,
                "predicted_congestion_level": congestion_level,
                "affected_stations": [],  # Would be computed based on geo-mapping
                "alternative_routes": []
            }
        
        except Exception as e:
            logger.error(f"Traffic forecast error: {e}")
            return self._fallback_traffic_forecast(area_id, timestamp.hour)
    
    def _fallback_traffic_forecast(self, area_id: str, hour: int) -> Dict[str, Any]:
        """Fallback traffic forecast"""
        # Rush hour = high congestion
        congestion = 0.8 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0.3
        
        return {
            "area_id": area_id,
            "predicted_congestion_level": congestion,
            "affected_stations": [],
            "alternative_routes": []
        }
    
    # ============= 5-13. OTHER MODELS (Similar Pattern) =============
    
    async def predict_customer_arrival(self, station_id: str, features: Dict[str, Any]) -> float:
        """Predict customer arrival time"""
        if self._is_model_available("customer_arrival"):
            # Use model
            pass
        return 10.0  # Fallback: 10 minutes
    
    async def predict_battery_rebalancing(
        self,
        station_inventories: Dict[str, int],
        predicted_demands: Dict[str, float],
        partner_inventories: Dict[str, int]
    ) -> Dict[str, Any]:
        """Generate battery rebalancing plan"""
        if not self._is_model_available("battery_rebalancing"):
            return self._fallback_rebalancing(station_inventories, predicted_demands)
        
        # Model-based rebalancing
        try:
            model = self.models["battery_rebalancing"]
            # Complex optimization logic here
            plan = []
            
            return {
                "rebalancing_plan": plan,
                "total_transfers": len(plan),
                "estimated_completion_hours": 2.5
            }
        except Exception as e:
            logger.error(f"Rebalancing error: {e}")
            return self._fallback_rebalancing(station_inventories, predicted_demands)
    
    def _fallback_rebalancing(
        self,
        inventories: Dict[str, int],
        demands: Dict[str, float]
    ) -> Dict[str, Any]:
        """Rule-based rebalancing"""
        plan = []
        
        # Simple: Move from oversupplied to undersupplied
        for station_id, inventory in inventories.items():
            demand = demands.get(station_id, 0)
            if inventory > demand * 1.5:
                plan.append({
                    "from": station_id,
                    "to": "nearest_undersupplied",
                    "quantity": int(inventory - demand)
                })
        
        return {
            "rebalancing_plan": plan,
            "total_transfers": len(plan),
            "estimated_completion_hours": len(plan) * 0.5
        }
    
    async def predict_staff_diversion(
        self,
        from_station: str,
        to_station: str,
        load_differential: float
    ) -> bool:
        """Determine if staff diversion is needed"""
        if self._is_model_available("staff_diversion"):
            # Use model
            pass
        
        # Fallback: Divert if load difference > 30%
        return load_differential > 0.3
    
    async def predict_battery_stock_order(
        self,
        current_stock: int,
        predicted_usage: float,
        lead_time_days: int
    ) -> Dict[str, Any]:
        """Predict battery stock order quantity"""
        # Simple safety stock calculation
        order_quantity = max(0, int(predicted_usage * lead_time_days * 1.2 - current_stock))
        
        return {
            "order_quantity": order_quantity,
            "urgency": "high" if current_stock < predicted_usage * 2 else "normal"
        }
    
    async def get_model_status(self) -> Dict[str, bool]:
        """Get status of all models"""
        return self.model_loaded.copy()


# Global AI service instance
ai_service = AIService()
