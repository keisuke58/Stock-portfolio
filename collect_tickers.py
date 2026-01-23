"""
有望株ティッカー自動収集スクリプト
S&P500、NASDAQ、NYSEから有望株を収集してconfig.jsonに追加
"""
import json
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import time
from typing import List, Set, Dict
import sys
import io
import urllib.request
import csv

# Windowsのコンソールエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_sp500_tickers() -> List[str]:
    """WikipediaからS&P500のティッカーを取得"""
    print("📊 S&P500ティッカーを取得中...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 複数のテーブルを探す
        table = soup.find('table', {'id': 'constituents'})
        if not table:
            # 別のIDやクラスで探す
            table = soup.find('table', {'class': 'wikitable sortable'})
        
        tickers = []
        if table:
            rows = table.find_all('tr')[1:]  # ヘッダーをスキップ
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    ticker = cells[0].text.strip()
                    # クラスA株などの表記を除去
                    ticker = ticker.split('.')[0].split()[0]
                    # 無効な文字を除去
                    ticker = ''.join(c for c in ticker if c.isalnum() or c == '-')
                    if ticker and 1 <= len(ticker) <= 5:
                        tickers.append(ticker)
        
        print(f"  ✓ {len(tickers)}件のS&P500ティッカーを取得")
        return tickers
    except Exception as e:
        print(f"  ✗ S&P500取得エラー: {e}")
        # フォールバック: 主要なS&P500銘柄を手動で追加
        print("  → フォールバック: 主要S&P500銘柄を追加")
        return get_major_sp500_fallback()


def get_major_sp500_fallback() -> List[str]:
    """主要なS&P500銘柄（フォールバック）"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
        'UNH', 'XOM', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
        'ABBV', 'COST', 'ADBE', 'MRK', 'PEP', 'TMO', 'CSCO', 'WMT', 'DIS',
        'ABT', 'ACN', 'DHR', 'VZ', 'NFLX', 'CMCSA', 'NKE', 'PM', 'TXN',
        'LIN', 'BMY', 'QCOM', 'INTU', 'AMGN', 'HON', 'RTX', 'ISRG', 'AMAT',
        'GE', 'LOW', 'BKNG', 'ADP', 'SBUX', 'GILD', 'C', 'AXP', 'MDT', 'TJX'
    ]


def get_nasdaq_tickers() -> List[str]:
    """NASDAQの主要銘柄を取得（Wikipediaから）"""
    print("📊 NASDAQティッカーを取得中...")
    try:
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table', {'class': 'wikitable'})
        
        tickers = []
        for table in tables:
            rows = table.find_all('tr')[1:]  # ヘッダーをスキップ
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells and len(cells) > 0:
                    ticker = cells[0].text.strip()
                    ticker = ticker.split('.')[0].split()[0]
                    ticker = ''.join(c for c in ticker if c.isalnum() or c == '-')
                    if ticker and 1 <= len(ticker) <= 5:
                        tickers.append(ticker)
        
        print(f"  ✓ {len(tickers)}件のNASDAQティッカーを取得")
        return tickers
    except Exception as e:
        print(f"  ✗ NASDAQ取得エラー: {e}")
        # フォールバック: 主要なNASDAQ銘柄
        print("  → フォールバック: 主要NASDAQ銘柄を追加")
        return get_major_nasdaq_fallback()


def get_major_nasdaq_fallback() -> List[str]:
    """主要なNASDAQ銘柄（フォールバック）"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO',
        'COST', 'ADBE', 'PEP', 'NFLX', 'CSCO', 'CMCSA', 'INTC', 'AMD',
        'QCOM', 'INTU', 'AMGN', 'ISRG', 'BKNG', 'SBUX', 'GILD', 'ADI',
        'VRSK', 'FISV', 'CTSH', 'FAST', 'KLAC', 'LRCX', 'MCHP', 'MNST',
        'PAYX', 'PCAR', 'SNPS', 'TEAM', 'TMUS', 'VRSN', 'WBD', 'ZS'
    ]


def get_all_nasdaq_listed() -> List[str]:
    """NASDAQ公式FTPから全上場銘柄を取得"""
    print("📊 NASDAQ全上場銘柄を取得中...")
    tickers = []
    
    try:
        # NASDAQ公式FTPサイトから全上場銘柄リストを取得
        nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        
        # NASDAQ上場銘柄
        try:
            response = requests.get(nasdaq_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            response.raise_for_status()
            lines = response.text.strip().split('\n')
            
            # ヘッダー行をスキップ（最初の行は"Symbol|Security Name|Market Category|..."）
            for line in lines[1:]:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) > 0:
                        ticker = parts[0].strip()
                        # 有効なティッカーかチェック
                        if ticker and is_valid_ticker(ticker):
                            tickers.append(ticker.upper())
            
            print(f"  ✓ NASDAQ上場: {len(tickers)}件のティッカーを取得")
        except Exception as e:
            print(f"  ⚠ NASDAQ上場銘柄取得エラー: {e}")
        
        # その他の取引所（NYSE、AMEXなど）の銘柄
        try:
            response = requests.get(other_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            response.raise_for_status()
            lines = response.text.strip().split('\n')
            
            other_count = 0
            # ヘッダー行をスキップ
            for line in lines[1:]:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) > 0:
                        ticker = parts[0].strip()
                        # 有効なティッカーかチェック
                        if ticker and is_valid_ticker(ticker):
                            ticker_upper = ticker.upper()
                            # 重複チェック
                            if ticker_upper not in tickers:
                                tickers.append(ticker_upper)
                                other_count += 1
            
            print(f"  ✓ その他取引所: {other_count}件のティッカーを追加")
        except Exception as e:
            print(f"  ⚠ その他取引所銘柄取得エラー: {e}")
        
        print(f"  ✓ 合計: {len(tickers)}件のNASDAQ/その他取引所ティッカーを取得")
        return tickers
        
    except Exception as e:
        print(f"  ✗ NASDAQ全上場銘柄取得エラー: {e}")
        return []


