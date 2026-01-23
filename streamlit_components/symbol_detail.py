"""
個別銘柄詳細ビューコンポーネント
"""
import streamlit as st
from typing import Dict, Optional
from streamlit_components.chart_components import create_price_chart, create_radar_chart
from streamlit_components.metrics_display import (
    display_financial_metrics,
    display_score_breakdown,
    display_investment_summary
)
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
    
    col1, col2 = st.columns([3, 1])
    with col1:
        period = st.selectbox("期間", [30, 90, 180, 365], index=0)
    with col2:
        show_ath = st.checkbox("ATHライン表示", value=True)
        show_ma = st.checkbox("移動平均線表示", value=True)
    
    prices = data.get('historical_prices', [])
    if prices:
        fig = create_price_chart(symbol, prices, period, show_ath, show_ma)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("価格データがありません")
    
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
