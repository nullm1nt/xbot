import tweepy
import requests
import time
import os
import json
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import random
import re
from urllib.parse import urlparse

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self):
        self.setup_twitter_client()
        self.posted_stories = set()
        self.load_posted_stories()
        self.last_post_time = None
        
    def setup_twitter_client(self):
        """Initialize Twitter API client"""
        try:
            self.client = tweepy.Client(
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                wait_on_rate_limit=True
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            
    def load_posted_stories(self):
        """Load previously posted stories to avoid duplicates"""
        try:
            # Use environment variable for GitHub Actions
            posted_urls = os.getenv('POSTED_STORIES', '')
            if posted_urls:
                self.posted_stories = set(posted_urls.split(','))
            else:
                with open('posted_stories.json', 'r') as f:
                    self.posted_stories = set(json.load(f))
        except FileNotFoundError:
            self.posted_stories = set()
            
    def save_posted_stories(self):
        """Save posted stories to file (local only)"""
        try:
            with open('posted_stories.json', 'w') as f:
                json.dump(list(self.posted_stories), f)
        except:
            pass  # Ignore errors in GitHub Actions
            
    def get_news_apis(self):
        """Get additional news sources"""
        return {
            'newsapi': f'https://newsapi.org/v2/everything?q=bitcoin OR ethereum OR cryptocurrency&sortBy=publishedAt&pageSize=10&apiKey={os.getenv("NEWS_API_KEY", "")}',
            'cryptonews': 'https://cryptonews-api.com/api/v1/category?section=general&items=10&page=1&token=' + os.getenv('CRYPTONEWS_API_KEY', ''),
            'alphavantage': f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=CRYPTO:BTC,CRYPTO:ETH&apikey={os.getenv("ALPHA_VANTAGE_KEY", "")}'
        }
        
    def get_crypto_news(self):
        """Fetch crypto news from multiple sources"""
        stories = []
        
        # CoinGecko trending
        try:
            response = requests.get('https://api.coingecko.com/api/v3/search/trending', timeout=10)
            if response.status_code == 200:
                trending = response.json()['coins'][:3]
                for coin in trending:
                    story = {
                        'title': f"{coin['item']['name']} ({coin['item']['symbol']}) trending on CoinGecko",
                        'content': f"Market cap rank: #{coin['item']['market_cap_rank']}",
                        'url': f"https://www.coingecko.com/en/coins/{coin['item']['id']}",
                        'type': 'crypto',
                        'source': 'CoinGecko'
                    }
                    stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching CoinGecko trending: {e}")
            
        # CoinDesk RSS - last 24 hours
        try:
            feed = feedparser.parse('https://www.coindesk.com/arc/outboundfeeds/rss/')
            current_time = datetime.now()
            for entry in feed.entries[:20]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'crypto',
                    'source': 'CoinDesk',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching CoinDesk RSS: {e}")
            
        # Cointelegraph RSS
        try:
            feed = feedparser.parse('https://cointelegraph.com/rss')
            current_time = datetime.now()
            for entry in feed.entries[:15]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'crypto',
                    'source': 'Cointelegraph',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching Cointelegraph RSS: {e}")
            
        # CryptoSlate RSS
        try:
            feed = feedparser.parse('https://cryptoslate.com/feed/')
            current_time = datetime.now()
            for entry in feed.entries[:10]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'crypto',
                    'source': 'CryptoSlate',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching CryptoSlate RSS: {e}")
            
        return stories
        
    def summarize_news(self, story):
        """Create a WatcherGuru-style summary"""
        title = story['title']
        content = story.get('content', '')
        
        # Clean title
        title = re.sub(r'[^\w\s$%:.-]', '', title)
        title = title.replace('\n', ' ').strip()
        
        # Extract key info
        breaking_keywords = ['breaking', 'urgent', 'alert', 'just in', 'developing']
        price_keywords = ['surge', 'pump', 'crash', 'rally', 'spike', 'soar', 'dive', 'plunge']
        
        # Format based on content
        if any(keyword in title.lower() for keyword in breaking_keywords):
            prefix = 'BREAKING: '
        elif any(keyword in title.lower() for keyword in price_keywords):
            prefix = 'JUST IN: '
        else:
            prefix = ''
            
        # Create summary without price extraction to avoid confusion
        summary = f"{prefix}{title}"
        
        # Ensure under 280 characters
        if len(summary) > 280:
            summary = summary[:277] + '...'
            
        return summary
        
    def get_ai_news(self):
        """Fetch AI news from multiple sources"""
        stories = []
        
        # VentureBeat AI RSS
        try:
            feed = feedparser.parse('https://venturebeat.com/category/ai/feed/')
            current_time = datetime.now()
            for entry in feed.entries[:10]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'ai',
                    'source': 'VentureBeat',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching VentureBeat AI: {e}")
            
        # TechCrunch AI RSS
        try:
            feed = feedparser.parse('https://techcrunch.com/category/artificial-intelligence/feed/')
            current_time = datetime.now()
            for entry in feed.entries[:10]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'ai',
                    'source': 'TechCrunch',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching TechCrunch AI: {e}")
            
        # AI News RSS
        try:
            feed = feedparser.parse('https://www.artificialintelligence-news.com/feed/')
            current_time = datetime.now()
            for entry in feed.entries[:10]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue
                        
                story = {
                    'title': entry.title,
                    'content': entry.summary[:300] if hasattr(entry, 'summary') else '',
                    'url': entry.link,
                    'type': 'ai',
                    'source': 'AI News',
                    'published': article_time,
                    'hours_old': hours_old
                }
                stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching AI News: {e}")
            
        return stories
        
    def filter_interesting_stories(self, stories):
        """Filter stories for important/breaking news"""
        high_priority_keywords = [
            'breaking', 'urgent', 'alert', 'just in', 'developing',
            'hack', 'exploit', 'vulnerability', 'breach', 'attack',
            'surge', 'crash', 'skyrocket', 'plunge', 'rally', 'spike',
            'record', 'all-time', 'new high', 'new low', 'milestone',
            'launch', 'release', 'unveil', 'announce', 'partnership',
            'acquisition', 'merger', 'ipo', 'funding', 'investment',
            'billion', 'million', 'massive', 'huge', 'major',
            'breakthrough', 'revolutionary', 'first ever', 'innovation',
            'approval', 'regulation', 'ban', 'legal', 'court',
            'dormant', 'whale', 'transfer', 'moved', 'activated'
        ]
        
        exclude_keywords = [
            'road', 'travel', 'transportation', 'geography', 'highway',
            'recipe', 'cooking', 'food', 'restaurant', 'weather',
            'sports', 'entertainment', 'celebrity', 'movie', 'music'
        ]
        
        filtered_stories = []
        for story in stories:
            story_text = (story['title'] + ' ' + story.get('content', '')).lower()
            
            # Skip excluded content
            if any(keyword in story_text for keyword in exclude_keywords):
                continue
                
            # Include high priority or recent stories
            if (any(keyword in story_text for keyword in high_priority_keywords) or 
                story.get('hours_old', 999) < 6):
                filtered_stories.append(story)
                
        return filtered_stories
        
    def format_post(self, story):
        """Format story into WatcherGuru-style simple post"""
        # Use the summarize_news method for clean formatting
        return self.summarize_news(story)
        
    def check_rate_limit(self):
        """Check if enough time has passed since last post"""
        if self.last_post_time is None:
            return True
        
        # Minimum 2 hours between posts
        time_diff = time.time() - self.last_post_time
        return time_diff >= 7200  # 2 hours
        
    def should_post_now(self):
        """Check if we should post based on time and rate limiting"""
        current_hour = datetime.now().hour
        
        # Post during active hours (6 AM - 11 PM)
        if current_hour < 6 or current_hour > 23:
            return False
            
        # Check rate limit
        return self.check_rate_limit()
        
    def post_to_twitter(self, content):
        """Post content to Twitter"""
        try:
            response = self.client.create_tweet(text=content)
            logger.info(f"Successfully posted tweet: {response.data['id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return False
            
    def run_posting_cycle(self):
        """Main posting cycle - finds and posts interesting news"""
        logger.info("Starting posting cycle...")
        
        # Check if we should post now
        if not self.should_post_now():
            logger.info("Not posting due to rate limiting or time restrictions")
            return
        
        # Get news from both sources
        crypto_stories = self.get_crypto_news()
        ai_stories = self.get_ai_news()
        
        all_stories = crypto_stories + ai_stories
        logger.info(f"Found {len(all_stories)} total stories")
        
        # Filter for interesting content
        interesting_stories = self.filter_interesting_stories(all_stories)
        logger.info(f"Found {len(interesting_stories)} interesting stories")
        
        # Remove already posted stories
        new_stories = [story for story in interesting_stories if story['url'] not in self.posted_stories]
        logger.info(f"Found {len(new_stories)} new stories")
        
        if not new_stories:
            logger.info("No new interesting stories found")
            return
            
        # Sort by priority: breaking news first, then by freshness
        def story_priority(story):
            title_lower = story['title'].lower()
            breaking_score = 0
            
            if any(word in title_lower for word in ['breaking', 'urgent', 'alert']):
                breaking_score += 1000
            if any(word in title_lower for word in ['hack', 'exploit', 'breach']):
                breaking_score += 800
            if any(word in title_lower for word in ['surge', 'crash', 'spike']):
                breaking_score += 600
            if any(word in title_lower for word in ['record', 'all-time', 'milestone']):
                breaking_score += 400
                
            # Subtract hours old (fresher = higher priority)
            hours_old = story.get('hours_old', 24)
            freshness_score = max(0, 24 - hours_old)
            
            return breaking_score + freshness_score
        
        # Sort stories by priority
        new_stories.sort(key=story_priority, reverse=True)
        best_story = new_stories[0]
        
        # Format and post
        formatted_post = self.format_post(best_story)
        logger.info(f"Attempting to post: {formatted_post[:50]}...")
        
        if self.post_to_twitter(formatted_post):
            self.posted_stories.add(best_story['url'])
            self.save_posted_stories()
            self.last_post_time = time.time()
            logger.info(f"Successfully posted: {best_story['title']}")
        else:
            logger.error("Failed to post story")
            
    def start_continuous_posting(self):
        """Start continuous posting with intelligent timing"""
        logger.info("Starting continuous news posting...")
        
        while True:
            try:
                self.run_posting_cycle()
                # Wait 2-4 hours before next check
                wait_time = random.randint(7200, 14400)  # 2-4 hours
                logger.info(f"Waiting {wait_time/3600:.1f} hours before next cycle")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error in posting cycle: {e}")
                time.sleep(1800)  # Wait 30 minutes on error

if __name__ == "__main__":
    bot = NewsBot()
    
    # Check if running in GitHub Actions (single run)
    if os.getenv('GITHUB_ACTIONS'):
        logger.info("Running in GitHub Actions mode - single post")
        bot.run_posting_cycle()
    else:
        logger.info("Running in continuous mode")
        bot.start_continuous_posting()