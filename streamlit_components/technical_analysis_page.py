"""
Technical Analysis Page
Provides comprehensive technical analysis tools including indicators,
pattern detection, and Fibonacci/Ichimoku analysis.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.indicators import FeatureCalculator
from features.pattern_detector import PatternDetector, PatternType, PatternResult
from fetchers import YahooFetcher, CoinGeckoFetcher
from signals import is_crypto_symbol
from core.constants import PATTERN_DETECTION_CONFIG


def render_technical_analysis_page():
    """Render the technical analysis page with tabs."""
    st.title("Technical Analysis")
    st.markdown("---")

    # Symbol input
    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input(
            "Symbol",
            value="AAPL",
            help="Enter a stock symbol (e.g., AAPL, MSFT) or crypto (e.g., BTC, ETH)"
        ).upper()
    with col2:
        lookback_days = st.selectbox(
            "Lookback Period",
            options=[30, 60, 90, 180, 365],
            index=2,
            help="Number of days to analyze"
        )

    if st.button("Analyze", type="primary"):
        with st.spinner(f"Analyzing {symbol}..."):
            # Fetch data
            prices, prices_with_volume = fetch_price_data(symbol, lookback_days)

            if not prices:
                st.error(f"Could not fetch data for {symbol}")
                return

            # Store in session state
            st.session_state['ta_prices'] = prices
            st.session_state['ta_prices_with_volume'] = prices_with_volume
            st.session_state['ta_symbol'] = symbol
            st.session_state['ta_lookback'] = lookback_days

    # Check if we have data to display
    if 'ta_prices' not in st.session_state:
        st.info("Enter a symbol and click Analyze to begin.")
        return

    prices = st.session_state['ta_prices']
    prices_with_volume = st.session_state.get('ta_prices_with_volume')
    symbol = st.session_state['ta_symbol']

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "Technical Indicators",
        "Pattern Detection",
        "Fibonacci & Ichimoku"
    ])

    with tab1:
        render_indicators_tab(prices, prices_with_volume, symbol)

    with tab2:
        render_pattern_detection_tab(prices, symbol)

    with tab3:
        render_fibonacci_ichimoku_tab(prices, symbol)


def fetch_price_data(symbol: str, days: int):
    """Fetch price data for the given symbol."""
    if is_crypto_symbol(symbol):
        fetcher = CoinGeckoFetcher()
        prices = fetcher.get_historical_prices(symbol, days=days)
        prices_with_volume = fetcher.get_historical_prices_with_volume(symbol, days=days)
    else:
        fetcher = YahooFetcher()
        prices = fetcher.get_historical_prices(symbol, days=days)
        prices_with_volume = fetcher.get_historical_prices_with_volume(symbol, days=days)

    return prices, prices_with_volume


def render_indicators_tab(prices, prices_with_volume, symbol: str):
    """Render the technical indicators tab."""
    st.subheader("Technical Indicators")

    current_price = prices[-1][1] if prices else 0

    # Calculate all indicators
    col1, col2, col3 = st.columns(3)

    # RSI
    rsi = FeatureCalculator.calculate_rsi(prices, 14)
    with col1:
        st.metric(
            "RSI (14)",
            f"{rsi:.1f}" if rsi else "N/A",
            delta="Oversold" if rsi and rsi < 30 else ("Overbought" if rsi and rsi > 70 else None),
            delta_color="normal" if rsi and rsi < 30 else "inverse"
        )

    # MACD
    macd = FeatureCalculator.calculate_macd(prices)
    with col2:
        if macd:
            signal_text = "Bullish Cross" if macd.get('bullish_cross') else (
                "Rising" if macd.get('histogram_rising') else "Neutral"
            )
            st.metric("MACD Signal", signal_text)
        else:
            st.metric("MACD Signal", "N/A")

    # Stochastic
    stoch = FeatureCalculator.calculate_stochastic(prices)
    with col3:
        if stoch:
            st.metric(
                "Stochastic %K",
                f"{stoch['k']:.1f}",
                delta="Oversold" if stoch.get('oversold') else None
            )
        else:
            st.metric("Stochastic %K", "N/A")

    st.markdown("---")

    # ATR and Volatility
    st.subheader("Volatility Metrics")
    col1, col2, col3 = st.columns(3)

    atr_data = FeatureCalculator.calculate_atr(prices)
    with col1:
        if atr_data:
            st.metric(
                "ATR (14)",
                f"${atr_data['atr']:.4f}",
                help="Average True Range - measures volatility"
            )
            st.caption(f"ATR %: {atr_data['atr_pct']:.2f}%")
            st.caption(f"Volatility: {atr_data['volatility_level'].upper()}")
        else:
            st.metric("ATR (14)", "N/A")

    with col2:
        if atr_data:
            st.metric(
                "Suggested Stop",
                f"${atr_data['suggested_stop']:.4f}",
                help="2x ATR below current price"
            )
            stop_distance = current_price - atr_data['suggested_stop']
            st.caption(f"Stop Distance: ${stop_distance:.4f}")
        else:
            st.metric("Suggested Stop", "N/A")

    volatility = FeatureCalculator.calculate_volatility(prices)
    with col3:
        if volatility:
            st.metric(
                "Daily Volatility",
                f"{volatility:.2f}%",
                help="Standard deviation of daily returns"
            )
        else:
            st.metric("Daily Volatility", "N/A")

    st.markdown("---")

    # CCI
    st.subheader("Momentum Indicators")
    col1, col2 = st.columns(2)

    cci_data = FeatureCalculator.calculate_cci(prices)
    with col1:
        if cci_data:
            st.metric(
                "CCI (20)",
                f"{cci_data['cci']:.1f}",
                delta="Overbought" if cci_data.get('overbought') else (
                    "Oversold" if cci_data.get('oversold') else None
                )
            )
            st.caption(f"Trend: {cci_data['trend'].upper()}")
        else:
            st.metric("CCI (20)", "N/A")

    # MFI (if volume data available)
    with col2:
        if prices_with_volume:
            mfi_data = FeatureCalculator.calculate_mfi(prices_with_volume)
            if mfi_data:
                st.metric(
                    "MFI (14)",
                    f"{mfi_data['mfi']:.1f}",
                    delta="Overbought" if mfi_data.get('overbought') else (
                        "Oversold" if mfi_data.get('oversold') else None
                    )
                )
                if mfi_data.get('divergence') != 'none':
                    st.caption(f"Divergence: {mfi_data['divergence'].upper()}")
            else:
                st.metric("MFI (14)", "N/A")
        else:
            st.metric("MFI (14)", "No volume data")

    st.markdown("---")

    # Pivot Points
    st.subheader("Pivot Points")
    pivot_data = FeatureCalculator.calculate_pivot_points(prices)

    if pivot_data:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**Resistance**")
            st.write(f"R3: ${pivot_data['r3']:.4f}")
            st.write(f"R2: ${pivot_data['r2']:.4f}")
            st.write(f"R1: ${pivot_data['r1']:.4f}")

        with col2:
            st.markdown("**Pivot**")
            st.write(f"P: ${pivot_data['pivot']:.4f}")
            st.caption(f"Current: ${current_price:.4f}")

        with col3:
            st.markdown("**Support**")
            st.write(f"S1: ${pivot_data['s1']:.4f}")
            st.write(f"S2: ${pivot_data['s2']:.4f}")
            st.write(f"S3: ${pivot_data['s3']:.4f}")

        with col4:
            st.markdown("**Position**")
            st.info(f"Zone: {pivot_data['current_zone']}")
    else:
        st.warning("Could not calculate pivot points")

    st.markdown("---")

    # OBV (if volume data available)
    if prices_with_volume:
        st.subheader("Volume Analysis")
        obv_data = FeatureCalculator.calculate_obv(prices_with_volume)

        if obv_data:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("OBV", f"{obv_data['obv']:,.0f}")

            with col2:
                st.metric(
                    "OBV Trend",
                    obv_data['obv_trend'].upper(),
                    delta="Confirmed" if obv_data.get('confirmation') else "Not Confirmed"
                )

            with col3:
                if obv_data.get('divergence') != 'none':
                    st.metric(
                        "Divergence",
                        obv_data['divergence'].upper(),
                        help="Divergence between price and OBV"
                    )
                else:
                    st.metric("Divergence", "None")


def render_pattern_detection_tab(prices, symbol: str):
    """Render the pattern detection tab."""
    st.subheader("Pattern Detection")

    # Configuration
    col1, col2 = st.columns(2)
    with col1:
        min_confidence = st.slider(
            "Minimum Confidence",
            min_value=0.3,
            max_value=0.9,
            value=0.6,
            step=0.1,
            help="Minimum confidence threshold for pattern detection"
        )

    with col2:
        pattern_lookback = st.selectbox(
            "Pattern Lookback",
            options=[30, 45, 60, 90],
            index=2,
            help="Number of days to search for patterns"
        )

    # Initialize detector with config
    config = {
        'gap_min_pct': PATTERN_DETECTION_CONFIG.GAP_MIN_PCT,
        'double_top_tolerance_pct': PATTERN_DETECTION_CONFIG.DOUBLE_TOP_TOLERANCE_PCT,
        'wedge_min_touches': PATTERN_DETECTION_CONFIG.WEDGE_MIN_TOUCHES,
        'trendline_break_threshold_pct': PATTERN_DETECTION_CONFIG.TRENDLINE_BREAK_THRESHOLD_PCT,
        'min_pattern_confidence': min_confidence
    }
    detector = PatternDetector(config)

    # Detect patterns
    if st.button("Detect Patterns", key="detect_patterns"):
        with st.spinner("Detecting patterns..."):
            all_patterns = detector.detect_all_patterns(prices, lookback=pattern_lookback)

            if all_patterns:
                st.session_state['detected_patterns'] = all_patterns
            else:
                st.session_state['detected_patterns'] = []

    # Display results
    if 'detected_patterns' in st.session_state:
        patterns = st.session_state['detected_patterns']

        if patterns:
            st.success(f"Found {len(patterns)} pattern(s)")

            # Separate bullish and bearish
            bullish = detector.get_bullish_patterns(patterns)
            bearish = detector.get_bearish_patterns(patterns)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Bullish Patterns")
                if bullish:
                    for p in bullish:
                        render_pattern_card(p, "bullish")
                else:
                    st.info("No bullish patterns detected")

            with col2:
                st.markdown("### Bearish Patterns")
                if bearish:
                    for p in bearish:
                        render_pattern_card(p, "bearish")
                else:
                    st.info("No bearish patterns detected")

            # Detailed table
            st.markdown("---")
            st.subheader("Pattern Details")
            pattern_df = pd.DataFrame([p.to_dict() for p in patterns])
            st.dataframe(pattern_df, use_container_width=True)
        else:
            st.info("No patterns detected with current settings. Try adjusting confidence threshold.")
    else:
        st.info("Click 'Detect Patterns' to search for chart patterns.")


def render_pattern_card(pattern: PatternResult, sentiment: str):
    """Render a card for a detected pattern."""
    color = "#28a745" if sentiment == "bullish" else "#dc3545"

    with st.container():
        st.markdown(f"""
        <div style="border-left: 4px solid {color}; padding-left: 10px; margin-bottom: 10px;">
            <strong>{pattern.pattern_type.value.replace('_', ' ').title()}</strong><br>
            <small>Confidence: {pattern.confidence:.0%}</small>
        </div>
        """, unsafe_allow_html=True)

        if pattern.target_price:
            st.caption(f"Target: ${pattern.target_price:.4f}")
        if pattern.invalidation_price:
            st.caption(f"Invalidation: ${pattern.invalidation_price:.4f}")
        if pattern.description:
            st.caption(pattern.description)


def render_fibonacci_ichimoku_tab(prices, symbol: str):
    """Render the Fibonacci and Ichimoku analysis tab."""
    current_price = prices[-1][1] if prices else 0

    # Fibonacci Section
    st.subheader("Fibonacci Retracement")

    fib_lookback = st.selectbox(
        "Fibonacci Lookback Period",
        options=[30, 60, 90, 120],
        index=1,
        key="fib_lookback"
    )

    fib_data = FeatureCalculator.calculate_fibonacci_retracement(prices, lookback=fib_lookback)

    if fib_data:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Fibonacci Levels**")

            # Create a DataFrame for levels
            levels_df = pd.DataFrame([
                {"Level": k, "Price": f"${v:.4f}"}
                for k, v in fib_data['levels'].items()
            ])
            st.dataframe(levels_df, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Current Position**")
            st.info(f"Price Zone: {fib_data['current_zone']}")
            st.metric("Swing High", f"${fib_data['swing_high']:.4f}")
            st.metric("Swing Low", f"${fib_data['swing_low']:.4f}")

            st.markdown("**Key Levels**")
            st.write(f"Nearest Support: ${fib_data['nearest_support']:.4f}")
            st.write(f"Nearest Resistance: ${fib_data['nearest_resistance']:.4f}")

        # Visual representation
        st.markdown("---")
        st.markdown("**Level Visualization**")

        # Create a simple chart showing price vs fib levels
        chart_data = []
        for level_name, level_price in fib_data['levels'].items():
            chart_data.append({
                'Level': level_name,
                'Price': level_price,
                'Type': 'Fib Level'
            })
        chart_data.append({
            'Level': 'Current',
            'Price': current_price,
            'Type': 'Current Price'
        })

        chart_df = pd.DataFrame(chart_data)
        st.bar_chart(chart_df.set_index('Level')['Price'])

    else:
        st.warning("Could not calculate Fibonacci levels. Ensure sufficient price data.")

    st.markdown("---")

    # Ichimoku Section
    st.subheader("Ichimoku Cloud")

    ichimoku_data = FeatureCalculator.calculate_ichimoku(prices)

    if ichimoku_data:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Lines**")
            st.write(f"Tenkan-sen: ${ichimoku_data['tenkan_sen']:.4f}")
            st.write(f"Kijun-sen: ${ichimoku_data['kijun_sen']:.4f}")
            st.write(f"Chikou Span: ${ichimoku_data['chikou_span']:.4f}")

        with col2:
            st.markdown("**Cloud (Kumo)**")
            st.write(f"Senkou A: ${ichimoku_data['senkou_span_a']:.4f}")
            st.write(f"Senkou B: ${ichimoku_data['senkou_span_b']:.4f}")
            st.write(f"Cloud Top: ${ichimoku_data['cloud_top']:.4f}")
            st.write(f"Cloud Bottom: ${ichimoku_data['cloud_bottom']:.4f}")

        with col3:
            st.markdown("**Analysis**")

            # Cloud color indicator
            if ichimoku_data['cloud_color'] == 'bullish':
                st.success("Cloud: BULLISH")
            else:
                st.error("Cloud: BEARISH")

            # Price position
            position = ichimoku_data['price_vs_cloud']
            if position == 'above':
                st.success(f"Price: ABOVE Cloud")
            elif position == 'below':
                st.error(f"Price: BELOW Cloud")
            else:
                st.warning(f"Price: INSIDE Cloud")

        # Ichimoku Signals
        st.markdown("---")
        st.markdown("**Ichimoku Signals**")

        signals = []

        # TK Cross
        if ichimoku_data['tenkan_sen'] > ichimoku_data['kijun_sen']:
            signals.append(("TK Cross", "Bullish", "Tenkan above Kijun"))
        else:
            signals.append(("TK Cross", "Bearish", "Tenkan below Kijun"))

        # Price vs Kijun
        if current_price > ichimoku_data['kijun_sen']:
            signals.append(("Price/Kijun", "Bullish", "Price above Kijun-sen"))
        else:
            signals.append(("Price/Kijun", "Bearish", "Price below Kijun-sen"))

        # Cloud thickness
        cloud_thickness = abs(ichimoku_data['senkou_span_a'] - ichimoku_data['senkou_span_b'])
        cloud_thickness_pct = (cloud_thickness / current_price) * 100 if current_price > 0 else 0
        signals.append(("Cloud Thickness", f"{cloud_thickness_pct:.2f}%",
                       "Thick cloud = strong support/resistance"))

        signals_df = pd.DataFrame(signals, columns=["Signal", "Status", "Description"])
        st.dataframe(signals_df, use_container_width=True, hide_index=True)

        # Overall assessment
        st.markdown("---")
        bullish_count = sum(1 for s in signals[:2] if s[1] == "Bullish")

        if bullish_count == 2 and ichimoku_data['price_vs_cloud'] == 'above':
            st.success("Overall Ichimoku Assessment: STRONGLY BULLISH")
        elif bullish_count >= 1 and ichimoku_data['price_vs_cloud'] != 'below':
            st.info("Overall Ichimoku Assessment: MODERATELY BULLISH")
        elif bullish_count == 0 and ichimoku_data['price_vs_cloud'] == 'below':
            st.error("Overall Ichimoku Assessment: STRONGLY BEARISH")
        else:
            st.warning("Overall Ichimoku Assessment: NEUTRAL/MIXED")

    else:
        st.warning("Could not calculate Ichimoku Cloud. Requires at least 52 days of data.")


# Entry point for the page
if __name__ == "__main__":
    st.set_page_config(
        page_title="Technical Analysis",
        page_icon="📊",
        layout="wide"
    )
    render_technical_analysis_page()
