"""
ティッカー解決モジュール
シンボル名（例: "A"）から正式な会社名（例: "Agilent Technologies"）を解決
"""
from typing import Optional, Dict
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_registry import DataSourceRegistry, ReliabilityLevel
from datetime import datetime


class TickerResolver:
    """ティッカーシンボルから会社情報を解決するクラス"""
    
    # よくある曖昧なティッカーの解決マッピング
    # 例: "A" は複数の会社に使われる可能性があるが、主要なものを優先
    COMMON_TICKER_MAPPING = {
        # 米国株の主要なティッカー
        'A': 'Agilent Technologies',
        'AA': 'Alcoa Corporation',
        'AAA': 'Listed as AAA but may be ambiguous',
        # 必要に応じて追加
    }
    
    def resolve_ticker(self, symbol: str) -> Dict:
        """
        ティッカーシンボルから会社情報を解決
        
        Args:
            symbol: ティッカーシンボル（例: "A", "AAPL"）
        
        Returns:
            会社情報の辞書:
            {
                'symbol': 'A',
                'company_name': 'Agilent Technologies Inc.',
                'long_name': 'Agilent Technologies, Inc.',
                'sector': 'Healthcare',
                'industry': 'Diagnostics & Research',
                'cik': '0001090872',  # SEC CIK（SEC EDGAR用）
                'data_sources': [...],
                'data_timestamp': ...
            }
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # 基本情報を取得
            company_name = info.get('longName') or info.get('shortName') or symbol
            long_name = info.get('longName', company_name)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # SEC CIKを取得（SEC EDGAR用）
            # yfinanceのinfoにはCIKが含まれていない場合があるので、
            # 別途取得が必要な場合は外部APIを使用
            cik = info.get('cik') or self._get_cik_from_symbol(symbol)
            
            resolved_data = {
                'symbol': symbol.upper(),
                'company_name': company_name,
                'long_name': long_name,
                'sector': sector,
                'industry': industry,
                'cik': cik,  # SEC EDGARで使用
                'market_cap': info.get('marketCap'),
                'website': info.get('website'),
                'data_sources': [
                    {
                        'name': 'Yahoo Finance Company Info',
                        'reliability': ReliabilityLevel.HIGH.value,
                        'url': DataSourceRegistry.format_source_url(
                            DataSourceRegistry.PRICE_SOURCES[0],
                            symbol
                        ),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                ],
                'data_timestamp': datetime.utcnow()
            }
            
            # よくある曖昧なティッカーの場合はマッピングを確認
            if symbol.upper() in self.COMMON_TICKER_MAPPING:
                expected_name = self.COMMON_TICKER_MAPPING[symbol.upper()]
                if expected_name.lower() not in company_name.lower():
                    resolved_data['note'] = f"Warning: Expected '{expected_name}' but got '{company_name}'"
            
            return resolved_data
            
        except Exception as e:
            print(f"Error resolving ticker {symbol}: {e}")
            return {
                'symbol': symbol.upper(),
                'company_name': symbol,  # フォールバック
                'error': str(e),
                'data_sources': [],
                'data_timestamp': datetime.utcnow()
            }
    
    def _get_cik_from_symbol(self, symbol: str) -> Optional[str]:
        """
        シンボルからSEC CIKを取得（簡易版）
        
        注意: 完全な実装にはSEC EDGAR APIまたはCIKマッピングDBが必要
        現時点ではNoneを返す（後で拡張可能）
        """
        # TODO: SEC EDGAR APIまたはCIKマッピングDBから取得
        # 例: https://www.sec.gov/cgi-bin/browse-edgar?CIK={symbol}&action=getcompany
        return None
    
    def is_valid_ticker(self, symbol: str) -> bool:
        """
        ティッカーが有効かどうかをチェック
        
        Args:
            symbol: ティッカーシンボル
        
        Returns:
            True if valid, False otherwise
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            # 基本的な情報が取得できれば有効とみなす
            return info is not None and len(info) > 0
        except Exception:
            return False
