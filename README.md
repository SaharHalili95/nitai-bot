# NitaiBot

A Telegram bot and web interface that generates professional Hebrew product pages for eCommerce using the Claude API. Given a product name, model number, or SKU, it produces structured marketing content ready to paste into WordPress - styled to the standards of leading Israeli retail chains (Bug, KSP).

## Features

- **Telegram bot** - send any product name or SKU and pick the content section you need via inline buttons
- **Web interface** - browser-based UI backed by a Flask API for the same generation workflow
- **Four content sections**, each generated independently or all at once:
  - Short description (marketing intro + 3 key benefits)
  - Full description (3-5 structured paragraphs, 200+ words)
  - Technical specs (HTML table with dimensions, power, energy rating, etc.)
  - Drawbacks and solutions (2 real cons with practical workarounds)
- **Web search grounding** - uses Claude's web_search tool to pull current, accurate product data before writing
- **WordPress-ready HTML output** - h3, p, ul, table tags; professional Hebrew with English technical terms in parentheses
- **Chunked Telegram delivery** - long responses are split to stay within Telegram's 4096-character message limit

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | python-telegram-bot |
| AI | Anthropic Claude API |
| Web server | Flask + Flask-CORS |
| Production server | Gunicorn |
| Config | python-dotenv |

## Setup

### Prerequisites

- Python 3.10+
- A Telegram bot token (from @BotFather)
- An Anthropic API key

### Install

```bash
git clone https://github.com/SaharHalili95/nitai-bot.git
cd nitai-bot
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Run

**Telegram bot:**
```bash
python bot.py
```

**Web server (development):**
```bash
python server.py
```

**Web server (production):**
```bash
gunicorn server:app
```

## Project Structure

```
nitai-bot/
├── bot.py            # Telegram bot (polling mode)
├── server.py         # Flask API + static file serving
├── gunicorn.conf.py  # Gunicorn config
├── search.html       # Web UI
├── index.html        # Landing page
└── requirements.txt
```

## License

MIT
