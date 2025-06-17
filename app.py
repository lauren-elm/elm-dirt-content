

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
    
    def generate_blog_with_claude(blog_title, seasonal_context):
    """Generate visually appealing blog post with schema and images"""
    
    prompt = f"""Write a comprehensive, visually appealing blog article titled "{blog_title}"

CONTEXT:
- Season: {seasonal_context['season']}
- Month: {seasonal_context['month']}
- Company: Elm Dirt - Premium organic soil amendments
- Target: Home gardeners aged 35-65

CONTENT REQUIREMENTS:
- 1200-1800 words minimum
- Engaging, expert but approachable tone
- Include practical, actionable advice
- Naturally mention Elm Dirt products where relevant:
  * Ancient Soil: Premium blend with worm castings, biochar, sea kelp
  * Plant Juice: 250+ beneficial microorganisms
  * Bloom Juice: Specialized for flowering plants

HTML FORMATTING REQUIREMENTS:
- Use proper HTML structure with semantic tags
- Include engaging introduction (2-3 paragraphs)
- 4-5 main sections with descriptive H2 headings
- 2-3 subsections with H3 headings under each main section
- Use bullet points (ul/li) for lists and tips
- Include informative paragraphs with <p> tags
- Add emphasis with <strong> and <em> tags where appropriate
- Include a compelling conclusion with actionable next steps

VISUAL ENHANCEMENT:
- Write descriptive headings that are engaging and SEO-friendly
- Include specific numbers, tips, and actionable advice
- Use compelling subheadings that make readers want to continue
- Add calls-to-action throughout the content
- Include seasonal timing and specific recommendations

SEO OPTIMIZATION:
- Use the main keyword "{blog_title.lower()}" naturally throughout
- Include related {seasonal_context['season']} gardening keywords
- Write compelling meta descriptions within content
- Use descriptive, keyword-rich headings

FORMAT: Return only the HTML content with proper tags, starting with an H1 for the title."""

    try:
        print(f"Generating enhanced blog content for: {blog_title}")
        
        # Call Claude API
        blog_response = make_direct_claude_call(prompt)
        
        if blog_response and len(blog_response) > 1000:
            # Claude worked and returned substantial content
            parsed_blog = parse_enhanced_blog_response(blog_response, blog_title, seasonal_context)
            print(f"Successfully generated enhanced blog ({len(blog_response)} chars)")
            return parsed_blog
        
        # Fallback if Claude fails
        print("Claude API failed, using enhanced fallback")
        return get_enhanced_fallback_blog(blog_title, seasonal_context)
        
    except Exception as e:
        print(f"Error in enhanced blog generation: {e}")
        return get_enhanced_fallback_blog(blog_title, seasonal_context)

def parse_enhanced_blog_response(claude_response, original_title, seasonal_context):
    """Parse blog response and add schema + image suggestions"""
    try:
        # Clean and enhance the HTML content
        content = claude_response.strip()
        
        # Ensure it starts with H1 if not already
        if not content.startswith('<h1>'):
            content = f"<h1>{original_title}</h1>\n{content}"
        
        # Generate image suggestions based on content
        image_suggestions = generate_image_suggestions(original_title, content, seasonal_context)
        
        # Generate schema markup
        schema_markup = generate_blog_schema(original_title, content, seasonal_context)
        
        # Generate meta description from content
        meta_description = extract_meta_description(content, original_title, seasonal_context)
        
        # Generate keywords
        keywords = extract_enhanced_keywords(original_title, content, seasonal_context)
        
        # Add enhanced content with image placeholders
        enhanced_content = add_image_placeholders_to_content(content, image_suggestions)
        
        return {
            'title': original_title,
            'content': enhanced_content,
            'meta_description': meta_description,
            'keywords': keywords,
            'schema_markup': schema_markup,
            'image_suggestions': image_suggestions,
            'word_count': len(content.split()),
            'reading_time': f"{len(content.split()) // 200 + 1} min read"
        }
        
    except Exception as e:
        print(f"Error parsing enhanced blog response: {e}")
        return get_enhanced_fallback_blog(original_title, seasonal_context)

def generate_image_suggestions(title, content, seasonal_context):
    """Generate specific image suggestions for the blog post"""
    season = seasonal_context.get('season', 'spring')
    
    # Analyze content for image opportunities
    image_suggestions = []
    
    # Hero image (always needed)
    image_suggestions.append({
        'position': 'hero',
        'description': f"Hero image showcasing {title.lower()} - wide shot of a thriving {season} garden with healthy soil and vibrant plants",
        'alt_text': f"{title} - {season} garden with healthy soil",
        'style': 'landscape',
        'priority': 'high'
    })
    
    # Look for specific content that needs images
    if 'soil' in content.lower():
        image_suggestions.append({
            'position': 'section_1',
            'description': f"Close-up photo of rich, dark soil with visible organic matter and worm castings - hands holding healthy soil",
            'alt_text': 'Healthy organic garden soil with rich texture',
            'style': 'close-up',
            'priority': 'high'
        })
    
    if 'plant' in content.lower() or 'vegetable' in content.lower():
        image_suggestions.append({
            'position': 'section_2', 
            'description': f"Vibrant {season} vegetables growing in garden beds - showing healthy plant growth and development",
            'alt_text': f'{season.title()} vegetables growing in organic garden',
            'style': 'medium shot',
            'priority': 'medium'
        })
    
    if 'compost' in content.lower() or 'organic matter' in content.lower():
        image_suggestions.append({
            'position': 'section_3',
            'description': "Compost pile or bin showing decomposing organic matter, with finished compost in foreground",
            'alt_text': 'Organic compost pile with finished compost',
            'style': 'process shot',
            'priority': 'medium'
        })
    
    # Product images if mentioned
    if 'ancient soil' in content.lower():
        image_suggestions.append({
            'position': 'product_mention',
            'description': "Elm Dirt Ancient Soil product bag with soil spilling out, showing rich texture and quality",
            'alt_text': 'Elm Dirt Ancient Soil organic amendment',
            'style': 'product shot',
            'priority': 'high'
        })
    
    if 'plant juice' in content.lower():
        image_suggestions.append({
            'position': 'product_mention_2',
            'description': "Elm Dirt Plant Juice bottle being used in garden - person applying to plants",
            'alt_text': 'Elm Dirt Plant Juice organic fertilizer application',
            'style': 'action shot',
            'priority': 'medium'
        })
    
    # Seasonal specific images
    seasonal_images = {
        'spring': {
            'description': "Early spring garden preparation - raised beds being prepared with tools and soil amendments",
            'alt_text': 'Spring garden preparation and soil amendment',
            'style': 'wide shot'
        },
        'summer': {
            'description': "Lush summer garden at peak growth with abundant vegetables and flowers",
            'alt_text': 'Thriving summer organic garden with abundant growth',
            'style': 'wide shot'
        },
        'fall': {
            'description': "Fall garden harvest with baskets of vegetables and autumn colors",
            'alt_text': 'Fall garden harvest with seasonal vegetables',
            'style': 'harvest shot'
        },
        'winter': {
            'description': "Winter garden protection with covered beds and cold frames",
            'alt_text': 'Winter garden protection and season extension',
            'style': 'protective shot'
        }
    }
    
    if season in seasonal_images:
        image_suggestions.append({
            'position': 'seasonal',
            **seasonal_images[season],
            'priority': 'medium'
        })
    
    return image_suggestions