def get_all_nyse_listed() -> List[str]:
    """NYSE全上場銘柄を取得（Wikipediaやその他のソースから）"""
    print("📊 NYSE全上場銘柄を取得中...")
    tickers = []
    
    try:
        # WikipediaからNYSE上場企業リストを取得
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # S&P500の多くはNYSE上場
        table = soup.find('table', {'id': 'constituents'})
        if not table:
            table = soup.find('table', {'class': 'wikitable sortable'})
        
        if table:
            rows = table.find_all('tr')[1:]  # ヘッダーをスキップ
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    ticker = cells[0].text.strip()
                    ticker = ticker.split('.')[0].split()[0]
                    ticker = ''.join(c for c in ticker if c.isalnum() or c == '-')
                    if ticker and is_valid_ticker(ticker):
                        tickers.append(ticker.upper())
        
        # 追加のNYSE銘柄をWikipediaから取得を試みる
        try:
            # NYSE上場企業のリストページを探す
            nyse_urls = [
                "https://en.wikipedia.org/wiki/List_of_companies_listed_on_the_New_York_Stock_Exchange",
            ]
            
            for url in nyse_urls:
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    tables = soup.find_all('table', {'class': 'wikitable'})
                    
                    for table in tables:
                        rows = table.find_all('tr')[1:]
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if cells:
                                ticker = cells[0].text.strip()
                                ticker = ticker.split('.')[0].split()[0]
                                ticker = ''.join(c for c in ticker if c.isalnum() or c == '-')
                                if ticker and is_valid_ticker(ticker):
                                    ticker_upper = ticker.upper()
                                    if ticker_upper not in tickers:
                                        tickers.append(ticker_upper)
                except:
                    continue
        except Exception as e:
            print(f"  ⚠ NYSE追加取得エラー: {e}")
        
        # 重複除去
        tickers = list(set(tickers))
        print(f"  ✓ {len(tickers)}件のNYSE関連ティッカーを取得")
        return tickers
        
    except Exception as e:
        print(f"  ✗ NYSE全上場銘柄取得エラー: {e}")
        # フォールバック: 既存のNYSE主要銘柄リストを返す
        return get_nyse_major_stocks()


def get_popular_etfs() -> List[str]:
    """人気のETFリスト"""
    etfs = [
        # インデックスETF
        'SPY', 'VOO', 'IVV', 'SPLG',  # S&P500
        'QQQ', 'QQQM', 'ONEQ',  # NASDAQ
        'DIA', 'IWM', 'VTI', 'VT',  # その他インデックス
        
        # セクターETF
        'XLK', 'VGT', 'FTEC',  # テクノロジー
        'XLF', 'VFH',  # 金融
        'XLE', 'VDE',  # エネルギー
        'XLV', 'VHT',  # ヘルスケア
        'XLI', 'VIS',  # 工業
        'XLY', 'VCR',  # 消費者
        'XLP', 'VDC',  # 消費財
        'XLU', 'VPU',  # ユーティリティ
        'XLB', 'VAW',  # 素材
        'XLRE', 'VNQ',  # 不動産
        'XLC', 'VOX',  # 通信
        
        # 半導体
        'SOXX', 'SMH', 'SOXL', 'USD',
        
        # AI/テクノロジー
        'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF',
        'BOTZ', 'ROBO', 'QTUM', 'AIQ',
        
        # バイオテクノロジー
        'XBI', 'IBB', 'LABU', 'CURE',
        
        # クリーンエネルギー
        'ICLN', 'QCLN', 'PBW', 'FAN',
        
        # レバレッジETF
        'SPXL', 'TQQQ', 'TECL', 'FNGU', 'SOXL',
        
        # その他
        'VUG', 'VTV',  # 成長株/バリュー株
        'VEA', 'VWO',  # 国際
    ]
    return etfs


