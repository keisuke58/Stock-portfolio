"""
Daily Runner: 1日1回実行するメインロジック
"""
import json
import sys
from typing import List, Dict, Optional
from datetime import datetime
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_loader import load_all_config
from cache import PriceCache
from fetchers import YahooFetcher, CoinGeckoFetcher
from features import FeatureCalculator
from validators import DataValidator
from state_machine import StateMachine
from signals import is_crypto_symbol
from scoring import VMSScorer
from selector import DailySelector
from notifiers import DiscordNotifier, LineNotifier, SlackNotifier, GmailNotifier
from state_store import StateStore
from ingest import FundamentalIngester, NewsIngester, TickerResolver, SECEdgarIngester
from knowledge import EventClassifier
from visualization import ReportGenerator


class DailyRunner:
    """1日1回実行するメインロジック"""
    
    def __init__(self, config_path: str = None):
        """設定ファイルから初期化
        
        Args:
            config_path: 既存のconfig.jsonのパス（後方互換性のため。Noneの場合は新しい設定ファイルを使用）
        """
        # config/config_loader.py経由で設定を読み込む
        self.config = load_all_config(legacy_config_path=config_path)
        
        # コンポーネント初期化
        self.cache = PriceCache()
        self.yahoo_fetcher = YahooFetcher(self.cache)
        self.coingecko_fetcher = CoinGeckoFetcher(self.cache)
        self.state_machine = StateMachine(self.yahoo_fetcher, self.coingecko_fetcher)
        self.selector = DailySelector()
        self.state_store = StateStore()
        
        # ティッカー解決コンポーネント
        self.ticker_resolver = TickerResolver()
        
        # L1-L3データ取得コンポーネント（実装済み）
        # L1: 財務指標（FCF、売上成長、利益率、財務健全性、アナリストデータ）
        self.fundamental_ingester = FundamentalIngester()
        # L1拡張: SEC EDGAR（公式決算・開示）
        self.sec_edgar_ingester = SECEdgarIngester()
        # L3: ニュース・開示（ニュース、決算カレンダー）
        self.news_ingester = NewsIngester()
        # L3: イベント分類（好材料/悪材料/中立）- LLM統合済み
        llm_api_key = self.config.get('llm_api_key', '')
        llm_model = self.config.get('llm_model', 'gpt-4o-mini')
        llm_temperature = self.config.get('llm_temperature', 0.3)
        self.event_classifier = EventClassifier(
            llm_api_key=llm_api_key if llm_api_key else None,
            llm_model=llm_model,
            llm_temperature=llm_temperature
        )
        
        # L2/L4データ取得コンポーネント（将来拡張用）
        # L2: マクロデータ（CPI、雇用、金利、DXY）- 未実装
        # self.macro_ingester = MacroIngester()  # TODO: 実装
        # L4: 代替データ（求人、アプリDL、Webトラフィック）- 未実装
        # self.alternative_ingester = AlternativeIngester()  # TODO: 実装
        
        # 通知設定（Discord、Line、Slack、Gmailに対応）
        self.notifiers = []
        
        webhook_url = self.config.get('webhook')
        if webhook_url:
            self.notifiers.append(DiscordNotifier(webhook_url))
        
        line_token = self.config.get('line_token')
        if line_token:
            self.notifiers.append(LineNotifier(line_token))
        
        slack_webhook_url = self.config.get('slack_webhook')
        if slack_webhook_url:
            self.notifiers.append(SlackNotifier(slack_webhook_url))
        
        # Gmail設定
        gmail_user = self.config.get('gmail_user')
        gmail_password = self.config.get('gmail_password')
        gmail_to = self.config.get('gmail_to')
        if gmail_user and gmail_password and gmail_to:
            self.notifiers.append(GmailNotifier(gmail_user, gmail_password, gmail_to))
        
        # 監視対象シンボル
        self.symbols = self.config.get('symbols', [])
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """1つのシンボルを分析して投資評価を返す
        
        処理順: fetch -> validate -> features -> state_machine -> scoring -> selector -> report -> notifier
        """
        try:
            # 1. fetch: 現在価格と履歴価格を取得
            if is_crypto_symbol(symbol):
                current_price = self.coingecko_fetcher.get_current_price(symbol)
                prices = self.coingecko_fetcher.get_historical_prices(symbol, days=30)
            else:
                current_price = self.yahoo_fetcher.get_current_price(symbol)
                prices = self.yahoo_fetcher.get_historical_prices(symbol, days=30)
            
            if current_price is None or prices is None:
                return None
            
            # 2. validate: データ検証
            # 価格の検証（NaN/<=0は除外）
            is_valid, validated_price = DataValidator.validate_price(current_price, symbol)
            if not is_valid:
                return None
            
            # 財務指標を取得・検証（米国株の場合）
            metrics = None
            pe_ratio = None
            fundamental_data = None  # L1データ
            analyst_data = None  # L1データ（アナリスト）
            events = []  # L3データ（イベント）
            
            if not is_crypto_symbol(symbol):
                # ティッカー解決（A = Agilent Technologies等）
                ticker_info = None
                cik = None
                try:
                    ticker_info = self.ticker_resolver.resolve_ticker(symbol)
                    cik = ticker_info.get('cik')
                except Exception as e:
                    print(f"Warning: Failed to resolve ticker {symbol}: {e}")
                
                # 基本財務指標（既存）
                metrics = self.yahoo_fetcher.get_metrics(symbol)
                # 配当利回りを検証
                metrics = DataValidator.validate_metrics(metrics, symbol)
                pe_ratio = metrics.get('pe_ratio')
                
                # L1: 財務データを取得（優先順位1-3）
                # ✅ 実装済み: FCF、売上成長、利益率、財務健全性、アナリストデータ
                try:
                    fundamental_data = self.fundamental_ingester.get_fundamental_data(symbol)
                    analyst_data = self.fundamental_ingester.get_analyst_data(symbol)
                except Exception as e:
                    print(f"Warning: Failed to fetch L1 data for {symbol}: {e}")
                
                # L1拡張: SEC EDGAR（公式決算・開示）- 優先順位1
                sec_filings = []
                guidance_updates = []
                if cik:
                    try:
                        # 最近の決算リリース（8-K）を取得
                        sec_filings = self.sec_edgar_ingester.get_recent_earnings_releases(cik, days=90)
                        # ガイダンス更新を取得
                        guidance_updates = self.sec_edgar_ingester.get_guidance_updates(cik)
                    except Exception as e:
                        print(f"Warning: Failed to fetch SEC EDGAR data for {symbol} (CIK: {cik}): {e}")
                
                # L3: ニュース・イベントを取得
                # ✅ 実装済み: ニュース分類（好材料/悪材料/中立）、決算カレンダー
                try:
                    news_items = self.news_ingester.get_recent_news(symbol, days=7)
                    if news_items:
                        events = self.event_classifier.classify_news(news_items)
                    
                    # 決算イベントも追加
                    earnings_data = self.news_ingester.get_earnings_calendar(symbol)
                    if earnings_data:
                        earnings_events = self.event_classifier.extract_earnings_events(earnings_data)
                        events.extend(earnings_events)
                    
                    # SEC EDGAR開示をイベントとして追加
                    if sec_filings:
                        sec_events = self.event_classifier.classify_sec_filings(sec_filings)
                        events.extend(sec_events)
                    
                    # ガイダンス更新をイベントとして追加
                    if guidance_updates:
                        guidance_events = self.event_classifier.classify_sec_filings(guidance_updates)
                        events.extend(guidance_events)
                except Exception as e:
                    print(f"Warning: Failed to fetch L3 data for {symbol}: {e}")
                
                # L2: マクロデータ取得（将来拡張用）
                # ⏳ 未実装: CPI、雇用、金利、DXY等
                # macro_data = None
                # try:
                #     macro_data = self.macro_ingester.get_macro_data()
                # except Exception as e:
                #     print(f"Warning: Failed to fetch L2 data: {e}")
                
                # L4: 代替データ取得（将来拡張用）
                # ⏳ 未実装: 求人、アプリDL、Webトラフィック等
                # alternative_data = None
                # try:
                #     alternative_data = self.alternative_ingester.get_alternative_data(symbol)
                # except Exception as e:
                #     print(f"Warning: Failed to fetch L4 data for {symbol}: {e}")
            
            # data_timestampを追加
            data_timestamp = datetime.utcnow()
            
            # 3. features: 指標を計算
            features = FeatureCalculator.calculate_all_features(prices)
            
            # 4. state_machine: 状態を更新
            old_state = self.state_store.get_state(symbol)
            new_state = self.state_machine.determine_state(symbol, prices, old_state)
            state_changed = self.state_store.set_state(symbol, new_state, validated_price)
            
            # 状態変化を通知（BUY新規発生のみ）
            if state_changed and new_state == 'BUY' and self.notifiers:
                if self.state_store.should_notify(symbol, new_state):
                    for notifier in self.notifiers:
                        notifier.notify_state_change(symbol, old_state, new_state, validated_price)
                    self.state_store.mark_notified(symbol, new_state)
            
            # 5. scoring: スコアを計算
            # 質スコアを計算（簡易版）
            quality_score = 3  # デフォルト
            if is_crypto_symbol(symbol):
                major_cryptos = ['BTC', 'ETH', 'BNB', 'SOL']
                if symbol.upper() in major_cryptos:
                    quality_score = 5
            else:
                # 米国株の場合、時価総額で判定
                if metrics:
                    market_cap = metrics.get('market_cap')
                    if market_cap:
                        if market_cap > 100_000_000_000:  # 1000億ドル以上
                            quality_score = 5
                        elif market_cap > 10_000_000_000:  # 100億ドル以上
                            quality_score = 4
            
            # 市場ボラティリティを計算（動的重み調整用）
            market_volatility = None
            if features.get('volatility') is not None:
                # 簡易版: 個別資産のボラティリティを市場ボラティリティの代理として使用
                # 将来的には市場全体のボラティリティ（例: VIX）を取得
                market_volatility = features.get('volatility')
            
            scores = VMSScorer.calculate_all_scores(
                features,
                new_state,
                pe_ratio,
                quality_score,
                fundamental_data,  # L1データ
                events,  # L3データ
                analyst_data,  # L1データ（アナリスト）
                market_volatility=market_volatility,
                use_dynamic_weights=True  # 動的重み調整を有効化
            )
            
            # BUY資格チェック
            buy_qualified = False
            buy_reasons = []
            if features.get('breakout_5d', False):
                buy_qualified = True
                buy_reasons.append("5日高値ブレイク")
            else:
                buy_reasons.append("5日高値未ブレイク")
            
            if features.get('return_30d') is not None:
                return_30d = features['return_30d']
                if -30 <= return_30d <= 30:
                    buy_qualified = buy_qualified and True
                    buy_reasons.append(f"30日リターン適正({return_30d:.1f}%)")
                else:
                    buy_qualified = False
                    buy_reasons.append(f"30日リターン極端({return_30d:.1f}%)")
            
            # 資産カテゴリを判定
            asset_category = 'その他'
            if is_crypto_symbol(symbol):
                asset_category = '仮想通貨'
            else:
                etf_patterns = ['SPY', 'QQQ', 'IVV', 'VTI', 'VOO', 'GLD', 'SLV']
                if symbol.upper() in etf_patterns:
                    asset_category = 'ETF'
                else:
                    asset_category = '米国株'
            
            # 結果をまとめる（data_timestampを含める）
            result = {
                'symbol': symbol,
                'asset_category': asset_category,
                'current_price': validated_price,
                'current_state': new_state,
                'ath_ratio': features.get('ath_ratio'),
                'return_30d': features.get('return_30d'),
                'volatility': features.get('volatility'),
                'total_score': scores['total_score'],
                'value_score': scores['value_score'],
                'momentum_score': scores['momentum_score'],
                'stability_score': scores['stability_score'],
                'buy_qualified': buy_qualified,
                'buy_reasons': buy_reasons,
                'quality_score': quality_score,
                'data_timestamp': data_timestamp,  # 取得時刻を追加
            }
            
            # metricsも含める（report生成時に使用）
            if metrics:
                result['metrics'] = metrics
            
            # L1-L3データを追加（レポート生成用）
            if fundamental_data:
                result['fundamental_data'] = fundamental_data
            if analyst_data:
                result['analyst_data'] = analyst_data
            if events:
                result['events'] = events
            if ticker_info:
                result['ticker_info'] = ticker_info
            if sec_filings:
                result['sec_filings'] = sec_filings
            if guidance_updates:
                result['guidance_updates'] = guidance_updates
            if scores.get('data_layers_used'):
                result['data_layers_used'] = scores['data_layers_used']
            if scores.get('weights_used'):
                result['weights_used'] = scores['weights_used']
            
            # 履歴価格データを追加（可視化用）
            result['historical_prices'] = prices
            
            return result
            
        except Exception as e:
            print(f"エラー: {symbol} の分析中にエラー: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self, max_assets: int = 200):
        """メイン実行ロジック"""
        print("=" * 80)
        print("Daily Runner: 1日1個選出")
        print("=" * 80)
        print(f"監視対象: {len(self.symbols)}件")
        print(f"実際に分析する資産数: 最大{max_assets}（主要資産優先）")
        print(f"開始時刻: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 80)
        print()
        
        # 1. 候補リスト（Universe）読み込み
        symbols_to_analyze = self.symbols[:max_assets]
        
        # 2-5. 各シンボルを分析
        candidates = []
        processed = 0
        skipped = 0
        
        for i, symbol in enumerate(symbols_to_analyze, 1):
            print(f"[{i}/{len(symbols_to_analyze)}] {symbol} を分析中...", end=' ')
            
            result = self.analyze_symbol(symbol)
            
            if result:
                candidates.append(result)
                print(f"OK スコア: {result['total_score']:.1f}")
                processed += 1
            else:
                print("スキップ")
                skipped += 1
            
            # レート制限対策: 10件ごとに少し待機
            if i % 10 == 0:
                print("  レート制限対策: 2秒待機中...")
                time.sleep(2)
            else:
                time.sleep(0.5)
        
        print()
        print(f"分析完了: {processed}件成功, {skipped}件スキップ")
        print()
        
        if not candidates:
            print("候補が見つかりませんでした。")
            return
        
        # 6. フィルタ（除外ルール）
        # WATCH状態は除外（急落直後なので買わない）
        candidates = [c for c in candidates if c['current_state'] != 'WATCH']
        
        # 7. セレクタで「スコアの高い上位3個」を決定
        top_picks = self.selector.select_top_n(candidates, n=3)
        
        if not top_picks:
            print("候補が見つかりませんでした。")
            return
        
        # 8. レポート保存＋Discord通知
        print("=" * 80)
        print("【スコア上位3個】")
        for i, pick in enumerate(top_picks, 1):
            print(f"\n{i}. {pick['symbol']}")
            print(f"   カテゴリ: {pick['asset_category']}")
            print(f"   状態: {pick['current_state']}")
            print(f"   信頼度: {pick.get('confidence', 'Spec')}")
            print(f"   投資スコア: {pick['total_score']:.1f}/100")
            print(f"     - Value: {pick['value_score']:.1f}")
            print(f"     - Momentum: {pick['momentum_score']:.1f}")
            print(f"     - Stability: {pick['stability_score']:.1f}")
        print("=" * 80)
        
        # 通知（Discord/Line）- 各ピックを個別に通知
        for notifier in self.notifiers:
            for pick in top_picks:
                notifier.notify_daily_pick(pick)
        
        # テキストレポートをファイルに保存（上位3個すべてを保存）
        self._save_report(top_picks, candidates)
        
        # HTML可視化レポートを生成・保存
        try:
            report_generator = ReportGenerator()
            html_report_path = report_generator.generate_html_report(top_picks, candidates)
            print(f"HTML可視化レポートを {html_report_path} に保存しました。")
        except Exception as e:
            print(f"警告: HTMLレポート生成エラー: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("完了！")
    
    def _save_report(self, top_picks: List[Dict], candidates: List[Dict]):
        """レポートをファイルに保存（上位3個すべてを保存）"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("【スコア上位3個】投資推奨レポート")
        report_lines.append("=" * 80)
        report_lines.append(f"生成時刻: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_lines.append("")
        
        # 各ピックの詳細を表示
        for idx, daily_pick in enumerate(top_picks, 1):
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append(f"【{idx}位】 {daily_pick['symbol']}")
            report_lines.append("=" * 80)
            
            # ティッカー情報を表示
            ticker_info = daily_pick.get('ticker_info')
            if ticker_info:
                company_name = ticker_info.get('company_name', '')
                if company_name:
                    report_lines.append(f"会社名: {company_name}")
                sector = ticker_info.get('sector', '')
                if sector and sector != 'Unknown':
                    report_lines.append(f"セクター: {sector}")
            
            report_lines.append(f"カテゴリ: {daily_pick['asset_category']}")
            report_lines.append(f"状態: {daily_pick['current_state']}")
            report_lines.append(f"信頼度: {daily_pick.get('confidence', 'Spec')}")
            report_lines.append(f"投資スコア: {daily_pick['total_score']:.1f}/100")
            report_lines.append(f"  - Value（割安度）: {daily_pick['value_score']:.1f}")
            report_lines.append(f"  - Momentum（反転）: {daily_pick['momentum_score']:.1f}")
            report_lines.append(f"  - Stability（安定性）: {daily_pick['stability_score']:.1f}")
            
            # 使用された重みを表示（動的重み調整の場合）
            weights_used = daily_pick.get('weights_used')
            if weights_used:
                report_lines.append(f"  使用重み: Value={weights_used.get('value', 0.4):.1%}, Momentum={weights_used.get('momentum', 0.35):.1%}, Stability={weights_used.get('stability', 0.25):.1%}")
            
            report_lines.append(f"現在価格: ${daily_pick['current_price']:,.2f}")
            
            # data_timestampを表示
            if daily_pick.get('data_timestamp'):
                data_ts = daily_pick['data_timestamp']
                if isinstance(data_ts, datetime):
                    report_lines.append(f"データ取得時刻: {data_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                else:
                    report_lines.append(f"データ取得時刻: {data_ts}")
            
            if daily_pick.get('ath_ratio'):
                report_lines.append(f"ATH比: {daily_pick['ath_ratio']:.1%}")
            
            if daily_pick.get('return_30d') is not None:
                report_lines.append(f"30日リターン: {daily_pick['return_30d']:+.1f}%")
            
            # L1データ（財務指標）を表示
            fundamental_data = daily_pick.get('fundamental_data')
            if fundamental_data:
                report_lines.append("")
                report_lines.append("【財務指標（L1データ）】")
                report_lines.append("-" * 80)
                
                fcf = fundamental_data.get('fcf')
                if fcf:
                    report_lines.append(f"フリーキャッシュフロー: ${fcf:,.0f}")
                
                revenue_growth = fundamental_data.get('revenue_growth')
                if revenue_growth is not None:
                    report_lines.append(f"売上成長率: {revenue_growth:.1%}")
                
                profit_margin = fundamental_data.get('profit_margin')
                if profit_margin is not None:
                    report_lines.append(f"利益率: {profit_margin:.1%}")
                
                financial_health_score = fundamental_data.get('financial_health_score')
                if financial_health_score is not None:
                    report_lines.append(f"財務健全性スコア: {financial_health_score:.1f}/100")
                
                # 根拠リンクを表示
                data_sources = fundamental_data.get('data_sources', [])
                if data_sources:
                    report_lines.append("")
                    report_lines.append("【データソース（根拠リンク）】")
                    for source in data_sources:
                        source_name = source.get('name', 'Unknown')
                        source_url = source.get('url', '')
                        reliability = source.get('reliability', 'unknown')
                        if source_url:
                            report_lines.append(f"  - {source_name} ({reliability}): {source_url}")
            
            # SEC EDGAR開示を表示
            sec_filings = daily_pick.get('sec_filings', [])
            if sec_filings:
                report_lines.append("")
                report_lines.append("【SEC EDGAR開示（公式）】")
                report_lines.append("-" * 80)
                for filing in sec_filings[:5]:  # 最大5件
                    form = filing.get('form', '')
                    filing_date = filing.get('filing_date', '')
                    description = filing.get('description', '')
                    url = filing.get('url', '')
                    report_lines.append(f"  - {form} ({filing_date})")
                    if description:
                        report_lines.append(f"    {description[:100]}...")  # 最初の100文字
                    if url:
                        report_lines.append(f"    リンク: {url}")
            
            guidance_updates = daily_pick.get('guidance_updates', [])
            if guidance_updates:
                report_lines.append("")
                report_lines.append("【ガイダンス更新】")
                report_lines.append("-" * 80)
                for update in guidance_updates[:3]:  # 最大3件
                    form = update.get('form', '')
                    filing_date = update.get('filing_date', '')
                    url = update.get('url', '')
                    report_lines.append(f"  - {form} ({filing_date})")
                    if url:
                        report_lines.append(f"    リンク: {url}")
            
            # L3データ（イベント要約）を表示
            events = daily_pick.get('events', [])
            if events:
                report_lines.append("")
                report_lines.append("【最近のイベント（L3データ）】")
                report_lines.append("-" * 80)
                
                # イベントをタイプ別に分類
                positive_events = [e for e in events if e.get('event_type') == 'positive']
                negative_events = [e for e in events if e.get('event_type') == 'negative']
                neutral_events = [e for e in events if e.get('event_type') == 'neutral']
                
                if positive_events:
                    report_lines.append("【好材料】")
                    for event in positive_events[:3]:  # 最大3件
                        title = event.get('title', '')
                        summary = event.get('summary', '')
                        link = event.get('link', '')
                        impact = event.get('impact', 'low')
                        report_lines.append(f"  - {title} ({impact} impact)")
                        if summary:
                            report_lines.append(f"    要約: {summary}")
                        if link:
                            report_lines.append(f"    リンク: {link}")
                
                if negative_events:
                    report_lines.append("【悪材料】")
                    for event in negative_events[:3]:  # 最大3件
                        title = event.get('title', '')
                        summary = event.get('summary', '')
                        link = event.get('link', '')
                        impact = event.get('impact', 'low')
                        report_lines.append(f"  - {title} ({impact} impact)")
                        if summary:
                            report_lines.append(f"    要約: {summary}")
                        if link:
                            report_lines.append(f"    リンク: {link}")
                
                if neutral_events:
                    report_lines.append("【中立】")
                    for event in neutral_events[:2]:  # 最大2件
                        summary = event.get('summary', '')
                        if summary:
                            report_lines.append(f"  - {summary}")
            
            # 使用したデータレイヤーを表示
            data_layers_used = daily_pick.get('data_layers_used', {})
            if data_layers_used:
                report_lines.append("")
                report_lines.append("【使用データレイヤー】")
                layers_info = []
                if data_layers_used.get('L0'):
                    layers_info.append("L0: 価格・出来高")
                if data_layers_used.get('L1'):
                    layers_info.append("L1: 財務指標")
                if data_layers_used.get('L3'):
                    layers_info.append("L3: ニュース・イベント")
                if layers_info:
                    report_lines.append(", ".join(layers_info))
        
        report_lines.append("")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("【候補リスト（Top 10）】")
        report_lines.append("=" * 80)
        
        # 候補をスコア順にソート
        candidates_sorted = sorted(candidates, key=lambda x: x['total_score'], reverse=True)
        
        for i, candidate in enumerate(candidates_sorted[:10], 1):
            report_lines.append(
                f"{i:2d}. {candidate['symbol']:6s} | "
                f"状態: {candidate['current_state']:5s} | "
                f"スコア: {candidate['total_score']:5.1f} | "
                f"カテゴリ: {candidate['asset_category']}"
            )
        
        report_lines.append("=" * 80)
        
        # ファイルに保存
        report_text = "\n".join(report_lines)
        with open('investment_report.txt', 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"レポートを investment_report.txt に保存しました。")
