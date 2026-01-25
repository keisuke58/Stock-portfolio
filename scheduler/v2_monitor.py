"""
V2 Signal Monitor: Deep Bottom V2シグナルのリアルタイム監視

V2スコアリング（出来高確認とシンクボーナス付き）を使用して
Deep Bottomシグナルをスキャンし、Discord通知を送信する。
"""
import json
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_loader import load_all_config
from cache import PriceCache
from fetchers import YahooFetcher, CoinGeckoFetcher
from features import FeatureCalculator
from signals import is_crypto_symbol
from notifiers import DiscordNotifier

logger = logging.getLogger(__name__)


class V2SignalMonitor:
    """
    V2 Deep Bottomシグナルのリアルタイム監視クラス

    Features:
    - V2スコアリング（出来高確認、シンクボーナス）を使用
    - 信頼度閾値によるフィルタリング
    - 24時間クールダウン付きDiscord通知
    - デイリーサマリー生成
    """

    def __init__(
        self,
        confidence_threshold: int = 70,
        volume_filter: bool = True,
        config_path: str = None
    ):
        """
        初期化

        Args:
            confidence_threshold: 最小信頼度閾値（デフォルト70）
            volume_filter: 出来高確認フィルターを有効にするか
            config_path: 設定ファイルのパス
        """
        self.confidence_threshold = confidence_threshold
        self.volume_filter = volume_filter

        # 設定読み込み
        self.config = load_all_config(legacy_config_path=config_path)

        # V2監視設定を読み込み
        v2_config = self.config.get('v2_monitoring', {})
        if v2_config.get('confidence_threshold'):
            self.confidence_threshold = v2_config['confidence_threshold']

        # コンポーネント初期化
        self.cache = PriceCache()
        self.yahoo_fetcher = YahooFetcher(self.cache)
        self.coingecko_fetcher = CoinGeckoFetcher(self.cache)

        # Discord通知
        self.notifier = None
        webhook_url = self.config.get('webhook')
        if webhook_url:
            self.notifier = DiscordNotifier(webhook_url)

        # 高信頼度用のWebhook（オプション）
        self.high_confidence_notifier = None
        high_conf_webhook = self.config.get('webhook_high_confidence')
        if high_conf_webhook:
            self.high_confidence_notifier = DiscordNotifier(high_conf_webhook)

        # 監視対象シンボル
        self.symbols = self.config.get('symbols', [])

        # 検出されたシグナルの履歴（デイリーサマリー用）
        self.detected_signals: List[Dict] = []
        self.last_scan_date: Optional[str] = None

    def scan_symbol_v2(self, symbol: str) -> Optional[Dict]:
        """
        単一シンボルのV2スキャン

        Args:
            symbol: スキャン対象のシンボル

        Returns:
            V2シグナルデータ辞書、またはシグナルなしの場合None
        """
        try:
            # 価格データ取得
            if is_crypto_symbol(symbol):
                prices = self.coingecko_fetcher.get_historical_prices(symbol, days=365)
                prices_with_volume = self.coingecko_fetcher.get_historical_prices_with_volume(
                    symbol, days=365
                )
                current_price = self.coingecko_fetcher.get_current_price(symbol)
            else:
                prices = self.yahoo_fetcher.get_historical_prices(symbol, days=365)
                prices_with_volume = self.yahoo_fetcher.get_historical_prices_with_volume(
                    symbol, days=365
                )
                current_price = self.yahoo_fetcher.get_current_price(symbol)

            if not prices or len(prices) < 100:
                logger.debug(f"{symbol}: 価格データ不足")
                return None

            # V2スコア計算
            v2_result = FeatureCalculator.calculate_deep_bottom_score_v2(
                prices, prices_with_volume
            )

            if not v2_result:
                return None

            total_score = v2_result.get('total_score', 0)
            signal_strength = v2_result.get('signal_strength')
            confidence = v2_result.get('confidence', 0)
            volume_confirmed = v2_result.get('volume_confirmed', False)

            # 信頼度チェック
            if confidence < self.confidence_threshold:
                return None

            # シグナル強度チェック
            if signal_strength is None:
                return None

            # 出来高フィルター
            if self.volume_filter and not volume_confirmed:
                return None

            # 追加指標計算
            drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices) or 0
            rsi = FeatureCalculator.calculate_rsi(prices, 14) or 50

            # シグナルデータ構築
            signal_data = {
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat(),
                'total_score': total_score,
                'signal_strength': signal_strength,
                'confidence': confidence,
                'volume_confirmed': volume_confirmed,
                'component_scores': v2_result.get('component_scores', {}),
                'risk_factors': [],
                'current_price': current_price,
                'drawdown_pct': drawdown,
                'rsi': rsi,
                'volume_climax_ratio': v2_result.get('volume_climax_ratio', 1.0)
            }

            # リスク要因抽出
            risk_info = v2_result.get('risk', {})
            if risk_info:
                if risk_info.get('recent_spike', 0) > 0:
                    signal_data['risk_factors'].append('recent_spike')
                if risk_info.get('high_volatility', 0) > 0:
                    signal_data['risk_factors'].append('high_volatility')
                if risk_info.get('thin_volume', 0) > 0:
                    signal_data['risk_factors'].append('thin_volume')

            logger.info(
                f"V2 Signal detected: {symbol} - "
                f"confidence={confidence}%, strength={signal_strength}, "
                f"volume_confirmed={volume_confirmed}"
            )

            return signal_data

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None

    def run_scan(
        self,
        symbols: List[str] = None,
        batch_size: int = 10
    ) -> List[Dict]:
        """
        複数シンボルのV2スキャン実行

        Args:
            symbols: スキャン対象シンボルリスト（Noneの場合は設定から取得）
            batch_size: バッチサイズ（レート制限対策）

        Returns:
            検出されたV2シグナルのリスト
        """
        if symbols is None:
            symbols = self.symbols

        if not symbols:
            logger.warning("No symbols to scan")
            return []

        logger.info(f"Starting V2 scan for {len(symbols)} symbols")

        detected = []
        scanned = 0

        for i, symbol in enumerate(symbols, 1):
            try:
                signal = self.scan_symbol_v2(symbol)
                if signal:
                    detected.append(signal)
                scanned += 1

                # レート制限対策
                if i % batch_size == 0:
                    logger.debug(f"Scanned {i}/{len(symbols)}, sleeping...")
                    time.sleep(2)
                else:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue

        logger.info(
            f"V2 scan complete: {len(detected)} signals detected "
            f"from {scanned} symbols scanned"
        )

        # デイリーサマリー用に保存
        today = datetime.utcnow().strftime('%Y-%m-%d')
        if self.last_scan_date != today:
            self.detected_signals = []
            self.last_scan_date = today

        self.detected_signals.extend(detected)

        return detected

    def notify_signals(self, signals: List[Dict]) -> int:
        """
        検出されたシグナルをDiscordに通知

        Args:
            signals: 通知するシグナルのリスト

        Returns:
            通知成功数
        """
        if not self.notifier:
            logger.warning("No notifier configured")
            return 0

        notified = 0

        for signal in signals:
            try:
                symbol = signal.get('symbol')
                confidence = signal.get('confidence', 0)

                # 高信頼度は専用チャンネルにも通知
                if confidence >= 75 and self.high_confidence_notifier:
                    self.high_confidence_notifier.notify_deep_bottom_v2(symbol, signal)

                # 通常チャンネルに通知
                success = self.notifier.notify_deep_bottom_v2(symbol, signal)
                if success:
                    notified += 1

            except Exception as e:
                logger.error(f"Error notifying signal for {signal.get('symbol')}: {e}")
                continue

        logger.info(f"Notified {notified}/{len(signals)} signals")
        return notified

    def send_daily_summary(self) -> bool:
        """
        デイリーサマリーをDiscordに送信

        Returns:
            成功した場合はTrue
        """
        if not self.notifier:
            logger.warning("No notifier configured")
            return False

        if not self.detected_signals:
            logger.info("No signals to summarize")
            return False

        today = datetime.utcnow().strftime('%Y-%m-%d')
        total_scanned = len(self.symbols)

        try:
            success = self.notifier.notify_v2_daily_summary(
                today,
                self.detected_signals,
                total_scanned
            )
            return success
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False

    def run(self, max_symbols: int = 200, send_summary: bool = True):
        """
        V2監視のメイン実行ループ

        Args:
            max_symbols: 最大スキャン数
            send_summary: デイリーサマリーを送信するか
        """
        print("=" * 80)
        print("V2 Signal Monitor: Deep Bottom V2 Scan")
        print("=" * 80)
        print(f"Confidence Threshold: {self.confidence_threshold}%")
        print(f"Volume Filter: {self.volume_filter}")
        print(f"Symbols to scan: {min(len(self.symbols), max_symbols)}")
        print(f"Start time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 80)
        print()

        # スキャン実行
        symbols_to_scan = self.symbols[:max_symbols]
        signals = self.run_scan(symbols_to_scan)

        # 通知
        if signals:
            notified = self.notify_signals(signals)
            print(f"\nNotified {notified} signals")

        # デイリーサマリー
        if send_summary:
            self.send_daily_summary()

        print()
        print("=" * 80)
        print("V2 Signal Monitor Complete")
        print(f"Signals detected: {len(signals)}")
        print("=" * 80)

        return signals


def run_v2_monitor():
    """V2モニターを実行するエントリーポイント"""
    # 設定から監視設定を読み込み
    config = load_all_config()
    v2_config = config.get('v2_monitoring', {})

    if not v2_config.get('enabled', True):
        print("V2 monitoring is disabled in config")
        return

    confidence_threshold = v2_config.get('confidence_threshold', 70)
    daily_summary_enabled = v2_config.get('daily_summary_enabled', True)

    monitor = V2SignalMonitor(
        confidence_threshold=confidence_threshold,
        volume_filter=True
    )

    monitor.run(
        max_symbols=200,
        send_summary=daily_summary_enabled
    )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_v2_monitor()
