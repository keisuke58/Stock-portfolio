"""
投資分析サービス
InvestmentAnalyzerをラップしてサービス化
"""
from typing import List, Dict, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from investment_analyzer import InvestmentAnalyzer


class AnalysisService:
    """投資分析サービス"""
    
    def __init__(self):
        """初期化"""
        self.analyzer = InvestmentAnalyzer()
    
    def calculate_investment_score(self, symbol: str) -> Optional[Dict]:
        """
        投資スコアを計算
        
        Args:
            symbol: シンボル名
        
        Returns:
            投資評価辞書
        """
        return self.analyzer.calculate_investment_score(symbol)
    
    def analyze_all_assets(
        self,
        symbols: List[str],
        max_assets: int = 200
    ) -> List[Dict]:
        """
        複数の資産を分析
        
        Args:
            symbols: シンボルのリスト
            max_assets: 最大分析数
        
        Returns:
            分析結果のリスト
        """
        return self.analyzer.analyze_all_assets(symbols, max_assets=max_assets)
    
    def get_comprehensive_financial_data(self, symbol: str) -> Optional[Dict]:
        """
        包括的な財務データを取得
        
        Args:
            symbol: シンボル名
        
        Returns:
            財務データ辞書
        """
        return self.analyzer.get_comprehensive_financial_data(symbol)
    
    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """
        会社情報を取得
        
        Args:
            symbol: シンボル名
        
        Returns:
            会社情報辞書
        """
        return self.analyzer.get_company_info(symbol)
    
    def get_analyst_recommendations(self, symbol: str) -> Optional[Dict]:
        """
        アナリスト推奨を取得
        
        Args:
            symbol: シンボル名
        
        Returns:
            アナリストデータ辞書
        """
        return self.analyzer.get_analyst_recommendations(symbol)
