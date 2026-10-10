# Final Viva Questions & Model Answers

### Q1: What is the core problem this project solves?
**Answer:** Traditional supermarkets either sell perishables at full price until they expire or rely on arbitrary, manual end-of-day markdowns by employees. This leads to substantial food wastage and inventory write-offs. Our system uses a Reinforcement Learning agent trained on perishable retail dynamics to recommend optimal, timely discounts based on days remaining until expiry, current batch stock, and demand footfall, maximizing realized gross profit while preventing spoilage.

---

### Q2: Why did you choose Tabular Q-Learning instead of Deep Q-Networks (DQN)?
**Answer:** 
1. **Explainability & Transparency:** In retail auditing, every pricing decision must be interpretable. A tabular Q-matrix clearly maps state tuples $(d, q, \omega)$ directly to expected Q-values for each discount tier, making decisions auditable by store managers.
2. **Computational Efficiency:** Tabular Q-learning trains in seconds without GPU requirements, produces zero inference latency, and saves into a lightweight, portable JSON policy file (~4 KB) ideal for edge POS registers.
3. **Appropriate State Dimensionality:** By thoughtfully binning days until expiry (4 bins), stock level (3 bins), and demand scenarios (3 bins), the state space is compact (36 states), eliminating the risk of deep neural network instability or catastrophic forgetting.

---

### Q3: How is the state space defined in your MDP?
**Answer:** The state is represented as $s = (\text{days\_bin}, \text{stock\_bin}, \text{demand\_scenario})$:
- **Days Bin:** $0$ ($\le 1$ day), $1$ ($2-3$ days), $2$ ($4-6$ days), $3$ ($>6$ days).
- **Stock Bin:** $0$ ($1-10$ units), $1$ ($11-30$ units), $2$ ($>30$ units).
- **Demand Scenario:** $0$ (Slow footfall), $1$ (Regular), $2$ (Peak footfall).

---

### Q4: How does the reward function prevent the agent from over-discounting or destroying inventory?
**Answer:** The reward is defined as:
$$R_t = \text{Gross Profit}_t - \text{Wastage Penalty}_t$$
- **Gross Profit** is $(\text{Revenue} - \text{COGS})$, rewarding sales above cost price.
- **Wastage Penalty** charges the store $1.1 \times \text{Cost Price}$ for each unit that expires unsold ($d < 0$).
If the agent discounts too deeply too early (e.g., $75\%$ on fresh items), it sacrifices gross profit. If it discounts too little, unsold items perish, incurring heavy wastage penalties. The agent naturally converges to dynamic markdowns that clear batches just before expiration.

---

### Q5: How do you enforce business constraints such as price floors?
**Answer:** The system implements a strict server-side **cost-price floor**. Regardless of the RL agent's candidate action, if $P_{\text{base}} \times (1 - \text{discount}) < P_{\text{cost}}$, the pricing engine clamps the discount to ensure the item is never sold below cost, except when explicit same-day emergency clearance ($d = 0$) is authorized.

---

### Q6: How does the checkout process prevent overselling and maintain data integrity?
**Answer:** The checkout endpoint executes within an atomic database transaction. The requested batch is queried, validated for active status, non-expired date, and sufficient stock. If all line items pass validation, inventory is decremented, the sale record is created, and the transaction is committed. If any constraint fails, the entire transaction is rolled back with zero inventory alteration.

---

### Q7: What are the primary limitations and future work?
**Answer:**
- **Current Limitations:** Tabular discretization groups stock and days into bins; demand is modeled via stochastic Poisson footfall rather than proprietary scanner telemetry.
- **Future Work:** Integration of historical time-series demand forecasting (Prophet/LSTM), batch-level GS1-128 barcode scanning hardware integration, and multi-store federated policy training.
