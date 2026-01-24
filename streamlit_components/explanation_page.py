"""
理由説明ページコンポーネント
スコアの内訳を視覚化し、各要素の寄与度を説明
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Optional, List
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.explainer import SignalExplainer
from services.symbol_service import get_symbol_detail_data


def create_score_breakdown_chart(scores: Dict, score_type: str = 'vms') -> go.Figure:
    """
    スコア内訳を棒グラフで表示
    
    Args:
        scores: スコア辞書
        score_type: スコアタイプ（'vms' または 'v2'）
    
    Returns:
        Plotly Figure
    """
    if score_type == 'v2':
        categories = ['Return', 'Risk', 'Confidence', 'Regime']
        values = [
            scores.get('return_score', 0),
            scores.get('risk_score', 0),
            scores.get('confidence_score', 0),
            scores.get('regime_score', 0)
        ]
        max_values = [40, 25, 20, 15]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    else:
        # VMSスコア
        categories = ['Value', 'Momentum', 'Stability']
        values = [
            scores.get('value_score', 0),
            scores.get('momentum_score', 0),
            scores.get('stability_score', 0)
        ]
        max_values = [100, 100, 100]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    # 正規化されたスコア（0-100%）
    normalized_values = [(v / m * 100) if m > 0 else 0 for v, m in zip(values, max_values)]
    
    fig = go.Figure()
    
    # 各カテゴリのバー
    for i, (cat, val, max_val, norm_val, color) in enumerate(zip(categories, values, max_values, normalized_values, colors)):
        fig.add_trace(go.Bar(
            x=[cat],
            y=[norm_val],
            name=cat,
            marker_color=color,
            text=[f"{val:.1f}/{max_val}"],
            textposition='outside',
            hovertemplate=f'<b>{cat}</b><br>スコア: {val:.1f}/{max_val}<br>正規化: {norm_val:.1f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title="スコア内訳",
        xaxis=dict(title="カテゴリ"),
        yaxis=dict(title="正規化スコア (%)", range=[0, 100]),
        barmode='group',
        height=400,
        template='plotly_white',
        showlegend=False
    )
    
    return fig


def create_contribution_chart(scores: Dict, score_type: str = 'vms') -> go.Figure:
    """
    各要素の寄与度をドーナツチャートで表示
    
    Args:
        scores: スコア辞書
        score_type: スコアタイプ（'vms' または 'v2'）
    
    Returns:
        Plotly Figure
    """
    if score_type == 'v2':
        labels = ['Return (40点)', 'Risk (25点)', 'Confidence (20点)', 'Regime (15点)']
        values = [
            scores.get('return_score', 0),
            scores.get('risk_score', 0),
            scores.get('confidence_score', 0),
            scores.get('regime_score', 0)
        ]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    else:
        # VMSスコア
        labels = ['Value (40%)', 'Momentum (35%)', 'Stability (25%)']
        values = [
            scores.get('value_score', 0) * 0.4,
            scores.get('momentum_score', 0) * 0.35,
            scores.get('stability_score', 0) * 0.25
        ]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    total_score = sum(values)
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker_colors=colors,
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>寄与度: %{value:.1f}<br>割合: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=f"総合スコアへの寄与度<br><sub>総合スコア: {total_score:.1f}</sub>",
        height=400,
        template='plotly_white',
        annotations=[dict(text=f'{total_score:.1f}', x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    
    return fig


def create_state_timeline(features_history: List[Dict]) -> go.Figure:
    """
    状態変化の理由を時系列で表示
    
    Args:
        features_history: 履歴特徴量のリスト
    
    Returns:
        Plotly Figure
    """
    if not features_history:
        fig = go.Figure()
        fig.add_annotation(
            text="履歴データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    dates = [datetime.fromisoformat(d.get('date', '')) for d in features_history]
    states = [d.get('state', 'NORMAL') for d in features_history]
    scores = [d.get('total_score', 0) for d in features_history]
    
    state_colors = {
        'WATCH': '#ff7f0e',
        'BASE': '#2ca02c',
        'BUY': '#d62728',
        'NORMAL': '#1f77b4'
    }
    
    colors = [state_colors.get(state, '#808080') for state in states]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode='lines+markers',
        name='総合スコア',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8, color=colors),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>状態: %{customdata}<br>スコア: %{y:.1f}<extra></extra>',
        customdata=states
    ))
    
    # 状態変化のアノテーション
    for i in range(1, len(states)):
        if states[i] != states[i-1]:
            fig.add_annotation(
                x=dates[i],
                y=scores[i],
                text=f"{states[i-1]} → {states[i]}",
                showarrow=True,
                arrowhead=2,
                arrowcolor=colors[i],
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor=colors[i]
            )
    
    fig.update_layout(
        title="状態変化とスコア推移",
        xaxis=dict(title="日付"),
        yaxis=dict(title="総合スコア", range=[0, 100]),
        height=400,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def render_explanation_page(symbol: str, data: Optional[Dict] = None):
    """
    理由説明ページをレンダリング
    
    Args:
        symbol: シンボル名
        data: 銘柄データ（Noneの場合は取得）
    """
    st.markdown('<div class="main-header">💡 理由説明</div>', unsafe_allow_html=True)
    
    if data is None:
        with st.spinner(f"{symbol}のデータを取得中..."):
            data = get_symbol_detail_data(symbol)
    
    if not data:
        st.error(f"{symbol}のデータが取得できませんでした")
        return
    
    explainer = SignalExplainer()
    
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
    
    # スコア内訳
    st.subheader("📊 スコア内訳")
    
    # スコアタイプ判定
    score_type = 'vms'
    if 'return_score' in data or 'risk_score' in data:
        score_type = 'v2'
    
    scores = {}
    if score_type == 'v2':
        scores = {
            'return_score': data.get('return_score', 0),
            'risk_score': data.get('risk_score', 0),
            'confidence_score': data.get('confidence_score', 0),
            'regime_score': data.get('regime_score', 0),
            'total_score': total_score
        }
    else:
        scores = {
            'value_score': data.get('value_score', 0),
            'momentum_score': data.get('momentum_score', 0),
            'stability_score': data.get('stability_score', 0),
            'total_score': total_score
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_score_breakdown_chart(scores, score_type),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_contribution_chart(scores, score_type),
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 詳細説明
    st.subheader("📝 詳細説明")
    
    features = {
        'ath_ratio': data.get('ath_ratio'),
        'volatility': data.get('volatility'),
        'return_30d': data.get('return_30d'),
        'return_7d': data.get('return_7d'),
        'return_3d': data.get('return_3d'),
        'range_7d': data.get('range_7d'),
        'breakout_5d': data.get('breakout_5d', False),
        'current_price': data.get('current_price'),
        'high_5d': data.get('high_5d')
    }
    
    old_state = data.get('previous_state')
    current_state = data.get('current_state', 'NORMAL')
    data_layers_used = data.get('data_layers_used')
    market_regime = data.get('market_regime')
    
    explanations = explainer.explain_signal(
        symbol,
        current_state,
        features,
        scores,
        old_state,
        data_layers_used,
        market_regime,
        score_type
    )
    
    if explanations:
        for i, explanation in enumerate(explanations, 1):
            st.markdown(f"**{i}.** {explanation}")
    else:
        st.info("説明データがありません")
    
    st.markdown("---")
    
    # 状態変化の時系列
    st.subheader("📈 状態変化の時系列")
    
    historical_data = data.get('historical_scores', [])
    if historical_data:
        # 状態情報を追加
        features_history = []
        for h in historical_data:
            features_history.append({
                'date': h.get('date', ''),
                'state': h.get('state', 'NORMAL'),
                'total_score': h.get('total_score', 0)
            })
        
        st.plotly_chart(
            create_state_timeline(features_history),
            use_container_width=True
        )
    else:
        st.info("履歴データがありません。状態変化の時系列を表示するには、データの蓄積が必要です。")
    
    st.markdown("---")
    
    # 各要素の詳細
    st.subheader("🔍 各要素の詳細")
    
    if score_type == 'v2':
        with st.expander("Returnスコア（40点満点）", expanded=True):
            return_score = scores.get('return_score', 0)
            st.write(f"**スコア**: {return_score:.1f}/40点")
            st.write("**説明**: 30日リターンと7日リターンから計算されます。")
            st.write("- 30日リターンが-30%以下: 0点")
            st.write("- 30日リターンが-20%以下: 5点")
            st.write("- 30日リターンが-10%以下: 20点")
            st.write("- 30日リターンが0%以下: 30点")
            st.write("- 30日リターンが10%以下: 35点")
            st.write("- 30日リターンが30%以下: 40点")
            st.write("- 7日リターンがプラス: +5点ボーナス")
        
        with st.expander("Riskスコア（25点満点）", expanded=False):
            risk_score = scores.get('risk_score', 0)
            st.write(f"**スコア**: {risk_score:.1f}/25点")
            st.write("**説明**: ボラティリティと最大ドローダウンから計算されます。")
        
        with st.expander("Confidenceスコア（20点満点）", expanded=False):
            confidence_score = scores.get('confidence_score', 0)
            st.write(f"**スコア**: {confidence_score:.1f}/20点")
            st.write("**説明**: 使用されたデータレイヤーと状態から計算されます。")
        
        with st.expander("Regimeスコア（15点満点）", expanded=False):
            regime_score = scores.get('regime_score', 0)
            st.write(f"**スコア**: {regime_score:.1f}/15点")
            st.write("**説明**: 市場レジームとボラティリティから計算されます。")
    else:
        # VMSスコア
        with st.expander("Valueスコア（100点満点、重み40%）", expanded=True):
            value_score = scores.get('value_score', 0)
            st.write(f"**スコア**: {value_score:.1f}/100点")
            st.write(f"**寄与度**: {value_score * 0.4:.1f}点（総合スコアへの寄与）")
            st.write("**説明**: ATH比とPERから計算されます。割安度を示します。")
        
        with st.expander("Momentumスコア（100点満点、重み35%）", expanded=False):
            momentum_score = scores.get('momentum_score', 0)
            st.write(f"**スコア**: {momentum_score:.1f}/100点")
            st.write(f"**寄与度**: {momentum_score * 0.35:.1f}点（総合スコアへの寄与）")
            st.write("**説明**: 状態、ブレイク、リターンから計算されます。反転の可能性を示します。")
        
        with st.expander("Stabilityスコア（100点満点、重み25%）", expanded=False):
            stability_score = scores.get('stability_score', 0)
            st.write(f"**スコア**: {stability_score:.1f}/100点")
            st.write(f"**寄与度**: {stability_score * 0.25:.1f}点（総合スコアへの寄与）")
            st.write("**説明**: ボラティリティと質スコアから計算されます。安定性を示します。")
