"""
銘柄詳細データ取得サービス
個別銘柄の詳細データを取得する
"""
from typing import Dict, Optional
import logging
import time
from investment_analyzer import InvestmentAnalyzer
from signals import get_historical_prices, is_crypto_symbol

# ロガー設定
logger = logging.getLogger(__name__)


def get_symbol_detail_data(symbol: str, timeout: int = 60) -> Optional[Dict]:
    """個別銘柄の詳細データを取得（エラーハンドリング強化）
    
    Args:
        symbol: 銘柄シンボル
        timeout: タイムアウト（秒）
    
    Returns:
        銘柄詳細データの辞書、またはNone
    """
    if not symbol:
        logger.warning("シンボルが指定されていません")
        return None
    
    start_time = time.time()
    
    try:
        analyzer = InvestmentAnalyzer()
        
        # 基本スコアデータを取得
        try:
            score_data = analyzer.calculate_investment_score(symbol)
            if not score_data or not isinstance(score_data, dict):
                logger.warning(f"{symbol}: スコアデータが無効です")
                return None
        except TimeoutError:
            logger.error(f"{symbol}: スコア計算がタイムアウトしました")
            return None
        except ConnectionError as e:
            logger.error(f"{symbol}: 接続エラー - {e}")
            return None
        except Exception as e:
            logger.error(f"{symbol}: スコア計算エラー - {type(e).__name__}: {e}")
            return None
        
        # 財務データを追加（米国株の場合）
        if not is_crypto_symbol(symbol):
            try:
                financial_data = analyzer.get_comprehensive_financial_data(symbol)
                if financial_data:
                    score_data['financial_data'] = financial_data
                else:
                    logger.debug(f"{symbol}: 財務データが取得できませんでした")
            except TimeoutError:
                logger.warning(f"{symbol}: 財務データ取得がタイムアウトしました")
            except Exception as e:
                logger.warning(f"{symbol}: 財務データの取得に失敗 - {type(e).__name__}: {e}")
            
            # 会社情報を追加
            try:
                company_info = analyzer.get_company_info(symbol)
                if company_info:
                    score_data['company_info'] = company_info
            except Exception as e:
                logger.debug(f"{symbol}: 会社情報の取得に失敗 - {e}")
            
            # アナリスト推奨を追加
            try:
                analyst_data = analyzer.get_analyst_recommendations(symbol)
                if analyst_data:
                    score_data['analyst_data'] = analyst_data
            except Exception as e:
                logger.debug(f"{symbol}: アナリストデータの取得に失敗 - {e}")
        
        # 価格データを追加
        try:
            prices = get_historical_prices(symbol, days=365)
            if prices:
                score_data['historical_prices'] = prices
            else:
                score_data['historical_prices'] = []
                logger.debug(f"{symbol}: 価格データが取得できませんでした")
        except TimeoutError:
            logger.warning(f"{symbol}: 価格データ取得がタイムアウトしました")
            score_data['historical_prices'] = []
        except Exception as e:
            logger.warning(f"{symbol}: 価格データの取得に失敗 - {type(e).__name__}: {e}")
            score_data['historical_prices'] = []
        
        # タイムアウトチェック
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            logger.warning(f"{symbol}: 処理時間がタイムアウトを超過 ({elapsed_time:.1f}秒)")
        
        return score_data
        
    except Exception as e:
        logger.error(f"{symbol}: 予期しないエラー - {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
