"""
SQLiteベースの状態管理モジュール
急落→低迷→反転の状態遷移を追跡
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Tuple


class StateStore:
    """資産の状態（WATCH/BASE/BUY）をSQLiteで管理"""
    
    STATES = ['NORMAL', 'WATCH', 'BASE', 'BUY']
    
    def __init__(self, db_path: str = 'asset_state.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_state (
                symbol TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                state_since TEXT NOT NULL,
                last_price REAL,
                last_notified_state TEXT,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_state(self, symbol: str) -> Optional[str]:
        """現在の状態を取得（なければNone）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT state FROM asset_state WHERE symbol = ?',
            (symbol,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_state(self, symbol: str, state: str, price: float) -> bool:
        """
        状態を更新
        戻り値: 状態が変化したかどうか（True=変化あり、False=変化なし）
        """
        if state not in self.STATES:
            raise ValueError(f"Invalid state: {state}. Must be one of {self.STATES}")
        
        old_state = self.get_state(symbol)
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if old_state is None:
            # 新規登録
            cursor.execute('''
                INSERT INTO asset_state 
                (symbol, state, state_since, last_price, last_notified_state, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, state, now, price, None, now))
            conn.commit()
            conn.close()
            return True  # 新規なので「変化」とみなす
        
        if old_state == state:
            # 状態が同じ場合は更新時刻と価格だけ更新
            cursor.execute('''
                UPDATE asset_state 
                SET last_price = ?, updated_at = ?
                WHERE symbol = ?
            ''', (price, now, symbol))
            conn.commit()
            conn.close()
            return False  # 変化なし
        
        # 状態が変化した
        cursor.execute('''
            UPDATE asset_state 
            SET state = ?, state_since = ?, last_price = ?, updated_at = ?
            WHERE symbol = ?
        ''', (state, now, price, now, symbol))
        conn.commit()
        conn.close()
        return True  # 変化あり
    
    def should_notify(self, symbol: str, new_state: str) -> bool:
        """
        通知すべきかどうか（状態変化時のみ通知）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT last_notified_state FROM asset_state WHERE symbol = ?',
            (symbol,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[0] != new_state:
            return True
        return False
    
    def mark_notified(self, symbol: str, state: str):
        """通知済みフラグを更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE asset_state 
            SET last_notified_state = ?
            WHERE symbol = ?
        ''', (state, symbol))
        conn.commit()
        conn.close()
    
    def get_state_info(self, symbol: str) -> Optional[dict]:
        """状態情報を辞書で取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT state, state_since, last_price, last_notified_state, updated_at
            FROM asset_state WHERE symbol = ?
        ''', (symbol,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            'state': result[0],
            'state_since': result[1],
            'last_price': result[2],
            'last_notified_state': result[3],
            'updated_at': result[4]
        }
