# X (Twitter) News Bot

Automated news posting bot for crypto and AI news. Posts 3 times daily with well-formatted, interesting content.

## Features

- 🚀 Posts 3x daily (8 AM, 2 PM, 8 PM)
- 🔥 Focuses on crypto and AI news only
- 💎 Filters for "cool and interesting" content
- 📝 Well-structured 2-3 sentence posts
- 🔄 Avoids duplicate posts
- 📊 Multiple news sources (CoinGecko, CoinDesk, MIT Tech Review, Hacker News)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
TWITTER_API_KEY=your_key_here
TWITTER_API_SECRET=your_secret_here
TWITTER_ACCESS_TOKEN=your_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_token_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

3. Run the bot:
```bash
python main.py
```

## Free 24/7 Hosting Options

1. **Railway**: Upload to GitHub, connect to Railway
2. **Render**: Deploy as background service
3. **Heroku**: Use scheduler add-on
4. **GitHub Actions**: Use cron workflows

## News Sources

- **Crypto**: CoinGecko trending, CoinDesk RSS
- **AI**: MIT Technology Review, Hacker News AI stories

## Post Format

Example post:
```
🚀 Bitcoin hits new all-time high of $67,000

Market surges following institutional adoption news.

🔗 https://example.com/news
```