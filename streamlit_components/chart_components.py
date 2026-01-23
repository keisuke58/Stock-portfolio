"""
チャート生成コンポーネント
Plotlyを使用した高品質なインタラクティブチャート
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd


def create_price_chart(
    symbol: str,
    prices: List[Tuple[datetime, float]],
    period_days: int = 30,
    show_ath: bool = True,
    show_ma: bool = True
) -> go.Figure:
    """
    価格チャートを生成
    
    Args:
        symbol: シンボル名
        prices: [(datetime, price), ...] のリスト
        period_days: 表示期間（日数）
        show_ath: ATHラインを表示するか
        show_ma: 移動平均線を表示するか
    
    Returns:
        Plotly Figureオブジェクト
    """
    if not prices:
        fig = go.Figure()
        fig.add_annotation(
            text=f"{symbol}: データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # データをDataFrameに変換
    df = pd.DataFrame(prices, columns=['date', 'price'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 期間でフィルタリング
    if period_days > 0:
        cutoff_date = df['date'].max() - pd.Timedelta(days=period_days)
        df = df[df['date'] >= cutoff_date]
    
    # 基本チャート
    fig = go.Figure()
    
    # 価格ライン
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['price'],
        mode='lines',
        name='価格',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)',
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      '日付: %{x|%Y-%m-%d}<br>' +
                      '価格: $%{y:,.2f}<extra></extra>'
    ))
    
    # ATHライン
    if show_ath and len(df) > 0:
        ath_price = df['price'].max()
        ath_date = df.loc[df['price'].idxmax(), 'date']
        fig.add_hline(
            y=ath_price,
            line_dash="dash",
            line_color="red",
            annotation_text=f"ATH: ${ath_price:,.2f}",
            annotation_position="right"
        )
    
    # 移動平均線（7日、30日）
    if show_ma and len(df) >= 7:
        df['ma7'] = df['price'].rolling(window=7, min_periods=1).mean()
        df['ma30'] = df['price'].rolling(window=30, min_periods=1).mean()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma7'],
            mode='lines',
            name='MA7',
            line=dict(color='#ff7f0e', width=1, dash='dot'),
            hovertemplate='MA7: $%{y:,.2f}<extra></extra>'
        ))
        
        if len(df) >= 30:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['ma30'],
                mode='lines',
                name='MA30',
                line=dict(color='#2ca02c', width=1, dash='dot'),
                hovertemplate='MA30: $%{y:,.2f}<extra></extra>'
            ))
    
    # レイアウト設定
    fig.update_layout(
        title=dict(
            text=f"{symbol} - 価格推移",
            font=dict(size=20, color='#2c3e50')
        ),
        xaxis=dict(
            title="日付",
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            title="価格 (USD)",
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            tickformat='$,.2f'
        ),
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
    
    return fig


def create_radar_chart(
    data: List[Dict],
    categories: List[str] = None
) -> go.Figure:
    """
    レーダーチャートを生成（スコア内訳用）
    
    Args:
        data: [{'name': '銘柄名', 'value': 値, 'momentum': 値, 'stability': 値}, ...]
        categories: カテゴリ名のリスト（デフォルト: ['Value', 'Momentum', 'Stability']）
    
    Returns:
        Plotly Figureオブジェクト
    """
    if categories is None:
        categories = ['Value', 'Momentum', 'Stability']
    
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for idx, item in enumerate(data):
        name = item.get('name', f'銘柄{idx+1}')
        values = [
            item.get('value_score', item.get('value', 0)),
            item.get('momentum_score', item.get('momentum', 0)),
            item.get('stability_score', item.get('stability', 0))
        ]
        # レーダーチャートを閉じるために最初の値を最後に追加
        values = values + [values[0]]
        categories_closed = categories + [categories[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories_closed,
            fill='toself',
            name=name,
            line=dict(color=colors[idx % len(colors)], width=2),
            fillcolor=f'rgba({int(colors[idx % len(colors)][1:3], 16)}, {int(colors[idx % len(colors)][3:5], 16)}, {int(colors[idx % len(colors)][5:7], 16)}, 0.2)'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10),
                gridcolor='rgba(128, 128, 128, 0.3)'
            ),
            angularaxis=dict(
                tickfont=dict(size=12),
                rotation=90,
                direction="counterclockwise"
            )
        ),
        showlegend=True,
        title=dict(
            text="スコア内訳レーダーチャート",
            font=dict(size=18, color='#2c3e50')
        ),
        height=500,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_score_comparison_chart(
    data: List[Dict],
    chart_type: str = 'bar'
) -> go.Figure:
    """
    スコア比較チャートを生成
    
    Args:
        data: [{'symbol': 'AAPL', 'value_score': 50, 'momentum_score': 60, 'stability_score': 70}, ...]
        chart_type: 'bar' (積み上げバー) または 'grouped' (グループバー)
    
    Returns:
        Plotly Figureオブジェクト
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    symbols = [item.get('symbol', f'銘柄{i+1}') for i, item in enumerate(data)]
    value_scores = [item.get('value_score', 0) for item in data]
    momentum_scores = [item.get('momentum_score', 0) for item in data]
    stability_scores = [item.get('stability_score', 0) for item in data]
    
    fig = go.Figure()
    
    if chart_type == 'bar':
        # 積み上げバーチャート
        fig.add_trace(go.Bar(
            name='Value',
            x=symbols,
            y=value_scores,
            marker_color='#1f77b4',
            hovertemplate='<b>%{x}</b><br>Value: %{y:.1f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            name='Momentum',
            x=symbols,
            y=momentum_scores,
            marker_color='#ff7f0e',
            hovertemplate='<b>%{x}</b><br>Momentum: %{y:.1f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            name='Stability',
            x=symbols,
            y=stability_scores,
            marker_color='#2ca02c',
            hovertemplate='<b>%{x}</b><br>Stability: %{y:.1f}<extra></extra>'
        ))
    else:
        # グループバーチャート
        fig.add_trace(go.Bar(
            name='Value',
            x=symbols,
            y=value_scores,
            marker_color='#1f77b4',
            hovertemplate='<b>%{x}</b><br>Value: %{y:.1f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            name='Momentum',
            x=symbols,
            y=momentum_scores,
            marker_color='#ff7f0e',
            hovertemplate='<b>%{x}</b><br>Momentum: %{y:.1f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            name='Stability',
            x=symbols,
            y=stability_scores,
            marker_color='#2ca02c',
            hovertemplate='<b>%{x}</b><br>Stability: %{y:.1f}<extra></extra>'
        ))
    
    fig.update_layout(
        barmode='group' if chart_type == 'grouped' else 'stack',
        title=dict(
            text="スコア内訳比較",
            font=dict(size=18, color='#2c3e50')
        ),
        xaxis=dict(title="銘柄"),
        yaxis=dict(title="スコア", range=[0, 100]),
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_score_distribution_chart(
    data: List[Dict]
) -> go.Figure:
    """
    スコア分布ヒストグラムを生成
    
    Args:
        data: 投資分析結果のリスト
    
    Returns:
        Plotly Figureオブジェクト
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    total_scores = [item.get('total_score', item.get('investment_score', 0)) for item in data]
    value_scores = [item.get('value_score', 0) for item in data]
    momentum_scores = [item.get('momentum_score', 0) for item in data]
    stability_scores = [item.get('stability_score', 0) for item in data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=total_scores,
        name='総合スコア',
        marker_color='#1f77b4',
        opacity=0.7,
        nbinsx=20
    ))
    fig.add_trace(go.Histogram(
        x=value_scores,
        name='Value',
        marker_color='#ff7f0e',
        opacity=0.7,
        nbinsx=20
    ))
    fig.add_trace(go.Histogram(
        x=momentum_scores,
        name='Momentum',
        marker_color='#2ca02c',
        opacity=0.7,
        nbinsx=20
    ))
    fig.add_trace(go.Histogram(
        x=stability_scores,
        name='Stability',
        marker_color='#d62728',
        opacity=0.7,
        nbinsx=20
    ))
    
    fig.update_layout(
        title=dict(
            text="スコア分布",
            font=dict(size=18, color='#2c3e50')
        ),
        xaxis=dict(title="スコア", range=[0, 100]),
        yaxis=dict(title="頻度"),
        barmode='overlay',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_donut_chart(
    labels: List[str],
    values: List[float],
    title: str = "分布"
) -> go.Figure:
    """
    ドーナツチャートを生成
    
    Args:
        labels: ラベルのリスト
        values: 値のリスト
        title: チャートタイトル
    
    Returns:
        Plotly Figureオブジェクト
    """
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors[:len(labels)],
        textinfo='label+percent',
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>値: %{value}<br>割合: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#2c3e50')
        ),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        showlegend=True
    )
    
    return fig
