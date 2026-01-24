"""
新機能のテストスクリプト
ティッカー解決、SEC EDGAR統合、イベント分類をテスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest import TickerResolver, SECEdgarIngester, FundamentalIngester, NewsIngester
from knowledge import EventClassifier


def test_ticker_resolver():
    """ティッカー解決のテスト"""
    print("=" * 80)
    print("【テスト1】ティッカー解決")
    print("=" * 80)
    
    resolver = TickerResolver()
    
    # テストケース
    test_symbols = ["A", "AAPL", "MSFT"]
    
    for symbol in test_symbols:
        print(f"\nシンボル: {symbol}")
        try:
            result = resolver.resolve_ticker(symbol)
            print(f"  会社名: {result.get('company_name', 'N/A')}")
            print(f"  セクター: {result.get('sector', 'N/A')}")
            print(f"  CIK: {result.get('cik', 'N/A')}")
            if result.get('error'):
                print(f"  エラー: {result['error']}")
        except Exception as e:
            print(f"  エラー: {e}")
    
    print("\n[OK] ティッカー解決テスト完了")


def test_sec_edgar():
    """SEC EDGAR統合のテスト"""
    print("\n" + "=" * 80)
    print("【テスト2】SEC EDGAR統合")
    print("=" * 80)
    
    edgar = SECEdgarIngester()
    
    # テスト用CIK（Apple Inc.）
    test_cik = "0000320193"
    
    print(f"\nCIK: {test_cik} (Apple Inc.)")
    
    try:
        # 最近の決算リリースを取得
        print("\n1. 最近の決算リリース（8-K）を取得中...")
        filings = edgar.get_recent_earnings_releases(test_cik, days=90)
        print(f"   取得件数: {len(filings)}件")
        for i, filing in enumerate(filings[:3], 1):
            print(f"   {i}. {filing.get('form')} ({filing.get('filing_date')})")
            if filing.get('url'):
                print(f"      URL: {filing['url'][:80]}...")
        
        # ガイダンス更新を取得
        print("\n2. ガイダンス更新を取得中...")
        guidance = edgar.get_guidance_updates(test_cik)
        print(f"   取得件数: {len(guidance)}件")
        for i, update in enumerate(guidance[:3], 1):
            print(f"   {i}. {update.get('form')} ({update.get('filing_date')})")
        
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[OK] SEC EDGAR統合テスト完了")


def test_event_classifier():
    """イベント分類のテスト"""
    print("\n" + "=" * 80)
    print("【テスト3】イベント分類")
    print("=" * 80)
    
    classifier = EventClassifier()
    
    # テスト用ニュース
    test_news = [
        {
            'title': 'Apple beats earnings expectations with strong iPhone sales',
            'link': 'https://example.com/news1',
            'published_time': '2026-01-20T10:00:00'
        },
        {
            'title': 'Company faces regulatory investigation',
            'link': 'https://example.com/news2',
            'published_time': '2026-01-19T15:00:00'
        },
        {
            'title': 'Quarterly financial report released',
            'link': 'https://example.com/news3',
            'published_time': '2026-01-18T09:00:00'
        }
    ]
    
    print("\n1. ニュース分類テスト...")
    try:
        events = classifier.classify_news(test_news)
        print(f"   分類件数: {len(events)}件")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event.get('title', 'N/A')[:50]}...")
            print(f"      タイプ: {event.get('event_type')}, 影響: {event.get('impact')}")
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # SEC EDGAR開示分類テスト
    print("\n2. SEC EDGAR開示分類テスト...")
    test_filings = [
        {
            'form': '8-K',
            'filing_date': '2026-01-15',
            'description': 'Acquisition of new technology company',
            'url': 'https://www.sec.gov/...'
        },
        {
            'form': '10-K',
            'filing_date': '2025-12-31',
            'description': 'Annual report',
            'url': 'https://www.sec.gov/...'
        }
    ]
    
    try:
        sec_events = classifier.classify_sec_filings(test_filings)
        print(f"   分類件数: {len(sec_events)}件")
        for i, event in enumerate(sec_events, 1):
            print(f"   {i}. {event.get('title')}")
            print(f"      タイプ: {event.get('event_type')}, 影響: {event.get('impact')}")
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[OK] イベント分類テスト完了")


def test_fundamental_ingester():
    """財務データ取得のテスト"""
    print("\n" + "=" * 80)
    print("【テスト4】財務データ取得（L1）")
    print("=" * 80)
    
    ingester = FundamentalIngester()
    test_symbol = "AAPL"
    
    print(f"\nシンボル: {test_symbol}")
    
    try:
        # 財務データ取得
        print("\n1. 財務データ取得中...")
        fundamental = ingester.get_fundamental_data(test_symbol)
        if fundamental.get('error'):
            print(f"   エラー: {fundamental['error']}")
        else:
            print(f"   FCF: ${fundamental.get('fcf', 0):,.0f}" if fundamental.get('fcf') else "   FCF: N/A")
            print(f"   売上成長率: {fundamental.get('revenue_growth', 0):.1%}" if fundamental.get('revenue_growth') is not None else "   売上成長率: N/A")
            print(f"   利益率: {fundamental.get('profit_margin', 0):.1%}" if fundamental.get('profit_margin') is not None else "   利益率: N/A")
            print(f"   財務健全性スコア: {fundamental.get('financial_health_score', 0):.1f}/100" if fundamental.get('financial_health_score') is not None else "   財務健全性スコア: N/A")
        
        # アナリストデータ取得
        print("\n2. アナリストデータ取得中...")
        analyst = ingester.get_analyst_data(test_symbol)
        if analyst.get('error'):
            print(f"   エラー: {analyst['error']}")
        else:
            print(f"   目標株価: ${analyst.get('target_price', 0):.2f}" if analyst.get('target_price') else "   目標株価: N/A")
            print(f"   推奨: {analyst.get('recommendation', 'N/A')}")
            print(f"   EPS成長率: {analyst.get('eps_growth', 0):.1%}" if analyst.get('eps_growth') is not None else "   EPS成長率: N/A")
        
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[OK] 財務データ取得テスト完了")


def test_news_ingester():
    """ニュース取得のテスト"""
    print("\n" + "=" * 80)
    print("【テスト5】ニュース取得（L3）")
    print("=" * 80)
    
    ingester = NewsIngester()
    test_symbol = "AAPL"
    
    print(f"\nシンボル: {test_symbol}")
    
    try:
        # 最近のニュース取得
        print("\n1. 最近のニュース取得中...")
        news = ingester.get_recent_news(test_symbol, days=7)
        print(f"   取得件数: {len(news)}件")
        for i, item in enumerate(news[:3], 1):
            print(f"   {i}. {item.get('title', 'N/A')[:60]}...")
            print(f"      公開日: {item.get('published_time', 'N/A')}")
        
        # 決算カレンダー取得
        print("\n2. 決算カレンダー取得中...")
        calendar = ingester.get_earnings_calendar(test_symbol)
        if calendar:
            print(f"   次回決算予定: {calendar.get('next_earnings_date', 'N/A')}")
        else:
            print("   決算カレンダー: データなし")
        
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[OK] ニュース取得テスト完了")


def main():
    """メインテスト実行"""
    print("=" * 80)
    print("新機能テストスイート")
    print("=" * 80)
    print("\n注意: SEC EDGAR APIはレート制限があるため、")
    print("      テストは控えめに実行してください。\n")
    
    try:
        # テスト1: ティッカー解決
        test_ticker_resolver()
        
        # テスト2: SEC EDGAR統合（レート制限に注意）
        # test_sec_edgar()  # コメントアウト（レート制限回避）
        print("\n" + "=" * 80)
        print("【テスト2】SEC EDGAR統合 - スキップ（レート制限回避）")
        print("=" * 80)
        print("注意: SEC EDGAR APIはレート制限が厳しいため、")
        print("      実際の使用時のみ実行してください。")
        
        # テスト3: イベント分類
        test_event_classifier()
        
        # テスト4: 財務データ取得
        test_fundamental_ingester()
        
        # テスト5: ニュース取得
        test_news_ingester()
        
        print("\n" + "=" * 80)
        print("[OK] 全テスト完了")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
