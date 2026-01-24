"""
バックテストサービス
Backtesterをラップ
"""
from typing import List, Dict, Optional
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backtesting.backtester import Backtester


class BacktestService:
    """バックテストサービス"""
    
    def __init__(
        self,
        entry_fee_rate: float = 0.001,
        exit_fee_rate: float = 0.001,
        buy_slippage: float = 0.0005,
        sell_slippage: float = 0.0005
    ):
        """
        初期化
        
        Args:
            entry_fee_rate: エントリー手数料率
            exit_fee_rate: エグジット手数料率
            buy_slippage: 買いスリッページ率
            sell_slippage: 売りスリッページ率
        """
        self.backtester = Backtester(
            entry_fee_rate=entry_fee_rate,
            exit_fee_rate=exit_fee_rate,
            buy_slippage=buy_slippage,
            sell_slippage=sell_slippage
        )
    
    def backtest_strategy_daily(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        stop_loss_pct: float = -10.0,
        take_profit_pct: float = 20.0
    ) -> Dict:
        """
        日次戦略バックテスト
        
        Args:
            symbols: シンボルのリスト
            start_date: 開始日
            end_date: 終了日
            initial_capital: 初期資本
            stop_loss_pct: ストップロス（%）
            take_profit_pct: 利確（%）
        
        Returns:
            バックテスト結果の辞書
        """
        return self.backtester.backtest_strategy_daily(
            symbols,
            start_date,
            end_date,
            initial_capital,
            stop_loss_pct,
            take_profit_pct
        )
    
    def backtest_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        1つのシンボルをバックテスト
        
        Args:
            symbol: シンボル名
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            バックテスト結果の辞書
        """
        return self.backtester.backtest_symbol(symbol, start_date, end_date)
    
    def backtest_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        output_file: Optional[str] = None
    ) -> Dict:
        """
        複数のシンボルをバックテスト
        
        Args:
            symbols: シンボルのリスト
            start_date: 開始日
            end_date: 終了日
            output_file: 結果を保存するファイル
        
        Returns:
            バックテスト結果の辞書
        """
        return self.backtester.backtest_multiple_symbols(
            symbols,
            start_date,
            end_date,
            output_file
        )