def generate_blog_schema(title, content, seasonal_context):
    """Generate JSON-LD schema markup for SEO"""
    from datetime import datetime
    
    # Extract first paragraph for description
    description = extract_meta_description(content, title, seasonal_context)
    
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "image": [
            "https://elmdirt.com/images/blog/soil-health-hero.jpg",
            "https://elmdirt.com/images/blog/organic-garden-wide.jpg",
            "https://elmdirt.com/images/blog/healthy-plants-growing.jpg"
        ],
        "author": {
            "@type": "Organization",
            "name": "Elm Dirt",
            "url": "https://elmdirt.com",
            "logo": {
                "@type": "ImageObject",
                "url": "https://elmdirt.com/images/elm-dirt-logo.png"
            }
        },
        "publisher": {
            "@type": "Organization",
            "name": "Elm Dirt",
            "logo": {
                "@type": "ImageObject",
                "url": "https://elmdirt.com/images/elm-dirt-logo.png"
            }
        },
        "datePublished": datetime.now().strftime('%Y-%m-%d'),
        "dateModified": datetime.now().strftime('%Y-%m-%d'),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://elmdirt.com/blogs/garden-tips/{title.lower().replace(' ', '-')}"
        },
        "articleSection": "Gardening Tips",
        "keywords": extract_enhanced_keywords(title, content, seasonal_context),
        "wordCount": len(content.split()),
        "inLanguage": "en-US",
        "isFamilyFriendly": True,
        "audience": {
            "@type": "Audience",
            "audienceType": "Gardeners"
        }
    }
    
    return schema

def add_image_placeholders_to_content(content, image_suggestions):
    """Add image placeholders throughout the blog content"""
    
    # Add hero image after H1
    if '<h1>' in content:
        hero_img = next((img for img in image_suggestions if img['position'] == 'hero'), None)
        if hero_img:
            hero_html = f"""
<div class="blog-image hero-image">
    <img src="/images/placeholder-{hero_img['style']}.jpg" alt="{hero_img['alt_text']}" loading="lazy" />
    <p class="image-caption">📸 Suggested: {hero_img['description']}</p>
</div>
"""
            content = content.replace('</h1>', f"</h1>\n{hero_html}")
    
    # Add section images after H2 headings
    h2_count = 0
    for img in image_suggestions:
        if img['position'].startswith('section_'):
            section_num = int(img['position'].split('_')[1]) if '_' in img['position'] else 1
            
            # Find the Nth H2 tag
            h2_positions = []
            temp_content = content
            pos = 0
            while True:
                h2_pos = temp_content.find('<h2>', pos)
                if h2_pos == -1:
                    break
                h2_positions.append(h2_pos + pos)
                pos = h2_pos + 4
                temp_content = temp_content[h2_pos + 4:]
            
            if len(h2_positions) >= section_num:
                # Find the end of this H2 section
                h2_end = content.find('</h2>', h2_positions[section_num - 1])
                next_h2 = content.find('<h2>', h2_end) if h2_end != -1 else len(content)
                
                # Add image after first paragraph of this section
                section_content = content[h2_end:next_h2] if h2_end != -1 else content[h2_positions[section_num - 1]:]
                first_p_end = section_content.find('</p>')
                
                if first_p_end != -1:
                    image_html = f"""
<div class="blog-image section-image">
    <img src="/images/placeholder-{img['style']}.jpg" alt="{img['alt_text']}" loading="lazy" />
    <p class="image-caption">📸 Suggested: {img['description']}</p>
</div>
"""
                    insert_pos = h2_end + first_p_end + 4
                    content = content[:insert_pos] + image_html + content[insert_pos:]
    
    return content

def extract_meta_description(content, title, seasonal_context):
    """Extract or generate compelling meta description"""
    # Try to get first paragraph
    first_p_start = content.find('<p>')
    if first_p_start != -1:
        first_p_end = content.find('</p>', first_p_start)
        if first_p_end != -1:
            first_paragraph = content[first_p_start + 3:first_p_end].strip()
            # Clean up any HTML tags
            import re
            clean_text = re.sub(r'<[^>]+>', '', first_paragraph)
            if len(clean_text) > 50:
                return clean_text[:157] + "..." if len(clean_text) > 157 else clean_text
    
    # Fallback meta description
    season = seasonal_context.get('season', 'spring')
    return f"Expert guide to {title.lower()} with proven organic methods for {season} gardening success. Get actionable tips for healthy soil and thriving plants."

def extract_enhanced_keywords(title, content, seasonal_context):
    """Extract comprehensive SEO keywords"""
    import re
    
    season = seasonal_context.get('season', 'spring')
    
    # Base keywords
    base_keywords = [
        f"{season} gardening",
        "organic gardening", 
        "soil health",
        "garden tips",
        "plant care"
    ]
    
    # Extract from title
    title_words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
    title_keywords = [word for word in title_words if word not in ['garden', 'gardening', 'guide', 'complete', 'best', 'ultimate']]
    
    # Content-based keywords
    content_keywords = []
    keyword_patterns = [
        r'\b(compost|composting)\b',
        r'\b(organic matter)\b',
        r'\b(soil amendment|soil health)\b',
        r'\b(beneficial microorganisms|microbes)\b',
        r'\b(worm castings?)\b',
        r'\b(natural fertilizer|organic fertilizer)\b'
    ]
    
    for pattern in keyword_patterns:
        matches = re.findall(pattern, content.lower())
        content_keywords.extend(matches)
    
    # Combine all keywords
    all_keywords = base_keywords + title_keywords[:3] + list(set(content_keywords))[:3]
    return ', '.join(all_keywords[:8])

