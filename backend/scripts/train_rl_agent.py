import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rl.environment import RetailExpiryEnv
from app.rl.agent import QLearningAgent
from app.core.config import settings

def train_agent(
    episodes: int = 3000,
    learning_rate: float = 0.1,
    discount_factor: float = 0.95,
    epsilon: float = 0.3,
    epsilon_decay: float = 0.998,
    seed: int = 42,
    output_path: str = None
):
    print(f"[*] Starting offline Q-learning training ({episodes} episodes, seed={seed})...")
    output_path = output_path or settings.RL_MODEL_PATH
    
    env = RetailExpiryEnv(seed=seed)
    agent = QLearningAgent(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        epsilon_decay=epsilon_decay,
        seed=seed
    )

    rewards_history = []
    
    for ep in range(episodes):
        # Varying initial inventory and remaining shelf life for robustness
        starting_stock = int(env.rng.integers(10, 50))
        starting_days = int(env.rng.integers(1, 9))
        state = env.reset(stock=starting_stock, days=starting_days)
        total_ep_reward = 0.0
        done = False
        
        while not done:
            action = agent.choose_action(state, explore=True)
            next_state, reward, done, _ = env.step(action)
            agent.update(state, action, reward, next_state, done)
            total_ep_reward += reward
            state = next_state
            
        agent.decay_epsilon()
        rewards_history.append(total_ep_reward)

        if (ep + 1) % 500 == 0:
            avg_last = sum(rewards_history[-100:]) / 100.0
            print(f"    Episode {ep+1}/{episodes} | Avg Reward (last 100): {avg_last:.2f} | Epsilon: {agent.epsilon:.4f}")

    training_summary = {
        "episodes": episodes,
        "final_epsilon": round(agent.epsilon, 4),
        "states_learned": len(agent.q_table),
        "avg_reward_last_100": round(sum(rewards_history[-100:]) / 100.0, 2),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed
    }

    agent.save_policy(output_path, training_summary)
    print(f"[+] Training completed successfully! Learned {len(agent.q_table)} states.")
    print(f"[+] Policy saved to: {output_path}")

if __name__ == "__main__":
    train_agent()
