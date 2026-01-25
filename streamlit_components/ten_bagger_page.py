"""
Ten Bagger Stock Screener Page
Identifies stocks with 10x return potential based on growth, profitability,
valuation, and market position scores.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screeners.ten_bagger_screener import TenBaggerScreener, TenBaggerScore
from screeners.relative_strength import RelativeStrengthCalculator, RSRating
from core.constants import TEN_BAGGER_CONFIG, GROWTH_SECTORS


# Pre-defined stock universes for screening
SCREENER_UNIVERSES = {
    'AI & Semiconductors': [
        'NVDA', 'AMD', 'AVGO', 'MRVL', 'ARM', 'SMCI', 'TSM', 'ASML',
        'LRCX', 'AMAT', 'KLAC', 'QCOM', 'INTC', 'MU', 'ADI', 'NXPI'
    ],
    'Cloud & Software': [
        'MSFT', 'GOOGL', 'AMZN', 'CRM', 'NOW', 'SNOW', 'NET', 'DDOG',
        'MDB', 'TEAM', 'ZS', 'CRWD', 'PANW', 'OKTA', 'SPLK', 'ESTC'
    ],
    'High Growth Tech': [
        'SHOP', 'SQ', 'COIN', 'AFRM', 'UPST', 'SOFI', 'RBLX', 'U',
        'DKNG', 'PATH', 'CFLT', 'GTLB', 'DOCN', 'BILL', 'HUBS', 'VEEV'
    ],
    'Biotech & Healthcare': [
        'MRNA', 'REGN', 'VRTX', 'ILMN', 'CRSP', 'NTLA', 'BEAM', 'EDIT',
        'ISRG', 'DXCM', 'ALGN', 'IDXX', 'PODD', 'INCY', 'SGEN', 'BMRN'
    ],
    'Clean Energy': [
        'ENPH', 'SEDG', 'FSLR', 'RUN', 'PLUG', 'BE', 'CHPT', 'BLNK',
        'LCID', 'RIVN', 'NEE', 'AES', 'CWEN', 'ORA', 'NOVA', 'ARRY'
    ],
    'All Growth Sectors': [],  # Will be populated dynamically
    'Custom': []
}


def render_ten_bagger_page(symbols: List[str] = None):
    """Render the Ten Bagger Stock Screener page."""
    st.markdown(
        '<div class="main-header">Ten Bagger Stock Screener</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    Identify stocks with potential for **10x returns** based on:
    - Growth metrics (revenue & earnings growth)
    - Profitability indicators (margins, ROE)
    - Valuation measures (PEG, FCF yield)
    - Market position (sector, momentum, market cap)
    """)

    # Initialize screener
    screener = TenBaggerScreener()

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Single Stock Analysis",
        "Universe Screening",
        "RS Leaders",
        "Sector Leaders",
        "Historical Winners"
    ])

    with tab1:
        render_single_stock_analysis(screener, symbols)

    with tab2:
        render_universe_screening(screener, symbols)

    with tab3:
        render_rs_leaders_tab()

    with tab4:
        render_sector_leaders(screener)

    with tab5:
        render_historical_winners()


def render_single_stock_analysis(screener: TenBaggerScreener, symbols: List[str] = None):
    """Render single stock analysis tab."""
    st.subheader("Analyze Individual Stock")

    col1, col2 = st.columns([2, 1])

    with col1:
        if symbols:
            symbol = st.selectbox(
                "Select or enter symbol",
                options=[""] + symbols,
                key="ten_bagger_symbol"
            )
            if not symbol:
                symbol = st.text_input("Or enter symbol manually", key="ten_bagger_manual")
        else:
            symbol = st.text_input("Enter stock symbol", key="ten_bagger_input")

    with col2:
        analyze_btn = st.button("Analyze", type="primary", key="analyze_btn")

    if analyze_btn and symbol:
        with st.spinner(f"Analyzing {symbol.upper()}..."):
            score = screener.score_stock(symbol.upper())

        if score:
            render_score_result(score)
        else:
            st.error(f"Could not analyze {symbol}. Please check the symbol and try again.")


