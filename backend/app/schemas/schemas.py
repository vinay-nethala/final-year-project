from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, datetime
from app.models.entities import BatchStatus

# ----------------- Product Schemas -----------------
class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, example="Organic Whole Milk 1L")
    sku: str = Field(..., min_length=3, max_length=50, example="MLK-ORG-001")
    category: str = Field(..., min_length=2, max_length=100, example="Dairy")
    base_price: float = Field(..., gt=0, example=3.99)
    cost_price: float = Field(..., gt=0, example=2.20)
    is_active: bool = True

    @field_validator("cost_price")
    @classmethod
    def validate_cost_price(cls, v, info):
        base_price = info.data.get("base_price")
        if base_price is not None and v > base_price:
            raise ValueError("cost_price cannot be greater than base_price")
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    base_price: Optional[float] = Field(None, gt=0)
    cost_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    product_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Batch Schemas -----------------
class BatchBase(BaseModel):
    product_id: int
    batch_code: str = Field(..., min_length=2, max_length=50, example="BCH-2026-001")
    initial_qty: int = Field(..., gt=0, example=50)
    current_qty: int = Field(..., ge=0, example=50)
    manufacturing_date: Optional[date] = None
    expiry_date: date
    current_discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    status: BatchStatus = BatchStatus.ACTIVE

    @field_validator("current_qty")
    @classmethod
    def validate_qty(cls, v, info):
        init_qty = info.data.get("initial_qty")
        if init_qty is not None and v > init_qty:
            raise ValueError("current_qty cannot exceed initial_qty")
        return v

class BatchCreate(BaseModel):
    product_id: int
    batch_code: str
    initial_qty: int = Field(..., gt=0)
    current_qty: Optional[int] = None
    manufacturing_date: Optional[date] = None
    expiry_date: date

    @field_validator("current_qty")
    @classmethod
    def default_current_qty(cls, v, info):
        if v is None and "initial_qty" in info.data:
            return info.data["initial_qty"]
        return v

class BatchUpdate(BaseModel):
    current_qty: Optional[int] = Field(None, ge=0)
    current_discount_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[BatchStatus] = None

class BatchResponse(BatchBase):
    batch_id: int
    days_until_expiry: int
    urgency_band: str
    is_sellable: bool
    created_at: datetime
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True

# ----------------- Pricing Schemas -----------------
class PricingRecommendation(BaseModel):
    batch_id: int
    product_id: int
    product_name: str
    sku: str
    category: str
    days_until_expiry: int
    urgency_band: str
    stock_level: int
    base_price: float
    cost_price: float
    recommended_discount_pct: float
    final_unit_price: float
    policy_type: str
    policy_version: str
    explanation: str
    is_sellable: bool

# ----------------- POS Checkout Schemas -----------------
class CartItemInput(BaseModel):
    batch_id: int
    quantity: int = Field(..., gt=0, example=2)

class CheckoutRequest(BaseModel):
    items: List[CartItemInput] = Field(..., min_items=1)
    payment_method: str = "CASH"

class SaleItemResponse(BaseModel):
    item_id: int
    batch_id: int
    product_name: str
    quantity: int
    base_unit_price: float
    discount_pct: float
    final_unit_price: float
    unit_cost: float
    line_total: float
    line_profit: float

    class Config:
        from_attributes = True

class SaleReceiptResponse(BaseModel):
    sale_id: int
    sale_code: str
    total_amount: float
    total_cost: float
    total_profit: float
    total_items: int
    payment_method: str
    sold_at: datetime
    items: List[SaleItemResponse]

    class Config:
        from_attributes = True

# ----------------- Analytics & AI Schemas -----------------
class AnalyticsSummary(BaseModel):
    sales_count: int
    units_sold: int
    revenue: float
    gross_profit: float
    total_discount_given: float
    current_inventory_units: int
    expiring_soon_units: int # 0-5 days
    expired_units: int
    estimated_wastage_cost: float

class TimeseriesPoint(BaseModel):
    date: str
    revenue: float
    profit: float
    units_sold: int

class CategorySales(BaseModel):
    category: str
    revenue: float
    units: int

class DiscountDistributionItem(BaseModel):
    discount_pct: float
    count: int
    revenue: float

class AIStatusResponse(BaseModel):
    model_loaded: bool
    policy_type: str
    policy_version: str
    state_count: int
    allowed_actions: List[float]
    model_path: str
    last_trained: Optional[str] = None

class TrainRequest(BaseModel):
    episodes: int = Field(1000, ge=100, le=20000)
    learning_rate: float = Field(0.1, gt=0.0, le=1.0)
    discount_factor: float = Field(0.95, gt=0.0, le=1.0)
    epsilon: float = Field(0.2, ge=0.0, le=1.0)
    epsilon_decay: float = Field(0.995, gt=0.0, le=1.0)
    seed: int = 42

class SimulationComparisonResponse(BaseModel):
    simulation_episodes: int
    comparison_seed: int
    scenarios_evaluated: int
    rl_agent: dict
    baseline_rule: dict
    summary_verdict: str
