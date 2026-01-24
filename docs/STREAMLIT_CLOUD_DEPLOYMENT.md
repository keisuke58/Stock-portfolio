# Streamlit Cloud 招待制公開ガイド

## 🎯 「招待制」とは？

**認証システムは不要です。** Streamlit CloudのURLを直接知っている人だけに共有する方式です。

### 基本方針

- ✅ **認証・決済は入れない** - 外部認証サービス（Auth0、Clerk等）は使わない
- ✅ **URL共有方式** - URLを知っている人だけがアクセス可能
- ✅ **Streamlit Cloudのみ** - 外部サービス依存なし
- ✅ **無料で運用可能** - Streamlit Cloudの無料プランで完結

---

## 📋 Streamlit Cloudの仕様

### アクセス制御

| 項目 | 説明 |
|------|------|
| **公開設定** | デフォルトで「非公開」（URLを知っている人のみアクセス可能） |
| **認証機能** | 標準では提供されていない |
| **URL形式** | `https://[app-name].streamlit.app` |
| **共有方法** | URLを直接共有するだけ |

### 無料プランでできること

- ✅ アプリの公開（URL共有）
- ✅ 無制限のアクセス（URLを知っている人）
- ✅ Secrets管理（APIキー等の機密情報）
- ✅ GitHub連携（自動デプロイ）

---

## 🚀 デプロイ手順

### 1. 準備

#### GitHubリポジトリにプッシュ

```bash
git add .
git commit -m "Streamlit Cloudデプロイ準備"
git push origin main
```

#### 必要なファイル

- ✅ `streamlit_app.py` - メインアプリファイル
- ✅ `requirements.txt` - 依存パッケージ
- ✅ `.streamlit/config.toml` - Streamlit設定（オプション）

### 2. Streamlit Cloudでデプロイ

1. **Streamlit Cloudにアクセス**
   - [share.streamlit.io](https://share.streamlit.io) にアクセス
   - GitHubアカウントでサインイン

2. **新規アプリ作成**
   - "New app" をクリック
   - リポジトリを選択: `your-username/Crypto-Price-Movement-Discord-Alerting-Bot`
   - Main file path: `streamlit_app.py`
   - Branch: `main`
   - "Deploy!" をクリック

3. **デプロイ完了**
   - 数分でデプロイが完了
   - URLが生成される: `https://[app-name].streamlit.app`

### 3. Secrets設定（重要）

#### Secretsの設定方法

1. アプリの設定画面（☰ → Settings → Secrets）を開く
2. 以下の形式でSecretsを追加:

```toml
# Discord通知設定
webhook = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

# 監視銘柄リスト
symbols = ["BTC", "ETH", "AAPL", "TSLA"]

# その他の設定
check_interval = 3600
```

#### Secretsの優先順位

アプリは以下の順序で設定を読み込みます：

1. **Streamlit Secrets**（Streamlit Cloud用）← 最優先
2. `config/app_config.json`（ローカル開発用）
3. `config/notifications_config.json`（ローカル開発用）
4. 環境変数
5. デフォルト値

**実装済み**: `config/config_loader.py` の `load_config_for_streamlit()` が自動的に処理します。

---

## 🔒 「招待制」の実現方法

### 方法1: URL共有のみ（推奨）

**最もシンプルな方法**

1. Streamlit Cloudでアプリをデプロイ
2. 生成されたURLを信頼できる人に直接共有
3. URLを知らない人はアクセスできない

**メリット**:
- ✅ 認証システム不要
- ✅ 設定が簡単
- ✅ 無料で運用可能

**デメリット**:
- ⚠️ URLが漏れると誰でもアクセス可能
- ⚠️ アクセスログが取れない（無料プラン）

### 方法2: カスタムドメイン + パスワード保護（オプション）

**より厳格な制御が必要な場合**

Streamlit Cloudでは標準でパスワード保護機能はありませんが、以下の方法で実現可能：

1. **Streamlit Secretsで簡易パスワードチェック**
   ```python
   # streamlit_app.py に追加
   import streamlit as st
   
   # パスワードチェック（簡易版）
   if 'authenticated' not in st.session_state:
       password = st.text_input("パスワードを入力", type="password")
       if password == st.secrets.get('app_password', ''):
           st.session_state.authenticated = True
           st.rerun()
       else:
           st.stop()
   ```

2. **カスタムドメイン設定**（有料プラン）
   - Streamlit Cloudの有料プランでカスタムドメインが利用可能

**注意**: この方法は簡易的なもので、本格的な認証システムではありません。

---

## 📊 段階4での「招待制」の定義

### 目標

> **「URLを知っている人だけが使える、説明できて実績のある株分析プラットフォーム」**

### 実装レベル

| 項目 | 実装内容 | 状態 |
|------|---------|------|
| **デプロイ** | Streamlit Cloudで公開 | ⏳ 未着手 |
| **URL共有** | 直接URLを共有 | ✅ 準備完了 |
| **認証システム** | 不要（URL共有のみ） | ✅ 設計済み |
| **Secrets管理** | Streamlit Secrets使用 | ✅ 実装済み |

---

## 🎯 次のステップ

### 1. デプロイ準備チェックリスト

- [ ] GitHubリポジトリに最新コードをプッシュ
- [ ] `requirements.txt` が最新であることを確認
- [ ] `.streamlit/config.toml` が存在することを確認
- [ ] Secretsに必要な情報を整理

### 2. デプロイ実行

- [ ] Streamlit Cloudでアプリを作成
- [ ] Secretsを設定
- [ ] デプロイが成功することを確認
- [ ] URLが生成されることを確認

### 3. 招待制運用開始

- [ ] URLを信頼できる人に共有
- [ ] 動作確認
- [ ] フィードバック収集

---

## 💡 よくある質問

### Q: 認証システムは必要ですか？

**A: 不要です。** 段階4では「URL共有方式」で十分です。認証システムは段階5（SaaS化）で初めて必要になります。

### Q: URLが漏れたらどうなりますか？

**A: 誰でもアクセス可能になります。** そのため、URLは信頼できる人にのみ共有してください。より厳格な制御が必要な場合は、段階5で認証システムを導入することを検討してください。

### Q: アクセスログは取れますか？

**A: 無料プランでは制限があります。** Streamlit Cloudの有料プランでは、より詳細なログが取得可能です。

### Q: カスタムドメインは使えますか？

**A: 有料プランで可能です。** 無料プランでは `*.streamlit.app` ドメインのみ使用可能です。

---

## 📝 まとめ

**「招待制Streamlit公開」= URL共有方式**

- ✅ 認証システム不要
- ✅ Streamlit Cloudのみで完結
- ✅ 無料で運用可能
- ✅ URLを知っている人だけがアクセス可能

**段階4の目標**: URLを直接共有するだけで、知人レベルから月¥1k–3kを取れるサービスを提供する。

---

**最終更新**: 2026-01-23
