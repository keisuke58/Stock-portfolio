"""
Streamlit投資分析ダッシュボード
最高完成度の可視化ダッシュボード
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

from investment_analyzer import InvestmentAnalyzer
from signals import get_historical_prices, is_crypto_symbol
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

# ページ設定
st.set_page_config(
    page_title="投資分析ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


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
def load_config(config_path: str = "config.json") -> Dict:
    """設定ファイルを読み込む（Streamlit Cloud Secrets対応）"""
    config = {}
    
    # まずStreamlit Secretsを試す（Streamlit Cloud用）
    try:
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            config = dict(st.secrets)
            return config
    except Exception:
        pass
    
    # 次にconfig.jsonファイルを試す（ローカル開発用）
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
    except Exception as e:
        st.warning(f"設定ファイル読み込みエラー: {e}")
    
    # デフォルト値: 全銘柄リスト（約20000件）
    if not config or not config.get('symbols'):
        all_tickers = get_all_tickers()
        config = {
            "symbols": all_tickers,
            "check_interval": 3600
        }
        st.info(f"デフォルト設定を使用しています。{len(all_tickers)}件の銘柄を監視します。設定ファイルまたはSecretsを設定してカスタマイズできます。")
    
    return config


@st.cache_data(ttl=1800)  # 30分キャッシュ
def get_analysis_data(symbols: List[str], max_assets: int = 200) -> List[Dict]:
    """投資分析データを取得"""
    try:
        analyzer = InvestmentAnalyzer()
        results = analyzer.analyze_all_assets(symbols, max_assets=max_assets)
        return results
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        import traceback
        st.exception(e)
        return []


@st.cache_data(ttl=1800)
def get_symbol_detail_data(symbol: str) -> Optional[Dict]:
    """個別銘柄の詳細データを取得"""
    try:
        analyzer = InvestmentAnalyzer()
        score_data = analyzer.calculate_investment_score(symbol)
        
        if not score_data:
            return None
        
        # 財務データを追加
        if not is_crypto_symbol(symbol):
            try:
                financial_data = analyzer.get_comprehensive_financial_data(symbol)
                company_info = analyzer.get_company_info(symbol)
                analyst_data = analyzer.get_analyst_recommendations(symbol)
                
                score_data['financial_data'] = financial_data
                score_data['company_info'] = company_info
                score_data['analyst_data'] = analyst_data
            except Exception as e:
                st.warning(f"財務データの取得に失敗しました ({symbol}): {e}")
        
        # 価格データを追加
        try:
            prices = get_historical_prices(symbol, days=365)
            score_data['historical_prices'] = prices
        except Exception as e:
            st.warning(f"価格データの取得に失敗しました ({symbol}): {e}")
            score_data['historical_prices'] = []
        
        return score_data
    except Exception as e:
        st.error(f"銘柄データ取得エラー ({symbol}): {e}")
        import traceback
        st.exception(e)
        return None


def main():
    """メインアプリケーション"""
    # サイドバー
    with st.sidebar:
        st.title("📊 投資分析ダッシュボード")
        st.markdown("---")
        
        # ページ選択
        page = st.radio(
            "ページを選択",
            ["🏠 ホーム", "📈 銘柄詳細", "🔍 比較分析", "⚙️ 設定"],
            index=0
        )
        
        st.markdown("---")
        
        # 設定読み込み
        config = load_config()
        symbols = config.get('symbols', [])
        
        if not symbols:
            st.warning("設定ファイルにシンボルがありません")
            st.stop()
        
        st.info(f"監視銘柄数: {len(symbols)}")
        
        # データ更新ボタン
        if st.button("🔄 データを更新"):
            st.cache_data.clear()
            st.rerun()
    
    # メインコンテンツ
    if page == "🏠 ホーム":
        show_home_page(symbols)
    elif page == "📈 銘柄詳細":
        show_symbol_detail_page(symbols)
    elif page == "🔍 比較分析":
        show_comparison_page(symbols)
    elif page == "⚙️ 設定":
        show_settings_page()


def show_home_page(symbols: List[str]):
    """ホームページを表示"""
    # データ取得
    try:
        with st.spinner("データを取得中..."):
            data = get_analysis_data(symbols, max_assets=200)
        
        if not data:
            st.error("データが取得できませんでした。設定ファイルを確認してください。")
            return
        
        # コンポーネントを使用してレンダリング
        render_home_dashboard(data)
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.exception(e)


def show_symbol_detail_page(symbols: List[str]):
    """銘柄詳細ページを表示"""
    # 銘柄選択
    symbol = st.selectbox("銘柄を選択", symbols)
    
    if not symbol:
        st.warning("銘柄を選択してください")
        return
    
    # データ取得
    try:
        with st.spinner(f"{symbol}のデータを取得中..."):
            data = get_symbol_detail_data(symbol)
        
        if not data:
            st.error(f"{symbol}のデータが取得できませんでした")
            return
        
        # コンポーネントを使用してレンダリング
        render_symbol_detail(data, symbol)
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.exception(e)


def show_comparison_page(symbols: List[str]):
    """比較分析ページを表示"""
    # 銘柄選択（最大5個）
    selected_symbols = st.multiselect(
        "比較する銘柄を選択（最大5個）",
        symbols,
        max_selections=5
    )
    
    if not selected_symbols:
        st.warning("比較する銘柄を選択してください")
        return
    
    # データ取得
    try:
        comparison_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, symbol in enumerate(selected_symbols):
            status_text.text(f"{symbol}のデータを取得中... ({idx+1}/{len(selected_symbols)})")
            data = get_symbol_detail_data(symbol)
            if data:
                comparison_data.append(data)
            progress_bar.progress((idx + 1) / len(selected_symbols))
        
        progress_bar.empty()
        status_text.empty()
        
        if not comparison_data:
            st.error("データが取得できませんでした")
            return
        
        # コンポーネントを使用してレンダリング
        render_comparison_view(comparison_data)
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.exception(e)


def show_settings_page():
    """設定ページを表示"""
    st.markdown('<div class="main-header">⚙️ 設定</div>', unsafe_allow_html=True)
    
    st.subheader("設定情報")
    
    config = load_config()
    
    st.write(f"**設定ファイル**: config.json")
    st.write(f"**監視銘柄数**: {len(config.get('symbols', []))}")
    
    st.markdown("---")
    
    st.subheader("データ更新")
    st.write("データは自動的にキャッシュされます。")
    st.write("- 分析データ: 30分間キャッシュ")
    st.write("- 銘柄詳細: 30分間キャッシュ")
    st.write("- 設定ファイル: 1時間キャッシュ")
    
    if st.button("🔄 全キャッシュをクリア"):
        st.cache_data.clear()
        st.success("キャッシュをクリアしました")
        st.rerun()


if __name__ == "__main__":
    main()
