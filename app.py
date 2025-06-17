

# Enhanced Elm Dirt Content Automation Platform - Part 1: Beginning
# Imports, Configuration, and Core Classes

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import calendar
import os
from typing import Dict, List, Optional, Tuple
import re
import logging
import sqlite3
from dataclasses import dataclass
from enum import Enum
import uuid
import random
from export_routes import export_bp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.register_blueprint(export_bp)

# Configuration
class Config:
    # Claude API (Primary) - Add your Claude API key here
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your_claude_api_key_here')
    CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'
    
    # Shopify API
    SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY', 'your_shopify_api_key')
    SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD', 'your_shopify_password')
    SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL', 'elmdirt.myshopify.com')
    SHOPIFY_BLOG_ID = os.getenv('SHOPIFY_BLOG_ID', 'your_blog_id')
    
    # Metricool API
    METRICOOL_API_KEY = os.getenv('METRICOOL_API_KEY', 'your_metricool_api_key')
    
    # Database
    DB_PATH = os.getenv('DB_PATH', 'content_automation.db')
    
    # SEO and Content Settings - Elm Dirt focused keywords
    TARGET_KEYWORDS = [
        "organic fertilizer", "plant food", "worm castings", "ancient soil", 
        "bloom juice", "plant juice", "organic gardening", "sustainable farming", 
        "microbe rich soil", "living soil", "composting", "garden nutrients",
        "elm dirt", "organic plant care", "natural fertilizer"
    ]
    
    # US Gardening Holidays and Special Dates
    GARDENING_HOLIDAYS = {
        (2, 14): ('Valentine\'s Day', 'flowering plants and love for gardening', 'Show Your Garden Some Love'),
        (3, 17): ('St. Patrick\'s Day', 'green plants and Irish garden traditions', 'Going Green in the Garden'),
        (3, 20): ('Spring Equinox', 'spring awakening and soil preparation', 'Spring Awakening'),
        (4, 22): ('Earth Day', 'sustainable gardening and environmental stewardship', 'Sustainable Gardening'),
        (5, 1): ('May Day', 'spring planting and garden celebrations', 'May Day Garden Celebration'),
        (5, 8): ('Mother\'s Day Week', 'garden gifts and family gardening', 'Mother\'s Day Garden Gifts'),
        (5, 30): ('Memorial Day', 'summer garden prep and remembrance gardens', 'Memorial Day Garden Prep'),
        (6, 21): ('Summer Solstice', 'peak growing season and plant care', 'Peak Summer Growing'),
        (7, 4): ('Independence Day', 'summer garden maintenance and patriotic plants', 'July 4th Garden Display'),
        (8, 15): ('National Relaxation Day', 'peaceful garden spaces', 'Creating Garden Sanctuary'),
        (9, 22): ('Fall Equinox', 'harvest time and winter preparation', 'Fall Harvest Celebration'),
        (10, 31): ('Halloween', 'fall garden cleanup and decorative plants', 'Halloween Garden Magic'),
        (11, 11): ('Veterans Day', 'remembrance gardens and hardy plants', 'Honoring Through Gardens'),
        (11, 24): ('Thanksgiving Week', 'gratitude for harvest and garden reflection', 'Thanksgiving Garden Gratitude'),
        (12, 21): ('Winter Solstice', 'garden planning and indoor plant care', 'Winter Garden Dreams')
    }

class ContentStatus(Enum):
    DRAFT = "draft"
    PREVIEW = "preview"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

