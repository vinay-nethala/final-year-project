import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.entities import Batch, Sale, SaleItem, PricingDecisionLog, BatchStatus
from app.schemas.schemas import CheckoutRequest
from app.services.pricing_service import pricing_service

class CheckoutService:
    """
    Handles atomic POS checkout transactions:
    1. Validates cart items, quantities, expiry status, and active product states.
    2. Calculates official dynamic discount and unit prices via PricingService (cannot be bypassed by frontend).
    3. Decrements inventory in SQLite/DB within a transaction.
    4. Records the Sale, individual SaleItem lines, and feedback PricingDecisionLog entries.
    5. Commits atomically or rolls back on any error.
    """

    @staticmethod
    def process_checkout(db: Session, request: CheckoutRequest) -> Sale:
        if not request.items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        # Consolidate items if multiple of same batch submitted
        batch_requests: Dict[int, int] = {}
        for item in request.items:
            batch_requests[item.batch_id] = batch_requests.get(item.batch_id, 0) + item.quantity

        try:
            total_sale_amount = 0.0
            total_sale_cost = 0.0
            total_sale_profit = 0.0
            total_sale_units = 0
            sale_items_to_create = []
            pricing_logs_to_create = []

            # Process each requested batch
            for batch_id, qty_requested in batch_requests.items():
                batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
                if not batch:
                    raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

                if not batch.product.is_active:
                    raise HTTPException(status_code=400, detail=f"Product '{batch.product.name}' is inactive and cannot be sold.")

                if batch.status != BatchStatus.ACTIVE:
                    raise HTTPException(status_code=400, detail=f"Batch {batch.batch_code} is {batch.status.value} and cannot be sold.")

                if batch.days_until_expiry < 0:
                    batch.status = BatchStatus.EXPIRED
                    raise HTTPException(status_code=400, detail=f"Batch {batch.batch_code} has expired on {batch.expiry_date} and cannot be sold.")

                if batch.current_qty < qty_requested:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient inventory for {batch.product.name} (Batch {batch.batch_code}). Available: {batch.current_qty}, Requested: {qty_requested}."
                    )

                # Compute dynamic price
                pricing = pricing_service.recommend_discount(batch)
                discount_pct = pricing["recommended_discount_pct"]
                final_unit_price = pricing["final_price"]
                base_unit_price = batch.product.base_price
                unit_cost = batch.product.cost_price

                line_total = round(qty_requested * final_unit_price, 2)
                line_cost = round(qty_requested * unit_cost, 2)
                line_profit = round(line_total - line_cost, 2)

                # Deduct inventory
                batch.current_qty -= qty_requested
                if batch.current_qty == 0:
                    batch.status = BatchStatus.SOLD_OUT
                batch.current_discount_pct = discount_pct

                # Prepare SaleItem
                sale_item = SaleItem(
                    batch_id=batch.batch_id,
                    product_name=batch.product.name,
                    quantity=qty_requested,
                    base_unit_price=base_unit_price,
                    discount_pct=discount_pct,
                    final_unit_price=final_unit_price,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    line_profit=line_profit
                )
                sale_items_to_create.append(sale_item)

                # Prepare Pricing Decision Feedback Log
                log_entry = PricingDecisionLog(
                    batch_id=batch.batch_id,
                    days_to_expiry=batch.days_until_expiry,
                    stock_level=batch.current_qty,
                    demand_scenario="CHECKOUT_EVENT",
                    state_key=pricing["state_key"],
                    recommended_discount_pct=discount_pct,
                    base_price=base_unit_price,
                    cost_price=unit_cost,
                    final_price=final_unit_price,
                    policy_type=pricing["policy_type"],
                    policy_version=pricing["policy_version"],
                    explanation=f"Sold {qty_requested} units at {discount_pct}% discount: {pricing['explanation']}"
                )
                pricing_logs_to_create.append(log_entry)

                total_sale_amount += line_total
                total_sale_cost += line_cost
                total_sale_profit += line_profit
                total_sale_units += qty_requested

            # Create parent Sale record
            sale_code = f"TXN-{uuid.uuid4().hex[:8].upper()}"
            sale = Sale(
                sale_code=sale_code,
                total_amount=round(total_sale_amount, 2),
                total_cost=round(total_sale_cost, 2),
                total_profit=round(total_sale_profit, 2),
                total_items=total_sale_units,
                payment_method=request.payment_method
            )
            db.add(sale)
            db.flush() # Populate sale.sale_id

            # Associate sale_id with items
            for item in sale_items_to_create:
                item.sale_id = sale.sale_id
                db.add(item)

            for log in pricing_logs_to_create:
                db.add(log)

            # Commit atomic transaction
            db.commit()
            db.refresh(sale)
            return sale

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Checkout transaction failed: {str(e)}")

checkout_service = CheckoutService()
