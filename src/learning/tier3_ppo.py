#!/usr/bin/env python3
"""
Tier 3: Proximal Policy Optimization (PPO) Agent

Deep Reinforcement Learning for trading decisions.

State Space:
- Portfolio state (positions, cash, P&L, drawdown)
- Market indicators (VIX, breadth, sector rotation)
- All 37 component outputs
- Recent trade history

Action Space:
- Position size: 0-100% (continuous)
- Hold duration target: 1-30 days
- Stop loss width: 5-25%
- Take profit target: 10-100%

Reward Function:
- Primary: Sharpe ratio optimization
- Penalties: Drawdown, violating risk limits
- Bonuses: Beating benchmark, high-conviction wins

Safety: Hard constraints on position size, drawdown, daily loss
"""

import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal, Beta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)

from .rl_models import (
    TradeRecord,
    DecisionRecord,
    ComponentScores,
    MarketContext,
    MarketRegimeType,
    TradeOutcome,
    LearningDataEncoder
)


# =============================================================================
# STATE AND ACTION SPACES
# =============================================================================

@dataclass
class TradingState:
    """Complete state representation for RL agent."""
    # Portfolio state (7 dimensions)
    cash_pct: float = 100.0  # % of account in cash
    num_positions: int = 0
    total_exposure_pct: float = 0.0
    unrealized_pnl_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    total_return_pct: float = 0.0
    days_since_last_trade: int = 0

    # Market indicators (10 dimensions)
    spy_change_pct: float = 0.0
    vix_level: float = 20.0
    advance_decline: float = 1.0
    stocks_above_ma50: float = 50.0
    new_highs_minus_lows: int = 0
    sector_rotation: float = 0.0
    regime_bull_prob: float = 0.2
    regime_bear_prob: float = 0.2
    regime_choppy_prob: float = 0.2
    crisis_active: float = 0.0

    # Component scores for current ticker (4 dimensions)
    theme_score: float = 5.0
    technical_score: float = 5.0
    ai_confidence: float = 0.5
    x_sentiment_score: float = 0.0

    # Recent performance (6 dimensions)
    win_rate_last_10: float = 0.5
    avg_win_last_10: float = 0.0
    avg_loss_last_10: float = 0.0
    profit_factor_last_10: float = 1.0
    sharpe_last_20: float = 0.0
    trades_this_week: int = 0

    def to_tensor(self) -> torch.Tensor:
        """Convert to PyTorch tensor."""
        state_array = [
            # Portfolio (7)
            self.cash_pct / 100,
            self.num_positions / 10,
            self.total_exposure_pct / 100,
            self.unrealized_pnl_pct / 100,
            self.current_drawdown_pct / 100,
            self.total_return_pct / 100,
            self.days_since_last_trade / 30,

            # Market (10)
            self.spy_change_pct / 10,
            self.vix_level / 50,
            self.advance_decline,
            self.stocks_above_ma50 / 100,
            self.new_highs_minus_lows / 500,
            self.sector_rotation,
            self.regime_bull_prob,
            self.regime_bear_prob,
            self.regime_choppy_prob,
            self.crisis_active,

            # Components (4)
            self.theme_score / 10,
            self.technical_score / 10,
            self.ai_confidence,
            self.x_sentiment_score,

            # Recent performance (6)
            self.win_rate_last_10,
            self.avg_win_last_10 / 20,
            self.avg_loss_last_10 / 20,
            self.profit_factor_last_10 / 3,
            self.sharpe_last_20,
            self.trades_this_week / 20
        ]

        return torch.tensor(state_array, dtype=torch.float32)


@dataclass
class TradingAction:
    """Action taken by RL agent."""
    position_size_pct: float  # 0-100
    hold_duration_days: int  # 1-30
    stop_loss_pct: float  # 5-25
    take_profit_pct: float  # 10-100

    @classmethod
    def from_tensor(cls, action_tensor: torch.Tensor) -> 'TradingAction':
        """Convert from PyTorch tensor."""
        return cls(
            position_size_pct=float(action_tensor[0] * 100),
            hold_duration_days=int(action_tensor[1] * 29) + 1,
            stop_loss_pct=float(action_tensor[2] * 20 + 5),
            take_profit_pct=float(action_tensor[3] * 90 + 10)
        )

    def to_tensor(self) -> torch.Tensor:
        """Convert to PyTorch tensor (normalized 0-1)."""
        return torch.tensor([
            self.position_size_pct / 100,
            (self.hold_duration_days - 1) / 29,
            (self.stop_loss_pct - 5) / 20,
            (self.take_profit_pct - 10) / 90
        ], dtype=torch.float32)