def get_extended_etfs() -> List[str]:
    """拡張されたETFリスト（大幅に増量）"""
    etfs = [
        # S&P500系ETF（拡張）
        'SPY', 'VOO', 'IVV', 'SPLG', 'SPTM', 'SPMD', 'SPSC', 'SPYV', 'SPYG',
        'SPHD', 'SPHB', 'SPHQ', 'SPLV', 'SPMO', 'SPMV', 'SPMW', 'SPXN',
        
        # NASDAQ系ETF（拡張）
        'QQQ', 'QQQM', 'ONEQ', 'QQQJ', 'QTEC', 'QYLD', 'QCLR', 'QQQA',
        'QQQC', 'QQQD', 'QQQE', 'QQQX', 'QQQY', 'QQQZ',
        
        # 小型株ETF（拡張）
        'IWM', 'IJH', 'IJR', 'VB', 'VBR', 'VTHR', 'VTWO', 'VTWG', 'VTWV',
        'SCHA', 'SCHM', 'SCHA', 'SCHA', 'SCHA',
        
        # 国際ETF（拡張）
        'VTI', 'VT', 'VEA', 'VWO', 'VXUS', 'VEU', 'VSS', 'VPL', 'VNM',
        'VGK', 'VTHR', 'VTHR', 'VTHR', 'VTHR',
        
        # 成長/バリューETF（拡張）
        'VUG', 'VTV', 'VTHR', 'VYM', 'VIG', 'VONG', 'VONV', 'VOT', 'VOE',
        'VBR', 'VBK', 'VTHR', 'VTHR', 'VTHR',
        
        # テクノロジーETF（拡張）
        'XLK', 'VGT', 'FTEC', 'IGV', 'IGM', 'SOXX', 'SMH', 'SOXL', 'SOXS',
        'USD', 'QTEC', 'TECL', 'TECS', 'FXL', 'FDN', 'SKYY', 'HACK', 'CIBR',
        
        # 金融ETF（拡張）
        'XLF', 'VFH', 'KBE', 'KRE', 'KBWB', 'KBWR', 'KBWP', 'KBWY', 'KBWZ',
        'FAZ', 'FAS', 'UYG', 'DPST', 'FTXO',
        
        # エネルギーETF（拡張）
        'XLE', 'VDE', 'XOP', 'OIH', 'IEZ', 'IEO', 'IYE', 'FENY', 'ERX',
        'ERY', 'GUSH', 'DRIP', 'NRGU', 'NRGD',
        
        # ヘルスケアETF（拡張）
        'XLV', 'VHT', 'IBB', 'XBI', 'LABU', 'LABD', 'CURE', 'IHI', 'IHF',
        'IXJ', 'BBH', 'PJP', 'XHS', 'XPH',
        
        # 工業ETF（拡張）
        'XLI', 'VIS', 'IYT', 'XTN', 'IYJ', 'FIDU', 'FXR', 'PSCI', 'XAR',
        'ITA', 'DFEN', 'DFEN', 'DFEN',
        
        # 消費者ETF（拡張）
        'XLY', 'VCR', 'XRT', 'RTH', 'FDIS', 'FXD', 'PEJ', 'PEZ', 'PBJ',
        'IYC', 'IYT', 'IYT', 'IYT',
        
        # 消費財ETF（拡張）
        'XLP', 'VDC', 'PBJ', 'FSTA', 'FXG', 'IYK', 'IYK', 'IYK', 'IYK',
        'IYK', 'IYK', 'IYK', 'IYK',
        
        # ユーティリティETF（拡張）
        'XLU', 'VPU', 'IDU', 'FUTY', 'FXU', 'RYU', 'UPW', 'PUI', 'SDP',
        'JXI', 'JXI', 'JXI', 'JXI',
        
        # 素材ETF（拡張）
        'XLB', 'VAW', 'IYM', 'FXZ', 'PICK', 'PSCE', 'XME', 'REMX', 'LIT',
        'PALL', 'PPLT', 'SIL', 'SILJ', 'GDX', 'GDXJ',
        
        # 不動産ETF（拡張）
        'XLRE', 'VNQ', 'IYR', 'SCHH', 'VNQI', 'RWX', 'RWR', 'FREL', 'MORT',
        'KBWY', 'KBWY', 'KBWY', 'KBWY',
        
        # 通信ETF（拡張）
        'XLC', 'VOX', 'IYZ', 'FCOM', 'IXP', 'IXP', 'IXP', 'IXP', 'IXP',
        'IXP', 'IXP', 'IXP', 'IXP',
        
        # レバレッジETF（3倍）（拡張）
        'SPXL', 'SPXS', 'TQQQ', 'SQQQ', 'TECL', 'TECS', 'FNGU', 'FNGD',
        'SOXL', 'SOXS', 'LABU', 'LABD', 'CURE', 'TNA', 'TZA', 'FAS', 'FAZ',
        'UPRO', 'SPXU', 'UDOW', 'SDOW', 'TMF', 'TMV', 'CURE', 'CURE',
        
        # インバースETF（拡張）
        'SH', 'PSQ', 'DOG', 'DXD', 'QID', 'SDS', 'MYY', 'MYY', 'MYY',
        'MYY', 'MYY', 'MYY', 'MYY',
        
        # コモディティETF（拡張）
        'GLD', 'SLV', 'USO', 'UNG', 'DBA', 'DBC', 'PDBC', 'GSG', 'IAU',
        'SIVR', 'PALL', 'PPLT', 'CPER', 'JJM', 'JJN', 'JJT', 'JJU', 'LD',
        'NIB', 'JJG', 'JJG', 'JJG',
        
        # 債券ETF（拡張）
        'TLT', 'IEF', 'SHY', 'HYG', 'JNK', 'LQD', 'BND', 'AGG', 'VCIT',
        'VCSH', 'VGIT', 'VGSH', 'SCHZ', 'SCHQ', 'SCHM', 'SCHR', 'SCHQ',
        'SCHZ', 'SCHQ', 'SCHQ', 'SCHQ',
        
        # ARK ETF（拡張）
        'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF', 'PRNT', 'IZRL', 'CTRU',
        'CTRU', 'CTRU', 'CTRU', 'CTRU',
        
        # テーマETF（拡張）
        'BOTZ', 'ROBO', 'QTUM', 'AIQ', 'BLOK', 'FINX', 'FINX', 'FINX',
        'FINX', 'FINX', 'FINX', 'FINX',
        
        # クリーンエネルギーETF（拡張）
        'ICLN', 'QCLN', 'PBW', 'FAN', 'TAN', 'ACES', 'ERTH', 'RNRG',
        'RNRG', 'RNRG', 'RNRG', 'RNRG',
        
        # 原子力ETF（拡張）
        'URA', 'URNM', 'NLR', 'NLR', 'NLR', 'NLR', 'NLR', 'NLR',
        'NLR', 'NLR', 'NLR', 'NLR',
        
        # レアメタルETF（拡張）
        'REMX', 'LIT', 'PICK', 'PICK', 'PICK', 'PICK', 'PICK', 'PICK',
        'PICK', 'PICK', 'PICK', 'PICK',
        
        # 金鉱ETF（拡張）
        'GDX', 'GDXJ', 'SIL', 'SILJ', 'SILJ', 'SILJ', 'SILJ', 'SILJ',
        'SILJ', 'SILJ', 'SILJ', 'SILJ',
        
        # 鉱業ETF（拡張）
        'XME', 'PICK', 'PSCE', 'PSCE', 'PSCE', 'PSCE', 'PSCE', 'PSCE',
        'PSCE', 'PSCE', 'PSCE', 'PSCE',
        
        # その他の人気ETF
        'SPHD', 'SPHB', 'SPHQ', 'SPLV', 'SPMO', 'SPMV', 'SPMW', 'SPXN',
        'QYLD', 'QCLR', 'QQQA', 'QQQC', 'QQQD', 'QQQE', 'QQQX', 'QQQY',
        'QQQZ', 'VTWO', 'VTWG', 'VTWV', 'VONG', 'VONV', 'VOT', 'VOE',
        'VBK', 'VBR', 'HACK', 'CIBR', 'SKYY', 'FDN', 'FXL', 'DPST',
        'FTXO', 'ERX', 'ERY', 'GUSH', 'DRIP', 'NRGU', 'NRGD', 'DFEN',
        'UPRO', 'SPXU', 'UDOW', 'SDOW', 'TMF', 'TMV', 'MYY', 'CPER',
        'JJM', 'JJN', 'JJT', 'JJU', 'LD', 'NIB', 'JJG', 'SCHZ', 'SCHQ',
        'SCHM', 'SCHR', 'PRNT', 'IZRL', 'CTRU', 'FINX', 'ACES', 'ERTH',
        'RNRG',
    ]
    
    # 重複除去
    return list(set(etfs))


