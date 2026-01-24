"""
チャート生成コンポーネント
Plotlyを使用した高品質なインタラクティブチャート
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf
from signals import is_crypto_symbol

try:
    from scipy.cluster.hierarchy import linkage, dendrogram
    from scipy.spatial.distance import pdist, squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


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


def get_ohlc_data(symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
    """
    OHLCデータを取得（yfinance使用）
    
    Args:
        symbol: シンボル名
        days: 取得日数
    
    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    try:
        if is_crypto_symbol(symbol):
            # 仮想通貨の場合はOHLCデータが取得できないため、Noneを返す
            return None
        
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=f"{days}d", interval="1d")
        
        if hist.empty:
            return None
        
        # カラム名を標準化
        hist = hist.reset_index()
        hist.columns = [col.replace(' ', '_') for col in hist.columns]
        
        # 必要なカラムのみ選択
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [col for col in required_cols if col in hist.columns]
        
        if len(available_cols) < 4:  # Open, High, Low, Close は必須
            return None
        
        return hist[available_cols]
    except Exception as e:
        print(f"Error fetching OHLC data for {symbol}: {e}")
        return None


def create_candlestick_chart(
    symbol: str,
    period_days: int = 30,
    show_ma: bool = True,
    show_volume: bool = False
) -> go.Figure:
    """
    ローソク足チャートを生成
    
    Args:
        symbol: シンボル名
        period_days: 表示期間（日数）
        show_ma: 移動平均線を表示するか
        show_volume: 出来高を表示するか（サブプロット）
    
    Returns:
        Plotly Figureオブジェクト
    """
    ohlc_data = get_ohlc_data(symbol, period_days)
    
    if ohlc_data is None or ohlc_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"{symbol}: OHLCデータが取得できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # サブプロットの設定
    if show_volume and 'Volume' in ohlc_data.columns:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{symbol} - ローソク足チャート", "出来高")
        )
    else:
        fig = go.Figure()
    
    # ローソク足
    candlestick = go.Candlestick(
        x=ohlc_data['Date'],
        open=ohlc_data['Open'],
        high=ohlc_data['High'],
        low=ohlc_data['Low'],
        close=ohlc_data['Close'],
        name='価格',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350'
    )
    
    if show_volume:
        fig.add_trace(candlestick, row=1, col=1)
    else:
        fig.add_trace(candlestick)
    
    # 移動平均線
    if show_ma:
        ohlc_data['MA7'] = ohlc_data['Close'].rolling(window=7, min_periods=1).mean()
        ohlc_data['MA30'] = ohlc_data['Close'].rolling(window=30, min_periods=1).mean()
        
        ma7_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=ohlc_data['MA7'],
            mode='lines',
            name='MA7',
            line=dict(color='#ff7f0e', width=1.5, dash='dot'),
            hovertemplate='MA7: $%{y:,.2f}<extra></extra>'
        )
        
        ma30_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=ohlc_data['MA30'],
            mode='lines',
            name='MA30',
            line=dict(color='#2ca02c', width=1.5, dash='dot'),
            hovertemplate='MA30: $%{y:,.2f}<extra></extra>'
        )
        
        if show_volume:
            fig.add_trace(ma7_trace, row=1, col=1)
            fig.add_trace(ma30_trace, row=1, col=1)
        else:
            fig.add_trace(ma7_trace)
            fig.add_trace(ma30_trace)
    
    # 出来高チャート
    if show_volume and 'Volume' in ohlc_data.columns:
        volume_colors = ['#26a69a' if close >= open_price else '#ef5350' 
                         for close, open_price in zip(ohlc_data['Close'], ohlc_data['Open'])]
        
        volume_trace = go.Bar(
            x=ohlc_data['Date'],
            y=ohlc_data['Volume'],
            name='出来高',
            marker_color=volume_colors,
            opacity=0.6,
            hovertemplate='<b>出来高</b><br>日付: %{x|%Y-%m-%d}<br>出来高: %{y:,.0f}<extra></extra>'
        )
        fig.add_trace(volume_trace, row=2, col=1)
    
    # レイアウト設定
    if show_volume:
        fig.update_xaxes(title_text="日付", row=2, col=1)
        fig.update_yaxes(title_text="価格 (USD)", row=1, col=1, tickformat='$,.2f')
        fig.update_yaxes(title_text="出来高", row=2, col=1)
    else:
        fig.update_xaxes(title_text="日付")
        fig.update_yaxes(title_text="価格 (USD)", tickformat='$,.2f')
    
    fig.update_layout(
        title=dict(
            text=f"{symbol} - ローソク足チャート" + ("（出来高付き）" if show_volume else ""),
            font=dict(size=20, color='#2c3e50')
        ),
        hovermode='x unified',
        template='plotly_white',
        height=600 if show_volume else 500,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis_rangeslider_visible=False
    )
    
    return fig