def render_score_result(score: TenBaggerScore):
    """Render the score result for a single stock."""
    # Overall Score Header
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.markdown(f"### {score.symbol}")
        if score.sector:
            st.caption(f"Sector: {score.sector}")

    with col2:
        # Color-coded rating
        rating_colors = {
            'EXCELLENT': '🟢',
            'GOOD': '🟡',
            'MARGINAL': '🟠',
            'WEAK': '🔴'
        }
        st.metric("Rating", f"{rating_colors.get(score.rating, '')} {score.rating}")

    with col3:
        st.metric("Total Score", f"{score.total_score:.1f}/100")

    with col4:
        # RS Rating with color coding
        if score.rs_rating is not None:
            rs_color = _get_rs_color(score.rs_rating)
            rs_trend_icon = _get_rs_trend_icon(score.rs_trend)
            st.metric(
                "RS Rating",
                f"{rs_color} {score.rs_rating}",
                delta=rs_trend_icon,
                help="IBD-style Relative Strength (1-99). Higher = outperforming more stocks."
            )
        else:
            st.metric("RS Rating", "N/A")

    st.markdown("---")

    # RS Rating Details (if available)
    if score.rs_rating is not None:
        render_rs_details(score)

    # Score Breakdown
    st.subheader("Score Breakdown")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Growth",
            f"{score.growth_score:.1f}/35",
            help="Revenue growth, earnings growth, acceleration"
        )
        pct = score.growth_score / 35 * 100
        st.progress(pct / 100)

    with col2:
        st.metric(
            "Profitability",
            f"{score.profitability_score:.1f}/25",
            help="Margins, ROE, ROA"
        )
        pct = score.profitability_score / 25 * 100
        st.progress(pct / 100)

    with col3:
        st.metric(
            "Valuation",
            f"{score.valuation_score:.1f}/20",
            help="PEG ratio, FCF yield, P/S"
        )
        pct = score.valuation_score / 20 * 100
        st.progress(pct / 100)

    with col4:
        st.metric(
            "Market Position",
            f"{score.market_position_score:.1f}/20",
            help="Market cap, sector, momentum"
        )
        pct = score.market_position_score / 20 * 100
        st.progress(pct / 100)

    st.markdown("---")

    # Strengths and Risks
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key Strengths")
        if score.key_strengths:
            for strength in score.key_strengths:
                st.markdown(f"- {strength}")
        else:
            st.info("No significant strengths identified")

    with col2:
        st.subheader("Key Risks")
        if score.key_risks:
            for risk in score.key_risks:
                st.markdown(f"- {risk}")
        else:
            st.success("No significant risks identified")

    st.markdown("---")

    # Detailed Metrics
    st.subheader("Detailed Metrics")

    metrics = score.metrics

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Growth Metrics**")
        _display_metric("Revenue Growth", metrics.get('revenue_growth'), pct=True)
        _display_metric("Earnings Growth", metrics.get('earnings_growth'), pct=True)
        _display_metric("52-Week Return", metrics.get('return_52w'), pct=True)

    with col2:
        st.markdown("**Profitability**")
        _display_metric("Profit Margin", metrics.get('profit_margin'), pct=True)
        _display_metric("Operating Margin", metrics.get('operating_margin'), pct=True)
        _display_metric("ROE", metrics.get('roe'), pct=True)
        _display_metric("ROA", metrics.get('roa'), pct=True)

    with col3:
        st.markdown("**Valuation**")
        _display_metric("P/E Ratio", metrics.get('pe_ratio'), fmt=".1f")
        _display_metric("Forward P/E", metrics.get('forward_pe'), fmt=".1f")
        _display_metric("PEG Ratio", metrics.get('peg_ratio'), fmt=".2f")
        _display_metric("P/S Ratio", metrics.get('ps_ratio'), fmt=".1f")
        _display_metric("FCF Yield", metrics.get('fcf_yield'), pct=True)

    # Additional info
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        market_cap = metrics.get('market_cap')
        if market_cap:
            cap_str = _format_market_cap(market_cap)
            st.metric("Market Cap", cap_str)

    with col2:
        if metrics.get('current_price'):
            st.metric("Current Price", f"${metrics.get('current_price'):.2f}")

    with col3:
        _display_metric("Beta", metrics.get('beta'), fmt=".2f")

    if metrics.get('sector') or metrics.get('industry'):
        st.info(f"**Sector:** {metrics.get('sector', 'N/A')} | **Industry:** {metrics.get('industry', 'N/A')}")


