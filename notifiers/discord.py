"""
Discord通知モジュール
状態変化 or Daily pick を通知
"""
import requests
from typing import Optional
from datetime import datetime


class DiscordNotifier:
    """Discord Webhookに通知を送信するクラス"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, message: str) -> bool:
        """メッセージを送信"""
        headers = {'Content-Type': 'application/json'}
        data = {'content': message}
        
        try:
            response = requests.post(self.webhook_url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            # エンコーディングエラー回避のため、ASCII文字のみでログ出力
            preview = message[:50].encode('ascii', errors='ignore').decode('ascii')
            print(f"OK Discord通知送信成功: {preview}...")
            return True
        except Exception as e:
            print(f"NG Discord通知エラー: {e}")
            return False
    
    def format_state_change_message(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> str:
        """状態変化時のメッセージを生成"""
        emoji_map = {
            'WATCH': '⚠️',
            'BASE': '📊',
            'BUY': '🚀',
            'NORMAL': '📈'
        }
        
        state_names = {
            'WATCH': '急落検知（WATCH入り）',
            'BASE': '低迷継続（BASE入り）',
            'BUY': '反転シグナル（BUY候補）',
            'NORMAL': '通常状態'
        }
        
        emoji = emoji_map.get(new_state, '📌')
        state_name = state_names.get(new_state, new_state)
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if old_state is None:
            msg = f"{emoji} **{symbol} 状態更新: {state_name}**\n"
        else:
            msg = f"{emoji} **{symbol} 状態変化: {old_state} → {new_state}**\n"
            msg += f"**{state_name}**\n"
        
        msg += f"現在価格: ${price:,.2f}\n"
        msg += f"時刻: {timestamp}\n"
        
        # 仮想通貨か米国株かでURLを変更
        from ..signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
        else:
            msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
        
        return msg
    
    def format_daily_pick_message(self, daily_pick: dict) -> str:
        """Daily pickのメッセージを生成（L1/L3データ拡張版）"""
        symbol = daily_pick['symbol']
        category = daily_pick.get('asset_category', 'その他')
        state = daily_pick.get('current_state', 'NORMAL')
        total_score = daily_pick.get('total_score', 0)
        confidence = daily_pick.get('confidence', 'Spec')
        
        value_score = daily_pick.get('value_score', 0)
        momentum_score = daily_pick.get('momentum_score', 0)
        stability_score = daily_pick.get('stability_score', 0)
        
        current_price = daily_pick.get('current_price', 0)
        ath_ratio = daily_pick.get('ath_ratio')
        return_30d = daily_pick.get('return_30d')
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # 信頼度の絵文字
        confidence_emoji = {
            'High': '🟢',
            'Mid': '🟡',
            'Spec': '🟠'
        }
        
        emoji = confidence_emoji.get(confidence, '⚪')
        
        msg = f"{emoji} **【今日の1個】{symbol}**\n"
        
        # ティッカー情報（会社名・セクター）
        ticker_info = daily_pick.get('ticker_info')
        if ticker_info:
            company_name = ticker_info.get('company_name', '')
            if company_name:
                msg += f"**{company_name}**\n"
            sector = ticker_info.get('sector', '')
            if sector and sector != 'Unknown':
                msg += f"セクター: {sector} | "
        
        msg += f"信頼度: **{confidence}** | 状態: **{state}** | カテゴリ: **{category}**\n"
        msg += f"\n**投資スコア: {total_score:.1f}/100点**\n"
        msg += f"  • Value（割安度）: {value_score:.1f}/100\n"
        msg += f"  • Momentum（反転）: {momentum_score:.1f}/100\n"
        msg += f"  • Stability（安定性）: {stability_score:.1f}/100\n"
        
        msg += f"\n**基本情報**\n"
        msg += f"  現在価格: ${current_price:,.2f}\n"
        
        if ath_ratio:
            msg += f"  ATH比: {ath_ratio:.1%} (ATHから{(1-ath_ratio)*100:.1f}%下落)\n"
        
        if return_30d:
            msg += f"  30日リターン: {return_30d:+.1f}%\n"
        
        # L1データ（財務指標）
        fundamental_data = daily_pick.get('fundamental_data')
        if fundamental_data:
            msg += f"\n**📊 財務指標（L1データ）**\n"
            
            fcf = fundamental_data.get('fcf')
            if fcf:
                fcf_billions = fcf / 1_000_000_000
                msg += f"  • FCF: ${fcf_billions:.1f}B\n"
            
            revenue_growth = fundamental_data.get('revenue_growth')
            if revenue_growth is not None:
                msg += f"  • 売上成長率: {revenue_growth:.1%}\n"
            
            profit_margin = fundamental_data.get('profit_margin')
            if profit_margin is not None:
                msg += f"  • 利益率: {profit_margin:.1%}\n"
            
            financial_health_score = fundamental_data.get('financial_health_score')
            if financial_health_score is not None:
                msg += f"  • 財務健全性: {financial_health_score:.0f}/100\n"
            
            # 根拠リンク
            data_sources = fundamental_data.get('data_sources', [])
            if data_sources:
                source = data_sources[0]
                if source.get('url'):
                    msg += f"  • [データソース]({source['url']})\n"
        
        # SEC EDGAR開示
        sec_filings = daily_pick.get('sec_filings', [])
        if sec_filings:
            msg += f"\n**📋 SEC EDGAR開示（公式）**\n"
            for filing in sec_filings[:3]:  # 最大3件
                form = filing.get('form', '')
                filing_date = filing.get('filing_date', '')
                url = filing.get('url', '')
                if url:
                    msg += f"  • [{form} ({filing_date})]({url})\n"
                else:
                    msg += f"  • {form} ({filing_date})\n"
        
        # L3データ（イベント要約）
        events = daily_pick.get('events', [])
        if events:
            positive_events = [e for e in events if e.get('event_type') == 'positive']
            negative_events = [e for e in events if e.get('event_type') == 'negative']
            
            if positive_events or negative_events:
                msg += f"\n**📰 最近のイベント（L3データ）**\n"
                
                if positive_events:
                    msg += f"  ✅ 好材料: {len(positive_events)}件\n"
                    for event in positive_events[:2]:  # 最大2件
                        title = event.get('title', '')[:50]
                        link = event.get('link', '')
                        if link:
                            msg += f"    • [{title}...]({link})\n"
                        else:
                            msg += f"    • {title}...\n"
                
                if negative_events:
                    msg += f"  ⚠️ 悪材料: {len(negative_events)}件\n"
                    for event in negative_events[:2]:  # 最大2件
                        title = event.get('title', '')[:50]
                        link = event.get('link', '')
                        if link:
                            msg += f"    • [{title}...]({link})\n"
                        else:
                            msg += f"    • {title}...\n"
        
        # 使用データレイヤー
        data_layers_used = daily_pick.get('data_layers_used', {})
        if data_layers_used:
            layers = []
            if data_layers_used.get('L0'):
                layers.append("L0:価格")
            if data_layers_used.get('L1'):
                layers.append("L1:財務")
            if data_layers_used.get('L3'):
                layers.append("L3:イベント")
            if layers:
                msg += f"\n**使用データレイヤー**: {', '.join(layers)}\n"
        
        msg += f"\n時刻: {timestamp}\n"
        
        # URL
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
        else:
            msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
        
        # Discordの2000文字制限に対応
        if len(msg) > 1900:  # 安全マージン
            # イベントセクションを削減
            msg = msg[:1500] + "\n\n... (メッセージが長いため一部省略) ..."
        
        return msg
    
    def notify_state_change(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> bool:
        """状態変化を通知"""
        message = self.format_state_change_message(symbol, old_state, new_state, price)
        return self.send(message)
    
    def notify_daily_pick(self, daily_pick: dict) -> bool:
        """Daily pickを通知"""
        message = self.format_daily_pick_message(daily_pick)
        return self.send(message)
