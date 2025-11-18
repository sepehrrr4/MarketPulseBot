# Crypto Price Watcher & Telegram Bot 🚀

A complete ecosystem for real-time cryptocurrency and gold price monitoring, featuring a multi-source scraper, a FastAPI backend, and a fully interactive Telegram Bot.

## 🌟 Features

- **🕷 Multi-Layer Scraper:** Fetches prices from Binance, Mexc, LBank, and CoinGecko with smart fallback logic to ensure 100% uptime.
- **🤖 Telegram Bot:** - Live price checks.
  - Price alerts (Above/Below targets).
  - Group management (Add to groups, set auto-post intervals).
  - Bilingual support (English & Persian).
- **⚡️ FAST API:** Exposes real-time price data via REST endpoints.
- **🛡 Resilience:** Uses atomic file writes to prevent race conditions between scraper and bot.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/REPO_NAME.git](https://github.com/YOUR_USERNAME/REPO_NAME.git)
   cd REPO_NAME