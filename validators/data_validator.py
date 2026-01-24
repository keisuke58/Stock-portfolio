"""
データ検証モジュール
時系列整合性チェック、異常値検出、データ品質スコアを含む
"""
import logging
import math
import statistics
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataValidator:
    """データ検証を行うクラス"""
    
    @staticmethod
    def validate_dividend_yield(dividend_yield: Optional[float], symbol: str) -> float:
        """
        配当利回りを検証・修正
        - 0〜0.10（10%）の範囲外なら0に丸め、warningログ
        
        Args:
            dividend_yield: 配当利回り（小数形式、例: 0.02 = 2%）
            symbol: シンボル名
            
        Returns:
            検証済みの配当利回り（0.0〜0.10の範囲、または0.0）
        """
        if dividend_yield is None:
            return 0.0
        
        # NaNチェック
        if math.isnan(dividend_yield):
            logger.warning(f"[{symbol}] dividend_yield is NaN, setting to 0.0")
            return 0.0
        
        # 範囲チェック（0〜0.10 = 0%〜10%）
        if dividend_yield < 0.0 or dividend_yield > 0.10:
            logger.warning(
                f"[{symbol}] dividend_yield {dividend_yield:.4f} ({dividend_yield*100:.2f}%) "
                f"is out of valid range [0.0, 0.10], setting to 0.0"
            )
            return 0.0
        
        return dividend_yield
    
    @staticmethod
    def validate_price(price: Optional[float], symbol: str) -> Tuple[bool, Optional[float]]:
        """
        価格を検証
        - NaN/<=0はその銘柄を除外（Falseを返す）
        
        Args:
            price: 価格
            symbol: シンボル名
            
        Returns:
            (is_valid, validated_price)
            - is_valid: True=有効、False=無効（銘柄を除外すべき）
            - validated_price: 検証済みの価格（Noneの場合は無効）
        """
        if price is None:
            logger.warning(f"[{symbol}] price is None, excluding symbol")
            return (False, None)
        
        # NaNチェック
        if math.isnan(price):
            logger.warning(f"[{symbol}] price is NaN, excluding symbol")
            return (False, None)
        
        # 0以下チェック
        if price <= 0:
            logger.warning(f"[{symbol}] price {price} is <= 0, excluding symbol")
            return (False, None)
        
        return (True, price)
    
    @staticmethod
    def validate_metrics(metrics: Dict, symbol: str) -> Dict:
        """
        財務指標を検証・修正
        
        Args:
            metrics: 財務指標の辞書
            symbol: シンボル名
            
        Returns:
            検証済みの財務指標の辞書
        """
        validated_metrics = metrics.copy()
        
        # 配当利回りを検証
        if 'dividend_yield' in validated_metrics:
            validated_metrics['dividend_yield'] = DataValidator.validate_dividend_yield(
                validated_metrics.get('dividend_yield'),
                symbol
            )
        
        return validated_metrics
    
    @staticmethod
    def validate_fundamental_data(fundamental_data: Dict, symbol: str) -> Dict:
        """
        L1データ（財務指標）を検証・修正
        
        Args:
            fundamental_data: 財務データの辞書
            symbol: シンボル名
        
        Returns:
            検証済みの財務データの辞書
        """
        validated = fundamental_data.copy()
        
        # FCF（フリーキャッシュフロー）の検証
        fcf = validated.get('fcf')
        if fcf is not None:
            if math.isnan(fcf) or math.isinf(fcf):
                logger.warning(f"[{symbol}] FCF is NaN/Inf, setting to None")
                validated['fcf'] = None
        
        # 売上成長率の検証（-1.0 〜 10.0 の範囲）
        revenue_growth = validated.get('revenue_growth')
        if revenue_growth is not None:
            if math.isnan(revenue_growth) or math.isinf(revenue_growth):
                logger.warning(f"[{symbol}] revenue_growth is NaN/Inf, setting to None")
                validated['revenue_growth'] = None
            elif revenue_growth < -1.0 or revenue_growth > 10.0:
                logger.warning(
                    f"[{symbol}] revenue_growth {revenue_growth:.2%} is out of valid range "
                    f"[-100%, 1000%], setting to None"
                )
                validated['revenue_growth'] = None
        
        # 利益率の検証（-1.0 〜 1.0 の範囲）
        profit_margin = validated.get('profit_margin')
        if profit_margin is not None:
            if math.isnan(profit_margin) or math.isinf(profit_margin):
                logger.warning(f"[{symbol}] profit_margin is NaN/Inf, setting to None")
                validated['profit_margin'] = None
            elif profit_margin < -1.0 or profit_margin > 1.0:
                logger.warning(
                    f"[{symbol}] profit_margin {profit_margin:.2%} is out of valid range "
                    f"[-100%, 100%], setting to None"
                )
                validated['profit_margin'] = None
        
        # 負債資本比率の検証（0 〜 200 の範囲に拡張、一部の企業は100超もあり得る）
        debt_to_equity = validated.get('debt_to_equity')
        if debt_to_equity is not None:
            if math.isnan(debt_to_equity) or math.isinf(debt_to_equity):
                logger.warning(f"[{symbol}] debt_to_equity is NaN/Inf, setting to None")
                validated['debt_to_equity'] = None
            elif debt_to_equity < 0 or debt_to_equity > 200:
                logger.warning(
                    f"[{symbol}] debt_to_equity {debt_to_equity:.2f} is out of valid range "
                    f"[0, 200], setting to None"
                )
                validated['debt_to_equity'] = None
        
        # 流動比率の検証（0 〜 50 の範囲）
        current_ratio = validated.get('current_ratio')
        if current_ratio is not None:
            if math.isnan(current_ratio) or math.isinf(current_ratio):
                logger.warning(f"[{symbol}] current_ratio is NaN/Inf, setting to None")
                validated['current_ratio'] = None
            elif current_ratio < 0 or current_ratio > 50:
                logger.warning(
                    f"[{symbol}] current_ratio {current_ratio:.2f} is out of valid range "
                    f"[0, 50], setting to None"
                )
                validated['current_ratio'] = None
        
        return validated
    
    @staticmethod
    def validate_analyst_data(analyst_data: Dict, symbol: str) -> Dict:
        """
        アナリストデータを検証・修正
        
        Args:
            analyst_data: アナリストデータの辞書
            symbol: シンボル名
        
        Returns:
            検証済みのアナリストデータの辞書
        """
        validated = analyst_data.copy()
        
        # 目標株価の検証
        target_price = validated.get('target_price')
        if target_price is not None:
            if math.isnan(target_price) or math.isinf(target_price) or target_price <= 0:
                logger.warning(f"[{symbol}] target_price is invalid, setting to None")
                validated['target_price'] = None
        
        # EPS成長率の検証（-10.0 〜 10.0 の範囲）
        eps_growth = validated.get('eps_growth')
        if eps_growth is not None:
            if math.isnan(eps_growth) or math.isinf(eps_growth):
                logger.warning(f"[{symbol}] eps_growth is NaN/Inf, setting to None")
                validated['eps_growth'] = None
            elif eps_growth < -10.0 or eps_growth > 10.0:
                logger.warning(
                    f"[{symbol}] eps_growth {eps_growth:.2%} is out of valid range "
                    f"[-1000%, 1000%], setting to None"
                )
                validated['eps_growth'] = None
        
        return validated
    
    @staticmethod
    def add_data_timestamp(data: Dict, timestamp: Optional[datetime] = None) -> Dict:
        """
        データに取得時刻（data_timestamp）を追加
        
        Args:
            data: データの辞書
            timestamp: 取得時刻（Noneの場合は現在時刻）
            
        Returns:
            data_timestampを追加したデータの辞書
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        data['data_timestamp'] = timestamp
        return data
    
    @staticmethod
    def check_time_series_consistency(prices: List[Tuple[datetime, float]], symbol: str) -> Tuple[bool, Optional[str]]:
        """
        時系列整合性チェック（価格が急激に変動していないか）
        
        Args:
            prices: 価格データのリスト [(datetime, price), ...]
            symbol: シンボル名
        
        Returns:
            (is_consistent, reason)
            - is_consistent: True=整合性あり、False=整合性なし
            - reason: 理由（整合性がない場合）
        """
        if not prices or len(prices) < 2:
            return (True, None)
        
        price_values = [p[1] for p in prices if p[1] is not None and p[1] > 0]
        
        if len(price_values) < 2:
            return (True, None)
        
        # 日次リターンを計算
        returns = []
        for i in range(1, len(price_values)):
            if price_values[i-1] > 0:
                daily_return = abs((price_values[i] - price_values[i-1]) / price_values[i-1])
                returns.append(daily_return)
        
        if not returns:
            return (True, None)
        
        # 異常値検出: 3シグマルール
        if len(returns) >= 3:
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0
            
            if std_return > 0:
                # 3シグマを超える変動があるかチェック
                threshold = mean_return + 3 * std_return
                extreme_returns = [r for r in returns if r > threshold]
                
                if extreme_returns:
                    max_extreme = max(extreme_returns)
                    return (False, f"異常な価格変動検出: 日次リターン{max_extreme:.1%}が3シグマ({threshold:.1%})を超過")
        
        # 50%以上の急激な変動をチェック
        extreme_changes = [r for r in returns if r > 0.5]
        if extreme_changes:
            max_change = max(extreme_changes)
            return (False, f"異常な価格変動検出: 日次リターン{max_change:.1%}が50%を超過")
        
        return (True, None)
    
    @staticmethod
    def detect_outliers(values: List[float], method: str = 'iqr') -> List[int]:
        """
        異常値検出（統計的手法）
        
        Args:
            values: 値のリスト
            method: 検出方法（'iqr'=四分位範囲、'zscore'=Zスコア）
        
        Returns:
            異常値のインデックスのリスト
        """
        if not values or len(values) < 3:
            return []
        
        outliers = []
        
        if method == 'iqr':
            # 四分位範囲（IQR）法
            sorted_values = sorted(values)
            q1_index = len(sorted_values) // 4
            q3_index = 3 * len(sorted_values) // 4
            
            if q3_index > q1_index:
                q1 = sorted_values[q1_index]
                q3 = sorted_values[q3_index]
                iqr = q3 - q1
                
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                for i, value in enumerate(values):
                    if value < lower_bound or value > upper_bound:
                        outliers.append(i)
        
        elif method == 'zscore':
            # Zスコア法
            mean_value = statistics.mean(values)
            std_value = statistics.stdev(values) if len(values) > 1 else 0
            
            if std_value > 0:
                for i, value in enumerate(values):
                    z_score = abs((value - mean_value) / std_value)
                    if z_score > 3:  # 3シグマルール
                        outliers.append(i)
        
        return outliers
    
    @staticmethod
    def calculate_data_quality_score(
        data: Dict,
        data_sources: Optional[List[Dict]] = None,
        data_timestamp: Optional[datetime] = None
    ) -> float:
        """
        データ品質スコアを計算（0-100点）
        
        Args:
            data: データの辞書
            data_sources: データソースのリスト
            data_timestamp: データ取得時刻
        
        Returns:
            データ品質スコア（0-100点）
        """
        score = 100.0
        
        # データ完全性スコア（欠損値チェック）
        completeness_score = DataValidator._calculate_completeness_score(data)
        score = min(score, completeness_score)
        
        # データ鮮度スコア
        freshness_score = DataValidator._calculate_freshness_score(data_timestamp)
        score = min(score, freshness_score)
        
        # データソース信頼度スコア
        if data_sources:
            reliability_score = DataValidator._calculate_reliability_score(data_sources)
            score = min(score, reliability_score)
        
        return max(0.0, score)
    
    @staticmethod
    def _calculate_completeness_score(data: Dict) -> float:
        """
        データ完全性スコアを計算（0-100点）
        
        Args:
            data: データの辞書
        
        Returns:
            完全性スコア
        """
        if not data:
            return 0.0
        
        # 重要なフィールドのリスト
        important_fields = [
            'current_price', 'ath_ratio', 'return_30d', 'volatility',
            'pe_ratio', 'fcf', 'revenue_growth', 'profit_margin'
        ]
        
        available_fields = sum(1 for field in important_fields if data.get(field) is not None)
        total_fields = len(important_fields)
        
        if total_fields == 0:
            return 100.0
        
        completeness = (available_fields / total_fields) * 100.0
        return completeness
    
    @staticmethod
    def _calculate_freshness_score(data_timestamp: Optional[datetime]) -> float:
        """
        データ鮮度スコアを計算（0-100点）
        
        Args:
            data_timestamp: データ取得時刻
        
        Returns:
            鮮度スコア
        """
        if data_timestamp is None:
            return 50.0  # タイムスタンプがない場合は中間スコア
        
        now = datetime.utcnow()
        age_hours = (now - data_timestamp).total_seconds() / 3600
        
        # 24時間以内: 100点
        # 48時間以内: 80点
        # 72時間以内: 60点
        # 1週間以内: 40点
        # それ以上: 20点
        if age_hours <= 24:
            return 100.0
        elif age_hours <= 48:
            return 80.0
        elif age_hours <= 72:
            return 60.0
        elif age_hours <= 168:  # 1週間
            return 40.0
        else:
            return 20.0
    
    @staticmethod
    def _calculate_reliability_score(data_sources: List[Dict]) -> float:
        """
        データソース信頼度スコアを計算（0-100点）
        
        Args:
            data_sources: データソースのリスト
        
        Returns:
            信頼度スコア
        """
        if not data_sources:
            return 50.0  # データソース情報がない場合は中間スコア
        
        # 信頼度レベルの重み
        reliability_weights = {
            'HIGH': 1.0,
            'MID': 0.7,
            'SPEC': 0.5,
            'LOW': 0.3
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for source in data_sources:
            reliability = source.get('reliability', 'MID')
            weight = reliability_weights.get(reliability, 0.5)
            total_score += weight * 100.0
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        return total_score / total_weight
    
    @staticmethod
    def cross_validate_sources(
        price_data: Optional[float],
        fundamental_data: Optional[Dict],
        symbol: str
    ) -> Tuple[bool, Optional[str]]:
        """
        データソース間のクロスチェック
        
        Args:
            price_data: 価格データ
            fundamental_data: 財務データ
            symbol: シンボル名
        
        Returns:
            (is_consistent, reason)
        """
        if price_data is None or fundamental_data is None:
            return (True, None)
        
        # 価格データと財務データの整合性チェック
        # 例: 時価総額が価格と発行済み株式数から計算できるか
        market_cap_from_price = fundamental_data.get('market_cap')
        shares_outstanding = fundamental_data.get('shares_outstanding')
        
        if market_cap_from_price and shares_outstanding and price_data:
            calculated_market_cap = price_data * shares_outstanding
            ratio = calculated_market_cap / market_cap_from_price if market_cap_from_price > 0 else 1.0
            
            # 10%以上の差異がある場合は警告
            if abs(ratio - 1.0) > 0.1:
                return (False, f"時価総額の不一致: 計算値${calculated_market_cap:,.0f} vs 報告値${market_cap_from_price:,.0f}")
        
        return (True, None)