@dataclass
class ContentPiece:
    id: str
    title: str
    content: str
    platform: str
    content_type: str
    status: ContentStatus
    scheduled_time: Optional[datetime]
    keywords: List[str]
    hashtags: List[str]
    image_suggestion: str
    ai_provider: str
    created_at: datetime
    updated_at: datetime
    week_id: Optional[str] = None
    holiday_context: Optional[str] = None
    meta_description: Optional[str] = None

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_pieces (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                platform TEXT NOT NULL,
                content_type TEXT NOT NULL,
                status TEXT NOT NULL,
                scheduled_time TIMESTAMP,
                keywords TEXT,
                hashtags TEXT,
                image_suggestion TEXT,
                ai_provider TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                week_id TEXT,
                holiday_context TEXT,
                meta_description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_packages (
                id TEXT PRIMARY KEY,
                week_start_date DATE NOT NULL,
                week_end_date DATE NOT NULL,
                season TEXT,
                holidays TEXT,
                theme TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_content_piece(self, content: ContentPiece) -> bool:
        """Save content piece to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO content_pieces 
                (id, title, content, platform, content_type, status, scheduled_time, 
                 keywords, hashtags, image_suggestion, ai_provider, created_at, 
                 updated_at, week_id, holiday_context, meta_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content.id, content.title, content.content, content.platform,
                content.content_type, content.status.value, 
                content.scheduled_time.isoformat() if content.scheduled_time else None,
                json.dumps(content.keywords), json.dumps(content.hashtags),
                content.image_suggestion, content.ai_provider, 
                content.created_at.isoformat(), content.updated_at.isoformat(),
                content.week_id, content.holiday_context, content.meta_description
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving content piece: {str(e)}")
            return False
    
    def get_content_piece(self, content_id: str) -> Optional[ContentPiece]:
        """Retrieve content piece by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM content_pieces WHERE id = ?', (content_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_content_piece(row)
            return None
        except Exception as e:
            logger.error(f"Error retrieving content piece: {str(e)}")
            return None
    
    def get_weekly_content(self, week_id: str) -> List[ContentPiece]:
        """Get all content for a specific week"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM content_pieces WHERE week_id = ? ORDER BY scheduled_time', (week_id,))
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_content_piece(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving weekly content: {str(e)}")
            return []
    
    def _row_to_content_piece(self, row) -> ContentPiece:
        """Convert database row to ContentPiece object"""
        return ContentPiece(
            id=row[0],
            title=row[1],
            content=row[2],
            platform=row[3],
            content_type=row[4],
            status=ContentStatus(row[5]),
            scheduled_time=datetime.fromisoformat(row[6]) if row[6] else None,
            keywords=json.loads(row[7]) if row[7] else [],
            hashtags=json.loads(row[8]) if row[8] else [],
            image_suggestion=row[9] or "",
            ai_provider=row[10] or "fallback",
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            week_id=row[13],
            holiday_context=row[14],
            meta_description=row[15] if len(row) > 15 else None
        )

class ClaudeAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = Config.CLAUDE_API_URL
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        }
    
    def generate_content(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate content using Claude API"""
        try:
            payload = {
                'model': 'claude-3-sonnet-latest',
                'max_tokens': max_tokens,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return None

class HolidayManager:
    def __init__(self):
        self.config = Config()
    
    def get_week_holidays(self, start_date: datetime) -> List[Tuple[datetime, str, str, str]]:
        """Get holidays and special gardening dates for a specific week"""
        holidays = []
        week_end = start_date + timedelta(days=6)
        
        current_date = start_date
        while current_date <= week_end:
            month_day = (current_date.month, current_date.day)
            if month_day in self.config.GARDENING_HOLIDAYS:
                holiday_name, gardening_focus, content_theme = self.config.GARDENING_HOLIDAYS[month_day]
                holidays.append((current_date, holiday_name, gardening_focus, content_theme))
            
            current_date += timedelta(days=1)
        
        return holidays
    
    def get_seasonal_focus(self, date: datetime) -> str:
        """Determine seasonal focus based on date"""
        month = date.month
        if month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        elif month in [9, 10, 11]:
            return 'fall'
        else:
            return 'winter'
    
    def get_week_theme(self, start_date: datetime) -> str:
        """Generate a theme for the week based on season and holidays"""
        season = self.get_seasonal_focus(start_date)
        holidays = self.get_week_holidays(start_date)
        
        if holidays:
            primary_holiday = holidays[0]
            return primary_holiday[3]
        else:
            seasonal_themes = {
                'spring': [
                    'Spring Garden Awakening',
                    'Soil Preparation and Testing',
                    'Early Planting Success',
                    'Spring Growth Boost'
                ],
                'summer': [
                    'Summer Care Essentials',
                    'Heat and Drought Protection',
                    'Peak Growing Season',
                    'Summer Harvest Time'
                ],
                'fall': [
                    'Fall Harvest Celebration',
                    'Winter Garden Preparation',
                    'Soil Building for Next Year',
                    'Garden Reflection and Planning'
                ],
                'winter': [
                    'Indoor Growing Success',
                    'Garden Planning and Dreams',
                    'Tool Care and Maintenance',
                    'Preparing for Spring'
                ]
            }
            
            week_of_year = start_date.isocalendar()[1]
            theme_index = (week_of_year % 4)
            return seasonal_themes[season][theme_index]

# Initialize core services
db_manager = DatabaseManager(Config.DB_PATH)

# This concludes Part 1 - Beginning
# Continue to Part 2 for ContentGenerator class and content generation methods
# Enhanced Elm Dirt Content Automation Platform - Part 2: Middle
# ContentGenerator Class and Content Creation Methods

class ContentGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.config = Config()
        self.db_manager = db_manager
        self.holiday_manager = HolidayManager()
        
        # Initialize Claude API client
        if self.config.CLAUDE_API_KEY and self.config.CLAUDE_API_KEY != 'your_claude_api_key_here':
            self.claude_client = ClaudeAPIClient(self.config.CLAUDE_API_KEY)
            logger.info("Claude API client initialized successfully")
        else:
            self.claude_client = None
            logger.info("Running in fallback mode - Claude API key not provided")
    
    def generate_weekly_content(self, week_start_date: datetime) -> Dict:
        """Generate a complete week of content including daily blog posts"""
        try:
            week_id = f"week_{week_start_date.strftime('%Y_%m_%d')}"
            season = self.holiday_manager.get_seasonal_focus(week_start_date)
            holidays = self.holiday_manager.get_week_holidays(week_start_date)
            theme = self.holiday_manager.get_week_theme(week_start_date)
            
            logger.info(f"Generating weekly content for {week_start_date.strftime('%Y-%m-%d')} with theme: {theme}")
            
            weekly_content = []
            
            # Generate 1 YouTube video outline for the week
            youtube_outline = self._generate_youtube_outline(
                week_start_date=week_start_date,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=week_id
            )
            weekly_content.append(youtube_outline)
            
            # Generate daily content for 6 days (Monday-Saturday)
            for day_offset in range(6):  # 0=Monday, 1=Tuesday, ..., 5=Saturday
                current_date = week_start_date + timedelta(days=day_offset)
                day_name = current_date.strftime('%A')
                
                # Generate 1 blog post per day
                daily_blog = self._generate_daily_blog_post(
                    date=current_date,
                    day_name=day_name,
                    season=season,
                    theme=theme,
                    holidays=holidays,
                    week_id=week_id
                )
                weekly_content.append(daily_blog)
                
                # Generate daily content package
                daily_content = self._generate_daily_content_package(
                    date=current_date,
                    day_name=day_name,
                    season=season,
                    theme=theme,
                    holidays=holidays,
                    week_id=week_id,
                    blog_post=daily_blog
                )
                weekly_content.extend(daily_content)
            
            # Save weekly package info
            self._save_weekly_package(week_id, week_start_date, season, holidays, theme)
            
            return {
                'success': True,
                'week_id': week_id,
                'week_start_date': week_start_date.isoformat(),
                'season': season,
                'theme': theme,
                'holidays': [(h[0].isoformat(), h[1], h[2], h[3]) for h in holidays],
                'content_pieces': len(weekly_content),
                'content_breakdown': self._get_content_breakdown(weekly_content),
                'content': [self._content_piece_to_dict(cp) for cp in weekly_content]
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_daily_blog_post(self, date: datetime, day_name: str, season: str, 
                                  theme: str, holidays: List, week_id: str) -> ContentPiece:
        """Generate a daily blog post using Claude API or fallback"""
        
        # Generate blog title based on day and season
        blog_title = self._generate_daily_blog_title(date, day_name, season, theme, holidays)
        
        # Determine keywords for the blog
        keywords = self._get_seasonal_keywords(season)[:5]
        
        # Holiday context for the day
        holiday_context = None
        for holiday_date, holiday_name, gardening_focus, content_theme in holidays:
            if holiday_date.date() == date.date():
                holiday_context = f"{holiday_name} - {gardening_focus}"
                break
        
        if not holiday_context:
            holiday_context = f"{season} gardening - {day_name} focus"
        
        # Generate blog content using Claude API or fallback
        if self.claude_client:
            blog_content = self._generate_blog_with_claude(blog_title, keywords, season, holiday_context)
        else:
            blog_content = self._generate_fallback_blog_html(blog_title, keywords, season, holiday_context)
        
        # Generate meta description
        meta_description = f"Expert {season} gardening advice from Elm Dirt. Learn organic methods for {holiday_context}. Professional tips for sustainable garden success."
        
        # Generate image suggestions
        image_suggestion = self._generate_blog_image_suggestions(blog_title, season, holiday_context)
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=blog_title,
            content=blog_content,
            platform="blog",
            content_type="daily_blog_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=8, minute=0, second=0),  # 8am daily
            keywords=keywords,
            hashtags=[],  # Blogs don't typically use hashtags
            image_suggestion=image_suggestion,
            ai_provider="claude" if self.claude_client else "fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context,
            meta_description=meta_description
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _generate_daily_blog_title(self, date: datetime, day_name: str, season: str, 
                                   theme: str, holidays: List) -> str:
        """Generate daily blog post titles"""
        
        # Check for holidays first
        for holiday_date, holiday_name, gardening_focus, content_theme in holidays:
            if holiday_date.date() == date.date():
                return f"{holiday_name} Garden Guide: {content_theme} for {season.title()} Success"
        
        # Day-specific blog themes
        daily_blog_themes = {
            'Monday': [
                f"Monday Motivation: {season.title()} Garden Goals That Actually Work",
                f"Start Your Week Right: Essential {season.title()} Garden Tasks",
                f"Monday Garden Planning: {theme} Success Strategies"
            ],
            'Tuesday': [
                f"Tuesday Tips: Professional {season.title()} Garden Techniques",
                f"Transform Tuesday: {season.title()} Garden Problem Solutions",
                f"Tuesday Techniques: Advanced {season.title()} Growing Methods"
            ],
            'Wednesday': [
                f"Wednesday Wisdom: Time-Tested {season.title()} Garden Secrets",
                f"Mid-Week Garden Guide: {season.title()} Care Essentials",
                f"Wednesday Wonder: {season.title()} Garden Transformations"
            ],
            'Thursday': [
                f"Thursday Thoughts: Why {season.title()} Soil Health Matters",
                f"Transform Thursday: {season.title()} Garden Success Stories",
                f"Thursday Tips: Organic {season.title()} Garden Methods"
            ],
            'Friday': [
                f"Friday Focus: Weekend {season.title()} Garden Projects",
                f"Feature Friday: Best {season.title()} Garden Products",
                f"Friday Favorites: {season.title()} Garden Must-Haves"
            ],
            'Saturday': [
                f"Saturday Success: Easy {season.title()} Garden Wins",
                f"Weekend Warrior: {season.title()} Garden Project Guide",
                f"Saturday Solutions: {season.title()} Garden Quick Fixes"
            ]
        }
        
        day_themes = daily_blog_themes.get(day_name, daily_blog_themes['Monday'])
        return random.choice(day_themes)
    
    def _generate_blog_with_claude(self, title: str, keywords: List[str], season: str, holiday_context: str) -> str:
        """Generate blog post using Claude API"""
        
        prompt = f"""Generate an SEO-optimized blog article for the title '{title}' for my ecommerce Shopify store, aiming to boost organic search rankings and conversions.

**Article Requirements:**
- Write a 700-1000 word article following SEO best practices
- Target audience: 50+ year old home gardeners across the US
- Use colloquial tone that works for experienced gardeners
- Include primary keyword '{keywords[0]}' at 1-2% density (5-7 times)
- Integrate secondary keywords naturally: {', '.join(keywords[1:3])}
- Include semantic variations and gardening terminology

**Content Structure:**
- H1 for title
- H2 for 3-4 main sections
- Introduction (100-150 words)
- Body sections with practical advice
- Conclusion with clear call-to-action

**Brand Integration:**
- Naturally mention Elm Dirt products (Ancient Soil, Plant Juice, Bloom Juice, Worm Castings)
- Focus on organic, sustainable gardening methods
- Emphasize soil health and microbe-rich growing
- Include seasonal context for {season} and {holiday_context}

**Technical Requirements:**
- Output in clean HTML format suitable for Shopify blog
- Use proper HTML tags (h1, h2, p, ul, li, strong, em)
- Include natural keyword placement
- Write for readability and engagement

**Output Format:**
Provide the complete HTML article ready for Shopify, starting with the H1 title tag."""

        try:
            response = self.claude_client.generate_content(prompt, max_tokens=4000)
            if response:
                return response
            else:
                logger.warning("Claude API returned empty response, using fallback")
                return self._generate_fallback_blog_html(title, keywords, season, holiday_context)
        except Exception as e:
            logger.error(f"Error generating blog with Claude: {str(e)}")
            return self._generate_fallback_blog_html(title, keywords, season, holiday_context)
    
    def _generate_fallback_blog_html(self, title: str, keywords: List[str], season: str, holiday_context: str) -> str:
        """Generate fallback blog content in HTML format"""
        primary_keyword = keywords[0] if keywords else 'organic gardening'
        
        return f"""<h1>{title}</h1>

<p>Welcome to another helpful guide from Elm Dirt! As experienced gardeners know, mastering <strong>{primary_keyword}</strong> during {season} is essential for long-term garden success. Today we're focusing on {holiday_context} and how organic methods can transform your garden experience.</p>

<h2>Understanding {primary_keyword.title()} for {season.title()} Success</h2>

<p>For home gardeners who've been working the soil for years, you know that {primary_keyword} isn't just about quick fixes—it's about building something that lasts. During {season}, your garden needs specific care that honors both the season's demands and nature's timing.</p>

<p>The key is working with what you've got while improving it naturally. That's where <em>sustainable practices</em> really shine. Instead of fighting against your soil and plants, you're building them up from the ground up.</p>

<h3>The Elm Dirt Approach to {season.title()} Gardening</h3>

<p>Our products like <strong>Ancient Soil</strong> and <strong>Plant Juice</strong> work because they respect what experienced gardeners already know—healthy soil creates healthy plants. These organic solutions provide the beneficial microbes and nutrients your plants need, especially important during {holiday_context}.</p>

<ul>
<li>Ancient Soil builds long-term soil health with worm castings and beneficial microbes</li>
<li>Plant Juice delivers over 250 species of bacteria and fungi for plant support</li>
<li>Bloom Juice provides targeted nutrition for flowering and fruiting plants</li>
<li>Worm Castings offer gentle, sustained nutrition that plants actually use</li>
</ul>

<h2>Essential {season.title()} Tasks That Make a Difference</h2>

<p>After decades of gardening, you learn what actually moves the needle. Here's what works for {season} success:</p>

<p><strong>Start with your soil foundation.</strong> Good {primary_keyword} always begins below ground. Test your soil pH and organic matter levels. Most gardeners are surprised by what they find when they actually test instead of guessing.</p>

<p><strong>Feed consistently, not heavily.</strong> Plants prefer steady nutrition over feast-or-famine feeding. Small, regular applications of organic amendments work better than dumping a bunch of synthetic fertilizer once and hoping for the best.</p>

<p><strong>Watch your plants, not your calendar.</strong> Nature doesn't follow our schedules. Your plants will tell you what they need if you know how to look. Yellowing leaves, stunted growth, poor flowering—these are conversations your plants are trying to have with you.</p>

<h2>Solving Common {season.title()} Challenges the Organic Way</h2>

<p>Every {season} brings its own set of problems. The good news? Most issues gardeners face come back to soil health and plant nutrition. When you build up your soil biology with products like our <strong>Ancient Soil</strong>, you're not just feeding this year's plants—you're investing in easier gardening for years to come.</p>

<p>Problems like poor germination, weak plant growth, or disappointing harvests usually trace back to soil that's been depleted or imbalanced. Synthetic fertilizers might give you a quick green-up, but they don't build the soil ecosystem your plants need for long-term health.</p>

<p>That's why we developed <strong>Plant Juice</strong> with over 250 species of beneficial bacteria and fungi. These microorganisms help plants with everything from nutrient uptake to disease resistance. It's like giving your plants a complete support system instead of just a quick meal.</p>

<h2>Your {season.title()} Action Plan</h2>

<p>Ready to put this into practice? Here's your straightforward approach for {holiday_context}:</p>

<ol>
<li><strong>Assess your current soil condition</strong> - Test pH and look at organic matter content</li>
<li><strong>Build soil biology</strong> - Add Ancient Soil and worm castings to establish beneficial microbes</li>
<li><strong>Feed strategically</strong> - Use Plant Juice for overall plant health and Bloom Juice for flowering plants</li>
<li><strong>Monitor and adjust</strong> - Watch plant response and adjust care based on what you see</li>
</ol>

<h2>The Long Game: Building Garden Success</h2>

<p>Good {primary_keyword} isn't about this year's harvest—though you'll definitely see improvements quickly. It's about creating a garden ecosystem that gets easier and more productive every year. When you focus on soil health and work with natural processes, you're setting yourself up for decades of successful gardening.</p>

<p>Whether you're dealing with {holiday_context} or just want to improve your garden's performance, organic methods provide solutions that get better over time. Visit our store to learn more about how our products can help you succeed this {season} and beyond.</p>

<p><strong>Ready to transform your garden this {season}?</strong> <a href="/collections/all">Shop our complete line of organic garden products</a> and start building the soil your plants deserve. Your future self will thank you for the investment you make today.</p>"""
    
    def _generate_blog_image_suggestions(self, title: str, season: str, holiday_context: str) -> str:
        """Generate detailed image suggestions for blog posts"""
        
        base_suggestions = [
            f"Hero image: Beautiful {season} garden showcasing healthy, thriving plants with rich, dark soil visible",
            f"Product showcase: Elm Dirt Ancient Soil being applied to garden bed with visible soil texture and earthworms",
            f"Before/after comparison: Garden transformation showing improvement in plant health and growth",
            f"Close-up: Healthy plant roots in rich, organic soil demonstrating soil health benefits",
            f"Seasonal garden scene: {season.title()} garden layout with diverse plants and organic growing methods",
            f"Lifestyle shot: Experienced gardener (50+) working in well-maintained organic garden"
        ]
        
        # Add holiday-specific suggestions if applicable
        if "Valentine" in holiday_context:
            base_suggestions.append("Romantic garden setting with flowering plants and heart-shaped decorations")
        elif "Earth Day" in holiday_context:
            base_suggestions.append("Sustainable gardening practices with compost bins and rain collection")
        elif "Mother's Day" in holiday_context:
            base_suggestions.append("Multi-generational gardening scene with mothers and children planting together")
        
        return " | ".join(base_suggestions[:6])  # Return top 6 suggestions
    
    def _generate_daily_content_package(self, date: datetime, day_name: str, season: str, 
                                       theme: str, holidays: List, week_id: str, blog_post: ContentPiece) -> List[ContentPiece]:
        """Generate all content for a single day"""
        daily_content = []
        
        # Determine daily theme variations
        daily_themes = {
            'Monday': 'Week Kickoff & Planning',
            'Tuesday': 'Tips & Techniques', 
            'Wednesday': 'Wisdom Wednesday',
            'Thursday': 'Transformation Thursday',
            'Friday': 'Feature Friday',
            'Saturday': 'Weekend Projects'
        }
        
        daily_theme = daily_themes.get(day_name, 'Garden Inspiration')
        
        # Holiday context for the day
        holiday_context = None
        for holiday_date, holiday_name, gardening_focus, content_theme in holidays:
            if holiday_date.date() == date.date():
                holiday_context = f"{holiday_name} - {gardening_focus}"
                break
        
        if not holiday_context:
            holiday_context = f"{season} gardening - {daily_theme}"
        
        # Generate 3 Instagram posts per day
        instagram_posts = self._generate_platform_posts(
            platform='instagram',
            count=3,
            date=date,
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            week_id=week_id,
            blog_post=blog_post
        )
        daily_content.extend(instagram_posts)
        
        # Generate 3 Facebook posts per day  
        facebook_posts = self._generate_platform_posts(
            platform='facebook',
            count=3,
            date=date,
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            week_id=week_id,
            blog_post=blog_post
        )
        daily_content.extend(facebook_posts)
        
        # Generate 1 TikTok video script per day
        tiktok_post = self._generate_tiktok_video_script(
            date=date,
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            week_id=week_id,
            blog_post=blog_post
        )
        daily_content.append(tiktok_post)
        
        # Generate 1 LinkedIn post per day
        linkedin_post = self._generate_linkedin_post(
            date=date,
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            week_id=week_id,
            blog_post=blog_post
        )
        daily_content.append(linkedin_post)
        
        return daily_content
    
    def _generate_platform_posts(self, platform: str, count: int, date: datetime, day_name: str,
                                daily_theme: str, season: str, holiday_context: str, 
                                week_id: str, blog_post: ContentPiece) -> List[ContentPiece]:
        """Generate multiple posts for a specific platform"""
        posts = []
        
        # Platform-specific posting times
        platform_times = {
            'instagram': [9, 13, 17],  # 9am, 1pm, 5pm
            'facebook': [10, 14, 18],  # 10am, 2pm, 6pm
        }
        
        post_times = platform_times.get(platform, [9, 13, 17])
        
        for i in range(count):
            post_time = date.replace(hour=post_times[i % len(post_times)], minute=0, second=0)
            
            # Generate different post types
            post_types = ['educational_tip', 'product_spotlight', 'community_question', 'seasonal_advice', 'behind_scenes']
            post_type = post_types[i % len(post_types)]
            
            post_content = self._create_platform_specific_post(
                platform=platform,
                post_type=post_type,
                date=date,
                day_name=day_name,
                daily_theme=daily_theme,
                season=season,
                holiday_context=holiday_context,
                blog_post=blog_post
            )
            
            content_piece = ContentPiece(
                id=str(uuid.uuid4()),
                title=f"{day_name} {platform.title()} Post {i+1} - {post_type.replace('_', ' ').title()}",
                content=post_content['content'],
                platform=platform,
                content_type=f"{platform}_post",
                status=ContentStatus.DRAFT,
                scheduled_time=post_time,
                keywords=blog_post.keywords[:3],
                hashtags=post_content['hashtags'],
                image_suggestion=post_content['image_suggestion'],
                ai_provider="fallback",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                week_id=week_id,
                holiday_context=holiday_context
            )
            
            self.db_manager.save_content_piece(content_piece)
            posts.append(content_piece)
        
        return posts
    
    def _generate_tiktok_video_script(self, date: datetime, day_name: str, daily_theme: str,
                                     season: str, holiday_context: str, week_id: str, 
                                     blog_post: ContentPiece) -> ContentPiece:
        """Generate TikTok video script"""
        
        # TikTok video templates based on day
        tiktok_templates = {
            'Monday': {
                'hook': "POV: You're starting your garden week right",
                'content': "Here's your Monday garden motivation! This week we're focusing on {theme}. Quick tip: {tip}. Who's ready to grow something amazing?",
                'cta': "Save this for your garden planning!"
            },
            'Tuesday': {
                'hook': "The gardening tip that changed everything",
                'content': "I wish someone told me this about {season} gardening sooner! {tip}. This simple trick will transform your {season} garden results.",
                'cta': "Try this and tell me your results!"
            },
            'Wednesday': {
                'hook': "Garden wisdom Wednesday: The secret pros know",
                'content': "Here's what professional gardeners do during {season} that beginners miss: {tip}. This one change makes ALL the difference.",
                'cta': "Which tip surprised you most?"
            },
            'Thursday': {
                'hook': "Transformation Thursday: Garden glow-up time",
                'content': "Watch how we transform struggling plants with this {season} method! Before vs after results are incredible. {tip}",
                'cta': "Show me your garden transformations!"
            },
            'Friday': {
                'hook': "Friday feature: This product is a game-changer",
                'content': "Why Elm Dirt's {product} is perfect for {season}! Here's exactly how to use it for amazing results. {tip}",
                'cta': "Link in bio to try it yourself!"
            },
            'Saturday': {
                'hook': "Weekend project that takes 10 minutes",
                'content': "Perfect Saturday garden project for {season}! Super easy and your plants will thank you. {tip}",
                'cta': "Who's trying this weekend?"
            }
        }
        
        template = tiktok_templates.get(day_name, tiktok_templates['Monday'])
        
        # Generate seasonal tips
        seasonal_tips = {
            'spring': "Start with healthy soil using Ancient Soil for better root development",
            'summer': "Water deeply but less frequently, and use Plant Juice to help with heat stress",
            'fall': "Build soil health now with compost and worm castings for next year's success",
            'winter': "Focus on houseplants and use this time to plan your best garden yet"
        }
        
        # Generate product mentions
        products = ['Ancient Soil', 'Plant Juice', 'Bloom Juice', 'Worm Castings']
        featured_product = random.choice(products)
        
        tip = seasonal_tips.get(season, "Focus on soil health as your foundation")
        
        script_content = f"TikTok Video Script - {day_name} {daily_theme}\n\nHOOK (0-3 seconds):\n{template['hook']}\n\nCONTENT (3-45 seconds):\n{template['content'].format(theme=daily_theme, season=season, tip=tip, product=featured_product)}\n\nCALL TO ACTION (45-60 seconds):\n{template['cta']}\n\nVISUAL NOTES:\n- Start with close-up of garden/plants\n- Show hands demonstrating technique\n- Before/after shots if applicable\n- End with product shot or garden result\n\nHASHTAGS: #gardentok #organicgardening #elmdirt #{season}gardening #planttok #gardeningtips #growyourown"
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=f"{day_name} TikTok Video Script - {daily_theme}",
            content=script_content,
            platform="tiktok",
            content_type="video_script",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=15, minute=0, second=0),  # 3pm
            keywords=blog_post.keywords[:3],
            hashtags=['gardentok', 'organicgardening', 'elmdirt', f'{season}gardening', 'planttok', 'gardeningtips'],
            image_suggestion=f"TikTok video showing {season} gardening technique with Elm Dirt products",
            ai_provider="fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _generate_linkedin_post(self, date: datetime, day_name: str, daily_theme: str,
                               season: str, holiday_context: str, week_id: str, 
                               blog_post: ContentPiece) -> ContentPiece:
        """Generate professional LinkedIn post"""
        
        linkedin_templates = {
            'Monday': "Starting the week with insights on sustainable agriculture and organic growing methods that benefit both business and environment...",
            'Tuesday': "Industry insight: The growing demand for organic gardening solutions reflects a broader shift toward sustainable practices...",
            'Wednesday': "Mid-week reflection on how small-scale organic gardening principles scale to commercial agriculture...",
            'Thursday': "The business case for organic growing methods: higher yields, lower long-term costs, and market demand...",
            'Friday': "Week wrap-up: Key trends in sustainable agriculture and what they mean for growers at every scale...",
            'Saturday': "Weekend perspective: How home gardening expertise translates to professional growing operations..."
        }
        
        template = linkedin_templates.get(day_name, linkedin_templates['Monday'])
        
        # Professional content based on season
        professional_content = {
            'spring': "Spring soil preparation investments pay dividends throughout the growing season. Professional growers who focus on soil biology see 20-30% better yields.",
            'summer': "Summer stress management in crops mirrors water-wise gardening principles. Efficient irrigation and soil health reduce input costs significantly.",
            'fall': "Fall soil building sets the foundation for next year's success. Commercial operations investing in organic matter see compounding returns.",
            'winter': "Winter planning season offers time to analyze data and optimize growing strategies. Indoor growing operations maintain year-round productivity."
        }
        
        content = f"{template}\n\n{professional_content.get(season, 'Sustainable growing practices benefit operations at every scale.')}\n\nKey takeaways from this {season} season:\n• Soil biology drives long-term profitability\n• Organic inputs reduce dependency on synthetic alternatives\n• Sustainable methods attract premium market pricing\n• Customer demand for organic products continues growing\n\nWhat sustainable practices are you implementing in your operations this {season}?\n\n#SustainableAgriculture #OrganicGrowing #AgBusiness #SoilHealth #RegenerativeAgriculture"
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=f"{day_name} LinkedIn Post - {daily_theme}",
            content=content,
            platform="linkedin",
            content_type="linkedin_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=11, minute=0, second=0),  # 11am
            keywords=blog_post.keywords[:3],
            hashtags=['SustainableAgriculture', 'OrganicGrowing', 'AgBusiness'],
            image_suggestion=f"Professional image of {season} agricultural/gardening operation",
            ai_provider="fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece

# This concludes Part 2 - Middle
# Continue to Part 3 for YouTube outline generation, utility methods, and Flask routes
# Enhanced Elm Dirt Content Automation Platform - Part 3: End
# YouTube Generation, Utility Methods, and Flask Routes

    def _generate_youtube_outline(self, week_start_date: datetime, season: str, theme: str,
                                 holidays: List, week_id: str) -> ContentPiece:
        """Generate 60-minute YouTube video outline"""
        
        # Determine video focus
        if holidays:
            primary_holiday = holidays[0]
            video_focus = f"{primary_holiday[1]} - {primary_holiday[2]}"
            video_title = f"{primary_holiday[1]} Garden Special: {theme} Complete Guide"
        else:
            video_focus = f"{season} gardening mastery"
            video_title = f"Complete {season.title()} Garden Mastery: {theme} (60-Min Deep Dive)"
        
        # 60-minute video outline
        outline_content = f"""YouTube Video Outline - 60 Minutes
Title: {video_title}

INTRO (0-3 minutes)
• Welcome and channel introduction
• What viewers will learn in this complete guide
• Why {season} gardening matters for {video_focus}
• Quick preview of Elm Dirt products we'll discuss

SECTION 1: FOUNDATION KNOWLEDGE (3-15 minutes)
• Understanding {season} growing conditions
• Soil preparation essentials for {season}
• Common mistakes to avoid this {season}
• Why organic methods work better long-term

SECTION 2: SOIL HEALTH DEEP DIVE (15-25 minutes)
• The science of living soil
• How Ancient Soil transforms your garden
• Worm castings: nature's perfect fertilizer
• Building soil biology for {season} success
• Demonstration: Testing and improving your soil

SECTION 3: PLANT NUTRITION MASTERY (25-35 minutes)
• Plant Juice: liquid nutrition that works
• When and how to feed plants in {season}
• Bloom Juice for flowering and fruiting plants
• Organic feeding schedules that actually work
• Demonstration: Proper application techniques

SECTION 4: SEASONAL STRATEGIES (35-45 minutes)
• {season.title()}-specific growing techniques
• Problem-solving common {season} challenges
• Water management for {season} conditions
• Pest and disease prevention naturally
• Regional considerations across the US

SECTION 5: ADVANCED TECHNIQUES (45-55 minutes)
• Companion planting for {season}
• Succession planting strategies
• Container gardening optimization
• Greenhouse and indoor growing tips
• Scaling up: from hobby to market garden

WRAP-UP & Q&A (55-60 minutes)
• Key takeaways for {season} success
• Viewer questions from comments
• Next week's topic preview
• Where to find Elm Dirt products
• Subscribe and notification bell reminder

RESOURCES MENTIONED:
• Elm Dirt Ancient Soil
• Plant Juice liquid fertilizer
• Bloom Juice for flowering plants
• Worm Castings
• Seasonal planting calendar
• Soil testing guide

KEYWORDS: {season} gardening, organic fertilizer, soil health, plant nutrition, garden success"""
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=video_title,
            content=outline_content,
            platform="youtube",
            content_type="video_outline",
            status=ContentStatus.DRAFT,
            scheduled_time=week_start_date.replace(hour=16, minute=0, second=0),
            keywords=self._get_seasonal_keywords(season)[:5],
            hashtags=[f'{season}gardening', 'organicgardening', 'elmdirt', 'gardeningtips', 'soilhealth'],
            image_suggestion=f"YouTube thumbnail showing {season} garden success with Elm Dirt products",
            ai_provider="fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=video_focus
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _create_platform_specific_post(self, platform: str, post_type: str, date: datetime,
                                      day_name: str, daily_theme: str, season: str, 
                                      holiday_context: str, blog_post: ContentPiece) -> Dict:
        """Create platform-specific post content"""
        
        # Instagram post templates
        if platform == 'instagram':
            if post_type == 'educational_tip':
                content = f"{day_name} Garden Wisdom: Here's a {season} tip that transforms gardens! During {season}, focus on soil health first - everything else follows. Ancient Soil provides the foundation your plants crave. What's your biggest {season} gardening question?"
                
            elif post_type == 'product_spotlight':
                content = f"Product Spotlight: Why Plant Juice is perfect for {season}! This liquid organic fertilizer delivers nutrients exactly when your plants need them. Perfect for {season} growing conditions. Results speak for themselves!"
                
            elif post_type == 'community_question':
                content = f"{day_name} Question: What's your secret for {season} garden success? We love hearing from our community! Share your best {season} tip below - let's learn from each other. Growing together!"
                
            elif post_type == 'seasonal_advice':
                content = f"{season.title()} Reminder: This is the perfect time for {holiday_context}! Don't miss out on optimal growing conditions. Your future self (and your plants) will thank you! Who's taking action this week?"
                
            elif post_type == 'behind_scenes':
                content = f"Behind the scenes at Elm Dirt: Creating products that work naturally with {season} growing cycles. Quality ingredients make the difference. From our garden to yours!"
            
            hashtags = ['organicgardening', 'elmdirt', 'plantcare', f'{season}gardening', 'gardenlife', 'growyourown', 'sustainablegardening', 'healthysoil', 'gardenlovers', 'plantparent']
        
        # Facebook post templates  
        elif platform == 'facebook':
            if post_type == 'educational_tip':
                content = f"Fellow gardeners! {day_name} brings us another opportunity to improve our {season} gardens. Here's something I wish I'd known sooner about {season} gardening: soil health truly is everything. When you invest in quality organic amendments like Ancient Soil, you're setting up success for months to come. What's working best in your {season} garden?"
                
            elif post_type == 'product_spotlight':
                content = f"Let's talk about Plant Juice and why it's become essential for {season} gardening success. This isn't just another fertilizer - it's a complete soil ecosystem in a bottle. The beneficial microbes help plants thrive naturally, especially during {season} growing conditions. Anyone else seeing amazing results?"
                
            elif post_type == 'community_question':
                content = f"Good {day_name}, garden friends! I'd love to hear from our community: what's your biggest {season} gardening challenge this year? Whether it's soil prep, plant selection, or timing, let's help each other succeed. The best tips often come from fellow gardeners who've been there!"
                
            elif post_type == 'seasonal_advice':
                content = f"Perfect timing for {holiday_context}! If you're planning your {season} garden activities, remember that small actions now create big results later. Organic methods might take a little more patience, but the long-term benefits for your soil and plants are incredible. Who's making moves this week?"
                
            elif post_type == 'behind_scenes':
                content = f"A peek behind the curtain: developing Elm Dirt products means understanding exactly what plants need during {season}. Every ingredient is chosen for a reason, tested extensively, and proven to work with nature's timing. Quality isn't accidental - it's intentional."
            
            hashtags = ['organicgardening', 'elmdirt', 'sustainablegardening', 'gardenlife', f'{season}gardening']
        
        return {
            'content': content,
            'hashtags': hashtags,
            'image_suggestion': f"{season.title()} garden photo featuring {post_type.replace('_', ' ')} for {platform}",
            'post_type': post_type
        }
    
    def _get_content_breakdown(self, content_pieces: List[ContentPiece]) -> Dict:
        """Get breakdown of content by platform and type"""
        breakdown = {}
        for piece in content_pieces:
            platform = piece.platform
            if platform not in breakdown:
                breakdown[platform] = 0
            breakdown[platform] += 1
        return breakdown
    
    def _get_seasonal_keywords(self, season: str) -> List[str]:
        """Get seasonal keywords"""
        base_keywords = self.config.TARGET_KEYWORDS[:3]
        
        seasonal_keywords = {
            'spring': ['spring gardening', 'soil preparation', 'planting season'] + base_keywords,
            'summer': ['summer care', 'plant nutrition', 'garden maintenance'] + base_keywords,
            'fall': ['fall gardening', 'harvest time', 'winter preparation'] + base_keywords,
            'winter': ['winter gardening', 'indoor plants', 'garden planning'] + base_keywords
        }
        
        return seasonal_keywords.get(season, base_keywords)
    
    def _content_piece_to_dict(self, content_piece: ContentPiece) -> Dict:
        """Convert ContentPiece to dictionary for JSON serialization"""
        return {
            'id': content_piece.id,
            'title': content_piece.title,
            'content': content_piece.content,
            'platform': content_piece.platform,
            'content_type': content_piece.content_type,
            'status': content_piece.status.value,
            'scheduled_time': content_piece.scheduled_time.isoformat() if content_piece.scheduled_time else None,
            'keywords': content_piece.keywords,
            'hashtags': content_piece.hashtags,
            'image_suggestion': content_piece.image_suggestion,
            'ai_provider': content_piece.ai_provider,
            'created_at': content_piece.created_at.isoformat(),
            'updated_at': content_piece.updated_at.isoformat(),
            'week_id': content_piece.week_id,
            'holiday_context': content_piece.holiday_context,
            'meta_description': content_piece.meta_description
        }
    
    def _save_weekly_package(self, week_id: str, start_date: datetime, season: str, 
                           holidays: List, theme: str):
        """Save weekly package information"""
        try:
            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()
            
            end_date = start_date + timedelta(days=6)
            holidays_json = json.dumps([(h[0].isoformat(), h[1], h[2], h[3]) for h in holidays])
            
            cursor.execute('''
                INSERT OR REPLACE INTO weekly_packages 
                (id, week_start_date, week_end_date, season, holidays, theme, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                week_id, start_date.date(), end_date.date(), season, holidays_json,
                theme, ContentStatus.DRAFT.value, datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving weekly package: {str(e)}")

# Initialize content generator
content_generator = ContentGenerator(db_manager)

# Flask Routes and Web Interface
@app.route('/')
def index():
    """Serve the main interface"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elm Dirt Content Automation Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, #c9d393, #d7c4b5); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #114817, #0a2b0d); color: white; padding: 2rem; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .main-content { padding: 2rem; }
        .section-title { color: #114817; font-size: 1.8rem; margin-bottom: 1rem; border-bottom: 3px solid #4eb155; padding-bottom: 0.5rem; }
        .calendar-controls { display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .week-selector { flex: 1; min-width: 250px; }
        .week-selector label { display: block; margin-bottom: 0.5rem; font-weight: 600; color: #114817; }
        .week-selector input { width: 100%; padding: 12px; border: 2px solid #c9d393; border-radius: 8px; font-size: 1rem; }
        .generate-btn { background: linear-gradient(135deg, #fec962, #c5a150); color: #3a2313; border: none; padding: 12px 30px; border-radius: 8px; font-weight: 600; font-size: 1rem; cursor: pointer; transition: all 0.3s ease; align-self: end; }
        .generate-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(254, 201, 98, 0.4); }
        .generate-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .week-info { background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .week-info h3 { color: #843648; margin-bottom: 0.5rem; }
        .holiday-badge { background: #fec962; color: #3a2313; padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; margin: 0.2rem; display: inline-block; }
        .content-preview { margin-top: 2rem; }
        .content-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; margin-top: 1rem; }
        .content-card { background: white; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.5rem; transition: all 0.3s ease; }
        .content-card:hover { border-color: #4eb155; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .content-card h4 { color: #114817; margin-bottom: 1rem; font-size: 1.2rem; }
        .platform-badge { background: #4eb155; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-bottom: 1rem; display: inline-block; }
        .content-preview-text { color: #666; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1rem; }
        .loading { text-align: center; padding: 2rem; color: #666; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #4eb155; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 1rem; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .error-message { background: #f8d7da; color: #721c24; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .success-message { background: #d1e7dd; color: #0f5132; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .api-status { margin: 1rem 0; padding: 1rem; border-radius: 8px; }
        .api-enabled { background: #d1e7dd; color: #0f5132; border-left: 4px solid #198754; }
        .api-disabled { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
        @media (max-width: 768px) { .calendar-controls { flex-direction: column; } .content-grid { grid-template-columns: 1fr; } .header h1 { font-size: 2rem; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 Elm Dirt Content Automation</h1>
            <p>Generate 56 pieces of weekly content with Claude AI and holiday awareness</p>
        </div>
        <div class="main-content">
            <div id="api-status-notice" class="api-status">
                <strong>🔄 Checking API Status...</strong> Verifying Claude API connection...
            </div>
            <div class="calendar-section">
                <h2 class="section-title">📅 Weekly Content Generator</h2>
                <div class="calendar-controls">
                    <div class="week-selector">
                        <label for="week-date">Select Week (Monday):</label>
                        <input type="date" id="week-date" />
                    </div>
                    <button class="generate-btn" id="generate-btn" onclick="generateWeeklyContent()">Generate 56 Pieces of Content</button>
                </div>
                <div id="week-info" class="week-info" style="display: none;">
                    <h3>Week Information</h3>
                    <div id="week-details"></div>
                </div>
            </div>
            <div class="content-preview" id="content-preview" style="display: none;">
                <h2 class="section-title">📝 Generated Content</h2>
                <div id="content-grid" class="content-grid"></div>
            </div>
        </div>
    </div>
    <script>
        async function checkAPIStatus() {
            try {
                const response = await fetch('/api/check-claude-status');
                const result = await response.json();
                const statusNotice = document.getElementById('api-status-notice');
                
                if (result.claude_enabled) {
                    statusNotice.className = 'api-status api-enabled';
                    statusNotice.innerHTML = '<strong>✅ Claude AI Enabled:</strong> High-quality content generation with AI assistance.';
                } else {
                    statusNotice.className = 'api-status api-disabled';
                    statusNotice.innerHTML = '<strong>⚠️ Claude AI Disabled:</strong> Using fallback templates. Add Claude API key for AI-powered content.';
                }
            } catch (error) {
                const statusNotice = document.getElementById('api-status-notice');
                statusNotice.className = 'api-status api-disabled';
                statusNotice.innerHTML = '<strong>❌ API Check Failed:</strong> Unable to verify Claude status. Content will use fallback mode.';
            }
        }
        
        function setDefaultDate() {
            const today = new Date();
            const monday = new Date(today);
            const dayOfWeek = today.getDay();
            const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
            monday.setDate(today.getDate() + daysUntilMonday);
            const dateInput = document.getElementById('week-date');
            dateInput.value = monday.toISOString().split('T')[0];
        }
        
        async function generateWeeklyContent() {
            const dateInput = document.getElementById('week-date');
            const generateBtn = document.getElementById('generate-btn');
            const weekInfo = document.getElementById('week-info');
            const contentPreview = document.getElementById('content-preview');
            const contentGrid = document.getElementById('content-grid');
            
            if (!dateInput.value) { 
                alert('Please select a date'); 
                return; 
            }
            
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating 56 Pieces...';
            contentGrid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating complete weekly content package...</p><p>Creating 56 pieces of content across all platforms</p><p>Including 6 daily blog posts with Claude AI</p><p>This may take 3-5 minutes</p></div>';
            contentPreview.style.display = 'block';
            
            try {
                const response = await fetch('/api/generate-weekly-content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ week_start_date: dateInput.value })
                });
                const result = await response.json();
                
                if (result.success) {
                    const weekDetails = document.getElementById('week-details');
                    weekDetails.innerHTML = '<p><strong>Season:</strong> ' + result.season + '</p><p><strong>Theme:</strong> ' + result.theme + '</p><p><strong>Content Pieces:</strong> ' + result.content_pieces + '</p>' + (result.holidays.length > 0 ? '<p><strong>Holidays:</strong></p>' + result.holidays.map(h => '<span class="holiday-badge">' + h[1] + '</span>').join('') : '');
                    weekInfo.style.display = 'block';
                    displayContent(result.content, result.content_breakdown);
                    contentGrid.insertAdjacentHTML('afterbegin', '<div class="success-message">✅ Successfully generated ' + result.content_pieces + ' pieces of content for the week of ' + new Date(result.week_start_date).toLocaleDateString() + '!<br><strong>Ready for:</strong> Blog publishing, social media scheduling, and video production.<br><strong>Includes:</strong> 6 daily blog posts, social media content, and video scripts.</div>');
                } else {
                    throw new Error(result.error || 'Failed to generate content');
                }
            } catch (error) {
                console.error('Error:', error);
                contentGrid.innerHTML = '<div class="error-message">❌ Error generating content: ' + error.message + '<br><br>Please check your configuration and try again.</div>';
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate 56 Pieces of Content';
            }
        }
        
        function displayContent(contentPieces, contentBreakdown) {
            const contentGrid = document.getElementById('content-grid');
            const successMessage = contentGrid.querySelector('.success-message');
            contentGrid.innerHTML = '';
            if (successMessage) { contentGrid.appendChild(successMessage); }
            
            const breakdownSummary = document.createElement('div');
            breakdownSummary.className = 'content-breakdown';
            breakdownSummary.innerHTML = '<div style="background: #e8f5e8; padding: 1rem; border-radius: 8px; margin: 1rem 0;"><h3 style="color: #114817; margin-bottom: 0.5rem;">📊 Weekly Content Breakdown</h3><div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">' + Object.entries(contentBreakdown || {}).map(([platform, count]) => '<div style="text-align: center; padding: 0.5rem; background: white; border-radius: 8px;"><div style="font-size: 1.5rem; font-weight: bold; color: #4eb155;">' + count + '</div><div style="font-size: 0.9rem; color: #666; text-transform: capitalize;">' + platform + ' ' + (count === 1 ? 'post' : 'posts') + '</div></div>').join('') + '</div><div style="margin-top: 1rem; padding: 0.5rem; background: #fff3cd; border-radius: 4px; font-size: 0.9rem; color: #856404;"><strong>🎯 Your Schedule:</strong> 56 pieces of content per week across all platforms including daily blogs!</div></div>';
            contentGrid.appendChild(breakdownSummary);
            
            const contentByPlatform = {};
            contentPieces.forEach(piece => {
                if (!contentByPlatform[piece.platform]) { contentByPlatform[piece.platform] = []; }
                contentByPlatform[piece.platform].push(piece);
            });
            
            Object.entries(contentByPlatform).forEach(([platform, pieces]) => {
                const platformHeader = document.createElement('div');
                platformHeader.className = 'platform-section';
                let platformIcon = '📱';
                if (platform === 'blog') platformIcon = '📝';
                if (platform === 'instagram') platformIcon = '📸';
                if (platform === 'facebook') platformIcon = '👥';
                if (platform === 'linkedin') platformIcon = '💼';
                if (platform === 'tiktok') platformIcon = '🎵';
                if (platform === 'youtube') platformIcon = '📺';
                
                platformHeader.innerHTML = '<h3 style="color: #114817; margin: 2rem 0 1rem 0; padding: 0.5rem; background: #f8f9fa; border-left: 4px solid #4eb155; text-transform: capitalize;">' + platformIcon + ' ' + platform + ' Content (' + pieces.length + ' pieces)</h3>';
                contentGrid.appendChild(platformHeader);
                
                pieces.forEach(piece => {
                    const contentCard = document.createElement('div');
                    contentCard.className = 'content-card';
                    let preview = piece.content.length > 300 ? piece.content.substring(0, 300) + '...' : piece.content;
                    
                    // Special handling for HTML blog content
                    if (piece.platform === 'blog' && piece.content.includes('<')) {
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = piece.content;
                        const textContent = tempDiv.textContent || tempDiv.innerText || '';
                        preview = textContent.length > 300 ? textContent.substring(0, 300) + '...' : textContent;
                    }
                    
                    let typeIcon = '📝';
                    if (piece.content_type.includes('video')) typeIcon = '🎬';
                    if (piece.content_type.includes('blog')) typeIcon = '📖';
                    if (piece.platform === 'instagram') typeIcon = '📸';
                    if (piece.platform === 'facebook') typeIcon = '👥';
                    if (piece.platform === 'linkedin') typeIcon = '💼';
                    if (piece.platform === 'tiktok') typeIcon = '🎵';
                    if (piece.platform === 'youtube') typeIcon = '📺';
                    
                    let specialBadges = '';
                    if (piece.content_type.includes('video')) {
                        specialBadges += '<span style="background: #fec962; color: #3a2313; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; margin-left: 0.5rem;">VIDEO</span>';
                    }
                    if (piece.content_type.includes('blog')) {
                        specialBadges += '<span style="background: #843648; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; margin-left: 0.5rem;">BLOG</span>';
                    }
                    if (piece.ai_provider === 'claude') {
                        specialBadges += '<span style="background: #4eb155; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; margin-left: 0.5rem;">AI-POWERED</span>';
                    }
                    
                    contentCard.innerHTML = '<div style="display: flex; align-items: center; margin-bottom: 1rem;"><span style="font-size: 1.5rem; margin-right: 0.5rem;">' + typeIcon + '</span><span class="platform-badge">' + piece.platform + '</span>' + specialBadges + '</div><h4>' + piece.title + '</h4><div class="content-preview-text">' + preview + '</div><div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #eee; font-size: 0.9rem; color: #666;"><p><strong>Keywords:</strong> ' + piece.keywords.join(', ') + '</p><p><strong>Scheduled:</strong> ' + new Date(piece.scheduled_time).toLocaleString() + '</p><p><strong>Status:</strong> ' + piece.status + '</p>' + (piece.hashtags && piece.hashtags.length > 0 ? '<p><strong>Hashtags:</strong> ' + piece.hashtags.slice(0, 5).map(tag => '#' + tag).join(' ') + '</p>' : '') + (piece.image_suggestion ? '<p><strong>Image Ideas:</strong> ' + piece.image_suggestion.split(' | ')[0] + '</p>' : '') + '</div>';
                    contentGrid.appendChild(contentCard);
                });
            });
        }
        
        checkAPIStatus();
        setDefaultDate();
    </script>
</body>
</html>'''

@app.route('/health')
def health_check():
    """Health check endpoint"""
    claude_enabled = bool(content_generator.claude_client)
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0',
        'mode': 'claude_ai' if claude_enabled else 'fallback_templates',
        'content_schedule': '56 pieces per week (including 6 daily blogs)',
        'features': {
            'weekly_calendar': True,
            'holiday_awareness': True,
            'content_preview': True,
            'database_storage': True,
            'bulk_generation': True,
            'claude_ai_integration': claude_enabled,
            'daily_blog_posts': True,
            'html_formatted_blogs': True,
            'image_suggestions': True
        },
        'services': {
            'claude_api': 'enabled' if claude_enabled else 'disabled',
            'shopify_api': 'configured' if Config.SHOPIFY_PASSWORD != 'your_shopify_password' else 'not_configured',
            'database': 'connected'
        }
    }
    return jsonify(health_status)

@app.route('/api/check-claude-status')
def check_claude_status():
    """Check if Claude API is enabled and working"""
    claude_enabled = bool(content_generator.claude_client)
    
    # Test Claude API if enabled
    if claude_enabled:
        try:
            test_response = content_generator.claude_client.generate_content("Test message", max_tokens=50)
            working = bool(test_response)
        except:
            working = False
    else:
        working = False
    
    return jsonify({
        'claude_enabled': claude_enabled,
        'claude_working': working,
        'api_key_configured': Config.CLAUDE_API_KEY != 'your_claude_api_key_here',
        'fallback_mode': not claude_enabled
    })

@app.route('/api/generate-content', methods=['POST'])
def generate_content_api():
    """Generate content based on selected date and type with Claude AI integration"""
    try:
        data = request.get_json()
        selected_date = data.get('date')  # Format: YYYY-MM-DD
        export_type = data.get('type')   # 'weekly' or 'daily'
        day_of_week = data.get('day_of_week')  # 0-6 (Sunday-Saturday)
        
        print(f"Generating content for: {selected_date}, type: {export_type}, day: {day_of_week}")
        
        # Convert date string to datetime object
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        
        # Generate content based on type
        if export_type == 'weekly':
            # Monday selected - generate full week with Claude AI
            content_pieces = generate_full_weekly_content(date_obj, selected_date)
            week_id = f"{date_obj.year}-W{date_obj.isocalendar()[1]}"
        else:
            # Other day selected - generate daily content
            content_pieces = generate_sample_daily_content(date_obj, day_of_week, selected_date)
            week_id = selected_date
        
        print(f"Generated {len(content_pieces)} content pieces")
        
        return jsonify({
            'success': True,
            'content_pieces': content_pieces,
            'week_id': week_id,
            'export_type': export_type,
            'total_pieces': len(content_pieces),
            'date': selected_date
        })
        
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_full_weekly_content(start_date, date_str):
    """Generate complete weekly content using Claude AI integration"""
    from datetime import timedelta
    import random
    
    content_pieces = []
    
    # Get seasonal context for the date
    seasonal_context = get_seasonal_context(start_date)
    
    # Step 1: Generate 6 Blog Post Ideas using Claude AI
    blog_ideas = generate_blog_ideas_with_claude(seasonal_context, start_date)
    
    # Step 2: Generate 6 Full Blog Posts using Claude AI
    for i, blog_idea in enumerate(blog_ideas):
        blog_date = start_date + timedelta(days=i)
        full_blog = generate_blog_with_claude(blog_idea, seasonal_context)
        
        content_pieces.append({
            'title': full_blog['title'],
            'content': full_blog['content'],
            'meta_description': full_blog['meta_description'],
            'keywords': full_blog['keywords'],
            'platform': 'blog',
            'scheduled_time': blog_date.strftime('%Y-%m-%d 09:00:00')
        })
    
    # Step 3: Generate Social Media Content (18 posts each for FB, IG, TikTok)
    social_content = generate_social_media_content(start_date, seasonal_context, blog_ideas)
    content_pieces.extend(social_content)
    
    # Step 4: Generate 6 LinkedIn Posts
    linkedin_content = generate_linkedin_content(start_date, seasonal_context, blog_ideas)
    content_pieces.extend(linkedin_content)
    
    # Step 5: Generate YouTube Outline
    youtube_outline = generate_youtube_outline(start_date, seasonal_context, blog_ideas)
    content_pieces.append(youtube_outline)
    
    return content_pieces

def get_seasonal_context(date_obj):
    """Get seasonal and holiday context for content generation"""
    month = date_obj.month
    day = date_obj.day
    
    # Seasonal mapping
    seasons = {
        (12, 1, 2): "winter",
        (3, 4, 5): "spring", 
        (6, 7, 8): "summer",
        (9, 10, 11): "fall"
    }
    
    current_season = "spring"  # default
    for months, season in seasons.items():
        if month in months:
            current_season = season
            break
    
    # Holiday context
    holidays = []
    if month == 3 and 15 <= day <= 25:
        holidays.append("Spring Equinox")
    elif month == 4 and 15 <= day <= 25:
        holidays.append("Earth Day")
    elif month == 5 and 8 <= day <= 15:
        holidays.append("Mother's Day")
    elif month == 6 and 15 <= day <= 25:
        holidays.append("Summer Solstice")
    elif month == 9 and 15 <= day <= 25:
        holidays.append("Fall Equinox")
    elif month == 10:
        holidays.append("Halloween/Fall Harvest")
    elif month == 11:
        holidays.append("Thanksgiving")
    elif month == 12:
        holidays.append("Winter Holidays")
    elif month == 1:
        holidays.append("New Year/Winter Gardening")
    elif month == 2:
        holidays.append("Valentine's Day")
    
    return {
        'season': current_season,
        'month': calendar.month_name[month],
        'holidays': holidays,
        'date': date_obj.strftime('%B %d, %Y')
    }

def generate_blog_ideas_with_claude(seasonal_context, start_date):
    """Generate 6 blog ideas using Claude AI"""
    
    # This should connect to your existing Claude AI system
    # For now, I'll create a function that calls your Claude API
    
    prompt = f"""Generate blog article ideas

Context:
- Season: {seasonal_context['season']}
- Month: {seasonal_context['month']}
- Date: {seasonal_context['date']}
- Holidays/Events: {', '.join(seasonal_context['holidays']) if seasonal_context['holidays'] else 'None'}

Generate 6 blog article titles for Elm Dirt, an organic gardening soil company. Consider:
- Seasonal gardening tasks appropriate for {seasonal_context['season']}
- Organic gardening methods
- Soil health and plant nutrition
- Seasonal plant care
- Holiday-related gardening if applicable

Make titles SEO-friendly and engaging for home gardeners."""

    # Call your existing Claude API function
    blog_ideas_response = call_claude_api(prompt)
    
    # Parse the response to extract 6 blog titles
    blog_ideas = parse_blog_ideas(blog_ideas_response)
    
    return blog_ideas

def generate_blog_with_claude(blog_title, seasonal_context):
    """Generate full blog post using Claude AI"""
    
    prompt = f"""Generate an SEO-optimized blog article for the title '{blog_title}'

Context:
- Season: {seasonal_context['season']}
- Month: {seasonal_context['month']}
- Brand: Elm Dirt (organic soil amendments and gardening products)
- Target audience: Home gardeners aged 35-65
- Focus: Organic gardening, soil health, sustainable practices

Requirements:
- 800-1200 words
- Include H2 and H3 subheadings
- SEO-optimized with natural keyword integration
- Include practical tips and actionable advice
- Mention Elm Dirt products naturally (Ancient Soil, Plant Juice, Bloom Juice)
- Write in friendly, expert tone
- Include seasonal considerations for {seasonal_context['season']}"""

    # Call your existing Claude API function
    blog_response = call_claude_api(prompt)
    
    # Parse the response
    parsed_blog = parse_blog_response(blog_response, blog_title)
    
    return parsed_blog

def call_claude_api(prompt):
    """Connect to your existing Claude AI system"""
    try:
        # This should use your existing Claude API setup
        # Replace this with your actual Claude API call from your existing system
        
        # Example using your existing setup:
        # return your_existing_claude_function(prompt)
        
        # For now, using a placeholder that connects to Claude
        response = generate_claude_content(prompt)  # Your existing function
        return response
        
    except Exception as e:
        print(f"Claude API error: {e}")
        # Fallback content if Claude fails
        return generate_fallback_content(prompt)

def parse_blog_ideas(claude_response):
    """Parse Claude response to extract blog titles"""
    try:
        # Extract titles from Claude response
        lines = claude_response.split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('1.') or line.startswith('-') or line.startswith('•')):
                # Clean up the title
                title = line.replace('1.', '').replace('2.', '').replace('3.', '')
                title = title.replace('4.', '').replace('5.', '').replace('6.', '')
                title = title.replace('-', '').replace('•', '').strip()
                if title and len(title) > 10:
                    titles.append(title)
        
        # Ensure we have 6 titles
        while len(titles) < 6:
            titles.append(f"Seasonal Gardening Guide for {get_seasonal_context(datetime.now())['season'].title()}")
        
        return titles[:6]
        
    except Exception as e:
        print(f"Error parsing blog ideas: {e}")
        # Fallback titles
        return [
            "Spring Garden Soil Preparation Guide",
            "Organic Pest Control Methods That Actually Work", 
            "Composting 101: Turn Waste into Garden Gold",
            "Seasonal Plant Care for Maximum Growth",
            "Building Healthy Soil with Natural Amendments",
            "Water-Wise Gardening for Sustainable Gardens"
        ]

def parse_blog_response(claude_response, original_title):
    """Parse Claude blog response into structured format"""
    try:
        # Extract meta description (look for it in the response)
        meta_description = f"Expert gardening advice about {original_title.lower()} with organic methods and proven techniques."
        
        # Extract keywords from title and content
        keywords = extract_keywords_from_content(original_title, claude_response)
        
        return {
            'title': original_title,
            'content': claude_response,
            'meta_description': meta_description,
            'keywords': keywords
        }
        
    except Exception as e:
        print(f"Error parsing blog response: {e}")
        return {
            'title': original_title,
            'content': f"<h2>{original_title}</h2><p>Content generated by Elm Dirt content system.</p>",
            'meta_description': f"Expert advice about {original_title.lower()}",
            'keywords': "organic gardening, soil health, plant care"
        }

def extract_keywords_from_content(title, content):
    """Extract SEO keywords from title and content"""
    # Simple keyword extraction
    import re
    
    # Common gardening keywords
    base_keywords = ["organic gardening", "soil health", "plant care", "garden tips"]
    
    # Extract keywords from title
    title_words = re.findall(r'\b\w+\b', title.lower())
    title_keywords = [word for word in title_words if len(word) > 3]
    
    # Combine and return
    all_keywords = base_keywords + title_keywords[:3]
    return ', '.join(all_keywords[:6])

def generate_social_media_content(start_date, seasonal_context, blog_ideas):
    """Generate 18 posts each for Facebook, Instagram, and TikTok"""
    content_pieces = []
    
    # Content themes for the week
    themes = [
        "Educational Tips",
        "Product Features", 
        "Seasonal Advice",
        "Community Engagement",
        "Behind the Scenes",
        "User Generated Content"
    ]
    
    platforms = ['facebook', 'instagram', 'tiktok']
    
    for platform in platforms:
        for day in range(7):  # 7 days
            current_date = start_date + timedelta(days=day)
            
            # Generate 2-3 posts per day to reach 18 total
            posts_per_day = 3 if day < 4 else 2  # More posts early in week
            
            for post_num in range(posts_per_day):
                theme = themes[post_num % len(themes)]
                
                if platform == 'facebook':
                    post_content = generate_facebook_post(theme, seasonal_context, blog_ideas, day, post_num)
                elif platform == 'instagram':
                    post_content = generate_instagram_post(theme, seasonal_context, blog_ideas, day, post_num)
                else:  # tiktok
                    post_content = generate_tiktok_idea(theme, seasonal_context, blog_ideas, day, post_num)
                
                # Schedule posts throughout the day
                hour = 9 + (post_num * 4)  # 9am, 1pm, 5pm
                
                content_pieces.append({
                    'title': f'{platform.title()} - {theme} (Day {day+1})',
                    'content': post_content['content'],
                    'keywords': post_content['keywords'],
                    'platform': platform,
                    'scheduled_time': current_date.strftime(f'%Y-%m-%d {hour:02d}:00:00')
                })
    
    return content_pieces

def generate_facebook_post(theme, seasonal_context, blog_ideas, day, post_num):
    """Generate Facebook post content"""
    
    facebook_templates = {
        "Educational Tips": [
            f"🌱 {seasonal_context['season'].title()} gardening tip: Did you know that healthy soil contains billions of microorganisms? These tiny helpers break down organic matter and make nutrients available to your plants. Our Ancient Soil blend supports this natural ecosystem!",
            f"💡 Quick {seasonal_context['season']} garden tip: The best time to water your plants is early morning. This gives them time to absorb water before the heat of the day and reduces evaporation. What's your watering schedule?",
            f"🌿 Soil health fact: Adding just 2 inches of compost to your garden beds can improve water retention by up to 40%! Perfect for {seasonal_context['season']} gardening when water efficiency matters."
        ],
        "Product Features": [
            f"🏆 Why gardeners love Ancient Soil: 'I've been using it for two seasons and my vegetable yields have doubled!' - Sarah K. Perfect for {seasonal_context['season']} planting!",
            f"✨ What makes our Plant Juice special? Over 250 beneficial microorganisms working together to create living soil. Your plants will thank you this {seasonal_context['season']}!",
            f"🌱 Ancient Soil vs regular potting mix: Our blend includes worm castings, biochar, and beneficial microbes. Regular potting mix? Just dead organic matter. See the difference in your {seasonal_context['season']} garden!"
        ],
        "Seasonal Advice": [
            f"🍂 {seasonal_context['season'].title()} garden checklist: Test soil pH, add organic matter, plan your layout, and don't forget to feed your soil! What's first on your {seasonal_context['season']} to-do list?",
            f"🌤️ Perfect {seasonal_context['season']} weather for garden prep! Time to get those beds ready for the growing season. Who else is excited to get their hands dirty?",
            f"📅 {seasonal_context['season'].title()} reminder: Don't rush the season! Wait for consistent soil temperatures before planting tender crops. Patience pays off in the garden."
        ]
    }
    
    templates = facebook_templates.get(theme, facebook_templates["Educational Tips"])
    content = templates[post_num % len(templates)]
    
    return {
        'content': content,
        'keywords': [f'{seasonal_context["season"]} gardening', 'organic soil', 'garden tips', 'plant care']
    }

def generate_instagram_post(theme, seasonal_context, blog_ideas, day, post_num):
    """Generate Instagram post content"""
    
    instagram_templates = {
        "Educational Tips": [
            f"{seasonal_context['season'].title()} soil prep 101! 🌱\n\n✨ Test pH levels\n🌿 Add organic matter\n💧 Check drainage\n🪱 Feed the microbes\n\nReady to level up your garden game?\n\n#OrganicGardening #{seasonal_context['season'].title()}Gardening #SoilHealth #ElmDirt",
            f"Garden myth busted! 🚫\n\nMyth: More fertilizer = better plants\nTruth: Healthy soil + balanced nutrition = thriving plants\n\nOur Ancient Soil provides slow, steady nutrition your plants actually need! 🌱\n\n#GardenMyths #OrganicGardening #HealthySoil",
            f"Why we're obsessed with soil microbes 🔬\n\n• Break down organic matter\n• Make nutrients available\n• Protect plant roots\n• Improve soil structure\n\nLiving soil = living plants! 🌿\n\n#SoilScience #MicroorganismsMatter #OrganicGardening"
        ],
        "Product Features": [
            f"Ancient Soil ingredients spotlight! ✨\n\n🪱 Premium worm castings\n🔥 Activated biochar\n🌊 Sea kelp meal\n🦇 Aged bat guano\n🌋 Volcanic azomite\n\nNature's perfect recipe for plant success!\n\n#AncientSoil #OrganicIngredients #PlantNutrition",
            f"Customer love! 💚\n\n'My tomatoes have never been bigger!' - Maria T.\n'Best investment for my garden' - John R.\n'Plants are thriving like never before' - Lisa K.\n\nJoin thousands of happy gardeners! 🌱\n\n#CustomerLove #GardenSuccess #HappyPlants",
            f"Science meets nature 🧪🌱\n\nOur Plant Juice contains:\n• 250+ beneficial microorganisms\n• Organic growth stimulants\n• Natural plant hormones\n• Enzyme activators\n\nWatch your garden come alive!\n\n#PlantScience #LivingSoil #OrganicGardening"
        ]
    }
    
    templates = instagram_templates.get(theme, instagram_templates["Educational Tips"])
    content = templates[post_num % len(templates)]
    
    hashtags = ['ElmDirt', 'OrganicGardening', f'{seasonal_context["season"].title()}Gardening', 'GardenLife', 'HealthySoil']
    
    return {
        'content': content,
        'keywords': hashtags
    }

def generate_tiktok_idea(theme, seasonal_context, blog_ideas, day, post_num):
    """Generate TikTok video ideas"""
    
    tiktok_ideas = {
        "Educational Tips": [
            f"POV: You're learning why soil pH matters for {seasonal_context['season']} planting 🌱 [Show pH test kit, explain ideal ranges, dramatic before/after plant comparison]",
            f"Soil transformation in 30 seconds! ⏰ [Time-lapse of adding Ancient Soil to garden bed, mixing, planting, fast-forward growth]",
            f"Garden hack: The paper towel soil test! 📄 [Show how to test soil drainage with simple paper towel method]"
        ],
        "Product Features": [
            f"Unboxing our Ancient Soil blend! 📦 [ASMR unboxing, show texture, smell, ingredients close-up, satisfied customer reaction]",
            f"Why worm castings are garden gold! 🪱✨ [Microscope view of castings, plant growth comparison, happy plant dance]",
            f"Ancient Soil vs regular soil challenge! ⚔️ [Side-by-side plant growth test, dramatic reveal after 2 weeks]"
        ],
        "Behind the Scenes": [
            f"How we make Ancient Soil! 🏭 [Behind-scenes of production, ingredients mixing, quality testing, team passion]",
            f"Meet our soil scientist! 👩‍🔬 [Quick expert tips, lab testing, nerdy soil facts made fun]",
            f"From farm to garden! 🚚 [Follow a bag from production to happy customer's garden]"
        ]
    }
    
    ideas = tiktok_ideas.get(theme, tiktok_ideas["Educational Tips"])
    content = ideas[post_num % len(ideas)]
    
    return {
        'content': content,
        'keywords': ['ElmDirtTok', 'GardeningHacks', 'PlantTok', f'{seasonal_context["season"]}Garden', 'OrganicGardening']
    }

def generate_linkedin_content(start_date, seasonal_context, blog_ideas):
    """Generate 6 LinkedIn posts for the week"""
    content_pieces = []
    
    linkedin_themes = [
        "Industry Insights",
        "Sustainability Focus", 
        "Business Growth",
        "Team Spotlight",
        "Customer Success",
        "Innovation Story"
    ]
    
    for i, theme in enumerate(linkedin_themes):
        post_date = start_date + timedelta(days=i)
        
        linkedin_content = generate_linkedin_post(theme, seasonal_context, blog_ideas[i % len(blog_ideas)])
        
        content_pieces.append({
            'title': f'LinkedIn - {theme}',
            'content': linkedin_content['content'],
            'keywords': linkedin_content['keywords'],
            'platform': 'linkedin',
            'scheduled_time': post_date.strftime('%Y-%m-%d 10:00:00')
        })
    
    return content_pieces

def generate_linkedin_post(theme, seasonal_context, blog_topic):
    """Generate individual LinkedIn post"""
    
    linkedin_templates = {
        "Industry Insights": f"""The organic gardening industry is experiencing unprecedented growth, with 77% of households now growing food at home.

Key trends we're seeing this {seasonal_context['season']}:
- Increased focus on soil health over quick fixes
- Growing demand for sustainable growing practices  
- Shift toward regenerative gardening methods
- Rising interest in beneficial microorganisms

At Elm Dirt, we're proud to be at the forefront of this movement, providing gardeners with science-backed, organic solutions that build healthy soil ecosystems.

What trends are you seeing in your industry? 

#OrganicGardening #Sustainability #IndustryTrends #SoilHealth""",

        "Sustainability Focus": f"""Sustainability isn't just a buzzword for us - it's our mission.

Our {seasonal_context['season']} sustainability initiatives:
🌱 Carbon-negative production process
♻️ 100% recyclable packaging  
🌍 Local sourcing to reduce transport
🔬 Supporting soil regeneration research
🤝 Partnering with sustainable farms

Every bag of Ancient Soil sold helps sequester carbon and builds healthier ecosystems. When business aligns with environmental impact, everyone wins.

How is your organization contributing to sustainability?

#Sustainability #RegenerativeAgriculture #CarbonSequestration #ClimateAction""",

        "Customer Success": f"""Customer spotlight: Sarah's garden transformation 🌟

"After switching to Ancient Soil last {seasonal_context['season']}, my vegetable yields increased 150%. But more importantly, my plants are healthier and more resilient. The soil feels alive!" - Sarah K., Colorado

This is why we do what we do. It's not just about selling products - it's about empowering people to grow healthy food and build sustainable gardens.

Success stories like Sarah's remind us that when we help soil thrive, we help communities thrive.

What success story would you like to share?

#CustomerSuccess #OrganicGardening #CommunityImpact #HealthySoil"""
    }
    
    content = linkedin_templates.get(theme, linkedin_templates["Industry Insights"])
    
    return {
        'content': content,
        'keywords': ['B2B gardening', 'organic agriculture', 'sustainability', 'soil health']
    }

def generate_youtube_outline(start_date, seasonal_context, blog_ideas):
    """Generate 60-minute YouTube video outline"""
    
    outline_content = f"""60-Minute YouTube Video: "Complete {seasonal_context['season'].title()} Garden Setup Guide"

INTRO (5 minutes)
- Welcome and channel introduction
- What we'll cover in this comprehensive guide
- Why {seasonal_context['season']} prep is crucial for year-round success

SEGMENT 1: Soil Foundation (15 minutes)
- Testing your soil pH and nutrients
- Understanding soil composition
- When and how to add organic amendments
- Ancient Soil demonstration and benefits
- Common soil mistakes to avoid

SEGMENT 2: {seasonal_context['season'].title()} Plant Selection (12 minutes) 
- Best plants for {seasonal_context['season']} in different zones
- Seed starting vs transplants
- Companion planting strategies
- Succession planting for continuous harvest

SEGMENT 3: Garden Layout & Design (10 minutes)
- Planning your {seasonal_context['season']} garden layout
- Maximizing space and sunlight
- Creating efficient watering systems
- Tool and equipment essentials

SEGMENT 4: Organic Pest & Disease Prevention (8 minutes)
- Preventive measures for {seasonal_context['season']}
- Beneficial insects and how to attract them
- Natural pest control methods
- Building plant immunity through soil health

SEGMENT 5: Maintenance Schedule (8 minutes)
- Weekly {seasonal_context['season']} garden tasks
- Watering, feeding, and monitoring schedules
- When to harvest for peak nutrition
- Preparing for next season

CONCLUSION & Q&A (2 minutes)
- Key takeaways for {seasonal_context['season']} success
- Where to find more resources
- Community engagement and comments

CALL TO ACTION:
- Subscribe for weekly garden tips
- Download free {seasonal_context['season']} planting calendar
- Try Ancient Soil with special YouTube discount

PRODUCTS TO FEATURE:
- Ancient Soil (soil amendment demo)
- Plant Juice (feeding demonstration)  
- Bloom Juice (flowering plant care)

SEASONAL FOCUS: {', '.join(seasonal_context['holidays']) if seasonal_context['holidays'] else f'{seasonal_context["season"]} gardening tasks'}"""

    return {
        'title': f'YouTube Video - Complete {seasonal_context["season"].title()} Garden Guide',
        'content': outline_content,
        'keywords': [f'{seasonal_context["season"]} gardening', 'garden setup', 'organic gardening', 'soil health'],
        'platform': 'youtube',
        'scheduled_time': start_date.strftime('%Y-%m-%d 11:00:00')
    }

def generate_fallback_content(prompt):
    """Fallback content when Claude API fails"""
    return """<h2>Seasonal Garden Care Guide</h2>
<p>Expert gardening advice for maintaining healthy plants and soil throughout the growing season.</p>
<h3>Essential Garden Tasks</h3>
<ul>
<li>Test and amend soil as needed</li>
<li>Monitor plant health regularly</li>
<li>Maintain consistent watering schedule</li>
<li>Add organic matter to support soil life</li>
</ul>
<p>For best results, use high-quality organic amendments like Ancient Soil to build healthy, living soil that supports vigorous plant growth.</p>"""

# You'll need to replace this with your actual Claude API function
def generate_claude_content(prompt):
    """Replace this with your existing Claude API integration"""
    # This should call your existing Claude API setup
    # Example: return your_claude_api_function(prompt)
    
    # Placeholder - replace with your actual implementation
    return generate_fallback_content(prompt)

def generate_sample_weekly_content(start_date, date_str):
    """Generate sample content for entire week"""
    from datetime import timedelta
    import random
    
    content_pieces = []
    
    # Blog topics for the week
    blog_topics = [
        {
            'title': 'Spring Garden Soil Preparation: Your Complete Guide',
            'content': '''<h2>Preparing Your Garden Soil for Spring Success</h2>
<p>As winter melts away, it's time to give your garden soil the attention it deserves. Proper soil preparation is the foundation of a thriving garden.</p>

<h3>Testing Your Soil</h3>
<p>Start with a soil test to understand your pH levels and nutrient content. Most vegetables prefer a pH between 6.0-7.0.</p>

<h3>Adding Organic Matter</h3>
<ul>
<li>Compost improves soil structure and adds nutrients</li>
<li>Worm castings provide gentle, slow-release nutrition</li>
<li>Our Ancient Soil blend combines the best of both worlds</li>
</ul>

<h3>Spring Soil Tasks</h3>
<p>Remove any winter debris, gently work in organic amendments, and avoid working wet soil to prevent compaction.</p>''',
            'meta_description': 'Complete guide to spring soil preparation including testing, organic amendments, and proper techniques for healthy garden soil.',
            'keywords': 'spring gardening, soil preparation, soil testing, organic gardening, compost, garden soil'
        },
        {
            'title': 'Organic Pest Prevention: Start Strong This Season',
            'content': '''<h2>Getting Ahead of Garden Pests Naturally</h2>
<p>The best pest control strategy starts before pests become a problem. Here's how to build natural defenses in your garden.</p>

<h3>Companion Planting</h3>
<p>Strategic plant combinations can naturally repel pests and attract beneficial insects.</p>

<h3>Soil Health = Plant Health</h3>
<p>Healthy plants in rich, living soil are naturally more resistant to pest damage. Strong root systems and robust growth help plants defend themselves.</p>

<h3>Early Season Prevention</h3>
<ul>
<li>Remove overwintering pest habitat</li>
<li>Install row covers for vulnerable plants</li>
<li>Encourage beneficial insects with diverse plantings</li>
</ul>''',
            'meta_description': 'Learn organic pest prevention strategies including companion planting, soil health, and natural deterrents for a healthy garden.',
            'keywords': 'organic pest control, companion planting, beneficial insects, natural gardening, pest prevention'
        }
    ]
    
    # Add 2 blog posts for the week
    for i, blog_topic in enumerate(blog_topics):
        blog_date = start_date + timedelta(days=i)
        content_pieces.append({
            'title': blog_topic['title'],
            'content': blog_topic['content'],
            'meta_description': blog_topic['meta_description'],
            'keywords': blog_topic['keywords'],
            'platform': 'blog',
            'scheduled_time': blog_date.strftime('%Y-%m-%d 09:00:00')
        })
    
    # Generate social media content for each day
    social_content_templates = {
        'monday': {
            'instagram': "Monday motivation: Spring is here! 🌱 Time to get those garden beds ready. What's first on your spring garden to-do list?",
            'facebook': "Monday means it's time to start thinking about spring garden prep! What's your biggest gardening goal this season?",
        },
        'tuesday': {
            'instagram': "Tuesday tip: Test your soil pH before adding amendments! Most veggies love a pH between 6.0-7.0 🧪",
            'facebook': "Tuesday garden tip: Don't skip the soil test! Understanding your soil's pH and nutrients is the first step to garden success.",
        },
        'wednesday': {
            'instagram': "Wednesday wisdom: Healthy soil = healthy plants! 🌿 Our Ancient Soil blend gives your garden the foundation it needs to thrive.",
            'facebook': "Wednesday reflection: What's the secret to amazing garden harvests? It all starts with the soil beneath your feet.",
        },
        'thursday': {
            'instagram': "Thursday thoughts: Companion planting isn't just pretty - it's practical! 🌸 Marigolds with tomatoes, anyone?",
            'facebook': "Thursday garden planning: Are you thinking about companion planting this year? Nature has some amazing partnerships to offer!",
        },
        'friday': {
            'instagram': "Friday feeling: Almost weekend = almost garden time! 🎉 What projects are on your weekend gardening agenda?",
            'facebook': "Friday check-in: How are your spring garden preparations going? Share your progress with our gardening community!",
        },
        'saturday': {
            'instagram': "Saturday garden day! ☀️ Perfect weather for getting your hands dirty. What are you planting today?",
            'facebook': "Saturday in the garden! Whether you're prepping beds or starting seeds, make today count in your garden journey.",
        },
        'sunday': {
            'instagram': "Sunday garden planning: Take time to dream and plan for your best garden season yet! 📝✨",
            'facebook': "Sunday reflection: Gardening teaches us patience, nurtures our souls, and feeds our families. What does your garden mean to you?",
        }
    }
    
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Generate content for each day of the week
    for day_num in range(7):
        current_date = start_date + timedelta(days=day_num)
        day_name = day_names[day_num]
        
        # Instagram post
        if day_num in [0, 2, 4, 6]:  # Monday, Wednesday, Friday, Sunday
            instagram_content = social_content_templates[day_name]['instagram']
            hashtags = ['SpringGardening', 'OrganicGardening', 'ElmDirt', 'GardenLife', 'HealthySoil']
            
            content_pieces.append({
                'title': f'Instagram Post - {day_name.title()}',
                'content': f"{instagram_content}\n\n#{' #'.join(hashtags)}",
                'keywords': hashtags,
                'platform': 'instagram',
                'scheduled_time': current_date.strftime('%Y-%m-%d 14:00:00')
            })
        
        # Facebook post
        if day_num in [0, 2, 5]:  # Monday, Wednesday, Saturday
            facebook_content = social_content_templates[day_name]['facebook']
            
            content_pieces.append({
                'title': f'Facebook Post - {day_name.title()}',
                'content': facebook_content,
                'keywords': ['gardening community', 'spring prep', 'organic gardening'],
                'platform': 'facebook',
                'scheduled_time': current_date.strftime('%Y-%m-%d 15:00:00')
            })
    
    # Add weekly email newsletter (Wednesday)
    email_date = start_date + timedelta(days=2)
    content_pieces.append({
        'title': 'Weekly Garden Newsletter',
        'content': f'''Subject: Your Spring Garden Success Plan - Week of {start_date.strftime('%B %d')}

Hello Fellow Gardener! 🌱

Spring is in full swing, and your garden is calling! This week, we're focusing on the foundation of great gardening: healthy soil.

THIS WEEK'S GARDEN PRIORITIES:
□ Test your soil pH and nutrient levels
□ Add 2-3 inches of compost to garden beds  
□ Plan your companion planting strategy
□ Start warm-season seeds indoors
□ Clean and prep garden tools

FEATURED TIP: Don't Rush Spring Planting!
While it's tempting to get everything in the ground, wait for consistent soil temperatures. Cold soil leads to poor germination and stressed plants.

PRODUCT SPOTLIGHT: Ancient Soil
Give your garden the best start with our premium soil amendment. Packed with worm castings, biochar, and beneficial microorganisms.

COMMUNITY QUESTION:
What's your biggest spring gardening challenge? Reply and let us know - we love helping fellow gardeners succeed!

Happy Gardening!
The Elm Dirt Team''',
        'platform': 'email',
        'scheduled_time': email_date.strftime('%Y-%m-%d 08:00:00')
    })
    
    return content_pieces

def generate_sample_daily_content(selected_date, day_of_week, date_str):
    """Generate sample content for specific day only"""
    content_pieces = []
    
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_name = day_names[day_of_week].lower()
    
    # Daily social media content templates
    daily_templates = {
        0: {  # Sunday
            'instagram': "Sunday garden reflection: What lessons has your garden taught you? 🌱✨ Share your garden wisdom below!",
            'facebook': "Sunday thoughts: Gardening connects us to nature, teaches patience, and rewards our care. What's your favorite thing about gardening?"
        },
        1: {  # Monday  
            'instagram': "Monday motivation: New week, new growth! 🌱 What garden goals are you tackling this week?",
            'facebook': "Monday garden check-in: What's growing in your garden this week? Share your progress with our community!"
        },
        2: {  # Tuesday
            'instagram': "Tuesday tip: Morning watering helps plants stay hydrated all day! 💧 What's your watering schedule?",
            'facebook': "Tuesday garden tip: Consistent watering is key to plant health. Deep, less frequent watering encourages strong root growth."
        },
        3: {  # Wednesday
            'instagram': "Wednesday wisdom: Healthy soil feeds healthy plants! 🌿 How are you nurturing your soil this season?",
            'facebook': "Wednesday reflection: The secret to amazing harvests? It all starts with healthy, living soil full of beneficial microorganisms."
        },
        4: {  # Thursday
            'instagram': "Thursday thoughts: Companion planting = nature's teamwork! 🌸 What plants are partnering in your garden?",
            'facebook': "Thursday planning: Companion planting isn't just beautiful - it's practical! Plants can help each other grow stronger and healthier."
        },
        5: {  # Friday
            'instagram': "Friday garden prep: Weekend projects ahead! 🎉 What's on your garden to-do list?",
            'facebook': "Friday motivation: The weekend is perfect for garden projects! What garden tasks are you excited to tackle?"
        },
        6: {  # Saturday
            'instagram': "Saturday garden time! ☀️ Perfect day to get your hands in the soil. What are you planting today?",
            'facebook': "Saturday in the garden! Whether you're weeding, planting, or just enjoying your space, make it a great garden day!"
        }
    }
    
    # Generate Instagram post for most days
    if day_of_week in [0, 1, 2, 4, 5, 6]:  # All days except Wednesday
        instagram_content = daily_templates[day_of_week]['instagram']
        hashtags = ['GardenLife', 'OrganicGardening', 'ElmDirt', 'PlantLove', 'GrowYourOwn']
        
        content_pieces.append({
            'title': f'Instagram Post - {day_name.title()}',
            'content': f"{instagram_content}\n\n#{' #'.join(hashtags)}",
            'keywords': hashtags,
            'platform': 'instagram',
            'scheduled_time': selected_date.strftime('%Y-%m-%d 14:00:00')
        })
    
    # Generate Facebook post for select days
    if day_of_week in [1, 3, 6]:  # Monday, Wednesday, Saturday
        facebook_content = daily_templates[day_of_week]['facebook']
        
        content_pieces.append({
            'title': f'Facebook Post - {day_name.title()}',
            'content': facebook_content,
            'keywords': ['gardening community', 'garden tips', 'organic gardening'],
            'platform': 'facebook',
            'scheduled_time': selected_date.strftime('%Y-%m-%d 15:00:00')
        })
    
    # Add daily email tip for Wednesday
    if day_of_week == 3:  # Wednesday
        content_pieces.append({
            'title': 'Daily Garden Tip Email',
            'content': f'''Subject: Wednesday Garden Wisdom - {selected_date.strftime('%B %d')}

Quick garden tip for your Wednesday! 🌱

Today's focus: SOIL HEALTH

The foundation of every great garden is healthy, living soil. Here's one simple thing you can do today:

ADD ORGANIC MATTER
Whether it's compost, aged manure, or our Ancient Soil blend, adding organic matter:
- Improves soil structure
- Feeds beneficial microorganisms  
- Increases water retention
- Provides slow-release nutrients

Even adding just an inch of compost to your beds makes a huge difference!

Keep growing!
The Elm Dirt Team''',
            'platform': 'email',
            'scheduled_time': selected_date.strftime('%Y-%m-%d 08:00:00')
        })
    
    return content_pieces

# Helper functions (integrate with your existing system)
def should_post_on_day(platform, day_of_week):
    """Determine if platform should post on this day"""
    posting_schedule = {
        'instagram': [1, 3, 5],  # Monday, Wednesday, Friday
        'facebook': [1, 2, 4, 6],  # Monday, Tuesday, Thursday, Saturday
        'pinterest': [0, 2, 4],  # Sunday, Tuesday, Thursday
        'twitter': [1, 2, 3, 4, 5]  # Weekdays
    }
    return day_of_week in posting_schedule.get(platform, [])

def get_optimal_time(platform):
    """Get optimal posting time for platform"""
    optimal_times = {
        'instagram': '14',  # 2 PM
        'facebook': '15',   # 3 PM
        'pinterest': '11',  # 11 AM
        'twitter': '12',    # 12 PM
        'email': '08'       # 8 AM
    }
    return optimal_times.get(platform, '12')

# Integration functions - replace these with your actual functions
def generate_blog_content(topic):
    """Replace with your actual blog generation function"""
    return f"<h2>{topic}</h2><p>Generated blog content about {topic}...</p>"

def generate_social_content(platform, date):
    """Replace with your actual social content generation function"""
    return f"Generated {platform} content for {date.strftime('%A, %B %d')}"

def generate_email_content(start_date):
    """Replace with your actual email generation function"""
    return f"Subject: Weekly Garden Update\n\nWeekly content for week of {start_date.strftime('%B %d, %Y')}"

def generate_daily_email_content(date):
    """Replace with your actual daily email generation function"""
    return f"Subject: Daily Garden Tip\n\nDaily tip for {date.strftime('%A, %B %d')}"

def extract_keywords(topic):
    """Replace with your actual keyword extraction function"""
    return topic.lower().replace(' ', ', ')

def get_platform_hashtags(platform):
    """Replace with your actual hashtag generation function"""
    hashtags = {
        'instagram': ['GardenLife', 'OrganicGardening', 'ElmDirt'],
        'facebook': ['gardening', 'organic', 'sustainable'],
        'pinterest': ['garden tips', 'organic gardening', 'plant care'],
        'twitter': ['gardening', 'plants', 'organic']
    }
    return hashtags.get(platform, ['gardening'])

@app.route('/api/generate-weekly-content', methods=['POST'])
def generate_weekly_content():
    """Generate a complete week of content with holiday awareness and daily blogs"""
    data = request.json
    
    try:
        week_start_str = data.get('week_start_date')
        if not week_start_str:
            return jsonify({
                'success': False,
                'error': 'week_start_date is required (YYYY-MM-DD format)'
            }), 400
        
        week_start_date = datetime.strptime(week_start_str, '%Y-%m-%d')
        
        if week_start_date.weekday() != 0:
            week_start_date = week_start_date - timedelta(days=week_start_date.weekday())
        
        result = content_generator.generate_weekly_content(week_start_date)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error generating weekly content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-generation', methods=['GET'])
def test_generation():
    """Test endpoint for content generation"""
    try:
        current_monday = datetime.now() - timedelta(days=datetime.now().weekday())
        
        logger.info("Testing weekly content generation...")
        result = content_generator.generate_weekly_content(current_monday)
        
        return jsonify({
            'success': True,
            'test_results': {
                'weekly_generation': result.get('success', False),
                'content_pieces_generated': result.get('content_pieces', 0),
                'week_theme': result.get('theme'),
                'season': result.get('season'),
                'ai_provider': 'claude' if content_generator.claude_client else 'fallback',
                'daily_blogs_included': True
            },
            'full_result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/content/<content_id>')
def get_content_piece(content_id):
    """Get individual content piece by ID"""
    try:
        content_piece = content_generator.db_manager.get_content_piece(content_id)
        if content_piece:
            return jsonify({
                'success': True,
                'content': content_generator._content_piece_to_dict(content_piece)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Content piece not found'
            }), 404
    except Exception as e:
        logger.error(f"Error retrieving content piece: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add this route to your app.py to provide real content data
@app.route('/api/weekly-content/<week_id>')
def get_weekly_content_api(week_id):
    """API endpoint to get actual weekly content"""
    try:
        # Replace this with your actual content retrieval logic
        # This should connect to your existing content generation system
        weekly_content = get_generated_content_for_week(week_id)  # Your existing function
        
        return jsonify({
            'success': True,
            'content_pieces': weekly_content,
            'week_id': week_id,
            'total_pieces': len(weekly_content)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Update the JavaScript in your export page to use real data:

@app.route('/api/export-content/<week_id>')
def export_weekly_content(week_id):
    """Export weekly content in various formats"""
    try:
        content_pieces = content_generator.db_manager.get_weekly_content(week_id)
        
        export_data = {
            'week_id': week_id,
            'generated_at': datetime.now().isoformat(),
            'total_pieces': len(content_pieces),
            'content_breakdown': content_generator._get_content_breakdown(content_pieces),
            'content': [content_generator._content_piece_to_dict(cp) for cp in content_pieces]
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data,
            'download_ready': True
        })
        
    except Exception as e:
        logger.error(f"Error exporting weekly content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/export')
def export_page():
    """Export page with date selection for daily or weekly content"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Content Export by Date</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1000px; 
                margin: 0 auto; 
                padding: 20px; 
                background: #f8f9fa; 
            }
            .header { 
                background: linear-gradient(135deg, #114817, #4eb155); 
                color: white; 
                padding: 2rem; 
                border-radius: 10px; 
                text-align: center; 
                margin-bottom: 2rem; 
            }
            .section { 
                background: white; 
                padding: 30px; 
                margin: 20px 0; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            .date-selector {
                display: flex;
                align-items: center;
                gap: 15px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            .date-input {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                min-width: 150px;
            }
            .btn { 
                padding: 15px 30px; 
                margin: 10px; 
                background: #4eb155; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: bold; 
                transition: all 0.3s ease;
            }
            .btn:hover { 
                background: #3e8e41; 
                transform: translateY(-2px); 
            }
            .btn:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            .btn-secondary {
                background: #6c757d;
            }
            .btn-secondary:hover {
                background: #545b62;
            }
            .info-box {
                background: #e8f4fd;
                border-left: 4px solid #4eb155;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            .selected-date-info {
                background: #fff3cd;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                border: 1px solid #ffeaa7;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌱 Content Export by Date</h1>
            <p>Select a date to export content - Mondays give you the whole week!</p>
        </div>
        
        <div class="section">
            <h2>📅 Select Export Date</h2>
            <div class="info-box">
                <strong>📋 How it works:</strong><br>
                • <strong>Monday:</strong> Exports entire week (Monday-Sunday)<br>
                • <strong>Other days:</strong> Exports content for that specific day only
            </div>
            
            <div class="date-selector">
                <label for="exportDate"><strong>Choose Date:</strong></label>
                <input type="date" id="exportDate" class="date-input" onchange="updateDateInfo()">
                <button class="btn" onclick="exportContent()" id="exportBtn" disabled>
                    🚀 Export Content
                </button>
                <button class="btn btn-secondary" onclick="exportToday()">
                    📅 Export Today
                </button>
            </div>
            
            <div id="dateInfo" class="selected-date-info" style="display: none;">
                <!-- Date info will be populated here -->
            </div>
            
            <div id="loading" class="loading">
                <h3>🔄 Generating your content export...</h3>
                <p>This may take a few moments</p>
            </div>
            
            <div id="error" class="error">
                <!-- Error messages will appear here -->
            </div>
        </div>
        
        <div class="section">
            <h2>🧪 Test with Sample Data</h2>
            <p>Try the export interface with sample content:</p>
            <button class="btn btn-secondary" onclick="testExportInterface()">
                Test Copy-Paste Interface
            </button>
        </div>
        
        <script>
            // Set today's date as default
            document.getElementById('exportDate').value = new Date().toISOString().split('T')[0];
            updateDateInfo();
            
            function updateDateInfo() {
                const dateInput = document.getElementById('exportDate');
                const dateInfo = document.getElementById('dateInfo');
                const exportBtn = document.getElementById('exportBtn');
    
            if (!dateInput.value) {
                dateInfo.style.display = 'none';
                exportBtn.disabled = true;
                return;
            }
                
                const dateStr = dateInput.value;
                const selectedDate = new Date(dateStr + 'T12:00:00'); // Add time to avoid timezone issues
                const dayOfWeek = selectedDate.getDay(); // 0 = Sunday, 1 = Monday, etc.
                const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const dayName = dayNames[dayOfWeek];
    
                let infoHTML = '';
    
                if (dayOfWeek === 1) { // Monday
                    const weekStart = new Date(selectedDate);
                    const weekEnd = new Date(selectedDate);
                    weekEnd.setDate(weekEnd.getDate() + 6);
                    
                     infoHTML = `
                        <h3>📅 Weekly Export Selected</h3>
                        <p><strong>Date:</strong> ${dayName}, ${selectedDate.toLocaleDateString()}</p>
                        <p><strong>Export Range:</strong> Full week (${weekStart.toLocaleDateString()} - ${weekEnd.toLocaleDateString()})</p>
                        <p><strong>Content:</strong> All blog posts, social media posts, emails, and other content for the entire week</p>
                        <p><strong>Platforms:</strong> Shopify blogs, Instagram, Facebook, Email newsletters, Pinterest, Twitter</p>
                    `;
                } else {
                    infoHTML = `
                        <h3>📅 Daily Export Selected</h3>
                        <p><strong>Date:</strong> ${dayName}, ${selectedDate.toLocaleDateString()}</p>
                        <p><strong>Export Range:</strong> Single day only</p>
                        <p><strong>Content:</strong> Social media posts and other content scheduled for this specific day</p>
                        <p><strong>Note:</strong> Blog posts are typically created weekly (Mondays)</p>
                    `;
                }
                
                 dateInfo.innerHTML = infoHTML;
                dateInfo.style.display = 'block';
                exportBtn.disabled = false;
            }
            
            function exportToday() {
                document.getElementById('exportDate').value = new Date().toISOString().split('T')[0];
                updateDateInfo();
            }
            
            function exportContent() {
                const dateInput = document.getElementById('exportDate');
                const dateStr = dateInput.value;
                const selectedDate = new Date(dateStr + 'T12:00:00'); // Fix timezone issue
                const dayOfWeek = selectedDate.getDay();
    
                showLoading(true);
                hideError();
                
                // Determine if it's a weekly or daily export
                const isWeekly = dayOfWeek === 1; // Monday = weekly
                const exportType = isWeekly ? 'weekly' : 'daily';
    
                console.log('Exporting:', {
                    date: dateStr,
                    dayOfWeek: dayOfWeek,
                    exportType: exportType
                });
             
            
                
                 // Call your content generation API
                fetch('/api/generate-content', {
                   method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                    date: dateStr,
                    type: exportType,
                    day_of_week: dayOfWeek
                })
            })
           .then(response => response.json())
           .then(data => {
                console.log('Content generation response:', data);
                if (data.success) {
                    // Content generated successfully, now open export interface
                    return fetch('/api/export/copy-paste', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            content_pieces: data.content_pieces,
                            week_id: data.week_id || dateStr,
                            export_type: exportType
                        })
                    });
                } else {
                    throw new Error(data.error || 'Failed to generate content');
                }
            })
            .then(response => response.text())
            .then(html => {
                showLoading(false);
                const newWindow = window.open('', '_blank', 'width=1400,height=800,scrollbars=yes,resizable=yes');
                newWindow.document.write(html);
                newWindow.document.close();
            })
            .catch(error => {
                showLoading(false);
                showError('Error generating content: ' + error.message);
                console.error('Error:', error);
            });
        }
            
            function testExportInterface() {
                showLoading(true);
                
                // Generate test content
                const testContent = [
                    {
                        title: "Spring Garden Preparation Guide",
                        content: "<h2>Getting Your Garden Ready for Spring</h2><p>As winter fades, it's time to prepare your garden for the growing season...</p><h3>Essential Steps</h3><ul><li>Test soil pH</li><li>Add compost</li><li>Plan your layout</li></ul>",
                        meta_description: "Complete guide to preparing your garden for spring with soil testing, composting, and planning tips.",
                        keywords: "spring gardening, soil preparation, garden planning, compost",
                        platform: "blog",
                        scheduled_time: "2025-06-17 09:00:00"
                    },
                    {
                        title: "Instagram - Spring Garden Tips",
                        content: "Spring is here! 🌱 Time to get your garden ready with these essential tips:\\n\\n✨ Test your soil pH\\n🌿 Add fresh compost\\n📋 Plan your layout\\n🌱 Start seeds indoors\\n\\nWhat's your first spring garden task? Tell us below! ⬇️",
                        keywords: ["SpringGardening", "GardenTips", "OrganicGardening", "ElmDirt"],
                        platform: "instagram",
                        scheduled_time: "2025-06-17 14:00:00"
                    },
                    {
                        title: "Facebook - Community Question",
                        content: "What's the biggest challenge you face when preparing your garden for spring? 🤔\\n\\nWe hear from gardeners all the time about:\\n• Soil that's too compact\\n• Not knowing when to start\\n• Overwhelming plant choices\\n• Pest prevention\\n\\nOur Ancient Soil blend helps with that first one - it creates loose, living soil that plants absolutely love! What's your biggest spring garden challenge? Share in the comments! 💬",
                        keywords: ["gardening community", "spring preparation", "soil health", "gardening tips"],
                        platform: "facebook",
                        scheduled_time: "2025-06-17 16:00:00"
                    },
                    {
                        title: "Email Newsletter - Spring Prep",
                        content: "Subject: Your Spring Garden Prep Checklist (Plus 20% Off!)\\n\\nHello Fellow Gardener! 🌱\\n\\nSpring is officially here, and it's time to get your garden ready for the best growing season yet!\\n\\nYOUR SPRING PREP CHECKLIST:\\n□ Test soil pH (6.0-7.0 is ideal for most plants)\\n□ Add 2-3 inches of compost to beds\\n□ Remove winter debris\\n□ Plan your garden layout\\n□ Start seeds indoors\\n\\nSPECIAL OFFER: Save 20% on Ancient Soil this week only! Perfect for spring soil prep.\\n\\nHappy Gardening!\\nThe Elm Dirt Team",
                        platform: "email",
                        scheduled_time: "2025-06-18 08:00:00"
                    }
                ];
                
                setTimeout(() => {
                    fetch('/api/export/copy-paste', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            content_pieces: testContent,
                            week_id: 'TEST-' + new Date().toISOString().split('T')[0],
                            export_type: 'test'
                        })
                    })
                    .then(response => response.text())
                    .then(html => {
                        showLoading(false);
                        const newWindow = window.open('', '_blank', 'width=1400,height=800,scrollbars=yes,resizable=yes');
                        newWindow.document.write(html);
                        newWindow.document.close();
                    });
                }, 1000);
            }
            
            function showLoading(show) {
                document.getElementById('loading').style.display = show ? 'block' : 'none';
                document.getElementById('exportBtn').disabled = show;
            }
            
            function showError(message) {
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
            }
            
            function hideError() {
                document.getElementById('error').style.display = 'none';
            }
        </script>
    </body>
    </html>
    '''
    
# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/',
            '/health',
            '/api/check-claude-status',
            '/api/generate-weekly-content',
            '/api/test-generation',
            '/api/content/<content_id>',
            '/api/weekly-content/<week_id>',
            '/api/export-content/<week_id>'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'Please check the logs for more details'
    }), 500

# Main application entry point
if __name__ == '__main__':
    logger.info("Starting Enhanced Elm Dirt Content Automation Platform v3.0")
    logger.info(f"Claude API: {'Enabled' if content_generator.claude_client else 'Disabled (using fallback)'}")
    logger.info("Features: 56 pieces per week including 6 daily blog posts")
    logger.info("Database: SQLite initialized")
    logger.info("Endpoints: Web interface and API routes configured")
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 5000))
    
    # Run the application
    app.run(debug=False, host='0.0.0.0', port=port)

# End of Enhanced Elm Dirt Content Automation Platform
# Total: 56 pieces of content per week including:
# - 6 Daily Blog Posts (HTML formatted for Shopify)
# - 18 Instagram Posts (3 per day × 6 days)
# - 18 Facebook Posts (3 per day × 6 days)
# - 6 TikTok Video Scripts (1 per day × 6 days)
# - 6 LinkedIn Posts (1 per day × 6 days)
# - 1 YouTube Video Outline (weekly)
# - 1 Weekly Content Package

# Features:
# ✅ Claude AI Integration with fallback templates
# ✅ Holiday and seasonal awareness
# ✅ SEO-optimized HTML blog content
# ✅ Comprehensive image suggestions
# ✅ Database storage and retrieval
# ✅ Professional web interface
# ✅ API endpoints for content management
# ✅ Error handling and logging
# ✅ Export functionality
# ✅ Health monitoring
