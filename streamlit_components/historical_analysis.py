"""
履歴分析コンポーネント
スコア推移、バックテスト結果の表示
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Optional
from datetime import datetime, timedelta


def render_historical_analysis(symbol: str, historical_data: Optional[List[Dict]] = None):
    """履歴分析をレンダリング"""
    st.subheader("📊 履歴分析")
    
    if not historical_data:
        st.info("履歴データがありません。過去のスコア推移を表示するには、データの蓄積が必要です。")
        return
    
    # スコア推移チャート
    dates = [datetime.fromisoformat(d['date']) for d in historical_data]
    total_scores = [d.get('total_score', 0) for d in historical_data]
    value_scores = [d.get('value_score', 0) for d in historical_data]
    momentum_scores = [d.get('momentum_score', 0) for d in historical_data]
    stability_scores = [d.get('stability_score', 0) for d in historical_data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=total_scores,
        mode='lines+markers',
        name='総合スコア',
        line=dict(color='#1f77b4', width=2),
        hovertemplate='<b>総合スコア</b><br>日付: %{x|%Y-%m-%d}<br>スコア: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=value_scores,
        mode='lines',
        name='Value',
        line=dict(color='#ff7f0e', width=1.5, dash='dot'),
        hovertemplate='Value: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=momentum_scores,
        mode='lines',
        name='Momentum',
        line=dict(color='#2ca02c', width=1.5, dash='dot'),
        hovertemplate='Momentum: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=stability_scores,
        mode='lines',
        name='Stability',
        line=dict(color='#d62728', width=1.5, dash='dot'),
        hovertemplate='Stability: %{y:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f"{symbol} - スコア推移",
        xaxis=dict(title="日付"),
        yaxis=dict(title="スコア", range=[0, 100]),
        hovermode='x unified',
        template='plotly_white',
        height=500,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 統計サマリー
    if len(total_scores) > 0:
        st.markdown("---")
        st.subheader("📈 統計サマリー")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("平均スコア", f"{sum(total_scores) / len(total_scores):.1f}")
        with col2:
            st.metric("最高スコア", f"{max(total_scores):.1f}")
        with col3:
            st.metric("最低スコア", f"{min(total_scores):.1f}")
        with col4:
            score_change = total_scores[-1] - total_scores[0] if len(total_scores) > 1 else 0
            st.metric("変化", f"{score_change:+.1f}")


def render_backtest_results(backtest_data: Optional[Dict] = None):
    """バックテスト結果をレンダリング"""
    st.subheader("🔬 バックテスト結果")
    
    if not backtest_data:
        st.info("バックテスト結果がありません。")
        return
    
    # パフォーマンスメトリクス
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総リターン", f"{backtest_data.get('total_return', 0):.2f}%")
    with col2:
        st.metric("年率リターン", f"{backtest_data.get('annual_return', 0):.2f}%")
    with col3:
        st.metric("シャープレシオ", f"{backtest_data.get('sharpe_ratio', 0):.2f}")
    with col4:
        st.metric("最大ドローダウン", f"{backtest_data.get('max_drawdown', 0):.2f}%")
    
    # パフォーマンスチャート
    if 'equity_curve' in backtest_data:
        equity_dates = [datetime.fromisoformat(d['date']) for d in backtest_data['equity_curve']]
        equity_values = [d['value'] for d in backtest_data['equity_curve']]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_dates,
            y=equity_values,
            mode='lines',
            name='エクイティカーブ',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        fig.update_layout(
            title="エクイティカーブ",
            xaxis=dict(title="日付"),
            yaxis=dict(title="ポートフォリオ価値"),
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
