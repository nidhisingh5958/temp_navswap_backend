"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============= ENUMS =============

class UserRole(str, Enum):
    CONSUMER = "consumer"
    STAFF = "staff"
    TRANSPORTER = "transporter"
    ADMIN = "admin"


class SwapStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    APPROACHING = "approaching"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BatteryStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAULTY = "faulty"
    MAINTENANCE = "maintenance"


class TransportJobStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class FaultLevel(str, Enum):
    LEVEL_1 = "level_1"  # Automated recovery
    LEVEL_2 = "level_2"  # AI analysis
    LEVEL_3 = "level_3"  # Human escalation


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ============= USER MODELS =============

class UserBase(BaseModel):
    name: str
    email: str
    phone: str
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str = Field(alias="_id")
    created_at: datetime
    credits: int = 0
    
    class Config:
        populate_by_name = True


# ============= LOCATION MODELS =============

class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LocationUpdate(BaseModel):
    user_id: str
    location: Location
    speed: Optional[float] = None
    heading: Optional[float] = None


# ============= STATION MODELS =============

class StationInventory(BaseModel):
    total_batteries: int = Field(..., ge=0)
    healthy_batteries: int = Field(..., ge=0)
    charging_batteries: int = Field(..., ge=0)
    faulty_batteries: int = Field(..., ge=0)


class StationBase(BaseModel):
    name: str
    location: Location
    capacity: int = Field(..., gt=0)
    inventory: StationInventory
    is_active: bool = True


class StationResponse(StationBase):
    id: str = Field(alias="_id")
    current_queue_length: int = 0
    predicted_load: Optional[float] = None
    predicted_fault_risk: Optional[float] = None
    
    class Config:
        populate_by_name = True


# ============= QUEUE MODELS =============

class QueueEntry(BaseModel):
    position: int
    user_id: str
    user_name: str
    estimated_wait_minutes: int
    qr_token: Optional[str] = None


class QueueConfirmRequest(BaseModel):
    station_id: str
    user_id: str
    current_location: Location


class QueueConfirmResponse(BaseModel):
    queue_position: int
    estimated_wait_minutes: int
    qr_token: str
    qr_expiry: datetime
    station_name: str
    station_location: Location


class QueueStatusResponse(BaseModel):
    station_id: str
    total_in_queue: int
    current_position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    queue_entries: List[QueueEntry] = []


# ============= QR MODELS =============

class QRVerifyRequest(BaseModel):
    qr_token: str
    station_id: str
    staff_id: str


class QRVerifyResponse(BaseModel):
    valid: bool
    swap_id: Optional[str] = None
    user_name: Optional[str] = None
    message: str


# ============= SWAP MODELS =============

class SwapCompleteRequest(BaseModel):
    swap_id: str
    staff_id: str
    old_battery_id: str
    new_battery_id: str
    old_battery_health: BatteryStatus
    notes: Optional[str] = None


class SwapResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    station_id: str
    status: SwapStatus
    qr_token: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    old_battery_id: Optional[str] = None
    new_battery_id: Optional[str] = None
    
    class Config:
        populate_by_name = True


# ============= BATTERY MODELS =============

class BatteryBase(BaseModel):
    battery_id: str
    status: BatteryStatus
    health_percentage: float = Field(..., ge=0, le=100)
    charge_cycles: int = Field(..., ge=0)
    current_location: str  # station_id or partner_shop_id


class BatteryResponse(BatteryBase):
    id: str = Field(alias="_id")
    manufactured_date: datetime
    last_swap_date: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


# ============= LOGISTICS MODELS =============

class TransportJobCreate(BaseModel):
    from_location: str  # station_id or partner_shop_id
    to_location: str
    battery_ids: List[str]
    priority: int = Field(default=1, ge=1, le=5)


class TransportJobResponse(BaseModel):
    id: str = Field(alias="_id")
    from_location: str
    to_location: str
    battery_ids: List[str]
    status: TransportJobStatus
    assigned_transporter_id: Optional[str] = None
    created_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    credits_earned: Optional[int] = None
    
    class Config:
        populate_by_name = True


class TransportJobAccept(BaseModel):
    job_id: str
    transporter_id: str
    current_location: Location


# ============= STAFF MODELS =============

