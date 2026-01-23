# アーキテクチャ再構成 - 実装サマリー

## ✅ 完了した作業

### 1. ディレクトリ構造の作成 ✅

以下のディレクトリを作成しました：

```
cache/          # キャッシュ層
fetchers/       # データ取得層
features/       # 指標計算層
signals/        # 状態機械層
scoring/        # スコアリング層
selector/       # セレクタ層（1日1個選ぶ）
notifiers/      # 通知層
scheduler/      # スケジューラ層
config/         # 設定ファイル用（将来の拡張）
```

### 2. 各レイヤーの実装 ✅

#### Cache層 (`cache/cache_sqlite.py`)
- SQLiteベースのTTL付きキャッシュ
- 現在価格: TTL 1時間
- 履歴価格: TTL 24時間
- 自動期限切れ削除機能

#### Fetchers層
- `fetchers/yahoo.py`: Yahoo Finance (yfinance) から米国株データ取得
- `fetchers/coingecko.py`: CoinGecko APIから仮想通貨データ取得
- 両方ともキャッシュ統合済み

#### Features層 (`features/indicators.py`)
- リターン計算（3日、7日、30日）
- ATH比計算
- ボラティリティ計算
- 価格レンジ計算
- 高値ブレイク判定

#### Signals層 (`signals/state_machine.py`)
- WATCH/BASE/BUY状態判定
- 状態遷移ロジック実装
- 既存の`signals.py`と互換性あり

#### Scoring層 (`scoring/vms_scorer.py`)
- Valueスコア（割安度）: ATH比、PERを考慮
- Momentumスコア（反転）: 状態、ブレイク、リターンを考慮
- Stabilityスコア（安定性）: ボラ、質スコアを考慮
- 総合スコア計算（重み付き）

#### Selector層 (`selector/daily_selector.py`) ⭐重要
- **BUY上限**: BUYは最大3候補まで、無ければBASEから1個
- **ローテーション**: 同一資産は7日間再選出禁止
- **偏り制限**: 同一セクター最大2、Crypto最大2
- **信頼度**: High/Mid/Spec を付与し、High優先
- 選出履歴をSQLiteで永続化

#### Notifiers層 (`notifiers/discord.py`)
- Discord Webhook通知
- 状態変化通知（BUY新規発生時のみ）
- Daily pick通知（1日1個）

#### Scheduler層 (`scheduler/daily_runner.py`)
- 1日1回実行するメインロジック
- 全データフローを統合
- レート制限対策（待機時間）
- レポートファイル保存

### 3. メインスクリプト ✅

- `run_daily.py`: 1日1回実行のメインスクリプト
- コマンドライン引数で設定ファイルと最大資産数を指定可能

### 4. ドキュメント ✅

- `ARCHITECTURE.md`: 詳細なアーキテクチャ説明
- `README_NEW_ARCHITECTURE.md`: 新アーキテクチャの使い方
- `MIGRATION_SUMMARY.md`: このファイル（実装サマリー）

## 🎯 実現した機能

### 「1日1個・本命だけ」

✅ **BUY上限**: BUYは最大3候補まで、無ければBASEから1個  
✅ **ローテーション**: 同一資産は7日間再選出禁止  
✅ **偏り制限**: 同一セクター最大2、Crypto最大2  
✅ **信頼度**: High/Mid/Spec を付与し、High優先  

### レート制限対策

✅ **キャッシュ層**: TTL付きSQLiteキャッシュ  
✅ **段階取得**: 必要時だけ追加データを取得  
✅ **待機時間**: 10件ごとに2秒待機  

### スコア内訳

✅ **Value（割安度）**: ATH比、PERを考慮（重み40%）  
✅ **Momentum（反転）**: 状態、ブレイク、リターンを考慮（重み35%）  
✅ **Stability（安定性）**: ボラ、質スコアを考慮（重み25%）  

## 📊 データフロー

```
1. 候補リスト（Universe）読み込み
   ↓
2. 価格取得（キャッシュ優先）
   ↓
3. 指標計算（features）
   ↓
4. 状態更新（WATCH/BASE/BUY）
   ↓
5. スコア算出（Value/Momentum/Stability）
   ↓
6. フィルタ（除外ルール）
   ↓
7. セレクタで「今日の1個」決定
   ↓
8. レポート保存＋Discord通知
```

## 🚀 使い方

### 基本的な使い方

```bash
# 1日1回実行（最大200資産を分析）
python run_daily.py config.json

# 最大資産数を指定
python run_daily.py config.json 100
```

### 設定ファイル

`config.json`に以下を設定:

```json
{
  "webhook": "https://discord.com/api/webhooks/...",
  "symbols": ["AAPL", "MSFT", "BTC", "ETH", ...]
}
```

## 🔄 既存コードとの関係

### 互換性

- 既存の`main.py`、`signals.py`、`investment_analyzer.py`は引き続き使用可能
- 新しいアーキテクチャでは`run_daily.py`を使用
- 既存の`state_store.py`はそのまま使用

### 移行オプション

1. **段階的移行**: 新アーキテクチャで動作確認後、既存コードを移行
2. **並行運用**: 新アーキテクチャと既存コードを並行運用
3. **完全移行**: 既存コードを削除して新アーキテクチャのみ使用

## ⚠️ 注意事項

### Importエラー

相対インポートの問題が発生する場合、各モジュールでパスを追加していますが、
環境によっては追加の設定が必要な場合があります。

### レート制限

- 分析する資産数が多い場合、レート制限に引っかかる可能性があります
- `max_assets`パラメータで制限してください
- キャッシュのTTLを調整することで改善できます

### データ取得エラー

- シンボル名が正しいか確認
- 仮想通貨の場合はCoinGeckoのシンボルマッピングを確認
- ネットワーク接続を確認

## 📝 次のステップ

### 推奨事項

1. **動作確認**: 少ない資産数でテスト実行
   ```bash
   python run_daily.py config.json 10
   ```

2. **設定調整**: 必要に応じてパラメータを調整
   - ローテーション日数（デフォルト7日）
   - BUY上限（デフォルト3）
   - 偏り制限（デフォルト: Crypto 2, ETF 2, TECH 2, OTHER 3）

3. **スケジューリング**: cronやタスクスケジューラで1日1回実行

### 今後の拡張

- [ ] Redisキャッシュ対応
- [ ] PostgreSQL対応（SQLiteから移行）
- [ ] より詳細なセクター分類
- [ ] 出来高データの取得
- [ ] テクニカル指標の追加（RSI、MACD等）

## 📚 参考資料

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 詳細なアーキテクチャ説明
- [README_NEW_ARCHITECTURE.md](./README_NEW_ARCHITECTURE.md) - 新アーキテクチャの使い方
- [既存README.md](./README.md) - 既存コードの説明