def render_universe_screening(screener: TenBaggerScreener, symbols: List[str] = None):
    """Render universe screening tab."""
    st.subheader("Screen Stock Universe")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Populate all growth sectors
        if not SCREENER_UNIVERSES['All Growth Sectors']:
            all_growth = []
            for sector_symbols in GROWTH_SECTORS.values():
                all_growth.extend(list(sector_symbols))
            SCREENER_UNIVERSES['All Growth Sectors'] = list(set(all_growth))

        universe_choice = st.selectbox(
            "Select Stock Universe",
            options=list(SCREENER_UNIVERSES.keys()),
            key="universe_select"
        )

    with col2:
        min_score = st.slider(
            "Minimum Score",
            min_value=0,
            max_value=80,
            value=50,
            step=5,
            key="min_score_slider"
        )

    # Custom symbols input
    if universe_choice == 'Custom':
        custom_symbols = st.text_area(
            "Enter symbols (comma-separated)",
            placeholder="NVDA, AMD, MSFT, GOOGL",
            key="custom_symbols"
        )
        if custom_symbols:
            screen_symbols = [s.strip().upper() for s in custom_symbols.split(',') if s.strip()]
        else:
            screen_symbols = []
    else:
        screen_symbols = SCREENER_UNIVERSES.get(universe_choice, [])

    st.info(f"Screening {len(screen_symbols)} stocks...")

    if st.button("Run Screening", type="primary", key="screen_btn"):
        if not screen_symbols:
            st.warning("No symbols to screen. Please select a universe or enter custom symbols.")
            return

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        results = []
        for i, symbol in enumerate(screen_symbols):
            status_text.text(f"Analyzing {symbol}... ({i+1}/{len(screen_symbols)})")
            try:
                score = screener.score_stock(symbol)
                if score and score.total_score >= min_score:
                    results.append(score)
            except Exception as e:
                st.warning(f"Error analyzing {symbol}: {e}")
            progress_bar.progress((i + 1) / len(screen_symbols))

        progress_bar.empty()
        status_text.empty()

        if results:
            st.success(f"Found {len(results)} stocks scoring {min_score}+ points")
            render_screening_results(results)
        else:
            st.warning(f"No stocks found with score >= {min_score}")