class StaffAssignment(BaseModel):
    staff_id: str
    station_id: str
    shift_start: datetime
    shift_end: datetime
    is_active: bool = True


class StaffDiversionRequest(BaseModel):
    from_station_id: str
    to_station_id: str
    staff_ids: List[str]
    reason: str


# ============= FAULT & TICKET MODELS =============

class FaultDetection(BaseModel):
    station_id: str
    battery_id: Optional[str] = None
    fault_type: str
    severity: FaultLevel
    description: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class TicketCreate(BaseModel):
    related_entity_type: str  # "station", "battery", "swap"
    related_entity_id: str
    fault_level: FaultLevel
    title: str
    description: str
    priority: int = Field(default=3, ge=1, le=5)


class TicketResponse(BaseModel):
    id: str = Field(alias="_id")
    ticket_number: str
    status: TicketStatus
    related_entity_type: str
    related_entity_id: str
    fault_level: FaultLevel
    title: str
    description: str
    priority: int
    created_at: datetime
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


# ============= PARTNER SHOP MODELS =============

class PartnerShopBase(BaseModel):
    name: str
    location: Location
    storage_capacity: int
    current_inventory: int = 0


class PartnerShopResponse(PartnerShopBase):
    id: str = Field(alias="_id")
    created_at: datetime
    
    class Config:
        populate_by_name = True


# ============= AI PREDICTION MODELS =============

class LoadPredictionRequest(BaseModel):
    station_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    day_of_week: int = Field(..., ge=0, le=6)
    hour: int = Field(..., ge=0, le=23)
    historical_avg_load: float


class LoadPredictionResponse(BaseModel):
    station_id: str
    predicted_load: float
    confidence: float
    recommendation: str


class FaultPredictionRequest(BaseModel):
    station_id: str
    battery_id: Optional[str] = None
    age_days: int
    swap_count: int
    charge_cycles: int
    health_percentage: float
    recent_error_count: int = 0


class FaultPredictionResponse(BaseModel):
    entity_id: str
    fault_probability: float
    risk_level: str  # low, medium, high
    recommended_action: str


class ActionRecommendationRequest(BaseModel):
    station_id: str
    current_queue_length: int
    available_batteries: int
    predicted_demand: float
    current_staff_count: int


class ActionRecommendationResponse(BaseModel):
    station_id: str
    recommended_actions: List[str]
    priority_score: float
    reasoning: str


class TrafficForecastRequest(BaseModel):
    area_id: str
    timestamp: datetime
    historical_data: List[Dict[str, Any]]


class TrafficForecastResponse(BaseModel):
    area_id: str
    predicted_congestion_level: float
    affected_stations: List[str]
    alternative_routes: List[str]


class BatteryRebalancingRequest(BaseModel):
    station_inventories: Dict[str, int]
    predicted_demands: Dict[str, float]
    partner_shop_inventories: Dict[str, int]


class BatteryRebalancingResponse(BaseModel):
    rebalancing_plan: List[Dict[str, Any]]
    total_transfers: int
    estimated_completion_hours: float


# ============= ADMIN DASHBOARD MODELS =============

class LiveDashboardResponse(BaseModel):
    timestamp: datetime
    total_stations: int
    active_swaps: int
    total_queue_length: int
    active_transporters: int
    pending_transport_jobs: int
    open_tickets: int
    system_health_score: float


class LogisticsOverview(BaseModel):
    total_batteries: int
    batteries_in_transit: int
    batteries_at_stations: int
    batteries_at_partners: int
    faulty_batteries: int
    pending_rebalancing_jobs: int


class TrafficAnalysis(BaseModel):
    high_congestion_areas: List[str]
    affected_stations: List[str]
    average_delay_minutes: float
    recommendations: List[str]


# ============= RECOMMENDATION MODELS =============

class RecommendationRequest(BaseModel):
    user_id: str
    current_location: Location
    battery_level: Optional[float] = None


class StationRecommendation(BaseModel):
    station_id: str
    station_name: str
    distance_km: float
    estimated_travel_minutes: int
    current_queue_length: int
    estimated_wait_minutes: int
    total_time_minutes: int
    recommendation_score: float


class RecommendationResponse(BaseModel):
    recommended_stations: List[StationRecommendation]
    traffic_alerts: List[str]
    optimal_station_id: str
