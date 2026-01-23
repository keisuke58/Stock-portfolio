# データレイヤー実装状況

## 実装方針

段階的なデータ拡張プラグイン型アーキテクチャを採用。まずは**L1（財務指標）とL3（ニュース）**から開始し、必要に応じて**L2（マクロ）やL4（代替データ）**を追加。

---

## ✅ 実装済みレイヤー

### L0: 価格・出来高（必須）✅

**目的**: 判定の土台  
**データ例**: OHLCV, 指数, 金利  
**更新頻度**: 分〜日  
**LLM向き**: ❌（数値はコードで処理）

**実装場所**:
- `fetchers/yahoo.py`: Yahoo Financeから価格データ取得
- `fetchers/coingecko.py`: CoinGeckoから仮想通貨価格取得
- `features/indicators.py`: 価格指標計算（ATH比、リターン、ボラティリティ等）

**使用状況**: 全スコア計算の基礎データとして使用中

---

### L1: ファンダ（必須）✅

**目的**: Value/Stabilityの根拠  
**データ例**: PER, FCF, 売上/利益, 配当, 財務健全性  
**更新頻度**: 四半期〜年  
**LLM向き**: △（抽出はLLM可、判定はコード）

**実装場所**:
- `ingest/fundamental_ingester.py`: 
  - `get_fundamental_data()`: FCF、売上成長、利益率、財務健全性を取得
  - `get_analyst_data()`: アナリスト改定・EPS推移を取得
- `scoring/vms_scorer.py`:
  - `calculate_value_score()`: L1データ（FCF、売上成長、利益率）を考慮
  - `calculate_stability_score()`: 財務健全性スコアを統合
  - `calculate_momentum_score()`: アナリストデータを考慮
- `validators/data_validator.py`:
  - `validate_fundamental_data()`: L1データの検証
  - `validate_analyst_data()`: アナリストデータの検証

**優先順位**:
1. ✅ 決算・ガイダンス（公式） - SEC EDGAR統合済み（`ingest/sec_edgar_ingester.py`）
2. ✅ バリュ指標（FCF, 売上成長, 利益率） - 実装済み
3. ✅ 財務健全性（負債、利払い、流動比率） - 実装済み
4. ✅ アナリスト改定・EPS推移 - 実装済み

**追加機能**:
- ✅ **ティッカー解決**（`ingest/ticker_resolver.py`）: シンボル名から正式な会社名を解決（例: "A" = "Agilent Technologies"）
- ✅ **SEC EDGAR統合**（`ingest/sec_edgar_ingester.py`）: 公式決算・開示（10-K, 10-Q, 8-K）を自動収集

**使用状況**: 
- Valueスコアに反映（FCF、売上成長、利益率）
- Stabilityスコアに反映（財務健全性スコア）
- Momentumスコアに反映（アナリスト推奨、EPS成長）

---

### L3: ニュース/開示 ✅

**目的**: リスク検知  
**データ例**: 決算, guidance, SEC, PR  
**更新頻度**: 即時  
**LLM向き**: ✅（要約/分類）

**実装場所**:
- `ingest/news_ingester.py`:
  - `get_recent_news()`: 最近7日間のニュースを取得
  - `get_earnings_calendar()`: 決算カレンダーを取得
- `knowledge/event_classifier.py`:
  - `classify_news()`: ニュースを「好材料/悪材料/中立」に分類
  - `extract_earnings_events()`: 決算イベントを抽出
- `scoring/vms_scorer.py`:
  - `calculate_momentum_score()`: イベント（L3）を考慮してMomentumスコアを調整

**優先順位**:
5. ✅ ニュースリスク（訴訟/規制/事故） - 実装済み（キーワードベース分類）

**使用状況**:
- Momentumスコアに反映（好材料イベントで+10〜20点、悪材料イベントで-10〜20点）
- レポートに「最近のイベント」セクションとして表示
- SEC EDGAR開示もイベントとして分類・表示

**追加機能**:
- ✅ **SEC EDGAR開示分類**（`knowledge/event_classifier.py`）: 8-K、10-K、10-Qを自動分類
- ✅ **ガイダンス更新検出**: 8-Kからガイダンス関連の開示を自動検出

