"""
SQLiteベースの価格キャッシュ
レート制限回避のため、TTL付きキャッシュを提供
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
import os


class PriceCache:
    """価格データのキャッシュ管理（TTL付き）"""
    
    def __init__(self, db_path: str = 'cache/price_cache.db'):
        """キャッシュDBを初期化"""
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 価格キャッシュテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT NOT NULL,
                cache_type TEXT NOT NULL,  -- 'current', 'historical', 'metrics'
                data TEXT NOT NULL,  -- JSON形式
                cached_at TEXT NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                PRIMARY KEY (symbol, cache_type)
            )
        ''')
        
        # インデックス作成
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_type 
            ON price_cache(symbol, cache_type)
        ''')
        
        conn.commit()
        conn.close()
    
    def _is_expired(self, cached_at: str, ttl_seconds: int) -> bool:
        """キャッシュが期限切れかどうかを判定"""
        try:
            cached_time = datetime.fromisoformat(cached_at)
            expiry_time = cached_time + timedelta(seconds=ttl_seconds)
            return datetime.utcnow() > expiry_time
        except (ValueError, TypeError) as e:
            # Parse error - treat as expired
            return True
    
    def get(self, symbol: str, cache_type: str = 'current') -> Optional[Dict]:
        """
        キャッシュからデータを取得
        戻り値: キャッシュがあって有効な場合はデータ、なければNone
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data, cached_at, ttl_seconds
            FROM price_cache
            WHERE symbol = ? AND cache_type = ?
        ''', (symbol, cache_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        data_json, cached_at, ttl_seconds = result
        
        # 期限切れチェック
        if self._is_expired(cached_at, ttl_seconds):
            # 期限切れの場合は削除
            self.delete(symbol, cache_type)
            return None
        
        # JSONをパースして返す
        try:
            return json.loads(data_json)
        except (json.JSONDecodeError, TypeError) as e:
            # Invalid JSON data - return None
            return None
    
    def set(self, symbol: str, data: Dict, cache_type: str = 'current', ttl_seconds: int = 3600):
        """
        キャッシュにデータを保存
        ttl_seconds: デフォルト1時間（3600秒）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data_json = json.dumps(data)
        cached_at = datetime.utcnow().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO price_cache 
            (symbol, cache_type, data, cached_at, ttl_seconds)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, cache_type, data_json, cached_at, ttl_seconds))
        
        conn.commit()
        conn.close()
    
    def delete(self, symbol: str, cache_type: str = 'current'):
        """キャッシュを削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM price_cache
            WHERE symbol = ? AND cache_type = ?
        ''', (symbol, cache_type))
        
        conn.commit()
        conn.close()
    
    def clear_expired(self):
        """期限切れのキャッシュを一括削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, cache_type, cached_at, ttl_seconds
            FROM price_cache
        ''')
        
        results = cursor.fetchall()
        deleted_count = 0
        
        for symbol, cache_type, cached_at, ttl_seconds in results:
            if self._is_expired(cached_at, ttl_seconds):
                cursor.execute('''
                    DELETE FROM price_cache
                    WHERE symbol = ? AND cache_type = ?
                ''', (symbol, cache_type))
                deleted_count += 1
        
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """現在価格をキャッシュから取得（簡易アクセス）"""
        cached = self.get(symbol, 'current')
        if cached and 'price' in cached:
            return cached['price']
        return None
    
    def set_current_price(self, symbol: str, price: float, ttl_seconds: int = 3600):
        """現在価格をキャッシュに保存（簡易アクセス）"""
        self.set(symbol, {'price': price, 'timestamp': datetime.utcnow().isoformat()}, 
                 'current', ttl_seconds)
    
    def get_historical_prices(self, symbol: str) -> Optional[List[Tuple[datetime, float]]]:
        """履歴価格をキャッシュから取得"""
        cached = self.get(symbol, 'historical')
        if cached and 'prices' in cached:
            # JSONから復元
            prices = []
            for dt_str, price in cached['prices']:
                prices.append((datetime.fromisoformat(dt_str), price))
            return prices
        return None
    
    def set_historical_prices(self, symbol: str, prices: List[Tuple[datetime, float]], 
                             ttl_seconds: int = 86400):
        """履歴価格をキャッシュに保存（デフォルト24時間）"""
        # datetimeを文字列に変換
        prices_json = [(dt.isoformat(), price) for dt, price in prices]
        self.set(symbol, {'prices': prices_json, 'timestamp': datetime.utcnow().isoformat()}, 
                 'historical', ttl_seconds)