def get_enhanced_fallback_blog(title, seasonal_context):
    """Enhanced fallback blog with proper formatting and images"""
    season = seasonal_context.get('season', 'spring')
    
    content = f"""<h1>{title}</h1>

<div class="blog-image hero-image">
    <img src="/images/placeholder-landscape.jpg" alt="{title} - {season} gardening guide" loading="lazy" />
    <p class="image-caption">📸 Suggested: Wide shot of thriving {season} garden with healthy soil and vibrant plants</p>
</div>

<p>Welcome to the ultimate guide for <strong>{title.lower()}</strong>! As experienced gardeners know, success in {season} gardening comes from understanding both the science and art of working with nature's seasonal rhythms and soil biology.</p>

<p>Whether you're a seasoned gardener or just beginning your {season} gardening journey, this comprehensive guide will provide you with proven strategies, expert insights, and practical techniques that make the difference between a struggling garden and a thriving ecosystem that produces abundant, nutritious harvests.</p>

<h2>Understanding {season.title()} Garden Fundamentals</h2>

<div class="blog-image section-image">
    <img src="/images/placeholder-close-up.jpg" alt="Healthy organic garden soil with rich texture" loading="lazy" />
    <p class="image-caption">📸 Suggested: Close-up of rich, dark soil showing organic matter and beneficial microorganisms</p>
</div>

<p>Every season presents unique opportunities and challenges for gardeners. During {season}, your plants have specific environmental needs that must be met for optimal growth, health, and productivity. <em>Understanding these requirements is the foundation of gardening success.</em></p>

<p><strong>Key considerations for {season} gardening include:</strong></p>

<ul>
<li><strong>Soil temperature and moisture management</strong> for optimal root development and nutrient uptake</li>
<li><strong>Seasonal pest and disease prevention</strong> using integrated organic methods</li>
<li><strong>Proper nutrition timing</strong> and organic fertilizer application schedules</li>
<li><strong>Weather protection strategies</strong> and microclimate creation techniques</li>
<li><strong>Harvest timing optimization</strong> for peak nutrition and flavor development</li>
</ul>

<h2>Building Living Soil: The Foundation of {season.title()} Success</h2>

<p>The secret to any thriving garden lies beneath the surface in the complex ecosystem of living soil. <strong>Healthy, biologically active soil provides the stable foundation</strong> that supports vigorous plant growth, natural pest resistance, improved nutrient density, and abundant harvests throughout the {season} growing season.</p>

<h3>Essential Components of Healthy Soil</h3>

<p>Creating truly healthy soil requires understanding and nurturing several key components that work together synergistically:</p>

<ul>
<li><strong>Beneficial Microorganisms:</strong> Billions of bacteria, fungi, and other microbes that break down organic matter, cycle nutrients, and protect plant roots from harmful pathogens</li>
<li><strong>Optimal pH Balance:</strong> Proper soil acidity/alkalinity (typically 6.0-7.0) that ensures maximum nutrient availability to plant roots</li>
<li><strong>Soil Structure:</strong> Well-aggregated soil that provides proper drainage while retaining adequate moisture and allowing easy root penetration</li>
<li><strong>Organic Matter Content:</strong> Decomposed plant and animal materials that feed soil life and dramatically improve water retention capacity</li>
</ul>

<p>Our <strong>Ancient Soil blend</strong> addresses all these essential components by combining premium worm castings, biochar, sea kelp meal, aged bat guano, and volcanic azomite to create a complete, living soil ecosystem that supports optimal plant health from the ground up.</p>

<div class="blog-image section-image">
    <img src="/images/placeholder-product-shot.jpg" alt="Elm Dirt Ancient Soil organic amendment" loading="lazy" />
    <p class="image-caption">📸 Suggested: Ancient Soil product with rich soil texture visible, showing quality and organic composition</p>
</div>

<h2>Organic {season.title()} Management Strategies</h2>

<p>Implementing proven organic gardening practices during {season} helps build long-term soil health while producing safe, nutritious food for your family. <em>These methods work with natural systems rather than against them</em>, creating sustainable abundance that improves year after year.</p>

<h3>Integrated Pest Management Approach</h3>

<p><strong>Prevention is always more effective and economical</strong> than treatment when dealing with garden pests. Healthy plants growing in nutrient-rich, biologically active soil naturally resist pest damage and disease pressure through stronger immune systems and improved cellular structure.</p>

<p>Effective organic pest prevention strategies include:</p>

<ul>
<li>Encouraging beneficial insects through diverse plantings and habitat creation</li>
<li>Using strategic companion planting to naturally repel harmful pests</li>
<li>Maintaining proper plant spacing for optimal air circulation</li>
<li>Regular monitoring and early intervention when issues first arise</li>
<li>Building soil biology that supports plant immune function</li>
</ul>

<h3>Seasonal Nutrition Management</h3>

<p>Plants have varying nutritional requirements throughout their growth cycles, and <strong>understanding when and how to provide proper nutrition</strong> ensures optimal development without waste or environmental impact. Organic fertilizers release nutrients slowly and feed soil biology, creating sustainable fertility systems.</p>

<p>Our <strong>Plant Juice</strong> provides over 250 beneficial microorganisms that work continuously to break down organic matter and make nutrients available precisely when plants need them most. This biological approach to plant nutrition creates healthier, more resilient plants that produce superior yields.</p>

<h2>Essential {season.title()} Maintenance Schedule</h2>

<div class="blog-image section-image">
    <img src="/images/placeholder-medium-shot.jpg" alt="{season.title()} garden maintenance and care" loading="lazy" />
    <p class="image-caption">📸 Suggested: Gardener performing {season} maintenance tasks in well-organized garden space</p>
</div>

<p>Consistent attention to key maintenance tasks throughout {season} ensures your garden continues to thrive and produce at its maximum potential. <em>Success comes from systematic care rather than sporadic intensive efforts.</em></p>

<p><strong>Weekly {season} garden tasks include:</strong></p>

<ul>
<li><strong>Soil Moisture Monitoring:</strong> Regular checking and adjustment of watering schedules based on weather conditions, plant growth stage, and soil moisture levels</li>
<li><strong>Systematic Garden Inspection:</strong> Thorough examination of plants for early signs of pest activity, disease symptoms, or nutritional deficiencies</li>
<li><strong>Optimal Harvesting Techniques:</strong> Timing harvests for peak nutrition and using methods that encourage continued production throughout the season</li>
<li><strong>Continuous Soil Health Improvement:</strong> Regular additions of organic matter and beneficial microorganisms to build and maintain soil life</li>
<li><strong>Strategic Season Extension Planning:</strong> Preparing for weather changes and implementing techniques to extend productive growing periods</li>
</ul>

<h2>Advanced Techniques for Maximum {season.title()} Results</h2>

<p>Once you've mastered the fundamentals, these advanced techniques can significantly improve your {season} garden's productivity, resilience, and overall performance:</p>

<h3>Succession Planting Strategy</h3>

<p><strong>Staggering plantings every 2-3 weeks</strong> ensures continuous harvests throughout {season} rather than overwhelming abundance followed by gaps in production. This technique maximizes both space utilization and harvest consistency.</p>

<h3>Strategic Companion Planting Systems</h3>

<p>Thoughtfully planned plant combinations provide mutual benefits through natural pest deterrence, efficient nutrient sharing, improved pollination, and enhanced growing conditions for all plants in the system.</p>

<h3>Soil Biology Enhancement Program</h3>

<p>Regular applications of compost tea, beneficial microorganism inoculants, and targeted organic amendments that specifically feed and support soil life create an increasingly productive growing environment.</p>

<h2>Your Path to {season.title()} Garden Success</h2>

<p><strong>Success in {season} gardening comes from understanding that healthy gardens are living ecosystems</strong> where soil organisms, plants, beneficial insects, and gardeners work together in harmonious partnership. By focusing on soil health first, implementing proven organic practices, and maintaining consistent care, you'll create a garden that not only produces abundantly this {season} but continues to improve and become more productive with each passing year.</p>

<p><em>Remember that gardening is a continuous learning journey</em> where each season brings new insights, challenges, and opportunities for growth and improvement. Start with the fundamentals of healthy soil biology, embrace organic methods that work with natural systems, and enjoy the deeply satisfying process of growing your own food naturally and sustainably.</p>

<p>The investment you make in building soil health and implementing these time-tested practices will pay dividends not just this {season}, but for many seasons to come as your garden ecosystem matures, flourishes, and becomes increasingly productive and resilient.</p>

<div class="blog-image section-image">
    <img src="/images/placeholder-harvest-shot.jpg" alt="Successful {season} garden harvest" loading="lazy" />
    <p class="image-caption">📸 Suggested: Abundant {season} harvest showing the results of healthy soil and organic gardening practices</p>
</div>"""

    # Generate enhanced fallback data
    image_suggestions = [
        {
            'position': 'hero',
            'description': f"Wide shot of thriving {season} garden with healthy soil and vibrant plants",
            'alt_text': f"{title} - {season} gardening guide",
            'style': 'landscape',
            'priority': 'high'
        },
        {
            'position': 'section_1',
            'description': "Close-up of rich, dark soil showing organic matter and beneficial microorganisms",
            'alt_text': 'Healthy organic garden soil with rich texture',
            'style': 'close-up',
            'priority': 'high'
        },
        {
            'position': 'product_mention',
            'description': "Ancient Soil product with rich soil texture visible, showing quality and organic composition",
            'alt_text': 'Elm Dirt Ancient Soil organic amendment',
            'style': 'product-shot',
            'priority': 'high'
        }
    ]
    
    schema_markup = generate_blog_schema(title, content, seasonal_context)
    
    return {
        'title': title,
        'content': content,
        'meta_description': f"Complete expert guide to {title.lower()} using proven organic methods and sustainable practices for successful {season} gardening.",
        'keywords': f"{season} gardening, organic gardening, soil health, {title.lower()}, sustainable practices, garden management",
        'schema_markup': schema_markup,
        'image_suggestions': image_suggestions,
        'word_count': len(content.split()),
        'reading_time': f"{len(content.split()) // 200 + 1} min read"
    }
    
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

