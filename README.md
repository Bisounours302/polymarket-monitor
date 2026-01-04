# Polymarket Insider Monitor 🕵️‍♂️

A containerized Python application to detect suspicious behaviors (e.g., large bets from fresh wallets) on Polymarket.

## Features

- **Monitor**: Scans recent high-volume trades on Polymarket.
- **Analyze**: Checks if the buyer wallet is "fresh" (Nonce < 10) using Polygon RPC.
- **Alert**: Sends Telegram notifications for suspicious trades > $5k.
- **Dashboard**: Streamlit interface to browse and sort alerts.

## Prerequisites

- Docker & Docker Compose installed on your VPS.
- A Telegram Bot Token & Chat ID.

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd polymarket-monitor
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in your `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, etc.

3. **Start the Application:**
   ```bash
   docker-compose up -d
   ```

4. **Access the Dashboard:**
   Open `http://<your-vps-ip>:8501` in your browser.

## Checking Logs

To see if the monitor is working:
```bash
docker-compose logs -f monitor
```

## Stopping

```bash
docker-compose down
```

## Architecture

- `monitor.py`: Background worker. Connects to Gamma API (Markets) and CLOB API (Trades).
- `app.py`: Frontend dashboard. Reads from SQLite.
- `database.py`: Shared SQLAlchemy models.
- `alerts.db`: SQLite database (persisted in `./data` volume).

## Note

The application uses public Polygon RPCs by default. For production reliability, use a private RPC (Alchemy/Infura) in `.env`.