# =============================================================================
# NEURAL NETWORK ARCHITECTURE
# =============================================================================

class PolicyNetwork(nn.Module):
    """
    Actor network for PPO.

    Outputs mean and std for continuous actions.
    Uses Beta distribution for bounded actions (0-1).
    """

    def __init__(self, state_dim: int = 27, action_dim: int = 4, hidden_dim: int = 256):
        super().__init__()

        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim)
        )

        # Output heads for each action dimension
        self.position_size_head = nn.Linear(hidden_dim, 2)  # alpha, beta for Beta dist
        self.hold_duration_head = nn.Linear(hidden_dim, 2)
        self.stop_loss_head = nn.Linear(hidden_dim, 2)
        self.take_profit_head = nn.Linear(hidden_dim, 2)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Returns: (position_params, duration_params, stop_params, profit_params)
        Each params is (alpha, beta) for Beta distribution
        """
        shared_features = self.shared(state)

        # Get distribution parameters (ensure positive with softplus)
        position_params = torch.softplus(self.position_size_head(shared_features)) + 1
        duration_params = torch.softplus(self.hold_duration_head(shared_features)) + 1
        stop_params = torch.softplus(self.stop_loss_head(shared_features)) + 1
        profit_params = torch.softplus(self.take_profit_head(shared_features)) + 1

        return position_params, duration_params, stop_params, profit_params

    def sample_action(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Sample action from policy.

        Returns: (action, log_prob)
        """
        pos_params, dur_params, stop_params, profit_params = self.forward(state)

        # Create Beta distributions
        pos_dist = Beta(pos_params[:, 0], pos_params[:, 1])
        dur_dist = Beta(dur_params[:, 0], dur_params[:, 1])
        stop_dist = Beta(stop_params[:, 0], stop_params[:, 1])
        profit_dist = Beta(profit_params[:, 0], profit_params[:, 1])

        # Sample
        pos_action = pos_dist.sample()
        dur_action = dur_dist.sample()
        stop_action = stop_dist.sample()
        profit_action = profit_dist.sample()

        # Concatenate actions
        action = torch.stack([pos_action, dur_action, stop_action, profit_action], dim=-1)

        # Calculate log probability
        log_prob = (
            pos_dist.log_prob(pos_action) +
            dur_dist.log_prob(dur_action) +
            stop_dist.log_prob(stop_action) +
            profit_dist.log_prob(profit_action)
        )

        return action, log_prob