def create_volume_chart(
    symbol: str,
    period_days: int = 30,
    show_price: bool = True
) -> go.Figure:
    """
    出来高チャートを生成
    
    Args:
        symbol: シンボル名
        period_days: 表示期間（日数）
        show_price: 価格も表示するか（サブプロット）
    
    Returns:
        Plotly Figureオブジェクト
    """
    ohlc_data = get_ohlc_data(symbol, period_days)
    
    if ohlc_data is None or ohlc_data.empty or 'Volume' not in ohlc_data.columns:
        fig = go.Figure()
        fig.add_annotation(
            text=f"{symbol}: 出来高データが取得できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # サブプロットの設定
    if show_price:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.4],
            subplot_titles=(f"{symbol} - 価格", "出来高")
        )
    else:
        fig = go.Figure()
    
    # 価格チャート
    if show_price:
        price_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=ohlc_data['Close'],
            mode='lines',
            name='価格',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)',
            hovertemplate='<b>価格</b><br>日付: %{x|%Y-%m-%d}<br>価格: $%{y:,.2f}<extra></extra>'
        )
        fig.add_trace(price_trace, row=1, col=1)
    
    # 出来高チャート（色分け：上昇=緑、下降=赤）
    volume_colors = ['#26a69a' if close >= open_price else '#ef5350' 
                     for close, open_price in zip(ohlc_data['Close'], ohlc_data['Open'])]
    
    # 平均出来高を計算（異常出来高の検出用）
    avg_volume = ohlc_data['Volume'].mean()
    std_volume = ohlc_data['Volume'].std()
    threshold = avg_volume + 2 * std_volume  # 2標準偏差以上を異常とみなす
    
    volume_trace = go.Bar(
        x=ohlc_data['Date'],
        y=ohlc_data['Volume'],
        name='出来高',
        marker=dict(
            color=volume_colors,
            opacity=0.7,
            line=dict(
                color=['#ff6b6b' if vol > threshold else 'transparent' 
                       for vol in ohlc_data['Volume']],
                width=2
            )
        ),
        hovertemplate='<b>出来高</b><br>日付: %{x|%Y-%m-%d}<br>出来高: %{y:,.0f}<br>' +
                      ('<extra>異常出来高</extra>' if any(vol > threshold for vol in ohlc_data['Volume']) else '<extra></extra>')
    )
    
    if show_price:
        fig.add_trace(volume_trace, row=2, col=1)
    else:
        fig.add_trace(volume_trace)
    
    # 平均出来高ライン
    if show_price:
        avg_volume_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=[avg_volume] * len(ohlc_data),
            mode='lines',
            name='平均出来高',
            line=dict(color='#ff7f0e', width=1, dash='dash'),
            hovertemplate=f'平均出来高: {avg_volume:,.0f}<extra></extra>'
        )
        fig.add_trace(avg_volume_trace, row=2, col=1)
    
    # レイアウト設定
    if show_price:
        fig.update_xaxes(title_text="日付", row=2, col=1)
        fig.update_yaxes(title_text="価格 (USD)", row=1, col=1, tickformat='$,.2f')
        fig.update_yaxes(title_text="出来高", row=2, col=1)
    else:
        fig.update_xaxes(title_text="日付")
        fig.update_yaxes(title_text="出来高")
    
    fig.update_layout(
        title=dict(
            text=f"{symbol} - 出来高チャート" + ("（価格付き）" if show_price else ""),
            font=dict(size=20, color='#2c3e50')
        ),
        hovermode='x unified',
        template='plotly_white',
        height=600 if show_price else 400,
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


def create_price_volume_chart(
    symbol: str,
    period_days: int = 30,
    show_indicators: bool = True
) -> go.Figure:
    """
    価格と出来高の組み合わせチャートを生成
    
    Args:
        symbol: シンボル名
        period_days: 表示期間（日数）
        show_indicators: テクニカル指標を表示するか
    
    Returns:
        Plotly Figureオブジェクト
    """
    ohlc_data = get_ohlc_data(symbol, period_days)
    
    if ohlc_data is None or ohlc_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"{symbol}: データが取得できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # サブプロット（価格、出来高）
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} - 価格と出来高", "")
    )
    
    # 価格チャート
    price_trace = go.Scatter(
        x=ohlc_data['Date'],
        y=ohlc_data['Close'],
        mode='lines',
        name='終値',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)',
        hovertemplate='<b>終値</b><br>日付: %{x|%Y-%m-%d}<br>価格: $%{y:,.2f}<extra></extra>'
    )
    fig.add_trace(price_trace, row=1, col=1)
    
    # 移動平均線
    if show_indicators:
        ohlc_data['MA7'] = ohlc_data['Close'].rolling(window=7, min_periods=1).mean()
        ohlc_data['MA30'] = ohlc_data['Close'].rolling(window=30, min_periods=1).mean()
        
        ma7_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=ohlc_data['MA7'],
            mode='lines',
            name='MA7',
            line=dict(color='#ff7f0e', width=1.5, dash='dot'),
            hovertemplate='MA7: $%{y:,.2f}<extra></extra>'
        )
        
        ma30_trace = go.Scatter(
            x=ohlc_data['Date'],
            y=ohlc_data['MA30'],
            mode='lines',
            name='MA30',
            line=dict(color='#2ca02c', width=1.5, dash='dot'),
            hovertemplate='MA30: $%{y:,.2f}<extra></extra>'
        )
        
        fig.add_trace(ma7_trace, row=1, col=1)
        fig.add_trace(ma30_trace, row=1, col=1)
    
    # 出来高チャート
    if 'Volume' in ohlc_data.columns:
        volume_colors = ['#26a69a' if close >= open_price else '#ef5350' 
                         for close, open_price in zip(ohlc_data['Close'], ohlc_data['Open'])]
        
        volume_trace = go.Bar(
            x=ohlc_data['Date'],
            y=ohlc_data['Volume'],
            name='出来高',
            marker_color=volume_colors,
            opacity=0.6,
            hovertemplate='<b>出来高</b><br>日付: %{x|%Y-%m-%d}<br>出来高: %{y:,.0f}<extra></extra>'
        )
        fig.add_trace(volume_trace, row=2, col=1)
    
    # レイアウト設定
    fig.update_xaxes(title_text="日付", row=2, col=1)
    fig.update_yaxes(title_text="価格 (USD)", row=1, col=1, tickformat='$,.2f')
    if 'Volume' in ohlc_data.columns:
        fig.update_yaxes(title_text="出来高", row=2, col=1)
    
    fig.update_layout(
        title=dict(
            text=f"{symbol} - 価格と出来高",
            font=dict(size=20, color='#2c3e50')
        ),
        hovermode='x unified',
        template='plotly_white',
        height=600,
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


def create_correlation_heatmap(
    symbols: List[str],
    days: int = 90,
    method: str = 'pearson'
) -> go.Figure:
    """
    銘柄間の相関ヒートマップを生成
    
    Args:
        symbols: シンボル名のリスト
        days: 相関計算に使用する日数
        method: 相関係数の計算方法（'pearson', 'kendall', 'spearman'）
    
    Returns:
        Plotly Figureオブジェクト
    """
    if len(symbols) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="相関分析には2つ以上の銘柄が必要です",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # 各銘柄の価格データを取得
    price_data = {}
    for symbol in symbols:
        try:
            if is_crypto_symbol(symbol):
                continue  # 仮想通貨はスキップ
            
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=f"{days}d", interval="1d")
            
            if not hist.empty:
                price_data[symbol] = hist['Close']
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            continue
    
    if len(price_data) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="十分なデータが取得できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # DataFrameに変換して相関行列を計算
    df = pd.DataFrame(price_data)
    correlation_matrix = df.corr(method=method)
    
    # ヒートマップを生成
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="相関係数")
    ))
    
    fig.update_layout(
        title=dict(
            text=f"銘柄間相関ヒートマップ ({method})",
            font=dict(size=20, color='#2c3e50')
        ),
        xaxis=dict(title="銘柄"),
        yaxis=dict(title="銘柄"),
        height=600,
        margin=dict(l=100, r=50, t=80, b=100),
        template='plotly_white'
    )
    
    return fig


