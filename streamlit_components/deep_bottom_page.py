"""
Deep Bottom Detection Page
長期投資向けの歴史的割安銘柄検出ページ
段階的スキャン機能付き
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional, Set
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.state_machine import StateMachine
from signals import is_crypto_symbol
from core.constants import DEEP_BOTTOM_THRESHOLDS, CRYPTO_SYMBOLS, ETF_SYMBOLS, TECH_SYMBOLS


# セクター別銘柄定義
SECTOR_SYMBOLS = {
    'テクノロジー': [
        'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'INTC', 'CRM', 'ADBE', 'ORCL',
        'CSCO', 'IBM', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL',
        'NOW', 'SNOW', 'PLTR', 'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'TEAM', 'OKTA'
    ],
    'ヘルスケア': [
        'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY',
        'AMGN', 'GILD', 'ISRG', 'MDT', 'SYK', 'REGN', 'VRTX', 'ZTS', 'BDX', 'BSX'
    ],
    '金融': [
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V',
        'MA', 'PYPL', 'SQ', 'COIN', 'HOOD', 'SOFI', 'ALLY', 'COF', 'DFS', 'USB'
    ],
    '消費財': [
        'AMZN', 'TSLA', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'COST', 'WMT', 'LOW',
        'TJX', 'ROST', 'DG', 'DLTR', 'BBY', 'ORLY', 'AZO', 'CMG', 'DPZ', 'YUM'
    ],
    'エネルギー': [
        'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
        'DVN', 'FANG', 'PXD', 'HES', 'BKR', 'KMI', 'WMB', 'OKE', 'TRGP', 'LNG'
    ],
    '通信': [
        'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'WBD', 'PARA', 'FOX',
        'RBLX', 'TTWO', 'EA', 'ATVI', 'MTCH', 'SNAP', 'PINS', 'SPOT', 'TTD', 'ROKU'
    ],
    '産業': [
        'CAT', 'DE', 'BA', 'HON', 'UPS', 'RTX', 'LMT', 'GE', 'MMM', 'EMR',
        'ITW', 'PH', 'ROK', 'ETN', 'CMI', 'PCAR', 'FAST', 'URI', 'ODFL', 'DAL'
    ],
    '素材': [
        'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'NUE', 'DOW', 'DD', 'PPG',
        'VMC', 'MLM', 'ALB', 'CTVA', 'CF', 'MOS', 'FMC', 'IFF', 'CE', 'EMN'
    ],
    '不動産': [
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL', 'DLR', 'AVB',
        'EQR', 'VTR', 'ARE', 'MAA', 'UDR', 'ESS', 'INVH', 'SUI', 'ELS', 'PEAK'
    ],
    '公益事業': [
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'XEL', 'ED', 'EXC', 'WEC',
        'ES', 'PEG', 'AWK', 'AEE', 'CMS', 'DTE', 'ETR', 'FE', 'PPL', 'EVRG'
    ]
}

# インデックス銘柄
INDEX_SYMBOLS = {
    'S&P 500 主要': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
        'UNH', 'XOM', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
        'ABBV', 'COST', 'ADBE', 'MRK', 'PEP', 'TMO', 'CSCO', 'WMT', 'DIS',
        'ABT', 'ACN', 'DHR', 'VZ', 'NFLX', 'CMCSA', 'NKE', 'PM', 'TXN'
    ],
    'NASDAQ 100': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO',
        'COST', 'ADBE', 'PEP', 'CSCO', 'NFLX', 'AMD', 'INTC', 'CMCSA',
        'TXN', 'QCOM', 'AMGN', 'INTU', 'HON', 'AMAT', 'BKNG', 'ISRG',
        'ADP', 'SBUX', 'GILD', 'MU', 'ADI', 'REGN', 'LRCX', 'PANW'
    ],
    'ダウ30': [
        'AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'MCD', 'AMGN', 'V', 'CAT', 'BA',
        'HON', 'TRV', 'AXP', 'JNJ', 'CRM', 'JPM', 'IBM', 'PG', 'CVX', 'MRK',
        'DIS', 'NKE', 'KO', 'WMT', 'DOW', 'CSCO', 'MMM', 'VZ', 'INTC', 'WBA'
    ]
}

# 暗号通貨カテゴリ
CRYPTO_CATEGORIES = {
    'メジャー': ['BTC', 'ETH'],
    'Layer 1': ['SOL', 'ADA', 'AVAX', 'DOT', 'ATOM', 'NEAR', 'FTM', 'ALGO'],
    'Layer 2': ['MATIC', 'ARB', 'OP', 'IMX'],
    'DeFi': ['UNI', 'AAVE', 'MKR', 'CRV', 'COMP', 'SUSHI', 'YFI', 'SNX'],
    'ミーム': ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK'],
    '取引所': ['BNB', 'CRO', 'FTT', 'OKB', 'LEO']
}

# ETFカテゴリ
ETF_CATEGORIES = {
    '主要指数': ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'IVV'],
    'セクター': ['XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE'],
    '国際': ['EFA', 'VEU', 'EEM', 'VWO', 'IEFA', 'ACWI'],
    '債券': ['BND', 'AGG', 'TLT', 'LQD', 'HYG', 'TIP', 'VCSH'],
    'コモディティ': ['GLD', 'SLV', 'USO', 'UNG', 'DBA', 'DBC'],
    'テーマ': ['ARKK', 'ARKG', 'ARKF', 'ARKW', 'ARKQ', 'BOTZ', 'ROBO', 'HACK']
}

# 日本株（ADR - 米国上場）
JAPAN_STOCKS = {
    '自動車': ['TM', 'HMC', 'NSANY', 'FUJHY', 'MZDAY'],
    'テクノロジー': ['SONY', 'NTDOY', 'KYOCY', 'FANUY', 'KNBWY', 'TOELY'],
    '金融': ['MUFG', 'SMFG', 'MFG', 'NMR', 'ORIX'],
    '製造業': ['CAJ', 'HTHIY', 'PCRFY', 'KDDIY', 'ITOCY'],
    '消費財': ['UNICY', 'APTS', 'BRFS', 'SHCAY', 'SFTBY'],
    '製薬': ['TAK', 'ALPMY', 'ESALY', 'CHGCY', 'DNZOY'],
    '通信': ['NTTYY', 'SFTBY', 'KDDIY'],
    '総合商社': ['MARUY', 'MITSY', 'ITOCY', 'SSUMY', 'SOMLY']
}

# 日本株主要銘柄（フラットリスト）
JAPAN_MAJOR = [
    'TM', 'SONY', 'HMC', 'MUFG', 'NTDOY', 'SMFG', 'NMR', 'TAK', 'KYOCY',
    'CAJ', 'MFG', 'ORIX', 'FANUY', 'NTTYY', 'ITOCY', 'MARUY', 'HTHIY'
]

# 欧州株（ADR）
EUROPE_STOCKS = {
    'ドイツ': ['SAP', 'SAP', 'DB', 'VWAGY', 'BMWYY', 'SIEGY', 'BAYRY', 'BASFY', 'DTEGY'],
    'イギリス': ['SHEL', 'BP', 'AZN', 'GSK', 'HSBC', 'UL', 'RIO', 'BTI', 'VOD', 'BCS'],
    'フランス': ['TTE', 'SNY', 'LVMUY', 'OR', 'BNPQY', 'CSGFY', 'EADSY'],
    'スイス': ['NSRGY', 'NVS', 'RHHBY', 'UBS', 'CS', 'ABB'],
    'オランダ': ['ASML', 'ING', 'PHIA', 'UNA'],
    'スペイン/イタリア': ['TEF', 'BBVA', 'SAN', 'ENEL', 'ENI']
}

# アジア株（日本以外、ADR）
ASIA_STOCKS = {
    '中国': ['BABA', 'JD', 'PDD', 'BIDU', 'NIO', 'XPEV', 'LI', 'TME', 'BILI', 'IQ',
             'NTES', 'TCEHY', 'MPNGY', 'YUMC', 'ZTO', 'TAL', 'EDU'],
    '韓国': ['005930.KS', '000660.KS', 'LPL', 'KB', 'SHG', 'PKX'],
    '台湾': ['TSM', 'UMC', 'ASX', 'HIMX'],
    'インド': ['INFY', 'WIT', 'HDB', 'IBN', 'SIFY', 'RDY', 'TTM', 'VEDL'],
    '東南アジア': ['SE', 'GRAB', 'CPNG', 'BEKE']
}

# テーマ別銘柄
THEME_STOCKS = {
    'AI・人工知能': [
        'NVDA', 'AMD', 'GOOGL', 'MSFT', 'META', 'AMZN', 'CRM', 'PLTR', 'AI', 'PATH',
        'SNOW', 'MDB', 'DDOG', 'S', 'CRWD', 'ZS', 'OKTA', 'SPLK', 'ESTC', 'CFLT'
    ],
    'EV・電気自動車': [
        'TSLA', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'FSR', 'GOEV', 'WKHS', 'RIDE',
        'QS', 'CHPT', 'BLNK', 'EVGO', 'LAC', 'ALB', 'LTHM', 'MP', 'PLUG', 'FCEL'
    ],
    'クリーンエネルギー': [
        'ENPH', 'SEDG', 'RUN', 'NOVA', 'ARRY', 'SPWR', 'FSLR', 'JKS', 'DQ', 'CSIQ',
        'NEE', 'AES', 'CWEN', 'BEP', 'ORA', 'VWSYF', 'PLUG', 'BE', 'BLDP', 'FCEL'
    ],
    '宇宙・航空': [
        'RKLB', 'SPCE', 'ASTR', 'RDW', 'MNTS', 'BKSY', 'ASTS', 'GSAT', 'IRDM', 'VSAT',
        'BA', 'LMT', 'NOC', 'RTX', 'GD', 'LHX', 'HII', 'TXT', 'SPR', 'ERJ'
    ],
    '量子コンピュータ': [
        'IBM', 'GOOGL', 'MSFT', 'IONQ', 'RGTI', 'QUBT', 'ARQQ', 'QBTS', 'COLD', 'QTUM'
    ],
    'サイバーセキュリティ': [
        'CRWD', 'PANW', 'ZS', 'FTNT', 'OKTA', 'S', 'NET', 'CYBR', 'TENB', 'RPD',
        'VRNS', 'SAIL', 'QLYS', 'FEYE', 'MIME', 'NTCT', 'CACI', 'LDOS', 'BAH', 'SAIC'
    ],
    'メタバース・ゲーム': [
        'META', 'RBLX', 'U', 'TTWO', 'EA', 'ATVI', 'NTDOY', 'SONY', 'NTES', 'SE',
        'BILI', 'DOYU', 'HUYA', 'SKLZ', 'PLTK', 'GMBL', 'DKNG', 'PENN', 'MGM', 'WYNN'
    ],
    'フィンテック': [
        'SQ', 'PYPL', 'AFRM', 'UPST', 'SOFI', 'HOOD', 'COIN', 'NU', 'MELI', 'STNE',
        'PAGS', 'V', 'MA', 'AXP', 'DFS', 'COF', 'ALLY', 'LC', 'OPEN', 'TREE'
    ],
    'バイオテック': [
        'MRNA', 'BNTX', 'NVAX', 'REGN', 'VRTX', 'SGEN', 'ALNY', 'BMRN', 'EXEL', 'INCY',
        'SRPT', 'IONS', 'BLUE', 'CRSP', 'EDIT', 'NTLA', 'BEAM', 'VERV', 'VCEL', 'FATE'
    ],
    '半導体': [
        'NVDA', 'AMD', 'INTC', 'TSM', 'AVGO', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX',
        'KLAC', 'ASML', 'MRVL', 'ADI', 'NXPI', 'ON', 'SWKS', 'QRVO', 'MPWR', 'MCHP'
    ],
    '大麻': [
        'TLRY', 'CGC', 'ACB', 'CRON', 'OGI', 'HEXO', 'SNDL', 'VFF', 'GRWG', 'CURLF'
    ],
    'SPAC・成長株': [
        'RIVN', 'LCID', 'JOBY', 'LILM', 'ACHR', 'OPEN', 'SOFI', 'CLOV', 'WISH', 'BARK'
    ]
}

# 配当株
DIVIDEND_STOCKS = {
    '高配当': [
        'VZ', 'T', 'MO', 'PM', 'XOM', 'CVX', 'IBM', 'ABBV', 'KO', 'PEP',
        'JNJ', 'PG', 'MMM', 'O', 'MAIN', 'STAG', 'AGNC', 'NLY', 'ARCC', 'PSEC'
    ],
    '配当貴族': [
        'JNJ', 'PG', 'KO', 'PEP', 'MMM', 'ABT', 'ABBV', 'MCD', 'WMT', 'CL',
        'ED', 'XOM', 'CVX', 'EMR', 'GPC', 'SWK', 'ADP', 'ITW', 'LOW', 'TGT'
    ],
    'REIT': [
        'O', 'STAG', 'NNN', 'WPC', 'STOR', 'ADC', 'EPRT', 'VICI', 'GLPI', 'IIPR',
        'AMT', 'CCI', 'SBAC', 'DLR', 'EQIX', 'PSA', 'EXR', 'CUBE', 'LSI', 'NSA'
    ]
}

# 小型成長株
SMALL_CAP_GROWTH = [
    'UPST', 'AFRM', 'HOOD', 'SOFI', 'RKLB', 'IONQ', 'JOBY', 'LILM', 'PATH', 'DOCN',
    'GTLB', 'CFLT', 'BRZE', 'CWAN', 'TXG', 'DOCS', 'FROG', 'API', 'JAMF', 'SUMO',
    'ASAN', 'MNDY', 'ZI', 'HUBS', 'PCTY', 'APPN', 'COUP', 'BILL', 'PAYC', 'WK'
]

# 割安株（バリュー）
VALUE_STOCKS = [
    'BRK-B', 'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC',
    'CVX', 'XOM', 'COP', 'EOG', 'SLB', 'VZ', 'T', 'CMCSA', 'CHTR', 'TMUS',
    'GM', 'F', 'TM', 'HMC', 'STLA', 'MRK', 'PFE', 'BMY', 'GILD', 'AMGN'
]


def analyze_single_symbol(state_machine: StateMachine, symbol: str, advanced: bool = False, use_v2: bool = False) -> Optional[Dict]:
    """
    単一シンボルのDeep Bottom分析

    Args:
        state_machine: StateMachineインスタンス
        symbol: 分析対象シンボル
        advanced: 高度な分析を使用するか
        use_v2: V2スコアリング（出来高確認付き）を使用するか

    Returns:
        分析結果辞書 or None
    """
    try:
        if use_v2:
            detected, metrics = state_machine.check_deep_bottom_advanced_v2(symbol)
        elif advanced:
            detected, metrics = state_machine.check_deep_bottom_advanced(symbol)
        else:
            detected, metrics = state_machine.check_deep_bottom(symbol)

        if metrics:
            result = {
                'symbol': symbol,
                'detected': detected,
                'current_price': metrics.get('current_price', 0),
                'ath_price': metrics.get('ath_price', 0),
                'drawdown_pct': metrics.get('drawdown_pct', 0),
                'week52_low_proximity': metrics.get('week52_low_proximity', 0),
                'rsi_14': metrics.get('rsi_14', 0),
                'ma_200': metrics.get('ma_200'),
                'return_7d': metrics.get('return_7d', 0),
                'return_30d': metrics.get('return_30d', 0),
                'conditions': metrics.get('conditions', metrics.get('basic_conditions', {})),
                'analyzed_at': datetime.now().isoformat()
            }

            # 高度な分析結果を追加
            if advanced:
                result['signal_strength'] = metrics.get('signal_strength', 'none')
                result['basic_conditions'] = metrics.get('basic_conditions', {})
                result['advanced_conditions'] = metrics.get('advanced_conditions', {})
                result['basic_score'] = metrics.get('basic_score', '0/5')
                result['advanced_score'] = metrics.get('advanced_score', '0/7')

                # スコア情報
                deep_score = metrics.get('deep_score', {})
                if deep_score:
                    result['total_score'] = deep_score.get('total_score', 0)
                    result['value_score'] = deep_score.get('value_score', 0)
                    result['technical_score'] = deep_score.get('technical_score', 0)
                    result['momentum_score'] = deep_score.get('momentum_score', 0)
                    result['risk_score'] = deep_score.get('risk_score', 0)

                # テクニカル指標
                result['divergence'] = metrics.get('divergence')
                result['support'] = metrics.get('support')
                result['consolidation'] = metrics.get('consolidation')
                result['higher_lows'] = metrics.get('higher_lows')
                result['bollinger'] = metrics.get('bollinger')
                result['stochastic'] = metrics.get('stochastic')
                result['macd'] = metrics.get('macd')

            # V2スコアリング結果を追加
            if use_v2 and metrics.get('scoring_version') == 'v2':
                result['scoring_version'] = 'v2'
                result['total_score'] = metrics.get('total_score', 0)
                result['signal_strength'] = metrics.get('signal_strength')
                result['confidence'] = metrics.get('confidence', 0)
                result['volume_confirmed'] = metrics.get('volume_confirmed', False)

                # コンポーネント別スコア
                result['value_score'] = metrics.get('value_score', {})
                result['technical_score'] = metrics.get('technical_score', {})
                result['momentum_score'] = metrics.get('momentum_score', {})
                result['volume_score'] = metrics.get('volume_score', {})
                result['sync_bonus'] = metrics.get('sync_bonus', {})

                # リスク情報
                result['risk_deduction'] = metrics.get('risk_deduction', 0)
                result['risk_factors'] = metrics.get('risk_factors', [])
                result['raw_score'] = metrics.get('raw_score', 0)

                # ファンダメンタル（株式のみ）
                if metrics.get('fundamental_score') is not None:
                    result['fundamental_score'] = metrics.get('fundamental_score')
                    result['fundamental_health'] = metrics.get('fundamental_health')
                    result['fundamental_warnings'] = metrics.get('fundamental_warnings', [])
                    result['adjusted_total_score'] = metrics.get('adjusted_total_score')

            return result
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e),
            'detected': False
        }
    return None


def get_recommendation(state_machine: StateMachine, symbol: str) -> Optional[Dict]:
    """投資推奨を取得"""
    try:
        return state_machine.get_bottom_recommendation(symbol)
    except Exception:
        return None


def render_deep_bottom_page(symbols: List[str]):
    """
    Deep Bottom検出ページをレンダリング

    Args:
        symbols: 監視対象シンボルのリスト
    """
    st.markdown('<div class="main-header">💎 Deep Bottom Detection</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 長期投資向け歴史的割安シグナル

    このページでは、**長期投資向け**に歴史的に極めて割安な銘柄を検出します。
    短期的な価格予測ではなく、**買い持ち（バイ＆ホールド）**戦略に適した銘柄を見つけます。
    """)

    # 検出条件の説明
    with st.expander("📋 検出条件（全て満たす必要あり）", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **1. ATH下落率 ≥ {DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN}%**
            - 史上最高値から大幅に下落
            - 歴史的な割安水準を示す

            **2. 52週安値に近い（{DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX*100:.0f}%以内）**
            - 直近1年の最安値付近
            - 極度の悲観を示す

            **3. RSI ≤ {DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD}**
            - テクニカル的に売られすぎ
            - 反転の可能性
            """)

        with col2:
            st.markdown(f"""
            **4. 200日移動平均より下**
            - 長期トレンドから乖離
            - 平均回帰の余地あり

            **5. 7日リターン > {DEEP_BOTTOM_THRESHOLDS.MIN_7D_RETURN}%**
            - 急落中ではない
            - 落ちるナイフを避ける

            ---
            **注意**: これは投資助言ではありません。
            必ずご自身で調査を行ってください。
            """)

    st.markdown("---")

    # セッション状態の初期化
    if 'deep_bottom_results' not in st.session_state:
        st.session_state.deep_bottom_results = []
    if 'deep_bottom_scanned' not in st.session_state:
        st.session_state.deep_bottom_scanned = set()
    if 'deep_bottom_scanning' not in st.session_state:
        st.session_state.deep_bottom_scanning = False
    if 'deep_bottom_detected_live' not in st.session_state:
        st.session_state.deep_bottom_detected_live = []
    if 'advanced_mode' not in st.session_state:
        st.session_state.advanced_mode = False
    if 'use_v2_scoring' not in st.session_state:
        st.session_state.use_v2_scoring = False

    # 高度な分析モード切替
    st.markdown("### ⚙️ 分析設定")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        advanced_mode = st.toggle(
            "🔬 高度な分析モード",
            value=st.session_state.advanced_mode,
            key="advanced_toggle",
            help="RSIダイバージェンス、サポートレベル、MACD等の高度な指標を使用"
        )
        st.session_state.advanced_mode = advanced_mode
    with col2:
        use_v2 = st.toggle(
            "📊 V2スコアリング",
            value=st.session_state.use_v2_scoring,
            key="v2_toggle",
            help="出来高確認、シンクボーナス、MA距離スコア等の改良版スコアリング"
        )
        st.session_state.use_v2_scoring = use_v2
    with col3:
        if use_v2:
            st.success("📊 V2: 出来高確認 + シンクボーナス + 改良スコアリング")
        elif advanced_mode:
            st.info("🔬 高度な分析: スコアリング + 7つの追加指標を使用")
        else:
            st.info("📊 基本分析: 5つの条件でシンプルに判定")

    # 分析実行セクション
    st.subheader("🔍 銘柄スキャン")

    # メインタブ
    main_tab = st.radio(
        "カテゴリ",
        ["🇺🇸 米国株", "🌏 国際株", "🪙 暗号通貨", "🎯 テーマ別", "🛠️ その他"],
        horizontal=True,
        key="main_tab"
    )

    st.markdown("---")

    if main_tab == "🇺🇸 米国株":
        tab1, tab2, tab3, tab4 = st.tabs(["🚀 クイック", "🏢 セクター別", "📊 インデックス", "🌐 全銘柄"])
        with tab1:
            render_quick_scan(symbols)
        with tab2:
            render_sector_scan(symbols)
        with tab3:
            render_index_scan(symbols)
        with tab4:
            render_full_scan(symbols)

    elif main_tab == "🌏 国際株":
        tab1, tab2, tab3, tab4 = st.tabs(["🇯🇵 日本株", "🇪🇺 欧州株", "🇨🇳 中国・アジア株", "🌍 全地域"])
        with tab1:
            render_japan_scan(symbols)
        with tab2:
            render_europe_scan(symbols)
        with tab3:
            render_asia_scan(symbols)
        with tab4:
            render_global_scan(symbols)

    elif main_tab == "🪙 暗号通貨":
        tab1, tab2 = st.tabs(["📊 カテゴリ別", "🔥 全暗号通貨"])
        with tab1:
            render_crypto_scan(symbols)
        with tab2:
            render_all_crypto_scan(symbols)

    elif main_tab == "🎯 テーマ別":
        tab1, tab2, tab3, tab4 = st.tabs(["🤖 テクノロジー", "💰 配当・バリュー", "📈 成長株", "🏷️ 全テーマ"])
        with tab1:
            render_tech_theme_scan(symbols)
        with tab2:
            render_dividend_scan(symbols)
        with tab3:
            render_growth_scan(symbols)
        with tab4:
            render_all_theme_scan(symbols)

    else:  # その他
        tab1, tab2 = st.tabs(["📝 カスタム", "⭐ ウォッチリスト"])
        with tab1:
            render_custom_scan(symbols)
        with tab2:
            render_watchlist_scan(symbols)

    # 結果表示
    if st.session_state.deep_bottom_results:
        display_deep_bottom_results(st.session_state.deep_bottom_results)


def render_quick_scan(symbols: List[str]):
    """クイックスキャン（主要銘柄のみ）"""
    st.markdown("**主要な暗号通貨・株式を素早くスキャン**")

    # プリセット選択
    preset = st.radio(
        "プリセット",
        ["トップ30（推奨）", "トップ50", "トップ100", "暗号通貨のみ", "米国株のみ"],
        horizontal=True,
        key="quick_preset"
    )

    # 主要銘柄リスト
    major_crypto = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC']
    major_stocks = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CRM',
        'NFLX', 'PYPL', 'SQ', 'COIN', 'MSTR', 'JPM', 'V', 'MA', 'DIS', 'NKE',
        'HD', 'WMT', 'COST', 'PEP', 'KO', 'JNJ', 'PFE', 'ABBV', 'UNH', 'XOM',
        'CVX', 'BA', 'CAT', 'GE', 'HON', 'LMT', 'RTX', 'GS', 'MS', 'BLK'
    ]
    major_etfs = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'ARKK', 'GLD', 'TLT', 'XLK', 'XLF']

    if preset == "トップ30（推奨）":
        scan_list = major_crypto[:10] + major_stocks[:15] + major_etfs[:5]
    elif preset == "トップ50":
        scan_list = major_crypto[:14] + major_stocks[:30] + major_etfs[:6]
    elif preset == "トップ100":
        scan_list = major_crypto + major_stocks + major_etfs
    elif preset == "暗号通貨のみ":
        scan_list = major_crypto
    else:  # 米国株のみ
        scan_list = major_stocks[:30] + major_etfs[:5]

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # 銘柄プレビュー
    with st.expander("スキャン対象を確認"):
        st.write(", ".join(scan_symbols))

    if st.button("🚀 クイックスキャン開始", key="quick_scan", type="primary"):
        run_scan(scan_symbols)


def render_sector_scan(symbols: List[str]):
    """セクター別スキャン"""
    st.markdown("**セクター（業種）別にスキャン**")

    # セクター選択
    selected_sectors = st.multiselect(
        "スキャンするセクターを選択",
        list(SECTOR_SYMBOLS.keys()),
        default=["テクノロジー"],
        key="sector_select"
    )

    if not selected_sectors:
        st.warning("セクターを選択してください")
        return

    # 選択されたセクターの銘柄を集める
    scan_list = []
    for sector in selected_sectors:
        scan_list.extend(SECTOR_SYMBOLS.get(sector, []))

    # 重複除去
    scan_list = list(dict.fromkeys(scan_list))
    scan_symbols = [s for s in scan_list if s in symbols]

    # セクター別内訳
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"対象: {len(scan_symbols)}銘柄")
    with col2:
        for sector in selected_sectors:
            count = len([s for s in SECTOR_SYMBOLS.get(sector, []) if s in symbols])
            st.caption(f"{sector}: {count}銘柄")

    # 銘柄プレビュー
    with st.expander("スキャン対象を確認"):
        for sector in selected_sectors:
            sector_syms = [s for s in SECTOR_SYMBOLS.get(sector, []) if s in symbols]
            st.markdown(f"**{sector}**: {', '.join(sector_syms)}")

    if st.button("🏢 セクタースキャン開始", key="sector_scan", type="primary"):
        run_scan(scan_symbols)


def render_index_scan(symbols: List[str]):
    """インデックス別スキャン"""
    st.markdown("**主要インデックス構成銘柄をスキャン**")

    # インデックス選択
    selected_index = st.radio(
        "インデックスを選択",
        list(INDEX_SYMBOLS.keys()),
        horizontal=True,
        key="index_select"
    )

    scan_list = INDEX_SYMBOLS.get(selected_index, [])
    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄 ({selected_index})")

    # 銘柄プレビュー
    with st.expander("スキャン対象を確認"):
        st.write(", ".join(scan_symbols))

    # ETFも含めるオプション
    include_etfs = st.checkbox("関連ETFも含める", value=True, key="include_index_etf")

    if include_etfs:
        if selected_index == "S&P 500 主要":
            etfs = ['SPY', 'VOO', 'IVV']
        elif selected_index == "NASDAQ 100":
            etfs = ['QQQ', 'QQQM']
        else:
            etfs = ['DIA']

        scan_symbols.extend([e for e in etfs if e in symbols and e not in scan_symbols])
        st.caption(f"ETF追加: {', '.join(etfs)}")

    if st.button("📊 インデックススキャン開始", key="index_scan", type="primary"):
        run_scan(scan_symbols)


def render_crypto_scan(symbols: List[str]):
    """暗号通貨スキャン"""
    st.markdown("**暗号通貨をカテゴリ別にスキャン**")

    # カテゴリ選択
    col1, col2 = st.columns(2)

    with col1:
        selected_categories = st.multiselect(
            "カテゴリを選択",
            list(CRYPTO_CATEGORIES.keys()),
            default=["メジャー", "Layer 1"],
            key="crypto_category"
        )

    with col2:
        # 全暗号通貨オプション
        scan_all_crypto = st.checkbox("全ての暗号通貨をスキャン", value=False, key="all_crypto")

    if scan_all_crypto:
        # 全暗号通貨
        scan_symbols = [s for s in symbols if is_crypto_symbol(s)]
        st.info(f"対象: {len(scan_symbols)}暗号通貨（全て）")
    else:
        if not selected_categories:
            st.warning("カテゴリを選択してください")
            return

        # 選択されたカテゴリの銘柄を集める
        scan_list = []
        for cat in selected_categories:
            scan_list.extend(CRYPTO_CATEGORIES.get(cat, []))

        scan_list = list(dict.fromkeys(scan_list))
        scan_symbols = [s for s in scan_list if s in symbols]

        st.info(f"対象: {len(scan_symbols)}銘柄")

        # カテゴリ別内訳
        for cat in selected_categories:
            syms = [s for s in CRYPTO_CATEGORIES.get(cat, []) if s in symbols]
            st.caption(f"{cat}: {', '.join(syms)}")

    # 暗号通貨関連株も含める
    include_crypto_stocks = st.checkbox(
        "暗号通貨関連株も含める（COIN, MSTR, RIOT等）",
        value=False,
        key="include_crypto_stocks"
    )

    if include_crypto_stocks:
        crypto_stocks = ['COIN', 'MSTR', 'RIOT', 'MARA', 'HUT', 'BITF', 'CLSK', 'CIFR']
        for s in crypto_stocks:
            if s in symbols and s not in scan_symbols:
                scan_symbols.append(s)
        st.caption(f"関連株追加: COIN, MSTR, RIOT等")

    if st.button("🪙 暗号通貨スキャン開始", key="crypto_scan", type="primary"):
        run_scan(scan_symbols)


def render_all_crypto_scan(symbols: List[str]):
    """全暗号通貨スキャン"""
    st.markdown("**全ての暗号通貨をスキャン**")

    # 全暗号通貨を取得
    all_crypto = [s for s in symbols if is_crypto_symbol(s)]

    st.info(f"対象: {len(all_crypto)}暗号通貨")

    if all_crypto:
        with st.expander("スキャン対象を確認"):
            st.write(", ".join(all_crypto))

    if st.button("🔥 全暗号通貨スキャン", key="all_crypto_scan", type="primary"):
        if all_crypto:
            run_scan(all_crypto)
        else:
            st.warning("暗号通貨が見つかりません")


def render_japan_scan(symbols: List[str]):
    """日本株スキャン"""
    st.markdown("**🇯🇵 日本株（ADR - 米国上場）をスキャン**")

    # セクター選択
    col1, col2 = st.columns(2)

    with col1:
        selected_sectors = st.multiselect(
            "セクターを選択",
            list(JAPAN_STOCKS.keys()),
            default=["自動車", "テクノロジー"],
            key="japan_sector"
        )

    with col2:
        scan_all = st.checkbox("全ての日本株をスキャン", value=False, key="all_japan")

    if scan_all:
        scan_list = JAPAN_MAJOR
    else:
        scan_list = []
        for sector in selected_sectors:
            scan_list.extend(JAPAN_STOCKS.get(sector, []))
        scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # 主要銘柄表示
    with st.expander("主要日本株ADR"):
        st.markdown("""
        | 銘柄 | 企業名 |
        |------|--------|
        | TM | トヨタ自動車 |
        | SONY | ソニー |
        | HMC | ホンダ |
        | MUFG | 三菱UFJ |
        | NTDOY | 任天堂 |
        | SMFG | 三井住友FG |
        | NMR | 野村證券 |
        | TAK | 武田薬品 |
        """)

    if st.button("🇯🇵 日本株スキャン開始", key="japan_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_europe_scan(symbols: List[str]):
    """欧州株スキャン"""
    st.markdown("**🇪🇺 欧州株（ADR）をスキャン**")

    # 国選択
    selected_countries = st.multiselect(
        "国を選択",
        list(EUROPE_STOCKS.keys()),
        default=["ドイツ", "イギリス"],
        key="europe_country"
    )

    scan_list = []
    for country in selected_countries:
        scan_list.extend(EUROPE_STOCKS.get(country, []))
    scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # 国別内訳
    for country in selected_countries:
        syms = [s for s in EUROPE_STOCKS.get(country, []) if s in symbols]
        if syms:
            st.caption(f"{country}: {', '.join(syms)}")

    if st.button("🇪🇺 欧州株スキャン開始", key="europe_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_asia_scan(symbols: List[str]):
    """アジア株スキャン"""
    st.markdown("**🌏 アジア株（日本除く、ADR）をスキャン**")

    # 国選択
    selected_countries = st.multiselect(
        "国/地域を選択",
        list(ASIA_STOCKS.keys()),
        default=["中国", "台湾"],
        key="asia_country"
    )

    scan_list = []
    for country in selected_countries:
        scan_list.extend(ASIA_STOCKS.get(country, []))
    scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # 主要銘柄
    with st.expander("主要アジア株ADR"):
        st.markdown("""
        **中国**: BABA (アリババ), JD, PDD, BIDU, NIO, XPEV
        **台湾**: TSM (TSMC), UMC
        **韓国**: Samsung (005930.KS), SK Hynix
        **インド**: INFY, WIT, HDB
        **東南アジア**: SE (Sea/Shopee), GRAB
        """)

    if st.button("🌏 アジア株スキャン開始", key="asia_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_global_scan(symbols: List[str]):
    """全地域スキャン"""
    st.markdown("**🌍 全地域の国際株をスキャン**")

    # 地域選択
    regions = st.multiselect(
        "地域を選択",
        ["日本", "欧州", "中国・アジア"],
        default=["日本", "欧州", "中国・アジア"],
        key="global_region"
    )

    scan_list = []

    if "日本" in regions:
        scan_list.extend(JAPAN_MAJOR)
    if "欧州" in regions:
        for stocks in EUROPE_STOCKS.values():
            scan_list.extend(stocks)
    if "中国・アジア" in regions:
        for stocks in ASIA_STOCKS.values():
            scan_list.extend(stocks)

    scan_list = list(dict.fromkeys(scan_list))
    scan_symbols = [s for s in scan_list if s in symbols]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("日本", len([s for s in JAPAN_MAJOR if s in symbols]))
    with col2:
        eu_count = sum(len([s for s in stocks if s in symbols]) for stocks in EUROPE_STOCKS.values())
        st.metric("欧州", eu_count)
    with col3:
        asia_count = sum(len([s for s in stocks if s in symbols]) for stocks in ASIA_STOCKS.values())
        st.metric("アジア", asia_count)

    st.info(f"合計対象: {len(scan_symbols)}銘柄")

    if st.button("🌍 全地域スキャン開始", key="global_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_tech_theme_scan(symbols: List[str]):
    """テクノロジーテーマスキャン"""
    st.markdown("**🤖 テクノロジー関連テーマ**")

    tech_themes = {
        'AI・人工知能': THEME_STOCKS.get('AI・人工知能', []),
        '半導体': THEME_STOCKS.get('半導体', []),
        'サイバーセキュリティ': THEME_STOCKS.get('サイバーセキュリティ', []),
        '量子コンピュータ': THEME_STOCKS.get('量子コンピュータ', []),
        'メタバース・ゲーム': THEME_STOCKS.get('メタバース・ゲーム', []),
        'フィンテック': THEME_STOCKS.get('フィンテック', [])
    }

    selected_themes = st.multiselect(
        "テーマを選択",
        list(tech_themes.keys()),
        default=["AI・人工知能", "半導体"],
        key="tech_theme"
    )

    scan_list = []
    for theme in selected_themes:
        scan_list.extend(tech_themes.get(theme, []))
    scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    for theme in selected_themes:
        syms = [s for s in tech_themes.get(theme, []) if s in symbols]
        if syms:
            st.caption(f"{theme}: {len(syms)}銘柄")

    if st.button("🤖 テックテーマスキャン", key="tech_theme_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_dividend_scan(symbols: List[str]):
    """配当・バリュースキャン"""
    st.markdown("**💰 配当株・バリュー株**")

    category = st.radio(
        "カテゴリ",
        ["高配当", "配当貴族", "REIT", "バリュー株"],
        horizontal=True,
        key="dividend_category"
    )

    if category == "バリュー株":
        scan_list = VALUE_STOCKS
    else:
        scan_list = DIVIDEND_STOCKS.get(category, [])

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    with st.expander("銘柄リスト"):
        st.write(", ".join(scan_symbols))

    if st.button("💰 配当・バリュースキャン", key="dividend_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_growth_scan(symbols: List[str]):
    """成長株スキャン"""
    st.markdown("**📈 成長株・スモールキャップ**")

    growth_options = {
        'EV・電気自動車': THEME_STOCKS.get('EV・電気自動車', []),
        'クリーンエネルギー': THEME_STOCKS.get('クリーンエネルギー', []),
        'バイオテック': THEME_STOCKS.get('バイオテック', []),
        '宇宙・航空': THEME_STOCKS.get('宇宙・航空', []),
        'SPAC・成長株': THEME_STOCKS.get('SPAC・成長株', []),
        '小型成長株': SMALL_CAP_GROWTH
    }

    selected = st.multiselect(
        "カテゴリを選択",
        list(growth_options.keys()),
        default=["EV・電気自動車", "小型成長株"],
        key="growth_category"
    )

    scan_list = []
    for cat in selected:
        scan_list.extend(growth_options.get(cat, []))
    scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # 注意書き
    st.warning("⚠️ 成長株は変動が大きいため、Deep Bottomシグナルが出やすい傾向があります")

    if st.button("📈 成長株スキャン", key="growth_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_all_theme_scan(symbols: List[str]):
    """全テーマスキャン"""
    st.markdown("**🏷️ 全テーマから選択**")

    all_themes = list(THEME_STOCKS.keys())

    selected_themes = st.multiselect(
        "テーマを選択（複数可）",
        all_themes,
        default=[],
        key="all_themes"
    )

    if not selected_themes:
        st.info("テーマを選択してください")
        return

    scan_list = []
    for theme in selected_themes:
        scan_list.extend(THEME_STOCKS.get(theme, []))
    scan_list = list(dict.fromkeys(scan_list))

    scan_symbols = [s for s in scan_list if s in symbols]

    st.info(f"対象: {len(scan_symbols)}銘柄")

    # テーマ別内訳
    for theme in selected_themes:
        count = len([s for s in THEME_STOCKS.get(theme, []) if s in symbols])
        st.caption(f"{theme}: {count}銘柄")

    if st.button("🏷️ テーマスキャン", key="all_theme_scan", type="primary"):
        if scan_symbols:
            run_scan(scan_symbols)
        else:
            st.warning("対象銘柄がリストにありません")


def render_watchlist_scan(symbols: List[str]):
    """ウォッチリストスキャン"""
    st.markdown("**⭐ ウォッチリスト管理**")

    # ウォッチリスト初期化
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

    # 現在のウォッチリスト表示
    if st.session_state.watchlist:
        st.success(f"ウォッチリスト: {len(st.session_state.watchlist)}銘柄")

        # 銘柄をタグ表示
        cols = st.columns(min(len(st.session_state.watchlist), 8))
        for idx, sym in enumerate(st.session_state.watchlist[:24]):
            with cols[idx % 8]:
                st.markdown(f"`{sym}`")

        if len(st.session_state.watchlist) > 24:
            st.caption(f"... 他 {len(st.session_state.watchlist) - 24}銘柄")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⭐ ウォッチリストをスキャン", key="scan_watchlist", type="primary"):
                run_scan(st.session_state.watchlist)
        with col2:
            if st.button("📋 エクスポート", key="export_watchlist"):
                st.code(",".join(st.session_state.watchlist))
        with col3:
            if st.button("🗑️ クリア", key="clear_watchlist"):
                st.session_state.watchlist = []
                st.rerun()

    else:
        st.info("ウォッチリストは空です")

    st.markdown("---")

    # 銘柄追加
    st.markdown("**銘柄を追加**")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_symbols = st.text_input(
            "銘柄（カンマ区切り）",
            placeholder="AAPL, BTC, NVDA, TM",
            key="add_to_watchlist_input"
        )
    with col2:
        if st.button("➕ 追加", key="add_watchlist_btn"):
            if new_symbols:
                to_add = [s.strip().upper() for s in new_symbols.split(',') if s.strip()]
                valid = [s for s in to_add if s in symbols and s not in st.session_state.watchlist]
                invalid = [s for s in to_add if s not in symbols]

                if valid:
                    st.session_state.watchlist.extend(valid)
                    st.success(f"追加: {', '.join(valid)}")
                if invalid:
                    st.warning(f"無効: {', '.join(invalid)}")
                st.rerun()

    # クイック追加オプション
    st.markdown("**クイック追加**")
    quick_add = st.selectbox(
        "プリセット",
        ["選択...", "主要米国株", "FAANG+", "日本株ADR", "主要暗号通貨", "高配当株"],
        key="quick_add_preset"
    )

    if quick_add != "選択...":
        preset_symbols = {
            "主要米国株": ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
            "FAANG+": ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL', 'MSFT', 'NVDA'],
            "日本株ADR": JAPAN_MAJOR[:10],
            "主要暗号通貨": ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP'],
            "高配当株": DIVIDEND_STOCKS.get('高配当', [])[:10]
        }

        if st.button(f"➕ {quick_add}を追加", key="quick_add_btn"):
            to_add = preset_symbols.get(quick_add, [])
            valid = [s for s in to_add if s in symbols and s not in st.session_state.watchlist]
            st.session_state.watchlist.extend(valid)
            st.success(f"{len(valid)}銘柄を追加しました")
            st.rerun()


def render_full_scan(symbols: List[str]):
    """全銘柄スキャン（段階的処理）"""
    st.markdown("**全銘柄を段階的にスキャン（バッチ処理）**")

    total_symbols = len(symbols)
    scanned_count = len(st.session_state.deep_bottom_scanned)
    remaining = total_symbols - scanned_count

    # 進捗表示
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("全銘柄数", total_symbols)
    with col2:
        st.metric("スキャン済み", scanned_count)
    with col3:
        st.metric("残り", remaining)
    with col4:
        detected_count = len([r for r in st.session_state.deep_bottom_results if r.get('detected')])
        st.metric("検出済み", detected_count)

    if scanned_count > 0:
        st.progress(scanned_count / total_symbols)

    # スキャン設定
    st.markdown("#### ⚙️ スキャン設定")

    col1, col2 = st.columns(2)

    with col1:
        # バッチサイズ設定
        batch_size = st.select_slider(
            "バッチサイズ（1回あたりの処理数）",
            options=[10, 25, 50, 100, 200, 500],
            value=50,
            key="batch_size"
        )

        # スキャン戦略
        strategy = st.radio(
            "スキャン戦略",
            ["順番にスキャン", "ランダムにスキャン", "暗号通貨優先", "ETF優先", "テック優先"],
            key="scan_strategy"
        )

    with col2:
        # フィルタリングオプション
        st.markdown("**プレフィルタ（高速化）**")

        filter_type = st.checkbox("アセットタイプでフィルタ", value=False, key="filter_type")
        if filter_type:
            asset_types = st.multiselect(
                "アセットタイプ",
                ["株式", "ETF", "暗号通貨"],
                default=["株式", "暗号通貨"],
                key="asset_type_filter"
            )

        skip_scanned = st.checkbox("スキャン済みをスキップ", value=True, key="skip_scanned")

    col1, col2, col3 = st.columns(3)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ 次のバッチをスキャン", key="next_batch", type="primary"):
            # 未スキャンの銘柄を取得
            unscanned = [s for s in symbols if s not in st.session_state.deep_bottom_scanned]

            # アセットタイプフィルタ適用
            if filter_type and asset_types:
                filtered = []
                for s in unscanned:
                    if "暗号通貨" in asset_types and is_crypto_symbol(s):
                        filtered.append(s)
                    elif "ETF" in asset_types and s in ETF_SYMBOLS:
                        filtered.append(s)
                    elif "株式" in asset_types and not is_crypto_symbol(s) and s not in ETF_SYMBOLS:
                        filtered.append(s)
                unscanned = filtered

            if not unscanned:
                st.success("スキャン対象の銘柄がありません！")
                return

            # 戦略に応じてソート
            if strategy == "ランダムにスキャン":
                import random
                random.shuffle(unscanned)
            elif strategy == "暗号通貨優先":
                crypto = [s for s in unscanned if is_crypto_symbol(s)]
                stocks = [s for s in unscanned if not is_crypto_symbol(s)]
                unscanned = crypto + stocks
            elif strategy == "ETF優先":
                etfs = [s for s in unscanned if s in ETF_SYMBOLS]
                others = [s for s in unscanned if s not in ETF_SYMBOLS]
                unscanned = etfs + others
            elif strategy == "テック優先":
                tech = [s for s in unscanned if s in TECH_SYMBOLS]
                others = [s for s in unscanned if s not in TECH_SYMBOLS]
                unscanned = tech + others

            # バッチ取得
            batch = unscanned[:batch_size]
            run_batch_scan(batch, show_live=True)

    with col2:
        if st.button("⏭️ 全てスキャン（自動継続）", key="auto_scan"):
            run_auto_scan(symbols, batch_size)

    with col3:
        if st.button("🔄 リセット", key="reset_scan"):
            st.session_state.deep_bottom_results = []
            st.session_state.deep_bottom_scanned = set()
            st.session_state.deep_bottom_detected_live = []
            st.rerun()

    # リアルタイム検出表示
    if st.session_state.deep_bottom_detected_live:
        st.markdown("---")
        st.subheader("🎯 リアルタイム検出")
        for item in st.session_state.deep_bottom_detected_live[-5:]:  # 最新5件
            st.success(f"💎 **{item['symbol']}** - ATH下落率: {item['drawdown_pct']:.1f}%, RSI: {item['rsi_14']:.1f}")


def render_custom_scan(symbols: List[str]):
    """カスタム選択スキャン"""
    st.markdown("**分析する銘柄を手動で選択**")

    # 入力方法選択
    input_method = st.radio(
        "入力方法",
        ["リストから選択", "テキスト入力（カンマ区切り）", "ウォッチリスト"],
        horizontal=True,
        key="input_method"
    )

    if input_method == "リストから選択":
        # フィルタオプション
        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 銘柄検索", key="symbol_search")
        with col2:
            type_filter = st.selectbox(
                "タイプ",
                ["全て", "株式のみ", "ETFのみ", "暗号通貨のみ"],
                key="type_filter_custom"
            )

        filtered_symbols = symbols

        # 検索フィルタ
        if search:
            filtered_symbols = [s for s in filtered_symbols if search.upper() in s.upper()]

        # タイプフィルタ
        if type_filter == "株式のみ":
            filtered_symbols = [s for s in filtered_symbols if not is_crypto_symbol(s) and s not in ETF_SYMBOLS]
        elif type_filter == "ETFのみ":
            filtered_symbols = [s for s in filtered_symbols if s in ETF_SYMBOLS]
        elif type_filter == "暗号通貨のみ":
            filtered_symbols = [s for s in filtered_symbols if is_crypto_symbol(s)]

        selected = st.multiselect(
            f"銘柄を選択（{len(filtered_symbols)}件中）",
            filtered_symbols,
            default=[],
            key="custom_symbols"
        )

    elif input_method == "テキスト入力（カンマ区切り）":
        st.markdown("銘柄シンボルをカンマ区切りで入力してください")
        text_input = st.text_area(
            "銘柄リスト",
            placeholder="AAPL, MSFT, GOOGL, BTC, ETH",
            key="text_symbols"
        )

        if text_input:
            # パース
            input_symbols = [s.strip().upper() for s in text_input.replace('\n', ',').split(',') if s.strip()]
            selected = [s for s in input_symbols if s in symbols]
            invalid = [s for s in input_symbols if s not in symbols]

            if selected:
                st.success(f"有効: {len(selected)}銘柄")
            if invalid:
                st.warning(f"無効（リストにない）: {', '.join(invalid[:10])}{'...' if len(invalid) > 10 else ''}")
        else:
            selected = []

    else:  # ウォッチリスト
        st.markdown("**保存されたウォッチリスト**")

        # ウォッチリスト管理
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = []

        # 既存のウォッチリスト表示
        if st.session_state.watchlist:
            st.info(f"ウォッチリスト: {len(st.session_state.watchlist)}銘柄")
            st.write(", ".join(st.session_state.watchlist))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ ウォッチリストをクリア", key="clear_watchlist"):
                    st.session_state.watchlist = []
                    st.rerun()
        else:
            st.info("ウォッチリストは空です")

        # 追加
        new_symbols = st.text_input(
            "追加する銘柄（カンマ区切り）",
            placeholder="AAPL, BTC, NVDA",
            key="add_watchlist"
        )

        if st.button("➕ ウォッチリストに追加", key="add_to_watchlist"):
            if new_symbols:
                to_add = [s.strip().upper() for s in new_symbols.split(',') if s.strip()]
                valid_adds = [s for s in to_add if s in symbols and s not in st.session_state.watchlist]
                st.session_state.watchlist.extend(valid_adds)
                st.success(f"{len(valid_adds)}銘柄を追加しました")
                st.rerun()

        selected = st.session_state.watchlist

    if selected:
        st.markdown("---")
        st.info(f"選択中: {len(selected)}銘柄")

        # プレビュー
        with st.expander("選択銘柄を確認"):
            st.write(", ".join(selected))

        if st.button("🔍 選択銘柄をスキャン", key="custom_scan", type="primary"):
            run_scan(selected)
    else:
        st.info("銘柄を選択してください")


def run_scan(symbols: List[str]):
    """シンプルなスキャン実行"""
    state_machine = StateMachine()
    results = []
    advanced = st.session_state.get('advanced_mode', False)
    use_v2 = st.session_state.get('use_v2_scoring', False)

    progress_bar = st.progress(0)
    status = st.empty()
    detected_container = st.empty()

    detected_symbols = []

    for idx, symbol in enumerate(symbols):
        progress_bar.progress((idx + 1) / len(symbols))
        mode_text = "📊V2" if use_v2 else ("🔬" if advanced else "📊")
        status.text(f"{mode_text} 分析中: {symbol} ({idx + 1}/{len(symbols)})")

        result = analyze_single_symbol(state_machine, symbol, advanced=advanced, use_v2=use_v2)
        if result:
            results.append(result)
            st.session_state.deep_bottom_scanned.add(symbol)

            if result.get('detected'):
                detected_symbols.append(result)
                strength = result.get('signal_strength', '')
                strength_emoji = {'strong': '🔥', 'moderate': '✨', 'weak': '📍'}.get(strength, '')
                detected_container.success(
                    f"💎{strength_emoji} 検出: {symbol} (ATH下落率: {result['drawdown_pct']:.1f}%)"
                )

    progress_bar.empty()
    status.empty()

    # 結果をマージ
    existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
    for r in results:
        if r['symbol'] not in existing_symbols:
            st.session_state.deep_bottom_results.append(r)

    st.session_state.deep_bottom_detected_live = detected_symbols
    st.rerun()


def run_batch_scan(symbols: List[str], show_live: bool = True):
    """バッチスキャン実行"""
    state_machine = StateMachine()
    results = []
    advanced = st.session_state.get('advanced_mode', False)
    use_v2 = st.session_state.get('use_v2_scoring', False)

    progress_bar = st.progress(0)
    status = st.empty()
    live_display = st.empty() if show_live else None

    detected_in_batch = []
    start_time = time.time()

    for idx, symbol in enumerate(symbols):
        progress_bar.progress((idx + 1) / len(symbols))

        elapsed = time.time() - start_time
        mode_text = "📊V2" if use_v2 else ("🔬" if advanced else "📊")
        if idx > 0:
            avg_time = elapsed / idx
            remaining = avg_time * (len(symbols) - idx)
            status.text(f"{mode_text} 分析中: {symbol} ({idx + 1}/{len(symbols)}) - 残り約{remaining:.0f}秒")
        else:
            status.text(f"{mode_text} 分析中: {symbol} ({idx + 1}/{len(symbols)})")

        result = analyze_single_symbol(state_machine, symbol, advanced=advanced, use_v2=use_v2)
        if result:
            results.append(result)
            st.session_state.deep_bottom_scanned.add(symbol)

            if result.get('detected'):
                detected_in_batch.append(result)
                if live_display:
                    strength = result.get('signal_strength', '')
                    strength_text = f" [{strength}]" if strength else ""
                    live_display.success(
                        f"💎 **{symbol}**{strength_text} 検出! "
                        f"ATH下落率: {result['drawdown_pct']:.1f}%, "
                        f"RSI: {result['rsi_14']:.1f}"
                    )

    progress_bar.empty()
    status.empty()

    # 結果をマージ
    existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
    for r in results:
        if r['symbol'] not in existing_symbols:
            st.session_state.deep_bottom_results.append(r)

    # ライブ検出リストに追加
    st.session_state.deep_bottom_detected_live.extend(detected_in_batch)

    # 完了メッセージ
    elapsed = time.time() - start_time
    st.success(f"✅ {len(symbols)}銘柄を{elapsed:.1f}秒で分析完了（検出: {len(detected_in_batch)}件）")

    st.rerun()


def run_auto_scan(symbols: List[str], batch_size: int):
    """自動継続スキャン"""
    unscanned = [s for s in symbols if s not in st.session_state.deep_bottom_scanned]

    if not unscanned:
        st.success("全銘柄のスキャンが完了しています！")
        return

    state_machine = StateMachine()
    advanced = st.session_state.get('advanced_mode', False)
    use_v2 = st.session_state.get('use_v2_scoring', False)
    total_batches = (len(unscanned) + batch_size - 1) // batch_size

    # 全体進捗
    overall_progress = st.progress(0)
    batch_status = st.empty()
    current_status = st.empty()
    live_detections = st.empty()

    all_detected = []
    start_time = time.time()
    mode_text = "🔬" if advanced else "📊"
    if use_v2:
        mode_text = "🚀V2 " + mode_text

    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(unscanned))
        batch = unscanned[batch_start:batch_end]

        batch_status.markdown(f"**{mode_text} バッチ {batch_idx + 1}/{total_batches}** ({len(batch)}銘柄)")

        for idx, symbol in enumerate(batch):
            overall_done = batch_start + idx + 1
            overall_progress.progress(overall_done / len(unscanned))

            elapsed = time.time() - start_time
            if overall_done > 1:
                avg_time = elapsed / overall_done
                remaining = avg_time * (len(unscanned) - overall_done)
                mins, secs = divmod(int(remaining), 60)
                current_status.text(
                    f"{mode_text} 分析中: {symbol} ({overall_done}/{len(unscanned)}) - "
                    f"残り約{mins}分{secs}秒"
                )
            else:
                current_status.text(f"{mode_text} 分析中: {symbol} ({overall_done}/{len(unscanned)})")

            result = analyze_single_symbol(state_machine, symbol, advanced=advanced, use_v2=use_v2)
            if result:
                st.session_state.deep_bottom_scanned.add(symbol)

                # 既存結果にマージ
                existing_symbols = {r['symbol'] for r in st.session_state.deep_bottom_results}
                if symbol not in existing_symbols:
                    st.session_state.deep_bottom_results.append(result)

                if result.get('detected'):
                    all_detected.append(result)
                    # 最新の検出を表示
                    recent = all_detected[-3:] if len(all_detected) >= 3 else all_detected
                    detection_text = "\n".join([
                        f"💎 **{r['symbol']}** (ATH下落: {r['drawdown_pct']:.1f}%, RSI: {r['rsi_14']:.1f})"
                        for r in recent
                    ])
                    live_detections.markdown(f"**リアルタイム検出:**\n{detection_text}")

    overall_progress.empty()
    batch_status.empty()
    current_status.empty()

    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)

    st.session_state.deep_bottom_detected_live = all_detected

    st.success(
        f"✅ 全{len(unscanned)}銘柄のスキャン完了！ "
        f"（{mins}分{secs}秒、検出: {len(all_detected)}件）"
    )

    st.rerun()


def display_deep_bottom_results(results: List[Dict]):
    """
    Deep Bottom分析結果を表示

    Args:
        results: 分析結果のリスト
    """
    st.markdown("---")
    st.subheader("📊 分析結果")

    # エラーを除外
    valid_results = [r for r in results if 'error' not in r]

    # シグナル検出された銘柄
    detected = [r for r in valid_results if r.get('detected')]

    # 高度な分析モードかどうか判定
    advanced_mode = any(r.get('signal_strength') for r in valid_results)

    # サマリーメトリクス
    if advanced_mode:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("分析銘柄数", len(valid_results))
        with col2:
            strong = len([r for r in detected if r.get('signal_strength') == 'strong'])
            moderate = len([r for r in detected if r.get('signal_strength') == 'moderate'])
            st.metric("シグナル検出", f"{len(detected)} (🔥{strong} ✨{moderate})")
        with col3:
            avg_drawdown = sum(r.get('drawdown_pct', 0) for r in valid_results) / len(valid_results) if valid_results else 0
            st.metric("平均ATH下落率", f"{avg_drawdown:.1f}%")
        with col4:
            scores = [r.get('total_score', 0) for r in valid_results if r.get('total_score')]
            avg_score = sum(scores) / len(scores) if scores else 0
            st.metric("平均スコア", f"{avg_score:.0f}/100")
        with col5:
            rsi_values = [r.get('rsi_14', 0) for r in valid_results if r.get('rsi_14')]
            avg_rsi = sum(rsi_values) / len(rsi_values) if rsi_values else 0
            st.metric("平均RSI", f"{avg_rsi:.1f}")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("分析銘柄数", len(valid_results))
        with col2:
            st.metric("シグナル検出", len(detected), delta=None)
        with col3:
            avg_drawdown = sum(r.get('drawdown_pct', 0) for r in valid_results) / len(valid_results) if valid_results else 0
            st.metric("平均ATH下落率", f"{avg_drawdown:.1f}%")
        with col4:
            rsi_values = [r.get('rsi_14', 0) for r in valid_results if r.get('rsi_14')]
            avg_rsi = sum(rsi_values) / len(rsi_values) if rsi_values else 0
            st.metric("平均RSI", f"{avg_rsi:.1f}")

    st.markdown("---")

    # シグナル検出銘柄
    if detected:
        # シグナル強度でソート（strong > moderate > weak）
        strength_order = {'strong': 0, 'moderate': 1, 'weak': 2, '': 3}
        detected_sorted = sorted(detected, key=lambda x: strength_order.get(x.get('signal_strength', ''), 3))

        st.success(f"💎 **{len(detected)}件のDeep Bottomシグナルを検出しました！**")

        for item in detected_sorted:
            with st.container():
                # シグナル強度に応じた表示
                signal_strength = item.get('signal_strength', '')
                if signal_strength == 'strong':
                    strength_badge = "🔥 強シグナル"
                    border_color = "#ff4444"
                    bg_gradient = "linear-gradient(135deg, #4a1a1a 0%, #5a2d2d 100%)"
                elif signal_strength == 'moderate':
                    strength_badge = "✨ 中シグナル"
                    border_color = "#ffaa00"
                    bg_gradient = "linear-gradient(135deg, #4a3a1a 0%, #5a4d2d 100%)"
                else:
                    strength_badge = ""
                    border_color = "#00ff88"
                    bg_gradient = "linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%)"

                st.markdown(f"""
                <div style="background: {bg_gradient};
                            padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;
                            border-left: 5px solid {border_color};">
                    <h3 style="color: {border_color}; margin: 0;">💎 {item['symbol']} {strength_badge}</h3>
                </div>
                """, unsafe_allow_html=True)

                # スコア表示（高度分析モードの場合）
                if item.get('total_score') is not None:
                    score_col1, score_col2, score_col3, score_col4, score_col5 = st.columns(5)
                    with score_col1:
                        total = item.get('total_score', 0)
                        color = "🟢" if total >= 70 else "🟡" if total >= 50 else "🔴"
                        st.metric("総合スコア", f"{color} {total:.0f}/100")
                    with score_col2:
                        st.metric("バリュー", f"{item.get('value_score', 0):.0f}/25")
                    with score_col3:
                        st.metric("テクニカル", f"{item.get('technical_score', 0):.0f}/25")
                    with score_col4:
                        st.metric("モメンタム", f"{item.get('momentum_score', 0):.0f}/25")
                    with score_col5:
                        st.metric("リスク", f"{item.get('risk_score', 0):.0f}/25")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "現在価格",
                        f"${item['current_price']:,.2f}",
                        f"ATH: ${item['ath_price']:,.2f}"
                    )

                with col2:
                    st.metric(
                        "ATH下落率",
                        f"{item['drawdown_pct']:.1f}%",
                        delta=None
                    )

                with col3:
                    st.metric(
                        "RSI(14)",
                        f"{item['rsi_14']:.1f}",
                        "売られすぎ" if item['rsi_14'] <= 30 else ""
                    )

                with col4:
                    proximity_pct = item['week52_low_proximity'] * 100
                    st.metric(
                        "52週安値からの距離",
                        f"{proximity_pct:.1f}%",
                        delta=None
                    )

                # 条件チェック詳細（基本条件）
                conditions = item.get('conditions', item.get('basic_conditions', {}))
                if conditions:
                    st.markdown("**📋 基本条件達成状況:**")
                    cond_cols = st.columns(5)
                    cond_labels = {
                        'ath_drawdown': 'ATH下落率',
                        'near_52week_low': '52週安値付近',
                        'rsi_oversold': 'RSI売られすぎ',
                        'below_ma200': '200日MA以下',
                        'not_crashing': '急落中でない'
                    }
                    for idx, (key, label) in enumerate(cond_labels.items()):
                        with cond_cols[idx]:
                            if conditions.get(key):
                                st.markdown(f"✅ {label}")
                            else:
                                st.markdown(f"❌ {label}")

                # 高度な条件（高度分析モードの場合）
                advanced_conds = item.get('advanced_conditions', {})
                if advanced_conds:
                    st.markdown("**🔬 高度指標:**")
                    adv_cols = st.columns(4)

                    adv_labels = [
                        ('bullish_divergence', 'RSIダイバージェンス'),
                        ('at_support', 'サポート接近'),
                        ('consolidating', 'レンジ形成'),
                        ('higher_lows_forming', '安値切り上げ'),
                        ('below_bollinger', 'ボリンジャー下限'),
                        ('stoch_oversold', 'ストキャス売られすぎ'),
                        ('macd_bullish', 'MACD反転')
                    ]

                    for idx, (key, label) in enumerate(adv_labels):
                        with adv_cols[idx % 4]:
                            if advanced_conds.get(key):
                                st.markdown(f"✅ {label}")
                            else:
                                st.markdown(f"⬜ {label}")

                # 追加テクニカル詳細（展開可能）
                if item.get('divergence') or item.get('support') or item.get('macd'):
                    with st.expander("📈 テクニカル詳細"):
                        tech_col1, tech_col2, tech_col3 = st.columns(3)

                        with tech_col1:
                            if item.get('divergence'):
                                div = item['divergence']
                                st.markdown("**RSIダイバージェンス**")
                                st.write(f"強気ダイバージェンス: {'あり' if div.get('bullish_divergence') else 'なし'}")

                            if item.get('bollinger'):
                                bb = item['bollinger']
                                st.markdown("**ボリンジャーバンド**")
                                st.write(f"位置: {bb.get('position', 'N/A')}")
                                st.write(f"下限以下: {'Yes' if bb.get('below_lower') else 'No'}")

                        with tech_col2:
                            if item.get('support'):
                                sup = item['support']
                                st.markdown("**サポートレベル**")
                                if sup.get('support_price'):
                                    st.write(f"サポート価格: ${sup['support_price']:,.2f}")
                                st.write(f"反発回数: {sup.get('touches', 0)}回")

                            if item.get('stochastic'):
                                stoch = item['stochastic']
                                st.markdown("**ストキャスティクス**")
                                st.write(f"%K: {stoch.get('k', 0):.1f}")
                                st.write(f"%D: {stoch.get('d', 0):.1f}")

                        with tech_col3:
                            if item.get('macd'):
                                macd = item['macd']
                                st.markdown("**MACD**")
                                st.write(f"MACD: {macd.get('macd', 0):.4f}")
                                st.write(f"シグナル: {macd.get('signal', 0):.4f}")
                                st.write(f"ヒストグラム上昇: {'Yes' if macd.get('histogram_rising') else 'No'}")

                            if item.get('consolidation'):
                                cons = item['consolidation']
                                st.markdown("**コンソリデーション**")
                                st.write(f"レンジ形成: {'Yes' if cons.get('is_consolidating') else 'No'}")
                                if cons.get('range_pct'):
                                    st.write(f"レンジ幅: {cons['range_pct']:.1f}%")

                # ファンダメンタル分析（株式のみ）
                if item.get('fundamental_score') is not None:
                    with st.expander("💰 ファンダメンタル分析"):
                        fund_col1, fund_col2 = st.columns(2)

                        with fund_col1:
                            fund_score = item.get('fundamental_score', 0)
                            fund_health = item.get('fundamental_health', 'unknown')

                            # 健全性に応じた色
                            health_colors = {
                                'healthy': '🟢',
                                'moderate': '🟡',
                                'weak': '🟠',
                                'value_trap': '🔴'
                            }
                            health_emoji = health_colors.get(fund_health, '⚪')

                            st.metric(
                                "ファンダメンタルスコア",
                                f"{fund_score:.0f}/25",
                                f"{health_emoji} {fund_health.upper()}"
                            )

                            # 調整後総合スコア
                            if item.get('adjusted_total_score') is not None:
                                adj_score = item['adjusted_total_score']
                                st.metric(
                                    "調整後総合スコア",
                                    f"{adj_score:.0f}/100",
                                    "テクニカル(75) + ファンダメンタル(25)"
                                )

                        with fund_col2:
                            details = item.get('fundamental_details', {})
                            if details:
                                st.markdown("**内訳:**")
                                st.write(f"• P/E: {details.get('pe_score', 0):.0f}/6")
                                st.write(f"• P/B: {details.get('pb_score', 0):.0f}/5")
                                st.write(f"• FCF: {details.get('fcf_score', 0):.0f}/5")
                                st.write(f"• 負債: {details.get('debt_score', 0):.0f}/5")
                                st.write(f"• 成長: {details.get('growth_score', 0):.0f}/4")

                        # 警告表示
                        warnings = item.get('fundamental_warnings', [])
                        if warnings:
                            st.warning("⚠️ " + " | ".join(warnings))

                        # ファンダメンタル調整の説明
                        if item.get('fundamental_adjustment'):
                            st.info(f"📉 {item['fundamental_adjustment']}")

                # V2スコアリング詳細（出来高・シンク）
                if item.get('scoring_version') == 'v2':
                    with st.expander("📊 V2スコア詳細（出来高確認付き）"):
                        v2_col1, v2_col2, v2_col3 = st.columns(3)

                        with v2_col1:
                            # 出来高スコア
                            vol_score = item.get('volume_score', {})
                            vol_total = vol_score.get('score', 0) if isinstance(vol_score, dict) else 0
                            vol_confirmed = item.get('volume_confirmed', False)

                            st.markdown("**📈 出来高スコア**")
                            st.metric(
                                "出来高",
                                f"{vol_total}/15",
                                "✅ 確認済" if vol_confirmed else "❌ 未確認"
                            )

                            vol_details = vol_score.get('details', {}) if isinstance(vol_score, dict) else {}
                            if vol_details:
                                climax = vol_details.get('climax_score', 0)
                                dryup = vol_details.get('dryup_score', 0)
                                trend = vol_details.get('trend_score', 0)
                                st.write(f"• クライマックス: {climax}/8")
                                st.write(f"• ドライアップ: {dryup}/5")
                                st.write(f"• トレンド: {trend}/2")

                        with v2_col2:
                            # シンクボーナス
                            sync = item.get('sync_bonus', {})
                            sync_score = sync.get('score', 0) if isinstance(sync, dict) else 0
                            sync_details = sync.get('details', {}) if isinstance(sync, dict) else {}

                            st.markdown("**🔄 シンクボーナス**")
                            st.metric("シンク", f"{sync_score}/10")

                            if sync_details:
                                details_list = sync_details.get('sync_details', [])
                                if details_list:
                                    for detail in details_list:
                                        detail_labels = {
                                            'triple_oversold': '🔻 トリプル売られ過ぎ (+5)',
                                            'divergence_confluence': '📈 ダイバージェンス合流 (+3)',
                                            'pattern_alignment': '📐 パターン整列 (+2)'
                                        }
                                        st.write(detail_labels.get(detail, detail))

                        with v2_col3:
                            # リスク情報
                            risk_deduction = item.get('risk_deduction', 0)
                            risk_factors = item.get('risk_factors', [])

                            st.markdown("**⚠️ リスク減点**")
                            st.metric("減点", f"-{risk_deduction}")

                            if risk_factors:
                                risk_labels = {
                                    'active_crash': '📉 急落中',
                                    'high_volatility': '🌊 高ボラ',
                                    'no_volume_confirmation': '❌ 出来高未確認'
                                }
                                for factor in risk_factors:
                                    st.write(f"• {risk_labels.get(factor, factor)}")

                        # コンポーネント別詳細
                        st.markdown("---")
                        st.markdown("**コンポーネント内訳**")

                        comp_cols = st.columns(5)
                        components = [
                            ('value_score', '💎 Value', 50),
                            ('technical_score', '🔧 Technical', 40),
                            ('momentum_score', '🚀 Momentum', 35),
                            ('volume_score', '📊 Volume', 15),
                            ('sync_bonus', '🔄 Sync', 10)
                        ]

                        for col, (key, label, max_score) in zip(comp_cols, components):
                            with col:
                                comp_data = item.get(key, {})
                                score = comp_data.get('score', 0) if isinstance(comp_data, dict) else 0
                                pct = (score / max_score * 100) if max_score > 0 else 0
                                st.metric(label, f"{score}/{max_score}", f"{pct:.0f}%")

                        # 生スコアと信頼度
                        raw_score = item.get('raw_score', 0)
                        confidence = item.get('confidence', 0)
                        st.caption(f"生スコア: {raw_score}/150 → 正規化: {item.get('total_score', 0)}/100 | 信頼度: {confidence}%")

                st.markdown("---")
    else:
        st.info("現在、Deep Bottomシグナルを満たす銘柄はありません。")

    # 全銘柄テーブル
    st.subheader("📋 全銘柄の詳細データ")

    # フィルタ
    col1, col2, col3 = st.columns(3)
    with col1:
        show_only_detected = st.checkbox("シグナル検出のみ表示", value=False)
    with col2:
        min_conditions = st.slider("最低条件達成数", 0, 5, 0)
    with col3:
        if advanced_mode:
            min_score = st.slider("最低スコア", 0, 100, 0)
        else:
            min_score = 0

    # ソートオプション
    sort_options = ["条件達成数（多い順）", "ATH下落率（高い順）", "RSI（低い順）", "52週安値からの距離（近い順）", "シグナル検出順"]
    if advanced_mode:
        sort_options.insert(0, "総合スコア（高い順）")
        sort_options.insert(1, "シグナル強度順")
    sort_by = st.selectbox(
        "並び替え",
        sort_options,
        key="sort_results"
    )

    # フィルタ適用
    filtered_results = valid_results
    if show_only_detected:
        filtered_results = [r for r in filtered_results if r.get('detected')]
    if min_conditions > 0:
        filtered_results = [
            r for r in filtered_results
            if sum(1 for v in r.get('conditions', r.get('basic_conditions', {})).values() if v) >= min_conditions
        ]
    if min_score > 0:
        filtered_results = [
            r for r in filtered_results
            if r.get('total_score', 0) >= min_score
        ]

    # ソート
    strength_order = {'strong': 0, 'moderate': 1, 'weak': 2, '': 3, None: 4}

    if sort_by == "総合スコア（高い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('total_score', 0), reverse=True)
    elif sort_by == "シグナル強度順":
        sorted_results = sorted(
            filtered_results,
            key=lambda x: (strength_order.get(x.get('signal_strength'), 4), -x.get('total_score', 0))
        )
    elif sort_by == "条件達成数（多い順）":
        sorted_results = sorted(
            filtered_results,
            key=lambda x: sum(1 for v in x.get('conditions', x.get('basic_conditions', {})).values() if v),
            reverse=True
        )
    elif sort_by == "ATH下落率（高い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('drawdown_pct', 0), reverse=True)
    elif sort_by == "RSI（低い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('rsi_14', 100))
    elif sort_by == "52週安値からの距離（近い順）":
        sorted_results = sorted(filtered_results, key=lambda x: x.get('week52_low_proximity', 1))
    else:
        sorted_results = sorted(filtered_results, key=lambda x: x.get('detected', False), reverse=True)

    st.info(f"表示: {len(sorted_results)}件 / 全{len(valid_results)}件")

    # データフレーム作成
    if sorted_results:
        if advanced_mode:
            # 高度分析モード用のテーブル
            df = pd.DataFrame([
                {
                    'シンボル': r['symbol'],
                    'シグナル': '🔥' if r.get('signal_strength') == 'strong' else ('✨' if r.get('signal_strength') == 'moderate' else ('📍' if r.get('signal_strength') == 'weak' else '')),
                    '強度': r.get('signal_strength', '-'),
                    'スコア': f"{r.get('total_score', 0):.0f}" if r.get('total_score') else '-',
                    '条件': f"{sum(1 for v in r.get('basic_conditions', r.get('conditions', {})).values() if v)}/5",
                    '高度条件': f"{sum(1 for v in r.get('advanced_conditions', {}).values() if v)}/7",
                    '価格': f"${r.get('current_price', 0):,.2f}",
                    'ATH下落': f"{r.get('drawdown_pct', 0):.1f}%",
                    'RSI': f"{r.get('rsi_14', 0):.1f}" if r.get('rsi_14') else '-',
                    '52週安値': f"{r.get('week52_low_proximity', 0)*100:.1f}%",
                    '7日': f"{r.get('return_7d', 0):+.1f}%"
                }
                for r in sorted_results
            ])
        else:
            # 基本分析モード用のテーブル
            df = pd.DataFrame([
                {
                    'シンボル': r['symbol'],
                    'シグナル': '💎' if r.get('detected') else '',
                    '条件達成': f"{sum(1 for v in r.get('conditions', r.get('basic_conditions', {})).values() if v)}/5",
                    '現在価格': f"${r.get('current_price', 0):,.2f}",
                    'ATH下落率': f"{r.get('drawdown_pct', 0):.1f}%",
                    'RSI(14)': f"{r.get('rsi_14', 0):.1f}" if r.get('rsi_14') else 'N/A',
                    '52週安値距離': f"{r.get('week52_low_proximity', 0)*100:.1f}%",
                    '7日リターン': f"{r.get('return_7d', 0):+.1f}%"
                }
                for r in sorted_results
            ])

        st.dataframe(df, use_container_width=True, height=400)

    # 条件別の銘柄数
    st.markdown("---")
    st.subheader("📈 条件別統計")

    col1, col2, col3 = st.columns(3)

    with col1:
        high_drawdown = sum(1 for r in valid_results if r.get('drawdown_pct', 0) >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN)
        st.metric(f"ATH下落率 ≥ {DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN}%", f"{high_drawdown}件")

    with col2:
        low_rsi = sum(1 for r in valid_results if r.get('rsi_14', 100) <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD)
        st.metric(f"RSI ≤ {DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD}", f"{low_rsi}件")

    with col3:
        near_low = sum(1 for r in valid_results if r.get('week52_low_proximity', 1) <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX)
        st.metric(f"52週安値 {DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX*100:.0f}%以内", f"{near_low}件")

    # 条件達成数別分布
    st.markdown("---")
    condition_counts = {}
    for r in valid_results:
        count = sum(1 for v in r.get('conditions', {}).values() if v)
        condition_counts[count] = condition_counts.get(count, 0) + 1

    st.subheader("📊 条件達成数別分布")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            count = condition_counts.get(i, 0)
            st.metric(f"{i}条件", f"{count}件")