def get_quantum_ai_stocks() -> List[str]:
    """量子コンピューティング・AI関連株"""
    stocks = [
        # 量子コンピューティング
        'IONQ', 'QUBT', 'RGTI', 'QBTS',
        
        # AI/機械学習
        'NVDA', 'AMD', 'INTC',  # 半導体
        'MSFT', 'GOOGL', 'META', 'AAPL',  # ビッグテック
        'PLTR', 'C3AI', 'AI', 'BBAI',  # AI企業
        'SMCI', 'DELL', 'HPE',  # AIサーバー
        'ARM', 'AVGO', 'TSM', 'ASML',  # 半導体設計/製造
        
        # データ/クラウド
        'SNOW', 'MDB', 'NET', 'CRWD', 'ZS',
        'DDOG', 'ESTC', 'SPLK', 'TEAM',
        
        # ロボティクス
        'TER', 'ROK', 'EMR',
    ]
    return stocks


def get_growth_stocks() -> List[str]:
    """成長株リスト（手動追加）"""
    stocks = [
        # 大型成長株
        'TSLA', 'AMZN', 'NFLX', 'COIN', 'HOOD',
        
        # セキュリティ
        'PANW', 'FTNT', 'OKTA', 'S', 'TENB', 'QLYS',
        
        # SaaS
        'CRM', 'NOW', 'WDAY', 'VEEV', 'ZM', 'DOCN', 'FROG', 'ESTC',
        
        # ゲーム/エンターテインメント
        'RBLX', 'U', 'DKNG', 'EA', 'TTWO', 'ATVI',
        
        # フィンテック
        'SQ', 'PYPL', 'AFRM', 'UPST', 'SOFI', 'LC', 'NU',
        
        # ヘルスケア
        'MRNA', 'BNTX', 'GILD', 'REGN', 'BIIB', 'VRTX', 'ILMN',
        
        # EV/自動車
        'RIVN', 'LCID', 'F', 'GM', 'FORD', 'NIO', 'XPEV', 'LI',
        
        # Eコマース/小売
        'SHOP', 'ETSY', 'MELI', 'SE', 'W', 'CHWY',
        
        # バイオテクノロジー
        'CRISPR', 'EDIT', 'BEAM', 'VERV', 'BLUE',
        
        # クリーンエネルギー
        'ENPH', 'SEDG', 'RUN', 'FSLR', 'NEE',
        
        # 宇宙/航空
        'RKLB', 'ASTR', 'SPCE', 'LMT', 'BA',
        
        # その他成長株
        'DOCU', 'ASAN', 'DDOG', 'BILL', 'APPN', 'FRSH', 'PATH'
    ]
    return stocks


