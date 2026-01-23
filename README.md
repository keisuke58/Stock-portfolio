# Crypto Price Movement Discord Alerting Bot & Investment Analysis Dashboard

A comprehensive investment analysis system that watches price movements of cryptocurrencies and stocks, alerts via Discord/Line/Slack/Gmail, and provides a Streamlit dashboard for visualization.

このプロジェクトは「段階4（招待制Streamlit提供）」を
最優先ゴールとする。
SaaS化（段階5）は将来オプションであり、
現時点では以下を絶対に守る：

- UIはStreamlit前提
- 認証・決済は入れない
- 外部サービス依存を増やさない
- 分析の強さ・説明・実績を最優先


## Features

### 1. Price Alerting Bot
- Real-time price movement detection
- Multi-channel notifications (Discord, Line, Slack, Gmail)
- State machine for trend detection (WATCH → BASE → BUY)

### 2. Streamlit Investment Dashboard 📊
- Interactive investment analysis dashboard
- Real-time price charts and metrics
- Multi-asset comparison
- Investment score calculation
- Financial data visualization

## Quick Start

### Streamlit Dashboard

Start the Streamlit dashboard:

```bash
streamlit run streamlit_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

**Dashboard Features:**
- 🏠 **Home**: Overview of all monitored assets with investment scores
- 📈 **Symbol Detail**: Detailed analysis for individual assets
- 🔍 **Comparison**: Side-by-side comparison of up to 5 assets
- ⚙️ **Settings**: Configuration and cache management

### Alerting Bot

Run the alerting bot:

```bash
python main.py config.json
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Create or edit `config.json`:

```json
{
    "webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
    "line_token": "YOUR_LINE_NOTIFY_ACCESS_TOKEN",
    "slack_webhook": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "gmail_user": "your-email@gmail.com",
    "gmail_password": "your-app-password",
    "gmail_to": "recipient@gmail.com",
    "symbols": ["BTC", "ETH", "AAPL", "TSLA"],
    "check_interval": 3600
}
```

### 3. Run

**Streamlit Dashboard:**
```bash
streamlit run streamlit_app.py
```

**Alerting Bot:**
```bash
python main.py config.json
```

**Daily Runner (Scheduled):**
```bash
python run_daily.py
```

## Deploy to Streamlit Cloud

### 1. Prepare Your Repository

Make sure your code is pushed to GitHub:
- `streamlit_app.py` (main app file)
- `requirements.txt` (dependencies)
- `.streamlit/config.toml` (optional configuration)

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `keisuke58/Stock-portfolio`
5. Set Main file path: `streamlit_app.py`
6. Click "Deploy!"

### 3. Configure Secrets (Important!)

After deployment, configure your secrets:

1. Go to your app's settings (☰ → Settings → Secrets)
2. Add your configuration as TOML format:

```toml
webhook = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
line_token = "YOUR_LINE_NOTIFY_ACCESS_TOKEN"
slack_webhook = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
gmail_user = "your-email@gmail.com"
gmail_password = "your-app-password"
gmail_to = "recipient@gmail.com"
symbols = ["BTC", "ETH", "AAPL", "TSLA"]
check_interval = 3600
```

**Note:** The app will work without secrets, but will use default symbols only.

### 4. Troubleshooting

If deployment fails:
- Check that all dependencies in `requirements.txt` are correct
- Ensure `streamlit_app.py` is in the root directory
- Check the deployment logs in Streamlit Cloud dashboard

## Data sources
Currently supported price data:
* [KuCoin Futures API](https://docs.kucoin.com/futures/#general)
To do:
* [KuCoin Ticker API](https://docs.kucoin.com/#get-symbols-list)
* [Coinbase Price Data API](https://developers.coinbase.com/docs/wallet/guides/price-data)

## Price movement detections
Currently supported price movements:
* % change over time

To do:
* ???

Also requires a Discord Webhook endpoint that is specific to the Discord server and channel. [Read here on how to get one.](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)

# Configuring the alerts bot
The `alerting.py` program requires a configuration file to determine what cryptocurrency it will be looking at and what calculations it will be making. the configuration file will also contain secrets like you API key to KuCoin.

An example configuration file looks like this. It may need to change for future calculations types as well as looking at ticker symbols other than cryptocurrency futures.

## config.json
```
{
    "name":"<key name>", // name of your KuCoin Futures API key
    "key":"<key id>", // key ID of your KuCoin Futures API key
    "secret":"<key secret>", // the secret key of your KuCoin Futures API key
    "pass":"<key pass>", // the password your KuCoin Futures API key
    "webhook":"<url>", // Discord webhook URL
    "time_window":60, // the time, in seconds, for the time window to analyze
    "delta":0.01, // percentage change to be analyzed in the time window. 0.01 = 1%
    "symbol":"ETHUSDTM" // ticker symbol of the futures contract
}
```

If you plan on having multiple configurations running at once, it helps to name them like `config-SYMBOL-TIMEWINDOW-PCT.json` or something.

## Logs for fired alerts appear in `logs/` directory
The logs directory will produce a file structure organized by the symbol and contract type.

The tree structure looks like this:
```
logs
└── ticker
    ├── ETHUSDTM
    ├── PEOPLEUSDTM
    ├── SUSHIUSDTM
    └── XBTUSDTM
```
Future endpoints will produce directories under `logs/` next to the `ticker` endpoint, e.g. `level2/`.