@app.route('/api/test-claude')
def test_claude_api():
    """Test Claude API connection"""
    try:
        import os
        import requests
        
        api_key = os.getenv('CLAUDE_API_KEY')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'CLAUDE_API_KEY environment variable not set',
                'instructions': 'Add your API key in Render Environment settings'
            })
        
        print(f"Testing Claude API with key: {api_key[:15]}...")
        
        # Test API call
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello, API is working!' and nothing else."
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"Claude API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'api_response': result["content"][0]["text"],
                'status_code': response.status_code,
                'api_key_preview': f"{api_key[:15]}...{api_key[-10:]}" if len(api_key) > 25 else "Key format issue",
                'message': 'Claude API is working correctly!'
            })
        elif response.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'API key unauthorized',
                'status_code': response.status_code,
                'solution': 'Check your API key at https://console.anthropic.com/',
                'api_key_preview': f"{api_key[:15]}..." if len(api_key) > 15 else "Key too short"
            })
        elif response.status_code == 429:
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'status_code': response.status_code,
                'solution': 'Wait a few minutes and try again'
            })
        elif response.status_code == 400:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'status_code': response.status_code,
                'response_text': response.text,
                'solution': 'Check model name and request format'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Unexpected status code: {response.status_code}",
                'response_text': response.text,
                'api_key_preview': f"{api_key[:15]}..." if len(api_key) > 15 else "Key issue"
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'solution': 'Check the error details and try again'
        })

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
    """Generate smaller amount of content to avoid timeouts"""
    from datetime import timedelta
    
    content_pieces = []
    
    try:
        print(f"Starting LIGHT content generation for {date_str}")
        
        # Get seasonal context
        seasonal_context = get_seasonal_context(start_date)
        print(f"Seasonal context: {seasonal_context}")
        
        # Generate 1 Blog Post
        try:
            print("Generating 1 blog post...")
            blog_ideas = generate_blog_ideas_with_claude(seasonal_context, start_date)
            
            if blog_ideas and len(blog_ideas) > 0:
                # Generate just the first blog post
                blog_title = blog_ideas[0]
                full_blog = generate_blog_with_claude(blog_title, seasonal_context)
                
                content_pieces.append({
                    'title': full_blog['title'],
                    'content': full_blog['content'],
                    'meta_description': full_blog['meta_description'],
                    'keywords': full_blog['keywords'],
                    'platform': 'blog',
                    'scheduled_time': start_date.strftime('%Y-%m-%d 09:00:00')
                })
                print(f"✅ Generated 1 blog post: {full_blog['title']}")
            
        except Exception as e:
            print(f"Error generating blog post: {e}")
        
        # Generate 3 Instagram Posts
        try:
            print("Generating 3 Instagram posts...")
            instagram_posts = generate_instagram_posts_light(start_date, seasonal_context)
            content_pieces.extend(instagram_posts)
            print(f"✅ Generated {len(instagram_posts)} Instagram posts")
        except Exception as e:
            print(f"Error generating Instagram posts: {e}")
        
        # Generate 3 Facebook Posts
        try:
            print("Generating 3 Facebook posts...")
            facebook_posts = generate_facebook_posts_light(start_date, seasonal_context)
            content_pieces.extend(facebook_posts)
            print(f"✅ Generated {len(facebook_posts)} Facebook posts")
        except Exception as e:
            print(f"Error generating Facebook posts: {e}")
        
        # Generate 3 TikTok Ideas
        try:
            print("Generating 3 TikTok ideas...")
            tiktok_posts = generate_tiktok_posts_light(start_date, seasonal_context)
            content_pieces.extend(tiktok_posts)
            print(f"✅ Generated {len(tiktok_posts)} TikTok ideas")
        except Exception as e:
            print(f"Error generating TikTok posts: {e}")
        
        print(f"🎉 Total content pieces generated: {len(content_pieces)}")
        return content_pieces
        
    except Exception as e:
        print(f"Critical error in light content generation: {e}")
        return []

