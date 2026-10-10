import numpy as np
from typing import Tuple, Dict, Any

class RetailExpiryEnv:
    """
    Retail Simulation Environment for Perishable Inventory Discounting.
    
    State Representation:
        - days_bin: 0 (<=1 day), 1 (2-3 days), 2 (4-6 days), 3 (>6 days)
        - stock_bin: 0 (Low: 1-10), 1 (Medium: 11-30), 2 (High: >30)
        - demand_scenario: 0 (Slow day), 1 (Regular day), 2 (Peak day)
        
    Discrete Actions:
        0: 0% discount
        1: 15% discount
        2: 30% discount
        3: 50% discount
        4: 75% discount
        
    Economics:
        - Base Price: default $10.00
        - Unit Cost Price: default $5.00 (Price floor: discount > 50% sells below cost unless authorized)
        - Wastage Penalty: Loss of unit cost plus handling penalty for each unsold unit when days reach -1.
    """

    ACTIONS = [0.0, 0.15, 0.30, 0.50, 0.75]

    def __init__(
        self,
        base_price: float = 10.0,
        cost_price: float = 5.0,
        initial_stock: int = 30,
        shelf_life_days: int = 7,
        seed: int = 42
    ):
        self.base_price = base_price
        self.cost_price = cost_price
        self.initial_stock = initial_stock
        self.shelf_life_days = shelf_life_days
        self.rng = np.random.default_rng(seed)
        
        # State variables
        self.current_stock = initial_stock
        self.days_remaining = shelf_life_days
        self.demand_scenario = 1  # 0: Slow, 1: Regular, 2: Peak

    @staticmethod
    def get_days_bin(days: int) -> int:
        if days <= 1:
            return 0
        elif days <= 3:
            return 1
        elif days <= 6:
            return 2
        else:
            return 3

    @staticmethod
    def get_stock_bin(stock: int) -> int:
        if stock <= 10:
            return 0
        elif stock <= 30:
            return 1
        else:
            return 2

    def get_state(self) -> Tuple[int, int, int]:
        d_bin = self.get_days_bin(self.days_remaining)
        s_bin = self.get_stock_bin(self.current_stock)
        return (d_bin, s_bin, self.demand_scenario)

    @classmethod
    def state_to_key(cls, state: Tuple[int, int, int]) -> str:
        return f"{state[0]}_{state[1]}_{state[2]}"

    def reset(self, stock: int = None, days: int = None) -> Tuple[int, int, int]:
        self.current_stock = stock if stock is not None else self.initial_stock
        self.days_remaining = days if days is not None else self.shelf_life_days
        self.demand_scenario = int(self.rng.choice([0, 1, 2], p=[0.25, 0.50, 0.25]))
        return self.get_state()

    def simulate_demand(self, discount_pct: float) -> int:
        """
        Simulate stochastic customer demand responding to price discount and remaining shelf-life.
        Baseline customer footfall scaled by demand scenario:
          - Slow: ~4 customers
          - Regular: ~8 customers
          - Peak: ~14 customers
        Purchase probability increases with higher discount, but drops slightly if shelf life is critical (1 day).
        """
        scenario_bases = {0: 4, 1: 8, 2: 14}
        base_customers = scenario_bases.get(self.demand_scenario, 8)
        footfall = self.rng.poisson(base_customers)

        # Baseline purchase probability at 0% discount
        # Shelf life perception penalty: consumers are wary of items with 0-1 days left unless heavily discounted
        shelf_factor = 0.8 if self.days_remaining <= 1 else 1.0
        
        # Price sensitivity curve:
        # 0% discount -> 25% buy prob
        # 15% discount -> 42% buy prob
        # 30% discount -> 65% buy prob
        # 50% discount -> 85% buy prob
        # 75% discount -> 95% buy prob
        discount_boost = discount_pct * 1.05
        buy_prob = min(0.96, (0.25 + discount_boost) * shelf_factor)
        
        units_sold = int(self.rng.binomial(n=max(0, footfall), p=buy_prob))
        return min(units_sold, self.current_stock)

    def step(self, action_idx: int) -> Tuple[Tuple[int, int, int], float, bool, Dict[str, Any]]:
        discount_pct = self.ACTIONS[action_idx]
        discounted_price = round(self.base_price * (1.0 - discount_pct), 2)
        
        # Simulate units sold today
        units_sold = self.simulate_demand(discount_pct)
        self.current_stock -= units_sold
        
        # Daily financial metrics
        daily_revenue = round(units_sold * discounted_price, 2)
        daily_cogs = round(units_sold * self.cost_price, 2)
        daily_gross_profit = round(daily_revenue - daily_cogs, 2)
        
        # Advance time by 1 day
        self.days_remaining -= 1
        
        # Check termination: stock depleted OR days exhausted (past expiry)
        terminated = (self.current_stock <= 0) or (self.days_remaining < 0)
        
        # Calculate reward:
        # Realized profit minus wastage penalty if items expire unsold
        wastage_cost = 0.0
        if terminated and self.current_stock > 0 and self.days_remaining < 0:
            # Expired unsold! Penalty is cost price of wasted items + disposal surcharge
            wastage_cost = round(self.current_stock * (self.cost_price * 1.1), 2)
            
        reward = daily_gross_profit - wastage_cost
        
        # Update demand scenario for next day
        if not terminated:
            self.demand_scenario = int(self.rng.choice([0, 1, 2], p=[0.25, 0.50, 0.25]))
            
        info = {
            "units_sold": units_sold,
            "revenue": daily_revenue,
            "gross_profit": daily_gross_profit,
            "wastage_cost": wastage_cost,
            "remaining_stock": self.current_stock,
            "days_remaining": self.days_remaining,
            "discount_pct": discount_pct,
            "price": discounted_price
        }
        
        return self.get_state(), reward, terminated, info
