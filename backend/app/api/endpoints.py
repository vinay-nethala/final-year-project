import os
import sys
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Product, Batch, Sale, BatchStatus
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchCreate, BatchUpdate, BatchResponse,
    PricingRecommendation, CheckoutRequest, SaleReceiptResponse,
    AnalyticsSummary, TimeseriesPoint, CategorySales, DiscountDistributionItem,
    AIStatusResponse, TrainRequest, SimulationComparisonResponse
)
from app.services.pricing_service import pricing_service
from app.services.checkout_service import checkout_service
from app.services.analytics_service import analytics_service
from app.rl.environment import RetailExpiryEnv
from app.rl.agent import QLearningAgent
from app.rl.baseline import run_policy_simulation
from app.core.config import settings

api_router = APIRouter()

# Global state tracker for training to avoid concurrent training loops
training_lock = False

# ----------------- Health -----------------
@api_router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected",
        "model_loaded": pricing_service.is_model_loaded,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ----------------- Products Endpoints -----------------
@api_router.get("/products", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if search:
        query = query.filter((Product.name.ilike(f"%{search}%")) | (Product.sku.ilike(f"%{search}%")))
    return query.order_by(Product.name.asc()).all()

@api_router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.sku == product_in.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{product_in.sku}' already exists.")
    
    product = Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@api_router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found.")
    return prod

@api_router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found.")
    
    update_data = product_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(prod, field, val)
        
    db.commit()
    db.refresh(prod)
    return prod

# ----------------- Batches Endpoints -----------------
@api_router.get("/batches", response_model=List[BatchResponse])
def get_batches(
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Batch)
    if product_id:
        query = query.filter(Batch.product_id == product_id)
    if status:
        query = query.filter(Batch.status == status)
    return query.order_by(Batch.expiry_date.asc()).all()

@api_router.post("/batches", response_model=BatchResponse, status_code=201)
def create_batch(batch_in: BatchCreate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.product_id == batch_in.product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product {batch_in.product_id} not found.")

    batch = Batch(**batch_in.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

@api_router.get("/batches/expiring", response_model=List[BatchResponse])
def get_expiring_batches(
    max_days: int = Query(5, description="Lookahead window in days"),
    db: Session = Depends(get_db)
):
    batches = db.query(Batch).filter(Batch.status == BatchStatus.ACTIVE).order_by(Batch.expiry_date.asc()).all()
    # Filter in Python using pure date calculation function
    return [b for b in batches if 0 <= b.days_until_expiry <= max_days and b.current_qty > 0]

@api_router.get("/batches/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batch

@api_router.patch("/batches/{batch_id}", response_model=BatchResponse)
def update_batch(batch_id: int, batch_in: BatchUpdate, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    
    update_data = batch_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(batch, field, val)

    db.commit()
    db.refresh(batch)
    return batch

# ----------------- Dynamic Pricing Endpoint -----------------
@api_router.get("/price/{batch_id}", response_model=PricingRecommendation)
def get_recommended_price(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    pricing = pricing_service.recommend_discount(batch)
    
    return PricingRecommendation(
        batch_id=batch.batch_id,
        product_id=batch.product.product_id,
        product_name=batch.product.name,
        sku=batch.product.sku,
        category=batch.product.category,
        days_until_expiry=batch.days_until_expiry,
        urgency_band=batch.urgency_band,
        stock_level=batch.current_qty,
        base_price=batch.product.base_price,
        cost_price=batch.product.cost_price,
        recommended_discount_pct=pricing["recommended_discount_pct"],
        final_unit_price=pricing["final_price"],
        policy_type=pricing["policy_type"],
        policy_version=pricing["policy_version"],
        explanation=pricing["explanation"],
        is_sellable=batch.is_sellable
    )

# ----------------- POS Checkout -----------------
@api_router.post("/checkout", response_model=SaleReceiptResponse)
def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    return checkout_service.process_checkout(db, request)

@api_router.get("/sales", response_model=List[SaleReceiptResponse])
def get_sales(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Sale).order_by(Sale.sold_at.desc()).limit(limit).all()

# ----------------- Analytics Endpoints -----------------
@api_router.get("/analytics/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    return analytics_service.get_summary(db)

@api_router.get("/analytics/timeseries", response_model=List[TimeseriesPoint])
def get_analytics_timeseries(db: Session = Depends(get_db)):
    return analytics_service.get_timeseries(db)

@api_router.get("/analytics/categories", response_model=List[CategorySales])
def get_analytics_categories(db: Session = Depends(get_db)):
    return analytics_service.get_category_distribution(db)

@api_router.get("/analytics/discounts", response_model=List[DiscountDistributionItem])
def get_analytics_discounts(db: Session = Depends(get_db)):
    return analytics_service.get_discount_distribution(db)

# ----------------- AI / RL Management -----------------
@api_router.get("/ai/status", response_model=AIStatusResponse)
def get_ai_status():
    agent = pricing_service.agent
    return AIStatusResponse(
        model_loaded=pricing_service.is_model_loaded,
        policy_type="RL_Q_LEARNING" if pricing_service.is_model_loaded else "FIXED_RULE_FALLBACK",
        policy_version=agent.policy_version,
        state_count=len(agent.q_table),
        allowed_actions=[a * 100 for a in RetailExpiryEnv.ACTIONS],
        model_path=settings.RL_MODEL_PATH,
        last_trained=agent.last_trained
    )

def _train_worker(req: TrainRequest):
    global training_lock
    try:
        env = RetailExpiryEnv(seed=req.seed)
        agent = QLearningAgent(
            learning_rate=req.learning_rate,
            discount_factor=req.discount_factor,
            epsilon=req.epsilon,
            epsilon_decay=req.epsilon_decay,
            seed=req.seed
        )

        rewards_history = []
        for ep in range(req.episodes):
            state = env.reset(stock=int(env.rng.integers(15, 45)), days=int(env.rng.integers(3, 10)))
            total_ep_reward = 0.0
            done = False
            while not done:
                action = agent.choose_action(state, explore=True)
                next_state, reward, done, _ = env.step(action)
                agent.update(state, action, reward, next_state, done)
                total_ep_reward += reward
                state = next_state
            agent.decay_epsilon()
            rewards_history.append(round(total_ep_reward, 2))

        summary = {
            "episodes": req.episodes,
            "final_epsilon": round(agent.epsilon, 4),
            "states_learned": len(agent.q_table),
            "avg_reward_last_50": round(float(sum(rewards_history[-50:]) / 50.0), 2) if len(rewards_history) >= 50 else 0.0,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        agent.save_policy(settings.RL_MODEL_PATH, summary)
        pricing_service.load_model()
        pricing_service.agent.last_trained = summary["completed_at"]
    finally:
        training_lock = False

@api_router.post("/ai/train")
def train_rl_policy(req: TrainRequest, background_tasks: BackgroundTasks):
    global training_lock
    if training_lock:
        raise HTTPException(status_code=409, detail="A training run is already in progress.")
    training_lock = True
    background_tasks.add_task(_train_worker, req)
    return {
        "status": "training_started",
        "message": f"Training job with {req.episodes} episodes queued in background.",
        "config": req.model_dump()
    }

@api_router.get("/ai/simulation-comparison", response_model=SimulationComparisonResponse)
def compare_simulation(episodes: int = 100, seed: int = 42):
    # Ensure policy exists or train in-memory if needed
    rl_agent = pricing_service.agent if pricing_service.is_model_loaded else None
    
    rl_res = run_policy_simulation(policy_type="RL", rl_agent=rl_agent, num_episodes=episodes, seed=seed)
    baseline_res = run_policy_simulation(policy_type="BASELINE", num_episodes=episodes, seed=seed)
    
    profit_diff = round(rl_res["total_profit"] - baseline_res["total_profit"], 2)
    wastage_diff = baseline_res["total_wastage_units"] - rl_res["total_wastage_units"]
    
    verdict = (
        f"RL agent achieved ${rl_res['total_profit']:.2f} total gross profit vs ${baseline_res['total_profit']:.2f} for fixed baseline. "
        f"Wastage prevented: {wastage_diff} units over {episodes} episodes."
    )

    return SimulationComparisonResponse(
        simulation_episodes=episodes,
        comparison_seed=seed,
        scenarios_evaluated=episodes * 7,
        rl_agent=rl_res,
        baseline_rule=baseline_res,
        summary_verdict=verdict
    )
