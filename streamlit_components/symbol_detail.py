"""
個別銘柄詳細ビューコンポーネント
"""
import streamlit as st
from typing import Dict, Optional
from streamlit_components.chart_components import (
    create_price_chart, 
    create_radar_chart,
    create_candlestick_chart,
    create_volume_chart,
    create_price_volume_chart
)
from streamlit_components.metrics_display import (
    display_financial_metrics,
    display_score_breakdown,
    display_investment_summary
)
from streamlit_components.export_components import export_chart_button
from streamlit_components.historical_analysis import render_historical_analysis
from streamlit_components.insights_display import add_chart_annotations
from signals import is_crypto_symbol


def render_symbol_detail(data: Dict, symbol: str):
    """
    個別銘柄詳細ビューをレンダリング
    
    Args:
        data: 銘柄の詳細データ
        symbol: シンボル名
    """
    st.markdown('<div class="main-header">📈 銘柄詳細分析</div>', unsafe_allow_html=True)
    
    if not data:
        st.error(f"{symbol}のデータが取得できませんでした")
        return
    
    # 基本情報
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("現在価格", f"${data.get('current_price', 0):,.2f}")
    with col2:
        total_score = data.get('total_score', data.get('investment_score', 0))
        st.metric("総合スコア", f"{total_score:.1f}")
    with col3:
        state = data.get('current_state', 'NORMAL')
        st.metric("状態", state)
    
    st.markdown("---")
    
    # 価格チャート
    st.subheader("📊 価格チャート")
    
    # チャートタイプ選択
    chart_type = st.radio(
        "チャートタイプ",
        ["ライン", "ローソク足", "出来高", "価格+出来高"],
        horizontal=True,
        key="chart_type"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        period = st.selectbox("期間", [30, 90, 180, 365], index=0, key="period")
    with col2:
        show_ath = st.checkbox("ATHライン表示", value=True, key="show_ath")
    with col3:
        show_ma = st.checkbox("移動平均線表示", value=True, key="show_ma")
    
    prices = data.get('historical_prices', [])
    
    fig = None
    if chart_type == "ライン":
        if prices:
            fig = create_price_chart(symbol, prices, period, show_ath, show_ma)
            # インサイトアノテーションを追加
            fig = add_chart_annotations(fig, data, prices)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("価格データがありません")
    elif chart_type == "ローソク足":
        show_volume = st.checkbox("出来高を表示", value=False, key="show_volume_candle")
        fig = create_candlestick_chart(symbol, period, show_ma, show_volume)
        st.plotly_chart(fig, use_container_width=True)
    elif chart_type == "出来高":
        show_price = st.checkbox("価格を表示", value=True, key="show_price_volume")
        fig = create_volume_chart(symbol, period, show_price)
        st.plotly_chart(fig, use_container_width=True)
    elif chart_type == "価格+出来高":
        show_indicators = st.checkbox("テクニカル指標を表示", value=True, key="show_indicators")
        fig = create_price_volume_chart(symbol, period, show_indicators)
        st.plotly_chart(fig, use_container_width=True)
    
    # チャート画像エクスポート
    if fig is not None:
        with st.expander("📷 チャート画像をエクスポート"):
            export_chart_button(fig, chart_name=f"{symbol}_chart")
    
    st.markdown("---")
    
    # スコア内訳と財務指標
    col1, col2 = st.columns(2)
    
    with col1:
        display_score_breakdown(
            data.get('value_score', 0),
            data.get('momentum_score', 0),
            data.get('stability_score', 0),
            total_score
        )
        
        # レーダーチャート
        st.subheader("🎯 スコアレーダーチャート")
        radar_data = [{
            'name': symbol,
            'value_score': data.get('value_score', 0),
            'momentum_score': data.get('momentum_score', 0),
            'stability_score': data.get('stability_score', 0)
        }]
        st.plotly_chart(
            create_radar_chart(radar_data),
            use_container_width=True
        )
    
    with col2:
        display_investment_summary(data)
        
        # 財務指標（米国株の場合）
        if not is_crypto_symbol(symbol) and 'financial_data' in data:
            st.subheader("💰 財務指標")
            display_financial_metrics(data['financial_data'])
            
            # 企業情報
            if 'company_info' in data and data['company_info']:
                st.subheader("🏢 企業情報")
                company_info = data['company_info']
                if company_info.get('company_name'):
                    st.write(f"**企業名**: {company_info['company_name']}")
                if company_info.get('sector'):
                    st.write(f"**セクター**: {company_info['sector']}")
                if company_info.get('industry'):
                    st.write(f"**業界**: {company_info['industry']}")
                
                # アナリスト評価
                if 'analyst_data' in data and data['analyst_data']:
                    st.subheader("📊 アナリスト評価")
                    analyst_data = data['analyst_data']
                    if analyst_data.get('recommendation'):
                        st.write(f"**推奨**: {analyst_data['recommendation']}")
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    target = analyst_data['target_mean_price']
                    current = analyst_data['current_price']
                    upside = ((target - current) / current) * 100 if current > 0 else 0
                    st.write(f"**目標株価**: ${target:.2f}")
                    st.write(f"**上昇余地**: {upside:+.1f}%")
    
    # 履歴分析
    st.markdown("---")
    historical_data = data.get('historical_scores', [])
    if historical_data:
        render_historical_analysis(symbol, historical_data)