def get_nyse_major_stocks() -> List[str]:
    """NYSEの主要銘柄"""
    return [
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'SCHW', 'BLK', 'BX', 'KKR',
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO', 'PSX', 'HAL',
        'JNJ', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'BMY', 'GILD', 'REGN',
        'WMT', 'HD', 'LOW', 'TGT', 'COST', 'TJX', 'DG', 'DLTR', 'BBY',
        'DIS', 'NFLX', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'LUMN',
        'BA', 'LMT', 'RTX', 'NOC', 'GD', 'HON', 'GE', 'CAT', 'DE',
        'MCD', 'SBUX', 'YUM', 'DPZ', 'CMG', 'QSR', 'WEN',
        'PG', 'KO', 'PEP', 'CL', 'EL', 'CLX', 'CHD',
        'UNH', 'CVS', 'CI', 'HUM', 'ANTM', 'CNC', 'MOH',
        'NEE', 'DUK', 'SO', 'AEP', 'EXC', 'SRE', 'XEL',
    ]


def get_small_mid_cap_growth() -> List[str]:
    """小型・中型成長株"""
    return [
        # 小型成長株
        'APP', 'APPS', 'BAND', 'BL', 'BLZE', 'BRZE', 'CARG', 'CERT', 'CLVT',
        'COUR', 'CRNC', 'CSWI', 'CTKB', 'CURV', 'DLO', 'DOCN', 'DOMO', 'DYN',
        'EAF', 'EGHT', 'ENVX', 'ESTC', 'EVBG', 'EVCM', 'EVTC', 'EXFY', 'FATE',
        'FBRX', 'FERG', 'FIVE', 'FRSH', 'FROG', 'FULC', 'FWRD', 'GDRX', 'GTLB',
        'HAYW', 'HCP', 'HIMS', 'HLIT', 'HSTM', 'HUBS', 'IBRX', 'ICFI', 'IMGN',
        'IMVT', 'INMD', 'INSP', 'INST', 'IOVA', 'IRBT', 'ITCI', 'JAMF', 'JBT',
        'KFRC', 'KIDS', 'KNSL', 'KROS', 'KRTX', 'LBRT', 'LECO', 'LFST', 'LNW',
        'LPSN', 'LQDA', 'LRN', 'LSPD', 'LULU', 'MARA', 'MCHX', 'MDB', 'MDRX',
        'MEDP', 'MGNX', 'MIME', 'MNDY', 'MODV', 'MORF', 'MRCY', 'MRVI', 'MSGS',
        'MTCH', 'MTDR', 'MTSI', 'NARI', 'NCNO', 'NEOG', 'NEXT', 'NMIH', 'NMRK',
        'NOVT', 'NRIX', 'NTCT', 'NTNX', 'NUVL', 'NVST', 'NXST', 'OCUL', 'ODP',
        'OMCL', 'OMI', 'ONON', 'ONTF', 'OPCH', 'OPEN', 'OPRT', 'ORIC', 'OSIS',
        'OTLY', 'PCTY', 'PD', 'PENN', 'PHR', 'PINC', 'PLUS', 'PODD', 'PRCT',
        'PRGS', 'PRME', 'PRTA', 'PRVA', 'PTC', 'PTCT', 'PTGX', 'PTON', 'PUMP',
        'QDEL', 'QLYS', 'QTRX', 'RAD', 'RAMP', 'RDFN', 'RDNT', 'RDWR', 'REAL',
        'RELY', 'RGNX', 'RHP', 'RKLB', 'RLAY', 'RLMD', 'RPD', 'RRR', 'RXRX',
        'RYTM', 'SAGE', 'SAVA', 'SCSC', 'SDGR', 'SENS', 'SFM', 'SGRY', 'SHLS',
        'SIGI', 'SITM', 'SKY', 'SLAB', 'SLP', 'SMTC', 'SNBR', 'SNCY', 'SNPS',
        'SPT', 'SPXC', 'SQSP', 'SRPT', 'SSNC', 'STAA', 'STRL', 'SUPN', 'SWAV',
        'SWTX', 'SYNA', 'TARS', 'TASK', 'TBBK', 'TCMD', 'TCOM', 'TDOC', 'TENB',
        'TGTX', 'THRM', 'TMDX', 'TMUS', 'TNDM', 'TNYA', 'TPG', 'TPTX', 'TRIP',
        'TRMB', 'TRUP', 'TSCO', 'TTD', 'TTEK', 'TTGT', 'TTCF', 'TTWO', 'TURN',
        'TWKS', 'TWLO', 'TXRH', 'U', 'UFPT', 'UHAL', 'UMH', 'UNIT', 'UPST',
        'USM', 'UTHR', 'VEEV', 'VERA', 'VERV', 'VERX', 'VICR', 'VIR', 'VITL',
        'VMEO', 'VNDA', 'VNT', 'VRRM', 'VRSN', 'VRTX', 'VSAT', 'VSH', 'VSTO',
        'VTLE', 'VTS', 'VZLA', 'W', 'WAFD', 'WDAY', 'WDFC', 'WERN', 'WING',
        'WK', 'WLDN', 'WMG', 'WOLF', 'WOOF', 'WRBY', 'WS', 'WSC', 'WSO',
        'WTFC', 'WTS', 'WWD', 'XENE', 'XFOR', 'XMTR', 'XNCR', 'XPEL', 'XRAY',
        'YELP', 'YETI', 'YEXT', 'YORW', 'YOU', 'Z', 'ZBRA', 'ZENV', 'ZI',
        'ZION', 'ZIP', 'ZLAB', 'ZM', 'ZNTL', 'ZS', 'ZUMZ', 'ZYME', 'ZYXI',
    ]


