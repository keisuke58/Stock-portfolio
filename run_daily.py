"""
1日1回実行するメインスクリプト
「今日の1個」を選出してDiscordに通知
"""
import sys
import os

# パスを追加（相対インポート対応）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.daily_runner import DailyRunner


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python run_daily.py <config.json> [max_assets]")
        print("  max_assets: 分析する最大資産数（デフォルト: 200）")
        sys.exit(1)
    
    config_path = sys.argv[1]
    max_assets = 200
    
    if len(sys.argv) > 2:
        try:
            max_assets = int(sys.argv[2])
        except ValueError:
            print(f"警告: 無効なmax_assets値 '{sys.argv[2]}'。デフォルト値200を使用します。")
    
    try:
        runner = DailyRunner(config_path)
        runner.run(max_assets=max_assets)
    except KeyboardInterrupt:
        print("\n\n中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
