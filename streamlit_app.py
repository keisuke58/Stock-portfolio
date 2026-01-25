"""
Investment Analysis Dashboard
Professional stock analysis and screening platform
"""
import streamlit as st
import json
import sys
import os
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signals import is_crypto_symbol
from services.config_service import load_config
from services.analysis_service import get_analysis_data
from services.symbol_service import get_symbol_detail_data
from streamlit_components.chart_components import (
    create_price_chart,
    create_radar_chart,
    create_score_comparison_chart,
    create_score_distribution_chart,
    create_donut_chart
)
from streamlit_components.metrics_display import (
    display_financial_metrics,
    display_score_breakdown,
    display_investment_summary
)
from streamlit_components.dashboard_home import render_home_dashboard
from streamlit_components.symbol_detail import render_symbol_detail
from streamlit_components.comparison_view import render_comparison_view
from streamlit_components.portfolio_tracker import render_portfolio_page
from streamlit_components.alert_manager import render_alerts_page
from streamlit_components.explanation_page import render_explanation_page
from streamlit_components.backtest_page import render_backtest_page
from streamlit_components.deep_bottom_page import render_deep_bottom_page
from streamlit_components.ten_bagger_page import render_ten_bagger_page

# Page configuration
st.set_page_config(
    page_title="Investment Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark mode detection
dark_mode = st.session_state.get('dark_mode', False)

# カスタムCSS - モダンでプロフェッショナルなデザイン（ダークモード対応）
if dark_mode:
    css_template = """
<style>
    /* ダークモード */
    .stApp {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        letter-spacing: -0.02em;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #a78bfa;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        color: #e0e0e0;
    }
    
    [data-testid="stMetricValue"] {
        color: #e0e0e0;
    }
    
    h1, h2, h3 {
        color: #e0e0e0;
    }
</style>
"""
else:
    css_template = """
<style>
    /* メインヘッダー */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        letter-spacing: -0.02em;
    }
    
    /* メトリクスカード */
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* ボタンスタイル */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* カードコンテナ */
    .asset-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    .asset-card:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }
    
    /* セクションヘッダー */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    
    /* テーブルスタイル */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* サイドバー */
    .css-1d391kg {
        background: linear-gradient(180deg, #f5f7fa 0%, #ffffff 100%);
    }
    
    /* プログレスバー */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* アニメーション */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* スクロールバー */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
    }
    
    /* レスポンシブデザイン */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
            padding: 1rem 0;
        }
        
        .metric-card {
            padding: 1rem;
            margin-bottom: 0.5rem;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        
        .stButton>button {
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }
    }
    
    @media (max-width: 480px) {
        .main-header {
            font-size: 1.5rem;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }
    }
    
    /* メトリクス値の強調 */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    
    /* サブヘッダー */
    h3 {
        color: #2c3e50;
        font-weight: 600;
        margin-top: 2rem;
    }
</style>
"""

st.markdown(css_template, unsafe_allow_html=True)


@st.cache_data(ttl=86400)  # 24時間キャッシュ（全銘柄リストは変更頻度が低い）
def get_all_tickers() -> List[str]:
    """全銘柄リストを取得（約20000件）"""
    try:
        from collect_tickers import (
            get_sp500_tickers,
            get_nasdaq_tickers,
            get_all_nasdaq_listed,
            get_all_nyse_listed,
            get_popular_etfs,
            get_extended_etfs,
            get_quantum_ai_stocks,
            get_growth_stocks,
            get_nyse_major_stocks,
            get_small_mid_cap_growth,
            get_more_stocks
        )
        
        all_tickers = []
        
        # 各ソースから銘柄を収集
        all_tickers.extend(get_sp500_tickers())
        all_tickers.extend(get_nasdaq_tickers())
        all_tickers.extend(get_all_nasdaq_listed())
        all_tickers.extend(get_all_nyse_listed())
        all_tickers.extend(get_popular_etfs())
        all_tickers.extend(get_extended_etfs())
        all_tickers.extend(get_quantum_ai_stocks())
        all_tickers.extend(get_growth_stocks())
        all_tickers.extend(get_nyse_major_stocks())
        all_tickers.extend(get_small_mid_cap_growth())
        all_tickers.extend(get_more_stocks())
        
        # 重複除去
        unique_tickers = list(set([t.upper() for t in all_tickers if t]))
        
        # 主要な暗号通貨も追加
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX']
        for crypto in crypto_symbols:
            if crypto not in unique_tickers:
                unique_tickers.append(crypto)
        
        return sorted(unique_tickers)
    except Exception as e:
        st.warning(f"全銘柄リスト取得エラー: {e}")
        # フォールバック: 基本的な銘柄リスト
        return ["BTC", "ETH", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "SPY", "QQQ"]


@st.cache_data(ttl=3600)  # 1時間キャッシュ
def load_config_cached(config_path: str = "config.json") -> Dict:
    """設定ファイルを読み込む（Streamlit Cloud Secrets対応、キャッシュ付き）"""
    config = load_config(config_path)
    
    # デフォルト値: 厳選1000銘柄（設定ファイルにsymbolsがない場合）
    if not config.get('symbols'):
        @st.cache_data(ttl=86400)  # 24時間キャッシュ
        def get_curated_1000_tickers() -> List[str]:
            """厳選1000銘柄を取得"""
            try:
                from collect_tickers import (
                    get_sp500_tickers,
                    get_nasdaq_tickers,
                    get_popular_etfs,
                    get_extended_etfs,
                    get_quantum_ai_stocks,
                    get_growth_stocks,
                    get_nyse_major_stocks,
                    get_small_mid_cap_growth,
                    get_more_stocks
                )
                
                all_tickers = []
                
                # 1. S&P500（約500件）
                all_tickers.extend(get_sp500_tickers())
                
                # 2. NASDAQ-100（約100件）
                all_tickers.extend(get_nasdaq_tickers())
                
                # 3. 人気ETF（約100件）
                all_tickers.extend(get_popular_etfs())
                
                # 4. 拡張ETF（約200件）
                extended_etfs = get_extended_etfs()
                all_tickers.extend(extended_etfs[:200])  # 上位200件に制限
                
                # 5. 量子/AI関連株（約50件）
                all_tickers.extend(get_quantum_ai_stocks())
                
                # 6. 成長株（約100件）
                all_tickers.extend(get_growth_stocks())
                
                # 7. NYSE主要銘柄（約100件）
                all_tickers.extend(get_nyse_major_stocks())
                
                # 8. 小型・中型成長株（約200件）
                small_mid = get_small_mid_cap_growth()
                all_tickers.extend(small_mid[:200])  # 上位200件に制限
                
                # 9. 追加の有望株（約150件）
                more_stocks = get_more_stocks()
                all_tickers.extend(more_stocks[:150])  # 上位150件に制限
                
                # 10. 主要暗号通貨（約20件）
                crypto_symbols = [
                    'BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX',
                    'LINK', 'UNI', 'ATOM', 'ALGO', 'VET', 'FIL', 'AAVE', 'MKR', 'COMP', 'SNX'
                ]
                all_tickers.extend(crypto_symbols)
                
                # 重複除去
                unique_tickers = list(set([t.upper() for t in all_tickers if t]))
                
                # 1000件に制限（優先順位順）
                if len(unique_tickers) > 1000:
                    # S&P500を優先的に保持
                    sp500_set = set([t.upper() for t in get_sp500_tickers()])
                    prioritized = [t for t in unique_tickers if t in sp500_set]
                    others = [t for t in unique_tickers if t not in sp500_set]
                    unique_tickers = prioritized + others[:1000 - len(prioritized)]
                
                return sorted(unique_tickers)
            except Exception as e:
                st.warning(f"厳選銘柄リスト取得エラー: {e}")
                # フォールバック: 基本的な銘柄リスト
                return ["BTC", "ETH", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "SPY", "QQQ"]
        
        curated_tickers = get_curated_1000_tickers()
        config['symbols'] = curated_tickers
        if 'check_interval' not in config:
            config['check_interval'] = 3600
        st.info(f"デフォルト設定を使用しています。{len(curated_tickers)}件の厳選銘柄を監視します。")
    
    return config


@st.cache_data(ttl=1800)  # 30分キャッシュ
def get_analysis_data_cached(symbols: List[str], max_assets: int = 200) -> List[Dict]:
    """投資分析データを取得（並列処理対応、キャッシュ付き）"""
    return get_analysis_data(symbols, max_assets)


@st.cache_data(ttl=1800)  # 30分キャッシュ
def get_symbol_detail_data_cached(symbol: str) -> Optional[Dict]:
    """個別銘柄の詳細データを取得（キャッシュ付き）"""
    return get_symbol_detail_data(symbol)


def main():
    """Main application"""
    # Sidebar
    with st.sidebar:
        st.title("📊 Investment Dashboard")
        st.markdown("---")

        # Page selection
        page = st.radio(
            "Select Page",
            [
                "🏠 Home",
                "💎 Deep Bottom",
                "🚀 Ten Bagger",
                "📈 Stock Detail",
                "💡 Analysis",
                "🔍 Compare",
                "🔬 Backtest",
                "💼 Portfolio",
                "🔔 Alerts",
                "⚙️ Settings"
            ],
            index=0
        )

        st.markdown("---")

        # Load configuration
        config = load_config_cached()
        symbols = config.get('symbols', [])

        if not symbols:
            st.warning("No symbols in configuration")
            st.stop()

        st.info(f"Tracking: {len(symbols)} symbols")

        # Real-time update settings
        st.markdown("---")
        st.subheader("🔄 Refresh Settings")
        auto_refresh = st.checkbox("Enable Auto-Refresh", value=st.session_state.get('auto_refresh', False))
        st.session_state.auto_refresh = auto_refresh
        if auto_refresh:
            refresh_interval = st.selectbox("Refresh Interval (sec)", [30, 60, 120, 300, 600], index=1, key="refresh_interval_select")
            st.session_state.refresh_interval = refresh_interval
            if 'last_refresh' not in st.session_state:
                st.session_state.last_refresh = datetime.now()

        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.session_state.last_refresh = datetime.now()
            st.rerun()

        # Refresh status
        if 'last_refresh' in st.session_state:
            time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
            st.caption(f"Last updated: {int(time_since_refresh)}s ago")
    
    # 自動更新処理
    if 'auto_refresh' in st.session_state and st.session_state.auto_refresh:
        if 'last_refresh' in st.session_state:
            refresh_interval = st.session_state.get('refresh_interval', 60)
            time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
            if time_since_refresh >= refresh_interval:
                st.cache_data.clear()
                st.session_state.last_refresh = datetime.now()
                st.rerun()
    
    # Main content routing
    if page == "🏠 Home":
        show_home_page(symbols)
    elif page == "💎 Deep Bottom":
        render_deep_bottom_page(symbols)
    elif page == "🚀 Ten Bagger":
        render_ten_bagger_page(symbols)
    elif page == "📈 Stock Detail":
        show_symbol_detail_page(symbols)
    elif page == "💡 Analysis":
        show_explanation_page(symbols)
    elif page == "🔍 Compare":
        show_comparison_page(symbols)
    elif page == "🔬 Backtest":
        render_backtest_page()
    elif page == "💼 Portfolio":
        render_portfolio_page()
    elif page == "🔔 Alerts":
        render_alerts_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_home_page(symbols: List[str]):
    """Display home page"""
    try:
        with st.spinner("Loading data..."):
            data = get_analysis_data_cached(symbols, max_assets=200)

        if not data:
            st.error("Failed to load data. Please check configuration.")
            return

        render_home_dashboard(data)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback
        st.exception(e)


def show_symbol_detail_page(symbols: List[str]):
    """Display stock detail page"""
    symbol = st.selectbox("Select Symbol", symbols)

    if not symbol:
        st.warning("Please select a symbol")
        return

    try:
        with st.spinner(f"Loading {symbol} data..."):
            data = get_symbol_detail_data_cached(symbol)

        if not data:
            st.error(f"Failed to load data for {symbol}")
            return

        render_symbol_detail(data, symbol)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback
        st.exception(e)


def show_explanation_page(symbols: List[str]):
    """Display analysis explanation page"""
    symbol = st.selectbox("Select Symbol", symbols, key="explanation_symbol")

    if not symbol:
        st.warning("Please select a symbol")
        return

    try:
        with st.spinner(f"Loading {symbol} data..."):
            data = get_symbol_detail_data_cached(symbol)

        if not data:
            st.error(f"Failed to load data for {symbol}")
            return

        render_explanation_page(symbol, data)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback
        st.exception(e)


def show_comparison_page(symbols: List[str]):
    """Display comparison analysis page"""
    selected_symbols = st.multiselect(
        "Select symbols to compare (max 5)",
        symbols,
        max_selections=5
    )

    if not selected_symbols:
        st.warning("Please select symbols to compare")
        return

    try:
        comparison_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, symbol in enumerate(selected_symbols):
            status_text.text(f"Loading {symbol}... ({idx+1}/{len(selected_symbols)})")
            data = get_symbol_detail_data_cached(symbol)
            if data:
                comparison_data.append(data)
            progress_bar.progress((idx + 1) / len(selected_symbols))

        progress_bar.empty()
        status_text.empty()

        if not comparison_data:
            st.error("Failed to load data")
            return

        render_comparison_view(comparison_data)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback
        st.exception(e)


def show_settings_page():
    """Display settings page"""
    st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)

    st.subheader("Configuration")

    config = load_config_cached()

    st.write(f"**Config File**: config.json")
    st.write(f"**Tracked Symbols**: {len(config.get('symbols', []))}")

    st.markdown("---")

    st.subheader("Cache Settings")
    st.write("Data is automatically cached:")
    st.write("- Analysis data: 30 min cache")
    st.write("- Stock details: 30 min cache")
    st.write("- Config file: 1 hour cache")

    if st.button("🔄 Clear All Cache"):
        st.cache_data.clear()
        st.success("Cache cleared successfully")
        st.rerun()


if __name__ == "__main__":
    main()