def get_more_stocks() -> List[str]:
    """追加の有望株リスト（5000件を目指す）"""
    stocks = [
        # 半導体関連（拡張）
        'INTC', 'TXN', 'NXPI', 'MRVL', 'ON', 'SWKS', 'QRVO', 'MXL',
        'WOLF', 'ALGM', 'DIOD', 'POWI', 'SLAB', 'AMBA', 'CRUS',
        
        # ソフトウェア（拡張）
        'ADSK', 'ANSS', 'CDNS', 'SNPS', 'ZM', 'DOCN', 'ESTC', 'FROG',
        'GTLB', 'MNDY', 'PCTY', 'ASAN', 'BILL', 'APPN', 'FRSH', 'PATH',
        'DOCU', 'WK', 'COUP', 'QLYS', 'TENB', 'QLYS',
        
        # クラウド/インフラ
        'DDOG', 'NET', 'FROG', 'ESTC', 'PD', 'PCTY', 'MNDY',
        
        # サイバーセキュリティ（拡張）
        'S', 'TENB', 'QLYS', 'VRRM', 'RDWR', 'RDNT', 'RPD',
        
        # ヘルスケアIT
        'TDOC', 'OMCL', 'EVH', 'HIMS', 'LFST',
        
        # バイオテクノロジー（拡張）
        'ALNY', 'ARWR', 'IONS', 'FOLD', 'RGNX', 'ALKS', 'ALLO',
        'BLUE', 'BEAM', 'CRISPR', 'EDIT', 'VERV', 'NTLA', 'PRME',
        
        # メディカルデバイス
        'ISRG', 'SWAV', 'TMDX', 'NVST', 'AXNX', 'INSP', 'SENS',
        
        # 製薬
        'REGN', 'VRTX', 'BIIB', 'ALKS', 'IONS', 'ARWR', 'ALNY',
        
        # 金融テクノロジー（拡張）
        'SOFI', 'LC', 'NU', 'UPST', 'AFRM', 'OPRT', 'LC', 'NU',
        
        # 不動産テック
        'OPEN', 'RDFN', 'COMP', 'Z', 'RKT',
        
        # 物流/配送
        'GXO', 'RXO', 'XPO', 'KNX', 'ARCB',
        
        # エネルギー（拡張）
        'ENPH', 'SEDG', 'RUN', 'FSLR', 'NEE', 'NEP', 'BEP', 'BEPC',
        
        # 素材/化学
        'ALB', 'LTHM', 'PLL', 'MP', 'REEMF',
        
        # 工業/ロボティクス
        'TER', 'ROK', 'EMR', 'AME', 'AOS', 'ZBRA',
        
        # 通信
        'TMUS', 'VZ', 'T', 'LUMN', 'USM',
        
        # メディア/エンターテインメント
        'DIS', 'WBD', 'PARA', 'FOX', 'NWS', 'NWSA',
        
        # 小売（拡張）
        'W', 'CHWY', 'ETSY', 'MELI', 'SE', 'SHOP', 'BIGC',
        
        # 旅行/レジャー
        'ABNB', 'BKNG', 'EXPE', 'TCOM', 'TRIP',
        
        # 食品/飲料
        'BYND', 'TTCF', 'OATLY', 'STKL',
        
        # その他有望株
        'RBLX', 'U', 'DKNG', 'PENN', 'MGM', 'LNW',  # ゲーミング/カジノ
        'COIN', 'HOOD', 'MSTR', 'RIOT', 'MARA',  # 仮想通貨関連
        'SPCE', 'RKLB', 'ASTR', 'LILM',  # 宇宙
        'RIVN', 'LCID', 'F', 'GM', 'NIO', 'XPEV', 'LI',  # EV
        
        # さらに多くのセクターETF
        'SPY', 'VOO', 'IVV', 'SPLG', 'SPTM', 'SPMD', 'SPSC',  # S&P500系
        'QQQ', 'QQQM', 'ONEQ', 'QQQJ', 'QTEC',  # NASDAQ系
        'IWM', 'IJH', 'IJR', 'VB', 'VBR',  # 小型株
        'VTI', 'VT', 'VEA', 'VWO', 'VXUS',  # 国際
        'VUG', 'VTV', 'VTHR', 'VYM',  # 成長/バリュー
        'XLK', 'VGT', 'FTEC', 'IGV', 'IGM',  # テクノロジー
        'XLF', 'VFH', 'KBE', 'KRE',  # 金融
        'XLE', 'VDE', 'XOP', 'OIH',  # エネルギー
        'XLV', 'VHT', 'IBB', 'XBI',  # ヘルスケア
        'XLI', 'VIS', 'IYT', 'XTN',  # 工業
        'XLY', 'VCR', 'XRT', 'RTH',  # 消費者
        'XLP', 'VDC', 'PBJ',  # 消費財
        'XLU', 'VPU', 'IDU',  # ユーティリティ
        'XLB', 'VAW', 'IYM',  # 素材
        'XLRE', 'VNQ', 'IYR', 'SCHH',  # 不動産
        'XLC', 'VOX', 'IYZ',  # 通信
        
        # レバレッジETF（3倍）
        'SPXL', 'SPXS', 'TQQQ', 'SQQQ', 'TECL', 'TECS',
        'FNGU', 'FNGD', 'SOXL', 'SOXS', 'LABU', 'LABD',
        'CURE', 'CURE', 'TNA', 'TZA', 'FAS', 'FAZ',
        
        # インバースETF
        'SH', 'PSQ', 'DOG', 'DXD', 'QID', 'SDS',
        
        # コモディティETF
        'GLD', 'SLV', 'USO', 'UNG', 'DBA', 'DBC',
        'PDBC', 'GSG', 'IAU', 'SIVR', 'PALL', 'PPLT',
        
        # 債券ETF
        'TLT', 'IEF', 'SHY', 'HYG', 'JNK', 'LQD',
        'BND', 'AGG', 'VCIT', 'VCSH', 'VGIT', 'VGSH',
        
        # その他ETF
        'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF',  # ARK
        'BOTZ', 'ROBO', 'QTUM', 'AIQ', 'BLOK',  # テーマ
        'ICLN', 'QCLN', 'PBW', 'FAN', 'TAN',  # クリーンエネルギー
        'URA', 'URNM', 'NLR',  # 原子力
        'REMX', 'LIT', 'PICK',  # レアメタル
        'GDX', 'GDXJ', 'SIL', 'SILJ',  # 金鉱
        'XME', 'PICK', 'PSCE',  # 鉱業
    ]
    return stocks


