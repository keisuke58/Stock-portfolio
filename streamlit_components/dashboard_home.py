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
        color: #4cc9f0;  /* Fallback color */
        background: linear-gradient(135deg, #4361ee 0%, #7209b7 50%, #f72585 100%);
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
        color: #4cc9f0;  /* Fallback - cyan */
        background: linear-gradient(135deg, #4cc9f0 0%, #4361ee 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #e0e0e0;  /* Lighter gray for better readability */
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
        color: #ffffff;  /* White text for symbol */
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .rec-score {
        font-size: 1.75rem;
        font-weight: 800;
        color: #4cc9f0;  /* Cyan - highly visible */
        margin: 0.25rem 0;
    }

    .rec-details {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #d0d0d0;  /* Light gray for details */
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
        background: linear-gradient(135deg, #06d6a0, #4cc9f0);
        color: #000000;  /* Black text on bright gradient */
    }

    .rec-badge.buy {
        background: rgba(76, 201, 240, 0.3);
        color: #4cc9f0;  /* Cyan */
        border: 1px solid #4cc9f0;
    }

    .rec-badge.hold {
        background: rgba(255, 214, 10, 0.2);
        color: #ffd60a;  /* Yellow */
        border: 1px solid #ffd60a;
    }

    .rec-badge.watch {
        background: rgba(255, 149, 0, 0.2);
        color: #ff9500;  /* Orange */
        border: 1px solid #ff9500;
    }

    .rec-badge.avoid {
        background: rgba(239, 71, 111, 0.2);
        color: #ef476f;  /* Red */
        border: 1px solid #ef476f;
    }

    /* Rank badge */
    .rank-badge {
        position: absolute;
        top: -5px;
        right: 10px;
        background: linear-gradient(135deg, #7209b7 0%, #f72585 100%);
        color: #ffffff;  /* White text */
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
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #c0c0c0;  /* Light gray */
        margin-right: 0.25rem;
    }

    /* Signal tag */
    .signal-tag {
        display: inline-block;
        padding: 0.15rem 0.4rem;
        border-radius: 8px;
        font-size: 0.6rem;
        font-weight: 500;
        background: rgba(67, 97, 238, 0.3);
        color: #7c9aff;  /* Light blue - readable */
        margin: 0.1rem;
    }

    /* Section header */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #ffffff;  /* White for section headers */
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(255, 255, 255, 0.15);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Sub-section header */
    .sub-header {
        font-size: 1rem;
        font-weight: 600;
        color: #4cc9f0;  /* Cyan for sub-headers */
        margin: 1rem 0 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Stats bar */
    .stats-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    .stats-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .stats-row:last-child {
        border-bottom: none;
    }

    .stats-label {
        color: #c0c0c0;  /* Light gray for labels */
        font-size: 0.85rem;
    }

    .stats-value {
        color: #ffffff;  /* White for values */
        font-weight: 600;
    }

    .stats-bar {
        height: 6px;
        background: #1a1a2e;
        border-radius: 3px;
        overflow: hidden;
        margin-top: 0.25rem;
    }

    .stats-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    .stats-bar-fill.excellent { background: linear-gradient(90deg, #06d6a0, #4cc9f0); }
    .stats-bar-fill.good { background: linear-gradient(90deg, #4361ee, #7209b7); }
    .stats-bar-fill.average { background: linear-gradient(90deg, #ffd60a, #ff9500); }
    .stats-bar-fill.below { background: linear-gradient(90deg, #ef476f, #f72585); }

    /* Divider */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
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
        background: rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        font-size: 0.65rem;
    }

    .score-mini-value {
        font-weight: 700;
        color: #4cc9f0;  /* Cyan for score values */
    }

    .score-mini-label {
        color: #a0a0a0;  /* Gray for labels */
        font-size: 0.55rem;
    }

    /* Screening progress */
    .screening-status {
        background: rgba(6, 214, 160, 0.1);
        border: 1px solid rgba(6, 214, 160, 0.3);
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
        color: #ffffff;  /* White for title */
    }

    .screening-status-detail {
        font-size: 0.8rem;
        color: #c0c0c0;  /* Light gray for details */
    }
    </style>
    """, unsafe_allow_html=True)


def run_unified_screening(symbols: List[str] = None, top_n: int = 20, max_workers: int = 5) -> Optional[Dict]:
    """Run unified screening on stock universe."""
    try:
        from screeners.unified_screener import UnifiedScreener, DEFAULT_SCREENING_UNIVERSE
        from fetchers import YahooFetcher

        if symbols is None:
            symbols = DEFAULT_SCREENING_UNIVERSE

        fetcher = YahooFetcher()
        screener = UnifiedScreener(fetcher)

        # Screen with parallel workers
        result = screener.screen_universe(symbols, max_workers=max_workers, top_n=top_n)

        # Convert to dict format expected by UI
        return {
            'overall': result.all_scores[:top_n],
            'growth': result.ten_bagger_candidates[:top_n],
            'momentum': result.momentum_leaders[:top_n],
            'value': result.deep_value_plays[:top_n],
            'recovery': result.recovery_candidates[:top_n],
            'strong_buys': result.strong_buys[:top_n],
            'total_screened': result.total_screened,
            'timestamp': result.timestamp
        }

    except ImportError as e:
        st.error(f"Import error: {e}. Make sure all dependencies are installed.")
        return None
    except Exception as e:
        st.error(f"Screening error: {e}")
        import traceback
        st.code(traceback.format_exc())
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

    # Company name (truncate if too long)
    company_name = getattr(score, 'company_name', '') or score.symbol
    if len(company_name) > 25:
        company_name = company_name[:22] + "..."

    # Links
    yahoo_link = f"https://finance.yahoo.com/quote/{score.symbol}"
    website = getattr(score, 'website', '') or ''

    # Build links HTML
    links_html = f'<a href="{yahoo_link}" target="_blank" style="color: #7c9aff; text-decoration: none; font-size: 0.7rem; margin-right: 8px;">📊 Yahoo</a>'
    if website:
        links_html += f'<a href="{website}" target="_blank" style="color: #7c9aff; text-decoration: none; font-size: 0.7rem;">🌐 Website</a>'

    st.markdown(f"""
    <div class="rec-card {rec_class}" style="position: relative;">
        <div class="rank-badge">#{rank}</div>
        <div class="rec-symbol">
            {rec_emoji} {score.symbol}
            <span class="category-badge">{score.sector or score.category}</span>
        </div>
        <div style="font-size: 0.75rem; color: #a0a0a0; margin-top: 2px;">{company_name}</div>
        <div class="rec-score">{score.unified_score:.1f}</div>
        <div class="rec-details">
            <span>${score.current_price:,.2f}</span>
            <span class="rec-badge {rec_class}">{score.recommendation.replace('_', ' ')}</span>
        </div>
        <div style="margin: 4px 0;">{links_html}</div>
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


def get_large_universe():
    """Get large stock universe (200+ stocks)."""
    return [
        # Mega Cap Tech
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'BRK-B',
        # Large Cap Tech
        'AVGO', 'ORCL', 'ADBE', 'CRM', 'AMD', 'INTC', 'QCOM', 'TXN', 'IBM', 'CSCO',
        'NOW', 'INTU', 'AMAT', 'ADI', 'LRCX', 'MU', 'KLAC', 'MRVL', 'SNPS', 'CDNS',
        # Software & Cloud
        'SNOW', 'DDOG', 'NET', 'ZS', 'CRWD', 'PANW', 'OKTA', 'MDB', 'TEAM', 'HUBS',
        'SPLK', 'WDAY', 'VEEV', 'DOCU', 'ZM', 'TWLO', 'BILL', 'CFLT', 'GTLB', 'PATH',
        # E-commerce & Internet
        'SHOP', 'MELI', 'BKNG', 'ABNB', 'UBER', 'LYFT', 'DASH', 'ETSY', 'EBAY', 'W',
        'PYPL', 'COIN', 'AFRM', 'SOFI', 'HOOD', 'SQ', 'UPST', 'LMND',
        # Semiconductors
        'TSM', 'ASML', 'ARM', 'SMCI', 'ON', 'NXPI', 'MPWR', 'SWKS', 'QRVO', 'MCHP',
        # AI & Data
        'PLTR', 'AI', 'IONQ', 'RGTI', 'S', 'U', 'RBLX', 'TTWO', 'EA', 'MTCH',
        # Healthcare & Biotech
        'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'DHR', 'ABT', 'BMY',
        'AMGN', 'GILD', 'VRTX', 'REGN', 'MRNA', 'BNTX', 'ISRG', 'DXCM', 'IDXX', 'IQV',
        'ZTS', 'SYK', 'BDX', 'MDT', 'EW', 'A', 'BSX', 'HCA', 'CI', 'ELV',
        # Financials
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'COF',
        'V', 'MA', 'SPGI', 'MCO', 'ICE', 'CME', 'NDAQ', 'MSCI', 'FIS', 'FISV',
        'PNC', 'USB', 'TFC', 'AIG', 'MET', 'PRU', 'AFL', 'ALL', 'TRV', 'PGR',
        # Consumer
        'WMT', 'COST', 'TGT', 'HD', 'LOW', 'NKE', 'SBUX', 'MCD', 'DIS', 'NFLX',
        'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'KO', 'PEP', 'PM', 'MO', 'MDLZ',
        'CL', 'PG', 'KMB', 'EL', 'CLX', 'KHC', 'GIS', 'K', 'CPB', 'SJM',
        'DG', 'DLTR', 'ROST', 'TJX', 'ORLY', 'AZO', 'BBY', 'GPS', 'KSS', 'M',
        'CMG', 'YUM', 'DPZ', 'QSR', 'WING', 'CAVA', 'SHAK', 'BROS',
        # Industrials
        'CAT', 'DE', 'BA', 'RTX', 'LMT', 'NOC', 'GD', 'GE', 'HON', 'MMM',
        'UPS', 'FDX', 'UNP', 'CSX', 'NSC', 'ODFL', 'JBHT', 'XPO', 'CHRW',
        'WM', 'RSG', 'FAST', 'PAYX', 'ADP', 'CTAS', 'ROK', 'EMR', 'ETN', 'ITW',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'PSX', 'VLO', 'MPC', 'PXD',
        'DVN', 'FANG', 'HAL', 'BKR', 'KMI', 'WMB', 'OKE', 'TRGP', 'LNG', 'ET',
        # Materials
        'LIN', 'APD', 'SHW', 'ECL', 'DD', 'DOW', 'NEM', 'FCX', 'NUE', 'STLD',
        # REITs
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'DLR', 'O', 'WELL', 'SPG', 'VICI',
        # Speculative Growth
        'RKLB', 'ASTS', 'LUNR', 'RDW', 'ACHR', 'JOBY', 'LILM', 'EVTL',
        'RIVN', 'LCID', 'FSR', 'GOEV', 'RIDE', 'WKHS', 'HYLN', 'XOS',
    ]


def get_sp500_top100():
    """Get S&P 500 top 100 by market cap."""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'JPM', 'V', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV', 'LLY',
        'PEP', 'COST', 'AVGO', 'KO', 'TMO', 'CSCO', 'WMT', 'MCD', 'ACN', 'ABT',
        'CRM', 'DHR', 'BAC', 'ADBE', 'PFE', 'NKE', 'AMD', 'DIS', 'CMCSA', 'TXN',
        'VZ', 'NFLX', 'PM', 'INTC', 'WFC', 'NEE', 'RTX', 'HON', 'T', 'QCOM',
        'COP', 'LOW', 'ORCL', 'UPS', 'BMY', 'MS', 'INTU', 'UNP', 'SPGI', 'ELV',
        'CAT', 'IBM', 'BA', 'GE', 'AMGN', 'DE', 'GS', 'SBUX', 'NOW', 'ISRG',
        'AMAT', 'BLK', 'GILD', 'AXP', 'PLD', 'SYK', 'MDLZ', 'ADI', 'TJX', 'VRTX',
        'ADP', 'BKNG', 'LMT', 'MMC', 'C', 'CVS', 'CI', 'REGN', 'SCHW', 'MO',
        'CB', 'ETN', 'TMUS', 'ZTS', 'LRCX', 'EOG', 'SO', 'DUK', 'BSX', 'BDX',
    ]


def render_screening_section():
    """Render the comprehensive screening section."""
    st.markdown('<div class="section-header">🎯 Smart Stock Screening</div>', unsafe_allow_html=True)

    # Screening options in expander for cleaner UI
    with st.expander("⚙️ Screening Settings", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            screening_mode = st.selectbox(
                "Universe",
                [
                    "Large Universe (200+ stocks)",
                    "S&P 500 Top 100",
                    "Default (70 stocks)",
                    "Tech & Growth (50 stocks)",
                    "Value & Dividend (40 stocks)",
                    "Semiconductors (30 stocks)",
                    "Custom Symbols"
                ],
                key="screening_mode"
            )

        with col2:
            top_n = st.selectbox(
                "Show Top N",
                [10, 20, 30, 50, 100],
                index=1,
                key="top_n_results"
            )

        with col3:
            max_workers = st.selectbox(
                "Speed",
                [("Fast (3)", 3), ("Normal (5)", 5), ("Thorough (10)", 10)],
                index=1,
                format_func=lambda x: x[0],
                key="max_workers"
            )[1]

    custom_symbols = None
    if screening_mode == "Custom Symbols":
        custom_input = st.text_area(
            "Enter symbols (comma or space separated)",
            placeholder="AAPL, MSFT, GOOGL, NVDA, AMD, TSLA...",
            height=100
        )
        if custom_input:
            # Support comma, space, newline separated
            import re
            custom_symbols = [s.strip().upper() for s in re.split(r'[,\s\n]+', custom_input) if s.strip()]
            st.info(f"Found {len(custom_symbols)} symbols")

    col1, col2 = st.columns([1, 3])
    with col1:
        run_screening = st.button("🔍 Run Screening", use_container_width=True, type="primary")
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state['screening_results'] = None
            st.rerun()

    if run_screening or st.session_state.get('screening_results') is not None:
        if run_screening:
            # Determine symbols based on mode
            if screening_mode == "Large Universe (200+ stocks)":
                symbols = get_large_universe()
            elif screening_mode == "S&P 500 Top 100":
                symbols = get_sp500_top100()
            elif screening_mode == "Tech & Growth (50 stocks)":
                symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'AVGO', 'QCOM',
                    'CRM', 'NOW', 'ADBE', 'INTU', 'SNOW', 'DDOG', 'NET', 'ZS', 'CRWD', 'PANW',
                    'SHOP', 'MELI', 'COIN', 'PLTR', 'AI', 'PATH', 'U', 'RBLX', 'MDB', 'TEAM',
                    'ARM', 'SMCI', 'IONQ', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ON', 'NXPI', 'MPWR',
                    'UBER', 'ABNB', 'DASH', 'BKNG', 'NFLX', 'ROKU', 'TTWO', 'EA', 'MTCH', 'ETSY'
                ]
            elif screening_mode == "Value & Dividend (40 stocks)":
                symbols = [
                    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'AXP', 'BLK',
                    'JNJ', 'PFE', 'ABBV', 'MRK', 'BMY', 'AMGN', 'GILD',
                    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC',
                    'WMT', 'COST', 'TGT', 'HD', 'LOW', 'KO', 'PEP', 'PG', 'CL',
                    'CAT', 'DE', 'HON', 'MMM', 'UPS', 'UNP'
                ]
            elif screening_mode == "Semiconductors (30 stocks)":
                symbols = [
                    'NVDA', 'AMD', 'AVGO', 'QCOM', 'TXN', 'INTC', 'MU', 'AMAT', 'LRCX', 'KLAC',
                    'MRVL', 'ADI', 'NXPI', 'ON', 'MPWR', 'SWKS', 'QRVO', 'MCHP', 'SNPS', 'CDNS',
                    'TSM', 'ASML', 'ARM', 'SMCI', 'WOLF', 'CRUS', 'SLAB', 'DIOD', 'SITM', 'ACLS'
                ]
            elif custom_symbols:
                symbols = custom_symbols
            else:
                symbols = None  # Use default

            # Show progress
            if symbols:
                st.info(f"🔄 Screening {len(symbols)} stocks...")

            with st.spinner(f"Analyzing stocks from all perspectives (this may take a moment)..."):
                results = run_unified_screening(symbols, top_n=top_n, max_workers=max_workers)
                st.session_state['screening_results'] = results

        results = st.session_state.get('screening_results')

        if results:
            # Display screening status
            total_screened = results.get('total_screened', len(results.get('overall', [])))
            strong_buys = len(results.get('strong_buys', []))
            top_results = len(results.get('overall', []))
            growth_candidates = len(results.get('growth', []))
            momentum_leaders = len(results.get('momentum', []))

            st.markdown(f"""
            <div class="screening-status">
                <div class="screening-status-icon">✅</div>
                <div class="screening-status-text">
                    <div class="screening-status-title">Screening Complete</div>
                    <div class="screening-status-detail">
                        Analyzed {total_screened} stocks • Top {top_results} shown • {strong_buys} Strong Buys • {growth_candidates} Growth • {momentum_leaders} Momentum Leaders
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Create tabs for different perspectives
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                f"🏆 Top Overall ({len(results.get('overall', []))})",
                f"🚀 Growth ({len(results.get('growth', []))})",
                f"📈 Momentum ({len(results.get('momentum', []))})",
                f"💎 Deep Value ({len(results.get('value', []))})",
                f"🔄 Recovery ({len(results.get('recovery', []))})",
                "📊 Full Table"
            ])

            def render_category_results(data_list, category_name, description):
                """Render results for a category with pagination."""
                if not data_list:
                    st.info(f"No {category_name.lower()} found")
                    return

                st.markdown(f'<div class="sub-header">{description}</div>', unsafe_allow_html=True)

                # Show count
                st.caption(f"Found {len(data_list)} stocks")

                # Pagination
                items_per_page = 20
                total_pages = (len(data_list) - 1) // items_per_page + 1

                if total_pages > 1:
                    page = st.selectbox(f"Page", range(1, total_pages + 1), key=f"page_{category_name}")
                else:
                    page = 1

                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(data_list))
                page_data = data_list[start_idx:end_idx]

                cols = st.columns(2)
                for idx, score in enumerate(page_data):
                    with cols[idx % 2]:
                        render_recommendation_card(score, start_idx + idx + 1, category_name)

            with tab1:
                render_category_results(
                    results.get('overall', []),
                    "overall",
                    "🏆 Top Recommendations by Unified Score"
                )

            with tab2:
                render_category_results(
                    results.get('growth', []),
                    "growth",
                    "🚀 Ten Bagger Candidates (High Growth Potential)"
                )

            with tab3:
                render_category_results(
                    results.get('momentum', []),
                    "momentum",
                    "📈 Momentum Leaders (High Relative Strength)"
                )

            with tab4:
                render_category_results(
                    results.get('value', []),
                    "value",
                    "💎 Deep Value Plays (Significant Drawdown + Strong Fundamentals)"
                )

            with tab5:
                render_category_results(
                    results.get('recovery', []),
                    "recovery",
                    "🔄 Recovery Candidates (Bottom Formation + Improving Momentum)"
                )

            with tab6:
                st.markdown('<div class="sub-header">📊 Full Screening Results Table</div>', unsafe_allow_html=True)
                overall = results.get('overall', [])
                if overall:
                    # Create DataFrame for table view
                    table_data = []
                    for idx, score in enumerate(overall):
                        company_name = getattr(score, 'company_name', '') or score.symbol
                        if len(company_name) > 30:
                            company_name = company_name[:27] + "..."

                        table_data.append({
                            'Rank': idx + 1,
                            'Symbol': score.symbol,
                            'Company': company_name,
                            'Score': round(score.unified_score, 1),
                            'Rec': score.recommendation,
                            '10-Bag': round(score.ten_bagger_score, 0),
                            'RS': score.rs_rating,
                            'Value': round(score.deep_bottom_score, 0),
                            'Fund': round(score.fundamental_score, 0),
                            'Price': f"${score.current_price:,.2f}" if score.current_price else "N/A",
                            'Drawdown': f"{score.drawdown_pct:.1f}%",
                            'Sector': score.sector or "N/A"
                        })

                    df = pd.DataFrame(table_data)

                    # Color code recommendations
                    def color_rec(val):
                        colors = {
                            'STRONG_BUY': 'background-color: rgba(6, 214, 160, 0.4)',
                            'BUY': 'background-color: rgba(76, 201, 240, 0.3)',
                            'HOLD': 'background-color: rgba(255, 214, 10, 0.2)',
                            'WATCH': 'background-color: rgba(255, 149, 0, 0.2)',
                            'AVOID': 'background-color: rgba(239, 71, 111, 0.2)'
                        }
                        return colors.get(val, '')

                    styled_df = df.style.applymap(color_rec, subset=['Rec'])
                    st.dataframe(styled_df, use_container_width=True, height=500)

                    # Download links for all symbols
                    st.markdown('<div class="sub-header">🔗 Quick Links</div>', unsafe_allow_html=True)
                    links_md = ""
                    for score in overall[:20]:
                        company_name = getattr(score, 'company_name', '') or score.symbol
                        if len(company_name) > 20:
                            company_name = company_name[:17] + "..."
                        links_md += f"[{score.symbol}](https://finance.yahoo.com/quote/{score.symbol}) ({company_name}) | "
                    st.markdown(links_md[:-3], unsafe_allow_html=True)  # Remove trailing " | "
                else:
                    st.info("No data available")

            st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

            # Export screening results
            if results.get('overall'):
                st.markdown('<div class="sub-header">📥 Export Screening Results</div>', unsafe_allow_html=True)
                export_data = []
                for score in results.get('overall', []):
                    export_data.append({
                        'Symbol': score.symbol,
                        'Company': getattr(score, 'company_name', '') or score.symbol,
                        'Website': getattr(score, 'website', '') or '',
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
