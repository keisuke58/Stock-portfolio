"""
投資推奨レポート生成スクリプト
全資産クラスを横断比較して「今から買う価値が高いもの」を10個厳選
"""
import json
import sys
from investment_analyzer import InvestmentAnalyzer


def main():
    """メイン処理"""
    # 設定ファイル読み込み
    if len(sys.argv) < 2:
        print("Usage: python generate_investment_report.py <config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
        sys.exit(1)
    
    # シンボルリストを取得
    symbols = config.get('symbols', [])
    
    if not symbols:
        print("エラー: シンボルリストが空です")
        sys.exit(1)
    
    print("=" * 80)
    print("投資リサーチAI: 全資産クラス横断比較分析")
    print("=" * 80)
    print(f"設定ファイル内の資産数: {len(symbols)}")
    
    # 分析する最大資産数を設定（タイムアウト対策）
    # コマンドライン引数で指定可能
    max_assets = None
    if len(sys.argv) > 2:
        try:
            max_assets = int(sys.argv[2])
        except ValueError:
            pass
    
    # デフォルトは200資産まで（主要資産を優先）
    if max_assets is None:
        max_assets = 200
    
    print(f"実際に分析する資産数: 最大{max_assets}（主要資産優先）")
    print("分析を開始します...\n")
    
    # 投資分析を実行
    analyzer = InvestmentAnalyzer()
    
    # まず分析を実行して結果を取得
    results = analyzer.analyze_all_assets(symbols, max_assets=max_assets)
    top_results = results[:10]
    
    # 簡易レポートを生成（状態フラグ付き）
    report = analyzer.generate_simple_report(symbols, top_n=10, max_assets=max_assets)
    
    # ファイルに保存（UTF-8）
    output_file = "investment_report.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nレポートを {output_file} に保存しました。")
        print(f"詳細は {output_file} をご確認ください。")
        
        # コンソールには簡易版を表示（エンコーディングエラー回避）
        print("\n" + "=" * 80)
        print("投資推奨レポート（Top 10 サマリー）")
        print("=" * 80)
        print(f"{'Rank':<6} {'資産名':<8} {'状態':<8} {'Score':<8} {'Value':<8} {'Momentum':<10} {'Stability':<10} {'スタンス':<12}")
        print("-" * 80)
        for rank, data in enumerate(top_results, 1):
            state = data.get('current_state', 'NORMAL')
            score = data['investment_score']
            value_score = data.get('value_score', 0)
            momentum_score = data.get('momentum_score', 0)
            stability_score = data.get('stability_score', 0)
            stance = data['investment_stance']
            print(f"{rank:<6} {data['symbol']:<8} {state:<8} {score:<8.0f} {value_score:<8.0f} {momentum_score:<10.0f} {stability_score:<10.0f} {stance:<12}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nレポート保存エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
