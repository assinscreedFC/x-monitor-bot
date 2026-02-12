# 🐦 Twitter/X Monitor & Telegram Bot

<div align="center">
  <p><strong>Automated Twitter/X monitoring with real-time Telegram notifications and media support</strong></p>

  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
  [![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-green?style=for-the-badge&logo=playwright)](https://playwright.dev/)

  ![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)
  ![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat-square)
</div>

## 📋 Overview

**Twitter/X Monitor Bot** is a sophisticated Python application designed to monitor X (formerly Twitter) user profiles in real-time. By utilizing **Playwright** with advanced stealth techniques, it detects new posts, processes media (images/videos) in high quality, and sends instant notifications to a Telegram channel.

- 📊 **Smart Scraping** of user profiles using persistent browser contexts
- 🚀 **Stealth Mode** to bypass bot detection and rate limits
- 📱 **Rich Alerts** on Telegram with media galleries and direct links
- 🔄 **Proxy Rotation** for enhanced privacy and stability
- 🍪 **Session Management** via persistent cookies (no API key required)

## ✨ Features

### Core Features
- **Real-Time Monitoring**: Periodic scanning of target profiles for new tweets.
- **Media Extraction**: Automatically extracts high-quality images and videos (`.jpg`, `.mp4`, `.m3u8`).
- **Telegram Integration**: Sends formatted messages with media attachments directly to your chat or channel.
- **Keyword/Date Filtering**: Avoids duplicates and filters old content.

### Advanced Features
- **Anti-Detection**: Uses `playwright-stealth` and custom JavaScript injection to mask automation.
- **Proxy Management**: Supports rotational proxies with automatic failover and error counting.
- **Admin Commands**: Control the bot via Telegram (`/add_watch`, `/status`, `/proxy_list`, etc.).
- **Scheduler**: Asynchronous task manager to handle multiple profiles efficiently.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** and pip
- **Playwright** browsers installed
- **Telegram Bot Token** from @BotFather

### Installation

1. **Clone the project**
   ```bash
   git clone https://github.com/assinscreedFC/x-monitor-bot.git
   cd x-monitor-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Environment Configuration**
   Create a `.env` file based on your `settings.py` or `config` folder:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_log_chat_id
   # Add other required vars from settings.py
   ```

## 🐳 Docker Deployment (Recommended)

This project is optimized for Docker, using `Xvfb` to run the browser in a headless environment.

1.  **Build the Image**
    ```bash
    docker build -t twitter-bot -f deploy/Dockerfile .
    ```

2.  **Run the Container**
    Mount your session folder (cookies) and your `.env` file:
    ```bash
    docker run -d \
      --name twitter-bot \
      -v $(pwd)/my_playwright_profile_1:/app/my_playwright_profile_1 \
      -v $(pwd)/.env:/app/.env \
      twitter-bot
    ```
    *Note: Ensure `my_playwright_profile_1` was created on a Linux machine (or VM) as per the "Cookie Management" section.*

## 🍪 Cookie Management & Session Extraction

> [!IMPORTANT]
> **CRITICAL: OS Compatibility**
> The browser cookies and session data extracted by Playwright are **OS-specific**.
> - If you run the bot on **Windows**, you must extract cookies on **Windows**.
> - If you run the bot on a **Linux server (e.g., Debian)**, you **MUST** extra cookies onto a **Linux (Debian) machine**.
>
> **Recommended approach for Linux servers**: Use a Virtual Machine (VM) running the same OS (e.g., Debian) to extract the session, then transfer the folder to your server.

### How to Extract Cookies
The bot uses **Persistent Contexts**. This means you don't export a `cookies.json` file manually; instead, you point Playwright to a user data directory where you have already logged in.

1.  **Run the Session Setup Script**:
    Use the provided `setup_session.py` (or a similar script) to launch a non-headless browser.
    ```bash
    python setup_session.py
    ```
2.  **Log In Manually**:
    A Chrome/Chromium window will open. Go to `https://x.com` and log in with your account.
    *Solve any CAPTCHAs or 2FA challenges manually.*
3.  **Close the Browser**:
    Once logged in and you can see the timeline, close the browser window or stop the script.
4.  **Locate the Folder**:
    The script creates a folder named `my_playwright_profile_N` (e.g., `my_playwright_profile_1`).
5.  **Use it in the Bot**:
    Target this folder path when configuring the monitor. The bot will reuse the session (cookies, local storage) to scrape as a logged-in user.

## 📖 Usage

### Start the Bot
To start the Telegram bot and the scheduler:
```bash
python main.py
```

### Telegram Commands
| Command | Description |
| :--- | :--- |
| `/start` | Start the bot and show welcome message |
| `/help` | Show list of available commands |
| `/add_watch <@user>` | Monitor a new Twitter account |
| `/list_watches` | List currently monitored accounts |
| `/status` | Show system status and worker health |
| `/proxy_list` | Manage and view proxy status |

## 📁 Project Structure

```
telegram_bot_project/
├── main.py              # Unified entry point (Orchestrator)
├── requirements.txt     # Python dependencies
├── setup_session.py     # Script to extract cookies/session
│
├── bot/                 # Telegram Bot logic
│   ├── commands/        # Handler functions (/add_watch, etc.)
│   └── main.py          # Bot setup
│
├── core/                # Core utilities
│   ├── auth.py          # Admin authorization
│   └── json_manager.py  # Data storage management
│
├── script/              # Scraping logic
│   ├── scheduler/       # Task scheduling
│   └── scrapers/        # Twitter/X scraper implementation
│       └── twitter.py   # Playwright scraper logic
│
└── config/              # Configuration settings
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1.  **Fork** the repository
2.  **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3.  **Make** your changes
4.  **Test** the changes thoroughly
5.  **Commit** your changes (`git commit -m 'Add amazing feature'`)
6.  **Push** to the branch (`git push origin feature/amazing-feature`)
7.  **Open** a Pull Request

### Development Guidelines

- Follow **PEP 8** coding standards for Python
- Document your code (docstrings)
- Write tests for new features
- Update documentation as needed

## 📝 License

Copyright © 2024. All rights reserved.
Internal usage only.

---
<div align="center">
  <p>Built with ❤️ for financial optimization</p>
</div>
