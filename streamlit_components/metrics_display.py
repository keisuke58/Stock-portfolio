"""
財務指標表示コンポーネント
"""
import streamlit as st
from typing import Dict, Optional


def display_metric_card(
    label: str,
    value: any,
    delta: Optional[float] = None,
    format_func: Optional[callable] = None,
    help_text: Optional[str] = None
):
    """
    メトリクスカードを表示
    
    Args:
        label: ラベル
        value: 値
        delta: 変化量（オプション）
        format_func: 値のフォーマット関数
        help_text: ヘルプテキスト
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if help_text:
            st.metric(label, value, delta=delta, help=help_text)
        else:
            st.metric(label, value, delta=delta)
    
    if format_func and value is not None:
        with col2:
            st.caption(format_func(value))


def display_financial_metrics(
    financial_data: Dict,
    columns: int = 3
):
    """
    財務指標をカード形式で表示
    
    Args:
        financial_data: 財務データの辞書
        columns: カラム数
    """
    if not financial_data:
        st.warning("財務データがありません")
        return
    
    # 主要指標を定義
    metrics = [
        {
            'label': '現在価格',
            'key': 'current_price',
            'format': lambda x: f"${x:,.2f}" if x else "N/A",
            'help': '現在の株価'
        },
        {
            'label': 'PER',
            'key': 'pe_ratio',
            'format': lambda x: f"{x:.2f}" if x else "N/A",
            'help': '株価収益率'
        },
        {
            'label': 'PBR',
            'key': 'pb_ratio',
            'format': lambda x: f"{x:.2f}" if x else "N/A",
            'help': '株価純資産倍率'
        },
        {
            'label': '配当利回り',
            'key': 'dividend_yield',
            'format': lambda x: f"{x*100:.2f}%" if x and x < 1 else f"{x:.2f}%" if x else "N/A",
            'help': '年間配当利回り'
        },
        {
            'label': 'ROE',
            'key': 'roe',
            'format': lambda x: f"{x*100:.2f}%" if x else "N/A",
            'help': '自己資本利益率'
        },
        {
            'label': 'ROA',
            'key': 'roa',
            'format': lambda x: f"{x*100:.2f}%" if x else "N/A",
            'help': '総資産利益率'
        },
        {
            'label': '売上成長率',
            'key': 'revenue_growth',
            'format': lambda x: f"{x*100:+.2f}%" if x else "N/A",
            'help': '売上高成長率'
        },
        {
            'label': '利益率',
            'key': 'profit_margin',
            'format': lambda x: f"{x*100:.2f}%" if x else "N/A",
            'help': '純利益率'
        },
        {
            'label': '負債資本比率',
            'key': 'debt_to_equity',
            'format': lambda x: f"{x:.2f}" if x else "N/A",
            'help': '負債/自己資本'
        }
    ]
    
    # カラムで表示
    cols = st.columns(columns)
    for idx, metric in enumerate(metrics):
        col = cols[idx % columns]
        with col:
            value = financial_data.get(metric['key'])
            formatted_value = metric['format'](value) if value is not None else "N/A"
            st.metric(
                metric['label'],
                formatted_value,
                help=metric['help']
            )


def display_score_breakdown(
    value_score: float,
    momentum_score: float,
    stability_score: float,
    total_score: float
):
    """
    スコア内訳を表示
    
    Args:
        value_score: Valueスコア
        momentum_score: Momentumスコア
        stability_score: Stabilityスコア
        total_score: 総合スコア
    """
    st.subheader("📊 スコア内訳")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総合スコア", f"{total_score:.1f}", help="Value 40% + Momentum 35% + Stability 25%")
    
    with col2:
        st.metric("Value", f"{value_score:.1f}", help="割安度スコア（重み40%）")
    
    with col3:
        st.metric("Momentum", f"{momentum_score:.1f}", help="反転スコア（重み35%）")
    
    with col4:
        st.metric("Stability", f"{stability_score:.1f}", help="安定性スコア（重み25%）")
    
    # プログレスバーで可視化
    st.progress(value_score / 100, text="Value")
    st.progress(momentum_score / 100, text="Momentum")
    st.progress(stability_score / 100, text="Stability")


def display_investment_summary(
    data: Dict
):
    """
    投資判断サマリーを表示
    
    Args:
        data: 投資分析結果の辞書
    """
    st.subheader("💡 投資判断サマリー")
    
    # 投資スタンス
    stance = data.get('investment_stance', '様子見')
    risk_level = data.get('risk_level', '中')
    current_state = data.get('current_state', 'NORMAL')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # スタンスに応じた色
        if stance == "積極的買い":
            st.success(f"**投資スタンス**: {stance}")
        elif stance == "買い":
            st.info(f"**投資スタンス**: {stance}")
        elif stance == "様子見":
            st.warning(f"**投資スタンス**: {stance}")
        else:
            st.error(f"**投資スタンス**: {stance}")
    
    with col2:
        # リスクレベルに応じた色
        if risk_level == "低":
            st.success(f"**リスクレベル**: {risk_level}")
        elif risk_level == "中":
            st.warning(f"**リスクレベル**: {risk_level}")
        else:
            st.error(f"**リスクレベル**: {risk_level}")
    
    with col3:
        # 状態に応じた色
        if current_state == "BUY":
            st.success(f"**状態**: {current_state}")
        elif current_state == "BASE":
            st.warning(f"**状態**: {current_state}")
        elif current_state == "WATCH":
            st.error(f"**状態**: {current_state}")
        else:
            st.info(f"**状態**: {current_state}")
    
    # 強み・弱み
    if 'strengths' in data or 'weaknesses' in data:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'strengths' in data and data['strengths']:
                st.success("**強み**")
                for strength in data['strengths']:
                    st.write(f"✅ {strength}")
            else:
                st.info("**強み**: 特になし")
        
        with col2:
            if 'weaknesses' in data and data['weaknesses']:
                st.error("**弱み・懸念点**")
                for weakness in data['weaknesses']:
                    st.write(f"⚠️ {weakness}")
            else:
                st.info("**弱み・懸念点**: 特に大きな懸念なし")
