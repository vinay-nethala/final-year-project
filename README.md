# AI-Based Expiry-Aware Dynamic Discount System

> **Subtitle:** *From Rule-Based to Reinforcement-Learned: Adaptive Discount Policy Design for Retail Inventory Management*  
> **Academic Level:** BTech Final-Year Computer Science & Engineering Project

---

## 📌 Project Overview
In modern grocery retail, perishables approaching expiration are either sold at fixed prices until disposal or subjected to ad-hoc, manual end-of-day markdowns. This project implements a full-stack supermarket inventory management and Point-of-Sale (POS) simulator powered by a **Tabular Q-Learning Reinforcement Learning (RL) agent**.

The system dynamically determines candidate discount tiers (`0%`, `15%`, `30%`, `50%`, `75%`) conditioned on **remaining shelf life**, **current stock level**, and **stochastic footfall demand**, while enforcing strict business constraints such as **cost-price floors**.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (ORM), Pydantic v2, Uvicorn, SQLite (portable to PostgreSQL).
- **AI / RL Engine:** NumPy, Tabular Q-Learning MDP, custom retail environment simulation, transparent JSON policy persistence.
- **Frontend:** React 19, TypeScript, Vite, responsive Admin Dashboard & POS simulator.
- **Testing:** Pytest backend suite.

---

## 🚀 Quickstart Guide (Windows PowerShell)

### Step 1: Open PowerShell in Project Root
```powershell
cd "c:\Users\Lenovo\OneDrive\Documents\final year project"
```

### Step 2: Set Up Backend
```powershell
cd backend
python -m pip install -r requirements.txt
```

### Step 3: Train RL Agent & Seed Realistic Data
```powershell
# 1. Train the Q-learning agent (generates trained_policy.json)
python scripts/train_rl_agent.py

# 2. Run simulation comparison against fixed heuristic baseline
python scripts/run_simulation_comparison.py

# 3. Seed demo supermarket products, batches, and transactions
python scripts/seed_demo_data.py
```

### Step 4: Run Backend Unit Tests
```powershell
python -m pytest tests -v
```

### Step 5: Start Backend Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend Health Check:** `http://127.0.0.1:8000/api/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

---

### Step 6: Start Frontend (In a New PowerShell Terminal)
```powershell
cd "c:\Users\Lenovo\OneDrive\Documents\final year project\frontend"
npm run dev
```
- **Frontend Dashboard URL:** `http://localhost:5173`

---

## 📊 RL Agent vs Fixed-Rule Baseline Benchmark

Evaluated over 200 identical simulation scenarios under stochastic Poisson footfall and price elasticity:

| Metric | Fixed-Rule Baseline | RL Agent (Q-Learning) | Impact |
| :--- | :--- | :--- | :--- |
| **Total Realized Gross Profit** | $10,030.50 | **$14,454.00** | **+$4,423.50 (+44.1%)** |
| **Total Revenue** | $40,875.50 | **$46,024.00** | **+$5,148.50** |
| **Units Sold** | 6,169 units | **6,314 units** | **+145 units** |
| **Wastage (Expired Unsold)** | 1,831 units | **1,686 units** | **-145 units saved** |
| **Wastage Rate %** | 22.89% | **21.07%** | **-1.82% reduction** |
| **Average Discount Granted** | 26.2% | **23.9%** | **2.3% lower discount** |

*Key Takeaway: The RL agent learns not to over-discount unnecessarily on items with ample shelf-life, preserving margin while aggressively discounting critical batches just in time to clear stock before expiry.*

---

## 📁 Repository Structure
```
final year project/
├── backend/
│   ├── app/
│   │   ├── api/endpoints.py       # FastAPI REST endpoints
│   │   ├── core/config.py         # App configuration & CORS
│   │   ├── core/expiry.py         # Days-to-expiry calculation & urgency bands
│   │   ├── db/session.py          # SQLAlchemy session & Base
│   │   ├── models/entities.py     # Product, Batch, Sale, SaleItem, PricingLog
│   │   ├── schemas/schemas.py     # Pydantic request/response schemas
│   │   ├── services/pricing_service.py   # Pricing orchestrator & floor enforcer
│   │   ├── services/checkout_service.py  # Atomic checkout transaction handler
│   │   ├── services/analytics_service.py # Aggregate analytics calculations
│   │   └── rl/
│   │       ├── environment.py     # Retail simulation MDP environment
│   │       ├── agent.py           # Tabular Q-learning agent & updates
│   │       ├── baseline.py        # Fixed-rule baseline & comparator
│   │       └── trained_policy.json # Serialized Q-table policy
│   ├── scripts/
│   │   ├── train_rl_agent.py      # Offline policy training script
│   │   ├── run_simulation_comparison.py # Comparative simulation benchmark
│   │   └── seed_demo_data.py      # Supermarket seed data
│   ├── tests/
│   │   └── test_discount_system.py # Pytest test suite (6/6 passing)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Main responsive React admin & POS interface
│   │   ├── api.ts                 # Type-safe API client
│   │   ├── types.ts               # Shared TypeScript data models
│   │   └── index.css              # Dashboard stylesheet
│   └── package.json
└── docs/
    ├── architecture.md            # System architecture, ER diagram, sequence flow
    ├── rl-methodology.md          # Mathematical MDP & Q-learning formulation
    ├── api-guide.md               # Complete REST API reference
    └── viva-questions.md          # BTech viva exam questions & answers
```

---

## 🎓 Academic Presentation Walkthrough (3-Minute Script)
1. **Introduction (30s):** Introduce the problem of supermarket perishable food waste and show the Overview Dashboard with real revenue and wastage figures.
2. **Expiry Radar (45s):** Navigate to the Expiry Radar tab, demonstrating the color-coded urgency bands (Red: 0–2 days, Yellow: 3–5 days, Green: >5 days).
3. **POS Simulator (45s):** Add a critical batch to the POS cart; show the live dynamic discount recommendation generated by the RL agent and complete checkout to observe stock deduction.
4. **RL Policy Center & Benchmark (60s):** Open the RL Policy tab; show the 36-state Q-table parameters, trigger retraining, and present the benchmark table comparing RL vs the Fixed-Rule baseline.
