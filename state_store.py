"""
SQLiteベースの状態管理モジュール
急落→低迷→反転の状態遷移を追跡

Thread-safe implementation with context managers.
"""
import sqlite3
import threading
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class StateStore:
    """資産の状態（WATCH/BASE/BUY）をSQLiteで管理（スレッドセーフ）"""

    STATES = ['NORMAL', 'WATCH', 'BASE', 'BUY']

    def __init__(self, db_path: str = 'asset_state.db'):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.
        Ensures connections are properly closed even on exceptions.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """データベースとテーブルを初期化"""
        with self._get_connection() as conn:
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

    def get_state(self, symbol: str) -> Optional[str]:
        """現在の状態を取得（なければNone）"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT state FROM asset_state WHERE symbol = ?',
                    (symbol,)
                )
                result = cursor.fetchone()
                return result[0] if result else None

    def set_state(self, symbol: str, state: str, price: float) -> bool:
        """
        状態を更新（スレッドセーフ）

        Args:
            symbol: Asset symbol
            state: New state (must be one of STATES)
            price: Current price

        Returns:
            True if state changed, False if unchanged

        Raises:
            ValueError: If state is not valid
        """
        if state not in self.STATES:
            raise ValueError(f"Invalid state: {state}. Must be one of {self.STATES}")

        with self._lock:
            old_state = self.get_state(symbol)
            now = datetime.utcnow().isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if old_state is None:
                    # 新規登録
                    cursor.execute('''
                        INSERT INTO asset_state
                        (symbol, state, state_since, last_price, last_notified_state, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (symbol, state, now, price, None, now))
                    logger.debug(f"New state for {symbol}: {state}")
                    return True  # 新規なので「変化」とみなす

                if old_state == state:
                    # 状態が同じ場合は更新時刻と価格だけ更新
                    cursor.execute('''
                        UPDATE asset_state
                        SET last_price = ?, updated_at = ?
                        WHERE symbol = ?
                    ''', (price, now, symbol))
                    return False  # 変化なし

                # 状態が変化した
                cursor.execute('''
                    UPDATE asset_state
                    SET state = ?, state_since = ?, last_price = ?, updated_at = ?
                    WHERE symbol = ?
                ''', (state, now, price, now, symbol))
                logger.info(f"State change for {symbol}: {old_state} -> {state}")
                return True  # 変化あり

    def should_notify(self, symbol: str, new_state: str) -> bool:
        """
        通知すべきかどうか（状態変化時のみ通知）
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT last_notified_state FROM asset_state WHERE symbol = ?',
                    (symbol,)
                )
                result = cursor.fetchone()

                if not result or result[0] != new_state:
                    return True
                return False

    def mark_notified(self, symbol: str, state: str) -> None:
        """通知済みフラグを更新"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE asset_state
                    SET last_notified_state = ?
                    WHERE symbol = ?
                ''', (state, symbol))

    def get_state_info(self, symbol: str) -> Optional[Dict]:
        """状態情報を辞書で取得"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT state, state_since, last_price, last_notified_state, updated_at
                    FROM asset_state WHERE symbol = ?
                ''', (symbol,))
                result = cursor.fetchone()

                if not result:
                    return None

                return {
                    'state': result[0],
                    'state_since': result[1],
                    'last_price': result[2],
                    'last_notified_state': result[3],
                    'updated_at': result[4]
                }

    def get_all_states(self) -> Dict[str, str]:
        """全シンボルの状態を取得"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT symbol, state FROM asset_state')
                return {row[0]: row[1] for row in cursor.fetchall()}

    def delete_state(self, symbol: str) -> bool:
        """シンボルの状態を削除"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM asset_state WHERE symbol = ?', (symbol,))
                return cursor.rowcount > 0

    def clear_all(self) -> int:
        """全ての状態を削除（テスト用）"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM asset_state')
                return cursor.rowcount
