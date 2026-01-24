# 急落→低迷→反転検知Bot（改造版）

既存のシンプルなDiscord Botを改造し、「急落→低迷→反転」を検知する機能を追加しました。

## 追加機能

- **状態管理**: SQLiteでWATCH/BASE/BUY状態を追跡
- **シグナル判定**: 急落/低迷/反転を自動検出
- **通知最適化**: 状態変化時のみ通知（通知過多を防止）
- **複数通知対応**: Discord、Line、Slack、Gmailのいずれか、または複数に同時通知可能

## ファイル構成

```
.
├── main.py              # メインロジック（新規）
├── state_store.py       # SQLite状態管理（新規）
├── signals.py           # シグナル判定ロジック（新規）
├── config.json          # 設定ファイル（新規）
├── requirements.txt     # 依存関係（新規）
├── alerting.py          # 既存ファイル（参考用）
└── README_NEW.md        # このファイル
```

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの編集

`config.json`を編集して通知設定を行います：

```json
{
    "webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
    "line_token": "YOUR_LINE_NOTIFY_ACCESS_TOKEN",
    "slack_webhook": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "gmail_user": "your-email@gmail.com",
    "gmail_password": "your-app-password",
    "gmail_to": "recipient@gmail.com",
    "symbols": ["BTC"],
    "check_interval": 3600
}
```

**設定項目:**
- `webhook`: Discord Webhook URL（オプション）
  - Discordチャンネルの設定からWebhookを作成
- `line_token`: Line Notify アクセストークン（オプション）
  - [Line Notify](https://notify-bot.line.me/)でトークンを取得
- `slack_webhook`: Slack Incoming Webhook URL（オプション）
  - Slackワークスペースの設定からIncoming Webhookを作成
- `gmail_user`: Gmail送信元アドレス（オプション）
- `gmail_password`: Gmailアプリパスワード（オプション）
  - 2段階認証を有効にしてアプリパスワードを生成
- `gmail_to`: 送信先メールアドレス（オプション）
- `symbols`: 監視対象のシンボルリスト（例: `["BTC", "ETH"]`）
- `check_interval`: チェック間隔（秒）。デフォルト3600（1時間）

**注意:** 通知設定は少なくとも1つ必要です。複数設定すると、すべての通知先に送信されます。

### 3. 実行

```bash
python main.py config.json
```

## 状態遷移ロジック

| 状態 | 条件 | 意味 |
|------|------|------|
| **WATCH** | 3日リターン ≤ -12% | 急落検知（候補入り） |
| **BASE** | WATCH後、7日の価格レンジが ±5%以内 | 底形成ゾーン（低迷継続） |
| **BUY** | 直近5日高値を上抜け | 反転シグナル（エントリー候補） |
| **NORMAL** | 上記以外 | 通常状態 |

## 通知ルール

**状態変化時のみ通知**（同じ状態のままでは通知なし）

- `NORMAL → WATCH`: 「急落検知：WATCH入り」
- `WATCH → BASE`: 「低迷継続：BASE入り」
- `BASE → BUY`: 「反転：BUY候補」（最重要）
- 同じ状態のまま: 通知なし

**通知先:**
- Discord: `webhook`が設定されている場合
- Line: `line_token`が設定されている場合
- Slack: `slack_webhook`が設定されている場合
- Gmail: `gmail_user`、`gmail_password`、`gmail_to`がすべて設定されている場合
- 複数設定されている場合は、すべての通知先に送信されます

## データソース

- **価格データ**: CoinGecko API（無料、APIキー不要）
- **状態管理**: SQLite（`asset_state.db`が自動作成）

## カスタマイズ

### 監視対象の追加

`config.json`の`symbols`に追加：

```json
{
    "symbols": ["BTC", "ETH", "SOL"]
}
```

### シグナル条件の調整

`signals.py`の以下の関数を編集：

- `detect_watch_signal()`: 急落の閾値（デフォルト: -12%）
- `detect_base_signal()`: 低迷のレンジ幅（デフォルト: ±5%）
- `detect_buy_signal()`: 反転の判定条件

### 実行頻度の変更

`config.json`の`check_interval`を変更：

- `3600`: 1時間ごと
- `86400`: 1日1回
- `1800`: 30分ごと

## トラブルシューティング

### CoinGecko APIのレート制限

CoinGeckoの無料プランは1分あたり10-50リクエストまで。複数シンボルを監視する場合は`check_interval`を長めに設定してください。

### データベースのリセット

状態をリセットしたい場合：

```bash
rm asset_state.db
```

次回実行時に自動的に再作成されます。

### Gmail通知の設定

Gmail通知を使用する場合：

1. **2段階認証を有効にする**
   - Googleアカウントの設定から2段階認証を有効化

2. **アプリパスワードを生成**
   - Googleアカウント設定 → セキュリティ → 2段階認証プロセス
   - 「アプリパスワード」を選択して生成
   - 生成された16文字のパスワードを`gmail_password`に設定

3. **設定例**
   ```json
   {
       "gmail_user": "your-email@gmail.com",
       "gmail_password": "abcd efgh ijkl mnop",
       "gmail_to": "recipient@gmail.com"
   }
   ```

### Slack通知の設定

1. Slackワークスペースにログイン
2. 「Apps」→「Incoming Webhooks」を検索
3. 「Add to Slack」をクリック
4. 通知を送信したいチャンネルを選択
5. Webhook URLをコピーして`slack_webhook`に設定

## 既存の`alerting.py`との違い

- **既存**: 短期的な価格変動をリアルタイム監視（KuCoin Futures API）
- **新規**: 中長期的なトレンド変化を検知（CoinGecko API）

両方を併用することも可能です。
