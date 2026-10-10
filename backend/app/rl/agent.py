import json
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
from app.rl.environment import RetailExpiryEnv

class QLearningAgent:
    """
    Tabular Q-Learning Agent for Dynamic Expiry Discounting.
    
    Q-learning Update Rule:
        Q(s, a) <- Q(s, a) + alpha * [ r + gamma * max_a' Q(s', a') - Q(s, a) ]
        
    Key Concepts Explained Simply:
    - State: (days_bin, stock_bin, demand_scenario)
    - Action: Choice of discount tier [0%, 15%, 30%, 50%, 75%]
    - Exploration (epsilon): Trying random discounts to discover profitable outcomes.
    - Exploitation: Choosing the discount that yields highest historical cumulative profit.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.2,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.02,
        seed: int = 42
    ):
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.rng = np.random.default_rng(seed)
        
        # Q-table: mapping state_key -> list of Q-values for each action [0..4]
        self.q_table: Dict[str, List[float]] = {}
        self.actions = RetailExpiryEnv.ACTIONS
        self.policy_version = "v1.0"
        self.last_trained: Optional[str] = None

    def get_q_values(self, state_key: str) -> List[float]:
        if state_key not in self.q_table:
            # Optimistic initialization to encourage initial exploration
            self.q_table[state_key] = [0.0] * len(self.actions)
        return self.q_table[state_key]

    def choose_action(self, state: Tuple[int, int, int], explore: bool = True) -> int:
        state_key = RetailExpiryEnv.state_to_key(state)
        q_vals = self.get_q_values(state_key)
        
        # Epsilon-greedy exploration
        if explore and self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, len(self.actions)))
        
        # Exploitation: pick highest Q-value action (break ties randomly)
        max_val = max(q_vals)
        best_indices = [i for i, v in enumerate(q_vals) if v == max_val]
        return int(self.rng.choice(best_indices))

    def update(
        self, 
        state: Tuple[int, int, int], 
        action: int, 
        reward: float, 
        next_state: Tuple[int, int, int], 
        terminated: bool
    ):
        s_key = RetailExpiryEnv.state_to_key(state)
        q_vals = self.get_q_values(s_key)
        current_q = q_vals[action]
        
        if terminated:
            target = reward
        else:
            next_key = RetailExpiryEnv.state_to_key(next_state)
            next_max_q = max(self.get_q_values(next_key))
            target = reward + self.gamma * next_max_q
            
        # Q-learning formula
        self.q_table[s_key][action] = round(current_q + self.alpha * (target - current_q), 4)

    def decay_epsilon(self):
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def save_policy(self, file_path: str, training_summary: Optional[Dict] = None):
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        data = {
            "policy_version": self.policy_version,
            "actions": self.actions,
            "learning_rate": self.alpha,
            "discount_factor": self.gamma,
            "q_table": self.q_table,
            "training_summary": training_summary or {}
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_policy(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.policy_version = data.get("policy_version", "v1.0")
            self.actions = data.get("actions", self.actions)
            self.q_table = data.get("q_table", {})
            return True
        except Exception:
            return False
