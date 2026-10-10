import enum
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, 
    ForeignKey, Enum, Text, Index
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.expiry import calculate_days_until_expiry, get_expiry_urgency_band

class BatchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SOLD_OUT = "SOLD_OUT"
    DISCARDED = "DISCARDED"

class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    base_price = Column(Float, nullable=False)   # Selling price without discount
    cost_price = Column(Float, nullable=False)   # Cost price (floor)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    batches = relationship("Batch", back_populates="product", cascade="all, delete-orphan")

class Batch(Base):
    __tablename__ = "batches"

    batch_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    batch_code = Column(String(50), nullable=False, index=True)
    initial_qty = Column(Integer, nullable=False)
    current_qty = Column(Integer, nullable=False)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False, index=True)
    current_discount_pct = Column(Float, default=0.0, nullable=False)  # 0, 15, 30, 50, 75
    status = Column(Enum(BatchStatus), default=BatchStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="batches")
    sale_items = relationship("SaleItem", back_populates="batch")
    pricing_logs = relationship("PricingDecisionLog", back_populates="batch")

    @property
    def days_until_expiry(self) -> int:
        return calculate_days_until_expiry(self.expiry_date)

    @property
    def urgency_band(self) -> str:
        return get_expiry_urgency_band(self.days_until_expiry)

    @property
    def is_sellable(self) -> bool:
        return (
            self.status == BatchStatus.ACTIVE and 
            self.current_qty > 0 and 
            self.days_until_expiry >= 0
        )

class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sale_code = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_profit = Column(Float, nullable=False)
    total_items = Column(Integer, nullable=False)
    payment_method = Column(String(50), default="CASH", nullable=False)
    sold_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"

    item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.sale_id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.batch_id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    base_unit_price = Column(Float, nullable=False)
    discount_pct = Column(Float, nullable=False)
    final_unit_price = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)
    line_profit = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="items")
    batch = relationship("Batch", back_populates="sale_items")

class PricingDecisionLog(Base):
    __tablename__ = "pricing_decision_logs"

    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.batch_id"), nullable=False, index=True)
    days_to_expiry = Column(Integer, nullable=False)
    stock_level = Column(Integer, nullable=False)
    demand_scenario = Column(String(50), default="NORMAL", nullable=False)
    state_key = Column(String(50), nullable=False)
    recommended_discount_pct = Column(Float, nullable=False)
    base_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    final_price = Column(Float, nullable=False)
    policy_type = Column(String(50), default="RL_Q_LEARNING", nullable=False) # RL_Q_LEARNING or FIXED_RULE or FALLBACK
    policy_version = Column(String(50), default="v1.0", nullable=False)
    explanation = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    batch = relationship("Batch", back_populates="pricing_logs")
