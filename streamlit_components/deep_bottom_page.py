"""
Deep Bottom Detection Page
長期投資向けの歴史的割安銘柄検出ページ
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.state_machine import StateMachine
from core.constants import DEEP_BOTTOM_THRESHOLDS


def get_deep_bottom_analysis(symbols: List[str], progress_callback=None) -> List[Dict]:
    """
    全シンボルのDeep Bottom分析を実行

    Args:
        symbols: 分析対象シンボルのリスト
        progress_callback: 進捗コールバック関数

    Returns:
        分析結果のリスト
    """
    state_machine = StateMachine()
    results = []

    for idx, symbol in enumerate(symbols):
        if progress_callback:
            progress_callback(idx, len(symbols), symbol)

        try:
            detected, metrics = state_machine.check_deep_bottom(symbol)

            if metrics:
                results.append({
                    'symbol': symbol,
                    'detected': detected,
                    'current_price': metrics.get('current_price', 0),
                    'ath_price': metrics.get('ath_price', 0),
                    'drawdown_pct': metrics.get('drawdown_pct', 0),
                    'week52_low_proximity': metrics.get('week52_low_proximity', 0),
                    'rsi_14': metrics.get('rsi_14', 0),
                    'ma_200': metrics.get('ma_200'),
                    'return_7d': metrics.get('return_7d', 0),
                    'conditions': metrics.get('conditions', {})
                })
        except Exception as e:
            # エラーが発生しても続行
            pass

    return results


def render_deep_bottom_page(symbols: List[str]):
    """
    Deep Bottom検出ページをレンダリング

    Args:
        symbols: 監視対象シンボルのリスト
    """
    st.markdown('<div class="main-header">💎 Deep Bottom Detection</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 長期投資向け歴史的割安シグナル

    このページでは、**長期投資向け**に歴史的に極めて割安な銘柄を検出します。
    短期的な価格予測ではなく、**買い持ち（バイ＆ホールド）**戦略に適した銘柄を見つけます。
    """)

    # 検出条件の説明
    with st.expander("📋 検出条件（全て満たす必要あり）", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **1. ATH下落率 ≥ {DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN}%**
            - 史上最高値から大幅に下落
            - 歴史的な割安水準を示す

            **2. 52週安値に近い（{DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX*100:.0f}%以内）**
            - 直近1年の最安値付近
            - 極度の悲観を示す

            **3. RSI ≤ {DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD}**
            - テクニカル的に売られすぎ
            - 反転の可能性
            """)

        with col2:
            st.markdown(f"""
            **4. 200日移動平均より下**
            - 長期トレンドから乖離
            - 平均回帰の余地あり

            **5. 7日リターン > {DEEP_BOTTOM_THRESHOLDS.MIN_7D_RETURN}%**
            - 急落中ではない
            - 落ちるナイフを避ける

            ---
            **注意**: これは投資助言ではありません。
            必ずご自身で調査を行ってください。
            """)

    st.markdown("---")

    # 分析実行セクション
    st.subheader("🔍 銘柄スキャン")

    # 分析対象の選択
    scan_option = st.radio(
        "スキャン対象",
        ["主要銘柄（高速）", "全銘柄（時間がかかります）", "カスタム選択"],
        horizontal=True
    )

    if scan_option == "主要銘柄（高速）":
        # 主要な暗号通貨と株式
        scan_symbols = [
            'BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX',
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CRM',
            'SPY', 'QQQ', 'DIA', 'IWM', 'VTI'
        ]
        # symbolsに存在するもののみに絞る
        scan_symbols = [s for s in scan_symbols if s in symbols]
    elif scan_option == "全銘柄（時間がかかります）":
        scan_symbols = symbols[:100]  # 最大100件に制限
        st.warning(f"パフォーマンスのため、最大100件に制限しています。（{len(symbols)}件中）")
    else:
        scan_symbols = st.multiselect(
            "分析する銘柄を選択",
            symbols,
            default=symbols[:10] if len(symbols) >= 10 else symbols
        )

    if st.button("🚀 スキャン開始", type="primary"):
        if not scan_symbols:
            st.warning("銘柄を選択してください")
            return

        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, symbol):
            progress_bar.progress(current / total)
            status_text.text(f"分析中: {symbol} ({current}/{total})")

        # 分析実行
        with st.spinner("Deep Bottom分析を実行中..."):
            results = get_deep_bottom_analysis(scan_symbols, update_progress)

        progress_bar.empty()
        status_text.empty()

        if not results:
            st.error("分析結果がありません")
            return

        # 結果をセッションに保存
        st.session_state.deep_bottom_results = results

    # 結果表示
    if 'deep_bottom_results' in st.session_state:
        results = st.session_state.deep_bottom_results
        display_deep_bottom_results(results)


def display_deep_bottom_results(results: List[Dict]):
    """
    Deep Bottom分析結果を表示

    Args:
        results: 分析結果のリスト
    """
    st.markdown("---")
    st.subheader("📊 分析結果")

    # シグナル検出された銘柄
    detected = [r for r in results if r.get('detected')]
    not_detected = [r for r in results if not r.get('detected')]

    # サマリーメトリクス
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("分析銘柄数", len(results))
    with col2:
        st.metric("シグナル検出", len(detected), delta=None)
    with col3:
        avg_drawdown = sum(r.get('drawdown_pct', 0) for r in results) / len(results) if results else 0
        st.metric("平均ATH下落率", f"{avg_drawdown:.1f}%")
    with col4:
        avg_rsi = sum(r.get('rsi_14', 0) for r in results if r.get('rsi_14')) / len([r for r in results if r.get('rsi_14')]) if results else 0
        st.metric("平均RSI", f"{avg_rsi:.1f}")

    st.markdown("---")

    # シグナル検出銘柄
    if detected:
        st.success(f"💎 **{len(detected)}件のDeep Bottomシグナルを検出しました！**")

        for item in detected:
            with st.container():
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
                            padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;
                            border-left: 5px solid #00ff88;">
                    <h3 style="color: #00ff88; margin: 0;">💎 {item['symbol']}</h3>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "現在価格",
                        f"${item['current_price']:,.2f}",
                        f"ATH: ${item['ath_price']:,.2f}"
                    )

                with col2:
                    st.metric(
                        "ATH下落率",
                        f"{item['drawdown_pct']:.1f}%",
                        delta=None
                    )

                with col3:
                    st.metric(
                        "RSI(14)",
                        f"{item['rsi_14']:.1f}",
                        "売られすぎ" if item['rsi_14'] <= 30 else ""
                    )

                with col4:
                    proximity_pct = item['week52_low_proximity'] * 100
                    st.metric(
                        "52週安値からの距離",
                        f"{proximity_pct:.1f}%",
                        delta=None
                    )

                # 条件チェック詳細
                conditions = item.get('conditions', {})
                if conditions:
                    st.markdown("**条件達成状況:**")
                    cond_cols = st.columns(5)
                    cond_labels = {
                        'ath_drawdown': 'ATH下落率',
                        'near_52week_low': '52週安値付近',
                        'rsi_oversold': 'RSI売られすぎ',
                        'below_ma200': '200日MA以下',
                        'not_crashing': '急落中でない'
                    }
                    for idx, (key, label) in enumerate(cond_labels.items()):
                        with cond_cols[idx]:
                            if conditions.get(key):
                                st.markdown(f"✅ {label}")
                            else:
                                st.markdown(f"❌ {label}")

                st.markdown("---")
    else:
        st.info("現在、Deep Bottomシグナルを満たす銘柄はありません。")

    # 全銘柄テーブル
    st.subheader("📋 全銘柄の詳細データ")

    # ソートオプション
    sort_by = st.selectbox(
        "並び替え",
        ["ATH下落率（高い順）", "RSI（低い順）", "52週安値からの距離（近い順）", "シグナル検出順"]
    )

    if sort_by == "ATH下落率（高い順）":
        sorted_results = sorted(results, key=lambda x: x.get('drawdown_pct', 0), reverse=True)
    elif sort_by == "RSI（低い順）":
        sorted_results = sorted(results, key=lambda x: x.get('rsi_14', 100))
    elif sort_by == "52週安値からの距離（近い順）":
        sorted_results = sorted(results, key=lambda x: x.get('week52_low_proximity', 1))
    else:
        sorted_results = sorted(results, key=lambda x: x.get('detected', False), reverse=True)

    # データフレーム作成
    df = pd.DataFrame([
        {
            'シンボル': r['symbol'],
            'シグナル': '💎 検出' if r.get('detected') else '-',
            '現在価格': f"${r.get('current_price', 0):,.2f}",
            'ATH価格': f"${r.get('ath_price', 0):,.2f}",
            'ATH下落率': f"{r.get('drawdown_pct', 0):.1f}%",
            'RSI(14)': f"{r.get('rsi_14', 0):.1f}" if r.get('rsi_14') else 'N/A',
            '52週安値距離': f"{r.get('week52_low_proximity', 0)*100:.1f}%",
            '7日リターン': f"{r.get('return_7d', 0):+.1f}%",
            '条件達成数': sum(1 for v in r.get('conditions', {}).values() if v)
        }
        for r in sorted_results
    ])

    st.dataframe(df, use_container_width=True, height=400)

    # 条件別の銘柄数
    st.markdown("---")
    st.subheader("📈 条件別統計")

    col1, col2, col3 = st.columns(3)

    with col1:
        high_drawdown = sum(1 for r in results if r.get('drawdown_pct', 0) >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN)
        st.metric(f"ATH下落率 ≥ {DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN}%", f"{high_drawdown}件")

    with col2:
        low_rsi = sum(1 for r in results if r.get('rsi_14', 100) <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD)
        st.metric(f"RSI ≤ {DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD}", f"{low_rsi}件")

    with col3:
        near_low = sum(1 for r in results if r.get('week52_low_proximity', 1) <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX)
        st.metric(f"52週安値 {DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX*100:.0f}%以内", f"{near_low}件")
