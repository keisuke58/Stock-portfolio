"""
ニュース・開示データ取得モジュール（L3: ニュース/開示）
yfinanceからニュースを取得（LLM処理は別モジュールで）
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_registry import DataSourceRegistry, ReliabilityLevel


class NewsIngester:
    """ニュース・開示データを取得するクラス（L3レイヤー）"""
    
    def get_recent_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        最近のニュースを取得
        
        Args:
            symbol: シンボル名
            days: 取得する日数
        
        Returns:
            ニュース記事のリスト（LLM処理前の生データ）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            news = ticker.news
            
            if not news:
                return []
            
            # 日付フィルタリング（簡易版）
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_news = []
            
            for item in news:
                # タイムスタンプを取得
                pub_time = item.get('providerPublishTime', 0)
                if pub_time:
                    pub_date = datetime.fromtimestamp(pub_time)
                    if pub_date >= cutoff_date:
                        recent_news.append({
                            'title': item.get('title', ''),
                            'publisher': item.get('publisher', ''),
                            'link': item.get('link', ''),
                            'published_time': pub_date.isoformat(),
                            'uuid': item.get('uuid', ''),
                            'raw_data': item  # LLM処理用に生データも保持
                        })
            
            return recent_news
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []
    
    def get_earnings_calendar(self, symbol: str) -> Optional[Dict]:
        """
        決算カレンダーを取得
        
        Returns:
            決算予定日の情報
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            calendar = ticker.calendar
            
            if calendar is None:
                return None
            
            # DataFrameかdictかをチェック
            import pandas as pd
            next_earnings = None
            calendar_data = {}
            
            if isinstance(calendar, pd.DataFrame):
                if calendar.empty:
                    return None
                # DataFrameの場合
                if 'Earnings Date' in calendar.index:
                    earnings_dates = calendar.loc['Earnings Date']
                    if len(earnings_dates) > 0:
                        next_earnings = str(earnings_dates.iloc[0])
                calendar_data = calendar.to_dict()
            elif isinstance(calendar, dict):
                # dictの場合
                next_earnings = calendar.get('Earnings Date')
                if next_earnings:
                    # リストの場合は最初の要素を取得
                    if isinstance(next_earnings, list) and len(next_earnings) > 0:
                        next_earnings = str(next_earnings[0])
                    else:
                        next_earnings = str(next_earnings)
                calendar_data = calendar
            else:
                return None
            
            return {
                'next_earnings_date': next_earnings,
                'calendar_data': calendar_data,
                'data_sources': [
                    {
                        'name': 'Yahoo Finance Calendar',
                        'reliability': ReliabilityLevel.HIGH.value,
                        'url': DataSourceRegistry.format_source_url(
                            DataSourceRegistry.NEWS_SOURCES[0],
                            symbol
                        ),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                ],
                'data_timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Error fetching earnings calendar for {symbol}: {e}")
            return None
