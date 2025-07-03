import tweepy
import requests
import schedule
import time
import os
import json
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import random

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self):
        self.setup_twitter_client()
        self.posted_stories = set()
        self.load_posted_stories()
        
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
            with open('posted_stories.json', 'r') as f:
                self.posted_stories = set(json.load(f))
        except FileNotFoundError:
            self.posted_stories = set()
            
    def save_posted_stories(self):
        """Save posted stories to file"""
        with open('posted_stories.json', 'w') as f:
            json.dump(list(self.posted_stories), f)
            
    def get_trending_hashtags(self):
        """Get trending crypto/AI hashtags"""
        crypto_hashtags = ['#Bitcoin', '#Ethereum', '#Crypto', '#DeFi', '#NFT', '#Web3', '#Blockchain', '#BTC', '#ETH']
        ai_hashtags = ['#AI', '#MachineLearning', '#ChatGPT', '#OpenAI', '#TechNews', '#Innovation', '#Future', '#ML', '#DeepLearning']
        return crypto_hashtags + ai_hashtags
        
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
                        'title': f"🚀 {coin['item']['name']} ({coin['item']['symbol']}) is trending #1 on CoinGecko",
                        'content': f"Market cap rank: #{coin['item']['market_cap_rank']}",
                        'url': f"https://www.coingecko.com/en/coins/{coin['item']['id']}",
                        'type': 'crypto',
                        'hashtags': ['#Crypto', f"#{coin['item']['symbol']}", '#Trending']
                    }
                    stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching CoinGecko trending: {e}")
            
        # CoinDesk RSS - only last 6 hours for ultra-fresh crypto news
        try:
            feed = feedparser.parse('https://www.coindesk.com/arc/outboundfeeds/rss/')
            current_time = datetime.now()
            for entry in feed.entries[:15]:  # Check more entries for recent content
                # Check if article is from last 6 hours (ultra-fresh for crypto)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    if hours_old > 6:  # Skip if older than 6 hours
                        continue
                        
                if any(keyword in entry.title.lower() for keyword in ['hack', 'exploit', 'surge', 'crash', 'breakthrough', 'launch', 'adoption', 'pump', 'rally', 'spike', 'soar']):
                    story = {
                        'title': entry.title,
                        'content': entry.summary[:200] + '...' if len(entry.summary) > 200 else entry.summary,
                        'url': entry.link,
                        'type': 'crypto',
                        'hashtags': self.get_relevant_hashtags(entry.title, 'crypto'),
                        'published': article_time if hasattr(entry, 'published_parsed') else current_time,
                        'hours_old': hours_old if hasattr(entry, 'published_parsed') else 0
                    }
                    stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching CoinDesk RSS: {e}")
            
        return stories
        
    def get_relevant_hashtags(self, title, story_type):
        """Get relevant hashtags based on story content"""
        hashtags = []
        
        if story_type == 'crypto':
            if 'bitcoin' in title.lower() or 'btc' in title.lower():
                hashtags.extend(['#Bitcoin', '#BTC'])
            if 'ethereum' in title.lower() or 'eth' in title.lower():
                hashtags.extend(['#Ethereum', '#ETH'])
            if any(word in title.lower() for word in ['hack', 'exploit', 'security']):
                hashtags.append('#CyberSecurity')
            if any(word in title.lower() for word in ['defi', 'yield', 'liquidity']):
                hashtags.append('#DeFi')
            if any(word in title.lower() for word in ['nft', 'collectible', 'art']):
                hashtags.append('#NFT')
            hashtags.append('#Crypto')
        else:  # AI
            if 'chatgpt' in title.lower() or 'gpt' in title.lower():
                hashtags.extend(['#ChatGPT', '#OpenAI'])
            if 'claude' in title.lower():
                hashtags.append('#Claude')
            if 'machine learning' in title.lower() or 'ml' in title.lower():
                hashtags.append('#MachineLearning')
            if 'neural' in title.lower():
                hashtags.append('#DeepLearning')
            hashtags.append('#AI')
            
        return hashtags[:3]  # Limit to 3 hashtags
        
    def get_ai_news(self):
        """Fetch AI news from multiple sources"""
        stories = []
        
        # MIT Technology Review AI RSS - last 3 days (more flexibility for AI news)
        try:
            feed = feedparser.parse('https://www.technologyreview.com/feed/')
            current_time = datetime.now()
            for entry in feed.entries[:8]:  # Check AI entries
                # Check if article is from last 3 days (more flexible for AI)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_time = datetime(*entry.published_parsed[:6])
                    days_old = (current_time - article_time).days
                    if days_old > 3:  # Skip if older than 3 days
                        continue
                        
                if any(keyword in entry.title.lower() for keyword in ['ai breakthrough', 'artificial intelligence', 'machine learning', 'openai', 'chatgpt', 'gpt-4', 'claude', 'neural network', 'deep learning']):
                    story = {
                        'title': entry.title,
                        'content': entry.summary[:200] + '...' if len(entry.summary) > 200 else entry.summary,
                        'url': entry.link,
                        'type': 'ai',
                        'hashtags': self.get_relevant_hashtags(entry.title, 'ai'),
                        'published': article_time if hasattr(entry, 'published_parsed') else current_time,
                        'days_old': days_old if hasattr(entry, 'published_parsed') else 0
                    }
                    stories.append(story)
        except Exception as e:
            logger.error(f"Error fetching MIT Tech Review: {e}")
            
        # Hacker News AI stories
        try:
            response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10)
            if response.status_code == 200:
                top_stories = response.json()[:20]
                for story_id in top_stories:
                    story_response = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json', timeout=5)
                    if story_response.status_code == 200:
                        story_data = story_response.json()
                        if story_data.get('title') and any(keyword in story_data['title'].lower() for keyword in ['openai', 'chatgpt', 'llm', 'gpt-4', 'gpt-3', 'claude', 'artificial intelligence breakthrough', 'ai model', 'machine learning breakthrough']):
                            story = {
                                'title': story_data['title'],
                                'content': f"Discussion on Hacker News with {story_data.get('score', 0)} points",
                                'url': story_data.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                                'type': 'ai',
                                'hashtags': self.get_relevant_hashtags(story_data['title'], 'ai')
                            }
                            stories.append(story)
                            if len(stories) >= 3:
                                break
        except Exception as e:
            logger.error(f"Error fetching Hacker News: {e}")
            
        return stories
        
    def filter_interesting_stories(self, stories):
        """Filter stories for 'cool and interesting' content"""
        interesting_keywords = [
            'breakthrough', 'revolutionary', 'first ever', 'record', 'massive', 'huge',
            'hack', 'exploit', 'vulnerability', 'surge', 'crash', 'skyrocket',
            'launch', 'release', 'unveil', 'announce', 'partnership', 'acquisition',
            'milestone', 'achievement', 'innovation', 'disruption', 'game-changer',
            'billion', 'million', 'new high', 'all-time', 'major', 'funding'
        ]
        
        # Exclude irrelevant content
        exclude_keywords = [
            'road', 'travel', 'transportation', 'geography', 'taiga', 'highway',
            'recipe', 'cooking', 'food', 'restaurant', 'weather', 'climate'
        ]
        
        filtered_stories = []
        for story in stories:
            story_text = (story['title'] + ' ' + story['content']).lower()
            
            # Skip if contains excluded keywords
            if any(keyword in story_text for keyword in exclude_keywords):
                continue
                
            # Only include if contains interesting keywords
            if any(keyword in story_text for keyword in interesting_keywords):
                filtered_stories.append(story)
                
        return filtered_stories
        
    def format_post(self, story):
        """Format story into a professional, engaging post"""
        
        # Enhanced emoji mapping with variety
        emoji_map = {
            'crypto': {
                'surge': '🚀', 'pump': '📈', 'rally': '💹', 'spike': '⚡',
                'hack': '🚨', 'exploit': '⚠️', 'launch': '🌟', 'adoption': '💎',
                'breakthrough': '🔥', 'default': '💰'
            },
            'ai': {
                'breakthrough': '🔬', 'launch': '🚀', 'model': '🧠', 'chatgpt': '💬',
                'openai': '💡', 'claude': '🤖', 'innovation': '⚡', 'default': '🤖'
            }
        }
        
        # Smart emoji selection based on content
        story_lower = (story['title'] + ' ' + story.get('content', '')).lower()
        story_type = story['type']
        emoji = emoji_map[story_type]['default']
        
        for keyword, emoji_choice in emoji_map[story_type].items():
            if keyword in story_lower:
                emoji = emoji_choice
                break
        
        # Clean and format title
        title = story['title'].strip()
        if title.startswith(('🚀', '💰', '🤖', '🧠', '⚡', '🌟', '🔥', '💎')):
            title = title[2:].strip()  # Remove existing emoji
        
        # Build professional post structure
        if story['type'] == 'crypto':
            # Crypto posts - emphasize market action
            post = f"{emoji} {title}\n\n"
        else:
            # AI posts - emphasize innovation
            post = f"{emoji} {title}\n\n"
        
        # Add compelling context with better formatting
        if story.get('content') and len(story['content']) > 15:
            context = story['content'].strip()
            # Clean up common RSS artifacts
            context = context.replace('...', '').replace('[...]', '').strip()
            if len(context) > 85:
                context = context[:82] + '...'
            post += f"→ {context}\n\n"
        
        # Add strategic hashtags (max 3 for readability)
        hashtags = story.get('hashtags', [])[:3]  # Limit to 3
        if hashtags:
            post += f"{' '.join(hashtags)}\n\n"
        
        # Clean link formatting with actual URL
        source_name = self.get_source_name(story['url'])
        post += f"🔗 {source_name}: {story['url']}"
        
        # Ensure under 280 characters with fallback
        if len(post) > 280:
            # Shorter version if too long
            short_context = story.get('content', '')[:45] + '...' if story.get('content') else ''
            post = f"{emoji} {title}\n\n"
            if short_context:
                post += f"→ {short_context}\n\n"
            post += f"{' '.join(hashtags[:2])}\n\n🔗 {story['url']}"
            
            if len(post) > 280:
                post = f"{emoji} {title}\n\n{' '.join(hashtags[:2])}\n\n🔗 {story['url']}"
        
        return post
        
    def get_source_name(self, url):
        """Extract clean source name from URL"""
        if 'coindesk.com' in url:
            return 'CoinDesk'
        elif 'coingecko.com' in url:
            return 'CoinGecko'
        elif 'technologyreview.com' in url:
            return 'MIT Tech Review'
        elif 'news.ycombinator.com' in url:
            return 'Hacker News'
        else:
            # Extract domain name
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace('www.', '').title()
            except:
                return 'Source'
        
    def engage_with_community(self):
        """Light engagement to grow followers (within free tier limits)"""
        try:
            # Search for recent tweets about crypto/AI
            search_queries = ['#Bitcoin', '#Ethereum', '#AI', '#ChatGPT', '#DeFi']
            query = random.choice(search_queries)
            
            # Get recent tweets
            tweets = self.client.search_recent_tweets(
                query=f"{query} -is:retweet",
                max_results=5,  # Reduced from 10
                tweet_fields=['public_metrics', 'author_id']
            )
            
            if tweets.data:
                # Light engagement - only 1 interaction per cycle
                for tweet in tweets.data[:1]:  # Only 1 interaction per cycle (was 2)
                    if tweet.public_metrics['like_count'] > 100:  # Higher threshold for quality
                        try:
                            self.client.like(tweet.id)
                            logger.info(f"Liked high-quality tweet: {tweet.id}")
                            break  # Only one action per cycle
                        except Exception as e:
                            logger.error(f"Failed to engage with tweet: {e}")
                            
        except Exception as e:
            logger.error(f"Error in community engagement: {e}")
        
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
        
        # Get news from both sources
        crypto_stories = self.get_crypto_news()
        ai_stories = self.get_ai_news()
        
        all_stories = crypto_stories + ai_stories
        
        # Filter for interesting content
        interesting_stories = self.filter_interesting_stories(all_stories)
        
        # Remove already posted stories
        new_stories = [story for story in interesting_stories if story['url'] not in self.posted_stories]
        
        if not new_stories:
            logger.info("No new interesting stories found")
            # Still engage with community even if no new stories
            self.engage_with_community()
            return
            
        # Prioritize crypto stories by freshness, AI stories by quality
        crypto_stories = [s for s in new_stories if s['type'] == 'crypto']
        ai_stories = [s for s in new_stories if s['type'] == 'ai']
        
        if crypto_stories:
            # For crypto, prioritize by freshness (sort by hours_old if available)
            crypto_stories.sort(key=lambda x: x.get('hours_old', 999))
            best_story = crypto_stories[0]  # Most recent crypto story
        elif ai_stories:
            # For AI, just pick randomly from available stories
            best_story = random.choice(ai_stories)
        else:
            best_story = random.choice(new_stories)
        
        # Format and post
        formatted_post = self.format_post(best_story)
        
        if self.post_to_twitter(formatted_post):
            self.posted_stories.add(best_story['url'])
            self.save_posted_stories()
            logger.info(f"Posted story: {best_story['title']}")
            
            # Engage with community after posting
            time.sleep(5)  # Quick wait before engaging (reduced from 30 seconds)
            self.engage_with_community()
        else:
            logger.error("Failed to post story")
            
    def start_scheduler(self):
        """Start the scheduled posting"""
        logger.info("Starting news bot scheduler...")
        
        # Schedule posts 3 times daily
        schedule.every().day.at("08:00").do(self.run_posting_cycle)
        schedule.every().day.at("14:00").do(self.run_posting_cycle)  # 2 PM
        schedule.every().day.at("20:00").do(self.run_posting_cycle)  # 8 PM
        
        logger.info("Scheduler started. Posts will be made at 8 AM, 2 PM, and 8 PM daily.")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    bot = NewsBot()
    
    # Test run first
    logger.info("Running test post...")
    bot.run_posting_cycle()
    
    # Start scheduler
    bot.start_scheduler()