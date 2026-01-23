"""
急落→低迷→反転のシグナル判定ロジック
仮想通貨（CoinGecko）と米国株（yfinance）の両方に対応
"""
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import requests
import yfinance as yf


def is_crypto_symbol(symbol: str) -> bool:
    """
    シンボルが仮想通貨かどうかを判定
    米国株は通常3-5文字の大文字、仮想通貨は特殊な命名規則
    """
    # 仮想通貨のシンボルマッピングに含まれるかチェック
    crypto_symbols = {
        'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE', 
        'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC'
    }
    
    # 仮想通貨シンボルリストに含まれる場合は仮想通貨
    if symbol.upper() in crypto_symbols:
        return True
    
    # 米国株の一般的なパターン（3-5文字の大文字、または末尾に数字なし）
    # 仮想通貨は通常 "-USD" などのサフィックスがあるが、ここではシンプルに判定
    symbol_upper = symbol.upper()
    
    # CoinGeckoの命名規則（bitcoin, ethereumなど）をチェック
    crypto_ids = ['bitcoin', 'ethereum', 'binancecoin', 'solana', 'cardano', 
                  'ripple', 'dogecoin', 'polkadot', 'matic-network', 'avalanche-2']
    
    # 小文字で始まる場合は仮想通貨IDの可能性
    if symbol.lower() in crypto_ids:
        return True
    
    # デフォルトは米国株とみなす（yfinanceで試す）
    return False


def get_crypto_historical_prices(symbol: str, days: int = 30) -> Optional[List[Tuple[datetime, float]]]:
    """
    CoinGecko APIから仮想通貨の履歴価格データを取得
    戻り値: [(datetime, price), ...] のリスト（時系列順）
    """
    # CoinGeckoのシンボルマッピング（BTC -> bitcoin）
    symbol_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'ADA': 'cardano',
        'XRP': 'ripple',
        'DOGE': 'dogecoin',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'AVAX': 'avalanche-2',
    }
    
    coin_id = symbol_map.get(symbol.upper(), symbol.lower())
    
    try:
        url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'  # 1日1回のデータポイント
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # pricesは [[timestamp_ms, price], ...] の形式
        prices = data.get('prices', [])
        if not prices:
            return None
        
        # datetimeと価格のタプルリストに変換
        result = []
        for ts_ms, price in prices:
            dt = datetime.fromtimestamp(ts_ms / 1000)
            result.append((dt, float(price)))
        
        return sorted(result, key=lambda x: x[0])  # 時系列順にソート
        
    except Exception as e:
        print(f"Error fetching crypto historical prices for {symbol}: {e}")
        return None


def get_stock_historical_prices(symbol: str, days: int = 30) -> Optional[List[Tuple[datetime, float]]]:
    """
    yfinanceから米国株の履歴価格データを取得
    戻り値: [(datetime, price), ...] のリスト（時系列順）
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        # 過去days日分のデータを取得（日次）
        hist = ticker.history(period=f"{days}d", interval="1d")
        
        if hist.empty:
            return None
        
        # datetimeと終値（Close）のタプルリストに変換
        result = []
        for date, row in hist.iterrows():
            # dateはTimestamp型なのでdatetimeに変換
            dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else datetime.fromtimestamp(date.timestamp())
            price = float(row['Close'])
            result.append((dt, price))
        
        return sorted(result, key=lambda x: x[0])  # 時系列順にソート
        
    except Exception as e:
        print(f"Error fetching stock historical prices for {symbol}: {e}")
        return None


def get_historical_prices(symbol: str, days: int = 30) -> Optional[List[Tuple[datetime, float]]]:
    """
    仮想通貨または米国株の履歴価格データを取得（自動判定）
    戻り値: [(datetime, price), ...] のリスト（時系列順）
    """
    if is_crypto_symbol(symbol):
        return get_crypto_historical_prices(symbol, days)
    else:
        return get_stock_historical_prices(symbol, days)


def calculate_3day_return(prices: List[Tuple[datetime, float]]) -> Optional[float]:
    """
    3日リターンを計算（最新から3日前までの変化率）
    戻り値: パーセンテージ（例: -12.5 は -12.5%）
    """
    if len(prices) < 4:  # 最低4日分必要
        return None
    
    # 最新の価格
    latest_price = prices[-1][1]
    # 3日前の価格（最低でも3日分前）
    three_days_ago_price = prices[-4][1] if len(prices) >= 4 else prices[0][1]
    
    if three_days_ago_price == 0:
        return None
    
    return ((latest_price - three_days_ago_price) / three_days_ago_price) * 100


def calculate_7day_range(prices: List[Tuple[datetime, float]]) -> Optional[Tuple[float, float, float]]:
    """
    直近7日間の価格レンジを計算
    戻り値: (min_price, max_price, range_pct) または None
    range_pct: (max - min) / min * 100
    """
    if len(prices) < 7:
        return None
    
    # 直近7日分
    recent_prices = [p[1] for p in prices[-7:]]
    min_price = min(recent_prices)
    max_price = max(recent_prices)
    
    if min_price == 0:
        return None
    
    range_pct = ((max_price - min_price) / min_price) * 100
    return (min_price, max_price, range_pct)


def calculate_5day_high_breakout(prices: List[Tuple[datetime, float]]) -> bool:
    """
    直近5日間の高値を上抜けしたかどうか
    戻り値: True=上抜け、False=未上抜け
    """
    if len(prices) < 6:
        return False
    
    # 直近5日分（最新を除く）
    last_5_days = [p[1] for p in prices[-6:-1]]
    if not last_5_days:
        return False
    
    five_day_high = max(last_5_days)
    current_price = prices[-1][1]
    
    return current_price > five_day_high


def detect_watch_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    WATCHシグナル（急落）を検出
    条件: 3日リターン ≤ -12%
    戻り値: (検出されたか, 3日リターン値)
    """
    prices = get_historical_prices(symbol, days=10)
    if not prices:
        return (False, None)
    
    return_3d = calculate_3day_return(prices)
    if return_3d is None:
        return (False, None)
    
    return (return_3d <= -12.0, return_3d)