def generate_instagram_posts_light(start_date, seasonal_context):
    """Generate 3 Instagram posts"""
    posts = []
    season = seasonal_context.get('season', 'spring')
    
    instagram_templates = [
        f"{season.title()} garden prep time! 🌱\n\n✨ Test your soil pH\n🌿 Add organic matter\n💧 Plan your watering\n🪱 Feed the soil life\n\nWhat's first on your {season} garden list?\n\n#OrganicGardening #{season.title()}Gardening #SoilHealth #ElmDirt #GardenLife",
        
        f"Soil health secret! 🤫\n\nHealthy soil = happy plants 🌱\n\nOur Ancient Soil blend contains:\n🪱 Premium worm castings\n🔥 Activated biochar\n🌊 Sea kelp meal\n🌋 Volcanic minerals\n\nReady to transform your garden?\n\n#HealthySoil #OrganicGardening #PlantNutrition #ElmDirt",
        
        f"Garden myth busted! 🚫\n\nMyth: More fertilizer = better plants\nTruth: Living soil + balance = thriving plants 🌿\n\nFocus on feeding the soil, not just the plant!\n\n#GardenMyths #OrganicGardening #SoilLife #PlantScience #ElmDirt"
    ]
    
    for i, template in enumerate(instagram_templates):
        hour = 14 + (i * 2)  # 2pm, 4pm, 6pm
        posts.append({
            'title': f'Instagram Post {i+1} - {season.title()} Tips',
            'content': template,
            'keywords': ['OrganicGardening', f'{season.title()}Gardening', 'SoilHealth', 'ElmDirt', 'GardenLife'],
            'platform': 'instagram',
            'scheduled_time': start_date.strftime(f'%Y-%m-%d {hour:02d}:00:00')
        })
    
    return posts

def generate_facebook_posts_light(start_date, seasonal_context):
    """Generate 3 Facebook posts"""
    posts = []
    season = seasonal_context.get('season', 'spring')
    
    facebook_templates = [
        f"🌱 {season.title()} gardening question for our community: What's your biggest garden challenge this season?\n\nWhether it's soil prep, pest control, or just knowing where to start - share below and let's help each other succeed! Our gardening community is here to support you. 💚\n\nDrop your questions in the comments! 👇",
        
        f"Did you know that healthy soil contains more living organisms than there are people on Earth? 🤯\n\nJust one teaspoon of quality garden soil hosts billions of beneficial bacteria, fungi, and microorganisms working 24/7 to:\n• Break down organic matter\n• Make nutrients available to plants\n• Protect roots from harmful pathogens\n• Improve soil structure and water retention\n\nThat's why we're passionate about creating living soil with our Ancient Soil blend! What's your soil doing for your garden?",
        
        f"{season.title()} garden success tip: Start with your soil! 🌿\n\nBefore you plant a single seed, take time to:\n✅ Test your soil pH (most veggies love 6.0-7.0)\n✅ Add organic matter like compost or aged manure\n✅ Ensure good drainage\n✅ Feed the beneficial microorganisms\n\nHealthy soil = healthy plants = amazing harvests! What's your soil prep routine looking like this {season}?"
    ]
    
    for i, template in enumerate(facebook_templates):
        hour = 15 + (i * 3)  # 3pm, 6pm, 9pm
        posts.append({
            'title': f'Facebook Post {i+1} - {season.title()} Community',
            'content': template,
            'keywords': ['gardening community', f'{season} gardening', 'soil health', 'organic gardening'],
            'platform': 'facebook',
            'scheduled_time': start_date.strftime(f'%Y-%m-%d {hour:02d}:00:00')
        })
    
    return posts

def generate_tiktok_posts_light(start_date, seasonal_context):
    """Generate 3 TikTok video ideas"""
    posts = []
    season = seasonal_context.get('season', 'spring')
    
    tiktok_templates = [
        f"POV: You're learning the soil pH test that changed everything 🧪\n\n[Show pH test kit, test garden soil, dramatic reaction to results, quick fix with lime or sulfur, happy plants growing]\n\nCaption: 'When you realize your plants weren't lazy, they just had the wrong pH! #{season}Garden #SoilTest #GardeningHacks #PlantTok'",
        
        f"Ancient Soil unboxing but make it ASMR 📦✨\n\n[Slow motion opening, close-up of rich soil texture, hands running through it, satisfied 'ahh' reaction, before/after plant comparison]\n\nCaption: 'This soil hits different 🌱 #SoilASMR #GardeningTok #PlantParent #OrganicGardening #ElmDirt'",
        
        f"Garden transformation in 30 seconds! ⏰\n\n[Time-lapse: sad garden bed → adding Ancient Soil → mixing → planting → fast-forward 2 weeks of growth → thriving plants]\n\nCaption: 'The glow up your garden deserves ✨ #GardenGlowUp #BeforeAndAfter #PlantTransformation #{season}Gardening'"
    ]
    
    for i, template in enumerate(tiktok_templates):
        hour = 16 + (i * 2)  # 4pm, 6pm, 8pm
        posts.append({
            'title': f'TikTok Video Idea {i+1} - {season.title()} Content',
            'content': template,
            'keywords': ['GardeningTok', 'PlantTok', f'{season}Garden', 'ElmDirt', 'OrganicGardening'],
            'platform': 'tiktok',
            'scheduled_time': start_date.strftime(f'%Y-%m-%d {hour:02d}:00:00')
        })
    
    return posts

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
    """Generate 6 blog ideas using Claude AI - FIXED VERSION"""
    
    prompt = f"""You are an expert content writer for Elm Dirt, an organic gardening soil company. Generate exactly 6 blog article titles.

CONTEXT:
- Current season: {seasonal_context['season']}
- Month: {seasonal_context['month']} 
- Date: {seasonal_context['date']}
- Holidays/Events: {', '.join(seasonal_context['holidays']) if seasonal_context['holidays'] else 'None'}

BRAND INFO:
- Company: Elm Dirt
- Products: Ancient Soil, Plant Juice, Bloom Juice
- Target audience: Home gardeners aged 35-65

REQUIREMENTS:
- Generate exactly 6 blog article titles
- Focus on {seasonal_context['season']} gardening tasks
- Make titles SEO-friendly and engaging
- Include seasonal plant care and soil health topics
- Each title should be 8-12 words long

FORMAT: Return only the titles, numbered 1-6, one per line.

Example:
1. Spring Garden Soil Preparation: Complete Guide for Success
2. Organic Pest Control Methods for Spring Gardens
3. Best Spring Vegetables to Plant in Small Gardens

Generate 6 titles for {seasonal_context['season']} gardening:"""

    try:
        # Call the ACTUAL Claude API (not recursive!)
        blog_ideas_response = make_direct_claude_call(prompt)
        blog_ideas = parse_blog_ideas(blog_ideas_response)
        print(f"Generated {len(blog_ideas)} blog ideas")
        return blog_ideas
        
    except Exception as e:
        print(f"Error generating blog ideas: {e}")
        return get_fallback_blog_titles(seasonal_context)

