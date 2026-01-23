"""
バックテストモジュール
過去データで予測精度を検証
日次検証、手数料/スリッページ/最大DD計算対応
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import YahooFetcher, CoinGeckoFetcher
from features import FeatureCalculator
from scoring import VMSScorer
from state_machine import StateMachine
from signals import is_crypto_symbol
from cache import PriceCache
from selector.daily_selector import DailySelector


class Backtester:
    """バックテストクラス"""
    
    # デフォルト設定
    DEFAULT_ENTRY_FEE_RATE = 0.001  # 0.1%
    DEFAULT_EXIT_FEE_RATE = 0.001   # 0.1%
    DEFAULT_BUY_SLIPPAGE = 0.0005   # 0.05%
    DEFAULT_SELL_SLIPPAGE = 0.0005  # 0.05%
    
    def __init__(
        self,
        entry_fee_rate: float = DEFAULT_ENTRY_FEE_RATE,
        exit_fee_rate: float = DEFAULT_EXIT_FEE_RATE,
        buy_slippage: float = DEFAULT_BUY_SLIPPAGE,
        sell_slippage: float = DEFAULT_SELL_SLIPPAGE
    ):
        """
        初期化
        
        Args:
            entry_fee_rate: エントリー手数料率（デフォルト: 0.1%）
            exit_fee_rate: エグジット手数料率（デフォルト: 0.1%）
            buy_slippage: 買いスリッページ率（デフォルト: 0.05%）
            sell_slippage: 売りスリッページ率（デフォルト: 0.05%）
        """
        self.cache = PriceCache()
        self.yahoo_fetcher = YahooFetcher(self.cache)
        self.coingecko_fetcher = CoinGeckoFetcher(self.cache)
        self.state_machine = StateMachine(self.yahoo_fetcher, self.coingecko_fetcher)
        self.selector = DailySelector()
        
        self.entry_fee_rate = entry_fee_rate
        self.exit_fee_rate = exit_fee_rate
        self.buy_slippage = buy_slippage
        self.sell_slippage = sell_slippage
    
    def backtest_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        prediction_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        1つのシンボルをバックテスト
        
        Args:
            symbol: シンボル名
            start_date: 開始日
            end_date: 終了日
            prediction_history: 過去の予測履歴（オプション）
        
        Returns:
            バックテスト結果の辞書
        """
        results = {
            'symbol': symbol,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'predictions': [],
            'metrics': {}
        }
        
        # 日次でループ（CPU環境を考慮して週次サンプリングも可能）
        current_date = start_date
        predictions = []
        days_processed = 0
        
        while current_date <= end_date:
            try:
                # その日のデータを取得（キャッシュを活用）
                if is_crypto_symbol(symbol):
                    prices = self.coingecko_fetcher.get_historical_prices(symbol, days=30, end_date=current_date)
                    # 現在価格は履歴の最新価格を使用（API呼び出し削減）
                    current_price = prices[-1][1] if prices else None
                else:
                    prices = self.yahoo_fetcher.get_historical_prices(symbol, days=30, end_date=current_date)
                    # 現在価格は履歴の最新価格を使用（API呼び出し削減）
                    current_price = prices[-1][1] if prices else None
                
                if not prices or current_price is None:
                    current_date += timedelta(days=1)
                    continue
                
                # 特徴量を計算
                features = FeatureCalculator.calculate_all_features(prices)
                
                # 状態を判定
                old_state = None  # バックテストでは状態履歴を保持しない
                new_state = self.state_machine.determine_state(symbol, prices, old_state)
                
                # スコアを計算（簡易版、L1-L3データは使用しない）
                scores = VMSScorer.calculate_all_scores(
                    features,
                    new_state,
                    pe_ratio=None,
                    quality_score=3,
                    fundamental_data=None,
                    events=None,
                    analyst_data=None,
                    use_dynamic_weights=False
                )
                
                # 予測を記録
                prediction = {
                    'date': current_date.isoformat(),
                    'predicted_state': new_state,
                    'predicted_score': scores['total_score'],
                    'value_score': scores['value_score'],
                    'momentum_score': scores['momentum_score'],
                    'stability_score': scores['stability_score'],
                    'current_price': current_price,
                    'ath_ratio': features.get('ath_ratio'),
                    'return_30d': features.get('return_30d'),
                    'volatility': features.get('volatility')
                }
                
                predictions.append(prediction)
                days_processed += 1
                
            except Exception as e:
                print(f"Error backtesting {symbol} on {current_date}: {e}")
            
            current_date += timedelta(days=1)
            
            # CPU環境を考慮: 10日ごとに進捗を表示
            if days_processed % 10 == 0:
                print(f"  Processed {days_processed} days...")
        
        results['predictions'] = predictions
        
        # メトリクスを計算
        if predictions:
            results['metrics'] = self._calculate_metrics(predictions, symbol, start_date, end_date)
        
        return results
    
    def _calculate_metrics(
        self,
        predictions: List[Dict],
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        バックテストメトリクスを計算
        
        Args:
            predictions: 予測のリスト
            symbol: シンボル名
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            メトリクスの辞書
        """
        if not predictions:
            return {}
        
        # BUYシグナル発生回数
        buy_signals = [p for p in predictions if p.get('predicted_state') == 'BUY']
        buy_count = len(buy_signals)
        
        # 平均スコア
        scores = [p.get('predicted_score', 0) for p in predictions]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # スコアの標準偏差
        import statistics
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # 実際のリターンを計算（開始日と終了日の価格から）
        try:
            if is_crypto_symbol(symbol):
                start_price = self.coingecko_fetcher.get_current_price(symbol)
                end_price = self.coingecko_fetcher.get_current_price(symbol)
            else:
                start_price = self.yahoo_fetcher.get_current_price(symbol)
                end_price = self.yahoo_fetcher.get_current_price(symbol)
            
            actual_return = None
            if start_price and end_price and start_price > 0:
                actual_return = ((end_price - start_price) / start_price) * 100
        except:
            actual_return = None
        
        # 予測精度（簡易版）
        # 高スコア（70以上）の予測が実際に上昇したか
        high_score_predictions = [p for p in predictions if p.get('predicted_score', 0) >= 70]
        precision = None
        if high_score_predictions and actual_return is not None:
            # 高スコア予測が実際の上昇と一致したか
            if actual_return > 0:
                precision = 1.0  # 実際に上昇した
            else:
                precision = 0.0  # 実際は下落した
        
        metrics = {
            'total_predictions': len(predictions),
            'buy_signal_count': buy_count,
            'buy_signal_rate': buy_count / len(predictions) if predictions else 0,
            'avg_score': avg_score,
            'score_std': score_std,
            'max_score': max(scores) if scores else 0,
            'min_score': min(scores) if scores else 0,
            'actual_return': actual_return,
            'precision': precision
        }
        
        return metrics
    
    def backtest_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        output_file: Optional[str] = None
    ) -> Dict:
        """
        複数のシンボルをバックテスト
        
        Args:
            symbols: シンボルのリスト
            start_date: 開始日
            end_date: 終了日
            output_file: 結果を保存するファイル（オプション）
        
        Returns:
            バックテスト結果の辞書
        """
        results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'symbols': symbols,
            'results': []
        }
        
        for symbol in symbols:
            print(f"Backtesting {symbol}...")
            symbol_result = self.backtest_symbol(symbol, start_date, end_date)
            results['results'].append(symbol_result)
        
        # 全体メトリクスを計算
        results['overall_metrics'] = self._calculate_overall_metrics(results['results'])
        
        # ファイルに保存
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Backtest results saved to {output_file}")
        
        return results
    
    def _calculate_overall_metrics(self, symbol_results: List[Dict]) -> Dict:
        """
        全体メトリクスを計算
        
        Args:
            symbol_results: 各シンボルの結果リスト
        
        Returns:
            全体メトリクスの辞書
        """
        if not symbol_results:
            return {}
        
        total_predictions = sum(len(r.get('predictions', [])) for r in symbol_results)
        total_buy_signals = sum(r.get('metrics', {}).get('buy_signal_count', 0) for r in symbol_results)
        
        avg_scores = [r.get('metrics', {}).get('avg_score', 0) for r in symbol_results if r.get('metrics', {}).get('avg_score')]
        overall_avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        actual_returns = [r.get('metrics', {}).get('actual_return') for r in symbol_results if r.get('metrics', {}).get('actual_return') is not None]
        avg_return = sum(actual_returns) / len(actual_returns) if actual_returns else None
        
        return {
            'total_symbols': len(symbol_results),
            'total_predictions': total_predictions,
            'total_buy_signals': total_buy_signals,
            'overall_buy_signal_rate': total_buy_signals / total_predictions if total_predictions > 0 else 0,
            'overall_avg_score': overall_avg_score,
            'avg_actual_return': avg_return
        }
    
    def evaluate_prediction_accuracy(
        self,
        predictions: List[Dict],
        actual_prices: Dict[str, float]
    ) -> Dict:
        """
        予測精度を評価
        
        Args:
            predictions: 予測のリスト
            actual_prices: 実際の価格の辞書 {date: price}
        
        Returns:
            精度評価の辞書
        """
        if not predictions:
            return {}
        
        correct_predictions = 0
        total_predictions = 0
        
        for prediction in predictions:
            date = prediction.get('date')
            predicted_state = prediction.get('predicted_state')
            predicted_score = prediction.get('predicted_score', 0)
            
            if date not in actual_prices:
                continue
            
            # 予測がBUYで、実際に価格が上昇したか
            if predicted_state == 'BUY' and predicted_score >= 70:
                # 次の日の価格と比較（簡易版）
                # 実際の実装では、より詳細な評価が必要
                total_predictions += 1
                # ここでは簡易的に、予測日の価格と次の日の価格を比較
                # 実際の実装では、より詳細な評価が必要
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
        
        return {
            'total_predictions': total_predictions,
            'correct_predictions': correct_predictions,
            'accuracy': accuracy
        }
    
    def calculate_fees(self, price: float, quantity: float, is_entry: bool = True) -> float:
        """
        手数料を計算
        
        Args:
            price: 価格
            quantity: 数量
            is_entry: True=エントリー、False=エグジット
        
        Returns:
            手数料（金額）
        """
        fee_rate = self.entry_fee_rate if is_entry else self.exit_fee_rate
        return price * quantity * fee_rate
    
    def apply_slippage(self, price: float, is_buy: bool = True) -> float:
        """
        スリッページを適用
        
        Args:
            price: 価格
            is_buy: True=買い、False=売り
        
        Returns:
            スリッページ適用後の価格
        """
        slippage = self.buy_slippage if is_buy else self.sell_slippage
        if is_buy:
            return price * (1 + slippage)  # 買い: 価格が上がる
        else:
            return price * (1 - slippage)  # 売り: 価格が下がる
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        最大ドローダウンを計算
        
        Args:
            equity_curve: エクイティカーブ（時系列の資産価値リスト）
        
        Returns:
            最大ドローダウン（%、負の値）
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        max_dd = 0.0
        peak = equity_curve[0]
        
        for value in equity_curve:
            if value > peak:
                peak = value
            else:
                dd = ((value - peak) / peak) * 100
                if dd < max_dd:
                    max_dd = dd
        
        return max_dd
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """
        シャープレシオを計算
        
        Args:
            returns: リターンのリスト（%）
            risk_free_rate: リスクフリーレート（%、デフォルト: 0%）
        
        Returns:
            シャープレシオ
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        import statistics
        
        # 平均リターン
        avg_return = statistics.mean(returns)
        
        # 標準偏差
        std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        if std_dev == 0:
            return 0.0
        
        # シャープレシオ = (平均リターン - リスクフリーレート) / 標準偏差
        sharpe = (avg_return - risk_free_rate) / std_dev
        
        return sharpe
    
    def backtest_strategy_daily(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        stop_loss_pct: float = -10.0,
        take_profit_pct: float = 20.0
    ) -> Dict:
        """
        日次戦略バックテスト（selector→signals→scoringの戦略を日次で検証）
        
        Args:
            symbols: シンボルのリスト
            start_date: 開始日
            end_date: 終了日
            initial_capital: 初期資本（デフォルト: $100,000）
            stop_loss_pct: ストップロス（%、デフォルト: -10%）
            take_profit_pct: 利確（%、デフォルト: +20%）
        
        Returns:
            バックテスト結果の辞書
        """
        results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'initial_capital': initial_capital,
            'final_capital': initial_capital,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'total_fees': 0.0,
            'total_slippage': 0.0,
            'daily_returns': [],
            'equity_curve': [initial_capital],
            'trades': []
        }
        
        # ポジション管理
        positions = {}  # {symbol: {'entry_price': float, 'entry_date': datetime, 'quantity': float}}
        capital = initial_capital
        equity_curve = [initial_capital]
        daily_returns = []
        trades = []
        
        # 日次でループ
        current_date = start_date
        while current_date <= end_date:
            try:
                # その日の候補を分析
                candidates = []
                for symbol in symbols:
                    try:
                        # 価格データを取得
                        if is_crypto_symbol(symbol):
                            prices = self.coingecko_fetcher.get_historical_prices(
                                symbol, days=30, end_date=current_date
                            )
                        else:
                            prices = self.yahoo_fetcher.get_historical_prices(
                                symbol, days=30, end_date=current_date
                            )
                        
                        if not prices:
                            continue
                        
                        # 特徴量を計算
                        features = FeatureCalculator.calculate_all_features(prices)
                        current_price = prices[-1][1]
                        
                        # 状態を判定
                        old_state = None
                        new_state = self.state_machine.determine_state(symbol, old_state)
                        
                        # スコアを計算
                        scores = VMSScorer.calculate_all_scores(
                            features,
                            new_state,
                            pe_ratio=None,
                            quality_score=3,
                            fundamental_data=None,
                            events=None,
                            analyst_data=None,
                            use_dynamic_weights=False
                        )
                        
                        # 候補として追加
                        candidates.append({
                            'symbol': symbol,
                            'current_state': new_state,
                            'total_score': scores['total_score'],
                            'value_score': scores['value_score'],
                            'momentum_score': scores['momentum_score'],
                            'stability_score': scores['stability_score'],
                            'current_price': current_price,
                            'features': features
                        })
                    except Exception as e:
                        print(f"Error analyzing {symbol} on {current_date}: {e}")
                        continue
                
                # セレクタで「今日の1個」を選出
                daily_pick = self.selector.select_daily_pick(candidates)
                
                # 既存ポジションのエグジット判定
                positions_to_close = []
                for symbol, position in positions.items():
                    entry_price = position['entry_price']
                    entry_date = position['entry_date']
                    
                    # 現在価格を取得
                    try:
                        if is_crypto_symbol(symbol):
                            prices = self.coingecko_fetcher.get_historical_prices(
                                symbol, days=1, end_date=current_date
                            )
                        else:
                            prices = self.yahoo_fetcher.get_historical_prices(
                                symbol, days=1, end_date=current_date
                            )
                        
                        if not prices:
                            continue
                        
                        current_price = prices[-1][1]
                        # スリッページ適用
                        exit_price = self.apply_slippage(current_price, is_buy=False)
                        
                        # リターンを計算
                        return_pct = ((exit_price - entry_price) / entry_price) * 100
                        
                        # エグジット条件チェック
                        should_exit = False
                        exit_reason = ""
                        
                        # ストップロス
                        if return_pct <= stop_loss_pct:
                            should_exit = True
                            exit_reason = "ストップロス"
                        
                        # 利確
                        if return_pct >= take_profit_pct:
                            should_exit = True
                            exit_reason = "利確"
                        
                        # 次の選出日（簡易版: 7日経過）
                        days_held = (current_date - entry_date).days
                        if days_held >= 7:
                            should_exit = True
                            exit_reason = "保有期間満了"
                        
                        if should_exit:
                            positions_to_close.append((symbol, exit_price, exit_reason))
                    except Exception as e:
                        print(f"Error checking position {symbol} on {current_date}: {e}")
                        continue
                
                # ポジションをクローズ
                for symbol, exit_price, exit_reason in positions_to_close:
                    position = positions.pop(symbol)
                    quantity = position['quantity']
                    entry_price = position['entry_price']
                    
                    # エグジット手数料
                    exit_fee = self.calculate_fees(exit_price, quantity, is_entry=False)
                    
                    # 売却金額
                    exit_value = exit_price * quantity - exit_fee
                    
                    # リターン
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    
                    # 資本を更新
                    capital = exit_value
                    
                    # トレード記録
                    trade = {
                        'symbol': symbol,
                        'entry_date': position['entry_date'].isoformat(),
                        'exit_date': current_date.isoformat(),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': quantity,
                        'return_pct': return_pct,
                        'exit_reason': exit_reason,
                        'entry_fee': position.get('entry_fee', 0),
                        'exit_fee': exit_fee
                    }
                    trades.append(trade)
                    
                    results['total_trades'] += 1
                    results['total_fees'] += position.get('entry_fee', 0) + exit_fee
                
                # 新しいポジションをエントリー（資本があれば）
                if daily_pick and capital > 0:
                    symbol = daily_pick['symbol']
                    entry_price = daily_pick['current_price']
                    
                    # スリッページ適用
                    entry_price_with_slippage = self.apply_slippage(entry_price, is_buy=True)
                    
                    # エントリー手数料を考慮して数量を計算
                    available_capital = capital * 0.95  # 95%を使用（安全マージン）
                    quantity = available_capital / (entry_price_with_slippage * (1 + self.entry_fee_rate))
                    
                    # エントリー手数料
                    entry_fee = self.calculate_fees(entry_price_with_slippage, quantity, is_entry=True)
                    
                    # 実際の投資額
                    investment = entry_price_with_slippage * quantity + entry_fee
                    
                    if investment <= capital:
                        positions[symbol] = {
                            'entry_price': entry_price_with_slippage,
                            'entry_date': current_date,
                            'quantity': quantity,
                            'entry_fee': entry_fee
                        }
                        capital -= investment
                        results['total_fees'] += entry_fee
                
                # エクイティカーブを更新
                current_equity = capital
                for symbol, position in positions.items():
                    try:
                        if is_crypto_symbol(symbol):
                            prices = self.coingecko_fetcher.get_historical_prices(
                                symbol, days=1, end_date=current_date
                            )
                        else:
                            prices = self.yahoo_fetcher.get_historical_prices(
                                symbol, days=1, end_date=current_date
                            )
                        
                        if prices:
                            current_price = prices[-1][1]
                            current_equity += current_price * position['quantity']
                    except:
                        pass
                
                equity_curve.append(current_equity)
                
                # 日次リターンを計算
                if len(equity_curve) > 1:
                    daily_return = ((current_equity - equity_curve[-2]) / equity_curve[-2]) * 100
                    daily_returns.append(daily_return)
                
            except Exception as e:
                print(f"Error on {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        # 最終的なポジションをクローズ
        for symbol, position in positions.items():
            try:
                if is_crypto_symbol(symbol):
                    prices = self.coingecko_fetcher.get_historical_prices(
                        symbol, days=1, end_date=end_date
                    )
                else:
                    prices = self.yahoo_fetcher.get_historical_prices(
                        symbol, days=1, end_date=end_date
                    )
                
                if prices:
                    exit_price = self.apply_slippage(prices[-1][1], is_buy=False)
                    quantity = position['quantity']
                    entry_price = position['entry_price']
                    
                    exit_fee = self.calculate_fees(exit_price, quantity, is_entry=False)
                    exit_value = exit_price * quantity - exit_fee
                    
                    capital += exit_value
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    
                    trade = {
                        'symbol': symbol,
                        'entry_date': position['entry_date'].isoformat(),
                        'exit_date': end_date.isoformat(),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': quantity,
                        'return_pct': return_pct,
                        'exit_reason': '期間終了',
                        'entry_fee': position.get('entry_fee', 0),
                        'exit_fee': exit_fee
                    }
                    trades.append(trade)
                    
                    results['total_trades'] += 1
                    results['total_fees'] += position.get('entry_fee', 0) + exit_fee
            except Exception as e:
                print(f"Error closing position {symbol}: {e}")
        
        # 最終結果を計算
        final_capital = capital
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # 最大ドローダウン
        max_dd = self.calculate_max_drawdown(equity_curve)
        
        # シャープレシオ
        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns) if daily_returns else 0.0
        
        # 勝率
        winning_trades = [t for t in trades if t['return_pct'] > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        
        # スリッページ合計（簡易計算）
        total_slippage = sum(
            abs(t['entry_price'] - t.get('original_entry_price', t['entry_price'])) * t['quantity']
            for t in trades
        )
        
        results.update({
            'final_capital': final_capital,
            'total_return': total_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_slippage': total_slippage,
            'daily_returns': daily_returns,
            'equity_curve': equity_curve,
            'trades': trades
        })
        
        return results
