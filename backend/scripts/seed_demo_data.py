import os
import sys
from datetime import date, timedelta, datetime, timezone
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, Base, engine
from app.models.entities import Product, Batch, Sale, SaleItem, PricingDecisionLog, BatchStatus

def seed():
    print("[*] Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    today = date.today()

    print("[*] Seeding realistic supermarket products...")
    # 8 realistic supermarket products across perishable categories
    products_data = [
        {"name": "Organic Whole Milk 1L", "sku": "MLK-ORG-101", "category": "Dairy", "base_price": 3.99, "cost_price": 2.10},
        {"name": "Greek Artisan Yogurt 500g", "sku": "YGT-GRK-202", "category": "Dairy", "base_price": 4.49, "cost_price": 2.40},
        {"name": "Fresh Sourdough Bread Loaf", "sku": "BRD-SRD-303", "category": "Bakery", "base_price": 4.99, "cost_price": 2.00},
        {"name": "Butter Croissant 4-Pack", "sku": "BAK-CRS-404", "category": "Bakery", "base_price": 5.49, "cost_price": 2.60},
        {"name": "Organic Baby Spinach 250g", "sku": "PRD-SPN-505", "category": "Produce", "base_price": 2.99, "cost_price": 1.20},
        {"name": "Vine-Ripened Cherry Tomatoes 350g", "sku": "PRD-TOM-606", "category": "Produce", "base_price": 3.49, "cost_price": 1.50},
        {"name": "Free-Range Chicken Breast 500g", "sku": "MET-CHK-707", "category": "Meat & Poultry", "base_price": 8.99, "cost_price": 5.20},
        {"name": "Atlantic Salmon Fillet 300g", "sku": "SEA-SAL-808", "category": "Seafood", "base_price": 9.99, "cost_price": 6.00},
    ]

    created_products = []
    for p_info in products_data:
        p = Product(**p_info)
        db.add(p)
        created_products.append(p)
    db.commit()

    print("[*] Seeding multi-batch inventory across urgency bands...")
    # Batches designed specifically with critical (0-2d), warning (3-5d), normal (>5d), and expired (<0d)
    batches_data = [
        # Milk: 1 critical batch (1 day left), 1 normal batch (8 days left)
        {"product_idx": 0, "batch_code": "BCH-MLK-01", "init": 25, "curr": 8, "days": 1, "mfg_days_ago": 6},
        {"product_idx": 0, "batch_code": "BCH-MLK-02", "init": 40, "curr": 40, "days": 8, "mfg_days_ago": 1},

        # Yogurt: 1 warning batch (4 days left)
        {"product_idx": 1, "batch_code": "BCH-YGT-01", "init": 20, "curr": 14, "days": 4, "mfg_days_ago": 10},

        # Sourdough: 1 same-day clearance batch (0 days left), 1 fresh batch (2 days left)
        {"product_idx": 2, "batch_code": "BCH-BRD-CLR", "init": 15, "curr": 4, "days": 0, "mfg_days_ago": 3},
        {"product_idx": 2, "batch_code": "BCH-BRD-NEW", "init": 20, "curr": 18, "days": 2, "mfg_days_ago": 1},

        # Croissants: 1 warning batch (3 days left)
        {"product_idx": 3, "batch_code": "BCH-CRS-01", "init": 18, "curr": 7, "days": 3, "mfg_days_ago": 2},

        # Spinach: 1 critical batch (2 days left), 1 normal batch (6 days left)
        {"product_idx": 4, "batch_code": "BCH-SPN-01", "init": 30, "curr": 12, "days": 2, "mfg_days_ago": 4},
        {"product_idx": 4, "batch_code": "BCH-SPN-02", "init": 35, "curr": 35, "days": 6, "mfg_days_ago": 1},

        # Tomatoes: 1 normal batch (7 days left)
        {"product_idx": 5, "batch_code": "BCH-TOM-01", "init": 25, "curr": 21, "days": 7, "mfg_days_ago": 2},

        # Chicken: 1 critical batch (1 day left)
        {"product_idx": 6, "batch_code": "BCH-CHK-01", "init": 20, "curr": 6, "days": 1, "mfg_days_ago": 4},

        # Salmon: 1 warning batch (4 days left), 1 expired batch for audit/wastage demonstration (-1 days)
        {"product_idx": 7, "batch_code": "BCH-SAL-01", "init": 15, "curr": 9, "days": 4, "mfg_days_ago": 3},
        {"product_idx": 7, "batch_code": "BCH-SAL-EXP", "init": 10, "curr": 3, "days": -1, "mfg_days_ago": 6, "status": BatchStatus.EXPIRED},
    ]

    created_batches = []
    for b_info in batches_data:
        p = created_products[b_info["product_idx"]]
        exp_date = today + timedelta(days=b_info["days"])
        mfg_date = today - timedelta(days=b_info["mfg_days_ago"])
        batch_status = b_info.get("status", BatchStatus.ACTIVE)

        b = Batch(
            product_id=p.product_id,
            batch_code=b_info["batch_code"],
            initial_qty=b_info["init"],
            current_qty=b_info["curr"],
            manufacturing_date=mfg_date,
            expiry_date=exp_date,
            current_discount_pct=0.0,
            status=batch_status
        )
        db.add(b)
        created_batches.append(b)
    db.commit()

    print("[*] Seeding simulated historical sales transactions...")
    # Add a few realistic completed sales over the past 3 days for analytics demonstration
    for days_ago in [3, 2, 1]:
        sale_time = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(1, 8))
        
        # Sale 1
        s = Sale(
            sale_code=f"TXN-DEMO-{days_ago}01",
            total_amount=16.96,
            total_cost=8.80,
            total_profit=8.16,
            total_items=4,
            payment_method="CARD",
            sold_at=sale_time
        )
        db.add(s)
        db.flush()

        item1 = SaleItem(
            sale_id=s.sale_id,
            batch_id=created_batches[0].batch_id, # Milk
            product_name="Organic Whole Milk 1L",
            quantity=2,
            base_unit_price=3.99,
            discount_pct=15.0,
            final_unit_price=3.39,
            unit_cost=2.10,
            line_total=6.78,
            line_profit=2.58
        )
        item2 = SaleItem(
            sale_id=s.sale_id,
            batch_id=created_batches[2].batch_id, # Sourdough
            product_name="Fresh Sourdough Bread Loaf",
            quantity=2,
            base_unit_price=4.99,
            discount_pct=30.0,
            final_unit_price=3.49,
            unit_cost=2.00,
            line_total=6.98,
            line_profit=2.98
        )
        db.add(item1)
        db.add(item2)

    db.commit()
    db.close()
    print("[+] Successfully seeded supermarket products, active batches, and historical transactions!")

if __name__ == "__main__":
    seed()
