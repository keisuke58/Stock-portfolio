# アーキテクチャ再構成: 「1日1個・本命だけ」

## 概要

急落→低迷→反転検知Botを「1日1個だけ通知」する強固なアーキテクチャに再構成しました。

## ディレクトリ構造

```
Crypto-Price-Movement-Discord-Alerting-Bot/
├── cache/              # キャッシュ層（レート制限回避）
│   ├── __init__.py
│   └── cache_sqlite.py
├── fetchers/           # データ取得層
│   ├── __init__.py
│   ├── yahoo.py        # Yahoo Finance (yfinance)
│   └── coingecko.py    # CoinGecko API
├── features/           # 指標計算層
│   ├── __init__.py
│   └── indicators.py   # リターン、ATH比、ボラ、出来高等
├── signals/            # 状態機械層
│   ├── __init__.py
│   └── state_machine.py # WATCH/BASE/BUY 判定
├── scoring/            # スコアリング層
│   ├── __init__.py
│   └── vms_scorer.py   # Value/Momentum/Stability を分解
├── selector/           # セレクタ層（1日1個選ぶ）
│   ├── __init__.py
│   └── daily_selector.py # ローテーション、偏り制御
├── notifiers/          # 通知層
│   ├── __init__.py
│   └── discord.py      # Discord通知
├── scheduler/          # スケジューラ層
│   ├── __init__.py
│   └── daily_runner.py # 1日1回実行ロジック
├── run_daily.py        # メインスクリプト（1日1回実行）
├── config.json         # 設定ファイル（監視銘柄リスト）
└── state_store.py      # 状態永続化（既存）
```

## データフロー

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

## 主要機能

### 1. キャッシュ層（cache/）

- **目的**: レート制限回避・再利用
- **実装**: SQLiteベースのTTL付きキャッシュ
- **TTL**: 現在価格1時間、履歴価格24時間

### 2. Fetcher層（fetchers/）

- **YahooFetcher**: 米国株データ取得（yfinance）
- **CoinGeckoFetcher**: 仮想通貨データ取得
- **キャッシュ統合**: 自動的にキャッシュをチェック

### 3. Features層（features/）

- **指標計算**:
  - リターン（3日、7日、30日）
  - ATH比
  - ボラティリティ
  - 価格レンジ
  - 高値ブレイク

### 4. Signals層（signals/）

- **状態機械**: WATCH/BASE/BUY 判定
- **状態遷移**:
  - WATCH: 3日リターン ≤ -12%（急落）
  - BASE: WATCH後、7日レンジ ≤ 5%（低迷）
  - BUY: 5日高値ブレイク（反転）

### 5. Scoring層（scoring/）

- **VMSスコア**:
  - **Value（割安度）**: ATH比、PERを考慮（重み40%）
  - **Momentum（反転）**: 状態、ブレイク、リターンを考慮（重み35%）
  - **Stability（安定性）**: ボラ、質スコアを考慮（重み25%）

### 6. Selector層（selector/）⭐重要

**「1日1個」を実現する核心部分**

- **BUY上限**: BUYは最大3候補まで、無ければBASEから1個
- **ローテーション**: 同一資産は7日間再選出禁止
- **偏り制限**: 同一セクター最大2、Crypto最大2
- **信頼度**: High/Mid/Spec を付与し、High優先

### 7. Notifier層（notifiers/）

- **Discord通知**:
  - Daily pick通知（1日1個）
  - BUY新規発生通知（状態変化時のみ）

### 8. Scheduler層（scheduler/）

- **DailyRunner**: 1日1回実行するメインロジック
- **処理フロー**: 上記データフローを実行

## 使い方

### 1. 設定ファイルの準備

`config.json`に以下を設定:

```json
{
  "webhook": "https://discord.com/api/webhooks/...",
  "symbols": ["AAPL", "MSFT", "BTC", "ETH", ...]
}
```

### 2. 実行

```bash
# 1日1回実行（最大200資産を分析）
python run_daily.py config.json

# 最大資産数を指定
python run_daily.py config.json 100
```

### 3. 出力

- **Discord通知**: 「今日の1個」が通知される
- **レポートファイル**: `investment_report.txt`に保存

## 設計のポイント

### レート制限対策

1. **キャッシュ優先**: 同じデータを何度も取得しない
2. **TTL管理**: 1時間/24時間で自動期限切れ
3. **段階取得**: 必要時だけ追加データを取得
4. **待機時間**: 10件ごとに2秒待機

### 「1日1個」の実現

1. **BUY上限**: 本命しか残らない（最大3候補）
2. **ローテーション**: 飽きない・偏らない（7日間再選出禁止）
3. **偏り制限**: 分散投資（同一セクター最大2）
4. **信頼度**: 外しにくい（High優先）

### 状態機械

- **WATCH**: 急落検知（通知なし、多すぎ防止）
- **BASE**: 低迷継続（通知なし、静かに監視）
- **BUY**: 反転シグナル（**BUY候補として強通知**）

## 移行ガイド

### 既存コードからの移行

既存の`main.py`、`signals.py`、`investment_analyzer.py`は引き続き使用可能ですが、
新しいアーキテクチャでは`run_daily.py`を使用してください。

### 段階的移行

1. **Phase 1**: 新アーキテクチャで動作確認
2. **Phase 2**: 既存コードを新構造に移行
3. **Phase 3**: 既存コードを削除（オプション）

## 今後の拡張

- [ ] Redisキャッシュ対応
- [ ] PostgreSQL対応（SQLiteから移行）
- [ ] より詳細なセクター分類
- [ ] 出来高データの取得
- [ ] テクニカル指標の追加（RSI、MACD等）

## トラブルシューティング

### Importエラー

相対インポートの問題が発生する場合は、各モジュールの`__init__.py`を確認してください。

### レート制限エラー

- キャッシュのTTLを調整
- 分析する資産数を減らす（`max_assets`パラメータ）
- 待機時間を増やす

### データ取得エラー

- シンボル名が正しいか確認
- 仮想通貨の場合はCoinGeckoのシンボルマッピングを確認
- ネットワーク接続を確認
