"""
Risk Management Page
Portfolio and position risk management tools including:
- Position Sizing Calculator
- Correlation Matrix
- Exit Strategy Evaluation
- Sector Rotation Analysis
- Portfolio Risk Metrics
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.risk_manager import (
    PositionSizer,
    CorrelationAnalyzer,
    ExitStrategyManager,
    SectorRotationAnalyzer,
    PortfolioRiskCalculator,
)
from features.indicators import FeatureCalculator
from fetchers import YahooFetcher, CoinGeckoFetcher
from signals import is_crypto_symbol
from core.constants import RISK_MANAGEMENT_CONFIG


def render_risk_management_page():
    """Render the risk management page with tabs."""
    st.title("Risk Management")
    st.markdown("---")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Position Sizing",
        "Correlation Matrix",
        "Exit Strategies",
        "Sector Rotation",
        "Risk Metrics"
    ])

    with tab1:
        render_position_sizing_tab()

    with tab2:
        render_correlation_matrix_tab()

    with tab3:
        render_exit_strategies_tab()

    with tab4:
        render_sector_rotation_tab()

    with tab5:
        render_risk_metrics_tab()


def render_position_sizing_tab():
    """Render the position sizing calculator tab."""
    st.subheader("Position Sizing Calculator")

    # Initialize position sizer
    config = {
        'default_risk_per_trade': RISK_MANAGEMENT_CONFIG.DEFAULT_RISK_PER_TRADE,
        'max_position_size': RISK_MANAGEMENT_CONFIG.MAX_POSITION_SIZE,
        'kelly_fraction': RISK_MANAGEMENT_CONFIG.KELLY_FRACTION,
        'atr_stop_multiplier': RISK_MANAGEMENT_CONFIG.ATR_STOP_MULTIPLIER
    }
    sizer = PositionSizer(config)

    # Portfolio value input
    st.markdown("### Portfolio Settings")
    col1, col2 = st.columns(2)

    with col1:
        portfolio_value = st.number_input(
            "Portfolio Value ($)",
            min_value=1000.0,
            max_value=10000000.0,
            value=100000.0,
            step=1000.0,
            help="Total portfolio value"
        )

    with col2:
        risk_pct = st.slider(
            "Risk Per Trade (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            help="Percentage of portfolio to risk per trade"
        ) / 100

    st.markdown("---")

    # Method selection
    sizing_method = st.radio(
        "Sizing Method",
        options=["Fixed Risk (Stop-Loss)", "Volatility Based (ATR)", "Kelly Criterion"],
        horizontal=True
    )

    if sizing_method == "Fixed Risk (Stop-Loss)":
        st.markdown("### Fixed Risk Position Sizing")
        st.info("Calculate position size based on a fixed stop-loss price.")

        col1, col2 = st.columns(2)
        with col1:
            entry_price = st.number_input(
                "Entry Price ($)",
                min_value=0.01,
                value=100.0,
                step=0.01
            )
        with col2:
            stop_loss_price = st.number_input(
                "Stop-Loss Price ($)",
                min_value=0.01,
                max_value=entry_price - 0.01,
                value=entry_price * 0.95,
                step=0.01
            )

        if st.button("Calculate Position", key="calc_fixed"):
            result = sizer.calculate_position(
                portfolio_value, entry_price, stop_loss_price, risk_pct
            )
            display_position_result(result)

    elif sizing_method == "Volatility Based (ATR)":
        st.markdown("### Volatility-Based Position Sizing")
        st.info("Calculate position size using ATR for dynamic stop-loss.")

        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input(
                "Symbol",
                value="AAPL",
                key="atr_symbol"
            ).upper()

        with col2:
            atr_multiplier = st.slider(
                "ATR Multiplier",
                min_value=1.0,
                max_value=4.0,
                value=2.0,
                step=0.5,
                help="Stop distance = ATR x Multiplier"
            )

        if st.button("Calculate Position", key="calc_atr"):
            with st.spinner("Fetching ATR data..."):
                # Fetch price data
                if is_crypto_symbol(symbol):
                    fetcher = CoinGeckoFetcher()
                else:
                    fetcher = YahooFetcher()

                prices = fetcher.get_historical_prices(symbol, days=30)

                if prices:
                    atr_data = FeatureCalculator.calculate_atr(prices)
                    if atr_data:
                        entry_price = prices[-1][1]
                        # Update sizer config with custom multiplier
                        sizer.atr_stop_multiplier = atr_multiplier

                        result = sizer.volatility_based_sizing(
                            portfolio_value, entry_price, atr_data['atr'], risk_pct
                        )

                        st.metric("Current Price", f"${entry_price:.4f}")
                        st.metric("ATR (14)", f"${atr_data['atr']:.4f}")
                        st.metric("Volatility Level", atr_data['volatility_level'].upper())

                        display_position_result(result)
                    else:
                        st.error("Could not calculate ATR")
                else:
                    st.error(f"Could not fetch data for {symbol}")

    else:  # Kelly Criterion
        st.markdown("### Kelly Criterion Position Sizing")
        st.info("Calculate optimal position size based on historical win rate and payoff ratio.")

        col1, col2, col3 = st.columns(3)
        with col1:
            win_rate = st.slider(
                "Win Rate (%)",
                min_value=30,
                max_value=80,
                value=55,
                help="Historical win rate"
            ) / 100

        with col2:
            avg_win = st.number_input(
                "Average Win ($)",
                min_value=1.0,
                value=150.0,
                step=10.0
            )

        with col3:
            avg_loss = st.number_input(
                "Average Loss ($)",
                min_value=1.0,
                value=100.0,
                step=10.0
            )

        if st.button("Calculate Kelly", key="calc_kelly"):
            kelly_pct = sizer.kelly_criterion(win_rate, avg_win, avg_loss)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Full Kelly",
                    f"{kelly_pct * 2 / sizer.kelly_fraction:.1%}",
                    help="Full Kelly position size"
                )
            with col2:
                st.metric(
                    "Half Kelly (Recommended)",
                    f"{kelly_pct:.1%}",
                    help="Conservative Kelly position size"
                )
            with col3:
                dollar_amount = portfolio_value * kelly_pct
                st.metric(
                    "Dollar Amount",
                    f"${dollar_amount:,.2f}"
                )

            # Win/Loss stats
            st.markdown("---")
            st.markdown("**Trade Statistics**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"Win Rate: {win_rate:.1%}")
            with col2:
                st.write(f"Payoff Ratio: {avg_win/avg_loss:.2f}")
            with col3:
                expected_value = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
                st.write(f"Expected Value: ${expected_value:.2f}")


def display_position_result(result):
    """Display position sizing result."""
    st.markdown("---")
    st.markdown("### Position Details")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Shares", f"{result.shares:,}")
    with col2:
        st.metric("Position Size", f"${result.dollar_amount:,.2f}")
    with col3:
        st.metric("Portfolio %", f"{result.position_pct:.1%}")
    with col4:
        st.metric("Risk Amount", f"${result.risk_amount:,.2f}")

    # Additional details
    if result.details:
        st.markdown("**Details**")
        details_df = pd.DataFrame([
            {"Metric": k, "Value": f"{v:.4f}" if isinstance(v, float) else str(v)}
            for k, v in result.details.items()
            if k != 'error'
        ])
        if not details_df.empty:
            st.dataframe(details_df, use_container_width=True, hide_index=True)


def render_correlation_matrix_tab():
    """Render the correlation matrix tab."""
    st.subheader("Portfolio Correlation Analysis")

    st.info("Enter multiple symbols to analyze correlations and concentration risk.")

    # Symbol input
    symbols_input = st.text_area(
        "Symbols (comma-separated)",
        value="AAPL, MSFT, GOOGL, AMZN, NVDA",
        help="Enter stock symbols separated by commas"
    )

    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

    if len(symbols) < 2:
        st.warning("Enter at least 2 symbols to analyze correlations.")
        return

    col1, col2 = st.columns(2)
    with col1:
        lookback_days = st.selectbox(
            "Lookback Period",
            options=[30, 60, 90, 180, 365],
            index=2,
            key="corr_lookback"
        )
    with col2:
        max_corr = st.slider(
            "High Correlation Threshold",
            min_value=0.5,
            max_value=0.9,
            value=0.7,
            step=0.05
        )

    if st.button("Analyze Correlations", key="analyze_corr"):
        with st.spinner("Fetching price data..."):
            # Fetch data for all symbols
            price_data = {}
            yahoo_fetcher = YahooFetcher()
            coingecko_fetcher = CoinGeckoFetcher()

            progress_bar = st.progress(0)
            for i, symbol in enumerate(symbols):
                if is_crypto_symbol(symbol):
                    prices = coingecko_fetcher.get_historical_prices(symbol, days=lookback_days)
                else:
                    prices = yahoo_fetcher.get_historical_prices(symbol, days=lookback_days)

                if prices:
                    price_data[symbol] = prices

                progress_bar.progress((i + 1) / len(symbols))

            progress_bar.empty()

        if len(price_data) < 2:
            st.error("Could not fetch data for enough symbols.")
            return

        # Calculate correlations
        analyzer = CorrelationAnalyzer()
        corr_result = analyzer.calculate_correlation_matrix(price_data)

        # Display correlation matrix
        st.markdown("### Correlation Matrix")
        if corr_result['matrix']:
            matrix_df = pd.DataFrame(corr_result['matrix'])
            st.dataframe(
                matrix_df.style.background_gradient(cmap='RdYlGn', vmin=-1, vmax=1),
                use_container_width=True
            )

        # Highly correlated pairs
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Highly Correlated Pairs")
            if corr_result['highly_correlated']:
                for pair in corr_result['highly_correlated']:
                    st.warning(
                        f"{pair['pair'][0]} - {pair['pair'][1]}: {pair['correlation']:.2f}"
                    )
            else:
                st.success("No highly correlated pairs found.")

        with col2:
            st.markdown("### Negatively Correlated")
            if corr_result['negatively_correlated']:
                for pair in corr_result['negatively_correlated']:
                    st.info(
                        f"{pair['pair'][0]} - {pair['pair'][1]}: {pair['correlation']:.2f}"
                    )
            else:
                st.info("No negatively correlated pairs found.")

        # Concentration risk (mock holdings)
        st.markdown("---")
        st.markdown("### Concentration Risk Analysis")
        st.caption("Enter position values to analyze concentration risk:")

        holdings = {}
        cols = st.columns(min(5, len(symbols)))
        for i, symbol in enumerate(symbols[:10]):
            with cols[i % 5]:
                holdings[symbol] = st.number_input(
                    f"{symbol} ($)",
                    min_value=0.0,
                    value=10000.0,
                    step=1000.0,
                    key=f"holding_{symbol}"
                )

        if st.button("Analyze Concentration", key="analyze_conc"):
            concentration = analyzer.check_portfolio_concentration(
                holdings, corr_result['matrix'], max_corr
            )

            # Display risk level
            risk_level = concentration['concentration_risk']
            if risk_level == 'high':
                st.error(f"Concentration Risk: HIGH")
            elif risk_level == 'medium':
                st.warning(f"Concentration Risk: MEDIUM")
            else:
                st.success(f"Concentration Risk: LOW")

            # Correlated groups
            if concentration['correlated_groups']:
                st.markdown("**Correlated Groups:**")
                for group in concentration['correlated_groups']:
                    st.write(
                        f"- {', '.join(group['symbols'])}: "
                        f"${group['total_value']:,.0f} ({group['pct_of_portfolio']:.1%} of portfolio)"
                    )

            # Recommendations
            if concentration['recommendations']:
                st.markdown("**Recommendations:**")
                for rec in concentration['recommendations']:
                    st.info(rec)


def render_exit_strategies_tab():
    """Render the exit strategies tab."""
    st.subheader("Exit Strategy Evaluation")

    # Initialize manager
    config = {
        'trailing_stop_pct': RISK_MANAGEMENT_CONFIG.TRAILING_STOP_PCT,
        'max_holding_days': RISK_MANAGEMENT_CONFIG.MAX_HOLDING_DAYS
    }
    manager = ExitStrategyManager(config)

    st.markdown("### Position Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        entry_price = st.number_input(
            "Entry Price ($)",
            min_value=0.01,
            value=100.0,
            step=0.01,
            key="exit_entry"
        )

    with col2:
        current_price = st.number_input(
            "Current Price ($)",
            min_value=0.01,
            value=110.0,
            step=0.01,
            key="exit_current"
        )

    with col3:
        high_since_entry = st.number_input(
            "High Since Entry ($)",
            min_value=current_price,
            value=max(current_price, entry_price * 1.15),
            step=0.01,
            key="exit_high"
        )

    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input(
            "Entry Date",
            value=datetime.now() - timedelta(days=30),
            key="exit_entry_date"
        )
    with col2:
        current_date = st.date_input(
            "Current Date",
            value=datetime.now(),
            key="exit_current_date"
        )

    st.markdown("---")
    st.markdown("### Exit Strategy Parameters")

    col1, col2, col3 = st.columns(3)
    with col1:
        trailing_pct = st.slider(
            "Trailing Stop %",
            min_value=5,
            max_value=25,
            value=10,
            key="trailing_pct"
        ) / 100

    with col2:
        profit_target_pct = st.slider(
            "Profit Target %",
            min_value=10,
            max_value=100,
            value=20,
            key="profit_target"
        ) / 100

    with col3:
        max_days = st.number_input(
            "Max Holding Days",
            min_value=7,
            max_value=365,
            value=90,
            key="max_days"
        )

    if st.button("Evaluate Exit Strategies", key="evaluate_exits"):
        # Convert dates
        entry_dt = datetime.combine(entry_date, datetime.min.time())
        current_dt = datetime.combine(current_date, datetime.min.time())

        # Evaluate all exits
        exits = manager.evaluate_all_exits(
            entry_price=entry_price,
            current_price=current_price,
            high_since_entry=high_since_entry,
            entry_date=entry_dt,
            current_date=current_dt,
            profit_targets=[profit_target_pct]
        )

        # Also check individual strategies
        trailing = manager.trailing_stop(entry_price, current_price, high_since_entry, trailing_pct)
        profit = manager.profit_target(entry_price, current_price, profit_target_pct)
        time_exit = manager.time_based_exit(entry_dt, current_dt, max_days)

        st.markdown("---")
        st.markdown("### Exit Strategy Status")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Trailing Stop**")
            if trailing.should_exit:
                st.error("TRIGGERED")
            else:
                st.success("Not Triggered")

            st.caption(f"Stop Level: ${trailing.details.get('stop_level', 0):.4f}")
            st.caption(f"Distance: {trailing.details.get('distance_to_stop_pct', 0):.1f}%")

        with col2:
            st.markdown("**Profit Target**")
            if profit.should_exit:
                st.success("REACHED")
            else:
                st.info("Not Reached")

            st.caption(f"Target: ${profit.details.get('target_price', 0):.4f}")
            st.caption(f"To Target: {profit.details.get('distance_to_target_pct', 0):.1f}%")

        with col3:
            st.markdown("**Time-Based Exit**")
            if time_exit.should_exit:
                st.warning("TIME LIMIT")
            else:
                st.success("Within Limit")

            st.caption(f"Days Held: {time_exit.details.get('days_held', 0)}")
            st.caption(f"Days Remaining: {time_exit.details.get('days_remaining', 0)}")

        # P&L Summary
        st.markdown("---")
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        pnl_dollar = current_price - entry_price

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Unrealized P&L %", f"{pnl_pct:.2f}%")
        with col2:
            st.metric("Unrealized P&L $", f"${pnl_dollar:.2f}")
        with col3:
            from_high = ((high_since_entry - current_price) / high_since_entry) * 100
            st.metric("From High", f"-{from_high:.2f}%")

        # Recommendation
        st.markdown("---")
        if exits:
            st.error(f"EXIT SIGNAL: {exits[0].reason.value.upper()}")
        elif pnl_pct >= profit_target_pct * 100 * 0.8:
            st.warning("Consider taking partial profits - near target")
        elif pnl_pct < 0:
            st.info("Position underwater - monitor stop levels")
        else:
            st.success("Position healthy - no exit signals")


def render_sector_rotation_tab():
    """Render the sector rotation tab."""
    st.subheader("Sector Rotation Analysis")

    st.info("Analyze sector momentum for rotation strategies using sector ETFs.")

    # Sector ETFs
    sector_etfs = {
        'XLF': 'Financials',
        'XLK': 'Technology',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'XLI': 'Industrials',
        'XLY': 'Consumer Disc.',
        'XLP': 'Consumer Staples',
        'XLU': 'Utilities',
        'XLB': 'Materials',
        'XLRE': 'Real Estate'
    }

    # Select sectors to analyze
    selected_sectors = st.multiselect(
        "Select Sectors",
        options=list(sector_etfs.keys()),
        default=list(sector_etfs.keys())[:6],
        format_func=lambda x: f"{x} ({sector_etfs[x]})"
    )

    if len(selected_sectors) < 2:
        st.warning("Select at least 2 sectors to analyze.")
        return

    lookback = st.selectbox(
        "Lookback Period",
        options=[30, 60, 90, 180],
        index=2,
        key="sector_lookback"
    )

    if st.button("Analyze Sector Momentum", key="analyze_sectors"):
        with st.spinner("Fetching sector data..."):
            yahoo_fetcher = YahooFetcher()
            sector_returns = {}

            progress_bar = st.progress(0)
            for i, etf in enumerate(selected_sectors):
                prices = yahoo_fetcher.get_historical_prices(etf, days=lookback + 10)

                if prices and len(prices) > 1:
                    # Calculate daily returns
                    price_vals = [p[1] for p in prices]
                    returns = [
                        (price_vals[j] - price_vals[j-1]) / price_vals[j-1]
                        for j in range(1, len(price_vals))
                    ]
                    sector_returns[etf] = returns

                progress_bar.progress((i + 1) / len(selected_sectors))
            progress_bar.empty()

        if len(sector_returns) < 2:
            st.error("Could not fetch data for enough sectors.")
            return

        # Analyze momentum
        analyzer = SectorRotationAnalyzer()
        momentum = analyzer.calculate_sector_momentum(sector_returns)

        # Display rankings
        st.markdown("### Sector Momentum Rankings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Leaders (Top 3)**")
            for sector in momentum['leaders']:
                score = momentum['momentum_scores'].get(sector, 0)
                st.success(f"{sector} ({sector_etfs.get(sector, '')}): {score:.2f}")

        with col2:
            st.markdown("**Laggards (Bottom 3)**")
            for sector in momentum['laggards']:
                score = momentum['momentum_scores'].get(sector, 0)
                st.error(f"{sector} ({sector_etfs.get(sector, '')}): {score:.2f}")

        # Detailed rankings table
        st.markdown("---")
        st.markdown("### Momentum by Period")

        periods_data = []
        for period, rankings in momentum['rankings'].items():
            for rank, (sector, ret) in enumerate(rankings, 1):
                periods_data.append({
                    'Period': f"{period}D",
                    'Rank': rank,
                    'Sector': sector,
                    'Return': f"{ret*100:.2f}%"
                })

        if periods_data:
            periods_df = pd.DataFrame(periods_data)
            st.dataframe(
                periods_df.pivot(index='Sector', columns='Period', values='Rank'),
                use_container_width=True
            )

        # Allocation suggestion
        st.markdown("---")
        st.markdown("### Suggested Allocation")

        # Mock current allocation
        current_allocation = {s: 1/len(selected_sectors) for s in selected_sectors}

        suggestion = analyzer.suggest_sector_allocation(
            current_allocation, momentum, target_positions=5
        )

        # Display suggested allocation
        alloc_df = pd.DataFrame([
            {
                'Sector': s,
                'Name': sector_etfs.get(s, ''),
                'Suggested %': f"{v*100:.1f}%"
            }
            for s, v in suggestion['suggested_allocation'].items()
        ])
        st.dataframe(alloc_df, use_container_width=True, hide_index=True)

        # Changes needed
        if suggestion['changes']:
            st.markdown("**Recommended Changes:**")
            for change in suggestion['changes']:
                if change['action'] == 'add':
                    st.success(f"ADD {change['sector']} - Target: {change['target_pct']:.1f}%")
                elif change['action'] == 'remove':
                    st.error(f"REMOVE {change['sector']} - Current: {change['current_pct']:.1f}%")
                else:
                    st.info(
                        f"REBALANCE {change['sector']}: "
                        f"{change['current_pct']:.1f}% -> {change['target_pct']:.1f}%"
                    )


def render_risk_metrics_tab():
    """Render the portfolio risk metrics tab."""
    st.subheader("Portfolio Risk Metrics")

    st.info("Calculate comprehensive risk metrics for your portfolio or individual positions.")

    # Input method
    input_method = st.radio(
        "Data Input Method",
        options=["Enter Symbol", "Manual Returns"],
        horizontal=True
    )

    if input_method == "Enter Symbol":
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input(
                "Symbol",
                value="SPY",
                key="risk_symbol"
            ).upper()

        with col2:
            lookback = st.selectbox(
                "Lookback Period",
                options=[90, 180, 365, 730],
                index=2,
                key="risk_lookback"
            )

        if st.button("Calculate Risk Metrics", key="calc_risk"):
            with st.spinner("Fetching data and calculating metrics..."):
                # Fetch data
                if is_crypto_symbol(symbol):
                    fetcher = CoinGeckoFetcher()
                else:
                    fetcher = YahooFetcher()

                prices = fetcher.get_historical_prices(symbol, days=lookback)

                if not prices or len(prices) < 30:
                    st.error(f"Insufficient data for {symbol}")
                    return

                # Calculate returns
                price_vals = [p[1] for p in prices]
                returns = [
                    (price_vals[i] - price_vals[i-1]) / price_vals[i-1]
                    for i in range(1, len(price_vals))
                ]

                # Build equity curve
                equity = [1.0]
                for r in returns:
                    equity.append(equity[-1] * (1 + r))

                # Calculate metrics
                calculator = PortfolioRiskCalculator(
                    risk_free_rate=RISK_MANAGEMENT_CONFIG.RISK_FREE_RATE
                )
                metrics = calculator.calculate_all_metrics(returns, equity)

                display_risk_metrics(metrics, symbol)

    else:
        st.markdown("### Manual Return Entry")
        st.caption("Enter comma-separated daily returns (as decimals, e.g., 0.01 for 1%)")

        returns_input = st.text_area(
            "Daily Returns",
            value="0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.012",
            key="manual_returns"
        )

        try:
            returns = [float(r.strip()) for r in returns_input.split(",") if r.strip()]

            if len(returns) < 10:
                st.warning("Enter at least 10 returns for meaningful analysis.")
            else:
                if st.button("Calculate Metrics", key="calc_manual"):
                    # Build equity curve
                    equity = [1.0]
                    for r in returns:
                        equity.append(equity[-1] * (1 + r))

                    calculator = PortfolioRiskCalculator()
                    metrics = calculator.calculate_all_metrics(returns, equity)

                    display_risk_metrics(metrics, "Custom Portfolio")

        except ValueError:
            st.error("Invalid return format. Use comma-separated decimal values.")


def display_risk_metrics(metrics, title: str):
    """Display calculated risk metrics."""
    st.markdown(f"### Risk Metrics for {title}")

    # VaR and CVaR
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "VaR (95%)",
            f"{metrics.var_95:.2%}",
            help="Maximum expected loss with 95% confidence (daily)"
        )

    with col2:
        st.metric(
            "VaR (99%)",
            f"{metrics.var_99:.2%}",
            help="Maximum expected loss with 99% confidence (daily)"
        )

    with col3:
        st.metric(
            "CVaR (95%)",
            f"{metrics.cvar_95:.2%}",
            help="Expected loss when VaR is exceeded"
        )

    with col4:
        st.metric(
            "Volatility",
            f"{metrics.volatility:.2%}",
            help="Annualized volatility"
        )

    st.markdown("---")

    # Risk-adjusted returns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sharpe_color = "normal" if metrics.sharpe_ratio > 1 else "inverse"
        st.metric(
            "Sharpe Ratio",
            f"{metrics.sharpe_ratio:.2f}",
            help="Risk-adjusted return (>1 is good, >2 is excellent)"
        )

    with col2:
        st.metric(
            "Sortino Ratio",
            f"{metrics.sortino_ratio:.2f}",
            help="Downside risk-adjusted return"
        )

    with col3:
        st.metric(
            "Max Drawdown",
            f"{metrics.max_drawdown:.2%}",
            help="Largest peak-to-trough decline"
        )

    with col4:
        st.metric(
            "DD Duration",
            f"{metrics.max_drawdown_duration} days",
            help="Length of maximum drawdown period"
        )

    # Beta and Alpha if available
    if metrics.beta is not None or metrics.alpha is not None:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if metrics.beta is not None:
                st.metric(
                    "Beta",
                    f"{metrics.beta:.2f}",
                    help="Sensitivity to market movements"
                )

        with col2:
            if metrics.alpha is not None:
                st.metric(
                    "Alpha",
                    f"{metrics.alpha:.2%}",
                    help="Excess return vs benchmark"
                )

    # Interpretation
    st.markdown("---")
    st.markdown("### Risk Assessment")

    assessments = []

    if metrics.sharpe_ratio >= 2:
        assessments.append(("Sharpe Ratio", "Excellent risk-adjusted returns", "success"))
    elif metrics.sharpe_ratio >= 1:
        assessments.append(("Sharpe Ratio", "Good risk-adjusted returns", "info"))
    elif metrics.sharpe_ratio >= 0:
        assessments.append(("Sharpe Ratio", "Moderate risk-adjusted returns", "warning"))
    else:
        assessments.append(("Sharpe Ratio", "Poor risk-adjusted returns", "error"))

    if metrics.max_drawdown < 0.1:
        assessments.append(("Drawdown", "Low maximum drawdown (<10%)", "success"))
    elif metrics.max_drawdown < 0.2:
        assessments.append(("Drawdown", "Moderate maximum drawdown (10-20%)", "info"))
    elif metrics.max_drawdown < 0.3:
        assessments.append(("Drawdown", "Elevated maximum drawdown (20-30%)", "warning"))
    else:
        assessments.append(("Drawdown", "High maximum drawdown (>30%)", "error"))

    if metrics.volatility < 0.15:
        assessments.append(("Volatility", "Low volatility (<15%)", "success"))
    elif metrics.volatility < 0.25:
        assessments.append(("Volatility", "Moderate volatility (15-25%)", "info"))
    else:
        assessments.append(("Volatility", "High volatility (>25%)", "warning"))

    for metric, msg, level in assessments:
        if level == "success":
            st.success(f"**{metric}:** {msg}")
        elif level == "info":
            st.info(f"**{metric}:** {msg}")
        elif level == "warning":
            st.warning(f"**{metric}:** {msg}")
        else:
            st.error(f"**{metric}:** {msg}")


# Entry point for the page
if __name__ == "__main__":
    st.set_page_config(
        page_title="Risk Management",
        page_icon="shield",
        layout="wide"
    )
    render_risk_management_page()
