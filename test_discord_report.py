"""
Discordレポート送信テスト
新機能（L1/L3データ）を含むレポートをDiscordに送信
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.daily_runner import DailyRunner
from notifiers import DiscordNotifier


def test_discord_report():
    """Discordレポート送信テスト"""
    print("=" * 80)
    print("Discordレポート送信テスト")
    print("=" * 80)
    
    # 設定ファイル読み込み
    config_path = "config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
        return
    
    webhook_url = config.get('webhook')
    if not webhook_url:
        print("エラー: Discord Webhook URLが設定されていません")
        print("config.jsonに'webhook'を設定してください")
        return
    
    # DailyRunnerで分析
    print("\n1. シンボル分析中...")
    runner = DailyRunner(config_path)
    
    # テスト用シンボル（AAPL）
    test_symbol = "AAPL"
    print(f"   シンボル: {test_symbol}")
    
    result = runner.analyze_symbol(test_symbol)
    
    if not result:
        print("   エラー: 分析に失敗しました")
        return
    
    print(f"   分析完了: スコア {result['total_score']:.1f}/100")
    
    # Discord通知を送信
    print("\n2. Discordレポート送信中...")
    notifier = DiscordNotifier(webhook_url)
    
    # 信頼度を設定（テスト用）
    result['confidence'] = 'High'
    
    success = notifier.notify_daily_pick(result)
    
    if success:
        print("   [OK] Discordレポート送信成功")
        print("\n   送信内容のプレビュー:")
        message = notifier.format_daily_pick_message(result)
        # 最初の500文字を表示（エンコーディングエラー回避）
        preview = message[:500] + "..." if len(message) > 500 else message
        try:
            print("   " + "\n   ".join(preview.split("\n")[:20]))
        except UnicodeEncodeError:
            # Windowsコンソールのエンコーディング問題を回避
            preview_ascii = preview.encode('ascii', errors='ignore').decode('ascii')
            print("   " + "\n   ".join(preview_ascii.split("\n")[:20]))
    else:
        print("   [ERROR] Discordレポート送信失敗")
    
    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    test_discord_report()
