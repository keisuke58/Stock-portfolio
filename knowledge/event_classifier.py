"""
イベント分類モジュール（LLM使用）
ニュース・開示を「好材料/悪材料/中立」に分類
"""
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

# OpenAI API統合（オプション）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. LLM classification will use keyword-based fallback.")

# Google Gemini API統合（オプション）
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI library not available. Gemini LLM classification will use keyword-based fallback.")


class EventType(Enum):
    """イベントタイプ"""
    POSITIVE = "positive"  # 好材料
    NEGATIVE = "negative"  # 悪材料
    NEUTRAL = "neutral"  # 中立
    UNKNOWN = "unknown"  # 不明


class EventImpact(Enum):
    """イベントの影響度"""
    HIGH = "high"  # 高影響
    MEDIUM = "medium"  # 中影響
    LOW = "low"  # 低影響


class EventClassifier:
    """
    イベント分類クラス（LLM使用）
    
    OpenAI APIまたはGoogle Gemini APIを使用してニュース・開示を分類します。
    APIが利用できない場合はキーワードベースのフォールバックを使用します。
    """
    
    def __init__(self, llm_api_key: Optional[str] = None, llm_model: str = "gpt-4o-mini", llm_temperature: float = 0.3):
        """
        Args:
            llm_api_key: OpenAI APIキーまたはGemini APIキー
            llm_model: 使用するモデル（デフォルト: gpt-4o-mini、Geminiの場合はgemini-pro等）
            llm_temperature: 温度パラメータ（デフォルト: 0.3）
        """
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.llm_temperature = llm_temperature
        self.client = None
        self.use_gemini = False
        
        # モデル名からGeminiかOpenAIかを判定
        if llm_model.lower().startswith('gemini'):
            self.use_gemini = True
        
        # Gemini APIクライアントの初期化
        if self.use_gemini and llm_api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=llm_api_key)
                self.client = genai.GenerativeModel(llm_model)
                logger.info(f"Gemini client initialized with model: {llm_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}. Using keyword-based fallback.")
                self.client = None
        # OpenAIクライアントの初期化
        elif not self.use_gemini and llm_api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=llm_api_key)
                logger.info(f"OpenAI client initialized with model: {llm_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Using keyword-based fallback.")
                self.client = None
        else:
            if not llm_api_key:
                logger.info("No LLM API key provided. Using keyword-based classification.")
            if self.use_gemini and not GEMINI_AVAILABLE:
                logger.warning("Gemini library not available. Using keyword-based classification.")
            elif not self.use_gemini and not OPENAI_AVAILABLE:
                logger.warning("OpenAI library not available. Using keyword-based classification.")
    
    def classify_news(self, news_items: List[Dict], max_llm_items: int = 5) -> List[Dict]:
        """
        ニュースを分類（好材料/悪材料/中立）
        
        LLM APIが利用可能な場合はLLMで分類、そうでない場合はキーワードベースで分類します。
        CPU環境でのパフォーマンスを考慮し、LLM分類は最大max_llm_items件までに制限します。
        
        Args:
            news_items: ニュース記事のリスト
            max_llm_items: LLMで分類する最大件数（デフォルト: 5、CPU環境でのパフォーマンス考慮）
        
        Returns:
            分類済みイベントのリスト
        """
        events = []
        
        # LLM分類するアイテムを制限（最新の重要そうなもの優先）
        llm_items = news_items[:max_llm_items] if self.client else []
        keyword_items = news_items[max_llm_items:] if self.client else news_items
        
        # LLM分類（制限付き）
        for news in llm_items:
            try:
                event = self._classify_with_llm(news)
            except Exception as e:
                logger.warning(f"LLM classification failed for news '{news.get('title', '')}': {e}. Using keyword-based fallback.")
                event = self._classify_simple(news)
            
            events.append({
                'title': news.get('title', ''),
                'link': news.get('link', ''),
                'event_type': event['type'].value,
                'impact': event['impact'].value,
                'summary': event.get('summary', ''),
                'published_time': news.get('published_time'),
                'data_timestamp': datetime.utcnow().isoformat(),
                'classification_method': 'llm'
            })
            
            # レート制限対策: リクエスト間に少し待機
            time.sleep(0.1)
        
        # キーワードベース分類（残りのアイテム）
        for news in keyword_items:
            event = self._classify_simple(news)
            events.append({
                'title': news.get('title', ''),
                'link': news.get('link', ''),
                'event_type': event['type'].value,
                'impact': event['impact'].value,
                'summary': event.get('summary', ''),
                'published_time': news.get('published_time'),
                'data_timestamp': datetime.utcnow().isoformat(),
                'classification_method': 'keyword'
            })
        
        return events
    
    def _classify_with_llm(self, news: Dict) -> Dict:
        """
        LLMを使用してニュースを分類
        
        Args:
            news: ニュース記事の辞書
        
        Returns:
            分類結果の辞書（type, impact, summary）
        """
        title = news.get('title', '')
        publisher = news.get('publisher', '')
        
        # プロンプト設計
        prompt = f"""You are a financial news analyst. Classify the following news article about a stock/company.

Title: {title}
Publisher: {publisher}

Classify this news as:
1. Event type: "positive" (good news), "negative" (bad news), or "neutral" (neither clearly positive nor negative)
2. Impact: "high" (significant market impact), "medium" (moderate impact), or "low" (minimal impact)
3. Summary: A brief 1-2 sentence summary in Japanese explaining why this is positive/negative/neutral

Respond in the following JSON format:
{{
    "event_type": "positive|negative|neutral",
    "impact": "high|medium|low",
    "summary": "brief summary in Japanese"
}}

Only respond with valid JSON, no additional text."""

        try:
            # LLM API呼び出し（リトライロジック付き）
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    import json
                    
                    # Gemini APIの場合
                    if self.use_gemini:
                        full_prompt = f"You are a financial news analyst. Always respond with valid JSON only.\n\n{prompt}"
                        response = self.client.generate_content(
                            full_prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=self.llm_temperature,
                                max_output_tokens=200,
                            )
                        )
                        content = response.text.strip()
                    # OpenAI APIの場合
                    else:
                        response = self.client.chat.completions.create(
                            model=self.llm_model,
                            messages=[
                                {"role": "system", "content": "You are a financial news analyst. Always respond with valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=self.llm_temperature,
                            max_tokens=200,
                            timeout=5  # CPU環境を考慮して5秒に短縮
                        )
                        content = response.choices[0].message.content.strip()
                    
                    # JSONを抽出（```json で囲まれている場合がある）
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    result = json.loads(content)
                    
                    # イベントタイプをマッピング
                    event_type_str = result.get('event_type', 'neutral').lower()
                    if event_type_str == 'positive':
                        event_type = EventType.POSITIVE
                    elif event_type_str == 'negative':
                        event_type = EventType.NEGATIVE
                    else:
                        event_type = EventType.NEUTRAL
                    
                    # 影響度をマッピング
                    impact_str = result.get('impact', 'low').lower()
                    if impact_str == 'high':
                        impact = EventImpact.HIGH
                    elif impact_str == 'medium':
                        impact = EventImpact.MEDIUM
                    else:
                        impact = EventImpact.LOW
                    
                    return {
                        'type': event_type,
                        'impact': impact,
                        'summary': result.get('summary', '分類完了')
                    }
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying...")
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        raise
            
        except Exception as e:
            logger.error(f"LLM classification failed after retries: {e}")
            raise
        
        # フォールバック（通常は到達しない）
        return {
            'type': EventType.NEUTRAL,
            'impact': EventImpact.LOW,
            'summary': '分類失敗'
        }
    
    def _classify_simple(self, news: Dict) -> Dict:
        """
        簡易分類（キーワードベース）
        TODO: LLMに置き換え
        """
        title = news.get('title', '').lower()
        
        # 好材料キーワード
        positive_keywords = [
            'beat', 'exceed', 'growth', 'profit', 'gain', 'upgrade',
            'positive', 'strong', 'record', 'expansion', 'acquisition'
        ]
        
        # 悪材料キーワード
        negative_keywords = [
            'miss', 'decline', 'loss', 'downgrade', 'negative', 'weak',
            'lawsuit', 'regulation', 'investigation', 'breach', 'hack'
        ]
        
        positive_count = sum(1 for kw in positive_keywords if kw in title)
        negative_count = sum(1 for kw in negative_keywords if kw in title)
        
        if positive_count > negative_count:
            return {
                'type': EventType.POSITIVE,
                'impact': EventImpact.MEDIUM,
                'summary': '好材料の可能性'
            }
        elif negative_count > positive_count:
            return {
                'type': EventType.NEGATIVE,
                'impact': EventImpact.MEDIUM,
                'summary': '悪材料の可能性'
            }
        else:
            return {
                'type': EventType.NEUTRAL,
                'impact': EventImpact.LOW,
                'summary': '中立'
            }
    
    def extract_earnings_events(self, earnings_data: Dict) -> List[Dict]:
        """
        決算データからイベントを抽出
        
        Args:
            earnings_data: 決算カレンダーデータ
        
        Returns:
            決算イベントのリスト
        """
        events = []
        
        if earnings_data and earnings_data.get('next_earnings_date'):
            events.append({
                'event_type': EventType.NEUTRAL.value,
                'impact': EventImpact.HIGH.value,
                'summary': f"次回決算予定: {earnings_data['next_earnings_date']}",
                'data_timestamp': datetime.utcnow().isoformat()
            })
        
        return events
    
    def classify_sec_filings(self, filings: List[Dict]) -> List[Dict]:
        """
        SEC EDGAR開示書類を分類（好材料/悪材料/中立）
        
        LLM APIが利用可能な場合はLLMで分類、そうでない場合はキーワードベースで分類します。
        
        Args:
            filings: SEC EDGAR開示書類のリスト
        
        Returns:
            分類済みイベントのリスト
        """
        events = []
        
        for filing in filings:
            form = filing.get('form', '')
            description = filing.get('description', '')
            filing_date = filing.get('filing_date', '')
            url = filing.get('url', '')
            
            # LLM分類を試行（8-Kなどの重要書類の場合）
            if self.client and form == '8-K' and description:
                try:
                    event_result = self._classify_sec_filing_with_llm(form, description, filing_date)
                    events.append({
                        'title': f"SEC Filing: {form}",
                        'link': url,
                        'event_type': event_result['type'].value,
                        'impact': event_result['impact'].value,
                        'summary': event_result.get('summary', description or f"{form} filed on {filing_date}"),
                        'published_time': filing_date,
                        'data_timestamp': datetime.utcnow().isoformat()
                    })
                    time.sleep(0.1)  # レート制限対策
                    continue
                except Exception as e:
                    logger.warning(f"LLM classification failed for SEC filing {form}: {e}. Using keyword-based fallback.")
            
            # キーワードベース分類（フォールバック）
            description_lower = description.lower() if description else ''
            
            if form == '8-K':
                # 8-Kは重要イベント
                event_type = EventType.NEUTRAL
                impact = EventImpact.HIGH
                
                # 説明文から好材料/悪材料を判定
                if any(keyword in description_lower for keyword in ['acquisition', 'merger', 'partnership', 'expansion']):
                    event_type = EventType.POSITIVE
                elif any(keyword in description_lower for keyword in ['bankruptcy', 'delisting', 'investigation', 'lawsuit']):
                    event_type = EventType.NEGATIVE
                
                events.append({
                    'title': f"SEC Filing: {form}",
                    'link': url,
                    'event_type': event_type.value,
                    'impact': impact.value,
                    'summary': description or f"{form} filed on {filing_date}",
                    'published_time': filing_date,
                    'data_timestamp': datetime.utcnow().isoformat()
                })
            elif form in ['10-K', '10-Q']:
                # 決算報告書は中立だが高影響
                events.append({
                    'title': f"SEC Filing: {form}",
                    'link': url,
                    'event_type': EventType.NEUTRAL.value,
                    'impact': EventImpact.HIGH.value,
                    'summary': f"{form} filed on {filing_date}",
                    'published_time': filing_date,
                    'data_timestamp': datetime.utcnow().isoformat()
                })
        
        return events
    
    def _classify_sec_filing_with_llm(self, form: str, description: str, filing_date: str) -> Dict:
        """
        LLMを使用してSEC EDGAR開示を分類
        
        Args:
            form: フォームタイプ（例: 8-K）
            description: 開示の説明
            filing_date: 提出日
        
        Returns:
            分類結果の辞書（type, impact, summary）
        """
        prompt = f"""You are a financial analyst. Classify the following SEC EDGAR filing.

Form Type: {form}
Filing Date: {filing_date}
Description: {description}

Classify this filing as:
1. Event type: "positive" (good news for investors), "negative" (bad news), or "neutral" (neither clearly positive nor negative)
2. Impact: "high" (significant market impact), "medium" (moderate impact), or "low" (minimal impact)
3. Summary: A brief 1-2 sentence summary in Japanese explaining the filing and its potential impact

Respond in the following JSON format:
{{
    "event_type": "positive|negative|neutral",
    "impact": "high|medium|low",
    "summary": "brief summary in Japanese"
}}

Only respond with valid JSON, no additional text."""

        try:
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    import json
                    
                    # Gemini APIの場合
                    if self.use_gemini:
                        full_prompt = f"You are a financial analyst. Always respond with valid JSON only.\n\n{prompt}"
                        response = self.client.generate_content(
                            full_prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=self.llm_temperature,
                                max_output_tokens=200,
                            )
                        )
                        content = response.text.strip()
                    # OpenAI APIの場合
                    else:
                        response = self.client.chat.completions.create(
                            model=self.llm_model,
                            messages=[
                                {"role": "system", "content": "You are a financial analyst. Always respond with valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=self.llm_temperature,
                            max_tokens=200,
                            timeout=5  # CPU環境を考慮して5秒に短縮
                        )
                        content = response.choices[0].message.content.strip()
                    
                    # JSONを抽出
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    result = json.loads(content)
                    
                    # イベントタイプをマッピング
                    event_type_str = result.get('event_type', 'neutral').lower()
                    if event_type_str == 'positive':
                        event_type = EventType.POSITIVE
                    elif event_type_str == 'negative':
                        event_type = EventType.NEGATIVE
                    else:
                        event_type = EventType.NEUTRAL
                    
                    # 影響度をマッピング
                    impact_str = result.get('impact', 'high').lower()  # SEC filingは通常高影響
                    if impact_str == 'high':
                        impact = EventImpact.HIGH
                    elif impact_str == 'medium':
                        impact = EventImpact.MEDIUM
                    else:
                        impact = EventImpact.LOW
                    
                    return {
                        'type': event_type,
                        'impact': impact,
                        'summary': result.get('summary', f"{form}提出: {description[:100]}")
                    }
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying...")
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        raise
            
        except Exception as e:
            logger.error(f"LLM classification failed after retries: {e}")
            raise
        
        # フォールバック
        return {
            'type': EventType.NEUTRAL,
            'impact': EventImpact.HIGH,
            'summary': f"{form}提出: {description[:100]}"
        }
