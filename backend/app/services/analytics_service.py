from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import Sale, SaleItem, Batch, Product, BatchStatus
from app.schemas.schemas import AnalyticsSummary, TimeseriesPoint, CategorySales, DiscountDistributionItem

class AnalyticsService:
    @staticmethod
    def get_summary(db: Session) -> AnalyticsSummary:
        # Sales aggregates
        sales = db.query(Sale).all()
        sales_count = len(sales)
        revenue = round(sum(s.total_amount for s in sales), 2)
        gross_profit = round(sum(s.total_profit for s in sales), 2)
        units_sold = sum(s.total_items for s in sales)

        # Discount given calculation: sum of (base_unit_price - final_unit_price) * quantity
        sale_items = db.query(SaleItem).all()
        total_discount_given = round(
            sum((item.base_unit_price - item.final_unit_price) * item.quantity for item in sale_items), 2
        )

        # Inventory aggregates
        batches = db.query(Batch).join(Product).filter(Product.is_active == True).all()
        current_inventory_units = sum(b.current_qty for b in batches if b.status == BatchStatus.ACTIVE)
        
        # Expiring soon: 0 to 5 days remaining
        expiring_soon_units = sum(
            b.current_qty for b in batches 
            if b.status == BatchStatus.ACTIVE and 0 <= b.days_until_expiry <= 5
        )

        # Expired inventory units and estimated wastage cost
        expired_batches = [b for b in batches if b.days_until_expiry < 0 or b.status == BatchStatus.EXPIRED]
        expired_units = sum(b.current_qty for b in expired_batches)
        estimated_wastage_cost = round(
            sum(b.current_qty * b.product.cost_price for b in expired_batches), 2
        )

        return AnalyticsSummary(
            sales_count=sales_count,
            units_sold=units_sold,
            revenue=revenue,
            gross_profit=gross_profit,
            total_discount_given=total_discount_given,
            current_inventory_units=current_inventory_units,
            expiring_soon_units=expiring_soon_units,
            expired_units=expired_units,
            estimated_wastage_cost=estimated_wastage_cost
        )

    @staticmethod
    def get_timeseries(db: Session) -> List[TimeseriesPoint]:
        # Group sales by sold_at calendar day
        sales = db.query(Sale).order_by(Sale.sold_at.asc()).all()
        daily_buckets: Dict[str, Dict[str, Any]] = {}

        for s in sales:
            day_str = s.sold_at.strftime("%Y-%m-%d")
            if day_str not in daily_buckets:
                daily_buckets[day_str] = {"revenue": 0.0, "profit": 0.0, "units": 0}
            daily_buckets[day_str]["revenue"] += s.total_amount
            daily_buckets[day_str]["profit"] += s.total_profit
            daily_buckets[day_str]["units"] += s.total_items

        result = []
        for day, data in daily_buckets.items():
            result.append(TimeseriesPoint(
                date=day,
                revenue=round(data["revenue"], 2),
                profit=round(data["profit"], 2),
                units_sold=data["units"]
            ))
        return result

    @staticmethod
    def get_category_distribution(db: Session) -> List[CategorySales]:
        items = db.query(SaleItem).join(Batch).join(Product).all()
        category_map: Dict[str, Dict[str, Any]] = {}
        for item in items:
            cat = item.batch.product.category if item.batch and item.batch.product else "General"
            if cat not in category_map:
                category_map[cat] = {"revenue": 0.0, "units": 0}
            category_map[cat]["revenue"] += item.line_total
            category_map[cat]["units"] += item.quantity

        return [
            CategorySales(
                category=cat, 
                revenue=round(vals["revenue"], 2), 
                units=vals["units"]
            )
            for cat, vals in category_map.items()
        ]

    @staticmethod
    def get_discount_distribution(db: Session) -> List[DiscountDistributionItem]:
        items = db.query(SaleItem).all()
        buckets: Dict[float, Dict[str, Any]] = {}
        for item in items:
            tier = round(item.discount_pct, 1)
            if tier not in buckets:
                buckets[tier] = {"count": 0, "revenue": 0.0}
            buckets[tier]["count"] += item.quantity
            buckets[tier]["revenue"] += item.line_total

        return [
            DiscountDistributionItem(
                discount_pct=tier,
                count=data["count"],
                revenue=round(data["revenue"], 2)
            )
            for tier, data in sorted(buckets.items())
        ]

analytics_service = AnalyticsService()
