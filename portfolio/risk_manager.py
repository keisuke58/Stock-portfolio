"""
Risk Management Module

Provides comprehensive portfolio and position risk management tools:
- Position Sizing (Kelly Criterion, Volatility-based)
- Correlation Analysis
- Exit Strategy Management
- Sector Rotation Analysis
- Portfolio Risk Metrics (VaR, CVaR, Sharpe, Sortino, Max Drawdown)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum
import math


@dataclass
class PositionSize:
    """Result of position sizing calculation"""
    shares: int
    dollar_amount: float
    position_pct: float  # Percentage of portfolio
    risk_amount: float  # Dollar amount at risk
    method: str  # Sizing method used
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'shares': self.shares,
            'dollar_amount': round(self.dollar_amount, 2),
            'position_pct': round(self.position_pct * 100, 2),
            'risk_amount': round(self.risk_amount, 2),
            'method': self.method,
            'details': self.details
        }


class ExitReason(Enum):
    """Reasons for exit signals"""
    TRAILING_STOP = "trailing_stop"
    PROFIT_TARGET = "profit_target"
    TIME_BASED = "time_based"
    VOLATILITY_STOP = "volatility_stop"
    TECHNICAL_SIGNAL = "technical_signal"


@dataclass
class ExitSignal:
    """Exit signal result"""
    should_exit: bool
    reason: Optional[ExitReason]
    exit_price: Optional[float]
    profit_loss_pct: float
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'should_exit': self.should_exit,
            'reason': self.reason.value if self.reason else None,
            'exit_price': round(self.exit_price, 4) if self.exit_price else None,
            'profit_loss_pct': round(self.profit_loss_pct, 2),
            'details': self.details
        }


@dataclass
class PortfolioRiskMetrics:
    """Comprehensive portfolio risk metrics"""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # Days
    volatility: float  # Annualized
    beta: Optional[float] = None
    alpha: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            'var_95': round(self.var_95, 4),
            'var_99': round(self.var_99, 4),
            'cvar_95': round(self.cvar_95, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 3),
            'sortino_ratio': round(self.sortino_ratio, 3),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_duration': self.max_drawdown_duration,
            'volatility': round(self.volatility, 4),
            'beta': round(self.beta, 3) if self.beta else None,
            'alpha': round(self.alpha, 4) if self.alpha else None
        }


class PositionSizer:
    """
    Position sizing calculator using various methods.

    Methods:
    - Kelly Criterion: Optimal position size based on win rate and payoff ratio
    - Volatility-based: Position size based on ATR for consistent risk
    - Fixed Risk: Position size based on fixed dollar risk amount
    """

    def __init__(self, config: Dict = None):
        """
        Initialize position sizer.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self.default_risk_pct = self.config.get('default_risk_per_trade', 0.02)
        self.max_position_pct = self.config.get('max_position_size', 0.10)
        self.kelly_fraction = self.config.get('kelly_fraction', 0.5)
        self.atr_stop_multiplier = self.config.get('atr_stop_multiplier', 2.0)

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion position size.

        Kelly % = W - [(1-W) / R]
        Where W = win rate, R = win/loss ratio

        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average winning trade (positive)
            avg_loss: Average losing trade (positive, absolute value)

        Returns:
            Optimal position size as fraction of portfolio (0-1)
        """
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        # Win/loss ratio
        r = avg_win / avg_loss

        # Kelly formula
        kelly = win_rate - ((1 - win_rate) / r)

        # Apply fractional Kelly (typically 0.5)
        fractional_kelly = kelly * self.kelly_fraction

        # Clamp to reasonable range
        return max(0.0, min(self.max_position_pct, fractional_kelly))

    def volatility_based_sizing(
        self,
        portfolio_value: float,
        entry_price: float,
        atr: float,
        target_risk_pct: float = None
    ) -> PositionSize:
        """
        Calculate position size based on ATR for consistent risk.

        Position Size = (Portfolio * Risk%) / (ATR * Multiplier)

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price per share
            atr: Average True Range
            target_risk_pct: Target risk as % of portfolio (default from config)

        Returns:
            PositionSize with calculated values
        """
        if target_risk_pct is None:
            target_risk_pct = self.default_risk_pct

        if atr <= 0 or entry_price <= 0:
            return PositionSize(
                shares=0,
                dollar_amount=0,
                position_pct=0,
                risk_amount=0,
                method='volatility_based',
                details={'error': 'Invalid ATR or entry price'}
            )

        # Calculate stop loss distance
        stop_distance = atr * self.atr_stop_multiplier

        # Dollar risk amount
        risk_amount = portfolio_value * target_risk_pct

        # Shares = Risk Amount / Stop Distance
        shares = int(risk_amount / stop_distance)

        # Dollar amount for position
        dollar_amount = shares * entry_price

        # Position as percentage of portfolio
        position_pct = dollar_amount / portfolio_value if portfolio_value > 0 else 0

        # Cap at max position size
        if position_pct > self.max_position_pct:
            position_pct = self.max_position_pct
            dollar_amount = portfolio_value * position_pct
            shares = int(dollar_amount / entry_price)
            risk_amount = shares * stop_distance

        return PositionSize(
            shares=shares,
            dollar_amount=dollar_amount,
            position_pct=position_pct,
            risk_amount=risk_amount,
            method='volatility_based',
            details={
                'atr': atr,
                'stop_distance': stop_distance,
                'atr_multiplier': self.atr_stop_multiplier,
                'suggested_stop': entry_price - stop_distance
            }
        )

    def calculate_position(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
        target_risk_pct: float = None
    ) -> PositionSize:
        """
        Calculate position size based on fixed stop-loss.

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price per share
            stop_loss_price: Stop-loss price
            target_risk_pct: Target risk as % of portfolio

        Returns:
            PositionSize with calculated values
        """
        if target_risk_pct is None:
            target_risk_pct = self.default_risk_pct

        if entry_price <= 0 or stop_loss_price >= entry_price:
            return PositionSize(
                shares=0,
                dollar_amount=0,
                position_pct=0,
                risk_amount=0,
                method='fixed_risk',
                details={'error': 'Invalid prices'}
            )

        # Risk per share
        risk_per_share = entry_price - stop_loss_price

        # Dollar risk amount
        risk_amount = portfolio_value * target_risk_pct

        # Number of shares
        shares = int(risk_amount / risk_per_share)

        # Dollar amount
        dollar_amount = shares * entry_price

        # Position percentage
        position_pct = dollar_amount / portfolio_value if portfolio_value > 0 else 0

        # Cap at max position size
        if position_pct > self.max_position_pct:
            position_pct = self.max_position_pct
            dollar_amount = portfolio_value * position_pct
            shares = int(dollar_amount / entry_price)
            risk_amount = shares * risk_per_share

        return PositionSize(
            shares=shares,
            dollar_amount=dollar_amount,
            position_pct=position_pct,
            risk_amount=risk_amount,
            method='fixed_risk',
            details={
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price,
                'risk_per_share': risk_per_share,
                'risk_pct': target_risk_pct
            }
        )


class CorrelationAnalyzer:
    """
    Analyze correlations between assets for portfolio diversification.
    """

    def calculate_correlation_matrix(
        self,
        price_data: Dict[str, List[Tuple[datetime, float]]]
    ) -> Dict:
        """
        Calculate correlation matrix for multiple assets.

        Args:
            price_data: Dict of {symbol: [(datetime, price), ...]}

        Returns:
            {
                'matrix': Dict[symbol][symbol] = correlation,
                'highly_correlated': List of pairs with corr > 0.7,
                'negatively_correlated': List of pairs with corr < -0.3
            }
        """
        symbols = list(price_data.keys())
        n = len(symbols)

        if n < 2:
            return {
                'matrix': {},
                'highly_correlated': [],
                'negatively_correlated': []
            }

        # Calculate returns for each asset
        returns = {}
        for symbol, prices in price_data.items():
            if len(prices) < 2:
                continue
            price_vals = [p[1] for p in prices]
            rets = [
                (price_vals[i] - price_vals[i-1]) / price_vals[i-1]
                for i in range(1, len(price_vals))
            ]
            returns[symbol] = rets

        # Build correlation matrix
        matrix = {}
        highly_correlated = []
        negatively_correlated = []

        for i, sym1 in enumerate(symbols):
            if sym1 not in returns:
                continue
            matrix[sym1] = {}
            for j, sym2 in enumerate(symbols):
                if sym2 not in returns:
                    continue
                if i == j:
                    matrix[sym1][sym2] = 1.0
                elif j < i and sym1 in matrix.get(sym2, {}):
                    matrix[sym1][sym2] = matrix[sym2][sym1]
                else:
                    corr = self._pearson_correlation(returns[sym1], returns[sym2])
                    matrix[sym1][sym2] = corr

                    if i < j:  # Only record pairs once
                        if corr > 0.7:
                            highly_correlated.append({
                                'pair': (sym1, sym2),
                                'correlation': corr
                            })
                        elif corr < -0.3:
                            negatively_correlated.append({
                                'pair': (sym1, sym2),
                                'correlation': corr
                            })

        return {
            'matrix': matrix,
            'highly_correlated': highly_correlated,
            'negatively_correlated': negatively_correlated
        }

    def check_portfolio_concentration(
        self,
        holdings: Dict[str, float],  # {symbol: position_value}
        correlation_matrix: Dict[str, Dict[str, float]],
        max_correlation: float = 0.7
    ) -> Dict:
        """
        Check portfolio for concentration risk due to correlated assets.

        Args:
            holdings: Dict of {symbol: position_value}
            correlation_matrix: Correlation matrix from calculate_correlation_matrix
            max_correlation: Threshold for high correlation warning

        Returns:
            {
                'concentration_risk': str ('low', 'medium', 'high'),
                'correlated_groups': List of correlated asset groups,
                'recommendations': List of recommendations
            }
        """
        total_value = sum(holdings.values())
        if total_value == 0:
            return {
                'concentration_risk': 'unknown',
                'correlated_groups': [],
                'recommendations': []
            }

        # Find correlated groups
        correlated_groups = []
        visited = set()

        for sym1 in holdings:
            if sym1 in visited or sym1 not in correlation_matrix:
                continue

            group = {sym1}
            for sym2 in holdings:
                if sym2 == sym1 or sym2 in visited or sym2 not in correlation_matrix.get(sym1, {}):
                    continue
                if correlation_matrix[sym1].get(sym2, 0) > max_correlation:
                    group.add(sym2)
                    visited.add(sym2)

            if len(group) > 1:
                group_value = sum(holdings.get(s, 0) for s in group)
                correlated_groups.append({
                    'symbols': list(group),
                    'total_value': group_value,
                    'pct_of_portfolio': group_value / total_value
                })
                visited.add(sym1)

        # Calculate concentration risk
        max_group_pct = max((g['pct_of_portfolio'] for g in correlated_groups), default=0)

        if max_group_pct > 0.5:
            concentration_risk = 'high'
        elif max_group_pct > 0.3:
            concentration_risk = 'medium'
        else:
            concentration_risk = 'low'

        # Generate recommendations
        recommendations = []
        for group in correlated_groups:
            if group['pct_of_portfolio'] > 0.3:
                recommendations.append(
                    f"Consider reducing exposure to correlated group: {', '.join(group['symbols'])} "
                    f"({group['pct_of_portfolio']*100:.1f}% of portfolio)"
                )

        return {
            'concentration_risk': concentration_risk,
            'correlated_groups': correlated_groups,
            'recommendations': recommendations
        }

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)


class ExitStrategyManager:
    """
    Manage various exit strategies for positions.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize exit strategy manager.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self.trailing_stop_pct = self.config.get('trailing_stop_pct', 0.10)
        self.max_holding_days = self.config.get('max_holding_days', 90)

    def trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        high_since_entry: float,
        trailing_pct: float = None
    ) -> ExitSignal:
        """
        Check trailing stop exit.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            high_since_entry: Highest price since entry
            trailing_pct: Trailing stop percentage (default from config)

        Returns:
            ExitSignal indicating if stop was hit
        """
        if trailing_pct is None:
            trailing_pct = self.trailing_stop_pct

        # Calculate trailing stop level
        stop_level = high_since_entry * (1 - trailing_pct)

        # Check if stop is hit
        should_exit = current_price <= stop_level

        # Calculate P&L
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        return ExitSignal(
            should_exit=should_exit,
            reason=ExitReason.TRAILING_STOP if should_exit else None,
            exit_price=current_price if should_exit else None,
            profit_loss_pct=pnl_pct,
            details={
                'stop_level': stop_level,
                'high_since_entry': high_since_entry,
                'trailing_pct': trailing_pct,
                'distance_to_stop_pct': ((current_price - stop_level) / current_price) * 100 if current_price > 0 else 0
            }
        )

    def profit_target(
        self,
        entry_price: float,
        current_price: float,
        target_pct: float
    ) -> ExitSignal:
        """
        Check profit target exit.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            target_pct: Target profit percentage (e.g., 0.20 for 20%)

        Returns:
            ExitSignal indicating if target was hit
        """
        # Calculate current P&L
        pnl_pct = ((current_price - entry_price) / entry_price) if entry_price > 0 else 0

        # Check if target is hit
        should_exit = pnl_pct >= target_pct

        # Target price
        target_price = entry_price * (1 + target_pct)

        return ExitSignal(
            should_exit=should_exit,
            reason=ExitReason.PROFIT_TARGET if should_exit else None,
            exit_price=current_price if should_exit else None,
            profit_loss_pct=pnl_pct * 100,
            details={
                'target_pct': target_pct * 100,
                'target_price': target_price,
                'distance_to_target_pct': (target_pct - pnl_pct) * 100
            }
        )

    def time_based_exit(
        self,
        entry_date: datetime,
        current_date: datetime,
        max_holding_days: int = None
    ) -> ExitSignal:
        """
        Check time-based exit.

        Args:
            entry_date: Date of entry
            current_date: Current date
            max_holding_days: Maximum days to hold (default from config)

        Returns:
            ExitSignal indicating if time limit is reached
        """
        if max_holding_days is None:
            max_holding_days = self.max_holding_days

        # Calculate days held
        days_held = (current_date - entry_date).days

        # Check if time limit reached
        should_exit = days_held >= max_holding_days

        return ExitSignal(
            should_exit=should_exit,
            reason=ExitReason.TIME_BASED if should_exit else None,
            exit_price=None,
            profit_loss_pct=0,  # P&L not known without price
            details={
                'days_held': days_held,
                'max_holding_days': max_holding_days,
                'days_remaining': max(0, max_holding_days - days_held)
            }
        )

    def volatility_stop(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        multiplier: float = 2.0
    ) -> ExitSignal:
        """
        Check volatility-based stop (ATR stop).

        Args:
            entry_price: Original entry price
            current_price: Current market price
            atr: Average True Range
            multiplier: ATR multiplier for stop distance

        Returns:
            ExitSignal indicating if volatility stop was hit
        """
        # Calculate stop level
        stop_distance = atr * multiplier
        stop_level = entry_price - stop_distance

        # Check if stop is hit
        should_exit = current_price <= stop_level

        # Calculate P&L
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        return ExitSignal(
            should_exit=should_exit,
            reason=ExitReason.VOLATILITY_STOP if should_exit else None,
            exit_price=current_price if should_exit else None,
            profit_loss_pct=pnl_pct,
            details={
                'stop_level': stop_level,
                'atr': atr,
                'multiplier': multiplier,
                'stop_distance': stop_distance
            }
        )

    def evaluate_all_exits(
        self,
        entry_price: float,
        current_price: float,
        high_since_entry: float,
        entry_date: datetime,
        current_date: datetime,
        atr: float = None,
        profit_targets: List[float] = None
    ) -> List[ExitSignal]:
        """
        Evaluate all exit strategies and return triggered signals.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            high_since_entry: Highest price since entry
            entry_date: Date of entry
            current_date: Current date
            atr: Average True Range (optional)
            profit_targets: List of profit target percentages

        Returns:
            List of triggered ExitSignals
        """
        signals = []

        # Trailing stop
        trailing = self.trailing_stop(entry_price, current_price, high_since_entry)
        if trailing.should_exit:
            signals.append(trailing)

        # Time-based
        time_exit = self.time_based_exit(entry_date, current_date)
        if time_exit.should_exit:
            signals.append(time_exit)

        # Volatility stop
        if atr:
            vol_stop = self.volatility_stop(entry_price, current_price, atr)
            if vol_stop.should_exit:
                signals.append(vol_stop)

        # Profit targets
        if profit_targets:
            for target in profit_targets:
                target_exit = self.profit_target(entry_price, current_price, target)
                if target_exit.should_exit:
                    signals.append(target_exit)
                    break  # Only need first hit target

        return signals


