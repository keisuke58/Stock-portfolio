"""
データソースレジストリ
各データソースの信頼度・更新頻度・コストを管理
"""
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class SourceType(Enum):
    """データソースの種類"""
    OFFICIAL = "official"  # 公式（決算、SEC、IR）
    REPUTABLE = "reputable"  # 信頼できる（Yahoo Finance、Bloomberg API等）
    COMMUNITY = "community"  # コミュニティ（Reddit、Twitter等）


class ReliabilityLevel(Enum):
    """信頼度レベル"""
    HIGH = "high"  # 公式・高信頼
    MID = "mid"  # 中程度
    SPEC = "spec"  # 推測・低信頼


@dataclass
class DataSource:
    """データソースの定義"""
    name: str
    source_type: SourceType
    reliability: ReliabilityLevel
    update_frequency: str  # "realtime", "daily", "weekly", "quarterly"
    cost: str  # "free", "paid", "api_key_required"
    description: str
    url_template: Optional[str] = None  # URLテンプレート（例: "https://finance.yahoo.com/quote/{symbol}"）
    max_sources_per_symbol: int = 5  # 1銘柄あたりの最大ソース数


class DataSourceRegistry:
    """データソースのカタログ"""
    
    # L0: 価格・出来高（必須）
    PRICE_SOURCES = [
        DataSource(
            name="Yahoo Finance",
            source_type=SourceType.REPUTABLE,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="realtime",
            cost="free",
            description="価格・出来高・基本財務指標",
            url_template="https://finance.yahoo.com/quote/{symbol}"
        ),
        DataSource(
            name="CoinGecko",
            source_type=SourceType.REPUTABLE,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="realtime",
            cost="free",
            description="仮想通貨価格・出来高",
            url_template="https://www.coingecko.com/en/coins/{symbol}"
        ),
    ]
    
    # L1: ファンダ（必須）
    FUNDAMENTAL_SOURCES = [
        DataSource(
            name="Yahoo Finance Fundamentals",
            source_type=SourceType.REPUTABLE,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="daily",
            cost="free",
            description="PER, PBR, FCF, 売上/利益, 配当",
            url_template="https://finance.yahoo.com/quote/{symbol}/key-statistics"
        ),
        DataSource(
            name="SEC EDGAR",
            source_type=SourceType.OFFICIAL,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="quarterly",
            cost="free",
            description="公式決算・財務諸表（10-K, 10-Q）",
            url_template="https://www.sec.gov/cgi-bin/browse-edgar?CIK={symbol}"
        ),
    ]
    
    # L2: マクロ
    MACRO_SOURCES = [
        DataSource(
            name="FRED (Federal Reserve)",
            source_type=SourceType.OFFICIAL,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="weekly",
            cost="free",
            description="CPI, 雇用, 金利, DXY",
            url_template="https://fred.stlouisfed.org/"
        ),
    ]
    
    # L3: ニュース/開示
    NEWS_SOURCES = [
        DataSource(
            name="Yahoo Finance News",
            source_type=SourceType.REPUTABLE,
            reliability=ReliabilityLevel.MID,
            update_frequency="realtime",
            cost="free",
            description="ニュース・プレスリリース",
            url_template="https://finance.yahoo.com/quote/{symbol}/news"
        ),
        DataSource(
            name="SEC Filings",
            source_type=SourceType.OFFICIAL,
            reliability=ReliabilityLevel.HIGH,
            update_frequency="realtime",
            cost="free",
            description="8-K（重要イベント）、PR（プレスリリース）",
            url_template="https://www.sec.gov/cgi-bin/browse-edgar?CIK={symbol}&type=8-K"
        ),
    ]
    
    # L4: 代替データ
    ALTERNATIVE_SOURCES = [
        DataSource(
            name="LinkedIn Jobs",
            source_type=SourceType.COMMUNITY,
            reliability=ReliabilityLevel.SPEC,
            update_frequency="weekly",
            cost="free",
            description="求人数（成長指標）",
            url_template="https://www.linkedin.com/jobs/search/?keywords={company_name}"
        ),
    ]
    
    @classmethod
    def get_sources_for_layer(cls, layer: str) -> List[DataSource]:
        """
        レイヤーに応じたデータソースを取得
        
        Args:
            layer: "L0", "L1", "L2", "L3", "L4"
        """
        layer_map = {
            "L0": cls.PRICE_SOURCES,
            "L1": cls.FUNDAMENTAL_SOURCES,
            "L2": cls.MACRO_SOURCES,
            "L3": cls.NEWS_SOURCES,
            "L4": cls.ALTERNATIVE_SOURCES,
        }
        return layer_map.get(layer, [])
    
    @classmethod
    def get_sources_for_symbol(cls, symbol: str, layers: List[str] = None) -> Dict[str, List[DataSource]]:
        """
        銘柄に応じたデータソースを取得（優先順位付き）
        
        Args:
            symbol: シンボル名
            layers: 取得するレイヤー（Noneの場合は全レイヤー）
        
        Returns:
            レイヤーごとのデータソースリスト
        """
        if layers is None:
            layers = ["L0", "L1", "L2", "L3", "L4"]
        
        result = {}
        for layer in layers:
            sources = cls.get_sources_for_layer(layer)
            # 信頼度順にソート（HIGH > MID > SPEC）
            reliability_order = {
                ReliabilityLevel.HIGH: 0,
                ReliabilityLevel.MID: 1,
                ReliabilityLevel.SPEC: 2
            }
            sources_sorted = sorted(
                sources,
                key=lambda s: reliability_order.get(s.reliability, 99)
            )
            result[layer] = sources_sorted
        
        return result
    
    @classmethod
    def format_source_url(cls, source: DataSource, symbol: str, **kwargs) -> Optional[str]:
        """
        データソースのURLを生成
        
        Args:
            source: データソース
            symbol: シンボル名
            **kwargs: URLテンプレートに渡す追加パラメータ
        """
        if source.url_template:
            try:
                return source.url_template.format(symbol=symbol, **kwargs)
            except KeyError:
                return None
        return None
