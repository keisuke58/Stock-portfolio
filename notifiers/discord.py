"""
Discord通知モジュール
状態変化 or Daily pick を通知
スコア閾値・異常検知・レジーム変化通知対応
"""
import logging
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.weight_optimizer import MarketRegime, WeightOptimizer
from core.retry import retry_with_backoff
from core.circuit_breaker import get_discord_circuit, CircuitOpenError

logger = logging.getLogger(__name__)


class NotificationThrottler:
    """通知抑制ロジック（クールダウン）"""
    
    def __init__(self, cooldown_hours: int = 24):
        """
        初期化
        
        Args:
            cooldown_hours: クールダウン時間（時間、デフォルト: 24時間）
        """
        self.cooldown_hours = cooldown_hours
        self.last_notified = {}  # {(symbol, notification_type): datetime}
    
    def should_notify(self, symbol: str, notification_type: str) -> bool:
        """
        通知すべきか判定
        
        Args:
            symbol: シンボル名
            notification_type: 通知タイプ（'score_threshold', 'anomaly', 'regime_change', 'state_change'）
        
        Returns:
            True=通知すべき、False=抑制
        """
        # 異常検知は常に通知（例外）
        if notification_type == 'anomaly':
            return True
        
        key = (symbol, notification_type)
        last_time = self.last_notified.get(key)
        
        if last_time is None:
            return True
        
        # クールダウン時間をチェック
        time_since_last = datetime.utcnow() - last_time
        if time_since_last >= timedelta(hours=self.cooldown_hours):
            return True
        
        return False
    
    def mark_notified(self, symbol: str, notification_type: str):
        """
        通知済みを記録
        
        Args:
            symbol: シンボル名
            notification_type: 通知タイプ
        """
        key = (symbol, notification_type)
        self.last_notified[key] = datetime.utcnow()


