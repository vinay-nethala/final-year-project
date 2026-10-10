import os
import math
from typing import Tuple, Dict, Any
from app.core.config import settings
from app.models.entities import Batch
from app.rl.environment import RetailExpiryEnv
from app.rl.agent import QLearningAgent
from app.rl.baseline import FixedRuleBaseline

class PricingService:
    """
    Orchestrates discount decisions:
    1. Loads trained Q-learning policy if present.
    2. Maps batch attributes (days left, inventory level) into environmental state.
    3. Evaluates business constraints (e.g. price floor so selling price >= cost price).
    4. Provides fallback safe pricing if model file is unavailable.
    """

    def __init__(self):
        self.agent = QLearningAgent()
        self.is_model_loaded = False
        self.load_model()

    def load_model(self) -> bool:
        model_path = settings.RL_MODEL_PATH
        if os.path.exists(model_path):
            self.is_model_loaded = self.agent.load_policy(model_path)
        else:
            self.is_model_loaded = False
        return self.is_model_loaded

    def recommend_discount(self, batch: Batch) -> Dict[str, Any]:
        days_left = batch.days_until_expiry
        stock = batch.current_qty
        base_price = batch.product.base_price
        cost_price = batch.product.cost_price

        # Check if expired or out of stock
        if days_left < 0 or stock <= 0:
            return {
                "recommended_discount_pct": 0.0,
                "final_price": base_price,
                "policy_type": "RESTRICTED",
                "policy_version": "N/A",
                "explanation": "Batch is expired or out of stock. Sale restricted.",
                "state_key": "RESTRICTED"
            }

        # Formulate RL state representation
        d_bin = RetailExpiryEnv.get_days_bin(days_left)
        s_bin = RetailExpiryEnv.get_stock_bin(stock)
        scenario = 1 # Average demand assumption for real-time checkout
        state = (d_bin, s_bin, scenario)
        state_key = RetailExpiryEnv.state_to_key(state)

        if self.is_model_loaded:
            action_idx = self.agent.choose_action(state, explore=False)
            candidate_discount = RetailExpiryEnv.ACTIONS[action_idx]
            policy_type = "RL_Q_LEARNING"
            policy_version = self.agent.policy_version
            explanation = f"RL agent chose {int(candidate_discount*100)}% discount based on state {state_key} (days bin {d_bin}, stock bin {s_bin})."
        else:
            # Safe heuristic fallback
            candidate_discount = FixedRuleBaseline.get_discount(days_left)
            policy_type = "FIXED_RULE_FALLBACK"
            policy_version = "fallback-1.0"
            explanation = f"Heuristic rule chose {int(candidate_discount*100)}% discount (Q-table offline or uninitialized)."

        # Enforce Business Price Floor Constraint:
        # Final price cannot be below cost price unless days_left == 0 (clearance)
        tentative_final_price = round(base_price * (1.0 - candidate_discount), 2)
        if tentative_final_price < cost_price and days_left > 0:
            # Clamp discount so price >= cost_price
            max_allowed_discount = max(0.0, (base_price - cost_price) / base_price)
            # Find highest action in allowed actions <= max_allowed_discount
            valid_actions = [a for a in RetailExpiryEnv.ACTIONS if a <= max_allowed_discount]
            if valid_actions:
                candidate_discount = max(valid_actions)
            else:
                candidate_discount = 0.0
            tentative_final_price = round(base_price * (1.0 - candidate_discount), 2)
            explanation += f" Adjusted to {int(candidate_discount*100)}% to satisfy cost-price floor (${cost_price:.2f})."

        return {
            "recommended_discount_pct": round(candidate_discount * 100, 1),
            "final_price": tentative_final_price,
            "policy_type": policy_type,
            "policy_version": policy_version,
            "explanation": explanation,
            "state_key": state_key
        }

pricing_service = PricingService()