def create_metrics_heatmap(
    data: List[Dict],
    metrics: List[str] = None
) -> go.Figure:
    """
    メトリクス比較ヒートマップを生成
    
    Args:
        data: 投資分析結果のリスト
        metrics: 表示するメトリクスのリスト（デフォルト: ['total_score', 'value_score', 'momentum_score', 'stability_score']）
    
    Returns:
        Plotly Figureオブジェクト
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    if metrics is None:
        metrics = ['total_score', 'value_score', 'momentum_score', 'stability_score']
    
    # データを準備
    symbols = [item.get('symbol', f'銘柄{i+1}') for i, item in enumerate(data)]
    metric_values = []
    
    for metric in metrics:
        values = [item.get(metric, item.get('investment_score', 0) if metric == 'total_score' else 0) 
                  for item in data]
        metric_values.append(values)
    
    # ヒートマップを生成
    fig = go.Figure(data=go.Heatmap(
        z=metric_values,
        x=symbols,
        y=metrics,
        colorscale='Viridis',
        text=metric_values,
        texttemplate='%{text:.1f}',
        textfont={"size": 9},
        colorbar=dict(title="スコア"),
        hovertemplate='<b>%{y}</b><br>%{x}<br>スコア: %{z:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text="メトリクス比較ヒートマップ",
            font=dict(size=20, color='#2c3e50')
        ),
        xaxis=dict(title="銘柄", tickangle=-45),
        yaxis=dict(title="メトリクス"),
        height=max(400, len(metrics) * 80),
        margin=dict(l=120, r=50, t=80, b=150),
        template='plotly_white'
    )
    
    return fig
