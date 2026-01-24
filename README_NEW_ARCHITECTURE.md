# Crypto Price Movement Discord Alerting Bot - 新アーキテクチャ

## 🎯 「1日1個・本命だけ」を実現する強固なアーキテクチャ

急落→低迷→反転検知Botを「1日1個だけ通知」する強固なアーキテクチャに再構成しました。

## 📋 目次

- [特徴](#特徴)
- [アーキテクチャ](#アーキテクチャ)
- [セットアップ](#セットアップ)
- [使い方](#使い方)
- [主要機能](#主要機能)
- [移行ガイド](#移行ガイド)

## ✨ 特徴

### 「1日1個」の実現

- **BUY上限**: BUYは最大3候補まで、無ければBASEから1個
- **ローテーション**: 同一資産は7日間再選出禁止
- **偏り制限**: 同一セクター最大2、Crypto最大2
- **信頼度**: High/Mid/Spec を付与し、High優先

### レート制限対策

- **キャッシュ層**: TTL付きSQLiteキャッシュ（1時間/24時間）
- **段階取得**: 必要時だけ追加データを取得
- **待機時間**: 10件ごとに2秒待機

### スコア内訳

- **Value（割安度）**: ATH比、PERを考慮（重み40%）
- **Momentum（反転）**: 状態、ブレイク、リターンを考慮（重み35%）
- **Stability（安定性）**: ボラ、質スコアを考慮（重み25%）

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    run_daily.py                          │
│              (1日1回実行のメインスクリプト)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              scheduler/daily_runner.py                    │
│          (メインロジック: データフロー実行)                 │
└─────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┘
      │      │      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼      ▼      ▼
   cache  fetchers features signals scoring selector notifiers
   (キャッシュ) (取得)   (指標)  (状態)  (スコア) (選出)  (通知)
```

### レイヤー構成

| レイヤ | コンポーネント | 役割 |
|--------|---------------|------|
| **Cache** | `cache/cache_sqlite.py` | レート制限回避・再利用 |
| **Fetchers** | `fetchers/yahoo.py`, `fetchers/coingecko.py` | 価格・基本情報取得 |
| **Features** | `features/indicators.py` | リターン、ATH比、ボラ、出来高等 |
| **Signals** | `signals/state_machine.py` | WATCH/BASE/BUY 判定（状態機械） |
| **Scoring** | `scoring/vms_scorer.py` | Value/Momentum/Stability を分解 |
| **Selector** | `selector/daily_selector.py` | 偏り制御して「今日の1個」を決定 |
| **Notifiers** | `notifiers/discord.py` | 状態変化 or Daily pick を通知 |
| **Scheduler** | `scheduler/daily_runner.py` | 定期実行（分離が重要） |

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md) を参照してください。

## 🚀 セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの準備

`config.json`に以下を設定:

```json
{
  "webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
  "symbols": [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "BTC", "ETH", "SOL", "BNB",
    "SPY", "QQQ", "GLD"
  ]
}
```

### 3. ディレクトリ構造の確認

以下のディレクトリが存在することを確認:

```
Crypto-Price-Movement-Discord-Alerting-Bot/
├── cache/
├── fetchers/
├── features/
├── signals/
├── scoring/
├── selector/
├── notifiers/
├── scheduler/
└── run_daily.py
```

## 📖 使い方

### 基本的な使い方

```bash
# 1日1回実行（最大200資産を分析）
python run_daily.py config.json

# 最大資産数を指定
python run_daily.py config.json 100
```

### 実行フロー

1. **候補リスト読み込み**: `config.json`から監視対象を読み込み
2. **価格取得**: キャッシュ優先で価格データを取得
3. **指標計算**: リターン、ATH比、ボラティリティ等を計算
4. **状態更新**: WATCH/BASE/BUY状態を判定・更新
5. **スコア算出**: Value/Momentum/Stabilityスコアを計算
6. **フィルタ**: WATCH状態を除外（急落直後なので買わない）
7. **セレクタ**: 「今日の1個」を決定（ローテーション、偏り制御）
8. **通知**: Discordに通知 + レポートファイル保存

### 出力

- **Discord通知**: 「今日の1個」が通知される
  - シンボル、カテゴリ、状態、信頼度
  - 投資スコア（Value/Momentum/Stability内訳）
  - 基本情報（価格、ATH比、30日リターン）
- **レポートファイル**: `investment_report.txt`に保存
  - Daily pick詳細
  - 候補リスト（Top 10）

## 🔧 主要機能

### 1. 状態機械（WATCH/BASE/BUY）

| State | 入る条件 | 通知 |
|-------|---------|------|
| **WATCH** | 3日リターン ≤ -12%（急落） | なし（多すぎ防止） |
| **BASE** | WATCH後、7日レンジ ≤ 5%（低迷） | なし（静かに監視） |
| **BUY** | 5日高値ブレイク（反転） | **BUY候補として強通知** |

### 2. セレクタ（「1日1個」の核心）

- **BUY上限**: BUYは最大3候補まで、無ければBASEから1個
- **ローテーション**: 同一資産は7日間再選出禁止
- **偏り制限**: 
  - Crypto最大2
  - ETF最大2
  - TECH最大2
  - OTHER最大3
- **信頼度**: 
  - **High**: スコア70以上、BUY状態、資格あり
  - **Mid**: スコア60以上、BUY/BASE状態
  - **Spec**: その他（投機的）

### 3. キャッシュ層

- **現在価格**: TTL 1時間
- **履歴価格**: TTL 24時間
- **自動期限切れ**: 期限切れデータは自動削除

## 🔄 移行ガイド

### 既存コードからの移行

既存の`main.py`、`signals.py`、`investment_analyzer.py`は引き続き使用可能ですが、
新しいアーキテクチャでは`run_daily.py`を使用してください。

### 段階的移行

1. **Phase 1**: 新アーキテクチャで動作確認
   ```bash
   python run_daily.py config.json 50  # 少ない資産数でテスト
   ```

2. **Phase 2**: 既存コードを新構造に移行（オプション）

3. **Phase 3**: 既存コードを削除（オプション）

### 既存コードとの違い

| 項目 | 既存コード | 新アーキテクチャ |
|------|----------|----------------|
| **実行方法** | `python main.py config.json` | `python run_daily.py config.json` |
| **通知頻度** | 状態変化時 | 1日1個（Daily pick） |
| **キャッシュ** | なし | TTL付きSQLiteキャッシュ |
| **選出ロジック** | なし | ローテーション、偏り制御 |
| **スコア内訳** | あり | Value/Momentum/Stability分解 |

## 🐛 トラブルシューティング

### Importエラー

```bash
# パスの問題が発生する場合
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python run_daily.py config.json
```

### レート制限エラー

- キャッシュのTTLを調整（`cache/cache_sqlite.py`）
- 分析する資産数を減らす（`max_assets`パラメータ）
- 待機時間を増やす（`scheduler/daily_runner.py`）

### データ取得エラー

- シンボル名が正しいか確認
- 仮想通貨の場合はCoinGeckoのシンボルマッピングを確認（`fetchers/coingecko.py`）
- ネットワーク接続を確認

## 📚 参考資料

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 詳細なアーキテクチャ説明
- [既存README.md](./README.md) - 既存コードの説明

## 🔮 今後の拡張

- [ ] Redisキャッシュ対応
- [ ] PostgreSQL対応（SQLiteから移行）
- [ ] より詳細なセクター分類
- [ ] 出来高データの取得
- [ ] テクニカル指標の追加（RSI、MACD等）
- [ ] バックテスト機能
- [ ] Web UI（ダッシュボード）

## 📝 ライセンス

[LICENSE](./LICENSE) を参照してください。
