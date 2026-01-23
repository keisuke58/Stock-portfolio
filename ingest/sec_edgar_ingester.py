"""
SEC EDGAR統合モジュール（L1拡張）
公式決算・財務諸表（10-K, 10-Q）を取得
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_registry import DataSourceRegistry, ReliabilityLevel
from validators import DataValidator


class SECEdgarIngester:
    """SEC EDGARから公式開示データを取得するクラス（L1拡張）"""
    
    # SEC EDGAR API ベースURL
    SEC_BASE_URL = "https://www.sec.gov"
    SEC_EDGAR_API = "https://data.sec.gov"
    
    def __init__(self):
        self.validator = DataValidator()
        # SEC EDGAR APIはUser-Agentヘッダーが必須
        self.headers = {
            'User-Agent': 'Investment Bot (contact@example.com)',  # TODO: 実際の連絡先に変更
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
    
    def get_company_filings(self, cik: str, filing_type: str = "10-K", limit: int = 5) -> List[Dict]:
        """
        SEC EDGARから会社の開示書類を取得
        
        Args:
            cik: SEC CIK（会社識別コード）
            filing_type: 開示タイプ（"10-K", "10-Q", "8-K"等）
            limit: 取得件数
        
        Returns:
            開示書類のリスト
        """
        if not cik:
            return []
        
        try:
            # CIKを10桁のゼロパディング形式に変換
            cik_padded = str(cik).zfill(10)
            
            # SEC EDGAR submissions API
            # 注意: 実際のAPIエンドポイントは変更される可能性がある
            # 公式ドキュメント: https://www.sec.gov/edgar/sec-api-documentation
            url = f"{self.SEC_EDGAR_API}/submissions/CIK{cik_padded}.json"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Warning: SEC EDGAR API returned status {response.status_code}")
                return []
            
            data = response.json()
            
            # 最新の開示書類をフィルタリング
            filings = data.get('filings', {}).get('recent', {})
            forms = filings.get('form', [])
            dates = filings.get('reportDate', [])
            descriptions = filings.get('description', [])
            accession_numbers = filings.get('accessionNumber', [])
            
            results = []
            for i, form in enumerate(forms):
                if form == filing_type and len(results) < limit:
                    filing_date = dates[i] if i < len(dates) else None
                    description = descriptions[i] if i < len(descriptions) else ''
                    accession = accession_numbers[i] if i < len(accession_numbers) else None
                    
                    results.append({
                        'form': form,
                        'filing_date': filing_date,
                        'description': description,
                        'accession_number': accession,
                        'url': self._build_filing_url(cik_padded, accession, form) if accession else None,
                        'data_sources': [
                            {
                                'name': 'SEC EDGAR',
                                'reliability': ReliabilityLevel.HIGH.value,
                                'url': DataSourceRegistry.format_source_url(
                                    DataSourceRegistry.FUNDAMENTAL_SOURCES[1],  # SEC EDGAR
                                    cik
                                ),
                                'timestamp': datetime.utcnow().isoformat()
                            }
                        ],
                        'data_timestamp': datetime.utcnow()
                    })
            
            return results
            
        except Exception as e:
            print(f"Error fetching SEC EDGAR filings for CIK {cik}: {e}")
            return []
    
    def _build_filing_url(self, cik: str, accession_number: str, form: str) -> str:
        """
        開示書類のURLを構築
        
        Args:
            cik: CIK（10桁ゼロパディング）
            accession_number: アクセッション番号（例: "0000950170-23-027789"）
            form: フォームタイプ（例: "10-K"）
        
        Returns:
            SEC EDGARのURL
        """
        # アクセッション番号からハイフンを削除
        accession_clean = accession_number.replace('-', '')
        # URL形式: https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession}&xbrl_type=v
        return f"{self.SEC_BASE_URL}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_clean}&xbrl_type=v"
    
    def get_recent_earnings_releases(self, cik: str, days: int = 90) -> List[Dict]:
        """
        最近の決算リリース（8-K）を取得
        
        Args:
            cik: SEC CIK
            days: 取得する日数
        
        Returns:
            決算リリースのリスト
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 8-K（重要イベント）を取得
        filings = self.get_company_filings(cik, filing_type="8-K", limit=20)
        
        # 日付でフィルタリング
        recent_filings = []
        for filing in filings:
            filing_date_str = filing.get('filing_date')
            if filing_date_str:
                try:
                    filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')
                    if filing_date >= cutoff_date:
                        recent_filings.append(filing)
                except ValueError:
                    continue
        
        return recent_filings
    
    def get_guidance_updates(self, cik: str) -> List[Dict]:
        """
        ガイダンス更新を取得（8-Kまたは10-Qから）
        
        Args:
            cik: SEC CIK
        
        Returns:
            ガイダンス更新のリスト
        """
        # 8-Kからガイダンス関連の開示を検索
        filings = self.get_company_filings(cik, filing_type="8-K", limit=10)
        
        guidance_updates = []
        for filing in filings:
            description = filing.get('description', '').lower()
            # ガイダンス関連のキーワードをチェック
            if any(keyword in description for keyword in ['guidance', 'outlook', 'forecast', 'earnings']):
                guidance_updates.append(filing)
        
        return guidance_updates
