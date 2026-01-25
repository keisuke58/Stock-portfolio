"""
Pattern Detection Module
Detects chart patterns for trading signal confirmation.

Patterns include:
- Gap Detection (gap up/down)
- Double Top/Bottom
- Head & Shoulders / Inverse Head & Shoulders
- Wedge Patterns (rising/falling)
- Trendline Breaks
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from datetime import datetime
import statistics


class PatternType(Enum):
    """Types of chart patterns"""
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    INV_HEAD_SHOULDERS = "inv_head_shoulders"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    TRENDLINE_BREAK_UP = "trendline_break_up"
    TRENDLINE_BREAK_DOWN = "trendline_break_down"


@dataclass
class PatternResult:
    """Result of pattern detection"""
    pattern_type: PatternType
    detected: bool
    confidence: float  # 0.0-1.0
    key_levels: Dict[str, float] = field(default_factory=dict)
    target_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            'pattern_type': self.pattern_type.value,
            'detected': self.detected,
            'confidence': round(self.confidence, 2),
            'key_levels': {k: round(v, 4) for k, v in self.key_levels.items()},
            'target_price': round(self.target_price, 4) if self.target_price else None,
            'invalidation_price': round(self.invalidation_price, 4) if self.invalidation_price else None,
            'description': self.description
        }


class PatternDetector:
    """
    Detects chart patterns in price data.

    All methods accept a list of (datetime, price) tuples and return PatternResult objects.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize pattern detector with configuration.

        Args:
            config: Optional configuration dict with detection parameters
        """
        self.config = config or {}
        self.gap_min_pct = self.config.get('gap_min_pct', 2.0)
        self.double_top_tolerance_pct = self.config.get('double_top_tolerance_pct', 3.0)
        self.wedge_min_touches = self.config.get('wedge_min_touches', 4)
        self.trendline_break_threshold_pct = self.config.get('trendline_break_threshold_pct', 2.0)
        self.min_pattern_confidence = self.config.get('min_pattern_confidence', 0.6)

    def detect_all_patterns(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 60
    ) -> List[PatternResult]:
        """
        Run all pattern detection algorithms and return results.

        Args:
            prices: List of (datetime, price) tuples
            lookback: Number of days to analyze

        Returns:
            List of PatternResult objects for detected patterns
        """
        results = []

        # Gap detection
        gap_results = self.detect_gaps(prices)
        results.extend([r for r in gap_results if r.detected])

        # Double top/bottom
        double_top = self.detect_double_top_bottom(prices, lookback, 'top')
        double_bottom = self.detect_double_top_bottom(prices, lookback, 'bottom')
        if double_top.detected:
            results.append(double_top)
        if double_bottom.detected:
            results.append(double_bottom)

        # Head & Shoulders
        hs = self.detect_head_shoulders(prices, lookback, inverse=False)
        ihs = self.detect_head_shoulders(prices, lookback, inverse=True)
        if hs.detected:
            results.append(hs)
        if ihs.detected:
            results.append(ihs)

        # Wedge patterns
        rising = self.detect_wedge_patterns(prices, lookback, 'rising')
        falling = self.detect_wedge_patterns(prices, lookback, 'falling')
        if rising.detected:
            results.append(rising)
        if falling.detected:
            results.append(falling)

        # Trendline breaks
        break_up = self.detect_trendline_breaks(prices, lookback, 'up')
        break_down = self.detect_trendline_breaks(prices, lookback, 'down')
        if break_up.detected:
            results.append(break_up)
        if break_down.detected:
            results.append(break_down)

        return results

    def detect_gaps(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 5
    ) -> List[PatternResult]:
        """
        Detect price gaps (gap up or gap down).

        A gap occurs when today's low is above yesterday's high (gap up)
        or today's high is below yesterday's low (gap down).

        Args:
            prices: List of (datetime, price) - uses close prices as proxy
            lookback: Number of recent days to check

        Returns:
            List of PatternResult for any gaps found
        """
        results = []

        if len(prices) < 2:
            return results

        check_range = min(lookback, len(prices) - 1)

        for i in range(-check_range, 0):
            prev_price = prices[i - 1][1]
            curr_price = prices[i][1]

            # Estimate high/low from close prices
            prev_high = prev_price * 1.02
            prev_low = prev_price * 0.98
            curr_high = curr_price * 1.02
            curr_low = curr_price * 0.98

            gap_pct = abs(curr_price - prev_price) / prev_price * 100

            # Gap Up: Current low > Previous high
            if curr_low > prev_high and gap_pct >= self.gap_min_pct:
                gap_size = curr_low - prev_high
                results.append(PatternResult(
                    pattern_type=PatternType.GAP_UP,
                    detected=True,
                    confidence=min(1.0, gap_pct / 5.0),  # Higher gap = higher confidence
                    key_levels={
                        'gap_size': gap_size,
                        'gap_pct': gap_pct,
                        'gap_fill_level': prev_high,  # Price level to fill the gap
                        'gap_date': prices[i][0].isoformat() if hasattr(prices[i][0], 'isoformat') else str(prices[i][0])
                    },
                    target_price=curr_price * 1.05,  # 5% above gap
                    invalidation_price=prev_high,  # Gap fill invalidates
                    description=f"Gap up of {gap_pct:.1f}%"
                ))

            # Gap Down: Current high < Previous low
            elif curr_high < prev_low and gap_pct >= self.gap_min_pct:
                gap_size = prev_low - curr_high
                results.append(PatternResult(
                    pattern_type=PatternType.GAP_DOWN,
                    detected=True,
                    confidence=min(1.0, gap_pct / 5.0),
                    key_levels={
                        'gap_size': gap_size,
                        'gap_pct': gap_pct,
                        'gap_fill_level': prev_low,
                        'gap_date': prices[i][0].isoformat() if hasattr(prices[i][0], 'isoformat') else str(prices[i][0])
                    },
                    target_price=curr_price * 0.95,
                    invalidation_price=prev_low,
                    description=f"Gap down of {gap_pct:.1f}%"
                ))

        return results

    def detect_double_top_bottom(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 60,
        pattern_type: str = 'top'
    ) -> PatternResult:
        """
        Detect Double Top or Double Bottom patterns.

        Double Top: Two peaks at similar levels followed by decline
        Double Bottom: Two troughs at similar levels followed by rise

        Args:
            prices: List of (datetime, price)
            lookback: Number of days to analyze
            pattern_type: 'top' or 'bottom'

        Returns:
            PatternResult indicating if pattern was detected
        """
        if len(prices) < lookback:
            lookback = len(prices)

        if lookback < 20:
            return PatternResult(
                pattern_type=PatternType.DOUBLE_TOP if pattern_type == 'top' else PatternType.DOUBLE_BOTTOM,
                detected=False,
                confidence=0.0,
                description="Insufficient data"
            )

        recent_prices = [p[1] for p in prices[-lookback:]]
        current_price = recent_prices[-1]

        # Find local extrema
        extrema = self._find_local_extrema(recent_prices, pattern_type)

        if len(extrema) < 2:
            return PatternResult(
                pattern_type=PatternType.DOUBLE_TOP if pattern_type == 'top' else PatternType.DOUBLE_BOTTOM,
                detected=False,
                confidence=0.0,
                description="No extrema found"
            )

        # Get the two most recent extrema
        peak1_idx, peak1_val = extrema[-2]
        peak2_idx, peak2_val = extrema[-1]

        # Check if peaks are at similar levels
        tolerance = max(peak1_val, peak2_val) * (self.double_top_tolerance_pct / 100)
        peaks_aligned = abs(peak1_val - peak2_val) <= tolerance

        # Check for proper separation (at least 10 bars apart)
        proper_separation = (peak2_idx - peak1_idx) >= 10

        # Find neckline (lowest point between peaks for double top, highest for double bottom)
        between_prices = recent_prices[peak1_idx:peak2_idx + 1]
        if pattern_type == 'top':
            neckline = min(between_prices)
        else:
            neckline = max(between_prices)

        # Check for confirmation (price breaking neckline)
        if pattern_type == 'top':
            confirmed = current_price < neckline
        else:
            confirmed = current_price > neckline

        # Calculate confidence
        confidence = 0.0
        if peaks_aligned:
            confidence += 0.4
        if proper_separation:
            confidence += 0.3
        if confirmed:
            confidence += 0.3

        detected = confidence >= self.min_pattern_confidence

        # Calculate target (pattern height projected from neckline)
        pattern_height = abs(max(peak1_val, peak2_val) - neckline)
        if pattern_type == 'top':
            target_price = neckline - pattern_height
        else:
            target_price = neckline + pattern_height

        return PatternResult(
            pattern_type=PatternType.DOUBLE_TOP if pattern_type == 'top' else PatternType.DOUBLE_BOTTOM,
            detected=detected,
            confidence=confidence,
            key_levels={
                'peak1': peak1_val,
                'peak2': peak2_val,
                'neckline': neckline,
                'pattern_height': pattern_height
            },
            target_price=target_price,
            invalidation_price=max(peak1_val, peak2_val) if pattern_type == 'top' else min(peak1_val, peak2_val),
            description=f"{'Double Top' if pattern_type == 'top' else 'Double Bottom'} - {'Confirmed' if confirmed else 'Forming'}"
        )

    def detect_head_shoulders(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 60,
        inverse: bool = False
    ) -> PatternResult:
        """
        Detect Head and Shoulders or Inverse Head and Shoulders patterns.

        H&S: Left shoulder, higher head, right shoulder at similar level to left
        Inverse H&S: Left trough, lower head, right trough at similar level

        Args:
            prices: List of (datetime, price)
            lookback: Number of days to analyze
            inverse: If True, detect inverse pattern (bullish)

        Returns:
            PatternResult indicating if pattern was detected
        """
        if len(prices) < lookback:
            lookback = len(prices)

        if lookback < 30:
            return PatternResult(
                pattern_type=PatternType.INV_HEAD_SHOULDERS if inverse else PatternType.HEAD_SHOULDERS,
                detected=False,
                confidence=0.0,
                description="Insufficient data"
            )

        recent_prices = [p[1] for p in prices[-lookback:]]
        current_price = recent_prices[-1]

        # Find local extrema
        pattern_type = 'bottom' if inverse else 'top'
        extrema = self._find_local_extrema(recent_prices, pattern_type)

        if len(extrema) < 3:
            return PatternResult(
                pattern_type=PatternType.INV_HEAD_SHOULDERS if inverse else PatternType.HEAD_SHOULDERS,
                detected=False,
                confidence=0.0,
                description="Not enough extrema"
            )

        # Need at least 3 peaks/troughs
        # Find potential head (middle extremum that's more extreme)
        for i in range(1, len(extrema) - 1):
            left_idx, left_val = extrema[i - 1]
            head_idx, head_val = extrema[i]
            right_idx, right_val = extrema[i + 1]

            # Check if head is more extreme
            if inverse:
                is_valid_head = head_val < left_val and head_val < right_val
            else:
                is_valid_head = head_val > left_val and head_val > right_val

            if not is_valid_head:
                continue

            # Check if shoulders are at similar levels
            tolerance = max(left_val, right_val) * (self.double_top_tolerance_pct / 100)
            shoulders_aligned = abs(left_val - right_val) <= tolerance

            if not shoulders_aligned:
                continue

            # Calculate neckline (connect the lows/highs between shoulders)
            between_left = recent_prices[left_idx:head_idx]
            between_right = recent_prices[head_idx:right_idx + 1]

            if inverse:
                neckline_left = max(between_left) if between_left else left_val
                neckline_right = max(between_right) if between_right else right_val
            else:
                neckline_left = min(between_left) if between_left else left_val
                neckline_right = min(between_right) if between_right else right_val

            neckline = (neckline_left + neckline_right) / 2

            # Check for confirmation
            if inverse:
                confirmed = current_price > neckline
            else:
                confirmed = current_price < neckline

            # Calculate confidence
            confidence = 0.3  # Base for finding pattern
            if shoulders_aligned:
                confidence += 0.3
            if confirmed:
                confidence += 0.3

            # Symmetry bonus
            left_to_head = head_idx - left_idx
            head_to_right = right_idx - head_idx
            symmetry = 1 - abs(left_to_head - head_to_right) / max(left_to_head, head_to_right)
            confidence += symmetry * 0.1

            if confidence >= self.min_pattern_confidence:
                pattern_height = abs(head_val - neckline)
                if inverse:
                    target_price = neckline + pattern_height
                else:
                    target_price = neckline - pattern_height

                return PatternResult(
                    pattern_type=PatternType.INV_HEAD_SHOULDERS if inverse else PatternType.HEAD_SHOULDERS,
                    detected=True,
                    confidence=min(1.0, confidence),
                    key_levels={
                        'left_shoulder': left_val,
                        'head': head_val,
                        'right_shoulder': right_val,
                        'neckline': neckline
                    },
                    target_price=target_price,
                    invalidation_price=head_val,
                    description=f"{'Inverse ' if inverse else ''}Head & Shoulders - {'Confirmed' if confirmed else 'Forming'}"
                )

        return PatternResult(
            pattern_type=PatternType.INV_HEAD_SHOULDERS if inverse else PatternType.HEAD_SHOULDERS,
            detected=False,
            confidence=0.0,
            description="Pattern not found"
        )

    def detect_wedge_patterns(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 60,
        wedge_type: str = 'rising'
    ) -> PatternResult:
        """
        Detect Rising or Falling Wedge patterns.

        Rising Wedge: Converging trendlines with upward slope (bearish)
        Falling Wedge: Converging trendlines with downward slope (bullish)

        Args:
            prices: List of (datetime, price)
            lookback: Number of days to analyze
            wedge_type: 'rising' or 'falling'

        Returns:
            PatternResult indicating if pattern was detected
        """
        if len(prices) < lookback:
            lookback = len(prices)

        if lookback < 20:
            return PatternResult(
                pattern_type=PatternType.RISING_WEDGE if wedge_type == 'rising' else PatternType.FALLING_WEDGE,
                detected=False,
                confidence=0.0,
                description="Insufficient data"
            )

        recent_prices = [p[1] for p in prices[-lookback:]]
        current_price = recent_prices[-1]

        # Find local highs and lows
        highs = self._find_local_extrema(recent_prices, 'top')
        lows = self._find_local_extrema(recent_prices, 'bottom')

        if len(highs) < 2 or len(lows) < 2:
            return PatternResult(
                pattern_type=PatternType.RISING_WEDGE if wedge_type == 'rising' else PatternType.FALLING_WEDGE,
                detected=False,
                confidence=0.0,
                description="Not enough swing points"
            )

        # Calculate upper and lower trendlines using linear regression
        high_x = [h[0] for h in highs]
        high_y = [h[1] for h in highs]
        low_x = [l[0] for l in lows]
        low_y = [l[1] for l in lows]

        upper_slope, upper_intercept = self._linear_regression(high_x, high_y)
        lower_slope, lower_intercept = self._linear_regression(low_x, low_y)

        if upper_slope is None or lower_slope is None:
            return PatternResult(
                pattern_type=PatternType.RISING_WEDGE if wedge_type == 'rising' else PatternType.FALLING_WEDGE,
                detected=False,
                confidence=0.0,
                description="Could not calculate trendlines"
            )

        # Check for wedge characteristics
        # Rising wedge: both slopes positive, converging (upper slope < lower slope)
        # Falling wedge: both slopes negative, converging (upper slope > lower slope)

        is_converging = abs(upper_slope - lower_slope) > 0  # Lines must converge

        if wedge_type == 'rising':
            is_valid_wedge = upper_slope > 0 and lower_slope > 0 and upper_slope < lower_slope
        else:
            is_valid_wedge = upper_slope < 0 and lower_slope < 0 and upper_slope > lower_slope

        # Calculate current trendline values
        current_x = lookback - 1
        upper_trendline = upper_slope * current_x + upper_intercept
        lower_trendline = lower_slope * current_x + lower_intercept

        # Check for breakout
        if wedge_type == 'rising':
            breakout = current_price < lower_trendline
        else:
            breakout = current_price > upper_trendline

        # Calculate confidence
        confidence = 0.0
        if is_valid_wedge:
            confidence += 0.4
        if is_converging:
            confidence += 0.2
        if breakout:
            confidence += 0.4

        # Count touches (how well prices respect trendlines)
        touches = self._count_trendline_touches(
            recent_prices, upper_slope, upper_intercept, lower_slope, lower_intercept
        )
        if touches >= self.wedge_min_touches:
            confidence += 0.1

        detected = confidence >= self.min_pattern_confidence

        # Calculate apex (where lines converge)
        if upper_slope != lower_slope:
            apex_x = (lower_intercept - upper_intercept) / (upper_slope - lower_slope)
            apex_y = upper_slope * apex_x + upper_intercept
        else:
            apex_x = current_x + 20
            apex_y = upper_trendline

        # Target price (pattern height projected from breakout)
        pattern_height = abs(upper_trendline - lower_trendline)
        if wedge_type == 'rising':
            target_price = current_price - pattern_height
        else:
            target_price = current_price + pattern_height

        return PatternResult(
            pattern_type=PatternType.RISING_WEDGE if wedge_type == 'rising' else PatternType.FALLING_WEDGE,
            detected=detected,
            confidence=min(1.0, confidence),
            key_levels={
                'upper_trendline': upper_trendline,
                'lower_trendline': lower_trendline,
                'upper_slope': upper_slope,
                'lower_slope': lower_slope,
                'apex': apex_y,
                'touches': touches
            },
            target_price=target_price,
            invalidation_price=upper_trendline if wedge_type == 'rising' else lower_trendline,
            description=f"{'Rising' if wedge_type == 'rising' else 'Falling'} Wedge - {'Breakout' if breakout else 'Forming'}"
        )

    def detect_trendline_breaks(
        self,
        prices: List[Tuple[datetime, float]],
        lookback: int = 60,
        direction: str = 'up'
    ) -> PatternResult:
        """
        Detect trendline breaks.

        Args:
            prices: List of (datetime, price)
            lookback: Number of days to analyze
            direction: 'up' for resistance break, 'down' for support break

        Returns:
            PatternResult indicating if break was detected
        """
        if len(prices) < lookback:
            lookback = len(prices)

        if lookback < 10:
            return PatternResult(
                pattern_type=PatternType.TRENDLINE_BREAK_UP if direction == 'up' else PatternType.TRENDLINE_BREAK_DOWN,
                detected=False,
                confidence=0.0,
                description="Insufficient data"
            )

        recent_prices = [p[1] for p in prices[-lookback:]]
        current_price = recent_prices[-1]
        prev_price = recent_prices[-2]

        # Find extrema for trendline
        if direction == 'up':
            extrema = self._find_local_extrema(recent_prices[:-5], 'top')  # Resistance line
        else:
            extrema = self._find_local_extrema(recent_prices[:-5], 'bottom')  # Support line

        if len(extrema) < 2:
            return PatternResult(
                pattern_type=PatternType.TRENDLINE_BREAK_UP if direction == 'up' else PatternType.TRENDLINE_BREAK_DOWN,
                detected=False,
                confidence=0.0,
                description="Not enough points for trendline"
            )

        # Calculate trendline from last two significant extrema
        x_vals = [e[0] for e in extrema[-3:]]
        y_vals = [e[1] for e in extrema[-3:]]

        slope, intercept = self._linear_regression(x_vals, y_vals)

        if slope is None:
            return PatternResult(
                pattern_type=PatternType.TRENDLINE_BREAK_UP if direction == 'up' else PatternType.TRENDLINE_BREAK_DOWN,
                detected=False,
                confidence=0.0,
                description="Could not calculate trendline"
            )

        # Calculate trendline value at current position
        current_x = lookback - 1
        trendline_value = slope * current_x + intercept
        prev_x = lookback - 2
        prev_trendline = slope * prev_x + intercept

        # Calculate break threshold
        break_threshold = trendline_value * (self.trendline_break_threshold_pct / 100)

        # Check for break
        if direction == 'up':
            # Break above resistance
            broke_through = current_price > trendline_value + break_threshold
            was_below = prev_price <= prev_trendline
        else:
            # Break below support
            broke_through = current_price < trendline_value - break_threshold
            was_below = prev_price >= prev_trendline

        # Calculate confidence
        confidence = 0.0
        if broke_through:
            confidence += 0.5
            break_pct = abs(current_price - trendline_value) / trendline_value * 100
            confidence += min(0.3, break_pct / 10)  # More break = more confidence
        if was_below and broke_through:
            confidence += 0.2

        detected = confidence >= self.min_pattern_confidence

        # Target: project the break distance
        break_distance = abs(current_price - trendline_value)
        if direction == 'up':
            target_price = current_price + break_distance
        else:
            target_price = current_price - break_distance

        return PatternResult(
            pattern_type=PatternType.TRENDLINE_BREAK_UP if direction == 'up' else PatternType.TRENDLINE_BREAK_DOWN,
            detected=detected,
            confidence=min(1.0, confidence),
            key_levels={
                'trendline_value': trendline_value,
                'trendline_slope': slope,
                'break_point': current_price,
                'break_pct': abs(current_price - trendline_value) / trendline_value * 100 if trendline_value > 0 else 0
            },
            target_price=target_price,
            invalidation_price=trendline_value,
            description=f"Trendline Break {'Up' if direction == 'up' else 'Down'}"
        )

    def _find_local_extrema(
        self,
        prices: List[float],
        extrema_type: str = 'top',
        window: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Find local maxima or minima in price data.

        Args:
            prices: List of price values
            extrema_type: 'top' for maxima, 'bottom' for minima
            window: Window size for extrema detection

        Returns:
            List of (index, value) tuples for each extremum
        """
        extrema = []
        half_window = window // 2

        for i in range(half_window, len(prices) - half_window):
            window_slice = prices[i - half_window:i + half_window + 1]
            center_val = prices[i]

            if extrema_type == 'top':
                if center_val == max(window_slice):
                    extrema.append((i, center_val))
            else:
                if center_val == min(window_slice):
                    extrema.append((i, center_val))

        return extrema

    def _linear_regression(
        self,
        x: List[float],
        y: List[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate simple linear regression (slope and intercept).

        Args:
            x: Independent variable values
            y: Dependent variable values

        Returns:
            (slope, intercept) or (None, None) if calculation fails
        """
        if len(x) < 2 or len(x) != len(y):
            return None, None

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = n * sum_x2 - sum_x ** 2

        if denominator == 0:
            return None, None

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        return slope, intercept

    def _count_trendline_touches(
        self,
        prices: List[float],
        upper_slope: float,
        upper_intercept: float,
        lower_slope: float,
        lower_intercept: float,
        tolerance_pct: float = 1.0
    ) -> int:
        """
        Count how many times price touches the trendlines.

        Args:
            prices: List of price values
            upper_slope, upper_intercept: Upper trendline parameters
            lower_slope, lower_intercept: Lower trendline parameters
            tolerance_pct: Percentage tolerance for touch detection

        Returns:
            Number of touches
        """
        touches = 0

        for i, price in enumerate(prices):
            upper_line = upper_slope * i + upper_intercept
            lower_line = lower_slope * i + lower_intercept

            upper_tolerance = upper_line * (tolerance_pct / 100)
            lower_tolerance = lower_line * (tolerance_pct / 100)

            if abs(price - upper_line) <= upper_tolerance:
                touches += 1
            elif abs(price - lower_line) <= lower_tolerance:
                touches += 1

        return touches

    def get_bullish_patterns(self, results: List[PatternResult]) -> List[PatternResult]:
        """Filter for bullish patterns only."""
        bullish_types = {
            PatternType.GAP_UP,
            PatternType.DOUBLE_BOTTOM,
            PatternType.INV_HEAD_SHOULDERS,
            PatternType.FALLING_WEDGE,
            PatternType.TRENDLINE_BREAK_UP
        }
        return [r for r in results if r.pattern_type in bullish_types]

    def get_bearish_patterns(self, results: List[PatternResult]) -> List[PatternResult]:
        """Filter for bearish patterns only."""
        bearish_types = {
            PatternType.GAP_DOWN,
            PatternType.DOUBLE_TOP,
            PatternType.HEAD_SHOULDERS,
            PatternType.RISING_WEDGE,
            PatternType.TRENDLINE_BREAK_DOWN
        }
        return [r for r in results if r.pattern_type in bearish_types]