def generate_blog_with_claude(blog_title, seasonal_context):
    """Generate full blog post using Claude AI - FIXED VERSION"""
    
    prompt = f"""Generate an SEO-optimized blog article for the title '{blog_title}'

CONTEXT:
- Season: {seasonal_context['season']}
- Month: {seasonal_context['month']}
- Brand: Elm Dirt (organic soil amendments and gardening products)
- Target audience: Home gardeners aged 35-65

REQUIREMENTS:
- Write 1000-1500 words minimum
- Include H2 and H3 HTML subheadings
- Use engaging, expert but approachable tone
- Include practical, actionable advice
- Naturally mention Elm Dirt products where relevant:
  * Ancient Soil: Premium soil amendment with worm castings, biochar, kelp
  * Plant Juice: Liquid fertilizer with 250+ beneficial microorganisms
  * Bloom Juice: Specialized fertilizer for flowering plants
- Focus on organic, sustainable gardening methods
- Include seasonal considerations for {seasonal_context['season']}
- Use proper HTML formatting (h2, h3, p, ul, li tags)

STRUCTURE:
- Introduction explaining importance of topic
- 3-4 main sections with H2 headings
- Subsections with H3 headings
- Practical tips and step-by-step instructions
- Conclusion with key takeaways

Write the complete article with HTML formatting:"""

    try:
        # Call the ACTUAL Claude API (not recursive!)
        blog_response = make_direct_claude_call(prompt)
        parsed_blog = parse_blog_response(blog_response, blog_title, seasonal_context)
        print(f"Generated blog length: {len(blog_response)} characters")
        return parsed_blog
        
    except Exception as e:
        print(f"Error generating blog: {e}")
        return get_fallback_blog_content(blog_title, seasonal_context)

def make_direct_claude_call(prompt):
    """Direct Claude API call - WORKING VERSION based on successful test"""
    try:
        import os
        import requests
        
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            print("ERROR: CLAUDE_API_KEY not found")
            return None
        
        print(f"Making Claude API call for content generation...")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000,  # Increased for longer blog posts
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"Claude API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["content"][0]["text"]
            print(f"✅ SUCCESS: Generated {len(content)} characters")
            return content
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error in make_direct_claude_call: {e}")
        return None

def parse_blog_ideas(claude_response):
    """Parse Claude response to extract blog titles - IMPROVED"""
    try:
        lines = claude_response.strip().split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            # Look for numbered lines
            if line and any(line.startswith(f'{i}.') for i in range(1, 7)):
                # Clean up the title
                title = line
                for i in range(1, 7):
                    title = title.replace(f'{i}.', '').strip()
                
                if title and len(title) > 10:
                    titles.append(title)
        
        print(f"Parsed {len(titles)} titles from Claude response")
        
        # Ensure we have exactly 6 titles
        if len(titles) < 6:
            fallback = get_fallback_blog_titles(get_seasonal_context(datetime.now()))
            titles.extend(fallback[len(titles):6])
        
        return titles[:6]
        
    except Exception as e:
        print(f"Error parsing blog ideas: {e}")
        return get_fallback_blog_titles(get_seasonal_context(datetime.now()))

def parse_blog_response(claude_response, original_title, seasonal_context):
    """Parse Claude blog response into structured format - IMPROVED"""
    try:
        content = claude_response.strip()
        
        # Check if content is substantial
        if len(content) < 800:
            print(f"Blog content too short ({len(content)} chars), using fallback")
            return get_fallback_blog_content(original_title, seasonal_context)
        
        # Generate meta description
        # Try to extract first paragraph
        if '<p>' in content:
            first_p_start = content.find('<p>') + 3
            first_p_end = content.find('</p>')
            if first_p_end > first_p_start:
                first_paragraph = content[first_p_start:first_p_end].strip()
                if len(first_paragraph) > 160:
                    meta_description = first_paragraph[:157] + "..."
                else:
                    meta_description = first_paragraph
            else:
                meta_description = f"Expert guide to {original_title.lower()} with organic methods for {seasonal_context['season']} gardening."
        else:
            meta_description = f"Expert guide to {original_title.lower()} with organic methods for {seasonal_context['season']} gardening."
        
        # Extract keywords
        keywords = extract_keywords_from_content(original_title, content, seasonal_context)
        
        return {
            'title': original_title,
            'content': content,
            'meta_description': meta_description,
            'keywords': keywords
        }
        
    except Exception as e:
        print(f"Error parsing blog response: {e}")
        return get_fallback_blog_content(original_title, seasonal_context)