def filter_promising_stocks(tickers: List[str], min_market_cap: float = 1e9, max_tickers: int = 5000) -> List[str]:
    """
    有望株をフィルタリング
    - 時価総額が一定以上
    - データが取得可能
    - 重複除去
    """
    print(f"\n🔍 {len(tickers)}件のティッカーをフィルタリング中...")
    
    valid_tickers = []
    checked = set()
    failed_count = 0
    
    for i, ticker in enumerate(tickers):
        if len(valid_tickers) >= max_tickers:
            break
        
        ticker_upper = ticker.upper()
        
        # 重複チェック
        if ticker_upper in checked:
            continue
        checked.add(ticker_upper)
        
        # 進捗表示
        if (i + 1) % 100 == 0:
            print(f"  進捗: {i+1}/{len(tickers)} (有効: {len(valid_tickers)}, 失敗: {failed_count})")
        
        try:
            # ティッカー情報を取得
            ticker_obj = yf.Ticker(ticker_upper)
            info = ticker_obj.info
            
            # 時価総額チェック
            market_cap = info.get('marketCap', 0)
            if market_cap and market_cap >= min_market_cap:
                # 価格データが取得可能かチェック
                hist = ticker_obj.history(period="5d", interval="1d")
                if not hist.empty:
                    valid_tickers.append(ticker_upper)
                else:
                    failed_count += 1
            else:
                failed_count += 1
            
            # API制限を避けるため少し待機
            time.sleep(0.1)
            
        except Exception as e:
            failed_count += 1
            continue
    
    print(f"  ✓ {len(valid_tickers)}件の有望株をフィルタリング完了")
    return valid_tickers


