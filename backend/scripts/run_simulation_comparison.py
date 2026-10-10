import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rl.agent import QLearningAgent
from app.rl.baseline import run_policy_simulation
from app.core.config import settings

def main():
    print("=" * 65)
    print("  EXPERIMENT: RL Agent vs Fixed-Rule Baseline Evaluation")
    print("=" * 65)
    print("Note: Results are generated under synthetic retail simulation assumptions.")
    print("Demand obeys stochastic Poisson footfall and price-elasticity curve.\n")
    
    agent = QLearningAgent()
    if os.path.exists(settings.RL_MODEL_PATH):
        agent.load_policy(settings.RL_MODEL_PATH)
        print(f"[+] Loaded trained policy ({len(agent.q_table)} states).")
    else:
        print("[!] Policy file not found. Running baseline comparison only.")
        return

    episodes = 200
    seed = 123
    print(f"[*] Running {episodes} comparative evaluation episodes (Seed: {seed})...\n")

    rl_results = run_policy_simulation(policy_type="RL", rl_agent=agent, num_episodes=episodes, seed=seed)
    baseline_results = run_policy_simulation(policy_type="BASELINE", num_episodes=episodes, seed=seed)

    print(f"{'Metric':<25} | {'Fixed-Rule Baseline':<18} | {'RL Agent (Q-Learning)':<20}")
    print("-" * 68)
    print(f"{'Total Revenue':<25} | ${baseline_results['total_revenue']:<17.2f} | ${rl_results['total_revenue']:<19.2f}")
    print(f"{'Total Gross Profit':<25} | ${baseline_results['total_profit']:<17.2f} | ${rl_results['total_profit']:<19.2f}")
    print(f"{'Units Sold':<25} | {baseline_results['total_units_sold']:<18} | {rl_results['total_units_sold']:<20}")
    print(f"{'Wastage Units (Expired)':<25} | {baseline_results['total_wastage_units']:<18} | {rl_results['total_wastage_units']:<20}")
    print(f"{'Wastage Cost':<25} | ${baseline_results['total_wastage_cost']:<17.2f} | ${rl_results['total_wastage_cost']:<19.2f}")
    print(f"{'Average Discount %':<25} | {baseline_results['avg_discount_pct']:<17.1f}% | {rl_results['avg_discount_pct']:<19.1f}%")
    print(f"{'Wastage Rate %':<25} | {baseline_results['wastage_rate_pct']:<17.2f}% | {rl_results['wastage_rate_pct']:<19.2f}%")
    print("-" * 68)

    profit_diff = rl_results['total_profit'] - baseline_results['total_profit']
    wastage_avoided = baseline_results['total_wastage_units'] - rl_results['total_wastage_units']
    print(f"\n[Verdict] Profit Difference: ${profit_diff:+.2f} | Waste Reduction: {wastage_avoided:+d} units.")
    print("=" * 65)

if __name__ == "__main__":
    main()
