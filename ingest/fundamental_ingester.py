"""
財務データ取得モジュール（L1: ファンダ）
yfinanceを拡張してFCF、売上成長、利益率、財務健全性を取得
"""
from typing import Optional, Dict, List
from datetime import datetime
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_registry import DataSourceRegistry, ReliabilityLevel
from validators import DataValidator


class FundamentalIngester:
    """財務データを取得するクラス（L1レイヤー）"""
    
    def __init__(self):
        self.validator = DataValidator()
    
    def get_fundamental_data(self, symbol: str) -> Dict:
        """
        財務データを取得（優先順位1-3のデータ）
        
        優先順位:
        1. 決算・ガイダンス（公式）
        2. バリュ指標（FCF, 売上成長, 利益率）
        3. 財務健全性（負債、利払い、流動比率）
        
        Returns:
            財務データの辞書（根拠リンク付き）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # 基本財務指標
            fundamental_data = {
                # バリュ指標
                'fcf': info.get('freeCashflow'),  # フリーキャッシュフロー
                'revenue_growth': info.get('revenueGrowth'),  # 売上成長率
                'profit_margin': info.get('profitMargins'),  # 利益率
                'operating_margin': info.get('operatingMargins'),  # 営業利益率
                'roe': info.get('returnOnEquity'),  # ROE
                'roa': info.get('returnOnAssets'),  # ROA
                
                # 財務健全性
                'total_debt': info.get('totalDebt'),  # 総負債
                'debt_to_equity': info.get('debtToEquity'),  # 負債資本比率
                'current_ratio': info.get('currentRatio'),  # 流動比率
                'quick_ratio': info.get('quickRatio'),  # 当座比率
                'interest_coverage': None,  # 利払い能力（計算が必要）
                
                # 既存指標（拡張）
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'dividend_yield': info.get('dividendYield'),
                
                # 成長指標
                'earnings_growth': info.get('earningsGrowth'),  # 利益成長率
                'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth'),  # 四半期利益成長率
                
                # データソース情報
                'data_sources': [
                    {
                        'name': 'Yahoo Finance Fundamentals',
                        'reliability': ReliabilityLevel.HIGH.value,
                        'url': DataSourceRegistry.format_source_url(
                            DataSourceRegistry.FUNDAMENTAL_SOURCES[0],
                            symbol
                        ),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                ],
                'data_timestamp': datetime.utcnow()
            }
            
            # 利払い能力を計算（EBIT / Interest Expense）
            ebit = info.get('ebit')
            interest_expense = info.get('interestExpense')
            if ebit and interest_expense and interest_expense > 0:
                fundamental_data['interest_coverage'] = ebit / interest_expense
            
            # 検証（L1データ用の検証を追加）
            fundamental_data = self.validator.validate_fundamental_data(fundamental_data, symbol)
            
            # 財務スコアを計算（簡易版）
            fundamental_data['financial_health_score'] = self._calculate_financial_health_score(
                fundamental_data
            )
            
            return fundamental_data
            
        except Exception as e:
            print(f"Error fetching fundamental data for {symbol}: {e}")
            return {
                'data_sources': [],
                'data_timestamp': datetime.utcnow(),
                'error': str(e)
            }
    
    def _calculate_financial_health_score(self, data: Dict) -> float:
        """
        財務健全性スコアを計算（0-100点）
        
        評価項目:
        - 負債資本比率（低いほど良い）
        - 流動比率（高いほど良い）
        - 利払い能力（高いほど良い）
        - 利益率（高いほど良い）
        """
        score = 50.0  # ベーススコア
        
        # 負債資本比率（< 0.5が理想）
        debt_to_equity = data.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity < 0.5:
                score += 15
            elif debt_to_equity < 1.0:
                score += 10
            elif debt_to_equity < 2.0:
                score += 5
            else:
                score -= 10
        
        # 流動比率（> 1.5が理想）
        current_ratio = data.get('current_ratio')
        if current_ratio is not None:
            if current_ratio > 2.0:
                score += 15
            elif current_ratio > 1.5:
                score += 10
            elif current_ratio > 1.0:
                score += 5
            else:
                score -= 10
        
        # 利払い能力（> 5が理想）
        interest_coverage = data.get('interest_coverage')
        if interest_coverage is not None:
            if interest_coverage > 10:
                score += 15
            elif interest_coverage > 5:
                score += 10
            elif interest_coverage > 2:
                score += 5
            else:
                score -= 15
        
        # 利益率（> 0.1が理想）
        profit_margin = data.get('profit_margin')
        if profit_margin is not None:
            if profit_margin > 0.2:
                score += 15
            elif profit_margin > 0.1:
                score += 10
            elif profit_margin > 0.05:
                score += 5
            else:
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def get_analyst_data(self, symbol: str) -> Dict:
        """
        アナリストデータを取得（優先順位4）
        
        Returns:
            アナリスト改定・EPS推移の辞書
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            analyst_data = {
                'target_price': info.get('targetMeanPrice'),  # 目標株価
                'target_high': info.get('targetHighPrice'),
                'target_low': info.get('targetLowPrice'),
                'recommendation': info.get('recommendationKey'),  # buy/hold/sell
                'number_of_analysts': info.get('numberOfAnalystOpinions'),
                
                # EPS推移
                'eps_current': info.get('trailingEps'),
                'eps_forward': info.get('forwardEps'),
                'eps_growth': None,  # 計算が必要
                
                # データソース情報
                'data_sources': [
                    {
                        'name': 'Yahoo Finance Analyst',
                        'reliability': ReliabilityLevel.HIGH.value,
                        'url': DataSourceRegistry.format_source_url(
                            DataSourceRegistry.FUNDAMENTAL_SOURCES[0],
                            symbol
                        ),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                ],
                'data_timestamp': datetime.utcnow()
            }
            
            # EPS成長率を計算
            eps_current = analyst_data.get('eps_current')
            eps_forward = analyst_data.get('eps_forward')
            if eps_current and eps_forward and eps_current > 0:
                analyst_data['eps_growth'] = (eps_forward - eps_current) / abs(eps_current)
            
            # 検証
            analyst_data = self.validator.validate_analyst_data(analyst_data, symbol)
            
            return analyst_data
            
        except Exception as e:
            print(f"Error fetching analyst data for {symbol}: {e}")
            return {
                'data_sources': [],
                'data_timestamp': datetime.utcnow(),
                'error': str(e)
            }
