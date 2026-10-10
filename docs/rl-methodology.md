# Reinforcement Learning Methodology: Tabular Q-Learning for Perishable Retail Markdown

## 1. Mathematical Formulation

Dynamic pricing of perishable inventory is formulated as a discrete-time **Markov Decision Process (MDP)**: $\langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$.

### State Space $\mathcal{S}$
To keep tabular Q-learning computationally tractable while retaining essential market context, the state vector is discretized into three intuitive dimensions:
$$s = (d, q, \omega)$$

1. **Days Remaining Until Expiry ($d \in \{0, 1, 2, 3\}$)**:
   - `0`: Critical window ($d \le 1$ day remaining)
   - `1`: Warning window ($2 \le d \le 3$ days remaining)
   - `2`: Approaching window ($4 \le d \le 6$ days remaining)
   - `3`: Fresh window ($d > 6$ days remaining)

2. **Current Stock Level ($q \in \{0, 1, 2\}$)**:
   - `0`: Low stock ($1 \le q \le 10$ units)
   - `1`: Medium stock ($11 \le q \le 30$ units)
   - `2`: High stock ($q > 30$ units)

3. **Customer Demand Footfall Scenario ($\omega \in \{0, 1, 2\}$)**:
   - `0`: Slow footfall day ($\sim 4$ shoppers)
   - `1`: Regular footfall day ($\sim 8$ shoppers)
   - `2`: Peak weekend/promotion footfall day ($\sim 14$ shoppers)

Total state combinations: $4 \times 3 \times 3 = 36$ discrete states.

---

### Action Space $\mathcal{A}$
The agent selects from discrete percentage markdowns:
$$\mathcal{A} = \{0\%, 15\%, 30\%, 50\%, 75\%\}$$

- **Business Price Floor Constraint**:
  $$P_{\text{final}} = P_{\text{base}} \times (1 - a)$$
  The system strictly enforces $P_{\text{final}} \ge P_{\text{cost}}$ unless same-day emergency clearance ($d = 0$) is authorized.

---

### Reward Function $\mathcal{R}(s, a, s')$
The objective balances realized revenue against Cost of Goods Sold (COGS) and wastage penalties:
$$R_t = \text{Gross Profit}_t - \text{Wastage Penalty}_t$$
Where:
- $\text{Gross Profit}_t = \sum (\text{Units Sold} \times (P_{\text{final}} - P_{\text{cost}}))$
- $\text{Wastage Penalty}_t = \text{Remaining Unsold Stock} \times (1.1 \times P_{\text{cost}})$ (incurred if $d < 0$).

---

## 2. Q-Learning Update Rule
The agent learns the expected cumulative discounted future reward $Q(s, a)$ via temporal difference updates:
$$Q(s_t, a_t) \leftarrow Q(s_t, a_t) + \alpha \left[ R_{t+1} + \gamma \max_{a'} Q(s_{t+1}, a') - Q(s_t, a_t) \right]$$

- **Learning Rate ($\alpha$)**: $0.1$
- **Discount Factor ($\gamma$)**: $0.95$
- **Exploration ($\epsilon$)**: $\epsilon$-greedy strategy initialized at $0.30$, decaying per episode by factor $0.998$ down to a minimum floor of $0.02$.

---

## 3. Policy Serialization & Deterministic Inference
The trained Q-matrix is stored as a portable, transparent JSON file (`backend/app/rl/trained_policy.json`). 
At runtime, greedy inference selects:
$$a^* = \arg\max_{a \in \mathcal{A}} Q(s, a)$$
If the policy file is uninitialized or missing, a safe heuristic fallback markdown curve takes over without service disruption.
