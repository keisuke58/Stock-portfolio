"""
Daily Selector: 「今日の1個」を選ぶ
- BUY上限（最大3候補）
- ローテーション（同一資産は7日間再選出禁止）
- 偏り制限（同一セクター最大2、Crypto最大2）
- 信頼度（High/Mid/Spec を付与し、High優先）
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import os


class DailySelector:
    """1日1個を選ぶセレクタ"""
    
    def __init__(self, db_path: str = 'selector/selection_history.db'):
        """セレクション履歴DBを初期化"""
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 選出履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS selection_history (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                score REAL,
                state TEXT,
                category TEXT,
                PRIMARY KEY (date, symbol)
            )
        ''')
        
        # インデックス作成
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date 
            ON selection_history(date)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_recent_selections(self, days: int = 7) -> List[str]:
        """直近days日間に選出されたシンボルを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT DISTINCT symbol
            FROM selection_history
            WHERE date >= ?
        ''', (cutoff_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in results]
    
    def record_selection(self, symbol: str, score: float, state: str, category: str):
        """今日の選出を記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT OR REPLACE INTO selection_history 
            (date, symbol, score, state, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, symbol, score, state, category))
        
        conn.commit()
        conn.close()
    
    def get_category(self, symbol: str, asset_category: str) -> str:
        """資産のカテゴリを取得（セクター判定用）"""
        # 仮想通貨
        if asset_category == '仮想通貨':
            return 'CRYPTO'
        
        # ETF判定
        etf_patterns = ['SPY', 'QQQ', 'IVV', 'VTI', 'VOO', 'GLD', 'SLV', 'DIA', 'IWM']
        if symbol.upper() in etf_patterns:
            return 'ETF'
        
        # セクター判定（簡易版）
        # 実際の実装では、より詳細なセクター分類が必要
        tech_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
        if symbol.upper() in tech_symbols:
            return 'TECH'
        
        return 'OTHER'
    
    def filter_by_rotation(self, candidates: List[Dict], rotation_days: int = 7) -> List[Dict]:
        """ローテーション: 同一資産はrotation_days日間再選出禁止"""
        recent_selections = self.get_recent_selections(rotation_days)
        recent_set = set(recent_selections)
        
        filtered = [c for c in candidates if c['symbol'] not in recent_set]
        return filtered
    
    def filter_by_bias_control(
        self,
        candidates: List[Dict],
        max_per_category: Dict[str, int] = None
    ) -> List[Dict]:
        """偏り制限: 同一カテゴリ/セクターの選出数を制限"""
        if max_per_category is None:
            max_per_category = {
                'CRYPTO': 2,
                'ETF': 2,
                'TECH': 2,
                'OTHER': 3
            }
        
        # カテゴリごとにグループ化
        by_category = {}
        for candidate in candidates:
            category = candidate.get('category', 'OTHER')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(candidate)
        
        # 各カテゴリから最大数まで選出
        filtered = []
        for category, items in by_category.items():
            max_count = max_per_category.get(category, 3)
            # スコア順にソートして上位を選ぶ
            items_sorted = sorted(items, key=lambda x: x.get('total_score', 0), reverse=True)
            filtered.extend(items_sorted[:max_count])
        
        return filtered
    
    def filter_by_buy_limit(self, candidates: List[Dict], max_buy: int = 3) -> List[Dict]:
        """BUY上限: BUYは最大max_buy候補まで、無ければBASEから1個"""
        buy_candidates = [c for c in candidates if c.get('current_state') == 'BUY']
        base_candidates = [c for c in candidates if c.get('current_state') == 'BASE']
        other_candidates = [c for c in candidates if c.get('current_state') not in ['BUY', 'BASE', 'WATCH']]
        
        # WATCH状態は除外（急落直後なので買わない）
        filtered = []
        
        # BUY候補を優先（最大max_buy個）
        if buy_candidates:
            buy_sorted = sorted(buy_candidates, key=lambda x: x.get('total_score', 0), reverse=True)
            filtered.extend(buy_sorted[:max_buy])
        
        # BUYが無い、または足りない場合はBASEから
        if len(filtered) < max_buy:
            base_sorted = sorted(base_candidates, key=lambda x: x.get('total_score', 0), reverse=True)
            needed = max_buy - len(filtered)
            filtered.extend(base_sorted[:needed])
        
        # それでも足りない場合はその他から
        if len(filtered) < max_buy:
            other_sorted = sorted(other_candidates, key=lambda x: x.get('total_score', 0), reverse=True)
            needed = max_buy - len(filtered)
            filtered.extend(other_sorted[:needed])
        
        return filtered
    
    def assign_confidence(self, candidate: Dict) -> str:
        """信頼度を付与（High/Mid/Spec）"""
        total_score = candidate.get('total_score', 0)
        current_state = candidate.get('current_state', 'NORMAL')
        buy_qualified = candidate.get('buy_qualified', False)
        
        # High: スコア高く、BUY状態で資格あり
        if total_score >= 70 and current_state == 'BUY' and buy_qualified:
            return 'High'
        
        # Mid: スコア中程度、BUYまたはBASE状態
        if total_score >= 60 and current_state in ['BUY', 'BASE']:
            return 'Mid'
        
        # Spec: その他（投機的）
        return 'Spec'
    
    def select_daily_pick(
        self,
        candidates: List[Dict],
        rotation_days: int = 7,
        max_buy: int = 3,
        max_per_category: Optional[Dict[str, int]] = None
    ) -> Optional[Dict]:
        """
        「今日の1個」を選ぶ
        
        処理フロー:
        1. BUY上限フィルタ（BUY最大3、無ければBASEから）
        2. ローテーションフィルタ（7日間再選出禁止）
        3. 偏り制限フィルタ（同一カテゴリ最大2）
        4. 信頼度付与
        5. スコア順で1個選出
        """
        if not candidates:
            return None
        
        # 1. BUY上限フィルタ
        filtered = self.filter_by_buy_limit(candidates, max_buy=max_buy)
        
        # 2. ローテーションフィルタ
        filtered = self.filter_by_rotation(filtered, rotation_days=rotation_days)
        
        # 3. 偏り制限フィルタ
        filtered = self.filter_by_bias_control(filtered, max_per_category=max_per_category)
        
        if not filtered:
            return None
        
        # 4. 信頼度付与
        for candidate in filtered:
            candidate['confidence'] = self.assign_confidence(candidate)
        
        # 5. スコア順でソート（High優先、次にスコア順）
        def sort_key(c):
            confidence_order = {'High': 3, 'Mid': 2, 'Spec': 1}
            return (confidence_order.get(c.get('confidence', 'Spec'), 1), c.get('total_score', 0))
        
        filtered_sorted = sorted(filtered, key=sort_key, reverse=True)
        
        # 6. トップ1を選出
        daily_pick = filtered_sorted[0]
        
        # 7. 選出を記録
        category = self.get_category(daily_pick['symbol'], daily_pick.get('asset_category', 'その他'))
        self.record_selection(
            daily_pick['symbol'],
            daily_pick.get('total_score', 0),
            daily_pick.get('current_state', 'NORMAL'),
            category
        )
        
        return daily_pick
    
    def select_top_n(
        self,
        candidates: List[Dict],
        n: int = 3,
        rotation_days: int = 7,
        max_buy: int = 3,
        max_per_category: Optional[Dict[str, int]] = None
    ) -> List[Dict]:
        """
        スコアの高い上位N個を選出
        
        処理フロー:
        1. WATCH状態を除外（既に除外済みの想定）
        2. スコア順でソート
        3. ローテーションフィルタ（7日間再選出禁止）
        4. 信頼度付与
        5. スコア順で上位N個を選出
        """
        if not candidates:
            return []
        
        # 1. スコア順でソート
        candidates_sorted = sorted(candidates, key=lambda x: x.get('total_score', 0), reverse=True)
        
        # 2. ローテーションフィルタ（最近選出されたものを除外）
        recent_selections = self.get_recent_selections(rotation_days)
        recent_set = set(recent_selections)
        
        filtered = [c for c in candidates_sorted if c['symbol'] not in recent_set]
        
        if not filtered:
            return []
        
        # 3. 信頼度付与
        for candidate in filtered:
            candidate['confidence'] = self.assign_confidence(candidate)
        
        # 4. 信頼度とスコアで再ソート（High優先、次にスコア順）
        def sort_key(c):
            confidence_order = {'High': 3, 'Mid': 2, 'Spec': 1}
            return (confidence_order.get(c.get('confidence', 'Spec'), 1), c.get('total_score', 0))
        
        filtered_sorted = sorted(filtered, key=sort_key, reverse=True)
        
        # 5. 上位N個を選出
        top_n = filtered_sorted[:n]
        
        # 6. 選出を記録
        for pick in top_n:
            category = self.get_category(pick['symbol'], pick.get('asset_category', 'その他'))
            self.record_selection(
                pick['symbol'],
                pick.get('total_score', 0),
                pick.get('current_state', 'NORMAL'),
                category
            )
        
        return top_n