def get_fallback_blog_titles(seasonal_context):
    """Fallback blog titles when Claude fails"""
    season = seasonal_context.get('season', 'spring')
    
    titles = {
        'spring': [
            "Spring Garden Soil Preparation: Complete Success Guide",
            "Organic Spring Pest Control Methods That Work",
            "Best Spring Vegetables for Beginning Gardeners",
            "Creating Living Soil: Transform Your Garden Naturally",
            "Spring Composting: Turn Scraps into Garden Gold",
            "Natural Spring Fertilizers for Healthy Plant Growth"
        ],
        'summer': [
            "Summer Garden Watering: Smart Strategies for Hot Weather",
            "Organic Summer Pest Management Without Chemicals",
            "Heat-Tolerant Vegetables: Best Summer Garden Crops",
            "Maintaining Healthy Soil During Hot Summer Months",
            "Summer Companion Planting for Garden Success",
            "Natural Ways to Keep Summer Gardens Thriving"
        ],
        'fall': [
            "Fall Garden Cleanup: Preparing Soil for Winter",
            "Fall Planting Guide: Cool Weather Crop Success",
            "Composting Fall Leaves: Building Next Year's Soil",
            "Winter Garden Prep: Protecting Plants and Soil",
            "Fall Soil Amendment: Perfect Time for Improvements",
            "Extending Growing Season: Fall Gardening Techniques"
        ],
        'winter': [
            "Winter Soil Health: Maintaining Garden Soil",
            "Indoor Gardening: Fresh Food All Winter Long",
            "Planning Next Year's Garden: Winter Design Tips",
            "Winter Composting: Active Compost in Cold Weather",
            "Protecting Garden Soil: Winter Cover Strategies",
            "Winter Garden Projects: Preparing for Spring"
        ]
    }
    
    return titles.get(season, titles['spring'])

def get_fallback_blog_content(title, seasonal_context):
    """Generate substantial fallback blog content"""
    season = seasonal_context.get('season', 'spring')
    
    content = f"""<h2>{title}</h2>

<p>Welcome to your comprehensive guide for {title.lower()}! As experienced gardeners know, success in {season} gardening comes from understanding both the science and art of working with nature's rhythms.</p>

<p>Whether you're a seasoned gardener or just beginning your {season} gardening journey, this guide will provide you with proven strategies, expert insights, and practical techniques that make the difference between a struggling garden and a thriving ecosystem that produces abundant, healthy harvests.</p>

<h3>Understanding {season.title()} Garden Fundamentals</h3>

<p>Every season presents unique opportunities and challenges for gardeners. During {season}, your plants have specific environmental needs that must be met for optimal growth, health, and productivity. Understanding these requirements is the first step toward gardening success.</p>

<p>Key considerations for {season} gardening include:</p>

<ul>
<li>Soil temperature and moisture management for optimal root development</li>
<li>Seasonal pest and disease prevention strategies</li>
<li>Proper nutrition timing and organic fertilizer application</li>
<li>Weather protection and microclimate creation techniques</li>
<li>Harvest timing for peak nutrition and flavor</li>
</ul>

<h3>Building the Foundation: Healthy Soil for {season.title()} Success</h3>

<p>The secret to any thriving garden lies beneath the surface in the complex ecosystem of living soil. Healthy, biologically active soil provides the stable foundation that supports vigorous plant growth, natural pest resistance, improved nutrient density, and abundant harvests throughout the {season} growing season.</p>

<h4>Essential Components of Living Soil</h4>

<p>Creating truly healthy soil requires understanding and nurturing several key components that work together:</p>

<ul>
<li><strong>Beneficial Microorganisms:</strong> Billions of bacteria, fungi, and other microbes that break down organic matter, cycle nutrients, and protect plant roots from pathogens</li>
<li><strong>Optimal pH Balance:</strong> Proper soil acidity/alkalinity (typically 6.0-7.0) that ensures maximum nutrient availability to plant roots</li>
<li><strong>Soil Structure:</strong> Well-aggregated soil that provides proper drainage while retaining adequate moisture and allowing root penetration</li>
<li><strong>Organic Matter:</strong> Decomposed plant and animal materials that feed soil life and improve water retention</li>
</ul>

<p>Our Ancient Soil blend addresses all these essential components by combining premium worm castings, biochar, sea kelp meal, aged bat guano, and volcanic azomite to create a complete, living soil ecosystem that supports plant health from the ground up.</p>

<h3>Organic {season.title()} Management Strategies</h3>

<p>Implementing proven organic gardening practices during {season} helps build long-term soil health while producing safe, nutritious food for your family. These methods work with natural systems rather than against them, creating sustainable abundance.</p>

<h4>Integrated Pest Management</h4>

<p>Prevention is always more effective and economical than treatment when dealing with garden pests. Healthy plants growing in nutrient-rich, biologically active soil naturally resist pest damage and disease pressure through stronger immune systems and improved cellular structure.</p>

<p>Effective organic pest prevention strategies include:</p>

<ul>
<li>Encouraging beneficial insects through diverse plantings and habitat creation</li>
<li>Using companion planting to naturally repel harmful pests</li>
<li>Maintaining proper plant spacing for good air circulation</li>
<li>Regular monitoring and early intervention when issues arise</li>
</ul>

<h4>Seasonal Nutrition Management</h4>

<p>Plants have varying nutritional requirements throughout their growth cycles, and understanding when and how to provide proper nutrition ensures optimal development without waste or environmental impact. Organic fertilizers release nutrients slowly and feed soil biology, creating sustainable fertility.</p>

<p>Our Plant Juice provides over 250 beneficial microorganisms that work continuously to break down organic matter and make nutrients available precisely when plants need them most. This biological approach to plant nutrition creates healthier, more resilient plants that produce better yields.</p>

<h3>Essential {season.title()} Maintenance Tasks</h3>

<p>Consistent attention to key maintenance tasks throughout {season} ensures your garden continues to thrive and produce at its maximum potential:</p>

<ul>
<li><strong>Soil Moisture Monitoring:</strong> Regular checking and adjustment of watering schedules based on weather, plant needs, and soil conditions</li>
<li><strong>Weekly Garden Inspection:</strong> Systematic examination of plants for early signs of pest, disease, or nutritional issues</li>
<li><strong>Proper Harvesting Techniques:</strong> Timing harvests for peak nutrition and using methods that encourage continued production</li>
<li><strong>Ongoing Soil Health Improvement:</strong> Regular additions of organic matter and beneficial microorganisms to build soil life</li>
<li><strong>Season Extension Planning:</strong> Preparing for weather changes and extending productive growing periods</li>
</ul>

<h3>Advanced {season.title()} Techniques for Maximum Results</h3>

<p>Once you've mastered the fundamentals, these advanced techniques can significantly improve your {season} garden's productivity and resilience:</p>

<h4>Succession Planting</h4>

<p>Staggering plantings every 2-3 weeks ensures continuous harvests throughout {season} rather than overwhelming abundance followed by gaps in production.</p>

<h4>Companion Planting Systems</h4>

<p>Strategic plant combinations that provide mutual benefits through pest deterrence, nutrient sharing, and improved growing conditions.</p>

<h4>Soil Biology Enhancement</h4>

<p>Regular applications of compost tea, beneficial microorganisms, and organic amendments that specifically feed and support soil life.</p>

<h3>Conclusion: Your Path to {season.title()} Garden Success</h3>

<p>Success in {season} gardening comes from understanding that healthy gardens are living ecosystems where soil, plants, beneficial insects, and gardeners work together in harmony. By focusing on soil health, implementing organic practices, and maintaining consistent care, you'll create a garden that not only produces abundantly this {season} but continues to improve and become more productive year after year.</p>

<p>Remember that gardening is a continuous learning journey where each season brings new insights and opportunities for improvement. Start with the fundamentals of healthy soil, embrace organic methods that work with nature, and enjoy the deeply satisfying process of growing your own food naturally and sustainably.</p>

<p>The investment you make in building soil health and implementing these practices will pay dividends not just this {season}, but for many seasons to come as your garden ecosystem matures and flourishes.</p>"""

    return {
        'title': title,
        'content': content,
        'meta_description': f"Complete expert guide to {title.lower()} using proven organic methods and sustainable practices for successful {season} gardening.",
        'keywords': f"{season} gardening, organic gardening, soil health, {title.lower()}, sustainable practices, garden management"
    }

