import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.models.entities import Product, Batch, BatchStatus, Sale
from app.main import app
from app.core.expiry import calculate_days_until_expiry, get_expiry_urgency_band
from app.rl.environment import RetailExpiryEnv
from app.rl.agent import QLearningAgent
from app.services.pricing_service import pricing_service
from app.schemas.schemas import CheckoutRequest, CartItemInput

# Use in-memory SQLite database for test suite isolation
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite with StaticPool so all sessions share the same in-memory DB connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# 1. Days-to-expiry calculation & urgency bands test
def test_expiry_date_calculation():
    today = date.today()
    assert calculate_days_until_expiry(today + timedelta(days=5), today) == 5
    assert calculate_days_until_expiry(today, today) == 0
    assert calculate_days_until_expiry(today - timedelta(days=2), today) == -2

    assert get_expiry_urgency_band(-1) == "EXPIRED"
    assert get_expiry_urgency_band(0) == "CRITICAL"
    assert get_expiry_urgency_band(2) == "CRITICAL"
    assert get_expiry_urgency_band(4) == "WARNING"
    assert get_expiry_urgency_band(7) == "NORMAL"

# 2. Product and batch validation & creation
def test_product_and_batch_creation():
    db = TestingSessionLocal()
    product = Product(name="Greek Yogurt", sku="YGT-001", category="Dairy", base_price=5.0, cost_price=2.5)
    db.add(product)
    db.commit()
    db.refresh(product)

    batch = Batch(
        product_id=product.product_id,
        batch_code="B001",
        initial_qty=20,
        current_qty=20,
        expiry_date=date.today() + timedelta(days=3)
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    assert batch.days_until_expiry == 3
    assert batch.urgency_band == "WARNING"
    assert batch.is_sellable is True
    db.close()

# 3. Stock cannot become negative and expired batch cannot be sold
def test_checkout_validation_and_stock_deduction():
    db = TestingSessionLocal()
    product = Product(name="Milk 1L", sku="MLK-001", category="Dairy", base_price=4.0, cost_price=2.0)
    db.add(product)
    db.commit()

    # Valid batch with stock = 5
    valid_batch = Batch(
        product_id=product.product_id,
        batch_code="B_VALID",
        initial_qty=5,
        current_qty=5,
        expiry_date=date.today() + timedelta(days=2)
    )
    # Expired batch
    expired_batch = Batch(
        product_id=product.product_id,
        batch_code="B_EXP",
        initial_qty=10,
        current_qty=10,
        expiry_date=date.today() - timedelta(days=1),
        status=BatchStatus.EXPIRED
    )
    db.add_all([valid_batch, expired_batch])
    db.commit()

    # Try to purchase more than available stock
    res = client.post("/api/checkout", json={"items": [{"batch_id": valid_batch.batch_id, "quantity": 10}]})
    assert res.status_code == 400
    assert "Insufficient inventory" in res.json()["detail"]

    # Try to purchase from expired batch
    res_exp = client.post("/api/checkout", json={"items": [{"batch_id": expired_batch.batch_id, "quantity": 1}]})
    assert res_exp.status_code == 400

    # Successful checkout
    res_ok = client.post("/api/checkout", json={"items": [{"batch_id": valid_batch.batch_id, "quantity": 3}]})
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["total_items"] == 3
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3

    # Check that stock was deducted exactly once
    db.refresh(valid_batch)
    assert valid_batch.current_qty == 2
    db.close()

# 4. Atomic transaction rollback verification
def test_checkout_atomic_rollback_on_partial_failure():
    db = TestingSessionLocal()
    p = Product(name="Bread", sku="BRD-001", category="Bakery", base_price=3.0, cost_price=1.5)
    db.add(p)
    db.commit()

    b1 = Batch(product_id=p.product_id, batch_code="B1", initial_qty=5, current_qty=5, expiry_date=date.today() + timedelta(days=5))
    b2 = Batch(product_id=p.product_id, batch_code="B2", initial_qty=2, current_qty=2, expiry_date=date.today() + timedelta(days=5))
    db.add_all([b1, b2])
    db.commit()

    # Request 2 from B1 (valid) but 10 from B2 (exceeds stock)
    req = {
        "items": [
            {"batch_id": b1.batch_id, "quantity": 2},
            {"batch_id": b2.batch_id, "quantity": 10}
        ]
    }
    res = client.post("/api/checkout", json=req)
    assert res.status_code == 400

    # Verify B1 stock remains untouched (rolled back)
    db.refresh(b1)
    assert b1.current_qty == 5
    # Verify no Sale was created
    assert db.query(Sale).count() == 0
    db.close()

# 5. Price floor restriction: cannot sell below cost price
def test_price_floor_enforcement():
    db = TestingSessionLocal()
    # High cost price product ($10 base, $9 cost)
    p = Product(name="Caviar", sku="CVR-001", category="Gourmet", base_price=10.0, cost_price=9.0)
    db.add(p)
    db.commit()

    b = Batch(product_id=p.product_id, batch_code="B_CVR", initial_qty=10, current_qty=10, expiry_date=date.today() + timedelta(days=1))
    db.add(b)
    db.commit()

    pricing = pricing_service.recommend_discount(b)
    # Base price $10, cost $9. Even with 1 day remaining, discount cannot drop price below $9.00
    assert pricing["final_price"] >= 9.0
    assert pricing["recommended_discount_pct"] <= 10.0 # Only 0% or <= 10% allowed
    db.close()

# 6. Q-learning agent reproducibility with fixed seed
def test_q_learning_agent_reproducibility():
    agent1 = QLearningAgent(seed=42)
    agent2 = QLearningAgent(seed=42)
    state = (1, 1, 1)

    actions1 = [agent1.choose_action(state, explore=True) for _ in range(20)]
    actions2 = [agent2.choose_action(state, explore=True) for _ in range(20)]
    assert actions1 == actions2
