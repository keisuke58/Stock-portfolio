"""
Signals層: WATCH/BASE/BUY 判定（状態機械）
"""
from .state_machine import StateMachine, determine_state, is_crypto_symbol
from .explainer import SignalExplainer
# signals.pyファイルから必要な関数をインポート
import sys
import os
# 親ディレクトリのsignals.pyからインポート
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
signals_file = os.path.join(parent_dir, 'signals.py')
if os.path.exists(signals_file):
    import importlib.util
    spec = importlib.util.spec_from_file_location("signals_module", signals_file)
    signals_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(signals_module)
    get_historical_prices = signals_module.get_historical_prices
    get_current_price = signals_module.get_current_price
    calculate_5day_high_breakout = signals_module.calculate_5day_high_breakout
else:
    # フォールバック: 直接インポートを試みる
    from signals import get_historical_prices, get_current_price, calculate_5day_high_breakout

__all__ = ['StateMachine', 'determine_state', 'is_crypto_symbol', 'SignalExplainer', 'get_historical_prices', 'get_current_price', 'calculate_5day_high_breakout']
