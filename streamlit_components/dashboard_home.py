"""
ホームダッシュボードコンポーネント
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
    ホームダッシュボードをレンダリング
    
    Args:
        data: 投資分析結果のリスト
    """
    st.markdown('<div class="main-header">📊 投資分析ダッシュボード</div>', unsafe_allow_html=True)
    
    if not data:
        st.error("データが取得できませんでした")
        return
    
    # KPIメトリクス
    st.subheader("📈 主要メトリクス")
    col1, col2, col3, col4 = st.columns(4)
    
    avg_score = sum(item.get('total_score', item.get('investment_score', 0)) for item in data) / len(data) if data else 0
    buy_count = sum(1 for item in data if item.get('current_state') == 'BUY')
    top_score = max((item.get('total_score', item.get('investment_score', 0)) for item in data), default=0)
    
    with col1:
        st.metric("平均スコア", f"{avg_score:.1f}")
    with col2:
        st.metric("BUY候補数", buy_count)
    with col3:
        st.metric("最高スコア", f"{top_score:.1f}")
    with col4:
        st.metric("分析銘柄数", len(data))
    
    st.markdown("---")
    
    # トップ10銘柄カード
    st.subheader("🏆 トップ10銘柄")
    top_10 = sorted(data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True)[:10]
    
    # カード表示
    cols = st.columns(5)
    for idx, item in enumerate(top_10[:10]):
        col = cols[idx % 5]
        with col:
            symbol = item.get('symbol', 'N/A')
            score = item.get('total_score', item.get('investment_score', 0))
            state = item.get('current_state', 'NORMAL')
            
            # 状態に応じた色
            if state == 'BUY':
                st.success(f"**{symbol}**\nスコア: {score:.1f}\n状態: {state}")
            elif state == 'BASE':
                st.warning(f"**{symbol}**\nスコア: {score:.1f}\n状態: {state}")
            elif state == 'WATCH':
                st.error(f"**{symbol}**\nスコア: {score:.1f}\n状態: {state}")
            else:
                st.info(f"**{symbol}**\nスコア: {score:.1f}\n状態: {state}")
    
    st.markdown("---")
    
    # データテーブル
    st.subheader("📋 全銘柄一覧")
    
    # 高度なフィルタリング
    with st.expander("🔍 高度なフィルタリング", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_state = st.multiselect("状態でフィルタ", ["BUY", "BASE", "WATCH", "NORMAL"], default=[])
        with col2:
            categories = list(set(item.get('category', 'その他') for item in data))
            filter_category = st.multiselect("カテゴリでフィルタ", categories, default=[])
        with col3:
            score_range = st.slider("スコア範囲", 0, 100, (0, 100))
        
        # 全文検索
        search_query = st.text_input("🔎 全文検索（シンボル名、カテゴリなど）", "")
    
    # フィルタリング適用
    filtered_data = data
    
    # 状態フィルタ
    if filter_state:
        filtered_data = [item for item in filtered_data if item.get('current_state') in filter_state]
    
    # カテゴリフィルタ
    if filter_category:
        filtered_data = [item for item in filtered_data if item.get('category') in filter_category]
    
    # スコア範囲フィルタ
    filtered_data = [item for item in filtered_data 
                     if score_range[0] <= item.get('total_score', item.get('investment_score', 0)) <= score_range[1]]
    
    # 全文検索
    if search_query:
        search_lower = search_query.lower()
        filtered_data = [item for item in filtered_data 
                        if search_lower in item.get('symbol', '').lower() 
                        or search_lower in item.get('category', '').lower()
                        or search_lower in str(item.get('investment_stance', '')).lower()]
    
    st.info(f"フィルタ結果: {len(filtered_data)}件 / 全{len(data)}件")
    
    # テーブル表示
    df = pd.DataFrame([
        {
            '順位': idx + 1,
            'シンボル': item.get('symbol', 'N/A'),
            'カテゴリ': item.get('category', 'その他'),
            '状態': item.get('current_state', 'NORMAL'),
            '総合スコア': item.get('total_score', item.get('investment_score', 0)),
            'Value': item.get('value_score', 0),
            'Momentum': item.get('momentum_score', 0),
            'Stability': item.get('stability_score', 0),
            '価格': item.get('current_price', 0),
            '投資スタンス': item.get('investment_stance', '様子見')
        }
        for idx, item in enumerate(sorted(filtered_data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True))
    ])
    
    st.dataframe(df, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # チャート
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_score_distribution_chart(data),
            use_container_width=True
        )
    
    with col2:
        # カテゴリ別分布
        category_counts = {}
        for item in data:
            cat = item.get('category', 'その他')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if category_counts:
            st.plotly_chart(
                create_donut_chart(
                    list(category_counts.keys()),
                    list(category_counts.values()),
                    "カテゴリ別分布"
                ),
                use_container_width=True
            )
    
    st.markdown("---")
    
    # メトリクスヒートマップ（トップ20銘柄）
    st.subheader("🔥 メトリクス比較ヒートマップ（トップ20）")
    top_20 = sorted(data, key=lambda x: x.get('total_score', x.get('investment_score', 0)), reverse=True)[:20]
    try:
        metrics_fig = create_metrics_heatmap(top_20)
        st.plotly_chart(metrics_fig, use_container_width=True)
    except Exception as e:
        st.warning(f"ヒートマップの生成に失敗しました: {e}")
    
    st.markdown("---")
    
    # エクスポート機能
    create_export_buttons(filtered_data, filename_prefix="investment_analysis")