class DiscordNotifier:
    """Discord Webhookに通知を送信するクラス"""
    
    def __init__(self, webhook_url: str, cooldown_hours: int = 24):
        """
        初期化
        
        Args:
            webhook_url: Discord Webhook URL
            cooldown_hours: クールダウン時間（時間、デフォルト: 24時間）
        """
        self.webhook_url = webhook_url
        self.throttler = NotificationThrottler(cooldown_hours=cooldown_hours)
    
    def send(self, message: str) -> bool:
        """メッセージを送信（リトライ・サーキットブレーカー対応）"""
        circuit = get_discord_circuit()

        try:
            return circuit.call(self._send_with_retry, message)
        except CircuitOpenError as e:
            logger.warning(f"Discord circuit open, skipping notification: {e}")
            return False
        except requests.RequestException as e:
            logger.error(f"Discord notification failed after retries: {e}")
            return False

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(requests.RequestException,)
    )
    def _send_with_retry(self, message: str) -> bool:
        """リトライ付きメッセージ送信"""
        headers = {'Content-Type': 'application/json'}
        data = {'content': message}

        response = requests.post(self.webhook_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()

        # エンコーディングエラー回避のため、ASCII文字のみでログ出力
        preview = message[:50].encode('ascii', errors='ignore').decode('ascii')
        logger.info(f"Discord notification sent: {preview}...")
        return True
    
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
    
    def format_score_threshold_message(
        self,
        symbol: str,
        score: float,
        threshold: float,
        direction: str = 'above'
    ) -> str:
        """
        スコア閾値通知メッセージを生成
        
        Args:
            symbol: シンボル名
            score: 現在のスコア
            threshold: 閾値
            direction: 'above'（上回った）または 'below'（下回った）
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if direction == 'above':
            emoji = '📈'
            msg = f"{emoji} **スコア閾値到達: {symbol}**\n"
            msg += f"スコア: **{score:.1f}点**（閾値: {threshold:.1f}点を上回りました）\n"
        else:
            emoji = '📉'
            msg = f"{emoji} **スコア閾値下落: {symbol}**\n"
            msg += f"スコア: **{score:.1f}点**（閾値: {threshold:.1f}点を下回りました）\n"
        
        msg += f"時刻: {timestamp}\n"
        
        # URL
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
        else:
            msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
        
        return msg
    
    def format_anomaly_message(
        self,
        symbol: str,
        anomaly_type: str,
        details: Dict
    ) -> str:
        """
        異常検知通知メッセージを生成
        
        Args:
            symbol: シンボル名
            anomaly_type: 異常タイプ（'price_spike', 'volume_surge', 'volatility_spike'）
            details: 詳細情報
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        emoji = '🚨'
        msg = f"{emoji} **異常検知: {symbol}**\n"
        
        if anomaly_type == 'price_spike':
            old_price = details.get('old_price')
            new_price = details.get('new_price')
            change_pct = details.get('change_pct')
            time_window = details.get('time_window', '1時間')
            
            msg += f"**価格急変**\n"
            msg += f"価格: ${old_price:,.2f} → ${new_price:,.2f} ({change_pct:+.1f}%)\n"
            msg += f"時間窓: {time_window}\n"
        
        elif anomaly_type == 'volume_surge':
            current_volume = details.get('current_volume')
            avg_volume = details.get('avg_volume')
            volume_ratio = details.get('volume_ratio')
            
            msg += f"**出来高急増**\n"
            msg += f"現在出来高: {current_volume:,.0f}\n"
            msg += f"平均出来高: {avg_volume:,.0f}\n"
            msg += f"比率: {volume_ratio:.0f}%\n"
        
        elif anomaly_type == 'volatility_spike':
            current_vol = details.get('current_volatility')
            avg_vol = details.get('avg_volatility')
            vol_ratio = details.get('volatility_ratio')
            
            msg += f"**ボラティリティ急上昇**\n"
            msg += f"現在ボラ: {current_vol:.1f}%\n"
            msg += f"平均ボラ: {avg_vol:.1f}%\n"
            msg += f"比率: {vol_ratio:.0f}%\n"
        
        msg += f"時刻: {timestamp}\n"
        
        # URL
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
        else:
            msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
        
        return msg
    
    def format_regime_change_message(
        self,
        old_regime: str,
        new_regime: str,
        affected_symbols: List[str] = None
    ) -> str:
        """
        レジーム変化通知メッセージを生成
        
        Args:
            old_regime: 以前のレジーム
            new_regime: 新しいレジーム
            affected_symbols: 影響を受けた銘柄のリスト
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        emoji = '📊'
        msg = f"{emoji} **レジーム変化**\n"
        msg += f"市場レジーム: **{old_regime}** → **{new_regime}**\n"
        
        regime_names = {
            'HIGH_VOLATILITY': '高ボラ',
            'LOW_VOLATILITY': '低ボラ',
            'NORMAL': '通常'
        }
        
        old_name = regime_names.get(old_regime, old_regime)
        new_name = regime_names.get(new_regime, new_regime)
        msg += f"**{old_name}** → **{new_name}**\n"
        
        if affected_symbols:
            msg += f"影響銘柄: {', '.join(affected_symbols[:10])}\n"
            if len(affected_symbols) > 10:
                msg += f"（他 {len(affected_symbols) - 10} 銘柄）\n"
        
        msg += f"時刻: {timestamp}\n"
        
        return msg
    
    def notify_score_threshold(
        self,
        symbol: str,
        score: float,
        threshold: float,
        direction: str = 'above'
    ) -> bool:
        """
        スコア閾値通知
        
        Args:
            symbol: シンボル名
            score: 現在のスコア
            threshold: 閾値
            direction: 'above'（上回った）または 'below'（下回った）
        """
        # 抑制ロジックチェック
        if not self.throttler.should_notify(symbol, 'score_threshold'):
            return False
        
        message = self.format_score_threshold_message(symbol, score, threshold, direction)
        success = self.send(message)
        
        if success:
            self.throttler.mark_notified(symbol, 'score_threshold')
        
        return success
    
    def notify_anomaly(
        self,
        symbol: str,
        anomaly_type: str,
        details: Dict
    ) -> bool:
        """
        異常検知通知
        
        Args:
            symbol: シンボル名
            anomaly_type: 異常タイプ
            details: 詳細情報
        """
        # 異常検知は常に通知（抑制なし）
        message = self.format_anomaly_message(symbol, anomaly_type, details)
        return self.send(message)
    
    def notify_regime_change(
        self,
        old_regime: str,
        new_regime: str,
        affected_symbols: List[str] = None
    ) -> bool:
        """
        レジーム変化通知
        
        Args:
            old_regime: 以前のレジーム
            new_regime: 新しいレジーム
            affected_symbols: 影響を受けた銘柄のリスト
        """
        # レジーム変化は抑制なし（市場全体の変化なので）
        message = self.format_regime_change_message(old_regime, new_regime, affected_symbols)
        return self.send(message)
