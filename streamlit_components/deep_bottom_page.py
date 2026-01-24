"""
Deep Bottom Detection Page
長期投資向けの歴史的割安銘柄検出ページ
段階的スキャン機能付き
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.state_machine import StateMachine
from core.constants import DEEP_BOTTOM_THRESHOLDS


def analyze_single_symbol(state_machine: StateMachine, symbol: str) -> Optional[Dict]:
    """
    単一シンボルのDeep Bottom分析

    Args:
        state_machine: StateMachineインスタンス
        symbol: 分析対象シンボル

    Returns:
        分析結果辞書 or None
    """
    try:
        detected, metrics = state_machine.check_deep_bottom(symbol)

        if metrics:
            return {
                'symbol': symbol,
                'detected': detected,
                'current_price': metrics.get('current_price', 0),
                'ath_price': metrics.get('ath_price', 0),
                'drawdown_pct': metrics.get('drawdown_pct', 0),
                'week52_low_proximity': metrics.get('week52_low_proximity', 0),
                'rsi_14': metrics.get('rsi_14', 0),
                'ma_200': metrics.get('ma_200'),
                'return_7d': metrics.get('return_7d', 0),
                'conditions': metrics.get('conditions', {}),
                'analyzed_at': datetime.now().isoformat()
            }
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e),
            'detected': False
        }
    return None


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

    # セッション状態の初期化
    if 'deep_bottom_results' not in st.session_state:
        st.session_state.deep_bottom_results = []
    if 'deep_bottom_scanned' not in st.session_state:
        st.session_state.deep_bottom_scanned = set()
    if 'deep_bottom_scanning' not in st.session_state:
        st.session_state.deep_bottom_scanning = False
    if 'deep_bottom_detected_live' not in st.session_state:
        st.session_state.deep_bottom_detected_live = []

    # 分析実行セクション
    st.subheader("🔍 銘柄スキャン")

    # タブで分ける
    tab1, tab2, tab3 = st.tabs(["🚀 クイックスキャン", "🌐 全銘柄スキャン", "📝 カスタム選択"])

    with tab1:
        render_quick_scan(symbols)

    with tab2:
        render_full_scan(symbols)

    with tab3:
        render_custom_scan(symbols)

    # 結果表示
    if st.session_state.deep_bottom_results:
        display_deep_bottom_results(st.session_state.deep_bottom_results)


def render_quick_scan(symbols: List[str]):
    """クイックスキャン（主要銘柄のみ）"""
    st.markdown("**主要な暗号通貨・株式を素早くスキャン**")

    # 主要銘柄リスト
    major_symbols = [
        'BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX',
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CRM',
        'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'NFLX', 'PYPL', 'SQ', 'COIN', 'MSTR'
    ]
    scan_symbols = [s for s in major_symbols if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    if st.button("🚀 クイックスキャン開始", key="quick_scan"):
        run_scan(scan_symbols)


def render_full_scan(symbols: List[str]):
    """全銘柄スキャン（段階的処理）"""
    st.markdown("**全銘柄を段階的にスキャン（バッチ処理）**")

    total_symbols = len(symbols)
    scanned_count = len(st.session_state.deep_bottom_scanned)
    remaining = total_symbols - scanned_count

    # 進捗表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("全銘柄数", total_symbols)
    with col2:
        st.metric("スキャン済み", scanned_count)
    with col3:
        st.metric("残り", remaining)

    if scanned_count > 0:
        st.progress(scanned_count / total_symbols)

    # バッチサイズ設定
    batch_size = st.select_slider(
        "バッチサイズ（1回あたりの処理数）",
        options=[10, 25, 50, 100, 200],
        value=50,
        key="batch_size"
    )

    # スキャン戦略
    strategy = st.radio(
        "スキャン戦略",
        ["順番にスキャン", "ランダムにスキャン", "暗号通貨優先"],
        horizontal=True,
        key="scan_strategy"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ 次のバッチをスキャン", key="next_batch", type="primary"):
            # 未スキャンの銘柄を取得
            unscanned = [s for s in symbols if s not in st.session_state.deep_bottom_scanned]

            if not unscanned:
                st.success("全銘柄のスキャンが完了しました！")
                return

            # 戦略に応じてソート
            if strategy == "ランダムにスキャン":
                import random
                random.shuffle(unscanned)
            elif strategy == "暗号通貨優先":
                from signals import is_crypto_symbol
                crypto = [s for s in unscanned if is_crypto_symbol(s)]
                stocks = [s for s in unscanned if not is_crypto_symbol(s)]
                unscanned = crypto + stocks

            # バッチ取得
            batch = unscanned[:batch_size]
            run_batch_scan(batch, show_live=True)

    with col2:
        if st.button("⏭️ 全てスキャン（自動継続）", key="auto_scan"):
            run_auto_scan(symbols, batch_size)

    with col3:
        if st.button("🔄 リセット", key="reset_scan"):
            st.session_state.deep_bottom_results = []
            st.session_state.deep_bottom_scanned = set()
            st.session_state.deep_bottom_detected_live = []
            st.rerun()

    # リアルタイム検出表示
    if st.session_state.deep_bottom_detected_live:
        st.markdown("---")
        st.subheader("🎯 リアルタイム検出")
        for item in st.session_state.deep_bottom_detected_live[-5:]:  # 最新5件
            st.success(f"💎 **{item['symbol']}** - ATH下落率: {item['drawdown_pct']:.1f}%, RSI: {item['rsi_14']:.1f}")


def render_custom_scan(symbols: List[str]):
    """カスタム選択スキャン"""
    st.markdown("**分析する銘柄を手動で選択**")

    # 検索フィルタ
    search = st.text_input("🔍 銘柄検索", key="symbol_search")

    filtered_symbols = symbols
    if search:
        filtered_symbols = [s for s in symbols if search.upper() in s.upper()]

    selected = st.multiselect(
        f"銘柄を選択（{len(filtered_symbols)}件中）",
        filtered_symbols,
        default=[],
        key="custom_symbols"
    )

    if selected:
        st.info(f"選択中: {len(selected)}銘柄")

        if st.button("🔍 選択銘柄をスキャン", key="custom_scan"):
            run_scan(selected)


def run_scan(symbols: List[str]):
    """シンプルなスキャン実行"""
    state_machine = StateMachine()
    results = []

    progress_bar = st.progress(0)
    status = st.empty()
    detected_container = st.empty()

    detected_symbols = []

    for idx, symbol in enumerate(symbols):
        progress_bar.progress((idx + 1) / len(symbols))
        status.text(f"分析中: {symbol} ({idx + 1}/{len(symbols)})")

        result = analyze_single_symbol(state_machine, symbol)
        if result:
            results.append(result)
            st.session_state.deep_bottom_scanned.add(symbol)

            if result.get('detected'):
                detected_symbols.append(result)
                detected_container.success(
                    f"💎 検出: {symbol} (ATH下落率: {result['drawdown_pct']:.1f}%)"
                )

    progress_bar.empty()
    status.empty()

    # 結果をマージ
    existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
    for r in results:
        if r['symbol'] not in existing_symbols:
            st.session_state.deep_bottom_results.append(r)

    st.session_state.deep_bottom_detected_live = detected_symbols
    st.rerun()


def run_batch_scan(symbols: List[str], show_live: bool = True):
    """バッチスキャン実行"""
    state_machine = StateMachine()
    results = []

    progress_bar = st.progress(0)
    status = st.empty()
    live_display = st.empty() if show_live else None

    detected_in_batch = []
    start_time = time.time()

    for idx, symbol in enumerate(symbols):
        progress_bar.progress((idx + 1) / len(symbols))

        elapsed = time.time() - start_time
        if idx > 0:
            avg_time = elapsed / idx
            remaining = avg_time * (len(symbols) - idx)
            status.text(f"分析中: {symbol} ({idx + 1}/{len(symbols)}) - 残り約{remaining:.0f}秒")
        else:
            status.text(f"分析中: {symbol} ({idx + 1}/{len(symbols)})")

        result = analyze_single_symbol(state_machine, symbol)
        if result:
            results.append(result)
            st.session_state.deep_bottom_scanned.add(symbol)

            if result.get('detected'):
                detected_in_batch.append(result)
                if live_display:
                    live_display.success(
                        f"💎 **{symbol}** 検出! "
                        f"ATH下落率: {result['drawdown_pct']:.1f}%, "
                        f"RSI: {result['rsi_14']:.1f}"
                    )

    progress_bar.empty()
    status.empty()

    # 結果をマージ
    existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
    for r in results:
        if r['symbol'] not in existing_symbols:
            st.session_state.deep_bottom_results.append(r)

    # ライブ検出リストに追加
    st.session_state.deep_bottom_detected_live.extend(detected_in_batch)

    # 完了メッセージ
    elapsed = time.time() - start_time
    st.success(f"✅ {len(symbols)}銘柄を{elapsed:.1f}秒で分析完了（検出: {len(detected_in_batch)}件）")

    st.rerun()


def run_auto_scan(symbols: List[str], batch_size: int):
    """自動継続スキャン"""
    unscanned = [s for s in symbols if s not in st.session_state.deep_bottom_scanned]

    if not unscanned:
        st.success("全銘柄のスキャンが完了しています！")
        return

    state_machine = StateMachine()
    total_batches = (len(unscanned) + batch_size - 1) // batch_size

    # 全体進捗
    overall_progress = st.progress(0)
    batch_status = st.empty()
    current_status = st.empty()
    live_detections = st.empty()

    all_detected = []
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(unscanned))
        batch = unscanned[batch_start:batch_end]

        batch_status.markdown(f"**バッチ {batch_idx + 1}/{total_batches}** ({len(batch)}銘柄)")

        for idx, symbol in enumerate(batch):
            overall_done = batch_start + idx + 1
            overall_progress.progress(overall_done / len(unscanned))

            elapsed = time.time() - start_time
            if overall_done > 1:
                avg_time = elapsed / overall_done
                remaining = avg_time * (len(unscanned) - overall_done)
                mins, secs = divmod(int(remaining), 60)
                current_status.text(
                    f"分析中: {symbol} ({overall_done}/{len(unscanned)}) - "
                    f"残り約{mins}分{secs}秒"
                )
            else:
                current_status.text(f"分析中: {symbol} ({overall_done}/{len(unscanned)})")

            result = analyze_single_symbol(state_machine, symbol)
            if result:
                st.session_state.deep_bottom_scanned.add(symbol)

                # 既存結果にマージ
                existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
                if symbol not in existing_symbols:
                    st.session_state.deep_bottom_results.append(result)

                if result.get('detected'):
                    all_detected.append(result)
                    # 最新の検出を表示
                    recent = all_detected[-3:] if len(all_detected) >= 3 else all_detected
                    detection_text = "\n".join([
                        f"💎 **{r['symbol']}** (ATH下落: {r['drawdown_pct']:.1f}%, RSI: {r['rsi_14']:.1f})"
                        for r in recent
                    ])
                    live_detections.markdown(f"**リアルタイム検出:**\n{detection_text}")

    overall_progress.empty()
    batch_status.empty()
    current_status.empty()

    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)

    st.session_state.deep_bottom_detected_live = all_detected

    st.success(
        f"✅ 全{len(unscanned)}銘柄のスキャン完了！ "
        f"（{mins}分{secs}秒、検出: {len(all_detected)}件）"
    )

    st.rerun()


def display_deep_bottom_results(results: List[Dict]):
    """
    Deep Bottom分析結果を表示

    Args:
        results: 分析結果のリスト
    """
    st.markdown("---")
    st.subheader("📊 分析結果")

    # エラーを除外
    valid_results = [r for r in results if 'error' not in r]

    # シグナル検出された銘柄
    detected = [r for r in valid_results if r.get('detected')]

    # サマリーメトリクス
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("分析銘柄数", len(valid_results))
    with col2:
        st.metric("シグナル検出", len(detected), delta=None)
    with col3:
        avg_drawdown = sum(r.get('drawdown_pct', 0) for r in valid_results) / len(valid_results) if valid_results else 0
        st.metric("平均ATH下落率", f"{avg_drawdown:.1f}%")
    with col4:
        rsi_values = [r.get('rsi_14', 0) for r in valid_results if r.get('rsi_14')]
        avg_rsi = sum(rsi_values) / len(rsi_values) if rsi_values else 0
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

    # フィルタ
    col1, col2 = st.columns(2)
    with col1:
        show_only_detected = st.checkbox("シグナル検出のみ表示", value=False)
    with col2:
        min_conditions = st.slider("最低条件達成数", 0, 5, 0)

    # ソートオプション
    sort_by = st.selectbox(
        "並び替え",
        ["条件達成数（多い順）", "ATH下落率（高い順）", "RSI（低い順）", "52週安値からの距離（近い順）", "シグナル検出順"],
        key="sort_results"
    )

    # フィルタ適用
    filtered_results = valid_results
    if show_only_detected:
        filtered_results = [r for r in filtered_results if r.get('detected')]
    if min_conditions > 0:
        filtered_results = [
            r for r in filtered_results
            if sum(1 for v in r.get('conditions', {}).values() if v) >= min_conditions
        ]

    # ソート
    if sort_by == "条件達成数（多い順）":
        sorted_results = sorted(
            filtered_results,
            key=lambda x: sum(1 for v in x.get('conditions', {}).values() if v),
            reverse=True
        )
    elif sort_by == "ATH下落率（高い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('drawdown_pct', 0), reverse=True)
    elif sort_by == "RSI（低い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('rsi_14', 100))
    elif sort_by == "52週安値からの距離（近い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('week52_low_proximity', 1))
    else:
        sorted_results = sorted(filtered_results, key=lambda x: x.get('detected', False), reverse=True)

    st.info(f"表示: {len(sorted_results)}件 / 全{len(valid_results)}件")

    # データフレーム作成
    if sorted_results:
        df = pd.DataFrame([
            {
                'シンボル': r['symbol'],
                'シグナル': '💎' if r.get('detected') else '',
                '条件達成': f"{sum(1 for v in r.get('conditions', {}).values() if v)}/5",
                '現在価格': f"${r.get('current_price', 0):,.2f}",
                'ATH下落率': f"{r.get('drawdown_pct', 0):.1f}%",
                'RSI(14)': f"{r.get('rsi_14', 0):.1f}" if r.get('rsi_14') else 'N/A',
                '52週安値距離': f"{r.get('week52_low_proximity', 0)*100:.1f}%",
                '7日リターン': f"{r.get('return_7d', 0):+.1f}%"
            }
            for r in sorted_results
        ])

        st.dataframe(df, use_container_width=True, height=400)

    # 条件別の銘柄数
    st.markdown("---")
    st.subheader("📈 条件別統計")

    col1, col2, col3 = st.columns(3)

    with col1:
        high_drawdown = sum(1 for r in valid_results if r.get('drawdown_pct', 0) >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN)
        st.metric(f"ATH下落率 ≥ {DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN}%", f"{high_drawdown}件")

    with col2:
        low_rsi = sum(1 for r in valid_results if r.get('rsi_14', 100) <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD)
        st.metric(f"RSI ≤ {DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD}", f"{low_rsi}件")

    with col3:
        near_low = sum(1 for r in valid_results if r.get('week52_low_proximity', 1) <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX)
        st.metric(f"52週安値 {DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX*100:.0f}%以内", f"{near_low}件")

    # 条件達成数別分布
    st.markdown("---")
    condition_counts = {}
    for r in valid_results:
        count = sum(1 for v in r.get('conditions', {}).values() if v)
        condition_counts[count] = condition_counts.get(count, 0) + 1

    st.subheader("📊 条件達成数別分布")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            count = condition_counts.get(i, 0)
            st.metric(f"{i}条件", f"{count}件")
