"""
インサイト表示コンポーネント
AI生成インサイト、自動アノテーション、推奨アクション
"""
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go


def generate_insights(data: Dict) -> List[str]:
    """データからインサイトを生成"""
    insights = []
    
    symbol = data.get('symbol', 'N/A')
    total_score = data.get('total_score', data.get('investment_score', 0))
    value_score = data.get('value_score', 0)
    momentum_score = data.get('momentum_score', 0)
    stability_score = data.get('stability_score', 0)
    current_state = data.get('current_state', 'NORMAL')
    current_price = data.get('current_price', 0)
    
    # スコアベースのインサイト
    if total_score >= 80:
        insights.append(f"🌟 {symbol}は非常に高い投資スコア（{total_score:.1f}）を示しています。強力な買いシグナルです。")
    elif total_score >= 60:
        insights.append(f"✅ {symbol}は良好な投資スコア（{total_score:.1f}）を示しています。買い候補として検討できます。")
    elif total_score < 40:
        insights.append(f"⚠️ {symbol}の投資スコア（{total_score:.1f}）は低めです。慎重に検討してください。")
    
    # バランス分析
    score_diff = max(value_score, momentum_score, stability_score) - min(value_score, momentum_score, stability_score)
    if score_diff > 30:
        if value_score > momentum_score and value_score > stability_score:
            insights.append("💡 Valueスコアが突出しています。割安度が高い可能性があります。")
        elif momentum_score > value_score and momentum_score > stability_score:
            insights.append("📈 Momentumスコアが突出しています。反転の可能性が高いです。")
        elif stability_score > value_score and stability_score > momentum_score:
            insights.append("🛡️ Stabilityスコアが突出しています。安定性が高い銘柄です。")
    
    # 状態ベースのインサイト
    if current_state == 'BUY':
        insights.append("🟢 現在の状態はBUYです。購入を検討する良いタイミングかもしれません。")
    elif current_state == 'WATCH':
        insights.append("👀 現在の状態はWATCHです。継続的に監視することをお勧めします。")
    
    # 価格ベースのインサイト
    ath_ratio = data.get('ath_ratio')
    if ath_ratio:
        if ath_ratio < 0.5:
            insights.append(f"📉 現在価格はATH比{ath_ratio:.1%}です。大幅に下落しており、割安の可能性があります。")
        elif ath_ratio > 0.9:
            insights.append(f"📈 現在価格はATH比{ath_ratio:.1%}です。高値圏にあり、注意が必要です。")
    
    return insights


def generate_recommendations(data: Dict) -> List[str]:
    """推奨アクションを生成"""
    recommendations = []
    
    symbol = data.get('symbol', 'N/A')
    total_score = data.get('total_score', data.get('investment_score', 0))
    current_state = data.get('current_state', 'NORMAL')
    
    if total_score >= 70 and current_state == 'BUY':
        recommendations.append(f"✅ {symbol}は購入を検討する価値があります。")
        recommendations.append("📊 財務指標を詳細に確認してください。")
        recommendations.append("📈 価格チャートでエントリーポイントを探してください。")
    elif total_score >= 60:
        recommendations.append(f"👀 {symbol}をウォッチリストに追加することをお勧めします。")
        recommendations.append("📅 定期的にスコアの変化を確認してください。")
    else:
        recommendations.append(f"⏸️ {symbol}は現時点では様子見が適切です。")
        recommendations.append("🔄 スコアの改善を待つか、他の銘柄を検討してください。")
    
    return recommendations


def render_insights(data: Dict, symbol: str):
    """インサイトをレンダリング"""
    st.subheader("💡 AI生成インサイト")
    
    insights = generate_insights(data)
    
    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.info("現在、特別なインサイトはありません。")
    
    st.markdown("---")
    st.subheader("🎯 推奨アクション")
    
    recommendations = generate_recommendations(data)
    
    for i, rec in enumerate(recommendations, 1):
        st.write(f"{i}. {rec}")


def add_chart_annotations(fig: go.Figure, data: Dict, prices: List) -> go.Figure:
    """チャートに自動アノテーションを追加"""
    if not prices or len(prices) < 2:
        return fig
    
    # ATHポイントをアノテーション
    max_price = max(p[1] for p in prices)
    max_date = next(p[0] for p in prices if p[1] == max_price)
    
    fig.add_annotation(
        x=max_date,
        y=max_price,
        text=f"ATH: ${max_price:,.2f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor="red",
        bgcolor="rgba(255, 0, 0, 0.2)",
        bordercolor="red"
    )
    
    # 重要な状態変化をアノテーション
    current_state = data.get('current_state', 'NORMAL')
    if current_state == 'BUY' and len(prices) > 0:
        current_price = prices[-1][1]
        current_date = prices[-1][0]
        
        fig.add_annotation(
            x=current_date,
            y=current_price,
            text="BUY Signal",
            showarrow=True,
            arrowhead=2,
            arrowcolor="green",
            bgcolor="rgba(0, 255, 0, 0.2)",
            bordercolor="green"
        )
    
    return fig