class SectorRotationAnalyzer:
    """
    Analyze sector momentum for rotation strategies.
    """

    # Default sector mapping
    DEFAULT_SECTORS = {
        'XLF': 'Financials',
        'XLK': 'Technology',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'XLI': 'Industrials',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLU': 'Utilities',
        'XLB': 'Materials',
        'XLRE': 'Real Estate',
        'XLC': 'Communication Services'
    }

    def calculate_sector_momentum(
        self,
        sector_returns: Dict[str, List[float]],
        lookback_periods: List[int] = None
    ) -> Dict:
        """
        Calculate sector momentum rankings.

        Args:
            sector_returns: Dict of {sector: [daily_returns, ...]}
            lookback_periods: Periods to analyze (default [20, 60, 120])

        Returns:
            {
                'rankings': Dict of {period: [(sector, momentum), ...]},
                'leaders': List of top sectors,
                'laggards': List of bottom sectors,
                'momentum_scores': Dict of {sector: composite_score}
            }
        """
        if lookback_periods is None:
            lookback_periods = [20, 60, 120]

        rankings = {}
        momentum_scores = {sector: 0 for sector in sector_returns}

        for period in lookback_periods:
            period_momentum = []

            for sector, returns in sector_returns.items():
                if len(returns) >= period:
                    # Calculate cumulative return for period
                    period_returns = returns[-period:]
                    cum_return = 1.0
                    for r in period_returns:
                        cum_return *= (1 + r)
                    cum_return -= 1

                    period_momentum.append((sector, cum_return))

            # Sort by momentum (highest first)
            period_momentum.sort(key=lambda x: x[1], reverse=True)
            rankings[period] = period_momentum

            # Add to composite score (weight by period importance)
            weight = 1 / math.sqrt(period)  # Shorter periods get more weight
            for rank, (sector, mom) in enumerate(period_momentum):
                # Higher rank = lower score addition
                momentum_scores[sector] += (len(period_momentum) - rank) * weight

        # Determine leaders and laggards
        sorted_sectors = sorted(
            momentum_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        leaders = [s[0] for s in sorted_sectors[:3]]
        laggards = [s[0] for s in sorted_sectors[-3:]]

        return {
            'rankings': rankings,
            'leaders': leaders,
            'laggards': laggards,
            'momentum_scores': momentum_scores
        }

    def suggest_sector_allocation(
        self,
        current_allocation: Dict[str, float],  # {sector: current_pct}
        momentum_rankings: Dict,  # From calculate_sector_momentum
        target_positions: int = 5,
        max_per_sector: float = 0.25
    ) -> Dict:
        """
        Suggest sector allocation based on momentum.

        Args:
            current_allocation: Current sector weights
            momentum_rankings: Result from calculate_sector_momentum
            target_positions: Number of sectors to hold
            max_per_sector: Maximum allocation per sector

        Returns:
            {
                'suggested_allocation': Dict of {sector: suggested_pct},
                'changes': List of recommended changes,
                'sectors_to_add': List,
                'sectors_to_remove': List
            }
        """
        momentum_scores = momentum_rankings.get('momentum_scores', {})
        leaders = momentum_rankings.get('leaders', [])

        # Sort sectors by momentum score
        sorted_sectors = sorted(
            momentum_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Select top N sectors
        selected_sectors = [s[0] for s in sorted_sectors[:target_positions]]

        # Calculate suggested allocation (equal weight, capped)
        base_weight = 1.0 / target_positions
        suggested_allocation = {}

        for sector in selected_sectors:
            # Overweight leaders slightly
            if sector in leaders[:2]:
                weight = min(max_per_sector, base_weight * 1.2)
            else:
                weight = min(max_per_sector, base_weight)
            suggested_allocation[sector] = weight

        # Normalize to sum to 1
        total = sum(suggested_allocation.values())
        if total > 0:
            suggested_allocation = {k: v/total for k, v in suggested_allocation.items()}

        # Determine changes
        current_sectors = set(s for s, v in current_allocation.items() if v > 0.01)
        suggested_sectors = set(suggested_allocation.keys())

        sectors_to_add = list(suggested_sectors - current_sectors)
        sectors_to_remove = list(current_sectors - suggested_sectors)

        changes = []
        for sector in sectors_to_add:
            changes.append({
                'action': 'add',
                'sector': sector,
                'target_pct': suggested_allocation.get(sector, 0) * 100
            })

        for sector in sectors_to_remove:
            changes.append({
                'action': 'remove',
                'sector': sector,
                'current_pct': current_allocation.get(sector, 0) * 100
            })

        for sector in (current_sectors & suggested_sectors):
            current = current_allocation.get(sector, 0)
            suggested = suggested_allocation.get(sector, 0)
            if abs(current - suggested) > 0.05:  # 5% threshold
                changes.append({
                    'action': 'rebalance',
                    'sector': sector,
                    'current_pct': current * 100,
                    'target_pct': suggested * 100
                })

        return {
            'suggested_allocation': {k: round(v, 4) for k, v in suggested_allocation.items()},
            'changes': changes,
            'sectors_to_add': sectors_to_add,
            'sectors_to_remove': sectors_to_remove
        }


class PortfolioRiskCalculator:
    """
    Calculate comprehensive portfolio risk metrics.
    """

    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize risk calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """
        Calculate Value at Risk (VaR).

        Args:
            returns: List of daily returns
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            method: 'historical' or 'parametric'

        Returns:
            VaR as positive value (loss)
        """
        if len(returns) < 20:
            return 0.0

        if method == 'historical':
            # Historical simulation: use actual return distribution
            sorted_returns = sorted(returns)
            index = int((1 - confidence_level) * len(sorted_returns))
            var = -sorted_returns[index]  # Convert to positive loss
        else:
            # Parametric: assume normal distribution
            mean = sum(returns) / len(returns)
            variance = sum((r - mean) ** 2 for r in returns) / len(returns)
            std = math.sqrt(variance)

            # Z-score for confidence level
            z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
            z = z_scores.get(confidence_level, 1.645)

            var = -(mean - z * std)  # Convert to positive loss

        return max(0, var)

    def calculate_cvar(
        self,
        returns: List[float],
        confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).

        CVaR is the expected loss given that loss exceeds VaR.

        Args:
            returns: List of daily returns
            confidence_level: Confidence level

        Returns:
            CVaR as positive value
        """
        if len(returns) < 20:
            return 0.0

        sorted_returns = sorted(returns)
        cutoff_index = int((1 - confidence_level) * len(sorted_returns))

        # Average of returns beyond VaR
        tail_returns = sorted_returns[:cutoff_index + 1]
        if not tail_returns:
            return 0.0

        cvar = -sum(tail_returns) / len(tail_returns)
        return max(0, cvar)

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = None,
        annualize: bool = True
    ) -> float:
        """
        Calculate Sharpe Ratio.

        Sharpe = (Return - Risk Free Rate) / Std Dev

        Args:
            returns: List of daily returns
            risk_free_rate: Annual risk-free rate
            annualize: Whether to annualize

        Returns:
            Sharpe ratio
        """
        if len(returns) < 20:
            return 0.0

        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        # Daily risk-free rate
        daily_rf = risk_free_rate / 252

        # Calculate excess returns
        excess_returns = [r - daily_rf for r in returns]

        mean_excess = sum(excess_returns) / len(excess_returns)
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / len(excess_returns)
        std = math.sqrt(variance)

        if std == 0:
            return 0.0

        sharpe = mean_excess / std

        if annualize:
            sharpe *= math.sqrt(252)

        return sharpe

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = None,
        annualize: bool = True
    ) -> float:
        """
        Calculate Sortino Ratio (downside-risk adjusted return).

        Sortino = (Return - Risk Free Rate) / Downside Std Dev

        Args:
            returns: List of daily returns
            risk_free_rate: Annual risk-free rate
            annualize: Whether to annualize

        Returns:
            Sortino ratio
        """
        if len(returns) < 20:
            return 0.0

        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        # Daily risk-free rate
        daily_rf = risk_free_rate / 252

        # Calculate excess returns
        excess_returns = [r - daily_rf for r in returns]
        mean_excess = sum(excess_returns) / len(excess_returns)

        # Downside returns only
        downside_returns = [r for r in excess_returns if r < 0]

        if not downside_returns:
            return float('inf') if mean_excess > 0 else 0.0

        # Downside deviation
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_std = math.sqrt(downside_variance)

        if downside_std == 0:
            return 0.0

        sortino = mean_excess / downside_std

        if annualize:
            sortino *= math.sqrt(252)

        return sortino

    def calculate_max_drawdown(
        self,
        equity_curve: List[float]
    ) -> Tuple[float, int, int]:
        """
        Calculate maximum drawdown.

        Args:
            equity_curve: List of portfolio values over time

        Returns:
            (max_drawdown, peak_index, trough_index)
        """
        if len(equity_curve) < 2:
            return (0.0, 0, 0)

        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0
        running_peak = equity_curve[0]
        running_peak_idx = 0

        for i, value in enumerate(equity_curve):
            if value > running_peak:
                running_peak = value
                running_peak_idx = i

            drawdown = (running_peak - value) / running_peak if running_peak > 0 else 0

            if drawdown > max_dd:
                max_dd = drawdown
                peak_idx = running_peak_idx
                trough_idx = i

        return (max_dd, peak_idx, trough_idx)

    def calculate_all_metrics(
        self,
        returns: List[float],
        equity_curve: List[float] = None,
        benchmark_returns: List[float] = None
    ) -> PortfolioRiskMetrics:
        """
        Calculate all portfolio risk metrics.

        Args:
            returns: List of daily returns
            equity_curve: Optional list of portfolio values
            benchmark_returns: Optional benchmark returns for beta/alpha

        Returns:
            PortfolioRiskMetrics object
        """
        # VaR and CVaR
        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        cvar_95 = self.calculate_cvar(returns, 0.95)

        # Risk-adjusted returns
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)

        # Max drawdown
        if equity_curve:
            max_dd, peak_idx, trough_idx = self.calculate_max_drawdown(equity_curve)
            max_dd_duration = trough_idx - peak_idx
        else:
            # Build equity curve from returns
            equity = [1.0]
            for r in returns:
                equity.append(equity[-1] * (1 + r))
            max_dd, peak_idx, trough_idx = self.calculate_max_drawdown(equity)
            max_dd_duration = trough_idx - peak_idx

        # Volatility (annualized)
        if returns:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) * math.sqrt(252)
        else:
            volatility = 0.0

        # Beta and Alpha (if benchmark provided)
        beta = None
        alpha = None
        if benchmark_returns and len(benchmark_returns) == len(returns):
            beta = self._calculate_beta(returns, benchmark_returns)
            alpha = self._calculate_alpha(returns, benchmark_returns, beta)

        return PortfolioRiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility,
            beta=beta,
            alpha=alpha
        )

    def _calculate_beta(
        self,
        returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """Calculate beta relative to benchmark."""
        if len(returns) != len(benchmark_returns) or len(returns) < 20:
            return 1.0

        mean_r = sum(returns) / len(returns)
        mean_b = sum(benchmark_returns) / len(benchmark_returns)

        covariance = sum(
            (returns[i] - mean_r) * (benchmark_returns[i] - mean_b)
            for i in range(len(returns))
        ) / len(returns)

        variance_b = sum((b - mean_b) ** 2 for b in benchmark_returns) / len(benchmark_returns)

        if variance_b == 0:
            return 1.0

        return covariance / variance_b

    def _calculate_alpha(
        self,
        returns: List[float],
        benchmark_returns: List[float],
        beta: float
    ) -> float:
        """Calculate Jensen's alpha."""
        if len(returns) != len(benchmark_returns):
            return 0.0

        mean_r = sum(returns) / len(returns) * 252  # Annualize
        mean_b = sum(benchmark_returns) / len(benchmark_returns) * 252

        # Alpha = Portfolio Return - (Risk-free + Beta * (Benchmark Return - Risk-free))
        alpha = mean_r - (self.risk_free_rate + beta * (mean_b - self.risk_free_rate))

        return alpha