def render_screening_results(results: List[TenBaggerScore]):
    """Render screening results as a table."""
    # Sort options
    sort_col = st.columns([3, 1])
    with sort_col[1]:
        sort_by = st.selectbox(
            "Sort by",
            ["Total Score", "RS Rating", "Growth", "Profitability"],
            key="sort_results"
        )

    # Sort results
    if sort_by == "RS Rating":
        sorted_results = sorted(results, key=lambda x: x.rs_rating or 0, reverse=True)
    elif sort_by == "Growth":
        sorted_results = sorted(results, key=lambda x: x.growth_score, reverse=True)
    elif sort_by == "Profitability":
        sorted_results = sorted(results, key=lambda x: x.profitability_score, reverse=True)
    else:
        sorted_results = sorted(results, key=lambda x: x.total_score, reverse=True)

    # Prepare data for table
    data = []
    for score in sorted_results:
        rs_display = f"{score.rs_rating}" if score.rs_rating else "-"
        rs_trend_icon = ""
        if score.rs_trend == 'IMPROVING':
            rs_trend_icon = " ↑"
        elif score.rs_trend == 'DECLINING':
            rs_trend_icon = " ↓"

        data.append({
            'Symbol': score.symbol,
            'Total': f"{score.total_score:.1f}",
            'RS': rs_display + rs_trend_icon,
            'Growth': f"{score.growth_score:.1f}",
            'Profit': f"{score.profitability_score:.1f}",
            'Value': f"{score.valuation_score:.1f}",
            'Rating': score.rating,
            'Sector': score.sector or '-',
            'Top Strength': score.key_strengths[0][:35] + '...' if score.key_strengths and len(score.key_strengths[0]) > 35 else (score.key_strengths[0] if score.key_strengths else '-')
        })

    df = pd.DataFrame(data)

    # Apply rating colors
    def color_rating(val):
        colors = {
            'EXCELLENT': 'background-color: #28a745; color: white',
            'GOOD': 'background-color: #ffc107; color: black',
            'MARGINAL': 'background-color: #fd7e14; color: white',
            'WEAK': 'background-color: #dc3545; color: white'
        }
        return colors.get(val, '')

    def color_rs(val):
        """Color RS ratings."""
        try:
            # Extract number from string like "95 ↑"
            rs_num = int(val.split()[0]) if val and val[0].isdigit() else 0
            if rs_num >= 80:
                return 'background-color: #28a745; color: white'
            elif rs_num >= 60:
                return 'background-color: #17a2b8; color: white'
            elif rs_num >= 40:
                return 'background-color: #ffc107; color: black'
            elif rs_num > 0:
                return 'background-color: #dc3545; color: white'
        except:
            pass
        return ''

    styled_df = df.style.applymap(color_rating, subset=['Rating']).applymap(color_rs, subset=['RS'])

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Export option
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Results CSV",
        data=csv,
        file_name=f"ten_bagger_screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def render_rs_leaders_tab():
    """Render RS Leaders tab showing stocks with highest relative strength."""
    st.subheader("Relative Strength Leaders")

    st.markdown("""
    **IBD-Style Relative Strength Ranking**

    RS Rating measures a stock's price performance over the past 12 months compared to all other stocks.
    - **RS 90+**: Elite performer (top 10%)
    - **RS 80+**: Strong performer (top 20%)
    - **RS 70+**: Above average
    - **RS <50**: Underperforming

    *Stocks with high RS ratings and improving trends often continue outperforming.*
    """)

    col1, col2 = st.columns(2)

    with col1:
        min_rs = st.slider(
            "Minimum RS Rating",
            min_value=50,
            max_value=90,
            value=70,
            step=5,
            key="min_rs_slider"
        )

    with col2:
        show_trend = st.checkbox("Only show improving RS", value=False, key="improving_only")

    if st.button("Find RS Leaders", type="primary", key="rs_leaders_btn"):
        rs_calc = RelativeStrengthCalculator()

        with st.spinner("Calculating relative strength rankings..."):
            # Build universe cache first
            rs_calc._build_universe_cache()

            if show_trend:
                results = rs_calc.get_improving_rs_stocks(min_rs=min_rs)
            else:
                results = rs_calc.get_rs_leaders(min_rs=min_rs, top_n=30)

        if results:
            st.success(f"Found {len(results)} stocks with RS >= {min_rs}")

            # Display results
            data = []
            for rs in results:
                trend_icon = {
                    'IMPROVING': '↑',
                    'STABLE': '→',
                    'DECLINING': '↓'
                }.get(rs.rs_trend, '')

                data.append({
                    'Symbol': rs.symbol,
                    'RS Rating': rs.rs_rating,
                    'Sector RS': rs.rs_rating_sector or '-',
                    'Trend': f"{trend_icon} {rs.rs_trend}",
                    '3M Return': f"{rs.return_3m*100:+.1f}%" if rs.return_3m else '-',
                    '6M Return': f"{rs.return_6m*100:+.1f}%" if rs.return_6m else '-',
                    '12M Return': f"{rs.return_12m*100:+.1f}%" if rs.return_12m else '-',
                    'Sector': rs.sector or '-',
                    'Price': f"${rs.current_price:.2f}" if rs.current_price else '-'
                })

            df = pd.DataFrame(data)

            # Color RS ratings
            def color_rs_value(val):
                try:
                    if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                        num = int(val)
                        if num >= 90:
                            return 'background-color: #6f42c1; color: white'  # Purple for elite
                        elif num >= 80:
                            return 'background-color: #28a745; color: white'
                        elif num >= 70:
                            return 'background-color: #17a2b8; color: white'
                        elif num >= 50:
                            return 'background-color: #ffc107; color: black'
                except:
                    pass
                return ''

            styled_df = df.style.applymap(color_rs_value, subset=['RS Rating'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Export option
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download RS Leaders CSV",
                data=csv,
                file_name=f"rs_leaders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning(f"No stocks found with RS >= {min_rs}")

    # Sector RS Leaders section
    st.markdown("---")
    st.subheader("Sector RS Rankings")

    if st.button("Analyze Sector RS", key="sector_rs_btn"):
        rs_calc = RelativeStrengthCalculator()

        with st.spinner("Analyzing sector relative strength..."):
            sector_leaders = rs_calc.get_sector_rs_leaders(top_n=3)

        for sector, leaders in sector_leaders.items():
            if leaders:
                st.markdown(f"### {sector}")
                cols = st.columns(len(leaders))
                for i, rs in enumerate(leaders):
                    with cols[i]:
                        trend_icon = '↑' if rs.rs_trend == 'IMPROVING' else ('↓' if rs.rs_trend == 'DECLINING' else '→')
                        st.metric(
                            rs.symbol,
                            f"RS: {rs.rs_rating}",
                            delta=f"{trend_icon} {rs.rs_trend}"
                        )
                        if rs.return_12m:
                            st.caption(f"12M: {rs.return_12m*100:+.1f}%")


def render_sector_leaders(screener: TenBaggerScreener):
    """Render sector leaders tab."""
    st.subheader("Growth Sector Leaders")

    st.markdown("""
    Top-scoring stocks in each high-growth sector with secular tailwinds.
    """)

    top_n = st.slider(
        "Top N per sector",
        min_value=1,
        max_value=5,
        value=3,
        key="sector_top_n"
    )

    if st.button("Find Sector Leaders", type="primary", key="sector_btn"):
        progress = st.progress(0)
        status = st.empty()

        sector_results = {}
        sector_list = list(GROWTH_SECTORS.keys())

        for i, (sector_name, sector_symbols) in enumerate(GROWTH_SECTORS.items()):
            status.text(f"Analyzing {sector_name}...")

            sector_scores = []
            for symbol in sector_symbols:
                try:
                    score = screener.score_stock(symbol)
                    if score:
                        sector_scores.append(score)
                except:
                    continue

            sector_scores.sort(key=lambda x: x.total_score, reverse=True)
            sector_results[sector_name] = sector_scores[:top_n]

            progress.progress((i + 1) / len(sector_list))

        progress.empty()
        status.empty()

        # Display results by sector
        for sector_name, leaders in sector_results.items():
            if leaders:
                st.markdown(f"### {sector_name.replace('_', ' ').title()}")

                cols = st.columns(len(leaders))
                for i, score in enumerate(leaders):
                    with cols[i]:
                        rating_emoji = {
                            'EXCELLENT': '🌟',
                            'GOOD': '✨',
                            'MARGINAL': '💡',
                            'WEAK': '⚪'
                        }.get(score.rating, '')

                        st.metric(
                            f"{rating_emoji} {score.symbol}",
                            f"{score.total_score:.1f}/100"
                        )
                        st.caption(f"Rating: {score.rating}")
                        if score.key_strengths:
                            st.caption(f"Key: {score.key_strengths[0][:40]}...")

                st.markdown("---")


def render_historical_winners():
    """Render historical winners tab with case studies."""
    st.subheader("Historical Ten Baggers")

    st.markdown("""
    Learn from stocks that achieved 10x+ returns and understand what made them successful.
    """)

    # Case studies
    case_studies = {
        'NVDA': {
            'name': 'NVIDIA Corporation',
            'period': '2019-2024',
            'return': '~2000%',
            'key_factors': [
                'AI/GPU revolution leader',
                'Data center revenue explosion',
                'Gaming dominance maintained',
                'Expanding software ecosystem',
                'High gross margins (60%+)'
            ],
            'metrics_then': {
                'Market Cap': '$100B (2019)',
                'Revenue Growth': '~40%',
                'P/E Ratio': '~35'
            }
        },
        'AMD': {
            'name': 'Advanced Micro Devices',
            'period': '2018-2024',
            'return': '~1500%',
            'key_factors': [
                'CPU market share gains vs Intel',
                'Lisa Su leadership turnaround',
                'Server chip momentum',
                'Xilinx acquisition synergies',
                'AI accelerator push'
            ],
            'metrics_then': {
                'Market Cap': '$10B (2018)',
                'Revenue Growth': '~25%',
                'Turnaround Story': 'From losses to profits'
            }
        },
        'TSLA': {
            'name': 'Tesla Inc.',
            'period': '2019-2021',
            'return': '~1500%',
            'key_factors': [
                'EV market leadership',
                'Production scaling success',
                'Software/FSD potential',
                'Energy storage growth',
                'Brand strength'
            ],
            'metrics_then': {
                'Market Cap': '$50B (2019)',
                'Deliveries': 'Growing 50%+ YoY',
                'P/E Ratio': 'N/A (unprofitable)'
            }
        },
        'SHOP': {
            'name': 'Shopify Inc.',
            'period': '2017-2021',
            'return': '~2500%',
            'key_factors': [
                'E-commerce platform dominance',
                'Merchant ecosystem expansion',
                'COVID acceleration',
                'International growth',
                'Fulfillment network'
            ],
            'metrics_then': {
                'Market Cap': '$8B (2017)',
                'Revenue Growth': '~70%',
                'GMV Growth': 'Accelerating'
            }
        }
    }

    for symbol, study in case_studies.items():
        with st.expander(f"{symbol}: {study['name']} ({study['return']})", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Period:** {study['period']}")
                st.markdown(f"**Total Return:** {study['return']}")

                st.markdown("**Key Success Factors:**")
                for factor in study['key_factors']:
                    st.markdown(f"- {factor}")

            with col2:
                st.markdown("**Metrics at Start:**")
                for metric, value in study['metrics_then'].items():
                    st.markdown(f"- **{metric}:** {value}")

    st.markdown("---")
    st.markdown("### Common Patterns of Ten Baggers")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Growth Characteristics:**
        - Revenue growth 30%+ consistently
        - Expanding addressable market
        - Market share gains
        - Multiple growth vectors
        """)

    with col2:
        st.markdown("""
        **Business Quality:**
        - High gross margins (50%+)
        - Scalable business model
        - Strong competitive moat
        - Visionary leadership
        """)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("""
        **Market Position:**
        - $5B-$50B market cap sweet spot
        - Category leader or disruptor
        - Secular tailwind exposure
        - Room for multiple expansion
        """)

    with col4:
        st.markdown("""
        **Risk Factors Managed:**
        - Reasonable valuation for growth
        - Positive cash flow (or path to it)
        - Manageable debt levels
        - Execution track record
        """)


def _display_metric(label: str, value, pct: bool = False, fmt: str = ".1f"):
    """Display a metric with proper formatting."""
    if value is None:
        st.markdown(f"**{label}:** N/A")
    elif pct:
        st.markdown(f"**{label}:** {value*100:.1f}%")
    else:
        st.markdown(f"**{label}:** {value:{fmt}}")


def _format_market_cap(value: float) -> str:
    """Format market cap to human readable string."""
    if value >= 1e12:
        return f"${value/1e12:.1f}T"
    elif value >= 1e9:
        return f"${value/1e9:.1f}B"
    elif value >= 1e6:
        return f"${value/1e6:.1f}M"
    else:
        return f"${value:,.0f}"


def _get_rs_color(rs_rating: int) -> str:
    """Get color emoji for RS rating."""
    if rs_rating >= 90:
        return "🟣"  # Elite (top 10%)
    elif rs_rating >= 80:
        return "🟢"  # Strong (top 20%)
    elif rs_rating >= 70:
        return "🟡"  # Good (top 30%)
    elif rs_rating >= 50:
        return "🟠"  # Average
    else:
        return "🔴"  # Weak


def _get_rs_trend_icon(rs_trend: str) -> str:
    """Get trend indicator for RS."""
    if rs_trend == 'IMPROVING':
        return "↑ Improving"
    elif rs_trend == 'DECLINING':
        return "↓ Declining"
    else:
        return "→ Stable"


def render_rs_details(score: TenBaggerScore):
    """Render detailed RS information."""
    st.subheader("Relative Strength Analysis")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # RS Rating with gauge-style display
        rs = score.rs_rating
        if rs >= 80:
            st.success(f"**RS Rating: {rs}** (Top {100-rs}%)")
        elif rs >= 60:
            st.info(f"**RS Rating: {rs}** (Top {100-rs}%)")
        elif rs >= 40:
            st.warning(f"**RS Rating: {rs}**")
        else:
            st.error(f"**RS Rating: {rs}** (Underperforming)")

    with col2:
        # Sector RS
        if score.rs_rating_sector is not None:
            st.metric(
                "Sector RS",
                score.rs_rating_sector,
                help="Relative strength vs sector peers"
            )
        else:
            st.metric("Sector RS", "N/A")

    with col3:
        # RS Trend
        trend = score.rs_trend or 'N/A'
        trend_colors = {
            'IMPROVING': '🟢 IMPROVING',
            'STABLE': '🟡 STABLE',
            'DECLINING': '🔴 DECLINING'
        }
        st.metric("RS Trend", trend_colors.get(trend, trend))

    with col4:
        # Returns from metrics
        metrics = score.metrics
        return_52w = metrics.get('return_52w')
        if return_52w is not None:
            delta_color = "normal" if return_52w >= 0 else "inverse"
            st.metric(
                "52-Week Return",
                f"{return_52w*100:+.1f}%",
            )
        else:
            st.metric("52-Week Return", "N/A")

    # RS Interpretation
    st.markdown("---")
    _render_rs_interpretation(score.rs_rating, score.rs_rating_sector, score.rs_trend)


def _render_rs_interpretation(rs: int, sector_rs: int, trend: str):
    """Render interpretation of RS ratings."""
    interpretations = []

    # Overall RS interpretation
    if rs >= 90:
        interpretations.append(
            "**Elite Performer:** Stock is in the top 10% of all stocks. "
            "Strong institutional interest likely. Consider for momentum strategies."
        )
    elif rs >= 80:
        interpretations.append(
            "**Strong Performer:** Stock is outperforming 80%+ of the market. "
            "Momentum is clearly positive. Good entry point on pullbacks."
        )
    elif rs >= 70:
        interpretations.append(
            "**Above Average:** Stock is performing better than most peers. "
            "Watch for continued strength or potential breakout."
        )
    elif rs >= 50:
        interpretations.append(
            "**Average Performer:** Stock is performing in line with market. "
            "Need other catalysts to drive outperformance."
        )
    else:
        interpretations.append(
            "**Underperformer:** Stock is lagging the market significantly. "
            "Wait for RS improvement before considering entry."
        )

    # Sector comparison
    if sector_rs is not None:
        if sector_rs > rs + 10:
            interpretations.append(
                f"**Sector Leader:** RS {sector_rs} vs sector shows relative strength within group."
            )
        elif sector_rs < rs - 10:
            interpretations.append(
                f"**Sector Laggard:** Underperforming sector peers despite market RS of {rs}."
            )

    # Trend interpretation
    if trend == 'IMPROVING':
        interpretations.append(
            "**Momentum Building:** RS trend is improving. Recent performance accelerating."
        )
    elif trend == 'DECLINING':
        interpretations.append(
            "**Momentum Fading:** RS trend declining. Consider tightening stops or reducing position."
        )

    # Display interpretations
    for interp in interpretations:
        st.markdown(interp)
