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
            
        # CoinDesk RSS
        try:
            feed = feedparser.parse('https://www.coindesk.com/arc/outboundfeeds/rss/')
            for entry in feed.entries[:5]:
                if any(keyword in entry.title.lower() for keyword in ['hack', 'exploit', 'surge', 'crash', 'breakthrough', 'launch', 'adoption']):
                    story = {
                        'title': entry.title,
                        'content': entry.summary[:200] + '...' if len(entry.summary) > 200 else entry.summary,
                        'url': entry.link,
                        'type': 'crypto',
                        'hashtags': self.get_relevant_hashtags(entry.title, 'crypto')
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
        
        # MIT Technology Review AI RSS
        try:
            feed = feedparser.parse('https://www.technologyreview.com/feed/')
            for entry in feed.entries[:5]:
                if any(keyword in entry.title.lower() for keyword in ['ai', 'artificial intelligence', 'machine learning', 'openai', 'chatgpt', 'llm', 'neural', 'robot']):
                    story = {
                        'title': entry.title,
                        'content': entry.summary[:200] + '...' if len(entry.summary) > 200 else entry.summary,
                        'url': entry.link,
                        'type': 'ai',
                        'hashtags': self.get_relevant_hashtags(entry.title, 'ai')
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
                        if story_data.get('title') and any(keyword in story_data['title'].lower() for keyword in ['ai', 'artificial intelligence', 'openai', 'chatgpt', 'llm', 'gpt', 'claude']):
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
            'milestone', 'achievement', 'innovation', 'disruption', 'game-changer'
        ]
        
        filtered_stories = []
        for story in stories:
            story_text = (story['title'] + ' ' + story['content']).lower()
            if any(keyword in story_text for keyword in interesting_keywords):
                filtered_stories.append(story)
                
        return filtered_stories
        
    def format_post(self, story):
        """Format story into a well-structured 2-3 sentence post with hashtags"""
        emoji_map = {
            'crypto': ['🚀', '💰', '⚡', '🌟', '🔥', '💎'],
            'ai': ['🤖', '🧠', '⚡', '🚀', '💡', '🔮']
        }
        
        emoji = random.choice(emoji_map.get(story['type'], ['🔥']))
        
        # Clean and shorten title
        title = story['title'][:100] + '...' if len(story['title']) > 100 else story['title']
        
        # Start building post
        post = f"{emoji} {title}\n\n"
            
        # Add brief context if available
        if story['content'] and len(story['content']) > 10:
            context = story['content'][:80] + '...' if len(story['content']) > 80 else story['content']
            post += f"{context}\n\n"
            
        # Add hashtags for better reach
        hashtags = story.get('hashtags', [])
        if hashtags:
            hashtag_text = ' '.join(hashtags)
            post += f"{hashtag_text}\n\n"
            
        # Add link
        post += f"🔗 {story['url']}"
        
        # Ensure post is under 280 characters
        if len(post) > 280:
            # Remove hashtags if too long
            post = f"{emoji} {title}\n\n{story['content'][:60]}...\n\n🔗 {story['url']}"
            if len(post) > 280:
                post = post[:276] + '...'
            
        return post
        
    def engage_with_community(self):
        """Engage with community posts to grow followers"""
        try:
            # Search for recent tweets about crypto/AI
            search_queries = ['#Bitcoin', '#Ethereum', '#AI', '#ChatGPT', '#DeFi']
            query = random.choice(search_queries)
            
            # Get recent tweets
            tweets = self.client.search_recent_tweets(
                query=f"{query} -is:retweet",
                max_results=10,
                tweet_fields=['public_metrics', 'author_id']
            )
            
            if tweets.data:
                # Like and retweet high-engagement posts
                for tweet in tweets.data[:2]:  # Limit to 2 interactions per cycle
                    if tweet.public_metrics['like_count'] > 50:  # Only engage with popular tweets
                        try:
                            self.client.like(tweet.id)
                            time.sleep(2)  # Rate limiting
                            if tweet.public_metrics['retweet_count'] > 20:
                                self.client.retweet(tweet.id)
                            logger.info(f"Engaged with tweet: {tweet.id}")
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
            
        # Select best story
        best_story = random.choice(new_stories)
        
        # Format and post
        formatted_post = self.format_post(best_story)
        
        if self.post_to_twitter(formatted_post):
            self.posted_stories.add(best_story['url'])
            self.save_posted_stories()
            logger.info(f"Posted story: {best_story['title']}")
            
            # Engage with community after posting
            time.sleep(30)  # Wait before engaging
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