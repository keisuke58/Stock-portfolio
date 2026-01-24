"""
アラート・通知管理コンポーネント
価格アラート、スコア変化アラートの設定と管理
"""
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd


def init_alerts_session():
    """アラートセッションを初期化"""
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'alert_history' not in st.session_state:
        st.session_state.alert_history = []


def add_price_alert(symbol: str, alert_type: str, threshold: float, condition: str = "above"):
    """価格アラートを追加"""
    init_alerts_session()
    
    alert = {
        'id': f"{symbol}_{alert_type}_{datetime.now().timestamp()}",
        'symbol': symbol.upper(),
        'type': 'price',
        'alert_type': alert_type,  # 'price' or 'change'
        'threshold': threshold,
        'condition': condition,  # 'above' or 'below'
        'created_at': datetime.now().isoformat(),
        'active': True
    }
    
    st.session_state.alerts.append(alert)
    return alert


def add_score_alert(symbol: str, threshold: float, condition: str = "above"):
    """スコアアラートを追加"""
    init_alerts_session()
    
    alert = {
        'id': f"{symbol}_score_{datetime.now().timestamp()}",
        'symbol': symbol.upper(),
        'type': 'score',
        'threshold': threshold,
        'condition': condition,
        'created_at': datetime.now().isoformat(),
        'active': True
    }
    
    st.session_state.alerts.append(alert)
    return alert


def remove_alert(alert_id: str):
    """アラートを削除"""
    if 'alerts' in st.session_state:
        st.session_state.alerts = [a for a in st.session_state.alerts if a['id'] != alert_id]


def toggle_alert(alert_id: str):
    """アラートの有効/無効を切り替え"""
    if 'alerts' in st.session_state:
        for alert in st.session_state.alerts:
            if alert['id'] == alert_id:
                alert['active'] = not alert['active']
                break


def add_alert_history(alert: Dict, triggered: bool, current_value: float):
    """アラート履歴に追加"""
    init_alerts_session()
    
    history_entry = {
        'alert_id': alert['id'],
        'symbol': alert['symbol'],
        'type': alert['type'],
        'triggered': triggered,
        'current_value': current_value,
        'threshold': alert['threshold'],
        'timestamp': datetime.now().isoformat()
    }
    
    st.session_state.alert_history.append(history_entry)


def check_alerts(symbol: str, current_price: Optional[float] = None, current_score: Optional[float] = None):
    """アラートをチェック（実際の実装では定期的に実行）"""
    init_alerts_session()
    triggered_alerts = []
    
    for alert in st.session_state.alerts:
        if not alert['active'] or alert['symbol'] != symbol.upper():
            continue
        
        if alert['type'] == 'price' and current_price is not None:
            threshold = alert['threshold']
            condition = alert['condition']
            
            if condition == 'above' and current_price >= threshold:
                triggered_alerts.append(alert)
                add_alert_history(alert, True, current_price)
            elif condition == 'below' and current_price <= threshold:
                triggered_alerts.append(alert)
                add_alert_history(alert, True, current_price)
        
        elif alert['type'] == 'score' and current_score is not None:
            threshold = alert['threshold']
            condition = alert['condition']
            
            if condition == 'above' and current_score >= threshold:
                triggered_alerts.append(alert)
                add_alert_history(alert, True, current_score)
            elif condition == 'below' and current_score <= threshold:
                triggered_alerts.append(alert)
                add_alert_history(alert, True, current_score)
    
    return triggered_alerts


def render_alert_management():
    """アラート管理UIをレンダリング"""
    st.subheader("🔔 アラート管理")
    
    init_alerts_session()
    alerts = st.session_state.alerts
    
    # アラート追加フォーム
    with st.expander("➕ アラートを追加", expanded=False):
        alert_type = st.radio("アラートタイプ", ["価格", "スコア"], horizontal=True, key="alert_type_select")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alert_symbol = st.text_input("シンボル", key="alert_symbol", placeholder="例: AAPL")
        
        if alert_type == "価格":
            with col2:
                price_alert_type = st.selectbox("アラート種類", ["価格", "変化率"], key="price_alert_type")
            with col3:
                price_condition = st.selectbox("条件", ["以上", "以下"], key="price_condition")
            
            threshold = st.number_input("閾値", min_value=0.0, value=0.0, step=0.01, key="price_threshold")
            
            if st.button("価格アラートを追加", key="add_price_alert"):
                if alert_symbol and threshold > 0:
                    condition = "above" if price_condition == "以上" else "below"
                    add_price_alert(alert_symbol, price_alert_type, threshold, condition)
                    st.success(f"{alert_symbol}の価格アラートを追加しました")
                    st.rerun()
        else:
            with col2:
                score_condition = st.selectbox("条件", ["以上", "以下"], key="score_condition")
            with col3:
                pass
            
            threshold = st.number_input("スコア閾値", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="score_threshold")
            
            if st.button("スコアアラートを追加", key="add_score_alert"):
                if alert_symbol and threshold > 0:
                    condition = "above" if score_condition == "以上" else "below"
                    add_score_alert(alert_symbol, threshold, condition)
                    st.success(f"{alert_symbol}のスコアアラートを追加しました")
                    st.rerun()
    
    # アラート一覧
    if alerts:
        st.markdown("---")
        st.subheader("📋 アクティブなアラート")
        
        alerts_df = pd.DataFrame([
            {
                'シンボル': alert['symbol'],
                'タイプ': '価格' if alert['type'] == 'price' else 'スコア',
                '条件': f"{'以上' if alert['condition'] == 'above' else '以下'} {alert['threshold']}",
                '状態': '有効' if alert['active'] else '無効',
                '作成日': datetime.fromisoformat(alert['created_at']).strftime('%Y-%m-%d %H:%M')
            }
            for alert in alerts
        ])
        
        st.dataframe(alerts_df, use_container_width=True)
        
        # アラート操作
        st.markdown("---")
        st.subheader("⚙️ アラート操作")
        
        if alerts:
            alert_options = [f"{a['symbol']} - {a['type']} ({'有効' if a['active'] else '無効'})" for a in alerts]
            selected_alert_idx = st.selectbox("アラートを選択", range(len(alerts)), format_func=lambda i: alert_options[i], key="select_alert")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("有効/無効を切り替え", key="toggle_alert"):
                    toggle_alert(alerts[selected_alert_idx]['id'])
                    st.rerun()
            with col2:
                if st.button("削除", key="delete_alert"):
                    remove_alert(alerts[selected_alert_idx]['id'])
                    st.success("アラートを削除しました")
                    st.rerun()
    else:
        st.info("アラートが設定されていません。")
    
    # アラート履歴
    if st.session_state.alert_history:
        st.markdown("---")
        st.subheader("📜 アラート履歴")
        
        history_df = pd.DataFrame([
            {
                'シンボル': h['symbol'],
                'タイプ': h['type'],
                '発動': '✓' if h['triggered'] else '✗',
                '現在値': h['current_value'],
                '閾値': h['threshold'],
                '発動時刻': datetime.fromisoformat(h['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            }
            for h in reversed(st.session_state.alert_history[-50:])  # 最新50件
        ])
        
        st.dataframe(history_df, use_container_width=True)


def render_alerts_page():
    """アラートページ全体をレンダリング"""
    st.markdown('<div class="main-header">🔔 アラート・通知</div>', unsafe_allow_html=True)
    render_alert_management()
