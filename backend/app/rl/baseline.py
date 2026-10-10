import numpy as np
from typing import Dict, Any, Tuple
from app.rl.environment import RetailExpiryEnv
from app.rl.agent import QLearningAgent

class FixedRuleBaseline:
    """
    Fixed-rule heuristic pricing baseline for comparison with RL.
    Standard retail clearance markdown rules:
      - > 5 days until expiry: 0% discount
      - 4 to 5 days: 15% discount
      - 2 to 3 days: 30% discount
      - 1 day: 50% discount
      - 0 days (expiry day): 75% discount
    """
    @staticmethod
    def get_discount(days_remaining: int) -> float:
        if days_remaining > 5:
            return 0.0
        elif days_remaining >= 4:
            return 0.15
        elif days_remaining >= 2:
            return 0.30
        elif days_remaining == 1:
            return 0.50
        else:
            return 0.75

    @classmethod
    def get_action_index(cls, days_remaining: int) -> int:
        discount = cls.get_discount(days_remaining)
        try:
            return RetailExpiryEnv.ACTIONS.index(discount)
        except ValueError:
            return 0

def run_policy_simulation(
    policy_type: str,
    rl_agent: QLearningAgent = None,
    num_episodes: int = 100,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Evaluates either the RL policy or the Fixed-Rule baseline across
    identical simulation scenarios and random seeds.
    """
    env = RetailExpiryEnv(seed=seed)
    total_revenue = 0.0
    total_profit = 0.0
    total_units_sold = 0
    total_wastage_units = 0
    total_wastage_cost = 0.0
    total_discounts_applied = []
    
    for ep in range(num_episodes):
        # Reset with consistent batch sizes
        starting_stock = 30 + (ep % 5) * 5
        starting_days = 7
        state = env.reset(stock=starting_stock, days=starting_days)
        done = False
        
        while not done:
            days_left = env.days_remaining
            if policy_type == "RL" and rl_agent is not None:
                action_idx = rl_agent.choose_action(state, explore=False)
            else:
                action_idx = FixedRuleBaseline.get_action_index(days_left)
                
            discount = RetailExpiryEnv.ACTIONS[action_idx]
            total_discounts_applied.append(discount)
            
            next_state, reward, done, info = env.step(action_idx)
            total_revenue += info["revenue"]
            total_profit += info["gross_profit"]
            total_units_sold += info["units_sold"]
            
            if done and info["remaining_stock"] > 0 and info["days_remaining"] < 0:
                total_wastage_units += info["remaining_stock"]
                total_wastage_cost += info["wastage_cost"]
                
            state = next_state

    avg_discount = float(np.mean(total_discounts_applied)) if total_discounts_applied else 0.0
    
    return {
        "policy": policy_type,
        "episodes": num_episodes,
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_units_sold": total_units_sold,
        "total_wastage_units": total_wastage_units,
        "total_wastage_cost": round(total_wastage_cost, 2),
        "avg_discount_pct": round(avg_discount * 100, 1),
        "wastage_rate_pct": round((total_wastage_units / max(1, (total_units_sold + total_wastage_units))) * 100, 2)
    }
