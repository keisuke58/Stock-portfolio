"""
Data classes for structured data passing.
Replaces dict-based data passing with type-safe dataclasses.

These models provide:
- Type safety and IDE autocomplete
- Clear contracts between functions
- Serialization to/from dicts for backward compatibility
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AssetState(Enum):
    """Valid asset states in the state machine."""
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    BASE = "BASE"
    BUY = "BUY"


class Confidence(Enum):
    """Confidence levels for daily picks."""
    HIGH = "High"
    MID = "Mid"
    SPEC = "Spec"


class AssetCategory(Enum):
    """Asset category classification."""
    US_LARGE_CAP = "US_LARGE_CAP"
    US_MID_CAP = "US_MID_CAP"
    US_SMALL_CAP = "US_SMALL_CAP"
    US_ETF = "US_ETF"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    OTHER = "OTHER"


@dataclass
class PricePoint:
    """Single price data point."""
    timestamp: datetime
    price: float


@dataclass
class PriceData:
    """Historical price data."""
    symbol: str
    prices: List[PricePoint]
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def to_tuple_list(self) -> List[tuple]:
        """Convert to legacy tuple list format."""
        return [(p.timestamp, p.price) for p in self.prices]

    @classmethod
    def from_tuple_list(
        cls,
        symbol: str,
        data: List[tuple]
    ) -> 'PriceData':
        """Create from legacy tuple list format."""
        prices = [PricePoint(timestamp=t, price=p) for t, p in data]
        return cls(symbol=symbol, prices=prices)


@dataclass
class StockMetrics:
    """Financial metrics for stocks."""
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[int] = None
    enterprise_value: Optional[int] = None
    beta: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockMetrics':
        """Create from dictionary."""
        return cls(
            pe_ratio=data.get('pe_ratio') or data.get('trailingPE'),
            forward_pe=data.get('forward_pe') or data.get('forwardPE'),
            pb_ratio=data.get('pb_ratio') or data.get('priceToBook'),
            dividend_yield=data.get('dividend_yield') or data.get('dividendYield'),
            market_cap=data.get('market_cap') or data.get('marketCap'),
            enterprise_value=data.get('enterprise_value') or data.get('enterpriseValue'),
            beta=data.get('beta'),
        )


@dataclass
class FundamentalData:
    """L1 fundamental financial data."""
    fcf: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    financial_health_score: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional['FundamentalData']:
        """Create from dictionary, returns None if data is None."""
        if data is None:
            return None
        return cls(
            fcf=data.get('fcf'),
            revenue_growth=data.get('revenue_growth'),
            profit_margin=data.get('profit_margin'),
            financial_health_score=data.get('financial_health_score'),
            debt_to_equity=data.get('debt_to_equity'),
            current_ratio=data.get('current_ratio'),
            data_sources=data.get('data_sources', []),
        )


@dataclass
class AnalystData:
    """Analyst estimates and recommendations."""
    target_price: Optional[float] = None
    recommendation: Optional[str] = None
    num_analysts: Optional[int] = None
    eps_growth: Optional[float] = None
    revenue_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional['AnalystData']:
        """Create from dictionary."""
        if data is None:
            return None
        return cls(
            target_price=data.get('target_price'),
            recommendation=data.get('recommendation'),
            num_analysts=data.get('num_analysts'),
            eps_growth=data.get('eps_growth'),
            revenue_estimate=data.get('revenue_estimate'),
        )


@dataclass
class Features:
    """Technical features calculated from price data."""
    ath_ratio: Optional[float] = None
    return_30d: Optional[float] = None
    return_7d: Optional[float] = None
    return_3d: Optional[float] = None
    volatility: Optional[float] = None
    breakout_5d: bool = False
    price_range_7d: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Features':
        """Create from dictionary."""
        return cls(
            ath_ratio=data.get('ath_ratio'),
            return_30d=data.get('return_30d'),
            return_7d=data.get('return_7d'),
            return_3d=data.get('return_3d'),
            volatility=data.get('volatility'),
            breakout_5d=data.get('breakout_5d', False),
            price_range_7d=data.get('price_range_7d'),
        )


@dataclass
class VMSScores:
    """Value/Momentum/Stability scores."""
    value_score: float
    momentum_score: float
    stability_score: float
    total_score: float
    weights_used: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'value_score': self.value_score,
            'momentum_score': self.momentum_score,
            'stability_score': self.stability_score,
            'total_score': self.total_score,
            **self.weights_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VMSScores':
        """Create from dictionary."""
        return cls(
            value_score=data.get('value_score', 0),
            momentum_score=data.get('momentum_score', 0),
            stability_score=data.get('stability_score', 0),
            total_score=data.get('total_score', 0),
            weights_used=data.get('weights_used', {}),
        )


@dataclass
class Event:
    """News or SEC filing event."""
    title: str
    event_type: str
    impact: str  # 'positive', 'negative', 'neutral'
    source: str
    url: Optional[str] = None
    published_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AnalysisResult:
    """Complete analysis result for a symbol."""
    symbol: str
    asset_category: AssetCategory
    current_price: float
    current_state: AssetState
    scores: VMSScores

    # Optional fields
    old_state: Optional[AssetState] = None
    features: Optional[Features] = None
    metrics: Optional[StockMetrics] = None
    fundamental_data: Optional[FundamentalData] = None
    analyst_data: Optional[AnalystData] = None
    events: List[Event] = field(default_factory=list)
    data_quality_score: Optional[float] = None
    data_timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def confidence(self) -> Confidence:
        """Determine confidence level based on data availability."""
        has_fundamentals = self.fundamental_data is not None
        has_analyst = self.analyst_data is not None
        has_events = len(self.events) > 0

        if has_fundamentals and (has_analyst or has_events):
            return Confidence.HIGH
        elif has_fundamentals or has_analyst:
            return Confidence.MID
        return Confidence.SPEC

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for backward compatibility.

        Returns a flat dict that matches the legacy daily_pick format.
        """
        result = {
            'symbol': self.symbol,
            'asset_category': self.asset_category.value,
            'current_price': self.current_price,
            'current_state': self.current_state.value,
            'old_state': self.old_state.value if self.old_state else None,
            'total_score': self.scores.total_score,
            'value_score': self.scores.value_score,
            'momentum_score': self.scores.momentum_score,
            'stability_score': self.scores.stability_score,
            'confidence': self.confidence.value,
            'data_quality_score': self.data_quality_score,
            'report_timestamp': self.data_timestamp.isoformat(),
        }

        # Add features if available
        if self.features:
            result.update({
                'ath_ratio': self.features.ath_ratio,
                'return_30d': self.features.return_30d,
                'return_7d': self.features.return_7d,
                'return_3d': self.features.return_3d,
                'volatility': self.features.volatility,
                'breakout_5d': self.features.breakout_5d,
            })

        # Add metrics if available
        if self.metrics:
            result['metrics'] = self.metrics.to_dict()

        # Add fundamental data if available
        if self.fundamental_data:
            result['fundamental_data'] = self.fundamental_data.to_dict()

        # Add analyst data if available
        if self.analyst_data:
            result['analyst_data'] = self.analyst_data.to_dict()

        # Add events if available
        if self.events:
            result['events'] = [e.to_dict() for e in self.events]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create from dictionary (for deserialization)."""
        # Parse enums
        asset_category = AssetCategory(data.get('asset_category', 'OTHER'))
        current_state = AssetState(data.get('current_state', 'NORMAL'))
        old_state = AssetState(data['old_state']) if data.get('old_state') else None

        # Parse scores
        scores = VMSScores(
            value_score=data.get('value_score', 0),
            momentum_score=data.get('momentum_score', 0),
            stability_score=data.get('stability_score', 0),
            total_score=data.get('total_score', 0),
        )

        # Parse features if present
        features = None
        if any(k in data for k in ['ath_ratio', 'return_30d', 'volatility']):
            features = Features.from_dict(data)

        return cls(
            symbol=data['symbol'],
            asset_category=asset_category,
            current_price=data.get('current_price', 0),
            current_state=current_state,
            old_state=old_state,
            scores=scores,
            features=features,
            metrics=StockMetrics.from_dict(data.get('metrics', {})),
            fundamental_data=FundamentalData.from_dict(data.get('fundamental_data')),
            analyst_data=AnalystData.from_dict(data.get('analyst_data')),
            data_quality_score=data.get('data_quality_score'),
        )


@dataclass
class DailyPick:
    """
    Daily pick recommendation.

    This is a convenience wrapper around AnalysisResult
    with additional selection metadata.
    """
    result: AnalysisResult
    selection_reason: str = ""
    rank: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy daily_pick format."""
        data = self.result.to_dict()
        data['selection_reason'] = self.selection_reason
        data['rank'] = self.rank
        return data
