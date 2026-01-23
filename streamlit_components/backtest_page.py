"""
バックテストページコンポーネント
バックテスト実行UI、結果可視化、実績データ保存
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


def render_backtest_page():
    """
    バックテストページをレンダリング
    """
    st.markdown('<div class="main-header">🔬 バックテスト</div>', unsafe_allow_html=True)
    
    # タブで分ける
    tab1, tab2, tab3 = st.tabs(["📊 バックテスト実行", "📈 結果表示", "📁 保存済み結果"])
    
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
