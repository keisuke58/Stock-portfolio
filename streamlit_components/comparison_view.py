"""
銘柄比較ビューコンポーネント
"""
import streamlit as st
import pandas as pd
from typing import List, Dict
from streamlit_components.chart_components import (
    create_score_comparison_chart,
    create_radar_chart,
    create_price_chart
)


def render_comparison_view(comparison_data: List[Dict]):
    """
    銘柄比較ビューをレンダリング
    
    Args:
        comparison_data: 比較する銘柄のデータリスト
    """
    st.markdown('<div class="main-header">🔍 銘柄比較分析</div>', unsafe_allow_html=True)
    
    if not comparison_data:
        st.warning("比較する銘柄を選択してください")
        return
    
    # スコア比較チャート
    st.subheader("📊 スコア比較")
    chart_type = st.radio("チャートタイプ", ["グループバー", "積み上げバー"], horizontal=True)
    
    chart_data = [{
        'symbol': item.get('symbol', 'N/A'),
        'value_score': item.get('value_score', 0),
        'momentum_score': item.get('momentum_score', 0),
        'stability_score': item.get('stability_score', 0)
    } for item in comparison_data]
    
    st.plotly_chart(
        create_score_comparison_chart(chart_data, 'grouped' if chart_type == "グループバー" else 'bar'),
        use_container_width=True
    )
    
    st.markdown("---")
    
    # レーダーチャート
    st.subheader("🎯 レーダーチャート比較")
    radar_data = [{
        'name': item.get('symbol', 'N/A'),
        'value_score': item.get('value_score', 0),
        'momentum_score': item.get('momentum_score', 0),
        'stability_score': item.get('stability_score', 0)
    } for item in comparison_data]
    
    st.plotly_chart(
        create_radar_chart(radar_data),
        use_container_width=True
    )
    
    st.markdown("---")
    
    # 価格チャート比較
    st.subheader("📈 価格チャート比較")
    period = st.selectbox("期間", [30, 90, 180, 365], index=0, key="comparison_period")
    
    # 銘柄数に応じてカラム数を調整
    num_symbols = len(comparison_data)
    if num_symbols <= 2:
        cols = st.columns(num_symbols)
    elif num_symbols <= 3:
        cols = st.columns(3)
    else:
        cols = st.columns(min(num_symbols, 5))
    
    for idx, (col, data) in enumerate(zip(cols, comparison_data)):
        with col:
            symbol = data.get('symbol', 'N/A')
            prices = data.get('historical_prices', [])
            if prices:
                fig = create_price_chart(symbol, prices, period, show_ath=False, show_ma=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"{symbol}: データなし")
    
    st.markdown("---")
    
    # 比較テーブル
    st.subheader("📋 詳細比較テーブル")
    comparison_df = pd.DataFrame([
        {
            'シンボル': item.get('symbol', 'N/A'),
            '総合スコア': item.get('total_score', item.get('investment_score', 0)),
            'Value': item.get('value_score', 0),
            'Momentum': item.get('momentum_score', 0),
            'Stability': item.get('stability_score', 0),
            '現在価格': item.get('current_price', 0),
            '状態': item.get('current_state', 'NORMAL'),
            '投資スタンス': item.get('investment_stance', '様子見'),
            'リスクレベル': item.get('risk_level', '中')
        }
        for item in comparison_data
    ])
    
    st.dataframe(comparison_df, use_container_width=True)
    
    # 追加の比較指標（財務指標がある場合）
    financial_data_list = [item.get('financial_data') for item in comparison_data if item.get('financial_data')]
    if financial_data_list:
        st.markdown("---")
        st.subheader("💰 財務指標比較")
        
        # 主要財務指標の比較テーブル
        financial_comparison = []
        for item in comparison_data:
            symbol = item.get('symbol', 'N/A')
            financial = item.get('financial_data', {})
            if financial:
                financial_comparison.append({
                    'シンボル': symbol,
                    'PER': financial.get('pe_ratio', 'N/A'),
                    'PBR': financial.get('pb_ratio', 'N/A'),
                    'ROE': f"{financial.get('roe', 0)*100:.2f}%" if financial.get('roe') else 'N/A',
                    'ROA': f"{financial.get('roa', 0)*100:.2f}%" if financial.get('roa') else 'N/A',
                    '売上成長率': f"{financial.get('revenue_growth', 0)*100:+.2f}%" if financial.get('revenue_growth') else 'N/A',
                    '利益率': f"{financial.get('profit_margin', 0)*100:.2f}%" if financial.get('profit_margin') else 'N/A'
                })
        
        if financial_comparison:
            financial_df = pd.DataFrame(financial_comparison)
            st.dataframe(financial_df, use_container_width=True)
