# API Reference Guide

All API endpoints are hosted with prefix `/api` (default base: `http://127.0.0.1:8000/api`). Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

---

## 1. Health Endpoint
### `GET /api/health`
Checks server readiness and model state.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "service": "AI-Based Expiry-Aware Dynamic Discount System",
  "database": "connected",
  "model_loaded": true,
  "timestamp": "2026-10-10T11:15:00.000000Z"
}
```

---

## 2. Dynamic Pricing Recommendation
### `GET /api/price/{batch_id}`
Computes real-time discount for a specific batch based on days left, stock level, and cost price floor.
- **Response `200 OK`**:
```json
{
  "batch_id": 1,
  "product_id": 1,
  "product_name": "Organic Whole Milk 1L",
  "sku": "MLK-ORG-101",
  "category": "Dairy",
  "days_until_expiry": 1,
  "urgency_band": "CRITICAL",
  "stock_level": 8,
  "base_price": 3.99,
  "cost_price": 2.10,
  "recommended_discount_pct": 30.0,
  "final_unit_price": 2.79,
  "policy_type": "RL_Q_LEARNING",
  "policy_version": "v1.0",
  "explanation": "RL agent chose 30% discount based on state 0_0_1 (days bin 0, stock bin 0).",
  "is_sellable": true
}
```

---

## 3. POS Checkout Simulator
### `POST /api/checkout`
Executes an atomic multi-item POS transaction. Stock is deducted and audited within a database transaction.
- **Request Body**:
```json
{
  "items": [
    {
      "batch_id": 1,
      "quantity": 2
    }
  ],
  "payment_method": "CASH"
}
```
- **Response `200 OK`**:
```json
{
  "sale_id": 4,
  "sale_code": "TXN-8A7B2C1D",
  "total_amount": 5.58,
  "total_cost": 4.20,
  "total_profit": 1.38,
  "total_items": 2,
  "payment_method": "CASH",
  "sold_at": "2026-10-10T11:15:30Z",
  "items": [
    {
      "item_id": 6,
      "batch_id": 1,
      "product_name": "Organic Whole Milk 1L",
      "quantity": 2,
      "base_unit_price": 3.99,
      "discount_pct": 30.0,
      "final_unit_price": 2.79,
      "unit_cost": 2.10,
      "line_total": 5.58,
      "line_profit": 1.38
    }
  ]
}
```

---

## 4. Reinforcement Learning Training & Comparison
### `POST /api/ai/train`
Triggers asynchronous offline training of the tabular Q-learning agent.
- **Request Body**:
```json
{
  "episodes": 3000,
  "learning_rate": 0.1,
  "discount_factor": 0.95,
  "epsilon": 0.3,
  "epsilon_decay": 0.998,
  "seed": 42
}
```

### `GET /api/ai/simulation-comparison`
Evaluates the RL agent against a fixed-rule heuristic over identical simulation episodes and starting inventory.
- **Response `200 OK`**:
```json
{
  "simulation_episodes": 100,
  "comparison_seed": 42,
  "scenarios_evaluated": 700,
  "rl_agent": {
    "policy": "RL",
    "total_revenue": 23012.0,
    "total_profit": 7227.0,
    "total_units_sold": 3157,
    "total_wastage_units": 843,
    "total_wastage_cost": 4636.5,
    "avg_discount_pct": 23.9,
    "wastage_rate_pct": 21.07
  },
  "baseline_rule": {
    "policy": "BASELINE",
    "total_revenue": 20437.75,
    "total_profit": 5015.25,
    "total_units_sold": 3084,
    "total_wastage_units": 916,
    "total_wastage_cost": 5035.25,
    "avg_discount_pct": 26.2,
    "wastage_rate_pct": 22.9
  },
  "summary_verdict": "RL agent achieved $7227.00 total gross profit vs $5015.25 for fixed baseline. Wastage prevented: 73 units over 100 episodes."
}
```
