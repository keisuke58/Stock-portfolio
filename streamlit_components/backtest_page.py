"""
バックテストページコンポーネント
バックテスト実行UI、結果可視化、実績データ保存
Deep Bottom バックテスト機能を含む
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtester import Backtester
from backtesting.deep_bottom_backtester import DeepBottomBacktester
from services.config_service import load_config


def save_backtest_result(result: Dict, symbol: str = None):
    """
    バックテスト結果を保存
    
    Args:
        result: バックテスト結果の辞書
        symbol: シンボル名（オプション）
    """
    results_dir = "backtest_results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{results_dir}/backtest_{symbol or 'all'}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    return filename


def load_backtest_results() -> List[Dict]:
    """
    保存されたバックテスト結果を読み込む
    
    Returns:
        バックテスト結果のリスト
    """
    results_dir = "backtest_results"
    if not os.path.exists(results_dir):
        return []
    
    results = []
    for filename in os.listdir(results_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(results_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    result['filename'] = filename
                    result['filepath'] = filepath
                    results.append(result)
            except Exception as e:
                st.warning(f"ファイル {filename} の読み込みに失敗: {e}")
    
    # 日付でソート（新しい順）
    results.sort(key=lambda x: x.get('start_date', ''), reverse=True)
    return results


def create_equity_curve_chart(result: Dict) -> go.Figure:
    """
    エクイティカーブを表示
    
    Args:
        result: バックテスト結果
    
    Returns:
        Plotly Figure
    """
    equity_curve = result.get('equity_curve', [])
    if not equity_curve:
        fig = go.Figure()
        fig.add_annotation(
            text="エクイティカーブデータがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # データ形式に応じて処理
    if isinstance(equity_curve[0], dict):
        dates = [datetime.fromisoformat(d.get('date', '')) for d in equity_curve]
        values = [d.get('value', 0) for d in equity_curve]
    else:
        # 単純なリストの場合
        dates = list(range(len(equity_curve)))
        values = equity_curve
    
    initial_capital = result.get('initial_capital', 100000)
    
    fig = go.Figure()
    
    # エクイティカーブ
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        name='ポートフォリオ価値',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>価値: $%{y:,.2f}<extra></extra>'
    ))
    
    # 初期資本ライン
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"初期資本: ${initial_capital:,.2f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title="エクイティカーブ",
        xaxis=dict(title="日付"),
        yaxis=dict(title="ポートフォリオ価値 ($)"),
        height=400,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def create_drawdown_chart(result: Dict) -> go.Figure:
    """
    ドローダウンチャートを表示
    
    Args:
        result: バックテスト結果
    
    Returns:
        Plotly Figure
    """
    equity_curve = result.get('equity_curve', [])
    if not equity_curve:
        fig = go.Figure()
        fig.add_annotation(
            text="エクイティカーブデータがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # データ形式に応じて処理
    if isinstance(equity_curve[0], dict):
        dates = [datetime.fromisoformat(d.get('date', '')) for d in equity_curve]
        values = [d.get('value', 0) for d in equity_curve]
    else:
        dates = list(range(len(equity_curve)))
        values = equity_curve
    
    # ドローダウン計算
    peak = values[0]
    drawdowns = []
    for value in values:
        if value > peak:
            peak = value
        drawdown = ((value - peak) / peak) * 100
        drawdowns.append(drawdown)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdowns,
        mode='lines',
        name='ドローダウン',
        line=dict(color='#d62728', width=2),
        fill='tozeroy',
        fillcolor='rgba(214, 39, 40, 0.1)',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>ドローダウン: %{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title="ドローダウン",
        xaxis=dict(title="日付"),
        yaxis=dict(title="ドローダウン (%)"),
        height=300,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def create_trades_chart(result: Dict) -> go.Figure:
    """
    取引履歴を表示
    
    Args:
        result: バックテスト結果
    
    Returns:
        Plotly Figure
    """
    trades = result.get('trades', [])
    if not trades:
        fig = go.Figure()
        fig.add_annotation(
            text="取引データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    entry_dates = [datetime.fromisoformat(t.get('entry_date', '')) for t in trades]
    exit_dates = [datetime.fromisoformat(t.get('exit_date', '')) for t in trades]
    returns = [t.get('return_pct', 0) for t in trades]
    
    colors = ['green' if r > 0 else 'red' for r in returns]
    
    fig = go.Figure()
    
    for i, (entry_date, exit_date, return_pct, color) in enumerate(zip(entry_dates, exit_dates, returns, colors)):
        fig.add_trace(go.Scatter(
            x=[entry_date, exit_date],
            y=[i, i],
            mode='lines+markers',
            name=f'取引 {i+1}',
            line=dict(color=color, width=2),
            marker=dict(size=8),
            hovertemplate=f'<b>取引 {i+1}</b><br>エントリー: %{{x|%Y-%m-%d}}<br>リターン: {return_pct:.2f}%<extra></extra>',
            showlegend=False
        ))
    
    fig.update_layout(
        title="取引履歴",
        xaxis=dict(title="日付"),
        yaxis=dict(title="取引番号", range=[-0.5, len(trades) - 0.5]),
        height=400,
        template='plotly_white'
    )
    
    return fig


def create_deep_bottom_signal_chart(result: Dict) -> go.Figure:
    """
    Deep Bottom シグナルタイムラインチャートを作成

    Args:
        result: バックテスト結果

    Returns:
        Plotly Figure
    """
    outcomes = result.get('outcomes', [])
    if not outcomes:
        fig = go.Figure()
        fig.add_annotation(
            text="シグナルデータがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig

    # シグナルを勝ち/負けで分類
    winning_dates = []
    winning_returns = []
    losing_dates = []
    losing_returns = []

    for outcome in outcomes:
        signal = outcome.get('signal', {})
        signal_date = signal.get('date')
        is_winner = outcome.get('is_winner', False)
        return_12m = outcome.get('return_12m', 0) or 0

        if signal_date:
            if isinstance(signal_date, str):
                signal_date = datetime.fromisoformat(signal_date)

            if is_winner:
                winning_dates.append(signal_date)
                winning_returns.append(return_12m * 100)
            else:
                losing_dates.append(signal_date)
                losing_returns.append(return_12m * 100)

    fig = go.Figure()

    # 勝ちシグナル
    if winning_dates:
        fig.add_trace(go.Scatter(
            x=winning_dates,
            y=winning_returns,
            mode='markers',
            name='勝ちシグナル (50%+)',
            marker=dict(
                size=15,
                color='green',
                symbol='triangle-up'
            ),
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>12ヶ月リターン: %{y:.1f}%<extra>勝ち</extra>'
        ))

    # 負けシグナル
    if losing_dates:
        fig.add_trace(go.Scatter(
            x=losing_dates,
            y=losing_returns,
            mode='markers',
            name='負けシグナル (<50%)',
            marker=dict(
                size=12,
                color='red',
                symbol='triangle-down'
            ),
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>12ヶ月リターン: %{y:.1f}%<extra>負け</extra>'
        ))

    # 50%ライン
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="blue",
        annotation_text="目標: +50%",
        annotation_position="right"
    )

    # 0%ライン
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="gray"
    )

    fig.update_layout(
        title="Deep Bottom シグナルと12ヶ月リターン",
        xaxis=dict(title="シグナル日"),
        yaxis=dict(title="12ヶ月リターン (%)"),
        height=400,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def create_return_distribution_chart(result: Dict) -> go.Figure:
    """
    リターン分布チャートを作成

    Args:
        result: バックテスト結果

    Returns:
        Plotly Figure
    """
    outcomes = result.get('outcomes', [])
    if not outcomes:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig

    returns_3m = [o.get('return_3m', 0) * 100 for o in outcomes if o.get('return_3m') is not None]
    returns_6m = [o.get('return_6m', 0) * 100 for o in outcomes if o.get('return_6m') is not None]
    returns_12m = [o.get('return_12m', 0) * 100 for o in outcomes if o.get('return_12m') is not None]

    fig = go.Figure()

    if returns_3m:
        fig.add_trace(go.Box(
            y=returns_3m,
            name='3ヶ月',
            boxpoints='all',
            jitter=0.3,
            marker_color='#3366cc'
        ))

    if returns_6m:
        fig.add_trace(go.Box(
            y=returns_6m,
            name='6ヶ月',
            boxpoints='all',
            jitter=0.3,
            marker_color='#dc3912'
        ))

    if returns_12m:
        fig.add_trace(go.Box(
            y=returns_12m,
            name='12ヶ月',
            boxpoints='all',
            jitter=0.3,
            marker_color='#109618'
        ))

    # 目標ライン
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="gold",
        annotation_text="目標 +50%"
    )

    fig.update_layout(
        title="期間別リターン分布",
        yaxis=dict(title="リターン (%)"),
        height=350,
        template='plotly_white',
        showlegend=False
    )

    return fig


def render_deep_bottom_backtest_tab():
    """
    Deep Bottom バックテストタブをレンダリング
    """
    st.subheader("💎 Deep Bottom バックテスト")
    st.caption("Deep Bottom シグナルが実際に50%以上の上昇につながったか検証します")

    # 設定
    col1, col2 = st.columns(2)

    with col1:
        # クラッシュ期間選択
        crash_periods = DeepBottomBacktester.CRASH_PERIODS
        period_options = ["カスタム"] + list(crash_periods.keys())
        period_labels = {
            "カスタム": "カスタム期間",
            "btc_2018": "BTC 2018年暴落",
            "covid_2020": "COVID-19 暴落",
            "crypto_2022": "仮想通貨冬 2022",
            "tech_crash_2022": "テック暴落 2022"
        }

        selected_period = st.selectbox(
            "検証期間",
            period_options,
            format_func=lambda x: period_labels.get(x, x)
        )

    with col2:
        detection_mode = st.selectbox(
            "検出モード",
            ["both", "basic", "advanced"],
            format_func=lambda x: {
                "both": "両方 (Basic + Advanced)",
                "basic": "Basic のみ (5条件)",
                "advanced": "Advanced のみ (7指標)"
            }.get(x, x)
        )

    # カスタム期間の場合
    if selected_period == "カスタム":
        col1, col2, col3 = st.columns(3)

        with col1:
            symbol = st.text_input("シンボル", value="BTC").upper()

        with col2:
            start_date = st.date_input(
                "開始日",
                value=datetime.now() - timedelta(days=365*3),
                max_value=datetime.now() - timedelta(days=365)  # 少なくとも1年前
            )

        with col3:
            end_date = st.date_input(
                "終了日",
                value=datetime.now() - timedelta(days=365),
                max_value=datetime.now() - timedelta(days=30)  # 少なくとも30日前
            )
    else:
        period_info = crash_periods[selected_period]
        symbol = period_info['symbol']
        start_date = datetime.strptime(period_info['start'], '%Y-%m-%d').date()
        end_date = datetime.strptime(period_info['end'], '%Y-%m-%d').date()

        st.info(f"📅 {symbol}: {start_date} 〜 {end_date}")

    # バックテスト実行
    if st.button("🚀 Deep Bottom バックテストを実行", type="primary"):
        with st.spinner("バックテストを実行中..."):
            try:
                backtester = DeepBottomBacktester()

                result = backtester.backtest_symbol(
                    symbol=symbol,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    detection_mode=detection_mode
                )

                # 結果をセッションに保存
                st.session_state['deep_bottom_backtest_result'] = result
                st.success("バックテストが完了しました！")
                st.rerun()

            except Exception as e:
                st.error(f"バックテスト実行エラー: {e}")
                import traceback
                st.exception(e)

    # 結果表示
    if 'deep_bottom_backtest_result' in st.session_state:
        result = st.session_state['deep_bottom_backtest_result']

        st.markdown("---")
        st.subheader("📊 バックテスト結果")

        # メトリクス
        metrics = result.get('metrics', {})
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            signal_count = metrics.get('signal_count', 0)
            st.metric("シグナル数", signal_count)

        with col2:
            win_rate = metrics.get('win_rate', 0) * 100
            st.metric(
                "勝率",
                f"{win_rate:.1f}%",
                help="12ヶ月以内に50%以上上昇した割合"
            )

        with col3:
            avg_12m = metrics.get('avg_return_12m', 0) * 100
            st.metric(
                "平均12ヶ月リターン",
                f"{avg_12m:.1f}%",
                delta=f"{avg_12m - 50:.1f}%" if avg_12m else None
            )

        with col4:
            max_dd = metrics.get('max_drawdown', 0) * 100
            st.metric(
                "最大ドローダウン",
                f"{max_dd:.1f}%",
                delta=None
            )

        with col5:
            days_to_target = metrics.get('avg_days_to_target', None)
            if days_to_target:
                st.metric("平均達成日数", f"{days_to_target:.0f}日")
            else:
                st.metric("平均達成日数", "N/A")

        # 追加メトリクス
        col1, col2, col3 = st.columns(3)

        with col1:
            avg_3m = metrics.get('avg_return_3m', 0) * 100
            st.metric("平均3ヶ月リターン", f"{avg_3m:.1f}%")

        with col2:
            avg_6m = metrics.get('avg_return_6m', 0) * 100
            st.metric("平均6ヶ月リターン", f"{avg_6m:.1f}%")

        with col3:
            win_count = metrics.get('winning_signals', 0)
            st.metric("勝ちシグナル数", f"{win_count}/{signal_count}")

        st.markdown("---")

        # チャート
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(
                create_deep_bottom_signal_chart(result),
                use_container_width=True
            )

        with col2:
            st.plotly_chart(
                create_return_distribution_chart(result),
                use_container_width=True
            )

        # シグナル詳細
        with st.expander("📋 シグナル詳細", expanded=False):
            outcomes = result.get('outcomes', [])
            if outcomes:
                import pandas as pd

                details = []
                for outcome in outcomes:
                    signal = outcome.get('signal', {})
                    details.append({
                        'シグナル日': signal.get('date', 'N/A'),
                        'シグナル価格': f"${signal.get('price', 0):,.2f}",
                        'スコア': f"{signal.get('score', 0):.0f}",
                        'モード': signal.get('mode', 'N/A'),
                        '3ヶ月': f"{(outcome.get('return_3m', 0) or 0) * 100:.1f}%",
                        '6ヶ月': f"{(outcome.get('return_6m', 0) or 0) * 100:.1f}%",
                        '12ヶ月': f"{(outcome.get('return_12m', 0) or 0) * 100:.1f}%",
                        '50%達成': '✅' if outcome.get('is_winner') else '❌',
                        '達成日数': outcome.get('days_to_target', 'N/A')
                    })

                df = pd.DataFrame(details)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("シグナルが検出されませんでした")

    # Basic vs Advanced 比較
    st.markdown("---")
    st.subheader("🔍 Basic vs Advanced 比較")

    col1, col2, col3 = st.columns(3)

    with col1:
        compare_symbol = st.text_input("比較シンボル", value="BTC", key="compare_symbol").upper()

    with col2:
        compare_start = st.date_input(
            "比較開始日",
            value=datetime.now() - timedelta(days=365*3),
            key="compare_start"
        )

    with col3:
        compare_end = st.date_input(
            "比較終了日",
            value=datetime.now() - timedelta(days=365),
            key="compare_end"
        )

    if st.button("📊 Basic vs Advanced を比較", type="secondary"):
        with st.spinner("比較分析中..."):
            try:
                backtester = DeepBottomBacktester()
                comparison = backtester.compare_basic_vs_advanced(
                    compare_symbol,
                    datetime.combine(compare_start, datetime.min.time()),
                    datetime.combine(compare_end, datetime.max.time())
                )

                st.session_state['deep_bottom_comparison'] = comparison
                st.success("比較が完了しました！")
                st.rerun()

            except Exception as e:
                st.error(f"比較エラー: {e}")

    if 'deep_bottom_comparison' in st.session_state:
        comparison = st.session_state['deep_bottom_comparison']

        basic = comparison.get('basic', {}).get('metrics', {})
        advanced = comparison.get('advanced', {}).get('metrics', {})

        import pandas as pd

        comparison_data = {
            '指標': [
                'シグナル数',
                '勝率',
                '平均3ヶ月リターン',
                '平均6ヶ月リターン',
                '平均12ヶ月リターン',
                '最大ドローダウン'
            ],
            'Basic': [
                basic.get('signal_count', 0),
                f"{basic.get('win_rate', 0) * 100:.1f}%",
                f"{basic.get('avg_return_3m', 0) * 100:.1f}%",
                f"{basic.get('avg_return_6m', 0) * 100:.1f}%",
                f"{basic.get('avg_return_12m', 0) * 100:.1f}%",
                f"{basic.get('max_drawdown', 0) * 100:.1f}%"
            ],
            'Advanced': [
                advanced.get('signal_count', 0),
                f"{advanced.get('win_rate', 0) * 100:.1f}%",
                f"{advanced.get('avg_return_3m', 0) * 100:.1f}%",
                f"{advanced.get('avg_return_6m', 0) * 100:.1f}%",
                f"{advanced.get('avg_return_12m', 0) * 100:.1f}%",
                f"{advanced.get('max_drawdown', 0) * 100:.1f}%"
            ]
        }

        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)


def render_v1_vs_v2_comparison_tab():
    """
    V1 vs V2 比較タブをレンダリング
    """
    st.subheader("🔄 V1 vs V2 比較分析")
    st.caption("V1（スコアベース）とV2（出来高強化）の精度を比較検証します")

    # 設定
    col1, col2 = st.columns(2)

    with col1:
        # クラッシュ期間選択
        crash_periods = DeepBottomBacktester.CRASH_PERIODS
        period_options = ["カスタム"] + list(crash_periods.keys())
        period_labels = {
            "カスタム": "カスタム期間",
            "btc_2018": "BTC 2018年暴落",
            "covid_2020": "COVID-19 暴落",
            "crypto_2022": "仮想通貨冬 2022",
            "tech_crash_2022": "テック暴落 2022"
        }

        selected_period = st.selectbox(
            "検証期間",
            period_options,
            format_func=lambda x: period_labels.get(x, x),
            key="v1v2_period"
        )

    with col2:
        min_confidence = st.slider(
            "V2 最小信頼度",
            min_value=40,
            max_value=90,
            value=50,
            step=5,
            help="V2シグナルの最小信頼度閾値"
        )

    # カスタム期間の場合
    if selected_period == "カスタム":
        col1, col2, col3 = st.columns(3)

        with col1:
            symbol = st.text_input("シンボル", value="BTC", key="v1v2_symbol").upper()

        with col2:
            start_date = st.date_input(
                "開始日",
                value=datetime.now() - timedelta(days=365*3),
                max_value=datetime.now() - timedelta(days=365),
                key="v1v2_start"
            )

        with col3:
            end_date = st.date_input(
                "終了日",
                value=datetime.now() - timedelta(days=365),
                max_value=datetime.now() - timedelta(days=30),
                key="v1v2_end"
            )
    else:
        period_info = crash_periods[selected_period]
        symbol = period_info['symbol']
        start_date = datetime.strptime(period_info['start'], '%Y-%m-%d').date()
        end_date = datetime.strptime(period_info['end'], '%Y-%m-%d').date()

        st.info(f"📅 {symbol}: {start_date} 〜 {end_date}")

    # V2オプション
    col1, col2 = st.columns(2)
    with col1:
        volume_filter = st.checkbox(
            "出来高確認フィルター",
            value=True,
            help="V2で出来高確認されたシグナルのみを使用"
        )

    # 比較実行
    if st.button("🔄 V1 vs V2 比較を実行", type="primary"):
        with st.spinner("V1 vs V2 比較分析中..."):
            try:
                backtester = DeepBottomBacktester()

                comparison = backtester.compare_v1_vs_v2(
                    symbol=symbol,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    min_confidence_v2=min_confidence,
                    volume_filter_v2=volume_filter
                )

                # 結果をセッションに保存
                st.session_state['v1_vs_v2_comparison'] = comparison
                st.success("比較分析が完了しました！")
                st.rerun()

            except Exception as e:
                st.error(f"比較分析エラー: {e}")
                import traceback
                st.exception(e)

    # 結果表示
    if 'v1_vs_v2_comparison' in st.session_state:
        comparison = st.session_state['v1_vs_v2_comparison']

        st.markdown("---")
        st.subheader("📊 比較結果")

        v1_result = comparison.v1_result
        v2_result = comparison.v2_result
        metrics = comparison.comparison_metrics

        # サマリーメトリクス
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            winner = metrics.get('winner', 'N/A')
            winner_emoji = "🏆" if winner == 'v2' else "📊"
            st.metric(
                "勝者",
                f"{winner_emoji} {winner.upper()}",
                help="勝率とリターンで判定"
            )

        with col2:
            win_rate_diff = metrics.get('win_rate_diff', 0)
            st.metric(
                "勝率差",
                f"{win_rate_diff:+.1f}%",
                delta=f"V2が{abs(win_rate_diff):.1f}%{'高い' if win_rate_diff > 0 else '低い'}",
                delta_color="normal" if win_rate_diff >= 0 else "inverse"
            )

        with col3:
            signal_reduction = metrics.get('signal_reduction', 0)
            st.metric(
                "シグナル削減率",
                f"{signal_reduction:.1f}%",
                help="V2はV1より厳選されたシグナル"
            )

        with col4:
            vol_confirm_rate = metrics.get('volume_confirmation_rate', 0)
            st.metric(
                "出来高確認率",
                f"{vol_confirm_rate:.1f}%",
                help="V2シグナルの出来高確認率"
            )

        st.markdown("---")

        # 詳細比較テーブル
        st.subheader("📋 詳細比較")

        import pandas as pd

        comparison_data = {
            '指標': [
                'シグナル数',
                '勝率',
                '平均3ヶ月リターン',
                '平均6ヶ月リターン',
                '平均12ヶ月リターン',
                '最大ドローダウン',
                '平均達成日数'
            ],
            'V1 (スコアベース)': [
                v1_result.total_signals if v1_result else 0,
                f"{v1_result.win_rate:.1f}%" if v1_result else "N/A",
                f"{v1_result.avg_return_3m:.1f}%" if v1_result else "N/A",
                f"{v1_result.avg_return_6m:.1f}%" if v1_result else "N/A",
                f"{v1_result.avg_return_12m:.1f}%" if v1_result else "N/A",
                f"{v1_result.avg_max_drawdown:.1f}%" if v1_result else "N/A",
                f"{v1_result.avg_days_to_target:.0f}日" if v1_result and v1_result.avg_days_to_target else "N/A"
            ],
            'V2 (出来高強化)': [
                v2_result.total_signals if v2_result else 0,
                f"{v2_result.win_rate:.1f}%" if v2_result else "N/A",
                f"{v2_result.avg_return_3m:.1f}%" if v2_result else "N/A",
                f"{v2_result.avg_return_6m:.1f}%" if v2_result else "N/A",
                f"{v2_result.avg_return_12m:.1f}%" if v2_result else "N/A",
                f"{v2_result.avg_max_drawdown:.1f}%" if v2_result else "N/A",
                f"{v2_result.avg_days_to_target:.0f}日" if v2_result and v2_result.avg_days_to_target else "N/A"
            ]
        }

        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 信頼度分布
        if metrics.get('confidence_distribution'):
            st.markdown("---")
            st.subheader("📈 V2 信頼度分布")

            conf_dist = metrics['confidence_distribution']

            col1, col2 = st.columns(2)

            with col1:
                # 信頼度分布チャート
                conf_data = {
                    '信頼度': ['高 (75%+)', '中 (55-74%)', '低 (<55%)'],
                    'シグナル数': [
                        conf_dist.get('high_75_plus', 0),
                        conf_dist.get('moderate_55_74', 0),
                        conf_dist.get('low_below_55', 0)
                    ]
                }
                conf_df = pd.DataFrame(conf_data)

                fig = px.bar(
                    conf_df,
                    x='信頼度',
                    y='シグナル数',
                    color='信頼度',
                    color_discrete_map={
                        '高 (75%+)': '#2ecc71',
                        '中 (55-74%)': '#f39c12',
                        '低 (<55%)': '#e74c3c'
                    },
                    title='V2 シグナル信頼度分布'
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                avg_conf = metrics.get('avg_confidence', 0)
                st.metric("平均信頼度", f"{avg_conf:.1f}%")

                st.markdown("**信頼度別シグナル数:**")
                st.write(f"- 高信頼度 (75%+): {conf_dist.get('high_75_plus', 0)}件")
                st.write(f"- 中信頼度 (55-74%): {conf_dist.get('moderate_55_74', 0)}件")
                st.write(f"- 低信頼度 (<55%): {conf_dist.get('low_below_55', 0)}件")

        # 勝率比較チャート
        st.markdown("---")
        st.subheader("📊 勝率比較")

        if v1_result and v2_result:
            col1, col2 = st.columns(2)

            with col1:
                # 勝率比較バーチャート
                win_rate_data = {
                    'バージョン': ['V1', 'V2'],
                    '勝率': [v1_result.win_rate, v2_result.win_rate]
                }
                win_df = pd.DataFrame(win_rate_data)

                fig = px.bar(
                    win_df,
                    x='バージョン',
                    y='勝率',
                    color='バージョン',
                    color_discrete_map={'V1': '#3498db', 'V2': '#2ecc71'},
                    title='勝率比較 (50%+ in 12ヶ月)'
                )
                fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="目標: 50%")
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # リターン比較バーチャート
                return_data = {
                    '期間': ['3ヶ月', '6ヶ月', '12ヶ月'],
                    'V1': [v1_result.avg_return_3m, v1_result.avg_return_6m, v1_result.avg_return_12m],
                    'V2': [v2_result.avg_return_3m, v2_result.avg_return_6m, v2_result.avg_return_12m]
                }
                return_df = pd.DataFrame(return_data)

                fig = go.Figure()
                fig.add_trace(go.Bar(name='V1', x=return_df['期間'], y=return_df['V1'], marker_color='#3498db'))
                fig.add_trace(go.Bar(name='V2', x=return_df['期間'], y=return_df['V2'], marker_color='#2ecc71'))
                fig.update_layout(
                    barmode='group',
                    title='平均リターン比較',
                    yaxis_title='リターン (%)',
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

        # V2シグナル詳細
        if v2_result and v2_result.outcomes:
            with st.expander("📋 V2 シグナル詳細", expanded=False):
                details = []
                for outcome in v2_result.outcomes:
                    signal = outcome.signal
                    v2_metrics = signal.metrics_snapshot.get('v2_metrics', {})

                    details.append({
                        'シグナル日': signal.signal_date.strftime('%Y-%m-%d') if hasattr(signal.signal_date, 'strftime') else str(signal.signal_date),
                        '信頼度': f"{v2_metrics.get('confidence', 0)}%",
                        '強度': v2_metrics.get('signal_strength', 'N/A'),
                        '出来高確認': '✅' if v2_metrics.get('volume_confirmed', False) else '❌',
                        'エントリー価格': f"${signal.entry_price:,.2f}",
                        '12ヶ月リターン': f"{(outcome.return_12m or 0):.1f}%",
                        '50%達成': '✅' if outcome.is_winner else '❌',
                        '達成日数': outcome.days_to_50pct if outcome.days_to_50pct else 'N/A'
                    })

                details_df = pd.DataFrame(details)
                st.dataframe(details_df, use_container_width=True)


def render_backtest_page():
    """
    バックテストページをレンダリング
    """
    st.markdown('<div class="main-header">🔬 バックテスト</div>', unsafe_allow_html=True)

    # タブで分ける
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 バックテスト実行", "📈 結果表示", "📁 保存済み結果", "💎 Deep Bottom", "🔄 V1 vs V2 比較"])
    
    with tab1:
        st.subheader("バックテスト設定")
        
        # 設定読み込み
        config = load_config()
        symbols = config.get('symbols', [])
        
        if not symbols:
            st.warning("設定ファイルにシンボルがありません")
            return
        
        # シンボル選択
        selected_symbols = st.multiselect(
            "バックテスト対象のシンボルを選択",
            symbols,
            default=symbols[:10] if len(symbols) > 10 else symbols
        )
        
        if not selected_symbols:
            st.warning("少なくとも1つのシンボルを選択してください")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "開始日",
                value=datetime.now() - timedelta(days=365),
                max_value=datetime.now()
            )
        
        with col2:
            end_date = st.date_input(
                "終了日",
                value=datetime.now(),
                max_value=datetime.now(),
                min_value=start_date
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            initial_capital = st.number_input(
                "初期資本 ($)",
                min_value=1000.0,
                value=100000.0,
                step=10000.0
            )
        
        with col2:
            stop_loss_pct = st.number_input(
                "ストップロス (%)",
                min_value=-50.0,
                max_value=0.0,
                value=-10.0,
                step=1.0
            )
        
        with col3:
            take_profit_pct = st.number_input(
                "利確 (%)",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
                step=5.0
            )
        
        # バックテスト実行
        if st.button("🚀 バックテストを実行", type="primary"):
            with st.spinner("バックテストを実行中..."):
                try:
                    backtester = Backtester()
                    result = backtester.backtest_strategy_daily(
                        selected_symbols,
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time()),
                        initial_capital,
                        stop_loss_pct,
                        take_profit_pct
                    )
                    
                    # 結果をセッションに保存
                    st.session_state['last_backtest_result'] = result
                    st.session_state['last_backtest_symbols'] = selected_symbols
                    
                    st.success("バックテストが完了しました！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"バックテスト実行エラー: {e}")
                    import traceback
                    st.exception(e)
    
    with tab2:
        st.subheader("最新のバックテスト結果")
        
        if 'last_backtest_result' not in st.session_state:
            st.info("バックテストを実行してください")
        else:
            result = st.session_state['last_backtest_result']
            symbols = st.session_state.get('last_backtest_symbols', [])
            
            # メトリクス表示
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                total_return = result.get('total_return', 0)
                st.metric("総リターン", f"{total_return:.2f}%")
            
            with col2:
                final_capital = result.get('final_capital', 0)
                initial_capital = result.get('initial_capital', 100000)
                st.metric("最終資本", f"${final_capital:,.2f}")
            
            with col3:
                max_drawdown = result.get('max_drawdown', 0)
                st.metric("最大ドローダウン", f"{max_drawdown:.2f}%")
            
            with col4:
                sharpe_ratio = result.get('sharpe_ratio', 0)
                st.metric("シャープレシオ", f"{sharpe_ratio:.2f}")
            
            with col5:
                win_rate = result.get('win_rate', 0)
                st.metric("勝率", f"{win_rate:.1f}%")
            
            st.markdown("---")
            
            # チャート表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(
                    create_equity_curve_chart(result),
                    use_container_width=True
                )
            
            with col2:
                st.plotly_chart(
                    create_drawdown_chart(result),
                    use_container_width=True
                )
            
            # 取引履歴
            st.subheader("取引履歴")
            trades = result.get('trades', [])
            if trades:
                st.plotly_chart(
                    create_trades_chart(result),
                    use_container_width=True
                )
                
                # 取引詳細テーブル
                with st.expander("取引詳細", expanded=False):
                    trades_df = []
                    for i, trade in enumerate(trades, 1):
                        trades_df.append({
                            '取引番号': i,
                            'シンボル': trade.get('symbol', 'N/A'),
                            'エントリー日': trade.get('entry_date', 'N/A'),
                            'エントリー価格': f"${trade.get('entry_price', 0):,.2f}",
                            'エグジット日': trade.get('exit_date', 'N/A'),
                            'エグジット価格': f"${trade.get('exit_price', 0):,.2f}",
                            'リターン': f"{trade.get('return_pct', 0):.2f}%"
                        })
                    
                    import pandas as pd
                    st.dataframe(pd.DataFrame(trades_df), use_container_width=True)
            else:
                st.info("取引がありませんでした")
            
            # 結果保存
            st.markdown("---")
            st.subheader("結果を保存")
            
            save_name = st.text_input(
                "保存名（オプション）",
                value=f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if st.button("💾 結果を保存"):
                try:
                    filename = save_backtest_result(result, save_name)
                    st.success(f"結果を保存しました: {filename}")
                except Exception as e:
                    st.error(f"保存エラー: {e}")
    
    with tab3:
        st.subheader("保存済みバックテスト結果")
        
        saved_results = load_backtest_results()
        
        if not saved_results:
            st.info("保存されたバックテスト結果がありません")
        else:
            # 結果選択
            result_names = [f"{r.get('filename', 'N/A')} ({r.get('start_date', 'N/A')} - {r.get('end_date', 'N/A')})" 
                           for r in saved_results]
            
            selected_index = st.selectbox(
                "表示する結果を選択",
                range(len(result_names)),
                format_func=lambda x: result_names[x]
            )
            
            if selected_index is not None:
                result = saved_results[selected_index]
                
                # メトリクス表示
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("総リターン", f"{result.get('total_return', 0):.2f}%")
                
                with col2:
                    st.metric("最終資本", f"${result.get('final_capital', 0):,.2f}")
                
                with col3:
                    st.metric("最大ドローダウン", f"{result.get('max_drawdown', 0):.2f}%")
                
                with col4:
                    st.metric("シャープレシオ", f"{result.get('sharpe_ratio', 0):.2f}")
                
                with col5:
                    st.metric("勝率", f"{result.get('win_rate', 0):.1f}%")
                
                st.markdown("---")
                
                # チャート表示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.plotly_chart(
                        create_equity_curve_chart(result),
                        use_container_width=True
                    )
                
                with col2:
                    st.plotly_chart(
                        create_drawdown_chart(result),
                        use_container_width=True
                    )
                
                # 削除ボタン
                if st.button("🗑️ この結果を削除", type="secondary"):
                    try:
                        os.remove(result['filepath'])
                        st.success("結果を削除しました")
                        st.rerun()
                    except Exception as e:
                        st.error(f"削除エラー: {e}")

    with tab4:
        render_deep_bottom_backtest_tab()

    with tab5:
        render_v1_vs_v2_comparison_tab()
