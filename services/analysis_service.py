"""
投資分析データ取得サービス
InvestmentAnalyzerを使用して分析データを取得する
"""
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from investment_analyzer import InvestmentAnalyzer

# ロガー設定
logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """分析エラーのカスタム例外"""
    pass


def get_analysis_data(symbols: List[str], max_assets: int = 200, timeout: int = 300) -> List[Dict]:
    """投資分析データを取得（並列処理対応、エラーハンドリング強化）
    
    Args:
        symbols: 分析対象のシンボルリスト
        max_assets: 最大分析資産数
        timeout: タイムアウト（秒）
    
    Returns:
        分析結果のリスト
    """
    if not symbols:
        logger.warning("シンボルリストが空です")
        return []
    
    start_time = time.time()
    results = []
    errors = []
    
    try:
        analyzer = InvestmentAnalyzer()
        
        # 並列処理でデータ取得（最大10スレッド）
        def analyze_symbol(symbol: str) -> Optional[Dict]:
            """個別シンボルの分析（エラーハンドリング付き）"""
            try:
                result = analyzer.calculate_investment_score(symbol)
                if result and isinstance(result, dict):
                    return result
                else:
                    logger.debug(f"{symbol}: 分析結果が無効です")
                    return None
            except TimeoutError:
                logger.warning(f"{symbol}: タイムアウトエラー")
                errors.append(f"{symbol}: タイムアウト")
                return None
            except ConnectionError as e:
                logger.warning(f"{symbol}: 接続エラー - {e}")
                errors.append(f"{symbol}: 接続エラー")
                return None
            except ValueError as e:
                logger.warning(f"{symbol}: データ取得エラー - {e}")
                errors.append(f"{symbol}: データ取得エラー")
                return None
            except Exception as e:
                logger.error(f"{symbol}: 予期しないエラー - {type(e).__name__}: {e}")
                errors.append(f"{symbol}: {type(e).__name__}")
                return None
        
        # 並列処理実行
        symbols_to_analyze = symbols[:max_assets]
        max_workers = min(10, len(symbols_to_analyze), 10)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(analyze_symbol, symbol): symbol 
                for symbol in symbols_to_analyze
            }
            
            completed = 0
            for future in as_completed(future_to_symbol):
                # タイムアウトチェック
                if time.time() - start_time > timeout:
                    logger.warning(f"タイムアウト: {timeout}秒経過")
                    break
                
                try:
                    result = future.result(timeout=30)  # 個別タイムアウト30秒
                    if result:
                        results.append(result)
                    completed += 1
                except Exception as e:
                    symbol = future_to_symbol[future]
                    logger.error(f"{symbol}: フューチャーエラー - {e}")
                    errors.append(f"{symbol}: 処理エラー")
        
        elapsed_time = time.time() - start_time
        logger.info(f"分析完了: {len(results)}/{len(symbols_to_analyze)} 成功, "
                   f"エラー: {len(errors)}, 経過時間: {elapsed_time:.1f}秒")
        
        if errors and len(errors) <= 10:
            logger.debug(f"エラー詳細: {', '.join(errors)}")
        
        return results
        
    except Exception as e:
        logger.error(f"データ取得エラー: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # フォールバック: 通常の方法で取得（シリアル処理）
        try:
            logger.info("フォールバックモード: シリアル処理で再試行")
            analyzer = InvestmentAnalyzer()
            fallback_results = []
            for symbol in symbols[:min(max_assets, 50)]:  # フォールバック時は50件まで
                try:
                    result = analyzer.calculate_investment_score(symbol)
                    if result:
                        fallback_results.append(result)
                except:
                    continue
            return fallback_results
        except Exception as fallback_error:
            logger.error(f"フォールバックも失敗: {fallback_error}")
            return []