def detect_base_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    BASEシグナル（低迷）を検出
    条件: WATCH後、7日の価格レンジが ±5%以内
    戻り値: (検出されたか, レンジ幅%)
    """
    prices = get_historical_prices(symbol, days=15)
    if not prices:
        return (False, None)
    
    range_info = calculate_7day_range(prices)
    if range_info is None:
        return (False, None)
    
    min_price, max_price, range_pct = range_info
    return (range_pct <= 5.0, range_pct)


def detect_buy_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    BUYシグナル（反転）を検出
    条件: 直近5日高値を上抜け
    戻り値: (検出されたか, 現在価格)
    """
    prices = get_historical_prices(symbol, days=10)
    if not prices:
        return (False, None)
    
    breakout = calculate_5day_high_breakout(prices)
    current_price = prices[-1][1] if prices else None
    
    return (breakout, current_price)


def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """
    現在の状態を判定（状態遷移ロジック）
    戻り値: 'NORMAL', 'WATCH', 'BASE', 'BUY' のいずれか
    """
    # BUYシグナルが最優先
    buy_detected, _ = detect_buy_signal(symbol)
    if buy_detected:
        return 'BUY'
    
    # BASEシグナル（WATCH状態の時のみ有効）
    if current_state in ['WATCH', 'BASE']:
        base_detected, _ = detect_base_signal(symbol)
        if base_detected:
            return 'BASE'
    
    # WATCHシグナル（急落）
    watch_detected, _ = detect_watch_signal(symbol)
    if watch_detected:
        return 'WATCH'
    
    # デフォルトはNORMAL
    return 'NORMAL'


def get_crypto_current_price(symbol: str) -> Optional[float]:
    """仮想通貨の現在価格を取得（CoinGecko）"""
    symbol_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'ADA': 'cardano',
        'XRP': 'ripple',
        'DOGE': 'dogecoin',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'AVAX': 'avalanche-2',
    }
    
    coin_id = symbol_map.get(symbol.upper(), symbol.lower())
    
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if coin_id in data and 'usd' in data[coin_id]:
            return float(data[coin_id]['usd'])
        
        return None
    except Exception as e:
        print(f"Error fetching crypto current price for {symbol}: {e}")
        return None


def get_stock_current_price(symbol: str) -> Optional[float]:
    """米国株の現在価格を取得（yfinance）"""
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        
        # 最新の終値を取得（リアルタイム価格が取得できない場合は前日の終値）
        if 'regularMarketPrice' in info:
            return float(info['regularMarketPrice'])
        elif 'previousClose' in info:
            return float(info['previousClose'])
        
        # 履歴データから最新の終値を取得
        hist = ticker.history(period="1d", interval="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        
        return None
    except Exception as e:
        print(f"Error fetching stock current price for {symbol}: {e}")
        return None


def get_current_price(symbol: str) -> Optional[float]:
    """現在の価格を取得（仮想通貨または米国株を自動判定）"""
    if is_crypto_symbol(symbol):
        return get_crypto_current_price(symbol)
    else:
        return get_stock_current_price(symbol)