**注意**: 現時点ではキーワードベース分類。LLM統合は`knowledge/event_classifier.py`の`classify_news()`メソッドを拡張することで可能。

---

## ⏳ 将来拡張用レイヤー

### L2: マクロ ⏳

**目的**: 逆風/追い風  
**データ例**: CPI, 雇用, 金利, DXY  
**更新頻度**: 月〜週  
**LLM向き**: △

**実装状況**: 
- ✅ `sources_registry/source_registry.py`にデータソース定義あり（FRED等）
- ❌ 実際のデータ取得は未実装

**拡張方法**:
1. `ingest/macro_ingester.py`を作成
2. FRED API等からマクロデータを取得
3. `scoring/vms_scorer.py`の各スコア計算にマクロ要因を統合
4. `scheduler/daily_runner.py`でマクロデータを取得・統合

**使用想定**:
- 全体的な市場環境を考慮したスコア調整
- 金利上昇時は成長株のスコアを下げる等

---

### L4: 代替データ ⏳

**目的**: 先行指標  
**データ例**: 求人, アプリDL, Webトラフィック  
**更新頻度**: 週〜月  
**LLM向き**: ✅（収集/要約）

**実装状況**:
- ✅ `sources_registry/source_registry.py`にデータソース定義あり（LinkedIn Jobs等）
- ❌ 実際のデータ取得は未実装

**拡張方法**:
1. `ingest/alternative_ingester.py`を作成
2. 各代替データソースから取得（スクレイピング/API）
3. `scoring/vms_scorer.py`のMomentumスコアに統合
4. `scheduler/daily_runner.py`で代替データを取得・統合

**使用想定**:
- 求人数の増減で成長性を判断
- アプリダウンロード数で事業拡大を判断

---

## データフロー

```
1. ティッカー解決 (ingest/ticker_resolver.py)
   - シンボル名 → 会社名、CIK取得
   ↓
2. L0: 価格データ取得 (fetchers/)
   ↓
3. L1: 財務データ取得 (ingest/fundamental_ingester.py)
   ↓
4. L1拡張: SEC EDGAR開示取得 (ingest/sec_edgar_ingester.py)
   - 公式決算（10-K, 10-Q）
   - 重要イベント（8-K）
   - ガイダンス更新
   ↓
5. L3: ニュース取得 (ingest/news_ingester.py)
   ↓
6. L3: イベント分類 (knowledge/event_classifier.py)
   - ニュース分類
   - SEC EDGAR開示分類
   ↓
7. スコア計算 (scoring/vms_scorer.py)
   - Value: L0 + L1
   - Momentum: L0 + L3（イベント含む）
   - Stability: L0 + L1
   ↓
8. レポート生成 (scheduler/daily_runner.py)
   - ティッカー情報表示
   - 財務指標表示
   - SEC EDGAR開示表示
   - 根拠リンク表示
   - イベント要約表示
```

---

## データソース管理

**sources_registry/source_registry.py**で全データソースを管理：

- 信頼度レベル: HIGH / MID / SPEC
- 更新頻度: realtime / daily / weekly / quarterly
- コスト: free / paid / api_key_required
- URLテンプレート: 根拠リンク生成用

**1銘柄あたり最大Nソース**の制限により、コスト・ノイズ爆増を防止。

---

## 次の拡張ステップ

### 優先度: 高
1. **LLM統合**: `knowledge/event_classifier.py`にOpenAI API等を統合
2. ✅ **ティッカー解決**: 「A = Agilent Technologies」のような解決機能 - **実装済み**
3. ✅ **SEC EDGAR統合**: 公式決算・開示の自動収集 - **実装済み**

### 優先度: 中
1. **マクロデータ（L2）**: FRED API統合

### 優先度: 低
5. **代替データ（L4）**: LinkedIn Jobs、アプリDL数等

---

## 注意事項

- **数値判定はルール/統計で固める**: LLMは「収集・要約・分類」に使用。価格判定の土台はコードで実装。
- **データは証拠として添付**: 数値はURL/時刻/フィールド名を保存（`data_sources`フィールド）。
- **LLM出力は必ず検証**: 数値は`validators/`で弾く。
