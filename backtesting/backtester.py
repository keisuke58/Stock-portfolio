"""
バックテストモジュール
過去データで予測精度を検証
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import YahooFetcher, CoinGeckoFetcher
from features import FeatureCalculator
from scoring import VMSScorer
from state_machine import StateMachine
from signals import is_crypto_symbol
from cache import PriceCache


class Backtester:
    """バックテストクラス"""
    
    def __init__(self):
        """初期化"""
        self.cache = PriceCache()
        self.yahoo_fetcher = YahooFetcher(self.cache)
        self.coingecko_fetcher = CoinGeckoFetcher(self.cache)
        self.state_machine = StateMachine(self.yahoo_fetcher, self.coingecko_fetcher)
    
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
