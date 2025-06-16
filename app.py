# Enhanced Elm Dirt Content Automation Platform
# Complete and ready for Railway deployment

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import anthropic
import requests
import json
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Tuple
import re
import logging
import sqlite3
from dataclasses import dataclass
from enum import Enum
import uuid
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    # Claude API (Primary)
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your_claude_api_key')
    
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
    
    # US Gardening Seasons and Topics
    SEASONAL_TOPICS = {
        'spring': [
            'seed starting', 'soil preparation', 'transplanting', 'organic fertilizer', 
            'spring planting', 'garden cleanup', 'compost preparation', 'frost protection',
            'early vegetables', 'soil testing', 'pruning', 'mulching'
        ],
        'summer': [
            'watering tips', 'pest control', 'heat stress', 'bloom boost', 
            'summer maintenance', 'harvesting', 'drought protection', 'companion planting',
            'disease prevention', 'container gardening', 'succession planting'
        ],
        'fall': [
            'harvest time', 'composting', 'winter prep', 'soil amendment', 
            'fall cleanup', 'planning next year', 'leaf composting', 'cover crops',
            'bulb planting', 'tree care', 'winterizing', 'seed saving'
        ],
        'winter': [
            'indoor plants', 'planning garden', 'houseplant care', 'seed catalogs', 
            'winter protection', 'tool maintenance', 'greenhouse management', 'forcing bulbs',
            'microgreens', 'herb gardening indoors', 'garden reflection'
        ]
    }
    
    # US Gardening Holidays and Special Dates
    GARDENING_HOLIDAYS = {
        # Format: (month, day): ('holiday_name', 'gardening_focus', 'content_theme')
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
        
        # Content pieces table
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
        
        # Weekly content packages
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
            ai_provider=row[10] or "claude",
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            week_id=row[13],
            holiday_context=row[14],
            meta_description=row[15] if len(row) > 15 else None
        )

class HolidayManager:
    def __init__(self):
        self.config = Config()
    
    def get_week_holidays(self, start_date: datetime) -> List[Tuple[datetime, str, str, str]]:
        """Get holidays and special gardening dates for a specific week"""
        holidays = []
        week_end = start_date + timedelta(days=6)
        
        # Check each day of the week for holidays
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
            # If there's a holiday, make it the primary theme
            primary_holiday = holidays[0]
            return primary_holiday[3]  # content_theme
        else:
            # Use seasonal themes based on specific weeks
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
            
            # Choose theme based on week of season
            week_of_year = start_date.isocalendar()[1]
            theme_index = (week_of_year % 4)
            return seasonal_themes[season][theme_index]

class ContentGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.config = Config()
        self.db_manager = db_manager
        self.holiday_manager = HolidayManager()
        
        # Initialize Claude client
        if self.config.CLAUDE_API_KEY and self.config.CLAUDE_API_KEY != 'your_claude_api_key':
            self.claude_client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
        else:
            self.claude_client = None
            logger.warning("Claude API key not configured - using fallback content generation")
    
    def generate_weekly_content(self, week_start_date: datetime) -> Dict:
        """Generate a complete week of content with holiday awareness"""
        try:
            week_id = f"week_{week_start_date.strftime('%Y_%m_%d')}"
            season = self.holiday_manager.get_seasonal_focus(week_start_date)
            holidays = self.holiday_manager.get_week_holidays(week_start_date)
            theme = self.holiday_manager.get_week_theme(week_start_date)
            
            logger.info(f"Generating weekly content for {week_start_date.strftime('%Y-%m-%d')} with theme: {theme}")
            
            # Generate content for the week
            weekly_content = []
            
            # Generate 1 blog post per week (usually on Monday)
            blog_post = self._generate_weekly_blog_post(
                week_start_date=week_start_date,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=week_id
            )
            weekly_content.append(blog_post)
            
            # Generate social media content for the week
            social_content = self._generate_weekly_social_content(
                blog_post=blog_post,
                week_start_date=week_start_date,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=week_id
            )
            weekly_content.extend(social_content)
            
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
                'content': [self._content_piece_to_dict(cp) for cp in weekly_content]
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_weekly_blog_post(self, week_start_date: datetime, season: str, 
                                  theme: str, holidays: List, week_id: str) -> ContentPiece:
        """Generate the main blog post for the week"""
        
        # Determine content focus
        if holidays:
            primary_holiday = holidays[0]
            content_focus = f"{primary_holiday[1]} - {primary_holiday[2]}"
            keywords = self._get_holiday_keywords(primary_holiday[1], season)
            title = self._generate_holiday_title(primary_holiday, season, week_start_date)
        else:
            content_focus = f"{season} gardening"
            keywords = self._get_seasonal_keywords(season)
            title = self._generate_seasonal_title(season, theme, week_start_date)
        
        return self._generate_blog_post(
            title=title,
            keywords=keywords,
            seasonal_focus=season,
            holiday_context=content_focus,
            date=week_start_date,
            week_id=week_id,
            theme=theme
        )
    
    def _generate_weekly_social_content(self, blog_post: ContentPiece, 
                                       week_start_date: datetime, season: str, 
                                       theme: str, holidays: List, week_id: str) -> List[ContentPiece]:
        """Generate social media content for the week"""
        social_content = []
        
        # Define posting schedule for the week
        posting_schedule = [
            (0, 'instagram', 2),  # Monday - 2 Instagram posts
            (1, 'facebook', 2),   # Tuesday - 2 Facebook posts
            (2, 'instagram', 1),  # Wednesday - 1 Instagram post
            (3, 'linkedin', 1),   # Thursday - 1 LinkedIn post
            (4, 'facebook', 1),   # Friday - 1 Facebook post
            (5, 'tiktok', 1),     # Saturday - 1 TikTok post
        ]
        
        for day_offset, platform, count in posting_schedule:
            post_date = week_start_date + timedelta(days=day_offset)
            
            social_posts = self._generate_social_posts(
                blog_post=blog_post,
                platform=platform,
                count=count,
                date=post_date,
                holiday_context=blog_post.holiday_context or f"{season} gardening",
                week_id=week_id
            )
            social_content.extend(social_posts)
        
        return social_content
    
    def _generate_blog_post(self, title: str, keywords: List[str], seasonal_focus: str,
                           holiday_context: str, date: datetime, week_id: str, theme: str) -> ContentPiece:
        """Generate a single blog post with enhanced prompting"""
        
        prompt = f"""
        Generate an SEO-optimized blog article for Elm Dirt's organic gardening ecommerce store.

        ARTICLE DETAILS:
        Title: "{title}"
        Publication Date: {date.strftime('%B %d, %Y')} ({date.strftime('%A')})
        Season: {seasonal_focus}
        Theme: {theme}
        Context: {holiday_context}

        TARGET AUDIENCE: 50+ year old home gardeners across the US
        BRAND VOICE: Friendly, knowledgeable gardening neighbor sharing practical wisdom
        WORD COUNT: 800-1000 words
        PRIMARY KEYWORDS: {', '.join(keywords[:3])}

        ELM DIRT PRODUCTS TO REFERENCE NATURALLY:
        - Ancient Soil (premium worm castings and organic blend)
        - Plant Juice (liquid organic fertilizer with microbes)
        - Bloom Juice (flowering and fruiting plant booster)
        - Worm Castings (pure organic soil amendment)
        - All-Purpose Soil Mix (complete potting solution)

        CONTENT REQUIREMENTS:
        - Write conversationally like talking to a gardening friend
        - Include practical, actionable advice for the current season/date
        - Reference seasonal timing and current gardening tasks
        - Weave in holiday context naturally if applicable
        - Include specific tips that 50+ gardeners will appreciate
        - Mention regional considerations for US gardeners
        - End with clear call-to-action to visit Elm Dirt

        STRUCTURE:
        1. H1: {title}
        2. Introduction acknowledging current timing/season (100-150 words)
        3. H2: Main seasonal focus with practical tips
        4. H2: Problem-solving section with Elm Dirt solutions
        5. H2: Action steps for this time period
        6. Conclusion with encouragement and CTA

        SEO REQUIREMENTS:
        - Primary keyword density: 1-2%
        - Include semantic variations naturally
        - Write a compelling meta description (150-160 characters)
        - Use proper heading hierarchy

        OUTPUT: Clean HTML with proper heading tags, ready for Shopify blog.
        """
        
        try:
            content_html = ""
            meta_description = ""
            
            if self.claude_client:
                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.7,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                full_response = response.content[0].text
                
                # Extract meta description if present
                meta_match = re.search(r'<meta name="description" content="(.*?)"', full_response, re.IGNORECASE)
                if meta_match:
                    meta_description = meta_match.group(1)
                
                # Clean up the content
                content_html = full_response
                
            else:
                content_html = self._generate_fallback_blog(title, keywords, seasonal_focus, holiday_context)
                meta_description = f"Expert {seasonal_focus} gardening advice from Elm Dirt. Learn organic methods for {holiday_context}."
            
            # Create ContentPiece object
            content_piece = ContentPiece(
                id=str(uuid.uuid4()),
                title=title,
                content=content_html,
                platform="blog",
                content_type="blog_post",
                status=ContentStatus.DRAFT,
                scheduled_time=date.replace(hour=9, minute=0, second=0),
                keywords=keywords,
                hashtags=[],
                image_suggestion=f"Seasonal {seasonal_focus} garden photo showcasing organic gardening methods",
                ai_provider="claude" if self.claude_client else "fallback",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                week_id=week_id,
                holiday_context=holiday_context,
                meta_description=meta_description
            )
            
            # Save to database
            self.db_manager.save_content_piece(content_piece)
            return content_piece
            
        except Exception as e:
            logger.error(f"Error generating blog post: {str(e)}")
            return self._create_fallback_blog_content(title, keywords, date, week_id, holiday_context)
    
    def _generate_social_posts(self, blog_post: ContentPiece, platform: str, count: int,
                              date: datetime, holiday_context: str, week_id: str) -> List[ContentPiece]:
        """Generate social media posts for a platform"""
        
        platform_specs = {
            'instagram': {
                'max_length': 2200, 
                'tone': 'visual and engaging with storytelling', 
                'optimal_hours': [11, 15, 19],
                'hashtag_count': 15
            },
            'facebook': {
                'max_length': 500, 
                'tone': 'community-focused and conversational', 
                'optimal_hours': [12, 15, 18],
                'hashtag_count': 5
            },
            'tiktok': {
                'max_length': 150, 
                'tone': 'quick tips and trendy', 
                'optimal_hours': [14, 17, 20],
                'hashtag_count': 8
            },
            'linkedin': {
                'max_length': 1300, 
                'tone': 'professional B2B gardening insights', 
                'optimal_hours': [9, 12, 17],
                'hashtag_count': 3
            }
        }
        
        specs = platform_specs.get(platform, platform_specs['instagram'])
        
        social_posts = []
        
        # Create fallback posts if Claude API not available
        for i in range(count):
            # Calculate posting time using optimal hours
            optimal_hours = specs['optimal_hours']
            hour = optimal_hours[i % len(optimal_hours)]
            post_time = date.replace(hour=hour, minute=0, second=0)
            
            # Generate content based on platform
            post_content = self._create_fallback_social_post(platform, blog_post, holiday_context)
            
            content_piece = ContentPiece(
                id=str(uuid.uuid4()),
                title=f"{platform.title()} Post {i+1} - {post_content['post_type']}",
                content=post_content['content'],
                platform=platform,
                content_type=f"{platform}_post",
                status=ContentStatus.DRAFT,
                scheduled_time=post_time,
                keywords=blog_post.keywords,
                hashtags=post_content['hashtags'],
                image_suggestion=post_content['image_suggestion'],
                ai_provider="fallback",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                week_id=week_id,
                holiday_context=holiday_context
            )
            
            self.db_manager.save_content_piece(content_piece)
            social_posts.append(content_piece)
        
        return social_posts
    
    def _generate_holiday_title(self, holiday: Tuple, season: str, date: datetime) -> str:
        """Generate holiday-specific title"""
        holiday_date, holiday_name, gardening_focus, content_theme = holiday
        
        holiday_title_templates = {
            'Valentine\'s Day': f"Valentine's Day Garden Love: Show Your Plants Some Appreciation",
            'St. Patrick\'s Day': f"Going Green for St. Patrick's Day: Organic Garden Success",
            'Spring Equinox': f"Spring Equinox Garden Awakening: Essential Soil Preparation Tips",
            'Earth Day': f"Earth Day Gardening: Sustainable Organic Methods That Work",
            'May Day': f"May Day Garden Celebration: Spring Planting Success Guide",
            'Mother\'s Day Week': f"Mother's Day Garden Gifts: Creating Beautiful Plant Displays",
            'Memorial Day': f"Memorial Day Weekend: Summer Garden Prep Made Easy",
            'Summer Solstice': f"Summer Solstice Garden Care: Peak Season Plant Nutrition",
            'Independence Day': f"July 4th Garden Display: Patriotic Plants and Summer Care",
            'National Relaxation Day': f"Creating Your Garden Sanctuary: Peaceful Outdoor Spaces",
            'Fall Equinox': f"Fall Equinox Harvest: Preparing Your Garden for Winter Success",
            'Halloween': f"Halloween Garden Magic: Fall Cleanup and Seasonal Decorations",
            'Veterans Day': f"Honoring Through Gardens: Creating Meaningful Memorial Spaces",
            'Thanksgiving Week': f"Thanksgiving Garden Gratitude: Celebrating This Year's Harvest",
            'Winter Solstice': f"Winter Solstice Garden Dreams: Planning for Next Year's Success"
        }
        
        return holiday_title_templates.get(holiday_name, 
            f"{holiday_name} Garden Guide: {content_theme} Tips for {season.title()}")
    
    def _generate_seasonal_title(self, season: str, theme: str, date: datetime) -> str:
        """Generate seasonal title when no holiday is present"""
        month_name = date.strftime('%B')
        
        seasonal_templates = {
            'spring': [
                f"{month_name} Spring Garden Success: Essential Organic Methods",
                f"Spring Garden Awakening: {month_name} Soil Preparation Guide",
                f"{month_name} Planting Success: Organic Garden Foundation Tips"
            ],
            'summer': [
                f"{month_name} Summer Garden Care: Beat the Heat Naturally",
                f"Summer Growing Success: {month_name} Plant Nutrition Guide",
                f"{month_name} Garden Maintenance: Organic Summer Care Tips"
            ],
            'fall': [
                f"{month_name} Fall Garden Tasks: Preparing for Winter Success",
                f"Fall Harvest Guide: {month_name} Garden Celebration",
                f"{month_name} Garden Preparation: Fall to Winter Transition"
            ],
            'winter': [
                f"{month_name} Indoor Garden Success: Winter Growing Tips",
                f"Winter Garden Planning: {month_name} Preparation Guide",
                f"{month_name} Garden Dreams: Planning Next Year's Success"
            ]
        }
        
        templates = seasonal_templates.get(season, seasonal_templates['spring'])
        return random.choice(templates)
    
    def _get_holiday_keywords(self, holiday_name: str, season: str) -> List[str]:
        """Get relevant keywords for holiday content"""
        base_keywords = self.config.TARGET_KEYWORDS[:3]
        
        holiday_keywords = {
            'Valentine\'s Day': ['flowering plants', 'plant gifts', 'garden love'] + base_keywords,
            'St. Patrick\'s Day': ['green plants', 'organic gardening', 'plant health'] + base_keywords,
            'Spring Equinox': ['spring gardening', 'soil preparation', 'garden awakening'] + base_keywords,
            'Earth Day': ['sustainable gardening', 'organic methods', 'eco-friendly'] + base_keywords,
            'May Day': ['spring planting', 'garden celebration', 'plant growth'] + base_keywords,
            'Mother\'s Day Week': ['garden gifts', 'plant care', 'flowering plants'] + base_keywords,
            'Memorial Day': ['summer preparation', 'garden maintenance', 'plant nutrition'] + base_keywords,
            'Summer Solstice': ['summer care', 'peak season', 'plant nutrition'] + base_keywords,
            'Independence Day': ['summer maintenance', 'patriotic plants', 'garden display'] + base_keywords,
            'National Relaxation Day': ['peaceful gardens', 'garden sanctuary', 'relaxing spaces'] + base_keywords,
            'Fall Equinox': ['fall preparation', 'harvest time', 'winter prep'] + base_keywords,
            'Halloween': ['fall harvest', 'seasonal plants', 'autumn garden'] + base_keywords,
            'Veterans Day': ['memorial gardens', 'remembrance plants', 'honor gardens'] + base_keywords,
            'Thanksgiving Week': ['harvest gratitude', 'fall garden', 'thanksgiving'] + base_keywords,
            'Winter Solstice': ['winter planning', 'garden reflection', 'next year prep'] + base_keywords
        }
        
        return holiday_keywords.get(holiday_name, base_keywords)
    
    def _get_seasonal_keywords(self, season: str) -> List[str]:
        """Get seasonal keywords"""
        base_keywords = self.config.TARGET_KEYWORDS[:3]
        
        seasonal_keywords = {
            'spring': ['spring gardening', 'soil preparation', 'planting season', 'garden awakening'] + base_keywords,
            'summer': ['summer care', 'plant nutrition', 'garden maintenance', 'heat protection'] + base_keywords,
            'fall': ['fall gardening', 'harvest time', 'winter preparation', 'soil building'] + base_keywords,
            'winter': ['winter gardening', 'indoor plants', 'garden planning', 'houseplant care'] + base_keywords
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
    
    def _generate_fallback_blog(self, title: str, keywords: List[str], seasonal_focus: str, holiday_context: str) -> str:
        """Generate fallback blog content when Claude API is unavailable"""
        primary_keyword = keywords[0] if keywords else 'organic gardening'
        
        return f"""
        <h1>{title}</h1>
        
        <p>Welcome to another helpful guide from Elm Dirt! As we navigate {seasonal_focus} gardening with a focus on {holiday_context}, let's explore how organic methods can transform your garden experience with proven, natural solutions.</p>
        
        <h2>Understanding {primary_keyword.title()} for {seasonal_focus.title()}</h2>
        <p>For home gardeners who want real results, mastering {primary_keyword} is essential during this {seasonal_focus} season. The key is working with nature's timing and using organic amendments that build soil health over time.</p>
        
        <h3>The Elm Dirt Approach</h3>
        <p>Our products like Ancient Soil and Plant Juice work with nature's timing, especially important during {holiday_context}. These organic solutions provide the beneficial microbes and nutrients your plants need to thrive naturally.</p>
        
        <h2>Essential {seasonal_focus.title()} Garden Tasks</h2>
        <p>Here are proven strategies for {seasonal_focus} success:</p>
        <p>1. Focus on soil health as your foundation - healthy soil creates healthy plants</p>
        <p>2. Use organic amendments consistently - small, regular applications work better than large, infrequent ones</p>
        <p>3. Work with seasonal timing - nature has its own schedule that we should respect</p>
        <p>4. Monitor and adjust based on plant response - observe your plants and adjust care accordingly</p>
        
        <h2>Solving Common {seasonal_focus.title()} Challenges</h2>
        <p>Many gardeners face similar challenges during {seasonal_focus}. The good news is that organic solutions often work better than synthetic alternatives because they address root causes rather than just symptoms.</p>
        
        <p>Our Plant Juice provides over 250 species of beneficial bacteria and fungi that help plants with everything from nutrient uptake to pest resistance. For flowering and fruiting plants, Bloom Juice offers the specific phosphorus and potassium needed for abundant blooms and harvests.</p>
        
        <h2>Ready to Transform Your Garden This {seasonal_focus.title()}?</h2>
        <p>Whether you're dealing with {holiday_context} or just want to improve your garden's performance, organic methods provide lasting solutions that get better over time. Visit our store to learn more about how our organic products can help you succeed this {seasonal_focus} and beyond.</p>
        
        <p>Remember, gardening is a journey, not a destination. Every season teaches us something new, and every challenge is an opportunity to grow as gardeners. Happy gardening!</p>
        """
    
    def _create_fallback_blog_content(self, title: str, keywords: List[str], date: datetime, 
                                    week_id: str, holiday_context: str) -> ContentPiece:
        """Create fallback blog content piece"""
        return ContentPiece(
            id=str(uuid.uuid4()),
            title=title,
            content=self._generate_fallback_blog(title, keywords, "current season", holiday_context),
            platform="blog",
            content_type="blog_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=9, minute=0, second=0),
            keywords=keywords,
            hashtags=[],
            image_suggestion="Seasonal garden photo showcasing organic methods",
            ai_provider="fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context,
            meta_description=f"Expert gardening advice from Elm Dirt for {holiday_context}. Learn organic methods that work."
        )
    
    def _create_fallback_social_post(self, platform: str, blog_post: ContentPiece, holiday_context: str) -> Dict:
        """Create fallback social media post"""
        
        post_templates = {
            'instagram': [
                f"Spring is calling and your garden is ready to answer! 🌱 Our organic methods help create the healthy soil foundation your plants are craving. What's your biggest garden goal this season?",
                f"Weekend garden wisdom: The secret to thriving plants isn't more fertilizer - it's better soil health! Ancient Soil builds the foundation for everything else to flourish.",
                f"Garden friends, let's talk about the magic happening beneath the surface. Healthy soil means happy plants, and happy plants mean a successful harvest! 🌿"
            ],
            'facebook': [
                f"Fellow gardeners, what's your biggest challenge this season? We've found that most garden problems start with soil health. Share your experiences in the comments!",
                f"Organic gardening tip: Your soil is a living ecosystem! Feed the beneficial microbes with quality organic matter, and they'll take care of feeding your plants naturally.",
                f"Ready to try organic methods in your garden? Start with soil health and watch everything else improve. Small steps lead to big results!"
            ],
            'linkedin': [
                f"The business of sustainable agriculture starts in our home gardens. Investing in organic soil health today creates better yields and environmental benefits for years to come.",
                f"Professional insight: Organic soil amendments provide both immediate plant nutrition and long-term soil structure improvement - a win-win for serious gardeners.",
                f"Industry trend: More gardeners are choosing organic methods not just for environmental reasons, but because they consistently produce better results over time."
            ],
            'tiktok': [
                f"POV: You discover the one thing that transforms every garden 🤯 Healthy soil = healthy plants = amazing harvests!",
                f"Garden hack: This simple organic method will change how your plants grow forever ✨",
                f"Quick tip: The secret ingredient your garden's been missing isn't what you think! 🌱"
            ]
        }
        
        templates = post_templates.get(platform, post_templates['instagram'])
        content = random.choice(templates)
        
        platform_hashtags = {
            'instagram': ['organicgardening', 'plantcare', 'gardening', 'elmdirt', 'sustainablegardening', 'gardenlife', 'growyourown', 'healthysoil', 'gardenlovers', 'plantparent'],
            'facebook': ['organicgardening', 'gardening', 'elmdirt', 'sustainablegardening', 'gardenlife'],
            'linkedin': ['sustainability', 'agriculture', 'organicgardening'],
            'tiktok': ['gardentok', 'organicgardening', 'planttok', 'gardening', 'elmdirt', 'growyourown', 'plantcare', 'gardenlife']
        }
        
        return {
            'content': content,
            'hashtags': platform_hashtags.get(platform, ['organicgardening', 'gardening', 'elmdirt']),
            'image_suggestion': f"Seasonal garden photo showcasing organic methods for {platform}",
            'engagement_hook': 'What has been your experience?',
            'post_type': 'educational_tip'
        }

class ShopifyAPI:
    def __init__(self):
        self.config = Config()
        self.base_url = f"https://{self.config.SHOPIFY_STORE_URL}/admin/api/2023-10/"
        self.headers = {
            "X-Shopify-Access-Token": self.config.SHOPIFY_PASSWORD,
            "Content-Type": "application/json"
        }
    
    def create_blog_post(self, content_piece: ContentPiece) -> Dict:
        """Create blog post in Shopify"""
        if self.config.SHOPIFY_PASSWORD == 'your_shopify_password':
            return {'success': False, 'error': 'Shopify not configured - add your API credentials'}
        
        formatted_content = self._format_for_shopify(content_piece.content)
        
        article_data = {
            "article": {
                "title": content_piece.title,
                "body_html": formatted_content,
                "tags": ", ".join(content_piece.keywords),
                "published": False,  # Create as draft first
                "summary": content_piece.meta_description or self._extract_meta_description(content_piece.content),
                "created_at": datetime.now().isoformat()
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}blogs/{self.config.SHOPIFY_BLOG_ID}/articles.json",
                headers=self.headers,
                json=article_data,
                timeout=30
            )
            
            if response.status_code == 201:
                article = response.json()['article']
                return {
                    'success': True,
                    'article_id': article['id'],
                    'url': f"https://{self.config.SHOPIFY_STORE_URL}/blogs/news/{article['handle']}",
                    'handle': article['handle'],
                    'status': 'draft'
                }
            else:
                logger.error(f"Shopify API error: {response.text}")
                return {'success': False, 'error': f"Shopify API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error creating Shopify blog post: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _format_for_shopify(self, content: str) -> str:
        """Format HTML content with Elm Dirt styling"""
        return f"""
        <div class="elm-dirt-blog-post">
            <style>
                .elm-dirt-blog-post {{
                    font-family: 'Poppins', sans-serif;
                    line-height: 1.7;
                    color: #114817;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .elm-dirt-blog-post h1 {{ 
                    color: #843648; 
                    font-size: 2.8rem; 
                    margin-bottom: 1.5rem; 
                    line-height: 1.2;
                }}
                .elm-dirt-blog-post h2 {{ 
                    color: #0a2b0d; 
                    font-size: 2.2rem; 
                    margin: 2.5rem 0 1rem 0; 
                    line-height: 1.3;
                }}
                .elm-dirt-blog-post h3 {{ 
                    color: #4eb155; 
                    font-size: 1.8rem; 
                    margin: 2rem 0 0.8rem 0; 
                }}
                .elm-dirt-blog-post p {{ 
                    margin-bottom: 1.2rem; 
                    font-size: 1.1rem; 
                }}
            </style>
            {content}
            <div style="background: linear-gradient(135deg, #c9d393, #d7c4b5); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center;">
                <p style="font-size: 1.2rem; margin-bottom: 1rem; font-weight: 600;">Ready to transform your garden naturally?</p>
                <p style="margin-bottom: 1.5rem;">Discover our complete line of organic gardening products designed to build healthy soil and grow thriving plants.</p>
                <a href="/collections/all" style="background-color: #fec962; color: #3a2313; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">Shop Elm Dirt Products</a>
            </div>
        </div>
        """
    
    def _extract_meta_description(self, content: str) -> str:
        """Extract or create meta description from content"""
        # Try to find existing meta description
        match = re.search(r'<meta name="description" content="(.*?)"', content, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: extract first paragraph and clean it
        clean_content = re.sub('<[^<]+?>', '', content)
        sentences = clean_content.split('.')
        
        # Find first substantial sentence
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 50:
                return (sentence + '.').strip()[:160]
        
        return "Expert organic gardening advice from Elm Dirt - sustainable methods for healthy plants and soil."

# Initialize services
db_manager = DatabaseManager(Config.DB_PATH)
content_generator = ContentGenerator(db_manager)
shopify_api = ShopifyAPI()

# Enhanced Web Interface
CALENDAR_INTERFACE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elm Dirt Content Automation Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #c9d393, #d7c4b5);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #114817, #0a2b0d);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .main-content {
            padding: 2rem;
        }
        
        .calendar-section {
            margin-bottom: 2rem;
        }
        
        .section-title {
            color: #114817;
            font-size: 1.8rem;
            margin-bottom: 1rem;
            border-bottom: 3px solid #4eb155;
            padding-bottom: 0.5rem;
        }
        
        .calendar-controls {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        
        .week-selector {
            flex: 1;
            min-width: 250px;
        }
        
        .week-selector label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #114817;
        }
        
        .week-selector input {
            width: 100%;
            padding: 12px;
            border: 2px solid #c9d393;
            border-radius: 8px;
            font-size: 1rem;
        }
        
        .generate-btn {
            background: linear-gradient(135deg, #fec962, #c5a150);
            color: #3a2313;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            align-self: end;
        }
        
        .generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(254, 201, 98, 0.4);
        }
        
        .generate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .week-info {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .week-info h3 {
            color: #843648;
            margin-bottom: 0.5rem;
        }
        
        .holiday-badge {
            background: #fec962;
            color: #3a2313;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            margin: 0.2rem;
            display: inline-block;
        }
        
        .content-preview {
            margin-top: 2rem;
        }
        
        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }
        
        .content-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .content-card:hover {
            border-color: #4eb155;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .content-card h4 {
            color: #114817;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        
        .platform-badge {
            background: #4eb155;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
            display: inline-block;
        }
        
        .content-preview-text {
            color: #666;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4eb155;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .success-message {
            background: #d1e7dd;
            color: #0f5132;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        @media (max-width: 768px) {
            .calendar-controls {
                flex-direction: column;
            }
            
            .content-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 Elm Dirt Content Automation</h1>
            <p>Generate weekly content with holiday awareness and seasonal focus</p>
        </div>
        
        <div class="main-content">
            <div class="calendar-section">
                <h2 class="section-title">📅 Weekly Content Generator</h2>
                
                <div class="calendar-controls">
                    <div class="week-selector">
                        <label for="week-date">Select Week (Monday):</label>
                        <input type="date" id="week-date" />
                    </div>
                    <button class="generate-btn" id="generate-btn" onclick="generateWeeklyContent()">
                        Generate Weekly Content
                    </button>
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
        // Set default date to next Monday
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
            
            // Disable button and show loading
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
            
            // Show loading spinner
            contentGrid.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Generating weekly content package...</p>
                    <p>This may take 2-3 minutes</p>
                </div>
            `;
            contentPreview.style.display = 'block';
            
            try {
                const response = await fetch('/api/generate-weekly-content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        week_start_date: dateInput.value
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Show week information
                    const weekDetails = document.getElementById('week-details');
                    weekDetails.innerHTML = `
                        <p><strong>Season:</strong> ${result.season}</p>
                        <p><strong>Theme:</strong> ${result.theme}</p>
                        <p><strong>Content Pieces:</strong> ${result.content_pieces}</p>
                        ${result.holidays.length > 0 ? `
                            <p><strong>Holidays:</strong></p>
                            ${result.holidays.map(h => `<span class="holiday-badge">${h[1]}</span>`).join('')}
                        ` : ''}
                    `;
                    weekInfo.style.display = 'block';
                    
                    // Show generated content
                    displayContent(result.content);
                    
                    // Show success message
                    contentGrid.insertAdjacentHTML('afterbegin', `
                        <div class="success-message">
                            ✅ Successfully generated ${result.content_pieces} pieces of content for the week of ${new Date(result.week_start_date).toLocaleDateString()}
                        </div>
                    `);
                    
                } else {
                    throw new Error(result.error || 'Failed to generate content');
                }
                
            } catch (error) {
                console.error('Error:', error);
                contentGrid.innerHTML = `
                    <div class="error-message">
                        ❌ Error generating content: ${error.message}
                        <br><br>
                        Please check your API configuration and try again.
                    </div>
                `;
            } finally {
                // Re-enable button
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Weekly Content';
            }
        }
        
        function displayContent(contentPieces) {
            const contentGrid = document.getElementById('content-grid');
            
            // Clear loading message but keep success message
            const successMessage = contentGrid.querySelector('.success-message');
            contentGrid.innerHTML = '';
            if (successMessage) {
                contentGrid.appendChild(successMessage);
            }
            
            contentPieces.forEach(piece => {
                const contentCard = document.createElement('div');
                contentCard.className = 'content-card';
                
                const preview = piece.content.length > 200 ? 
                    piece.content.substring(0, 200) + '...' : 
                    piece.content;
                
                contentCard.innerHTML = `
                    <span class="platform-badge">${piece.platform}</span>
                    <h4>${piece.title}</h4>
                    <div class="content-preview-text">${preview}</div>
                    <p><strong>Keywords:</strong> ${piece.keywords.join(', ')}</p>
                    <p><strong>Scheduled:</strong> ${new Date(piece.scheduled_time).toLocaleString()}</p>
                    <p><strong>Status:</strong> ${piece.status}</p>
                `;
                
                contentGrid.appendChild(contentCard);
            });
        }
        
        // Initialize
        setDefaultDate();
    </script>
</body>
</html>
"""

# API Routes
@app.route('/')
def index():
    """Serve the main interface"""
    return CALENDAR_INTERFACE

@app.route('/health')
def health_check():
    """Enhanced health check with detailed status"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'features': {
            'weekly_calendar': True,
            'holiday_awareness': True,
            'content_preview': True,
            'database_storage': True
        },
        'services': {
            'claude_api': 'connected' if content_generator.claude_client else 'not_configured',
            'shopify_api': 'configured' if Config.SHOPIFY_PASSWORD != 'your_shopify_password' else 'not_configured',
            'database': 'connected'
        },
        'database_info': {
            'path': Config.DB_PATH,
            'tables': ['content_pieces', 'weekly_packages']
        }
    }
    return jsonify(health_status)

@app.route('/api/generate-weekly-content', methods=['POST'])
def generate_weekly_content():
    """Generate a complete week of content with holiday awareness"""
    data = request.json
    
    try:
        # Parse the selected week start date
        week_start_str = data.get('week_start_date')
        if not week_start_str:
            return jsonify({
                'success': False,
                'error': 'week_start_date is required (YYYY-MM-DD format)'
            }), 400
        
        week_start_date = datetime.strptime(week_start_str, '%Y-%m-%d')
        
        # Ensure it's a Monday
        if week_start_date.weekday() != 0:
            week_start_date = week_start_date - timedelta(days=week_start_date.weekday())
        
        # Generate weekly content
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

@app.route('/api/weekly-content/<week_id>', methods=['GET'])
def get_weekly_content(week_id):
    """Get all content for a specific week"""
    try:
        content_pieces = db_manager.get_weekly_content(week_id)
        
        return jsonify({
            'success': True,
            'week_id': week_id,
            'content_count': len(content_pieces),
            'content': [content_generator._content_piece_to_dict(cp) for cp in content_pieces]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/content/<content_id>', methods=['GET'])
def get_content_piece(content_id):
    """Get a specific content piece for preview/editing"""
    try:
        content_piece = db_manager.get_content_piece(content_id)
        
        if not content_piece:
            return jsonify({
                'success': False,
                'error': 'Content piece not found'
            }), 404
        
        return jsonify({
            'success': True,
            'content': content_generator._content_piece_to_dict(content_piece)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/content/<content_id>', methods=['PUT'])
def update_content_piece(content_id):
    """Update a content piece (for editing)"""
    data = request.json
    
    try:
        content_piece = db_manager.get_content_piece(content_id)
        if not content_piece:
            return jsonify({
                'success': False,
                'error': 'Content piece not found'
            }), 404
        
        # Update fields
        if 'title' in data:
            content_piece.title = data['title']
        if 'content' in data:
            content_piece.content = data['content']
        if 'hashtags' in data:
            content_piece.hashtags = data['hashtags']
        if 'image_suggestion' in data:
            content_piece.image_suggestion = data['image_suggestion']
        if 'scheduled_time' in data:
            content_piece.scheduled_time = datetime.fromisoformat(data['scheduled_time'])
        
        content_piece.updated_at = datetime.now()
        content_piece.status = ContentStatus.PREVIEW  # Mark as preview after editing
        
        # Save changes
        if db_manager.save_content_piece(content_piece):
            return jsonify({
                'success': True,
                'message': 'Content updated successfully',
                'content': content_generator._content_piece_to_dict(content_piece)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save content'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/content/<content_id>/approve', methods=['POST'])
def approve_content(content_id):
    """Approve content for publishing"""
    try:
        content_piece = db_manager.get_content_piece(content_id)
        if not content_piece:
            return jsonify({
                'success': False,
                'error': 'Content piece not found'
            }), 404
        
        content_piece.status = ContentStatus.APPROVED
        content_piece.updated_at = datetime.now()
        
        if db_manager.save_content_piece(content_piece):
            return jsonify({
                'success': True,
                'message': 'Content approved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to approve content'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/content/<content_id>/publish', methods=['POST'])
def publish_content(content_id):
    """Publish content to appropriate platform"""
    try:
        content_piece = db_manager.get_content_piece(content_id)
        if not content_piece:
            return jsonify({
                'success': False,
                'error': 'Content piece not found'
            }), 404
        
        if content_piece.status != ContentStatus.APPROVED:
            return jsonify({
                'success': False,
                'error': 'Content must be approved before publishing'
            }), 400
        
        # Publish based on platform
        if content_piece.platform == 'blog':
            result = shopify_api.create_blog_post(content_piece)
        else:
            # For social media, we'll just mark as published
            # In production, you'd integrate with Metricool or other social tools
            result = {'success': True, 'message': 'Social post marked for publishing'}
        
        if result.get('success'):
            content_piece.status = ContentStatus.PUBLISHED
            content_piece.updated_at = datetime.now()
            db_manager.save_content_piece(content_piece)
            
            return jsonify({
                'success': True,
                'message': f'Content published to {content_piece.platform}',
                'result': result
            })
        else:
            content_piece.status = ContentStatus.FAILED
            db_manager.save_content_piece(content_piece)
            
            return jsonify({
                'success': False,
                'error': result.get('error', 'Publishing failed')
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-generation', methods=['GET'])
def test_generation():
    """Test endpoint for content generation"""
    try:
        # Test weekly generation with current date
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
                'ai_provider': 'claude' if content_generator.claude_client else 'fallback'
            },
            'full_result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get analytics summary"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        # Get content counts by status
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM content_pieces 
            GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())
        
        # Get content counts by platform
        cursor.execute('''
            SELECT platform, COUNT(*) 
            FROM content_pieces 
            GROUP BY platform
        ''')
        platform_counts = dict(cursor.fetchall())
        
        # Get recent activity
        cursor.execute('''
            SELECT COUNT(*) 
            FROM content_pieces 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_content = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'analytics': {
                'status_counts': status_counts,
                'platform_counts': platform_counts,
                'recent_content_7_days': recent_content,
                'total_content': sum(status_counts.values()) if status_counts else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting Elm Dirt Content Automation Platform v2.0")
    logger.info("Features: Weekly Calendar, Holiday Awareness, Content Preview/Edit")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
