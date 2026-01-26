"""
Home Dashboard Component
Modern, stylish home page with market overview, screening, and recommendations
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from streamlit_components.chart_components import (
    create_score_distribution_chart,
    create_donut_chart,
    create_metrics_heatmap
)
from streamlit_components.export_components import create_export_buttons


def inject_custom_css():
    """Inject custom CSS for modern styling."""
    st.markdown("""
    <style>
    /* Dark theme variables */
    :root {
        --bg-primary: #0f0f23;
        --bg-secondary: #1a1a2e;
        --bg-card: #16213e;
        --accent-blue: #4361ee;
        --accent-purple: #7209b7;
        --accent-pink: #f72585;
        --accent-cyan: #4cc9f0;
        --accent-green: #06d6a0;
        --accent-yellow: #ffd60a;
        --accent-red: #ef476f;
        --accent-orange: #ff9500;
        --text-primary: #ffffff;
        --text-secondary: #b0b0b0;
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
    }

    /* Main header styling */
    .main-title {
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 50%, var(--accent-pink) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
        letter-spacing: -1px;
    }

    /* Glass card effect */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(67, 97, 238, 0.15);
        border-color: var(--accent-blue);
    }

    /* Metric card */
    .metric-card {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        border-radius: 16px;
        padding: 1.25rem;
        text-align: center;
        border: 1px solid var(--glass-border);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 20px rgba(67, 97, 238, 0.2);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }

    /* Recommendation card */
    .rec-card {
        background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid var(--accent-blue);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .rec-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, transparent 0%, rgba(67, 97, 238, 0.05) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .rec-card:hover::before {
        opacity: 1;
    }

    .rec-card:hover {
        transform: translateX(4px);
        box-shadow: -4px 0 20px rgba(67, 97, 238, 0.3);
    }

    .rec-card.strong-buy { border-left-color: var(--accent-green); }
    .rec-card.buy { border-left-color: var(--accent-cyan); }
    .rec-card.hold { border-left-color: var(--accent-yellow); }
    .rec-card.watch { border-left-color: var(--accent-orange); }
    .rec-card.avoid { border-left-color: var(--accent-red); }

    .rec-symbol {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .rec-score {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--accent-cyan);
        margin: 0.25rem 0;
    }

    .rec-details {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    /* Recommendation badge */
    .rec-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    .rec-badge.strong-buy {
        background: linear-gradient(135deg, var(--accent-green), var(--accent-cyan));
        color: #000;
    }

    .rec-badge.buy {
        background: rgba(76, 201, 240, 0.3);
        color: var(--accent-cyan);
        border: 1px solid var(--accent-cyan);
    }

    .rec-badge.hold {
        background: rgba(255, 214, 10, 0.2);
        color: var(--accent-yellow);
        border: 1px solid var(--accent-yellow);
    }

    .rec-badge.watch {
        background: rgba(255, 149, 0, 0.2);
        color: var(--accent-orange);
        border: 1px solid var(--accent-orange);
    }

    .rec-badge.avoid {
        background: rgba(239, 71, 111, 0.2);
        color: var(--accent-red);
        border: 1px solid var(--accent-red);
    }

    /* Rank badge */
    .rank-badge {
        position: absolute;
        top: -5px;
        right: 10px;
        background: linear-gradient(135deg, var(--accent-purple) 0%, var(--accent-pink) 100%);
        color: white;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.25rem 0.5rem;
        border-radius: 0 0 8px 8px;
    }

    /* Category badge */
    .category-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        font-size: 0.65rem;
        font-weight: 600;
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        color: var(--text-secondary);
        margin-right: 0.25rem;
    }

    /* Signal tag */
    .signal-tag {
        display: inline-block;
        padding: 0.15rem 0.4rem;
        border-radius: 8px;
        font-size: 0.6rem;
        font-weight: 500;
        background: rgba(67, 97, 238, 0.2);
        color: var(--accent-blue);
        margin: 0.1rem;
    }

    /* Section header */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--glass-border);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Sub-section header */
    .sub-header {
        font-size: 1rem;
        font-weight: 600;
        color: var(--accent-cyan);
        margin: 1rem 0 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Stats bar */
    .stats-container {
        background: var(--glass-bg);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    .stats-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--glass-border);
    }

    .stats-row:last-child {
        border-bottom: none;
    }

    .stats-label {
        color: var(--text-secondary);
        font-size: 0.85rem;
    }

    .stats-value {
        color: var(--text-primary);
        font-weight: 600;
    }

    .stats-bar {
        height: 6px;
        background: var(--bg-secondary);
        border-radius: 3px;
        overflow: hidden;
        margin-top: 0.25rem;
    }

    .stats-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    .stats-bar-fill.excellent { background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan)); }
    .stats-bar-fill.good { background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)); }
    .stats-bar-fill.average { background: linear-gradient(90deg, var(--accent-yellow), #ff9500); }
    .stats-bar-fill.below { background: linear-gradient(90deg, var(--accent-red), var(--accent-pink)); }

    /* Divider */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
        margin: 2rem 0;
    }

    /* Score breakdown mini */
    .score-mini {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }

    .score-mini-item {
        flex: 1;
        text-align: center;
        padding: 0.25rem;
        background: var(--glass-bg);
        border-radius: 6px;
        font-size: 0.65rem;
    }

    .score-mini-value {
        font-weight: 700;
        color: var(--accent-cyan);
    }

    .score-mini-label {
        color: var(--text-secondary);
        font-size: 0.55rem;
    }

    /* Screening progress */
    .screening-status {
        background: var(--glass-bg);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .screening-status-icon {
        font-size: 1.5rem;
    }

    .screening-status-text {
        flex: 1;
    }

    .screening-status-title {
        font-weight: 600;
        color: var(--text-primary);
    }

    .screening-status-detail {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    </style>
    """, unsafe_allow_html=True)


def run_unified_screening(symbols: List[str] = None) -> Optional[Dict]:
    """Run unified screening on stock universe."""
    try:
        from screeners.unified_screener import UnifiedScreener, DEFAULT_SCREENING_UNIVERSE
        from api.yahoo_fetcher import YahooFetcher

        if symbols is None:
            symbols = DEFAULT_SCREENING_UNIVERSE

        fetcher = YahooFetcher()
        screener = UnifiedScreener(fetcher)

        return screener.get_top_recommendations(symbols, top_n=10)

    except Exception as e:
        st.error(f"Screening error: {e}")
        return None


def render_recommendation_card(score, rank: int, category: str = "overall"):
    """Render a single recommendation card."""
    rec_class = score.recommendation.lower().replace('_', '-')
    rec_emoji = {
        'STRONG_BUY': '🚀',
        'BUY': '📈',
        'HOLD': '📊',
        'WATCH': '👀',
        'AVOID': '⚠️'
    }.get(score.recommendation, '📊')

    # Format signals
    signals_html = ""
    for signal in score.key_signals[:3]:
        signals_html += f'<span class="signal-tag">{signal}</span>'

    st.markdown(f"""
    <div class="rec-card {rec_class}" style="position: relative;">
        <div class="rank-badge">#{rank}</div>
        <div class="rec-symbol">
            {rec_emoji} {score.symbol}
            <span class="category-badge">{score.sector or score.category}</span>
        </div>
        <div class="rec-score">{score.unified_score:.1f}</div>
        <div class="rec-details">
            <span>${score.current_price:,.2f}</span>
            <span class="rec-badge {rec_class}">{score.recommendation.replace('_', ' ')}</span>
        </div>
        <div class="score-mini">
            <div class="score-mini-item">
                <div class="score-mini-value">{score.ten_bagger_score:.0f}</div>
                <div class="score-mini-label">10-Bag</div>
            </div>
            <div class="score-mini-item">
                <div class="score-mini-value">{score.rs_rating}</div>
                <div class="score-mini-label">RS</div>
            </div>
            <div class="score-mini-item">
                <div class="score-mini-value">{score.deep_bottom_score:.0f}</div>
                <div class="score-mini-label">Value</div>
            </div>
            <div class="score-mini-item">
                <div class="score-mini-value">{score.fundamental_score:.0f}</div>
                <div class="score-mini-label">Fund</div>
            </div>
        </div>
        <div style="margin-top: 0.5rem;">
            {signals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_screening_section():
    """Render the comprehensive screening section."""
    st.markdown('<div class="section-header">🎯 Smart Stock Screening</div>', unsafe_allow_html=True)

    # Screening options
    col1, col2 = st.columns([3, 1])

    with col1:
        screening_mode = st.selectbox(
            "Screening Universe",
            ["Default Universe (70 stocks)", "Custom Symbols", "Tech Focus", "Value Focus"],
            key="screening_mode"
        )

    with col2:
        run_screening = st.button("🔍 Run Screening", use_container_width=True, type="primary")

    custom_symbols = None
    if screening_mode == "Custom Symbols":
        custom_input = st.text_input(
            "Enter symbols (comma-separated)",
            placeholder="AAPL, MSFT, GOOGL, NVDA..."
        )
        if custom_input:
            custom_symbols = [s.strip().upper() for s in custom_input.split(',')]

    if run_screening or st.session_state.get('screening_results') is not None:
        if run_screening:
            with st.spinner("🔄 Analyzing stocks from all perspectives..."):
                # Determine symbols based on mode
                if screening_mode == "Tech Focus":
                    symbols = [
                        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
                        'AMD', 'AVGO', 'QCOM', 'CRM', 'NOW', 'SNOW', 'NET',
                        'DDOG', 'ZS', 'CRWD', 'PANW', 'SHOP', 'PLTR', 'AI'
                    ]
                elif screening_mode == "Value Focus":
                    symbols = [
                        'JPM', 'BAC', 'GS', 'V', 'MA', 'JNJ', 'PFE', 'ABBV',
                        'XOM', 'CVX', 'CAT', 'DE', 'WMT', 'COST', 'TGT',
                        'DIS', 'NKE', 'SBUX', 'MCD', 'KO', 'PEP'
                    ]
                elif custom_symbols:
                    symbols = custom_symbols
                else:
                    symbols = None  # Use default

                results = run_unified_screening(symbols)
                st.session_state['screening_results'] = results

        results = st.session_state.get('screening_results')

        if results:
            # Display screening status
            total_screened = len(results.get('overall', []))
            strong_buys = len(results.get('strong_buys', []))

            st.markdown(f"""
            <div class="screening-status">
                <div class="screening-status-icon">✅</div>
                <div class="screening-status-text">
                    <div class="screening-status-title">Screening Complete</div>
                    <div class="screening-status-detail">
                        Analyzed {total_screened} stocks • Found {strong_buys} Strong Buy signals
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Create tabs for different perspectives
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🏆 Top Overall",
                "🚀 Growth (10-Bagger)",
                "📈 Momentum Leaders",
                "💎 Deep Value",
                "🔄 Recovery Plays"
            ])

            with tab1:
                st.markdown('<div class="sub-header">🏆 Top Recommendations by Unified Score</div>', unsafe_allow_html=True)
                overall = results.get('overall', [])
                if overall:
                    cols = st.columns(2)
                    for idx, score in enumerate(overall[:10]):
                        with cols[idx % 2]:
                            render_recommendation_card(score, idx + 1, "overall")
                else:
                    st.info("No recommendations available")

            with tab2:
                st.markdown('<div class="sub-header">🚀 Ten Bagger Candidates (High Growth Potential)</div>', unsafe_allow_html=True)
                growth = results.get('growth', [])
                if growth:
                    cols = st.columns(2)
                    for idx, score in enumerate(growth[:10]):
                        with cols[idx % 2]:
                            render_recommendation_card(score, idx + 1, "growth")
                else:
                    st.info("No growth candidates found")

            with tab3:
                st.markdown('<div class="sub-header">📈 Momentum Leaders (High Relative Strength)</div>', unsafe_allow_html=True)
                momentum = results.get('momentum', [])
                if momentum:
                    cols = st.columns(2)
                    for idx, score in enumerate(momentum[:10]):
                        with cols[idx % 2]:
                            render_recommendation_card(score, idx + 1, "momentum")
                else:
                    st.info("No momentum leaders found")

            with tab4:
                st.markdown('<div class="sub-header">💎 Deep Value Plays (Significant Drawdown + Strong Fundamentals)</div>', unsafe_allow_html=True)
                value = results.get('value', [])
                if value:
                    cols = st.columns(2)
                    for idx, score in enumerate(value[:10]):
                        with cols[idx % 2]:
                            render_recommendation_card(score, idx + 1, "value")
                else:
                    st.info("No deep value plays found")

            with tab5:
                st.markdown('<div class="sub-header">🔄 Recovery Candidates (Bottom Formation + Improving Momentum)</div>', unsafe_allow_html=True)
                recovery = results.get('recovery', [])
                if recovery:
                    cols = st.columns(2)
                    for idx, score in enumerate(recovery[:10]):
                        with cols[idx % 2]:
                            render_recommendation_card(score, idx + 1, "recovery")
                else:
                    st.info("No recovery candidates found")

            st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

            # Export screening results
            if results.get('overall'):
                st.markdown('<div class="sub-header">📥 Export Screening Results</div>', unsafe_allow_html=True)
                export_data = []
                for score in results.get('overall', []):
                    export_data.append({
                        'Symbol': score.symbol,
                        'Unified Score': score.unified_score,
                        'Recommendation': score.recommendation,
                        'Ten Bagger Score': score.ten_bagger_score,
                        'RS Rating': score.rs_rating,
                        'Deep Bottom Score': score.deep_bottom_score,
                        'Fundamental Score': score.fundamental_score,
                        'Price': score.current_price,
                        'Drawdown %': score.drawdown_pct,
                        'Sector': score.sector or 'N/A'
                    })
                create_export_buttons(export_data, filename_prefix="screening_results")


def render_home_dashboard(data: List[Dict]):
    """
    Render the home dashboard with modern styling.

    Args:
        data: List of investment analysis results
    """
    # Inject custom CSS
    inject_custom_css()

    # Main title
    st.markdown('<h1 class="main-title">Investment Analysis Dashboard</h1>', unsafe_allow_html=True)

    # ===== Smart Screening Section (NEW) =====
    render_screening_section()

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Existing Data Analysis =====
    if not data:
        st.info("Load your portfolio data to see additional analysis below.")
        return

    # Calculate summary statistics
    avg_score = sum(item.get('total_score', item.get('investment_score', 0)) for item in data) / len(data) if data else 0
    buy_count = sum(1 for item in data if item.get('current_state') == 'BUY')
    base_count = sum(1 for item in data if item.get('current_state') == 'BASE')
    watch_count = sum(1 for item in data if item.get('current_state') == 'WATCH')
    top_score = max((item.get('total_score', item.get('investment_score', 0)) for item in data), default=0)

    # ===== Market Overview Section =====
    st.markdown('<div class="section-header">📊 Portfolio Overview</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    metrics = [
        (col1, len(data), "Total Analyzed", "📈"),
        (col2, f"{avg_score:.1f}", "Avg Score", "⭐"),
        (col3, buy_count, "BUY Signals", "🟢"),
        (col4, base_count, "BASE Signals", "🟡"),
        (col5, watch_count, "WATCH Signals", "🔴"),
    ]

    for col, value, label, icon in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Top Performers Section =====
    st.markdown('<div class="section-header">🏆 Top 10 Portfolio Holdings</div>', unsafe_allow_html=True)

    top_10 = sorted(data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True)[:10]

    # Display in two rows of 5
    for row in range(2):
        cols = st.columns(5)
        for idx in range(5):
            item_idx = row * 5 + idx
            if item_idx >= len(top_10):
                break
            item = top_10[item_idx]
            col = cols[idx]

            with col:
                symbol = item.get('symbol', 'N/A')
                score = item.get('total_score', item.get('investment_score', 0))
                state = item.get('current_state', 'NORMAL')
                price = item.get('current_price', 0)
                rank = item_idx + 1

                state_class = state.lower() if state in ['BUY', 'BASE', 'WATCH'] else ''
                state_emoji = {'BUY': '🟢', 'BASE': '🟡', 'WATCH': '🔴', 'NORMAL': '⚪'}.get(state, '⚪')

                st.markdown(f"""
                <div class="rec-card {state_class}" style="position: relative;">
                    <div class="rank-badge">#{rank}</div>
                    <div class="rec-symbol">{state_emoji} {symbol}</div>
                    <div class="rec-score">{score:.1f}</div>
                    <div class="rec-details">
                        <span>${price:,.2f}</span>
                        <span class="rec-badge {state_class}">{state}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Quick Stats Section =====
    st.markdown('<div class="section-header">📈 Quick Stats</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        # Score Distribution
        score_dist = [
            ('Excellent (80+)', sum(1 for i in data if i.get('total_score', i.get('investment_score', 0)) >= 80), 'excellent'),
            ('Good (60-79)', sum(1 for i in data if 60 <= i.get('total_score', i.get('investment_score', 0)) < 80), 'good'),
            ('Average (40-59)', sum(1 for i in data if 40 <= i.get('total_score', i.get('investment_score', 0)) < 60), 'average'),
            ('Below Avg (<40)', sum(1 for i in data if i.get('total_score', i.get('investment_score', 0)) < 40), 'below'),
        ]

        st.markdown('<div class="stats-container">', unsafe_allow_html=True)
        st.markdown('<strong style="color: #fff; margin-bottom: 0.5rem; display: block;">Score Distribution</strong>', unsafe_allow_html=True)
        for label, count, style_class in score_dist:
            pct = count / len(data) * 100 if data else 0
            st.markdown(f"""
            <div class="stats-row">
                <span class="stats-label">{label}</span>
                <span class="stats-value">{count} ({pct:.0f}%)</span>
            </div>
            <div class="stats-bar">
                <div class="stats-bar-fill {style_class}" style="width: {pct}%;"></div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # State Distribution
        normal_count = len(data) - buy_count - base_count - watch_count
        state_dist = [
            ('🟢 BUY', buy_count, 'excellent'),
            ('🟡 BASE', base_count, 'average'),
            ('🔴 WATCH', watch_count, 'below'),
            ('⚪ NORMAL', normal_count, 'good'),
        ]

        st.markdown('<div class="stats-container">', unsafe_allow_html=True)
        st.markdown('<strong style="color: #fff; margin-bottom: 0.5rem; display: block;">Signal Distribution</strong>', unsafe_allow_html=True)
        for label, count, style_class in state_dist:
            pct = count / len(data) * 100 if data else 0
            st.markdown(f"""
            <div class="stats-row">
                <span class="stats-label">{label}</span>
                <span class="stats-value">{count} ({pct:.0f}%)</span>
            </div>
            <div class="stats-bar">
                <div class="stats-bar-fill {style_class}" style="width: {pct}%;"></div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        # Category breakdown
        categories = {}
        for item in data:
            cat = item.get('category', 'Other')
            categories[cat] = categories.get(cat, 0) + 1

        st.markdown('<div class="stats-container">', unsafe_allow_html=True)
        st.markdown('<strong style="color: #fff; margin-bottom: 0.5rem; display: block;">Category Breakdown</strong>', unsafe_allow_html=True)
        colors_list = ['excellent', 'good', 'average', 'below', 'excellent']
        for idx, (cat, count) in enumerate(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]):
            pct = count / len(data) * 100 if data else 0
            style_class = colors_list[idx % len(colors_list)]
            st.markdown(f"""
            <div class="stats-row">
                <span class="stats-label">{cat}</span>
                <span class="stats-value">{count}</span>
            </div>
            <div class="stats-bar">
                <div class="stats-bar-fill {style_class}" style="width: {pct}%;"></div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== All Stocks Table =====
    st.markdown('<div class="section-header">📋 All Holdings</div>', unsafe_allow_html=True)

    # Advanced filtering
    with st.expander("🔍 Advanced Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_state = st.multiselect("Filter by State", ["BUY", "BASE", "WATCH", "NORMAL"], default=[], key="home_filter_state")
        with col2:
            categories_list = list(set(item.get('category', 'Other') for item in data))
            filter_category = st.multiselect("Filter by Category", categories_list, default=[], key="home_filter_cat")
        with col3:
            score_range = st.slider("Score Range", 0, 100, (0, 100), key="home_score_range")
        with col4:
            search_query = st.text_input("🔎 Search", "", placeholder="Symbol or category...", key="home_search")

    # Apply filters
    filtered_data = data

    if filter_state:
        filtered_data = [item for item in filtered_data if item.get('current_state') in filter_state]

    if filter_category:
        filtered_data = [item for item in filtered_data if item.get('category') in filter_category]

    filtered_data = [item for item in filtered_data
                     if score_range[0] <= item.get('total_score', item.get('investment_score', 0)) <= score_range[1]]

    if search_query:
        search_lower = search_query.lower()
        filtered_data = [item for item in filtered_data
                        if search_lower in item.get('symbol', '').lower()
                        or search_lower in item.get('category', '').lower()
                        or search_lower in str(item.get('investment_stance', '')).lower()]

    st.info(f"Showing **{len(filtered_data)}** of {len(data)} holdings")

    # Create DataFrame
    df = pd.DataFrame([
        {
            'Rank': idx + 1,
            'Symbol': item.get('symbol', 'N/A'),
            'Category': item.get('category', 'Other'),
            'State': item.get('current_state', 'NORMAL'),
            'Score': round(item.get('total_score', item.get('investment_score', 0)), 1),
            'Value': round(item.get('value_score', 0), 1),
            'Momentum': round(item.get('momentum_score', 0), 1),
            'Stability': round(item.get('stability_score', 0), 1),
            'Price': f"${item.get('current_price', 0):,.2f}",
            'Stance': item.get('investment_stance', 'Hold')
        }
        for idx, item in enumerate(sorted(filtered_data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True))
    ])

    # Style the dataframe
    def highlight_state(val):
        colors = {
            'BUY': 'background-color: rgba(6, 214, 160, 0.3); color: #06d6a0;',
            'BASE': 'background-color: rgba(255, 214, 10, 0.3); color: #ffd60a;',
            'WATCH': 'background-color: rgba(239, 71, 111, 0.3); color: #ef476f;',
            'NORMAL': ''
        }
        return colors.get(val, '')

    if not df.empty:
        styled_df = df.style.applymap(highlight_state, subset=['State'])
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.warning("No holdings match the current filters")

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Charts Section =====
    st.markdown('<div class="section-header">📊 Charts & Visualizations</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        try:
            fig = create_score_distribution_chart(data)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#b0b0b0'
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create score distribution chart: {e}")

    with col2:
        # Category donut chart
        if categories:
            try:
                fig = create_donut_chart(
                    list(categories.keys()),
                    list(categories.values()),
                    "Category Distribution"
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#b0b0b0'
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not create category chart: {e}")

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Export Section =====
    st.markdown('<div class="section-header">📥 Export Portfolio Data</div>', unsafe_allow_html=True)
    create_export_buttons(filtered_data, filename_prefix="portfolio_analysis")
