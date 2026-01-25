"""
Home Dashboard Component
Modern, stylish home page with market overview and top performers
"""
import streamlit as st
import pandas as pd
from typing import List, Dict
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

    /* Top performer card */
    .performer-card {
        background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid var(--accent-blue);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .performer-card::before {
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

    .performer-card:hover::before {
        opacity: 1;
    }

    .performer-card:hover {
        transform: translateX(4px);
        box-shadow: -4px 0 20px rgba(67, 97, 238, 0.3);
    }

    .performer-card.buy { border-left-color: var(--accent-green); }
    .performer-card.base { border-left-color: var(--accent-yellow); }
    .performer-card.watch { border-left-color: var(--accent-red); }

    .performer-symbol {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .performer-score {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--accent-cyan);
        margin: 0.25rem 0;
    }

    .performer-details {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: var(--text-secondary);
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

    /* State badges */
    .state-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .state-badge.buy {
        background: rgba(6, 214, 160, 0.2);
        color: var(--accent-green);
        border: 1px solid var(--accent-green);
    }

    .state-badge.base {
        background: rgba(255, 214, 10, 0.2);
        color: var(--accent-yellow);
        border: 1px solid var(--accent-yellow);
    }

    .state-badge.watch {
        background: rgba(239, 71, 111, 0.2);
        color: var(--accent-red);
        border: 1px solid var(--accent-red);
    }

    /* Filter container */
    .filter-container {
        background: var(--glass-bg);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid var(--glass-border);
    }

    /* Data table styling */
    .dataframe {
        background: var(--bg-card) !important;
        border-radius: 12px !important;
    }

    /* Divider */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
        margin: 2rem 0;
    }

    /* Quick action buttons */
    .quick-action {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .quick-action:hover {
        border-color: var(--accent-blue);
        box-shadow: 0 4px 20px rgba(67, 97, 238, 0.2);
    }

    .quick-action-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }

    .quick-action-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    </style>
    """, unsafe_allow_html=True)


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

    if not data:
        st.error("No data available")
        return

    # Calculate summary statistics
    avg_score = sum(item.get('total_score', item.get('investment_score', 0)) for item in data) / len(data) if data else 0
    buy_count = sum(1 for item in data if item.get('current_state') == 'BUY')
    base_count = sum(1 for item in data if item.get('current_state') == 'BASE')
    watch_count = sum(1 for item in data if item.get('current_state') == 'WATCH')
    top_score = max((item.get('total_score', item.get('investment_score', 0)) for item in data), default=0)

    # ===== Market Overview Section =====
    st.markdown('<div class="section-header">📊 Market Overview</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="section-header">🏆 Top 10 Performers</div>', unsafe_allow_html=True)

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
                <div class="performer-card {state_class}" style="position: relative;">
                    <div class="rank-badge">#{rank}</div>
                    <div class="performer-symbol">{state_emoji} {symbol}</div>
                    <div class="performer-score">{score:.1f}</div>
                    <div class="performer-details">
                        <span>${price:,.2f}</span>
                        <span class="state-badge {state_class}">{state}</span>
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
    st.markdown('<div class="section-header">📋 All Stocks</div>', unsafe_allow_html=True)

    # Advanced filtering
    with st.expander("🔍 Advanced Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_state = st.multiselect("Filter by State", ["BUY", "BASE", "WATCH", "NORMAL"], default=[])
        with col2:
            categories_list = list(set(item.get('category', 'Other') for item in data))
            filter_category = st.multiselect("Filter by Category", categories_list, default=[])
        with col3:
            score_range = st.slider("Score Range", 0, 100, (0, 100))
        with col4:
            search_query = st.text_input("🔎 Search", "", placeholder="Symbol or category...")

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

    st.info(f"Showing **{len(filtered_data)}** of {len(data)} stocks")

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
        st.warning("No stocks match the current filters")

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

    # ===== Metrics Heatmap =====
    st.markdown('<div class="section-header">🔥 Top 20 Metrics Heatmap</div>', unsafe_allow_html=True)
    top_20 = sorted(data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True)[:20]
    try:
        metrics_fig = create_metrics_heatmap(top_20)
        metrics_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#b0b0b0'
        )
        st.plotly_chart(metrics_fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not create heatmap: {e}")

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ===== Export Section =====
    st.markdown('<div class="section-header">📥 Export Data</div>', unsafe_allow_html=True)
    create_export_buttons(filtered_data, filename_prefix="investment_analysis")