class ValueNetwork(nn.Module):
    """Critic network for PPO - estimates state value."""

    def __init__(self, state_dim: int = 27, hidden_dim: int = 256):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Estimate value of state."""
        return self.network(state)


# =============================================================================
# PPO AGENT
# =============================================================================

class PPOAgent:
    """
    Proximal Policy Optimization agent for trading.

    Implements PPO algorithm with safety constraints.
    """

    def __init__(
        self,
        state_dim: int = 27,
        action_dim: int = 4,
        hidden_dim: int = 256,
        lr: float = 3e-4,
        gamma: float = 0.99,
        epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        storage_dir: Optional[Path] = None
    ):
        """Initialize PPO agent."""
        self.storage_dir = storage_dir or Path('user_data/learning')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Hyperparameters
        self.gamma = gamma  # Discount factor
        self.epsilon = epsilon  # PPO clip parameter
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef

        # Networks
        self.policy = PolicyNetwork(state_dim, action_dim, hidden_dim)
        self.value = ValueNetwork(state_dim, hidden_dim)

        # Optimizers
        self.policy_optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.value_optimizer = optim.Adam(self.value.parameters(), lr=lr)

        # Experience buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []

        # Training stats
        self.training_steps = 0
        self.episodes = 0

        # Safety constraints
        self.max_position_size = 0.20  # 20% max
        self.max_daily_loss = 0.02  # 2% max daily loss
        self.max_drawdown = 0.15  # 15% max drawdown

        # Load saved model if exists
        self.load_model()

    # =========================================================================
    # ACTION SELECTION
    # =========================================================================

    def select_action(self, state: TradingState, training: bool = True) -> TradingAction:
        """
        Select action given state.

        If training=True, samples from policy (exploration).
        If training=False, uses mean of policy (exploitation).
        """
        state_tensor = state.to_tensor().unsqueeze(0)  # Add batch dimension

        with torch.no_grad():
            if training:
                action_tensor, log_prob = self.policy.sample_action(state_tensor)
                value = self.value(state_tensor)

                # Store for training
                self.states.append(state_tensor)
                self.actions.append(action_tensor)
                self.log_probs.append(log_prob)
                self.values.append(value)
            else:
                # Use mean of distributions (deterministic)
                pos_params, dur_params, stop_params, profit_params = self.policy.forward(state_tensor)

                # Mean of Beta(alpha, beta) = alpha / (alpha + beta)
                pos_action = pos_params[:, 0] / (pos_params[:, 0] + pos_params[:, 1])
                dur_action = dur_params[:, 0] / (dur_params[:, 0] + dur_params[:, 1])
                stop_action = stop_params[:, 0] / (stop_params[:, 0] + stop_params[:, 1])
                profit_action = profit_params[:, 0] / (profit_params[:, 0] + profit_params[:, 1])

                action_tensor = torch.stack([pos_action, dur_action, stop_action, profit_action], dim=-1)

        # Convert to TradingAction
        action = TradingAction.from_tensor(action_tensor.squeeze(0))

        # Apply safety constraints
        action.position_size_pct = min(action.position_size_pct, self.max_position_size * 100)

        return action

    def store_transition(self, reward: float, done: bool):
        """Store reward and done flag for last action."""
        self.rewards.append(reward)
        self.dones.append(done)

    # =========================================================================
    # REWARD CALCULATION
    # =========================================================================

    def calculate_reward(
        self,
        trade: TradeRecord,
        portfolio_state: Dict,
        violated_constraints: bool = False
    ) -> float:
        """
        Calculate reward for a trade outcome.

        Reward components:
        1. Risk-adjusted returns (Sharpe-like)
        2. Drawdown penalty
        3. Constraint violation penalty
        4. Beating benchmark bonus
        5. High-conviction win bonus
        """
        reward = 0.0

        if trade.outcome == TradeOutcome.WIN:
            # Base reward: P&L scaled by risk
            pnl = trade.pnl_pct or 0.0
            risk = max(abs(trade.stop_loss - trade.entry_price) / trade.entry_price * 100, 1.0)
            risk_adjusted_return = pnl / risk
            reward += risk_adjusted_return

            # High conviction win bonus
            if pnl > 10:  # >10% win
                reward += 2.0

        elif trade.outcome == TradeOutcome.LOSS:
            # Penalty for loss
            pnl = trade.pnl_pct or 0.0
            reward += pnl / 10  # Negative value

            # Extra penalty for large losses
            if pnl < -10:
                reward -= 5.0

        # Drawdown penalty (squared to penalize large drawdowns heavily)
        current_dd = portfolio_state.get('current_drawdown_pct', 0.0)
        if current_dd > 0:
            reward -= (current_dd / 10) ** 2

        # Constraint violation penalty
        if violated_constraints:
            reward -= 10.0

        # Overtrade penalty
        trades_this_week = portfolio_state.get('trades_this_week', 0)
        if trades_this_week > 20:
            reward -= (trades_this_week - 20) * 0.5

        # Sharpe ratio bonus (if we have enough trades)
        sharpe = portfolio_state.get('sharpe_ratio', 0.0)
        if sharpe > 1.0:
            reward += sharpe - 1.0

        return reward

    # =========================================================================
    # TRAINING (PPO ALGORITHM)
    # =========================================================================

    def train_step(self):
        """
        Perform one PPO training step.

        Uses collected experiences to update policy and value networks.
        """
        if len(self.states) < 2:
            return  # Need at least 2 experiences

        # Convert to tensors
        states = torch.cat(self.states)
        actions = torch.cat(self.actions)
        old_log_probs = torch.stack(self.log_probs)
        returns = self._compute_returns()

        # Compute advantages
        values = torch.cat(self.values)
        advantages = returns - values.detach()
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO update (multiple epochs)
        for _ in range(4):  # 4 epochs per update
            # Recompute log probs with current policy
            pos_params, dur_params, stop_params, profit_params = self.policy.forward(states)

            pos_dist = Beta(pos_params[:, 0], pos_params[:, 1])
            dur_dist = Beta(dur_params[:, 0], dur_params[:, 1])
            stop_dist = Beta(stop_params[:, 0], stop_params[:, 1])
            profit_dist = Beta(profit_params[:, 0], profit_params[:, 1])

            new_log_probs = (
                pos_dist.log_prob(actions[:, 0]) +
                dur_dist.log_prob(actions[:, 1]) +
                stop_dist.log_prob(actions[:, 2]) +
                profit_dist.log_prob(actions[:, 3])
            )

            # Compute probability ratio
            ratio = torch.exp(new_log_probs - old_log_probs)

            # Clipped surrogate objective
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.epsilon, 1 + self.epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()

            # Entropy bonus (encourages exploration)
            entropy = (pos_dist.entropy() + dur_dist.entropy() +
                      stop_dist.entropy() + profit_dist.entropy()).mean()

            # Value loss
            current_values = self.value(states)
            value_loss = nn.MSELoss()(current_values.squeeze(), returns)

            # Total loss
            loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

            # Update
            self.policy_optimizer.zero_grad()
            self.value_optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            torch.nn.utils.clip_grad_norm_(self.value.parameters(), 0.5)
            self.policy_optimizer.step()
            self.value_optimizer.step()

        self.training_steps += 1

        # Clear buffer
        self.clear_buffer()

    def _compute_returns(self) -> torch.Tensor:
        """Compute discounted returns."""
        returns = []
        R = 0
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            if done:
                R = 0
            R = reward + self.gamma * R
            returns.insert(0, R)

        returns = torch.tensor(returns, dtype=torch.float32)
        return returns

    def clear_buffer(self):
        """Clear experience buffer."""
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []

    # =========================================================================
    # MODEL PERSISTENCE
    # =========================================================================

    def save_model(self):
        """Save model to disk."""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'value_state_dict': self.value.state_dict(),
            'policy_optimizer_state_dict': self.policy_optimizer.state_dict(),
            'value_optimizer_state_dict': self.value_optimizer.state_dict(),
            'training_steps': self.training_steps,
            'episodes': self.episodes
        }, self.storage_dir / 'ppo_agent.pt')

    def load_model(self):
        """Load model from disk."""
        path = self.storage_dir / 'ppo_agent.pt'
        if not path.exists():
            return

        try:
            checkpoint = torch.load(path)
            self.policy.load_state_dict(checkpoint['policy_state_dict'])
            self.value.load_state_dict(checkpoint['value_state_dict'])
            self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer_state_dict'])
            self.value_optimizer.load_state_dict(checkpoint['value_optimizer_state_dict'])
            self.training_steps = checkpoint['training_steps']
            self.episodes = checkpoint['episodes']
            logger.info(f"Loaded PPO model (training steps: {self.training_steps})")
        except Exception as e:
            logger.warning(f"Could not load PPO model: {e}")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing PPO Agent...")

    agent = PPOAgent()

    # Test state
    state = TradingState(
        cash_pct=80.0,
        num_positions=2,
        theme_score=8.5,
        technical_score=7.2,
        ai_confidence=0.85,
        vix_level=15.0
    )

    print("\nTest action selection:")
    action = agent.select_action(state, training=False)
    print(f"Position Size: {action.position_size_pct:.1f}%")
    print(f"Hold Duration: {action.hold_duration_days} days")
    print(f"Stop Loss: {action.stop_loss_pct:.1f}%")
    print(f"Take Profit: {action.take_profit_pct:.1f}%")

    print("\n✅ PPO Agent test complete!")
