"""
ポートフォリオ追跡コンポーネント
ユーザーポートフォリオの登録・管理・パフォーマンス可視化
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def init_portfolio_session():
    """ポートフォリオセッションを初期化"""
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []


def add_to_portfolio(symbol: str, shares: float, purchase_price: float, purchase_date: str = None):
    """ポートフォリオに銘柄を追加"""
    init_portfolio_session()
    
    if purchase_date is None:
        purchase_date = datetime.now().strftime('%Y-%m-%d')
    
    entry = {
        'symbol': symbol.upper(),
        'shares': shares,
        'purchase_price': purchase_price,
        'purchase_date': purchase_date,
        'added_at': datetime.now().isoformat()
    }
    
    st.session_state.portfolio.append(entry)
    return entry


def remove_from_portfolio(index: int):
    """ポートフォリオから銘柄を削除"""
    if 'portfolio' in st.session_state and 0 <= index < len(st.session_state.portfolio):
        st.session_state.portfolio.pop(index)


def get_portfolio_data() -> List[Dict]:
    """ポートフォリオデータを取得"""
    init_portfolio_session()
    return st.session_state.portfolio


def calculate_portfolio_performance(portfolio: List[Dict], current_prices: Dict[str, float]) -> Dict:
    """ポートフォリオパフォーマンスを計算"""
    total_cost = 0
    total_value = 0
    positions = []
    
    for entry in portfolio:
        symbol = entry['symbol']
        shares = entry['shares']
        purchase_price = entry['purchase_price']
        current_price = current_prices.get(symbol, purchase_price)
        
        cost = shares * purchase_price
        value = shares * current_price
        gain_loss = value - cost
        gain_loss_pct = (gain_loss / cost * 100) if cost > 0 else 0
        
        total_cost += cost
        total_value += value
        
        positions.append({
            'symbol': symbol,
            'shares': shares,
            'purchase_price': purchase_price,
            'current_price': current_price,
            'cost': cost,
            'value': value,
            'gain_loss': gain_loss,
            'gain_loss_pct': gain_loss_pct
        })
    
    total_gain_loss = total_value - total_cost
    total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'total_value': total_value,
        'total_gain_loss': total_gain_loss,
        'total_gain_loss_pct': total_gain_loss_pct,
        'positions': positions
    }


def render_portfolio_management():
    """ポートフォリオ管理UIをレンダリング"""
    st.subheader("📊 ポートフォリオ管理")
    
    init_portfolio_session()
    portfolio = get_portfolio_data()
    
    # 銘柄追加フォーム
    with st.expander("➕ 銘柄を追加", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            new_symbol = st.text_input("シンボル", key="new_symbol", placeholder="例: AAPL")
        with col2:
            new_shares = st.number_input("株数", min_value=0.0, value=1.0, step=0.1, key="new_shares")
        with col3:
            new_price = st.number_input("購入価格", min_value=0.0, value=0.0, step=0.01, key="new_price")
        with col4:
            new_date = st.date_input("購入日", value=datetime.now(), key="new_date")
        
        if st.button("追加", key="add_portfolio"):
            if new_symbol and new_shares > 0 and new_price > 0:
                add_to_portfolio(new_symbol, new_shares, new_price, new_date.strftime('%Y-%m-%d'))
                st.success(f"{new_symbol}をポートフォリオに追加しました")
                st.rerun()
            else:
                st.error("すべてのフィールドを正しく入力してください")
    
    # ポートフォリオ一覧
    if portfolio:
        st.subheader("📋 ポートフォリオ一覧")
        
        # 現在価格を取得（簡易版：実際の実装ではAPIから取得）
        current_prices = {}
        for entry in portfolio:
            symbol = entry['symbol']
            # ここでは購入価格を現在価格として使用（実際の実装ではAPIから取得）
            current_prices[symbol] = entry['purchase_price'] * 1.05  # 仮の値
        
        performance = calculate_portfolio_performance(portfolio, current_prices)
        
        # パフォーマンスサマリー
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総投資額", f"${performance['total_cost']:,.2f}")
        with col2:
            st.metric("現在価値", f"${performance['total_value']:,.2f}")
        with col3:
            gain_loss_color = "normal" if performance['total_gain_loss'] >= 0 else "inverse"
            st.metric(
                "損益",
                f"${performance['total_gain_loss']:,.2f}",
                f"{performance['total_gain_loss_pct']:.2f}%",
                delta_color=gain_loss_color
            )
        with col4:
            st.metric("銘柄数", len(portfolio))
        
        st.markdown("---")
        
        # ポジション一覧テーブル
        positions_df = pd.DataFrame([
            {
                'シンボル': pos['symbol'],
                '株数': pos['shares'],
                '購入価格': f"${pos['purchase_price']:.2f}",
                '現在価格': f"${pos['current_price']:.2f}",
                '投資額': f"${pos['cost']:,.2f}",
                '現在価値': f"${pos['value']:,.2f}",
                '損益': f"${pos['gain_loss']:,.2f}",
                '損益率': f"{pos['gain_loss_pct']:.2f}%"
            }
            for pos in performance['positions']
        ])
        
        st.dataframe(positions_df, use_container_width=True)
        
        # ポートフォリオ削除
        st.markdown("---")
        st.subheader("🗑️ 銘柄を削除")
        if portfolio:
            delete_index = st.selectbox(
                "削除する銘柄を選択",
                range(len(portfolio)),
                format_func=lambda i: f"{portfolio[i]['symbol']} - {portfolio[i]['shares']}株",
                key="delete_portfolio"
            )
            if st.button("削除", key="delete_button"):
                remove_from_portfolio(delete_index)
                st.success("銘柄を削除しました")
                st.rerun()
        
        # ポートフォリオ可視化
        st.markdown("---")
        st.subheader("📈 ポートフォリオ可視化")
        
        # アセットアロケーション
        col1, col2 = st.columns(2)
        
        with col1:
            # 円グラフ
            symbols = [pos['symbol'] for pos in performance['positions']]
            values = [pos['value'] for pos in performance['positions']]
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=symbols,
                values=values,
                hole=0.4,
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>価値: $%{value:,.2f}<br>割合: %{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title="アセットアロケーション",
                height=400,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 損益バーチャート
            symbols = [pos['symbol'] for pos in performance['positions']]
            gains = [pos['gain_loss'] for pos in performance['positions']]
            colors = ['#26a69a' if g >= 0 else '#ef5350' for g in gains]
            
            fig_bar = go.Figure(data=[go.Bar(
                x=symbols,
                y=gains,
                marker_color=colors,
                text=[f"${g:,.2f}" for g in gains],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>損益: $%{y:,.2f}<extra></extra>'
            )])
            
            fig_bar.update_layout(
                title="銘柄別損益",
                xaxis=dict(title="銘柄"),
                yaxis=dict(title="損益 (USD)"),
                height=400,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("ポートフォリオが空です。銘柄を追加してください。")


def render_portfolio_page():
    """ポートフォリオページ全体をレンダリング"""
    st.markdown('<div class="main-header">💼 ポートフォリオ追跡</div>', unsafe_allow_html=True)
    render_portfolio_management()