def is_valid_ticker(ticker: str) -> bool:
    """有効なティッカーかどうかを判定"""
    if not ticker or len(ticker) == 0:
        return False
    
    # 数字のみは無効
    if ticker.isdigit():
        return False
    
    # 長すぎるティッカーは無効（通常1-5文字）
    if len(ticker) > 5:
        return False
    
    # 特殊文字が多すぎる場合は無効
    if not any(c.isalpha() for c in ticker):
        return False
    
    return True


def update_config_json(tickers: List[str], config_path: str = 'config.json'):
    """config.jsonにティッカーを追加"""
    print(f"\n📝 {config_path}を更新中...")
    
    try:
        # 既存のconfig.jsonを読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 既存のティッカーを取得
        existing_tickers = set(config.get('symbols', []))
        
        # 無効なティッカーをフィルタリング
        valid_tickers = [t for t in tickers if is_valid_ticker(t)]
        print(f"  → {len(valid_tickers)}/{len(tickers)}件が有効なティッカー")
        
        # 新しいティッカーを追加（重複除去）
        all_tickers = list(existing_tickers) + [t for t in valid_tickers if t not in existing_tickers]
        
        # 無効な既存ティッカーも除去
        all_tickers = [t for t in all_tickers if is_valid_ticker(t)]
        
        # ソート
        all_tickers.sort()
        
        # 更新
        config['symbols'] = all_tickers
        
        # 保存
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print(f"  ✓ {len(all_tickers)}件のティッカーを登録（新規: {len(all_tickers) - len(existing_tickers)}件）")
        return len(all_tickers)
        
    except Exception as e:
        print(f"  ✗ 設定ファイル更新エラー: {e}")
        return 0


def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 有望株ティッカー自動収集スクリプト")
    print("=" * 60)
    
    all_tickers = []
    
    # 1. S&P500
    sp500 = get_sp500_tickers()
    all_tickers.extend(sp500)
    
    # 2. NASDAQ-100（主要銘柄）
    nasdaq = get_nasdaq_tickers()
    all_tickers.extend(nasdaq)
    
    # 3. NASDAQ全上場銘柄（大幅追加）
    nasdaq_all = get_all_nasdaq_listed()
    all_tickers.extend(nasdaq_all)
    print(f"📊 {len(nasdaq_all)}件のNASDAQ全上場銘柄を追加")
    
    # 4. NYSE全上場銘柄（大幅追加）
    nyse_all = get_all_nyse_listed()
    all_tickers.extend(nyse_all)
    print(f"🏛️ {len(nyse_all)}件のNYSE全上場銘柄を追加")
    
    # 5. 人気ETF
    etfs = get_popular_etfs()
    all_tickers.extend(etfs)
    print(f"📊 {len(etfs)}件の人気ETFを追加")
    
    # 6. 拡張ETF（大幅追加）
    extended_etfs = get_extended_etfs()
    all_tickers.extend(extended_etfs)
    print(f"📊 {len(extended_etfs)}件の拡張ETFを追加")
    
    # 7. 量子/AI関連株
    quantum_ai = get_quantum_ai_stocks()
    all_tickers.extend(quantum_ai)
    print(f"⚛️ {len(quantum_ai)}件の量子/AI関連株を追加")
    
    # 8. 成長株
    growth = get_growth_stocks()
    all_tickers.extend(growth)
    print(f"📈 {len(growth)}件の成長株を追加")
    
    # 9. NYSE主要銘柄
    nyse = get_nyse_major_stocks()
    all_tickers.extend(nyse)
    print(f"🏛️ {len(nyse)}件のNYSE主要銘柄を追加")
    
    # 10. 小型・中型成長株
    small_mid = get_small_mid_cap_growth()
    all_tickers.extend(small_mid)
    print(f"📊 {len(small_mid)}件の小型・中型成長株を追加")
    
    # 11. 追加の有望株（5000件を目指す）
    more_stocks = get_more_stocks()
    all_tickers.extend(more_stocks)
    print(f"📊 {len(more_stocks)}件の追加有望株を追加")
    
    # 重複除去
    unique_tickers = list(set([t.upper() for t in all_tickers]))
    print(f"\n📊 合計: {len(unique_tickers)}件のユニークなティッカーを収集")
    
    # フィルタリング（オプション）
    if '--filter' in sys.argv:
        print("\n⚠️ フィルタリングモード: 時価総額10億ドル以上、データ取得可能な銘柄のみ")
        filtered = filter_promising_stocks(unique_tickers, min_market_cap=1e9, max_tickers=10000)
        unique_tickers = filtered
    else:
        print("\n⚠️ フィルタリングなし: 全ティッカーを追加します")
    
    # config.jsonを更新
    total_count = update_config_json(unique_tickers)
    
    print("\n" + "=" * 60)
    print(f"✅ 完了！合計 {total_count}件のティッカーを登録しました")
    print("=" * 60)
    print("\n💡 ヒント:")
    print("  - フィルタリングする場合: python collect_tickers.py --filter")
    print("  - フィルタリングなし（全件追加）: python collect_tickers.py")


if __name__ == '__main__':
    main()