def extract_keywords_from_content(title, content, seasonal_context):
    """Extract SEO keywords from title and content"""
    import re
    
    season = seasonal_context.get('season', 'spring')
    
    # Base keywords
    base_keywords = [f"{season} gardening", "organic gardening", "soil health"]
    
    # Extract from title
    title_words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
    title_keywords = [word for word in title_words if word not in ['garden', 'gardening', 'guide', 'complete', 'best']]
    
    # Combine
    all_keywords = base_keywords + title_keywords[:3]
    return ', '.join(all_keywords[:6])

# Remove the old recursive function completely
# DELETE THIS FUNCTION if it exists:
# def call_claude_api(prompt):

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
    """Connect to Claude API for content generation"""
    try:
        # Replace YOUR_API_KEY with your actual Claude API key
        import requests
        import os
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": os.getenv('CLAUDE_API_KEY'),  # Make sure this environment variable is set
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-5-sonnet-20241022",  # Updated model
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
            return generate_fallback_content_simple(prompt)
            
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return generate_fallback_content_simple(prompt)

def generate_fallback_content_simple(prompt):
    """Simple fallback content when Claude API fails"""
    if "blog article" in prompt.lower():
        return """<h2>Expert Garden Care Guide</h2>
<p>Creating a successful garden starts with understanding the fundamentals of soil health and plant nutrition.</p>
<h3>Essential Garden Practices</h3>
<p>Healthy soil is the foundation of any thriving garden. By focusing on organic amendments and beneficial microorganisms, you can create an environment where plants naturally flourish.</p>
<ul>
<li>Test soil pH regularly for optimal plant nutrition</li>
<li>Add organic matter to improve soil structure</li>
<li>Use beneficial microorganisms to enhance nutrient availability</li>
<li>Practice sustainable watering techniques</li>
</ul>
<p>Our Ancient Soil blend provides these essential components, creating the perfect foundation for your garden's success.</p>"""
    
    elif "blog ideas" in prompt.lower():
        return """1. Spring Garden Soil Preparation Complete Guide
2. Organic Pest Control Methods That Actually Work  
3. Best Vegetables for Beginning Gardeners
4. Creating Living Soil with Natural Amendments
5. Companion Planting for Garden Success
6. Natural Fertilizers vs Synthetic Options"""
    
    else:
        return "Quality gardening content generated for your organic garden success."

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
    return '''
    <div class="section">
        <h2>📋 Export Daily Content</h2>
        <p>Get a focused set of content for your selected date:</p>
        <ul>
            <li>📝 <strong>1 Blog Post</strong> - Full SEO-optimized article</li>
            <li>📱 <strong>3 Instagram Posts</strong> - Ready-to-post content with hashtags</li>
            <li>👥 <strong>3 Facebook Posts</strong> - Community-focused content</li>
            <li>🎵 <strong>3 TikTok Ideas</strong> - Video concepts with descriptions</li>
        </ul>
        <p><strong>Total: 10 pieces of content</strong> - Perfect for daily management!</p>
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
    
                if (!dateStr) {
                    showError('Please select a date first');
                    return;
                }
    
                const selectedDate = new Date(dateStr + 'T12:00:00');
                const dayOfWeek = selectedDate.getDay();
    
                showLoading(true);
                hideError();
    
                const isWeekly = dayOfWeek === 1;
                const exportType = isWeekly ? 'weekly' : 'daily';
    
                console.log('Starting export:', {
                    date: dateStr,
                    dayOfWeek: dayOfWeek,
                    exportType: exportType
                });
             
            
                
                 // Call content generation API
    fetch('/api/generate-content', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            date: dateStr,
            type: exportType,
            day_of_week: dayOfWeek
        })
    })
    .then(response => {
        console.log('Generate content response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    })
    .then(data => {
        console.log('Content generation response:', data);
        
        if (!data) {
            throw new Error('No data received from server');
        }
        
        if (!data.success) {
            throw new Error(data.error || 'Content generation failed');
        }
        
        if (!data.content_pieces || !Array.isArray(data.content_pieces)) {
            throw new Error('Invalid content pieces received');
        }
        
        console.log(`Received ${data.content_pieces.length} content pieces`);

        // Open copy-paste interface
        return fetch('/api/export/copy-paste', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                content_pieces: data.content_pieces,
                week_id: data.week_id || dateStr,
                export_type: exportType
            })
        });
    })
    .then(response => {
        console.log('Export interface response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Export interface error: HTTP ${response.status}`);
        }
        
        return response.text();
    })
    .then(html => {
        console.log('Received HTML response, opening window...');
        showLoading(false);
        
        if (!html || html.trim().length === 0) {
            throw new Error('Empty HTML response received');
        }
        
        // Open the copy-paste interface
        const newWindow = window.open('', '_blank', 'width=1400,height=800,scrollbars=yes,resizable=yes');
        
        if (!newWindow) {
            throw new Error('Failed to open new window - popup blocker may be active');
        }
        
        newWindow.document.write(html);
        newWindow.document.close();
        
        console.log('Successfully opened copy-paste interface');
    })
    .catch(error => {
        console.error('Export error:', error);
        showLoading(false);
        showError('Error generating content: ' + error.message);
        
        // Additional debugging info
        console.log('Full error details:', {
            error: error,
            stack: error.stack,
            message: error.message
        });
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
