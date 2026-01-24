"""
急落→低迷→反転検知Bot（メインロジック）
状態遷移時のみDiscord/Lineに通知
長期投資向けDEEP_BOTTOM検出も対応
"""
import json
import logging
import sys
import time
import requests
from datetime import datetime
from config.config_loader import load_all_config
from core.logging_config import setup_logging, get_logger
from state_store import StateStore
from signals import determine_state, is_crypto_symbol
from signals.state_machine import StateMachine
from fetchers import YahooFetcher, CoinGeckoFetcher
from notifiers import DiscordNotifier, LineNotifier, SlackNotifier, GmailNotifier

logger = get_logger(__name__)


def get_current_price(symbol: str) -> float:
    """現在の価格を取得（仮想通貨または米国株を自動判定）"""
    if is_crypto_symbol(symbol):
        fetcher = CoinGeckoFetcher()
    else:
        fetcher = YahooFetcher()
    return fetcher.get_current_price(symbol)


def generate_state_change_message(symbol: str, old_state: str, new_state: str, price: float) -> str:
    """状態変化時のメッセージを生成"""
    emoji_map = {
        'WATCH': '⚠️',
        'BASE': '📊',
        'BUY': '🚀',
        'NORMAL': '📈',
        'DEEP_BOTTOM': '💎'
    }

    state_names = {
        'WATCH': '急落検知（WATCH入り）',
        'BASE': '低迷継続（BASE入り）',
        'BUY': '反転シグナル（BUY候補）',
        'NORMAL': '通常状態',
        'DEEP_BOTTOM': '長期投資機会（歴史的割安）'
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
    if is_crypto_symbol(symbol):
        msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
    else:
        msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
    
    return msg


def main():
    """メイン処理"""
    # ロギング設定
    setup_logging(level=logging.INFO)

    # 設定ファイル読み込み
    config_path = None
    if len(sys.argv) >= 2:
        config_path = sys.argv[1]

    try:
        # config/config_loader.py経由で設定を読み込む
        config = load_all_config(legacy_config_path=config_path)
    except Exception as e:
        logger.error(f"Config file loading error: {e}")
        sys.exit(1)

    # 設定値取得
    webhook_url = config.get('webhook')
    line_token = config.get('line_token')
    symbols = config.get('symbols', ['BTC'])  # デフォルトはBTC
    check_interval = config.get('check_interval', 3600)  # デフォルト1時間（秒）

    # 通知設定（DiscordとLineの両方に対応）
    notifiers = []
    if webhook_url:
        notifiers.append(DiscordNotifier(webhook_url))
    if line_token:
        notifiers.append(LineNotifier(line_token))

    if not notifiers:
        logger.error("No notifier configured: webhook URL or line_token required")
        sys.exit(1)

    # 状態管理の初期化
    state_store = StateStore()

    # Deep Bottom検出用のStateMachine
    state_machine = StateMachine()

    # Deep Bottom通知済みシンボルを追跡
    deep_bottom_notified = set()

    logger.info("=== Price Movement Detection Bot Started ===")
    logger.info(f"Monitoring symbols: {', '.join(symbols)}")
    logger.info(f"Check interval: {check_interval}s ({check_interval/3600:.1f}h)")
    if webhook_url:
        logger.info("Discord Webhook: configured")
    if line_token:
        logger.info("Line Notify: configured")

    # メインループ
    while True:
        try:
            for symbol in symbols:
                logger.debug(f"Checking {symbol}...")

                # 現在価格を取得
                current_price = get_current_price(symbol)
                if current_price is None:
                    logger.warning(f"Failed to fetch price for {symbol}")
                    continue

                logger.debug(f"{symbol} current price: ${current_price:,.2f}")

                # 現在の状態を取得
                old_state = state_store.get_state(symbol)

                # 新しい状態を判定
                new_state = determine_state(symbol, old_state)

                # 状態を更新（変化があったかどうか）
                state_changed = state_store.set_state(symbol, new_state, current_price)

                if state_changed:
                    logger.info(
                        f"State change detected for {symbol}: "
                        f"{old_state or 'NONE'} -> {new_state}"
                    )

                    # 通知すべきかチェック
                    if state_store.should_notify(symbol, new_state):
                        # すべての通知先に送信
                        for notifier in notifiers:
                            notifier.notify_state_change(symbol, old_state, new_state, current_price)
                        state_store.mark_notified(symbol, new_state)
                    else:
                        logger.debug(f"{symbol}: Already notified, skipping")
                else:
                    logger.debug(f"{symbol}: No state change")

                # Deep Bottom検出（長期投資向け、独立したチェック）
                deep_bottom_detected, metrics = state_machine.check_deep_bottom(symbol)

                if deep_bottom_detected:
                    if symbol not in deep_bottom_notified:
                        logger.info(
                            f"DEEP_BOTTOM detected for {symbol}: "
                            f"drawdown={metrics.get('drawdown_pct', 0):.1f}%, "
                            f"RSI={metrics.get('rsi_14', 0):.1f}"
                        )

                        # Discord通知（DiscordNotifierのみ対応）
                        for notifier in notifiers:
                            if isinstance(notifier, DiscordNotifier):
                                notifier.notify_deep_bottom(symbol, metrics)

                        deep_bottom_notified.add(symbol)
                    else:
                        logger.debug(f"{symbol}: DEEP_BOTTOM already notified")
                else:
                    # Deep Bottom条件を満たさなくなったら通知済みリストから削除
                    if symbol in deep_bottom_notified:
                        deep_bottom_notified.discard(symbol)
                        logger.info(f"{symbol}: DEEP_BOTTOM condition no longer met")

            # 次のチェックまで待機
            logger.debug(f"Waiting {check_interval}s until next check...")
            time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Bot shutdown requested")
            break
        except Exception as e:
            logger.exception(f"Error occurred: {e}")
            logger.info(f"Retrying in {check_interval}s...")
            time.sleep(check_interval)


if __name__ == '__main__':
    main()
