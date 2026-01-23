"""
投資リサーチAI: 全資産クラス横断比較モジュール
急落→低迷→反転局面、割安度、質の評価を統合
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import requests
import time
from signals import (
    get_historical_prices, 
    get_current_price, 
    is_crypto_symbol,
    determine_state
)


class InvestmentAnalyzer:
    """投資評価を行うクラス"""
    
    # 主要資産のカテゴリ定義
    ASSET_CATEGORIES = {
        'US_LARGE_CAP': '米国大型株',
        'US_ETF': '米国ETF',
        'CRYPTO': '仮想通貨',
        'COMMODITY': 'コモディティ',
        'OTHER': 'その他'
    }
    
    def __init__(self):
        self.crypto_symbol_map = {
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
    
    def get_asset_category(self, symbol: str) -> str:
        """資産のカテゴリを判定"""
        symbol_upper = symbol.upper()
        
        # 仮想通貨
        if is_crypto_symbol(symbol):
            return self.ASSET_CATEGORIES['CRYPTO']
        
        # ETF判定（一般的なETFシンボルパターン）
        etf_patterns = ['SPY', 'QQQ', 'IVV', 'VTI', 'VOO', 'GLD', 'SLV', 'DIA', 'IWM']
        if symbol_upper in etf_patterns:
            return self.ASSET_CATEGORIES['US_ETF']
        
        # コモディティ
        commodity_symbols = ['GLD', 'SLV', 'GDX', 'GDXJ', 'IAU', 'SIVR']
        if symbol_upper in commodity_symbols:
            return self.ASSET_CATEGORIES['COMMODITY']
        
        # デフォルトは米国大型株
        return self.ASSET_CATEGORIES['US_LARGE_CAP']
    
    def calculate_ath_ratio(self, symbol: str) -> Optional[float]:
        """
        ATH（All-Time High）比を計算
        戻り値: 現在価格 / ATH価格（0.0-1.0、低いほど割安）
        """
        try:
            prices = get_historical_prices(symbol, days=365)  # 1年分のデータ
            if not prices or len(prices) < 30:
                return None
            
            current_price = prices[-1][1]
            ath_price = max([p[1] for p in prices])
            
            if ath_price == 0:
                return None
            
            return current_price / ath_price
            
        except Exception as e:
            print(f"Error calculating ATH ratio for {symbol}: {e}")
            return None
    
    def calculate_recent_drop(self, symbol: str) -> Optional[float]:
        """
        直近の急落率を計算（30日間）
        戻り値: パーセンテージ（負の値、例: -15.5 は -15.5%）
        """
        try:
            prices = get_historical_prices(symbol, days=30)
            if not prices or len(prices) < 2:
                return None
            
            current_price = prices[-1][1]
            # 30日前の価格（または利用可能な最古の価格）
            old_price = prices[0][1]
            
            if old_price == 0:
                return None
            
            return ((current_price - old_price) / old_price) * 100
            
        except Exception as e:
            print(f"Error calculating recent drop for {symbol}: {e}")
            return None
    
    def calculate_volatility(self, symbol: str, days: int = 30) -> Optional[float]:
        """
        ボラティリティを計算（標準偏差）
        戻り値: 標準偏差（パーセンテージ）
        """
        try:
            prices = get_historical_prices(symbol, days=days)
            if not prices or len(prices) < 2:
                return None
            
            price_values = [p[1] for p in prices]
            if len(price_values) < 2:
                return None
            
            # 日次リターンを計算
            returns = []
            for i in range(1, len(price_values)):
                if price_values[i-1] != 0:
                    daily_return = (price_values[i] - price_values[i-1]) / price_values[i-1]
                    returns.append(daily_return)
            
            if len(returns) < 2:
                return None
            
            # 標準偏差を計算
            import statistics
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            return std_dev * 100  # パーセンテージに変換
            
        except Exception as e:
            print(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    def get_stock_metrics(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        米国株の財務指標を取得（PER、PBRなど）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            return {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
            }
        except Exception as e:
            print(f"Error fetching stock metrics for {symbol}: {e}")
            return {
                'pe_ratio': None,
                'forward_pe': None,
                'pb_ratio': None,
                'dividend_yield': None,
                'market_cap': None,
                'enterprise_value': None,
            }
    
    def get_company_info(self, symbol: str) -> Dict[str, Optional[str]]:
        """
        企業情報を取得（会社概要、事業内容など）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            return {
                'company_name': info.get('longName') or info.get('shortName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'business_summary': info.get('longBusinessSummary'),
                'website': info.get('website'),
                'full_time_employees': info.get('fullTimeEmployees'),
                'city': info.get('city'),
                'state': info.get('state'),
                'country': info.get('country'),
            }
        except Exception as e:
            print(f"Error fetching company info for {symbol}: {e}")
            return {
                'company_name': None,
                'sector': None,
                'industry': None,
                'business_summary': None,
                'website': None,
                'full_time_employees': None,
                'city': None,
                'state': None,
                'country': None,
            }
    
    def get_analyst_recommendations(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        アナリスト評価を取得（目標株価、レコメンデーションなど）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # レコメンデーションの日本語変換
            recommendation_key = info.get('recommendationKey', '').lower()
            recommendation_jp = {
                'strong_buy': '強気買い',
                'buy': '買い',
                'hold': '中立',
                'underperform': '弱気',
                'sell': '売り',
            }.get(recommendation_key, recommendation_key)
            
            # EPS成長率を計算
            eps_current = info.get('trailingEps')
            eps_forward = info.get('forwardEps')
            eps_growth = None
            if eps_current and eps_forward and eps_current > 0:
                eps_growth = ((eps_forward - eps_current) / abs(eps_current)) * 100
            
            return {
                'target_mean_price': info.get('targetMeanPrice'),
                'target_high_price': info.get('targetHighPrice'),
                'target_low_price': info.get('targetLowPrice'),
                'recommendation': recommendation_jp,
                'recommendation_key': recommendation_key,
                'number_of_analysts': info.get('numberOfAnalystOpinions'),
                'current_price': info.get('regularMarketPrice') or info.get('previousClose'),
                'eps_current': eps_current,
                'eps_forward': eps_forward,
                'eps_growth': eps_growth,
            }
        except Exception as e:
            print(f"Error fetching analyst recommendations for {symbol}: {e}")
            return {
                'target_mean_price': None,
                'target_high_price': None,
                'target_low_price': None,
                'recommendation': None,
                'recommendation_key': None,
                'number_of_analysts': None,
                'current_price': None,
                'eps_current': None,
                'eps_forward': None,
                'eps_growth': None,
            }
    
    def get_comprehensive_financial_data(self, symbol: str) -> Dict:
        """
        包括的な財務データを取得（財務指標、財務健全性、株価情報など）
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # EPS成長率を計算
            eps_current = info.get('trailingEps')
            eps_forward = info.get('forwardEps')
            eps_growth = None
            if eps_current and eps_forward and eps_current > 0:
                eps_growth = (eps_forward - eps_current) / abs(eps_current) * 100
            
            # 配当情報
            dividend_yield = info.get('dividendYield')
            dividend_rate = info.get('dividendRate')
            payout_ratio = info.get('payoutRatio')
            five_year_avg_dividend_yield = info.get('fiveYearAvgDividendYield')
            
            # 株価チャート情報
            current_price = info.get('regularMarketPrice') or info.get('previousClose')
            fifty_two_week_high = info.get('fiftyTwoWeekHigh')
            fifty_two_week_low = info.get('fiftyTwoWeekLow')
            year_to_date_return = None
            if current_price and fifty_two_week_low:
                year_to_date_return = ((current_price - fifty_two_week_low) / fifty_two_week_low) * 100
            
            # ベータ値
            beta = info.get('beta')
            
            # 出来高情報
            average_volume = info.get('averageVolume')
            average_volume_10days = info.get('averageVolume10days')
            volume = info.get('volume')
            
            # 時価総額と企業価値
            market_cap = info.get('marketCap')
            enterprise_value = info.get('enterpriseValue')
            shares_outstanding = info.get('sharesOutstanding')
            float_shares = info.get('floatShares')
            
            # 財務健全性
            total_debt = info.get('totalDebt')
            total_cash = info.get('totalCash')
            debt_to_equity = info.get('debtToEquity')
            current_ratio = info.get('currentRatio')
            quick_ratio = info.get('quickRatio')
            
            # 利払い能力
            ebit = info.get('ebit')
            interest_expense = info.get('interestExpense')
            interest_coverage = None
            if ebit and interest_expense and interest_expense > 0:
                interest_coverage = ebit / interest_expense
            
            # 収益性指標
            profit_margin = info.get('profitMargins')
            operating_margin = info.get('operatingMargins')
            gross_margin = info.get('grossMargins')
            roe = info.get('returnOnEquity')
            roa = info.get('returnOnAssets')
            
            # 成長指標
            revenue_growth = info.get('revenueGrowth')
            earnings_growth = info.get('earningsGrowth')
            earnings_quarterly_growth = info.get('earningsQuarterlyGrowth')
            
            # フリーキャッシュフロー
            free_cashflow = info.get('freeCashflow')
            operating_cashflow = info.get('operatingCashflow')
            
            # 財務比率
            pe_ratio = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            peg_ratio = info.get('pegRatio')
            pb_ratio = info.get('priceToBook')
            ps_ratio = info.get('priceToSalesTrailing12Months')
            ev_to_revenue = info.get('enterpriseToRevenue')
            ev_to_ebitda = info.get('enterpriseToEbitda')
            
            # 売上と利益
            total_revenue = info.get('totalRevenue')
            revenue_per_share = info.get('revenuePerShare')
            earnings_per_share = eps_current
            
            # 決算・配当情報
            next_fiscal_year_end = info.get('nextFiscalYearEnd')
            most_recent_quarter = info.get('mostRecentQuarter')
            ex_dividend_date = info.get('exDividendDate')
            dividend_date = info.get('dividendDate')
            
            # 過去の業績（四半期）
            try:
                quarterly_earnings = ticker.quarterly_earnings
                if not quarterly_earnings.empty:
                    latest_quarter_revenue = quarterly_earnings.iloc[0]['Revenue'] if 'Revenue' in quarterly_earnings.columns else None
                    latest_quarter_earnings = quarterly_earnings.iloc[0]['Earnings'] if 'Earnings' in quarterly_earnings.columns else None
                else:
                    latest_quarter_revenue = None
                    latest_quarter_earnings = None
            except:
                latest_quarter_revenue = None
                latest_quarter_earnings = None
            
            # セクター/業界比較用の指標
            sector = info.get('sector')
            industry = info.get('industry')
            
            return {
                # 株価情報
                'current_price': current_price,
                'fifty_two_week_high': fifty_two_week_high,
                'fifty_two_week_low': fifty_two_week_low,
                'year_to_date_return': year_to_date_return,
                'beta': beta,
                'volume': volume,
                'average_volume': average_volume,
                'average_volume_10days': average_volume_10days,
                
                # 時価総額・企業価値
                'market_cap': market_cap,
                'enterprise_value': enterprise_value,
                'shares_outstanding': shares_outstanding,
                'float_shares': float_shares,
                
                # 財務健全性
                'total_debt': total_debt,
                'total_cash': total_cash,
                'debt_to_equity': debt_to_equity,
                'current_ratio': current_ratio,
                'quick_ratio': quick_ratio,
                'interest_coverage': interest_coverage,
                
                # 収益性
                'profit_margin': profit_margin,
                'operating_margin': operating_margin,
                'gross_margin': gross_margin,
                'roe': roe,
                'roa': roa,
                
                # 成長指標
                'revenue_growth': revenue_growth,
                'earnings_growth': earnings_growth,
                'earnings_quarterly_growth': earnings_quarterly_growth,
                'eps_growth': eps_growth,
                
                # キャッシュフロー
                'free_cashflow': free_cashflow,
                'operating_cashflow': operating_cashflow,
                
                # 財務比率
                'pe_ratio': pe_ratio,
                'forward_pe': forward_pe,
                'peg_ratio': peg_ratio,
                'pb_ratio': pb_ratio,
                'ps_ratio': ps_ratio,
                'ev_to_revenue': ev_to_revenue,
                'ev_to_ebitda': ev_to_ebitda,
                
                # 配当情報
                'dividend_yield': dividend_yield,
                'dividend_rate': dividend_rate,
                'payout_ratio': payout_ratio,
                'five_year_avg_dividend_yield': five_year_avg_dividend_yield,
                
                # 売上・利益
                'total_revenue': total_revenue,
                'revenue_per_share': revenue_per_share,
                'earnings_per_share': earnings_per_share,
                'eps_current': eps_current,
                'eps_forward': eps_forward,
                
                # 決算・配当情報
                'next_fiscal_year_end': next_fiscal_year_end,
                'most_recent_quarter': most_recent_quarter,
                'ex_dividend_date': ex_dividend_date,
                'dividend_date': dividend_date,
                
                # 過去の業績
                'latest_quarter_revenue': latest_quarter_revenue,
                'latest_quarter_earnings': latest_quarter_earnings,
                
                # セクター/業界
                'sector': sector,
                'industry': industry,
            }
        except Exception as e:
            print(f"Error fetching comprehensive financial data for {symbol}: {e}")
            return {}
    
    def evaluate_recovery_potential(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        回復余地を評価
        戻り値: (回復余地があるか, 理由)
        """
        try:
            # 状態を確認
            from state_store import StateStore
            state_store = StateStore()
            current_state = state_store.get_state(symbol)
            
            # BUYシグナルがある場合は回復余地あり
            if current_state == 'BUY':
                return (True, "反転シグナル検出")
            
            # ATH比が低い場合は回復余地あり
            ath_ratio = self.calculate_ath_ratio(symbol)
            if ath_ratio and ath_ratio < 0.7:  # ATH比70%以下
                return (True, f"ATH比{ath_ratio:.1%}で割安")
            
            # 直近急落後で低迷している場合は回復余地あり
            recent_drop = self.calculate_recent_drop(symbol)
            if recent_drop and recent_drop < -10:  # 10%以上下落
                return (True, f"直近{recent_drop:.1f}%下落")
            
            return (False, None)
            
        except Exception as e:
            print(f"Error evaluating recovery potential for {symbol}: {e}")
            return (False, None)
    
    def evaluate_quality(self, symbol: str) -> Tuple[int, Optional[str]]:
        """
        資産の質を評価（1-5スケール、5が最高）
        戻り値: (スコア, 理由)
        """
        score = 3  # デフォルトは中程度
        reasons = []
        
        try:
            if is_crypto_symbol(symbol):
                # 仮想通貨の場合
                major_cryptos = ['BTC', 'ETH', 'BNB', 'SOL']
                if symbol.upper() in major_cryptos:
                    score = 5
                    reasons.append("主要仮想通貨")
                else:
                    score = 3
                    reasons.append("中堅仮想通貨")
            else:
                # 米国株の場合
                metrics = self.get_stock_metrics(symbol)
                
                # 時価総額が大きいほど質が高い
                market_cap = metrics.get('market_cap')
                if market_cap:
                    if market_cap > 100_000_000_000:  # 1000億ドル以上
                        score += 1
                        reasons.append("大型株")
                    elif market_cap > 10_000_000_000:  # 100億ドル以上
                        reasons.append("中堅株")
                
                # PERが適正範囲内
                pe_ratio = metrics.get('pe_ratio')
                if pe_ratio:
                    if 10 <= pe_ratio <= 25:
                        score += 1
                        reasons.append("適正PER")
                    elif pe_ratio > 50:
                        score -= 1
                        reasons.append("高PER")
                
                # 配当利回りがある
                dividend_yield = metrics.get('dividend_yield')
                if dividend_yield and dividend_yield > 0.02:  # 2%以上
                    score += 1
                    reasons.append("配当あり")
            
            # スコアを1-5の範囲に制限
            score = max(1, min(5, score))
            
            return (score, ", ".join(reasons) if reasons else "標準")
            
        except Exception as e:
            print(f"Error evaluating quality for {symbol}: {e}")
            return (3, "評価不可")
    
    def calculate_value_score(self, symbol: str, ath_ratio: Optional[float]) -> float:
        """
        Valueスコア（割安度）を計算（0-100点）
        ATH比とPERを考慮
        """
        score = 0.0
        
        # ATH比による評価（低いほど割安で高スコア）
        if ath_ratio:
            if ath_ratio < 0.5:
                score += 50  # 大幅割安
            elif ath_ratio < 0.7:
                score += 40  # 割安
            elif ath_ratio < 0.85:
                score += 30  # やや割安
            elif ath_ratio < 0.95:
                score += 20  # ほぼ適正
            else:
                score += 10  # 高値圏
        
        # PERによる評価（米国株の場合）
        if not is_crypto_symbol(symbol):
            metrics = self.get_stock_metrics(symbol)
            pe_ratio = metrics.get('pe_ratio')
            if pe_ratio:
                if pe_ratio < 10:
                    score += 30  # 割安PER
                elif 10 <= pe_ratio <= 25:
                    score += 20  # 適正PER
                elif 25 < pe_ratio <= 50:
                    score += 10  # やや高PER
                else:
                    score += 0  # 高PER
        
        return min(100.0, score)
    
    def calculate_momentum_score(self, symbol: str, recent_drop: Optional[float], current_state: str) -> float:
        """
        Momentumスコア（反転の確からしさ）を計算（0-100点）
        5日高値ブレイク、出来高増加、30日リターンを考慮
        """
        score = 0.0
        
        # 状態による評価
        if current_state == 'BUY':
            score += 50  # 反転確認
        elif current_state == 'BASE':
            score += 30  # 低迷・横ばい
        elif current_state == 'WATCH':
            score += 10  # 急落直後（まだ買わない）
        
        # 5日高値ブレイクチェック
        from signals import get_historical_prices, calculate_5day_high_breakout
        prices = get_historical_prices(symbol, days=10)
        if prices and calculate_5day_high_breakout(prices):
            score += 30  # 反転シグナル強
        
        # 30日リターンチェック（極端でないことを確認）
        if recent_drop is not None:
            if -30 <= recent_drop <= 10:  # 適度な下落または上昇
                score += 20
            elif recent_drop < -30:  # 行き過ぎ下落
                score += 5  # まだ危険
            elif recent_drop > 30:  # 行き過ぎ上昇
                score += 5  # 買い遅れ
        
        return min(100.0, score)
    
    def calculate_stability_score(self, symbol: str, volatility: Optional[float], quality_score: int) -> float:
        """
        Stabilityスコア（事業・ボラ耐性）を計算（0-100点）
        ボラティリティと質スコアを考慮
        """
        score = 0.0
        
        # 質スコアによる評価
        if quality_score >= 5:
            score += 50  # 最高品質
        elif quality_score >= 4:
            score += 40  # 高品質
        elif quality_score >= 3:
            score += 30  # 標準品質
        elif quality_score >= 2:
            score += 20  # やや低品質
        else:
            score += 10  # 低品質
        
        # ボラティリティによる評価（低いほど安定）
        if volatility is not None:
            if volatility < 2:
                score += 30  # 非常に安定
            elif volatility < 3:
                score += 25  # 安定
            elif volatility < 5:
                score += 15  # やや不安定
            elif volatility < 8:
                score += 5  # 不安定
            else:
                score += 0  # 非常に不安定
        
        return min(100.0, score)
    
    def check_buy_qualification(self, symbol: str) -> Tuple[bool, List[str]]:
        """
        BUY候補の厳選ルールをチェック
        戻り値: (BUY資格があるか, 理由リスト)
        """
        reasons = []
        qualified = True
        
        # 1. 直近5日高値ブレイク
        from signals import get_historical_prices, calculate_5day_high_breakout
        prices = get_historical_prices(symbol, days=10)
        if prices:
            breakout = calculate_5day_high_breakout(prices)
            if breakout:
                reasons.append("5日高値ブレイク")
            else:
                qualified = False
                reasons.append("5日高値未ブレイク")
        else:
            qualified = False
            reasons.append("価格データ不足")
        
        # 2. 30日リターンが極端でない（-30%以上、+30%以下）
        recent_drop = self.calculate_recent_drop(symbol)
        if recent_drop is not None:
            if -30 <= recent_drop <= 30:
                reasons.append(f"30日リターン適正({recent_drop:.1f}%)")
            else:
                qualified = False
                reasons.append(f"30日リターン極端({recent_drop:.1f}%)")
        
        # 3. 出来高増加チェック（簡易版：価格データから推測）
        # 実際の出来高データは取得が難しいため、価格変動から推測
        if prices and len(prices) >= 5:
            recent_volatility = self.calculate_volatility(symbol, days=5)
            if recent_volatility and recent_volatility > 1.5:
                reasons.append("出来高増加の可能性")
        
        return (qualified, reasons)
    
    def calculate_investment_score(self, symbol: str) -> Dict:
        """
        投資スコアを総合的に計算（3要素：Value/Momentum/Stability）
        戻り値: 投資評価辞書
        """
        current_price = get_current_price(symbol)
        if current_price is None:
            return None
        
        # 各種指標を計算
        ath_ratio = self.calculate_ath_ratio(symbol)
        recent_drop = self.calculate_recent_drop(symbol)
        volatility = self.calculate_volatility(symbol)
        recovery_potential, recovery_reason = self.evaluate_recovery_potential(symbol)
        quality_score, quality_reason = self.evaluate_quality(symbol)
        
        # 状態を確認
        from state_store import StateStore
        state_store = StateStore()
        current_state = state_store.get_state(symbol) or 'NORMAL'
        
        # 3要素スコアを計算
        value_score = self.calculate_value_score(symbol, ath_ratio)
        momentum_score = self.calculate_momentum_score(symbol, recent_drop, current_state)
        stability_score = self.calculate_stability_score(symbol, volatility, quality_score)
        
        # 総合スコア = 0.4*Value + 0.35*Momentum + 0.25*Stability
        total_score = 0.4 * value_score + 0.35 * momentum_score + 0.25 * stability_score
        
        # BUY資格チェック
        buy_qualified, buy_reasons = self.check_buy_qualification(symbol)
        
        # 投資スタンスを判定（状態とスコアを組み合わせ）
        if current_state == 'BUY' and buy_qualified and total_score >= 70:
            stance = "積極的買い"
        elif current_state == 'BUY' and total_score >= 60:
            stance = "買い"
        elif current_state == 'BASE' and total_score >= 60:
            stance = "様子見（準備中）"
        elif current_state == 'WATCH':
            stance = "様子見（急落中）"
        elif total_score >= 65:
            stance = "買い"
        elif total_score >= 50:
            stance = "様子見"
        elif total_score >= 35:
            stance = "慎重"
        else:
            stance = "回避"
        
        # リスク評価
        risk_level = "低"
        if volatility:
            if volatility > 5:
                risk_level = "高"
            elif volatility > 3:
                risk_level = "中"
        
        return {
            'symbol': symbol,
            'category': self.get_asset_category(symbol),
            'current_price': current_price,
            'ath_ratio': ath_ratio,
            'recent_drop': recent_drop,
            'volatility': volatility,
            'recovery_potential': recovery_potential,
            'recovery_reason': recovery_reason,
            'quality_score': quality_score,
            'quality_reason': quality_reason,
            'current_state': current_state,
            'investment_score': total_score,
            'value_score': value_score,
            'momentum_score': momentum_score,
            'stability_score': stability_score,
            'investment_stance': stance,
            'risk_level': risk_level,
            'buy_qualified': buy_qualified,
            'buy_reasons': buy_reasons,
        }
    
    def analyze_all_assets(self, symbols: List[str], max_assets: Optional[int] = None) -> List[Dict]:
        """
        全資産を分析して投資スコアを計算
        戻り値: 投資評価リスト（スコア順）
        """
        results = []
        processed = 0
        skipped = 0
        
        # 主要資産を優先的に分析
        priority_symbols = [
            'BTC', 'ETH', 'SOL', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 
            'META', 'TSLA', 'SPY', 'QQQ', 'GLD', 'VTI', 'IVV'
        ]
        
        # 優先シンボルを先に処理
        symbols_to_process = []
        for sym in priority_symbols:
            if sym in symbols:
                symbols_to_process.append(sym)
        
        # 残りのシンボルを追加
        for sym in symbols:
            if sym not in symbols_to_process:
                symbols_to_process.append(sym)
        
        # 最大数で制限
        if max_assets:
            symbols_to_process = symbols_to_process[:max_assets]
        
        for symbol in symbols_to_process:
            try:
                print(f"分析中 ({processed + skipped + 1}/{len(symbols_to_process)}): {symbol}...", end=' ')
                
                # レート制限対策: リクエスト間に待機時間を追加
                if processed > 0 and processed % 10 == 0:
                    print("\nレート制限対策: 5秒待機中...")
                    time.sleep(5)
                
                # タイムアウト対策: 価格取得を先に試す
                current_price = get_current_price(symbol)
                if current_price is None:
                    print("価格取得失敗 - スキップ")
                    skipped += 1
                    # レート制限の可能性がある場合は待機
                    time.sleep(1)
                    continue
                
                score_data = self.calculate_investment_score(symbol)
                if score_data:
                    results.append(score_data)
                    print(f"OK スコア: {score_data['investment_score']:.0f}")
                    processed += 1
                else:
                    print("分析失敗 - スキップ")
                    skipped += 1
                
                # レート制限対策: 各リクエスト後に少し待機
                time.sleep(0.5)
                    
            except KeyboardInterrupt:
                print("\n\n分析を中断しました。")
                break
            except Exception as e:
                error_msg = str(e)
                print(f"エラー: {error_msg[:50]}")
                skipped += 1
                # レート制限エラーの場合は長めに待機
                if "429" in error_msg or "Rate limited" in error_msg:
                    print("レート制限検出: 10秒待機中...")
                    time.sleep(10)
                continue
        
        print(f"\n分析完了: {processed}件成功, {skipped}件スキップ")
        
        # 投資スコアでソート（高い順）
        results.sort(key=lambda x: x['investment_score'], reverse=True)
        
        # BUY候補の厳選：BUY状態の資産を優先し、WATCH状態は除外
        # Top10でもBUYは2〜4個で十分という方針
        buy_candidates = [r for r in results if r['current_state'] == 'BUY' and r.get('buy_qualified', False)]
        base_candidates = [r for r in results if r['current_state'] == 'BASE']
        other_candidates = [r for r in results if r['current_state'] not in ['BUY', 'BASE', 'WATCH']]
        
        # WATCH状態は除外（急落直後なので買わない）
        # 優先順位: BUY（最大4個） → BASE → その他
        final_results = []
        final_results.extend(buy_candidates[:4])  # BUYは最大4個
        final_results.extend(base_candidates[:3])  # BASEは最大3個
        final_results.extend(other_candidates[:3])  # その他は最大3個
        
        # 重複を除去してスコア順にソート
        seen_symbols = set()
        unique_results = []
        for r in final_results:
            if r['symbol'] not in seen_symbols:
                unique_results.append(r)
                seen_symbols.add(r['symbol'])
        
        # スコア順に再ソート
        unique_results.sort(key=lambda x: x['investment_score'], reverse=True)
        
        # 足りない場合は元の結果から追加（WATCH状態は除外）
        if len(unique_results) < len(results):
            for r in results:
                if r['symbol'] not in seen_symbols and r['current_state'] != 'WATCH':
                    unique_results.append(r)
                    seen_symbols.add(r['symbol'])
                if len(unique_results) >= len(results):
                    break
        
        return unique_results[:len(results)]  # 元の件数まで
    
    def _create_score_bar(self, score: float, max_score: float = 100, width: int = 40) -> str:
        """スコアを可視化するバーを生成"""
        filled = int((score / max_score) * width)
        # Unicodeブロック文字を使用（UTF-8対応）
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {score:.1f}/{max_score:.0f}"
    
    def _rate_with_stars(self, value: float, thresholds: List[Tuple[float, int]], max_stars: int = 5) -> str:
        """値を★で評価（thresholds: [(閾値, 星の数), ...]）"""
        stars = 0
        for threshold, star_count in sorted(thresholds, reverse=True):
            if value >= threshold:
                stars = star_count
                break
        return "★" * stars + "☆" * (max_stars - stars)
    
    def _evaluate_indicator(self, value: Optional[float], good_threshold: float, excellent_threshold: float, 
                           is_higher_better: bool = True) -> str:
        """指標を評価して記号で表示"""
        if value is None:
            return "❓ データなし"
        
        if is_higher_better:
            if value >= excellent_threshold:
                return f"✅ 優秀 ({value:.2f})"
            elif value >= good_threshold:
                return f"✓ 良好 ({value:.2f})"
            else:
                return f"⚠ 要改善 ({value:.2f})"
        else:
            if value <= excellent_threshold:
                return f"✅ 優秀 ({value:.2f})"
            elif value <= good_threshold:
                return f"✓ 良好 ({value:.2f})"
            else:
                return f"⚠ 要改善 ({value:.2f})"
    
    def _format_percentage(self, value: Optional[float], is_growth: bool = True) -> str:
        """パーセンテージをフォーマットして評価記号付きで表示"""
        if value is None:
            return "❓ データなし"
        
        if is_growth:
            if value > 20:
                return f"🚀 高成長 (+{value:.1f}%)"
            elif value > 10:
                return f"📈 成長 (+{value:.1f}%)"
            elif value > 0:
                return f"✓ 微増 (+{value:.1f}%)"
            elif value > -10:
                return f"⚠ 減少 ({value:.1f}%)"
            else:
                return f"🔻 大幅減少 ({value:.1f}%)"
        else:
            if value > 20:
                return f"✅ 優秀 ({value:.1f}%)"
            elif value > 10:
                return f"✓ 良好 ({value:.1f}%)"
            elif value > 5:
                return f"⚠ 普通 ({value:.1f}%)"
            else:
                return f"🔻 低い ({value:.1f}%)"
    
    def _calculate_score_breakdown(self, data: Dict) -> Dict[str, float]:
        """スコアの内訳を計算"""
        breakdown = {
            'base_score': 50.0,
            'ath_score': 0.0,
            'drop_score': 0.0,
            'recovery_score': 0.0,
            'quality_score': 0.0,
            'state_score': 0.0,
        }
        
        # ATH比スコア
        if data['ath_ratio']:
            if data['ath_ratio'] < 0.5:
                breakdown['ath_score'] = 20.0
            elif data['ath_ratio'] < 0.7:
                breakdown['ath_score'] = 15.0
            elif data['ath_ratio'] < 0.85:
                breakdown['ath_score'] = 10.0
        
        # 急落スコア
        if data['recent_drop']:
            if data['recent_drop'] < -20:
                breakdown['drop_score'] = 15.0
            elif data['recent_drop'] < -10:
                breakdown['drop_score'] = 10.0
            elif data['recent_drop'] < -5:
                breakdown['drop_score'] = 5.0
        
        # 回復余地スコア
        if data['recovery_potential']:
            breakdown['recovery_score'] = 15.0
        
        # 質スコア
        breakdown['quality_score'] = (data['quality_score'] - 3) * 5.0
        
        # 状態スコア
        if data['current_state'] == 'BUY':
            breakdown['state_score'] = 20.0
        elif data['current_state'] == 'BASE':
            breakdown['state_score'] = 10.0
        elif data['current_state'] == 'WATCH':
            breakdown['state_score'] = 5.0
        
        return breakdown
    
    def generate_simple_report(self, symbols: List[str], top_n: int = 10, max_assets: Optional[int] = None) -> str:
        """
        簡易レポートを生成（状態フラグ付きテーブル形式）
        """
        results = self.analyze_all_assets(symbols, max_assets=max_assets)
        top_results = results[:top_n]
        
        if not top_results:
            return "分析対象の資産が見つかりませんでした。"
        
        report_lines = []
        
        # ヘッダー
        report_lines.append("=" * 120)
        report_lines.append("投資推奨レポート（Top 10）")
        report_lines.append("=" * 120)
        report_lines.append("")
        
        # テーブルヘッダー（状態フラグ追加）
        report_lines.append("| Rank | 資産名 | カテゴリ | 状態 | Score | Value | Momentum | Stability | 主な指標 | リスク | 投資スタンス |")
        report_lines.append("|------|--------|----------|------|-------|-------|----------|-----------|----------|--------|--------------|")
        
        for rank, data in enumerate(top_results, 1):
            symbol = data['symbol']
            category = data['category']
            state = data['current_state']
            total_score = data['investment_score']
            value_score = data.get('value_score', 0)
            momentum_score = data.get('momentum_score', 0)
            stability_score = data.get('stability_score', 0)
            
            # 主な指標を簡潔に
            indicators = []
            if data['ath_ratio']:
                indicators.append(f"ATH比{data['ath_ratio']:.0%}")
            if data['recent_drop']:
                indicators.append(f"30日{data['recent_drop']:+.0f}%")
            main_indicators = ", ".join(indicators) if indicators else "-"
            
            risk = data['risk_level']
            stance = data['investment_stance']
            
            report_lines.append(
                f"| {rank:2d} | {symbol:6s} | {category:8s} | {state:5s} | "
                f"{total_score:5.0f} | {value_score:5.0f} | {momentum_score:8.0f} | "
                f"{stability_score:9.0f} | {main_indicators:8s} | {risk:4s} | {stance:10s} |"
            )
        
        report_lines.append("")
        report_lines.append("=" * 120)
        
        # 最初の銘柄（Top 1）について詳細情報を追加
        if top_results:
            top_data = top_results[0]
            symbol = top_data['symbol']
            
            # 企業情報を取得（米国株の場合のみ）
            if not is_crypto_symbol(symbol):
                company_info = self.get_company_info(symbol)
                analyst_data = self.get_analyst_recommendations(symbol)
                
                report_lines.append("")
                report_lines.append("=" * 120)
                report_lines.append(f"【今日の1個】{symbol}")
                report_lines.append("=" * 120)
                report_lines.append("")
                
                # 基本情報
                report_lines.append("基本情報")
                if company_info.get('company_name'):
                    report_lines.append(f"  企業名: {company_info['company_name']}")
                if company_info.get('sector'):
                    report_lines.append(f"  セクター: {company_info['sector']}")
                if company_info.get('industry'):
                    report_lines.append(f"  業界: {company_info['industry']}")
                if company_info.get('full_time_employees'):
                    employees = company_info['full_time_employees']
                    if employees >= 1000:
                        employees_str = f"{employees/1000:.1f}千人"
                    else:
                        employees_str = f"{employees}人"
                    report_lines.append(f"  従業員数: {employees_str}")
                if company_info.get('website'):
                    report_lines.append(f"  ウェブサイト: {company_info['website']}")
                if company_info.get('city') and company_info.get('country'):
                    location = f"{company_info['city']}"
                    if company_info.get('state'):
                        location += f", {company_info['state']}"
                    location += f", {company_info['country']}"
                    report_lines.append(f"  所在地: {location}")
                
                report_lines.append("")
                
                # 企業概要
                if company_info.get('business_summary'):
                    summary = company_info['business_summary']
                    # 長すぎる場合は最初の500文字に制限
                    if len(summary) > 500:
                        summary = summary[:500] + "..."
                    report_lines.append("企業概要")
                    # 複数行に分割して表示（80文字ごと）
                    words = summary.split()
                    current_line = "  "
                    for word in words:
                        if len(current_line) + len(word) + 1 > 80:
                            report_lines.append(current_line)
                            current_line = "  " + word
                        else:
                            if current_line != "  ":
                                current_line += " "
                            current_line += word
                    if current_line != "  ":
                        report_lines.append(current_line)
                    report_lines.append("")
                
                # 包括的な財務データを取得
                financial_data = self.get_comprehensive_financial_data(symbol)
                
                # 簡潔なサマリー（一目でわかる評価）
                report_lines.append("📊 投資評価サマリー")
                report_lines.append("-" * 80)
                
                # 投資スコアの評価
                investment_score = top_data['investment_score']
                if investment_score >= 70:
                    score_eval = "🟢 非常に有望"
                elif investment_score >= 60:
                    score_eval = "🟡 有望"
                elif investment_score >= 50:
                    score_eval = "🟠 要検討"
                else:
                    score_eval = "🔴 慎重に"
                report_lines.append(f"  総合評価: {score_eval} (スコア: {investment_score:.1f}/100)")
                
                # アナリスト評価
                analyst_data = self.get_analyst_recommendations(symbol)
                if analyst_data.get('recommendation'):
                    rec = analyst_data['recommendation']
                    if rec in ['強気買い', '買い']:
                        rec_icon = "🟢"
                    elif rec == '中立':
                        rec_icon = "🟡"
                    else:
                        rec_icon = "🔴"
                    report_lines.append(f"  アナリスト推奨: {rec_icon} {rec}")
                
                # 上昇余地
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    target = analyst_data['target_mean_price']
                    current = analyst_data['current_price']
                    upside = ((target - current) / current) * 100 if current > 0 else 0
                    if upside > 20:
                        upside_eval = "🚀 大幅上昇余地"
                    elif upside > 10:
                        upside_eval = "📈 上昇余地あり"
                    elif upside > 0:
                        upside_eval = "✓ やや上昇余地"
                    else:
                        upside_eval = "⚠ 上昇余地少"
                    report_lines.append(f"  目標株価上昇余地: {upside_eval} (+{upside:.1f}%)")
                
                # 財務健全性の簡易評価
                if financial_data.get('debt_to_equity') is not None:
                    debt_equity = financial_data['debt_to_equity']
                    if debt_equity < 0.5:
                        debt_eval = "✅ 健全"
                    elif debt_equity < 1.0:
                        debt_eval = "✓ 良好"
                    else:
                        debt_eval = "⚠ 負債多め"
                    report_lines.append(f"  財務健全性: {debt_eval} (負債資本比: {debt_equity:.2f})")
                
                # 成長性の評価
                if financial_data.get('revenue_growth') is not None:
                    growth = financial_data['revenue_growth'] * 100
                    growth_eval = self._format_percentage(growth, is_growth=True)
                    report_lines.append(f"  成長性: {growth_eval}")
                
                # 収益性の評価
                if financial_data.get('roe') is not None:
                    roe = financial_data['roe'] * 100
                    roe_eval = self._format_percentage(roe, is_growth=False)
                    report_lines.append(f"  収益性(ROE): {roe_eval}")
                
                report_lines.append("")
                
                # 株価情報
                report_lines.append("📈 株価情報")
                if financial_data.get('current_price'):
                    report_lines.append(f"  現在価格: ${financial_data['current_price']:,.2f}")
                if financial_data.get('fifty_two_week_high') and financial_data.get('fifty_two_week_low'):
                    high = financial_data['fifty_two_week_high']
                    low = financial_data['fifty_two_week_low']
                    current = financial_data.get('current_price', 0)
                    if current > 0:
                        high_pct = ((current - low) / (high - low)) * 100 if high > low else 0
                        report_lines.append(f"  52週高値: ${high:,.2f}")
                        report_lines.append(f"  52週安値: ${low:,.2f}")
                        report_lines.append(f"  52週レンジ内位置: {high_pct:.1f}%")
                if financial_data.get('year_to_date_return'):
                    report_lines.append(f"  年初来リターン: {financial_data['year_to_date_return']:+.1f}%")
                if financial_data.get('beta'):
                    report_lines.append(f"  ベータ値: {financial_data['beta']:.2f}")
                if financial_data.get('volume') and financial_data.get('average_volume'):
                    vol_ratio = (financial_data['volume'] / financial_data['average_volume']) if financial_data['average_volume'] > 0 else 0
                    report_lines.append(f"  出来高: {financial_data['volume']:,}株 (平均比: {vol_ratio:.1f}倍)")
                report_lines.append("")
                
                # 時価総額・企業価値
                report_lines.append("時価総額・企業価値")
                if financial_data.get('market_cap'):
                    market_cap = financial_data['market_cap']
                    if market_cap >= 1_000_000_000_000:
                        report_lines.append(f"  時価総額: ${market_cap/1_000_000_000_000:.2f}T")
                    elif market_cap >= 1_000_000_000:
                        report_lines.append(f"  時価総額: ${market_cap/1_000_000_000:.2f}B")
                    elif market_cap >= 1_000_000:
                        report_lines.append(f"  時価総額: ${market_cap/1_000_000:.2f}M")
                if financial_data.get('enterprise_value'):
                    ev = financial_data['enterprise_value']
                    if ev >= 1_000_000_000_000:
                        report_lines.append(f"  企業価値(EV): ${ev/1_000_000_000_000:.2f}T")
                    elif ev >= 1_000_000_000:
                        report_lines.append(f"  企業価値(EV): ${ev/1_000_000_000:.2f}B")
                if financial_data.get('shares_outstanding'):
                    shares = financial_data['shares_outstanding']
                    if shares >= 1_000_000_000:
                        report_lines.append(f"  発行済み株式数: {shares/1_000_000_000:.2f}B株")
                    elif shares >= 1_000_000:
                        report_lines.append(f"  発行済み株式数: {shares/1_000_000:.2f}M株")
                report_lines.append("")
                
                # 財務比率
                report_lines.append("💰 財務比率（バリュエーション）")
                if financial_data.get('pe_ratio'):
                    pe = financial_data['pe_ratio']
                    pe_eval = self._evaluate_indicator(pe, 25, 15, is_higher_better=False)
                    report_lines.append(f"  PER（株価収益率）: {pe_eval}")
                if financial_data.get('forward_pe'):
                    fpe = financial_data['forward_pe']
                    fpe_eval = self._evaluate_indicator(fpe, 25, 15, is_higher_better=False)
                    report_lines.append(f"  予想PER: {fpe_eval}")
                if financial_data.get('peg_ratio'):
                    peg = financial_data['peg_ratio']
                    if peg:
                        if peg < 1.0:
                            peg_eval = f"✅ 割安 ({peg:.2f})"
                        elif peg < 1.5:
                            peg_eval = f"✓ 適正 ({peg:.2f})"
                        else:
                            peg_eval = f"⚠ やや高め ({peg:.2f})"
                        report_lines.append(f"  PEG（PER成長率比）: {peg_eval}")
                if financial_data.get('pb_ratio'):
                    pb = financial_data['pb_ratio']
                    if pb and pb > 0:
                        pb_eval = self._evaluate_indicator(pb, 3, 1.5, is_higher_better=False)
                        report_lines.append(f"  PBR（株価純資産倍率）: {pb_eval}")
                if financial_data.get('ps_ratio'):
                    ps = financial_data['ps_ratio']
                    ps_eval = self._evaluate_indicator(ps, 5, 2, is_higher_better=False)
                    report_lines.append(f"  PSR（株価売上高倍率）: {ps_eval}")
                if financial_data.get('ev_to_revenue'):
                    ev_rev = financial_data['ev_to_revenue']
                    ev_rev_eval = self._evaluate_indicator(ev_rev, 5, 2, is_higher_better=False)
                    report_lines.append(f"  EV/売上高: {ev_rev_eval}")
                if financial_data.get('ev_to_ebitda'):
                    ev_ebitda = financial_data['ev_to_ebitda']
                    ev_ebitda_eval = self._evaluate_indicator(ev_ebitda, 15, 10, is_higher_better=False)
                    report_lines.append(f"  EV/EBITDA: {ev_ebitda_eval}")
                report_lines.append("")
                
                # 収益性指標
                report_lines.append("💵 収益性指標")
                if financial_data.get('profit_margin'):
                    pm = financial_data['profit_margin'] * 100
                    pm_eval = self._format_percentage(pm, is_growth=False)
                    report_lines.append(f"  純利益率: {pm_eval}")
                if financial_data.get('operating_margin'):
                    om = financial_data['operating_margin'] * 100
                    om_eval = self._format_percentage(om, is_growth=False)
                    report_lines.append(f"  営業利益率: {om_eval}")
                if financial_data.get('gross_margin'):
                    gm = financial_data['gross_margin'] * 100
                    gm_eval = self._format_percentage(gm, is_growth=False)
                    report_lines.append(f"  粗利率: {gm_eval}")
                if financial_data.get('roe'):
                    roe = financial_data['roe'] * 100
                    roe_eval = self._format_percentage(roe, is_growth=False)
                    report_lines.append(f"  ROE（自己資本利益率）: {roe_eval}")
                if financial_data.get('roa'):
                    roa = financial_data['roa'] * 100
                    roa_eval = self._format_percentage(roa, is_growth=False)
                    report_lines.append(f"  ROA（総資産利益率）: {roa_eval}")
                report_lines.append("")
                
                # 成長指標
                report_lines.append("🚀 成長指標")
                if financial_data.get('revenue_growth'):
                    report_lines.append(f"  売上成長率: {financial_data['revenue_growth']*100:+.2f}%")
                if financial_data.get('earnings_growth'):
                    report_lines.append(f"  利益成長率: {financial_data['earnings_growth']*100:+.2f}%")
                if financial_data.get('earnings_quarterly_growth'):
                    report_lines.append(f"  四半期利益成長率: {financial_data['earnings_quarterly_growth']*100:+.2f}%")
                if financial_data.get('eps_growth'):
                    report_lines.append(f"  EPS成長率（予想）: {financial_data['eps_growth']:+.2f}%")
                if financial_data.get('eps_current') and financial_data.get('eps_forward'):
                    report_lines.append(f"  EPS（実績）: ${financial_data['eps_current']:.2f}")
                    report_lines.append(f"  EPS（予想）: ${financial_data['eps_forward']:.2f}")
                report_lines.append("")
                
                # 財務健全性
                report_lines.append("🏦 財務健全性")
                if financial_data.get('debt_to_equity'):
                    dte = financial_data['debt_to_equity']
                    dte_eval = self._evaluate_indicator(dte, 1.0, 0.5, is_higher_better=False)
                    report_lines.append(f"  負債資本比率: {dte_eval}")
                if financial_data.get('current_ratio'):
                    cr = financial_data['current_ratio']
                    cr_eval = self._evaluate_indicator(cr, 1.5, 2.0, is_higher_better=True)
                    report_lines.append(f"  流動比率: {cr_eval}")
                if financial_data.get('quick_ratio'):
                    qr = financial_data['quick_ratio']
                    qr_eval = self._evaluate_indicator(qr, 1.0, 1.5, is_higher_better=True)
                    report_lines.append(f"  当座比率: {qr_eval}")
                if financial_data.get('interest_coverage'):
                    ic = financial_data['interest_coverage']
                    ic_eval = self._evaluate_indicator(ic, 5, 10, is_higher_better=True)
                    report_lines.append(f"  利払い能力（EBIT/利息）: {ic_eval}")
                if financial_data.get('total_debt') and financial_data.get('total_cash'):
                    debt = financial_data['total_debt']
                    cash = financial_data['total_cash']
                    net_debt = debt - cash
                    if debt >= 1_000_000_000:
                        report_lines.append(f"  総負債: ${debt/1_000_000_000:.2f}B")
                    if cash >= 1_000_000_000:
                        report_lines.append(f"  現金・預金: ${cash/1_000_000_000:.2f}B")
                    if net_debt >= 1_000_000_000:
                        report_lines.append(f"  純負債: ${net_debt/1_000_000_000:.2f}B")
                    elif net_debt <= -1_000_000_000:
                        report_lines.append(f"  純現金: ${abs(net_debt)/1_000_000_000:.2f}B")
                report_lines.append("")
                
                # キャッシュフロー
                report_lines.append("キャッシュフロー")
                if financial_data.get('free_cashflow'):
                    fcf = financial_data['free_cashflow']
                    if abs(fcf) >= 1_000_000_000:
                        report_lines.append(f"  フリーキャッシュフロー: ${fcf/1_000_000_000:.2f}B")
                    elif abs(fcf) >= 1_000_000:
                        report_lines.append(f"  フリーキャッシュフロー: ${fcf/1_000_000:.2f}M")
                if financial_data.get('operating_cashflow'):
                    ocf = financial_data['operating_cashflow']
                    if abs(ocf) >= 1_000_000_000:
                        report_lines.append(f"  営業キャッシュフロー: ${ocf/1_000_000_000:.2f}B")
                report_lines.append("")
                
                # 配当情報
                report_lines.append("💎 配当情報")
                if financial_data.get('dividend_yield'):
                    div_yield = financial_data['dividend_yield']
                    if div_yield > 1.0:
                        div_yield_pct = div_yield
                    else:
                        div_yield_pct = div_yield * 100
                    if div_yield_pct > 4:
                        div_eval = f"💰 高配当 ({div_yield_pct:.2f}%)"
                    elif div_yield_pct > 2:
                        div_eval = f"✓ 配当あり ({div_yield_pct:.2f}%)"
                    elif div_yield_pct > 0:
                        div_eval = f"✓ 低配当 ({div_yield_pct:.2f}%)"
                    else:
                        div_eval = "⚠ 配当なし"
                    report_lines.append(f"  配当利回り: {div_eval}")
                if financial_data.get('dividend_rate'):
                    report_lines.append(f"  1株当たり配当: ${financial_data['dividend_rate']:.2f}")
                if financial_data.get('payout_ratio'):
                    po = financial_data['payout_ratio'] * 100
                    if po > 100:
                        po_eval = f"⚠ 配当性向高め ({po:.1f}%)"
                    elif po > 50:
                        po_eval = f"✓ 適正 ({po:.1f}%)"
                    else:
                        po_eval = f"✓ 低め ({po:.1f}%)"
                    report_lines.append(f"  配当性向: {po_eval}")
                if financial_data.get('five_year_avg_dividend_yield'):
                    avg_yield = financial_data['five_year_avg_dividend_yield']
                    if avg_yield > 1.0:
                        avg_yield_pct = avg_yield
                    else:
                        avg_yield_pct = avg_yield * 100
                    report_lines.append(f"  5年平均配当利回り: {avg_yield_pct:.2f}%")
                report_lines.append("")
                
                # 売上・利益情報
                report_lines.append("売上・利益情報")
                if financial_data.get('total_revenue'):
                    revenue = financial_data['total_revenue']
                    if revenue >= 1_000_000_000_000:
                        report_lines.append(f"  総売上高: ${revenue/1_000_000_000_000:.2f}T")
                    elif revenue >= 1_000_000_000:
                        report_lines.append(f"  総売上高: ${revenue/1_000_000_000:.2f}B")
                    elif revenue >= 1_000_000:
                        report_lines.append(f"  総売上高: ${revenue/1_000_000:.2f}M")
                if financial_data.get('revenue_per_share'):
                    report_lines.append(f"  1株当たり売上: ${financial_data['revenue_per_share']:.2f}")
                if financial_data.get('earnings_per_share'):
                    report_lines.append(f"  1株当たり利益(EPS): ${financial_data['earnings_per_share']:.2f}")
                report_lines.append("")
                
                # 決算・配当スケジュール
                report_lines.append("決算・配当スケジュール")
                if financial_data.get('most_recent_quarter'):
                    try:
                        # Unixタイムスタンプを日付に変換
                        quarter_ts = financial_data['most_recent_quarter']
                        if isinstance(quarter_ts, (int, float)):
                            quarter_date = datetime.fromtimestamp(quarter_ts).strftime('%Y-%m-%d')
                            report_lines.append(f"  直近決算日: {quarter_date}")
                    except:
                        pass
                if financial_data.get('next_fiscal_year_end'):
                    try:
                        fiscal_ts = financial_data['next_fiscal_year_end']
                        if isinstance(fiscal_ts, (int, float)):
                            fiscal_date = datetime.fromtimestamp(fiscal_ts).strftime('%Y-%m-%d')
                            report_lines.append(f"  次回決算予定日: {fiscal_date}")
                    except:
                        pass
                if financial_data.get('ex_dividend_date'):
                    try:
                        ex_div_ts = financial_data['ex_dividend_date']
                        if isinstance(ex_div_ts, (int, float)):
                            ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d')
                            report_lines.append(f"  配当権利落ち日: {ex_div_date}")
                    except:
                        pass
                if financial_data.get('dividend_date'):
                    try:
                        div_ts = financial_data['dividend_date']
                        if isinstance(div_ts, (int, float)):
                            div_date = datetime.fromtimestamp(div_ts).strftime('%Y-%m-%d')
                            report_lines.append(f"  配当支払日: {div_date}")
                    except:
                        pass
                report_lines.append("")
                
                # 過去の業績
                if financial_data.get('latest_quarter_revenue') or financial_data.get('latest_quarter_earnings'):
                    report_lines.append("直近四半期業績")
                    if financial_data.get('latest_quarter_revenue'):
                        revenue = financial_data['latest_quarter_revenue']
                        if revenue >= 1_000_000_000:
                            report_lines.append(f"  四半期売上高: ${revenue/1_000_000_000:.2f}B")
                        elif revenue >= 1_000_000:
                            report_lines.append(f"  四半期売上高: ${revenue/1_000_000:.2f}M")
                    if financial_data.get('latest_quarter_earnings'):
                        earnings = financial_data['latest_quarter_earnings']
                        if abs(earnings) >= 1_000_000_000:
                            report_lines.append(f"  四半期利益: ${earnings/1_000_000_000:.2f}B")
                        elif abs(earnings) >= 1_000_000:
                            report_lines.append(f"  四半期利益: ${earnings/1_000_000:.2f}M")
                    report_lines.append("")
                
                # セクター・業界情報
                if financial_data.get('sector') or financial_data.get('industry'):
                    report_lines.append("セクター・業界情報")
                    if financial_data.get('sector'):
                        report_lines.append(f"  セクター: {financial_data['sector']}")
                    if financial_data.get('industry'):
                        report_lines.append(f"  業界: {financial_data['industry']}")
                    report_lines.append("")
                
                # アナリスト評価
                report_lines.append("アナリスト評価")
                if analyst_data.get('number_of_analysts'):
                    report_lines.append(f"  アナリスト数: {analyst_data['number_of_analysts']}名")
                if analyst_data.get('recommendation'):
                    report_lines.append(f"  推奨: {analyst_data['recommendation']}")
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    target = analyst_data['target_mean_price']
                    current = analyst_data['current_price']
                    upside = ((target - current) / current) * 100 if current > 0 else 0
                    report_lines.append(f"  目標株価（平均）: ${target:.2f}")
                    report_lines.append(f"  現在価格: ${current:.2f}")
                    report_lines.append(f"  上昇余地: {upside:+.1f}%")
                if analyst_data.get('target_high_price'):
                    report_lines.append(f"  目標株価（最高）: ${analyst_data['target_high_price']:.2f}")
                if analyst_data.get('target_low_price'):
                    report_lines.append(f"  目標株価（最低）: ${analyst_data['target_low_price']:.2f}")
                if analyst_data.get('eps_current') and analyst_data.get('eps_forward'):
                    eps_current = analyst_data['eps_current']
                    eps_forward = analyst_data['eps_forward']
                    if eps_current > 0:
                        eps_growth = ((eps_forward - eps_current) / abs(eps_current)) * 100
                        report_lines.append(f"  EPS成長率（予想）: {eps_growth:+.1f}%")
                report_lines.append("")
                
                # 投資スコア情報（既存の情報を再表示）
                report_lines.append("📊 投資スコア詳細")
                report_lines.append(f"  総合スコア: {top_data['investment_score']:.1f}/100点")
                
                # 各スコアの可視化
                value_score = top_data.get('value_score', 0)
                momentum_score = top_data.get('momentum_score', 0)
                stability_score = top_data.get('stability_score', 0)
                
                report_lines.append(f"  • Value（割安度）: {self._create_score_bar(value_score, 100, 20)}")
                report_lines.append(f"  • Momentum（反転）: {self._create_score_bar(momentum_score, 100, 20)}")
                report_lines.append(f"  • Stability（安定性）: {self._create_score_bar(stability_score, 100, 20)}")
                report_lines.append("")
                
                # 強み・弱みの分析
                report_lines.append("💪 強み・弱み分析")
                strengths = []
                weaknesses = []
                
                # 強みの判定
                if value_score >= 60:
                    strengths.append("✅ 割安度が高い")
                if momentum_score >= 60:
                    strengths.append("✅ 反転の可能性あり")
                if stability_score >= 70:
                    strengths.append("✅ 財務安定性が高い")
                if financial_data.get('roe') and financial_data['roe'] > 0.15:
                    strengths.append("✅ ROEが高い（収益性良好）")
                if financial_data.get('revenue_growth') and financial_data['revenue_growth'] > 0.1:
                    strengths.append("✅ 売上成長率が高い")
                if financial_data.get('dividend_yield') and financial_data['dividend_yield'] > 0.02:
                    strengths.append("✅ 配当利回りが良好")
                if analyst_data.get('recommendation') in ['買い', '強気買い']:
                    strengths.append("✅ アナリスト推奨が良好")
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    upside = ((analyst_data['target_mean_price'] - analyst_data['current_price']) / analyst_data['current_price']) * 100
                    if upside > 15:
                        strengths.append("✅ 目標株価の上昇余地が大きい")
                
                # 弱みの判定
                if value_score < 30:
                    weaknesses.append("⚠ 割安度が低い")
                if momentum_score < 30:
                    weaknesses.append("⚠ 反転の兆しが弱い")
                if stability_score < 50:
                    weaknesses.append("⚠ 財務安定性に懸念")
                if financial_data.get('debt_to_equity') and financial_data['debt_to_equity'] > 1.0:
                    weaknesses.append("⚠ 負債比率が高い")
                if financial_data.get('current_ratio') and financial_data['current_ratio'] < 1.0:
                    weaknesses.append("⚠ 流動比率が低い（流動性懸念）")
                if financial_data.get('profit_margin') and financial_data['profit_margin'] < 0.05:
                    weaknesses.append("⚠ 利益率が低い")
                if financial_data.get('revenue_growth') and financial_data['revenue_growth'] < -0.1:
                    weaknesses.append("⚠ 売上が減少傾向")
                
                if strengths:
                    report_lines.append("  【強み】")
                    for strength in strengths:
                        report_lines.append(f"    {strength}")
                else:
                    report_lines.append("  【強み】特になし")
                
                if weaknesses:
                    report_lines.append("  【弱み・懸念点】")
                    for weakness in weaknesses:
                        report_lines.append(f"    {weakness}")
                else:
                    report_lines.append("  【弱み・懸念点】特に大きな懸念なし")
                
                report_lines.append("")
                
                # 基本情報（既存）
                report_lines.append("基本情報")
                report_lines.append(f"  現在価格: ${top_data['current_price']:,.2f}")
                if top_data.get('ath_ratio'):
                    ath_pct = (1 - top_data['ath_ratio']) * 100
                    report_lines.append(f"  ATH比: {top_data['ath_ratio']:.1%} (ATHから{ath_pct:.1f}%下落)")
                report_lines.append("")
                
                # 投資判断の推奨アクション
                report_lines.append("🎯 投資判断の推奨アクション")
                report_lines.append("-" * 80)
                
                investment_stance = top_data.get('investment_stance', '様子見')
                investment_score = top_data['investment_score']
                
                if investment_stance == "積極的買い":
                    report_lines.append("  🟢【積極的買い推奨】")
                    report_lines.append("    複数の好材料が重なっており、積極的な買いが推奨されます。")
                    report_lines.append("    ・急落後の反転局面または割安水準")
                    report_lines.append("    ・回復余地が大きい")
                    report_lines.append("    ・質が高いまたは改善傾向")
                elif investment_stance == "買い":
                    report_lines.append("  🟡【買い推奨】")
                    report_lines.append("    買いシグナルが出ていますが、リスク管理を心がけてください。")
                    report_lines.append("    ・割安または急落後の回復余地あり")
                    report_lines.append("    ・適切なポジションサイズで投資を検討")
                elif investment_stance == "様子見":
                    report_lines.append("  🟠【様子見推奨】")
                    report_lines.append("    現時点では様子見が適切です。")
                    report_lines.append("    ・反転の兆しを待つ")
                    report_lines.append("    ・追加情報を確認してから判断")
                else:
                    report_lines.append("  🔴【慎重に】")
                    report_lines.append("    現時点での投資は慎重に検討してください。")
                    report_lines.append("    ・リスク要因が多い")
                    report_lines.append("    ・より良いタイミングを待つことを推奨")
                
                report_lines.append("")
                report_lines.append(f"  投資スタンス: {investment_stance}")
                report_lines.append(f"  リスクレベル: {top_data.get('risk_level', '中')}")
                report_lines.append(f"  現在の状態: {top_data.get('current_state', 'NORMAL')}")
                report_lines.append("")
                
                # 状態と信頼度
                report_lines.append(f"📅 データ取得情報")
                report_lines.append(f"  信頼度: {top_data.get('current_state', 'NORMAL')} | 状態: {top_data.get('current_state', 'NORMAL')} | カテゴリ: {top_data.get('category', 'N/A')}")
                report_lines.append(f"  時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                report_lines.append(f"  詳細: https://finance.yahoo.com/quote/{symbol}")
                report_lines.append("")
        
        report_lines.append("=" * 120)
        report_lines.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(report_lines)
    
    def generate_investment_report(self, symbols: List[str], top_n: int = 10, max_assets: Optional[int] = None) -> str:
        """
        投資推奨レポートを生成（詳細版：スコア内訳・根拠・可視化付き）
        max_assets: 分析する最大資産数（Noneの場合は全資産）
        """
        results = self.analyze_all_assets(symbols, max_assets=max_assets)
        top_results = results[:top_n]
        
        if not top_results:
            return "分析対象の資産が見つかりませんでした。"
        
        report_lines = []
        
        # ヘッダー
        report_lines.append("=" * 120)
        report_lines.append(" " * 40 + "投資推奨レポート（Top 10）")
        report_lines.append(" " * 35 + "全資産クラス横断比較分析")
        report_lines.append("=" * 120)
        report_lines.append("")
        
        # サマリーテーブル（状態フラグ追加）
        report_lines.append("【サマリー】")
        report_lines.append("-" * 120)
        report_lines.append(f"| Rank | 資産名 | カテゴリ | 状態 | Score | Value | Momentum | Stability | リスク | 投資スタンス |")
        report_lines.append(f"|------|--------|----------|------|-------|-------|----------|-----------|--------|--------------|")
        
        for rank, data in enumerate(top_results, 1):
            symbol = data['symbol']
            category = data['category']
            state = data['current_state']
            score = data['investment_score']
            value_score = data.get('value_score', 0)
            momentum_score = data.get('momentum_score', 0)
            stability_score = data.get('stability_score', 0)
            risk = data['risk_level']
            stance = data['investment_stance']
            
            report_lines.append(
                f"| {rank:2d}  | {symbol:6s} | {category:8s} | {state:5s} | "
                f"{score:5.0f} | {value_score:5.0f} | {momentum_score:8.0f} | "
                f"{stability_score:9.0f} | {risk:4s} | {stance:10s} |"
            )
        
        report_lines.append("")
        report_lines.append("=" * 120)
        report_lines.append("")
        
        # 各資産の詳細
        for rank, data in enumerate(top_results, 1):
            symbol = data['symbol']
            category = data['category']
            
            report_lines.append("")
            report_lines.append("█" * 120)
            report_lines.append(f"  【Rank {rank}】 {symbol} ({category})")
            report_lines.append("█" * 120)
            report_lines.append("")
            
            # 基本情報
            report_lines.append("【基本情報】")
            report_lines.append(f"  現在価格: ${data['current_price']:,.2f}")
            report_lines.append(f"  投資スコア: {data['investment_score']:.1f}/100点")
            report_lines.append(f"  投資スタンス: {data['investment_stance']}")
            report_lines.append(f"  リスクレベル: {data['risk_level']}")
            report_lines.append(f"  現在の状態: {data['current_state']}")
            report_lines.append("")
            
            # 企業情報（米国株の場合のみ）
            if not is_crypto_symbol(symbol):
                company_info = self.get_company_info(symbol)
                analyst_data = self.get_analyst_recommendations(symbol)
                
                # 企業情報セクション
                report_lines.append("【企業情報】")
                if company_info.get('company_name'):
                    report_lines.append(f"  企業名: {company_info['company_name']}")
                if company_info.get('sector'):
                    report_lines.append(f"  セクター: {company_info['sector']}")
                if company_info.get('industry'):
                    report_lines.append(f"  業界: {company_info['industry']}")
                if company_info.get('full_time_employees'):
                    employees = company_info['full_time_employees']
                    if employees >= 1000:
                        employees_str = f"{employees/1000:.1f}千人"
                    else:
                        employees_str = f"{employees}人"
                    report_lines.append(f"  従業員数: {employees_str}")
                if company_info.get('website'):
                    report_lines.append(f"  ウェブサイト: {company_info['website']}")
                if company_info.get('city') and company_info.get('country'):
                    location = f"{company_info['city']}"
                    if company_info.get('state'):
                        location += f", {company_info['state']}"
                    location += f", {company_info['country']}"
                    report_lines.append(f"  所在地: {location}")
                report_lines.append("")
                
                # 企業概要
                if company_info.get('business_summary'):
                    summary = company_info['business_summary']
                    # 長すぎる場合は最初の800文字に制限
                    if len(summary) > 800:
                        summary = summary[:800] + "..."
                    report_lines.append("【企業概要】")
                    # 複数行に分割して表示（100文字ごと）
                    words = summary.split()
                    current_line = "  "
                    for word in words:
                        if len(current_line) + len(word) + 1 > 100:
                            report_lines.append(current_line)
                            current_line = "  " + word
                        else:
                            if current_line != "  ":
                                current_line += " "
                            current_line += word
                    if current_line != "  ":
                        report_lines.append(current_line)
                    report_lines.append("")
                
                # アナリスト評価セクション
                report_lines.append("【アナリスト評価】")
                if analyst_data.get('number_of_analysts'):
                    report_lines.append(f"  アナリスト数: {analyst_data['number_of_analysts']}名")
                if analyst_data.get('recommendation'):
                    report_lines.append(f"  推奨: {analyst_data['recommendation']}")
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    target = analyst_data['target_mean_price']
                    current = analyst_data['current_price']
                    upside = ((target - current) / current) * 100 if current > 0 else 0
                    report_lines.append(f"  目標株価（平均）: ${target:.2f}")
                    report_lines.append(f"  現在価格: ${current:.2f}")
                    report_lines.append(f"  上昇余地: {upside:+.1f}%")
                if analyst_data.get('target_high_price'):
                    report_lines.append(f"  目標株価（最高）: ${analyst_data['target_high_price']:.2f}")
                if analyst_data.get('target_low_price'):
                    report_lines.append(f"  目標株価（最低）: ${analyst_data['target_low_price']:.2f}")
                report_lines.append("")
            
            # スコア内訳（3要素）
            value_score = data.get('value_score', 0)
            momentum_score = data.get('momentum_score', 0)
            stability_score = data.get('stability_score', 0)
            total_score = data['investment_score']
            
            report_lines.append("【投資スコア内訳（3要素）】")
            report_lines.append(f"  Value（割安度）:    {self._create_score_bar(value_score, 100, 30)} (重み40%)")
            report_lines.append(f"  Momentum（反転）:   {self._create_score_bar(momentum_score, 100, 30)} (重み35%)")
            report_lines.append(f"  Stability（安定性）: {self._create_score_bar(stability_score, 100, 30)} (重み25%)")
            report_lines.append(f"  ────────────────────────────────────────────────────────────────")
            report_lines.append(f"  合計スコア:         {self._create_score_bar(total_score, 100, 30)}")
            
            # BUY資格チェック
            buy_qualified = data.get('buy_qualified', False)
            buy_reasons = data.get('buy_reasons', [])
            if buy_qualified:
                report_lines.append(f"  ✓ BUY資格: あり ({', '.join(buy_reasons)})")
            else:
                report_lines.append(f"  ⚠ BUY資格: なし ({', '.join(buy_reasons)})")
            report_lines.append("")
            
            # 詳細指標
            report_lines.append("【詳細指標】")
            
            # ATH比
            if data['ath_ratio']:
                ath_pct = (1 - data['ath_ratio']) * 100
                report_lines.append(f"  ✓ ATH比: {data['ath_ratio']:.1%} (ATHから{ath_pct:.1f}%下落)")
                if data['ath_ratio'] < 0.5:
                    report_lines.append(f"    → 大幅割安（ATH比50%未満）")
                elif data['ath_ratio'] < 0.7:
                    report_lines.append(f"    → 割安（ATH比70%未満）")
                elif data['ath_ratio'] < 0.85:
                    report_lines.append(f"    → やや割安（ATH比85%未満）")
            else:
                report_lines.append(f"  - ATH比: データなし")
            
            # 直近価格変動
            if data['recent_drop']:
                if data['recent_drop'] < 0:
                    report_lines.append(f"  ✓ 30日間変動率: {data['recent_drop']:.2f}% (下落)")
                    if data['recent_drop'] < -20:
                        report_lines.append(f"    → 大幅下落（20%以上）")
                    elif data['recent_drop'] < -10:
                        report_lines.append(f"    → 急落（10%以上）")
                    elif data['recent_drop'] < -5:
                        report_lines.append(f"    → 下落（5%以上）")
                else:
                    report_lines.append(f"  ✓ 30日間変動率: +{data['recent_drop']:.2f}% (上昇)")
            else:
                report_lines.append(f"  - 30日間変動率: データなし")
            
            # ボラティリティ
            if data['volatility']:
                report_lines.append(f"  ✓ ボラティリティ: {data['volatility']:.2f}%")
                if data['volatility'] > 5:
                    report_lines.append(f"    → 高ボラティリティ（リスク高）")
                elif data['volatility'] > 3:
                    report_lines.append(f"    → 中ボラティリティ（リスク中）")
                else:
                    report_lines.append(f"    → 低ボラティリティ（リスク低）")
            else:
                report_lines.append(f"  - ボラティリティ: データなし")
            
            # 質の評価
            report_lines.append(f"  ✓ 質スコア: {data['quality_score']}/5")
            report_lines.append(f"    → {data['quality_reason']}")
            
            report_lines.append("")
            
            # 投資判断の根拠
            report_lines.append("【投資判断の根拠】")
            reasons = []
            
            # ATH比による根拠
            if data['ath_ratio']:
                if data['ath_ratio'] < 0.5:
                    reasons.append(f"ATH比{data['ath_ratio']:.0%}で大幅割安（過去最高値から{(1-data['ath_ratio'])*100:.0f}%下落）")
                elif data['ath_ratio'] < 0.7:
                    reasons.append(f"ATH比{data['ath_ratio']:.0%}で割安（過去最高値から{(1-data['ath_ratio'])*100:.0f}%下落）")
            
            # 急落による根拠
            if data['recent_drop'] and data['recent_drop'] < -10:
                reasons.append(f"直近30日間で{abs(data['recent_drop']):.1f}%下落しており、急落局面にある")
            
            # 反転シグナル
            if data['current_state'] == 'BUY':
                reasons.append("反転シグナル検出（急落→低迷→反転の局面）")
            elif data['current_state'] == 'BASE':
                reasons.append("低迷継続中（反転の準備段階）")
            elif data['current_state'] == 'WATCH':
                reasons.append("急落検知（WATCH状態）")
            
            # 回復余地
            if data['recovery_potential']:
                reasons.append(f"回復余地あり: {data['recovery_reason']}")
            
            # 質の評価
            if data['quality_score'] >= 4:
                reasons.append(f"質が高い（スコア{data['quality_score']}/5）: {data['quality_reason']}")
            elif data['quality_score'] <= 2:
                reasons.append(f"質に注意（スコア{data['quality_score']}/5）: {data['quality_reason']}")
            
            # 財務指標（米国株の場合）
            if not is_crypto_symbol(symbol):
                metrics = self.get_stock_metrics(symbol)
                if metrics.get('pe_ratio'):
                    pe = metrics['pe_ratio']
                    if 10 <= pe <= 25:
                        reasons.append(f"PER {pe:.1f}倍で適正水準")
                    elif pe < 10:
                        reasons.append(f"PER {pe:.1f}倍で割安")
                    elif pe > 50:
                        reasons.append(f"PER {pe:.1f}倍で高PER（成長期待）")
                
                dividend_yield = metrics.get('dividend_yield')
                if dividend_yield and dividend_yield > 0.02:
                    # Yahoo FinanceのdividendYieldは小数形式（0.0042 = 0.42%）で返される
                    # ただし、既にパーセンテージ形式（>1.0）の場合は100で割る
                    if dividend_yield > 1.0:
                        dividend_yield_pct = dividend_yield
                    else:
                        dividend_yield_pct = dividend_yield * 100
                    reasons.append(f"配当利回り{dividend_yield_pct:.2f}%で配当あり")
                
                if metrics.get('market_cap'):
                    market_cap = metrics['market_cap']
                    if market_cap > 100_000_000_000:
                        reasons.append(f"時価総額${market_cap/1_000_000_000:.0f}Bで大型株（流動性高）")
            
            # 根拠を番号付きで表示
            if reasons:
                for i, reason in enumerate(reasons, 1):
                    report_lines.append(f"  {i}. {reason}")
            else:
                report_lines.append(f"  - 総合的な評価による推奨")
            
            report_lines.append("")
            
            # リスク要因
            report_lines.append("【リスク要因】")
            risk_factors = []
            
            if data['volatility'] and data['volatility'] > 5:
                risk_factors.append(f"高ボラティリティ（{data['volatility']:.2f}%）により価格変動が大きい")
            
            if data['recent_drop'] and data['recent_drop'] < -20:
                risk_factors.append("大幅下落中で、さらに下落する可能性がある")
            
            if data['quality_score'] <= 2:
                risk_factors.append(f"質スコアが低い（{data['quality_score']}/5）")
            
            if not is_crypto_symbol(symbol):
                metrics = self.get_stock_metrics(symbol)
                if metrics.get('pe_ratio') and metrics['pe_ratio'] > 50:
                    risk_factors.append(f"高PER（{metrics['pe_ratio']:.1f}倍）で割高の可能性")
            
            if risk_factors:
                for i, risk in enumerate(risk_factors, 1):
                    report_lines.append(f"  ⚠ {i}. {risk}")
            else:
                report_lines.append(f"  ✓ 特に大きなリスク要因は見当たりません")
            
            report_lines.append("")
            
            # 投資スタンスの詳細
            report_lines.append("【投資スタンス詳細】")
            stance = data['investment_stance']
            if stance == "積極的買い":
                report_lines.append(f"  → {stance}: 投資スコア{data['investment_score']:.1f}点で、複数の好材料が重なっています")
                report_lines.append(f"    ・急落後の反転局面または割安水準")
                report_lines.append(f"    ・回復余地が大きい")
                report_lines.append(f"    ・質が高いまたは改善傾向")
            elif stance == "買い":
                report_lines.append(f"  → {stance}: 投資スコア{data['investment_score']:.1f}点で、買いシグナルが出ています")
                report_lines.append(f"    ・割安または急落後の回復余地あり")
            elif stance == "様子見":
                report_lines.append(f"  → {stance}: 投資スコア{data['investment_score']:.1f}点で、現時点では様子見が適切です")
            else:
                report_lines.append(f"  → {stance}: 投資スコア{data['investment_score']:.1f}点")
            
            report_lines.append("")
        
        # フッター
        report_lines.append("")
        report_lines.append("=" * 120)
        report_lines.append("【重要事項】")
        report_lines.append("  • 本レポートは自動生成された投資分析であり、投資判断の参考情報です")
        report_lines.append("  • 実際の投資判断は自己責任で行ってください")
        report_lines.append("  • 過去の実績は将来の成果を保証するものではありません")
        report_lines.append("  • 分散投資とリスク管理を心がけてください")
        report_lines.append("")
        report_lines.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 120)
        
        return "\n".join(report_lines)
