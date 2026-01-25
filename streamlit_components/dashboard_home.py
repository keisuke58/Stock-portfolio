"""
Home Dashboard Component
Enhanced home page with market overview, top performers, and quick actions
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


def render_home_dashboard(data: List[Dict]):
    """
    Render the home dashboard with market overview and top stocks.

    Args:
        data: List of investment analysis results
    """
    st.markdown('<div class="main-header">📊 Investment Analysis Dashboard</div>', unsafe_allow_html=True)

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
    st.subheader("📈 Market Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Analyzed", len(data), help="Number of stocks analyzed")
    with col2:
        st.metric("Average Score", f"{avg_score:.1f}", help="Average investment score")
    with col3:
        st.metric("🟢 BUY Signals", buy_count, help="Stocks with BUY signal")
    with col4:
        st.metric("🟡 BASE Signals", base_count, help="Stocks in consolidation")
    with col5:
        st.metric("🔴 WATCH Signals", watch_count, help="Stocks to watch (recent drop)")

    st.markdown("---")

    # ===== Top Performers Section =====
    st.subheader("🏆 Top 10 Performers")

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

                # Card with state-based styling
                state_emoji = {'BUY': '🟢', 'BASE': '🟡', 'WATCH': '🔴', 'NORMAL': '⚪'}.get(state, '⚪')

                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
                    padding: 15px;
                    border-radius: 10px;
                    border-left: 4px solid {'#28a745' if state == 'BUY' else '#ffc107' if state == 'BASE' else '#dc3545' if state == 'WATCH' else '#6c757d'};
                    margin-bottom: 10px;
                ">
                    <div style="font-size: 1.2em; font-weight: bold;">{state_emoji} {symbol}</div>
                    <div style="font-size: 1.5em; color: #2c3e50;">{score:.1f}</div>
                    <div style="font-size: 0.9em; color: #666;">${price:,.2f}</div>
                    <div style="font-size: 0.8em; color: #888;">{state}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== Quick Stats Section =====
    st.subheader("📊 Quick Stats")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Score Distribution
        score_dist = {
            'Excellent (80+)': sum(1 for i in data if i.get('total_score', i.get('investment_score', 0)) >= 80),
            'Good (60-79)': sum(1 for i in data if 60 <= i.get('total_score', i.get('investment_score', 0)) < 80),
            'Average (40-59)': sum(1 for i in data if 40 <= i.get('total_score', i.get('investment_score', 0)) < 60),
            'Below Avg (<40)': sum(1 for i in data if i.get('total_score', i.get('investment_score', 0)) < 40),
        }
        st.markdown("**Score Distribution**")
        for label, count in score_dist.items():
            pct = count / len(data) * 100 if data else 0
            st.progress(pct / 100, text=f"{label}: {count} ({pct:.1f}%)")

    with col2:
        # State Distribution
        state_dist = {
            '🟢 BUY': buy_count,
            '🟡 BASE': base_count,
            '🔴 WATCH': watch_count,
            '⚪ NORMAL': len(data) - buy_count - base_count - watch_count,
        }
        st.markdown("**Signal Distribution**")
        for label, count in state_dist.items():
            pct = count / len(data) * 100 if data else 0
            st.progress(pct / 100, text=f"{label}: {count} ({pct:.1f}%)")

    with col3:
        # Category breakdown
        categories = {}
        for item in data:
            cat = item.get('category', 'Other')
            categories[cat] = categories.get(cat, 0) + 1

        st.markdown("**Category Breakdown**")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = count / len(data) * 100 if data else 0
            st.progress(pct / 100, text=f"{cat}: {count}")

    st.markdown("---")

    # ===== All Stocks Table =====
    st.subheader("📋 All Stocks")

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
            'Score': item.get('total_score', item.get('investment_score', 0)),
            'Value': item.get('value_score', 0),
            'Momentum': item.get('momentum_score', 0),
            'Stability': item.get('stability_score', 0),
            'Price': item.get('current_price', 0),
            'Stance': item.get('investment_stance', 'Hold')
        }
        for idx, item in enumerate(sorted(filtered_data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True))
    ])

    # Style the dataframe
    def highlight_state(val):
        colors = {'BUY': 'background-color: #d4edda', 'BASE': 'background-color: #fff3cd',
                  'WATCH': 'background-color: #f8d7da', 'NORMAL': ''}
        return colors.get(val, '')

    if not df.empty:
        styled_df = df.style.applymap(highlight_state, subset=['State'])
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.warning("No stocks match the current filters")

    st.markdown("---")

    # ===== Charts Section =====
    st.subheader("📈 Charts & Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        try:
            st.plotly_chart(
                create_score_distribution_chart(data),
                use_container_width=True
            )
        except Exception as e:
            st.warning(f"Could not create score distribution chart: {e}")

    with col2:
        # Category donut chart
        if categories:
            try:
                st.plotly_chart(
                    create_donut_chart(
                        list(categories.keys()),
                        list(categories.values()),
                        "Category Distribution"
                    ),
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"Could not create category chart: {e}")

    st.markdown("---")

    # ===== Metrics Heatmap =====
    st.subheader("🔥 Top 20 Metrics Heatmap")
    top_20 = sorted(data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True)[:20]
    try:
        metrics_fig = create_metrics_heatmap(top_20)
        st.plotly_chart(metrics_fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not create heatmap: {e}")

    st.markdown("---")

    # ===== Export Section =====
    st.subheader("📥 Export Data")
    create_export_buttons(filtered_data, filename_prefix="investment_analysis")
