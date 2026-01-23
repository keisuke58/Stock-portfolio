"""
急落→低迷→反転検知Bot（メインロジック）
状態遷移時のみDiscord/Lineに通知
"""
import json
import sys
import time
import requests
from datetime import datetime
from config.config_loader import load_all_config
from state_store import StateStore
from signals import determine_state, is_crypto_symbol
from fetchers import YahooFetcher, CoinGeckoFetcher
from notifiers import DiscordNotifier, LineNotifier, SlackNotifier, GmailNotifier


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
    if is_crypto_symbol(symbol):
        msg += f"`https://www.coingecko.com/en/coins/{symbol.lower()}`"
    else:
        msg += f"`https://finance.yahoo.com/quote/{symbol.upper()}`"
    
    return msg


def main():
    """メイン処理"""
    # 設定ファイル読み込み
    config_path = None
    if len(sys.argv) >= 2:
        config_path = sys.argv[1]
    
    try:
        # config/config_loader.py経由で設定を読み込む
        config = load_all_config(legacy_config_path=config_path)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
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
        print("エラー: webhook URL または line_token が設定されていません")
        sys.exit(1)
    
    # 状態管理の初期化
    state_store = StateStore()
    
    print(f"=== 急落→低迷→反転検知Bot 起動 ===")
    print(f"監視対象: {', '.join(symbols)}")
    print(f"チェック間隔: {check_interval}秒 ({check_interval/3600:.1f}時間)")
    if webhook_url:
        print(f"Discord Webhook: 設定済み")
    if line_token:
        print(f"Line Notify: 設定済み")
    print("=" * 50)
    
    # メインループ
    while True:
        try:
            for symbol in symbols:
                print(f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {symbol} をチェック中...")
                
                # 現在価格を取得
                current_price = get_current_price(symbol)
                if current_price is None:
                    print(f"  [X] 価格取得失敗")
                    continue
                
                print(f"  現在価格: ${current_price:,.2f}")
                
                # 現在の状態を取得
                old_state = state_store.get_state(symbol)
                print(f"  現在の状態: {old_state or 'NORMAL（未登録）'}")
                
                # 新しい状態を判定
                new_state = determine_state(symbol, old_state)
                print(f"  判定結果: {new_state}")
                
                # 状態を更新（変化があったかどうか）
                state_changed = state_store.set_state(symbol, new_state, current_price)
                
                if state_changed:
                    print(f"  [OK] 状態変化検出: {old_state or 'NONE'} -> {new_state}")
                    
                    # 通知すべきかチェック
                    if state_store.should_notify(symbol, new_state):
                        # すべての通知先に送信
                        for notifier in notifiers:
                            notifier.notify_state_change(symbol, old_state, new_state, current_price)
                        state_store.mark_notified(symbol, new_state)
                    else:
                        print(f"  - 既に通知済みのためスキップ")
                else:
                    print(f"  - 状態変化なし（通知なし）")
            
            # 次のチェックまで待機
            print(f"\n次回チェックまで {check_interval}秒 待機中...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n\nBotを停止します...")
            break
        except Exception as e:
            print(f"\nエラー発生: {e}")
            import traceback
            traceback.print_exc()
            print(f"{check_interval}秒後に再試行します...")
            time.sleep(check_interval)


if __name__ == '__main__':
    main()
