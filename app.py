# Enhanced Elm Dirt Content Automation Platform
# 6 blog posts per week + Claude API integration + Preview System

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Tuple
import re
import logging
import sqlite3
from dataclasses import dataclass, asdict
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
    # Claude API (Primary) - Fixed initialization
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your_claude_api_key')
    
    # Shopify API
    SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY', 'your_shopify_api_key')
    SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD', 'your_shopify_password')
    SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL', 'elmdirt.myshopify.com')
    SHOPIFY_BLOG_ID = os.getenv('SHOPIFY_BLOG_ID', 'your_blog_id')
    
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
        (1, 1): ('New Year', 'garden planning and resolutions', 'New Year Garden Resolutions'),
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
        (12, 21): ('Winter Solstice', 'garden planning and indoor plant care', 'Winter Garden Dreams'),
        (12, 25): ('Christmas', 'holiday plants and winter care', 'Christmas Garden Magic')
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
    image_suggestions: List[str]
    ai_provider: str
    created_at: datetime
    updated_at: datetime
    week_id: Optional[str] = None
    holiday_context: Optional[str] = None
    meta_description: Optional[str] = None
    seo_score: Optional[int] = None

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
                image_suggestions TEXT,
                ai_provider TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                week_id TEXT,
                holiday_context TEXT,
                meta_description TEXT,
                seo_score INTEGER
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
                 keywords, hashtags, image_suggestions, ai_provider, created_at, 
                 updated_at, week_id, holiday_context, meta_description, seo_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content.id, content.title, content.content, content.platform,
                content.content_type, content.status.value, 
                content.scheduled_time.isoformat() if content.scheduled_time else None,
                json.dumps(content.keywords), json.dumps(content.hashtags),
                json.dumps(content.image_suggestions), content.ai_provider, 
                content.created_at.isoformat(), content.updated_at.isoformat(),
                content.week_id, content.holiday_context, content.meta_description,
                content.seo_score
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
    
    def get_content_by_date_range(self, start_date: datetime, end_date: datetime) -> List[ContentPiece]:
        """Get content within a date range"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM content_pieces 
                WHERE scheduled_time BETWEEN ? AND ? 
                ORDER BY scheduled_time
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_content_piece(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving content by date range: {str(e)}")
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
            image_suggestions=json.loads(row[9]) if row[9] else [],
            ai_provider=row[10] or "fallback",
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            week_id=row[13],
            holiday_context=row[14],
            meta_description=row[15] if len(row) > 15 else None,
            seo_score=row[16] if len(row) > 16 else None
        )

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

class ContentGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.config = Config()
        self.db_manager = db_manager
        self.holiday_manager = HolidayManager()
        
        # Initialize Claude client with proper error handling - FIXED
        self.claude_client = None
        if self.config.CLAUDE_API_KEY and self.config.CLAUDE_API_KEY != 'your_claude_api_key':
            try:
                import anthropic
                # Fixed: Remove invalid 'proxies' parameter
                self.claude_client = anthropic.Anthropic(
                    api_key=self.config.CLAUDE_API_KEY
                )
                logger.info("Claude API client initialized successfully")
            except ImportError:
                logger.error("Anthropic library not installed. Install with: pip install anthropic")
            except Exception as e:
                logger.error(f"Failed to initialize Claude API: {str(e)}")
        else:
            logger.warning("Claude API key not configured - using fallback content generation")
    
    def generate_content_for_date(self, target_date: datetime) -> Dict:
        """Generate content for a specific date"""
        try:
            # Get Monday of the week containing target_date
            week_start_date = target_date - timedelta(days=target_date.weekday())
            
            # Check if it's a specific day request or week request
            if target_date.weekday() == 0:  # Monday - generate whole week
                return self.generate_weekly_content(week_start_date)
            else:  # Specific day - generate just that day
                return self.generate_daily_content_only(target_date, week_start_date)
        
        except Exception as e:
            logger.error(f"Error generating content for date: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def generate_daily_content_only(self, target_date: datetime, week_start_date: datetime) -> Dict:
        """Generate content for just one specific day"""
        try:
            week_id = f"week_{week_start_date.strftime('%Y_%m_%d')}"
            season = self.holiday_manager.get_seasonal_focus(target_date)
            holidays = self.holiday_manager.get_week_holidays(week_start_date)
            theme = self.holiday_manager.get_week_theme(week_start_date)
            
            day_name = target_date.strftime('%A')
            day_number = target_date.weekday() + 1
            
            logger.info(f"Generating content for {day_name}, {target_date.strftime('%Y-%m-%d')}")
            
            # Generate daily content package
            daily_content = self._generate_daily_content_package(
                date=target_date,
                day_name=day_name,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=week_id,
                day_number=day_number
            )
            
            return {
                'success': True,
                'date': target_date.isoformat(),
                'day_name': day_name,
                'season': season,
                'theme': theme,
                'holidays': [(h[0].isoformat(), h[1], h[2], h[3]) for h in holidays],
                'content_pieces': len(daily_content),
                'content_breakdown': self._get_content_breakdown(daily_content),
                'ai_provider': 'claude' if self.claude_client else 'fallback',
                'content': [self._content_piece_to_dict(cp) for cp in daily_content]
            }
            
        except Exception as e:
            logger.error(f"Error generating daily content: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def generate_weekly_content(self, week_start_date: datetime) -> Dict:
        """Generate a complete week of content - 6 BLOG POSTS!"""
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
                
                # Generate daily content package (including blog post each day)
                daily_content = self._generate_daily_content_package(
                    date=current_date,
                    day_name=day_name,
                    season=season,
                    theme=theme,
                    holidays=holidays,
                    week_id=week_id,
                    day_number=day_offset + 1
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
                'ai_provider': 'claude' if self.claude_client else 'fallback',
                'content': [self._content_piece_to_dict(cp) for cp in weekly_content]
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly content: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _generate_daily_content_package(self, date: datetime, day_name: str, season: str, 
                                       theme: str, holidays: List, week_id: str, day_number: int) -> List[ContentPiece]:
        """Generate all content for a single day - INCLUDING DAILY BLOG POST"""
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
        
        # Generate 1 blog post per day (6 total per week)
        daily_blog_post = self._generate_daily_blog_post(
            date=date,
            day_name=day_name,
            day_number=day_number,
            season=season,
            theme=theme,
            daily_theme=daily_theme,
            holiday_context=holiday_context,
            week_id=week_id
        )
        daily_content.append(daily_blog_post)
        
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
            blog_post=daily_blog_post
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
            blog_post=daily_blog_post
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
            blog_post=daily_blog_post
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
            blog_post=daily_blog_post
        )
        daily_content.append(linkedin_post)
        
        return daily_content
    
    def _generate_daily_blog_post(self, date: datetime, day_name: str, day_number: int,
                                 season: str, theme: str, daily_theme: str, 
                                 holiday_context: str, week_id: str) -> ContentPiece:
        """Generate one blog post per day with unique daily focus"""
        
        # Create unique daily blog titles
        daily_blog_topics = {
            'Monday': {
                'focus': 'Weekly Planning & Soil Health',
                'title_template': 'Week {week_num} {season} Garden Plan: {daily_theme} Success Strategy',
                'angle': 'planning and preparation'
            },
            'Tuesday': {
                'focus': 'Techniques & Methods',
                'title_template': '{season} Garden Techniques: {daily_theme} That Actually Work',
                'angle': 'practical methods and techniques'
            },
            'Wednesday': {
                'focus': 'Plant Nutrition & Care',
                'title_template': 'Mid-Week {season} Wisdom: Advanced {daily_theme} Guide',
                'angle': 'nutrition and plant care'
            },
            'Thursday': {
                'focus': 'Problem Solving',
                'title_template': '{season} Garden Transformations: {daily_theme} Solutions',
                'angle': 'troubleshooting and solutions'
            },
            'Friday': {
                'focus': 'Product Features & Results',
                'title_template': 'Friday Feature: {daily_theme} with Elm Dirt Products',
                'angle': 'product features and case studies'
            },
            'Saturday': {
                'focus': 'Weekend Projects',
                'title_template': 'Weekend {season} Projects: {daily_theme} Made Easy',
                'angle': 'DIY projects and weekend activities'
            }
        }
        
        # Get today's blog configuration
        blog_config = daily_blog_topics.get(day_name, daily_blog_topics['Monday'])
        
        # Generate title
        week_num = date.isocalendar()[1]
        title = blog_config['title_template'].format(
            week_num=week_num,
            season=season.title(),
            daily_theme=daily_theme
        )
        
        # Override with holiday title if applicable
        if any(holiday_date.date() == date.date() for holiday_date, _, _, _ in self.holiday_manager.get_week_holidays(date)):
            for holiday_date, holiday_name, gardening_focus, content_theme in self.holiday_manager.get_week_holidays(date):
                if holiday_date.date() == date.date():
                    title = f"{holiday_name} {season.title()} Garden Guide: {blog_config['focus']}"
                    break
        
        # Generate keywords specific to daily focus
        keywords = self._get_daily_keywords(day_name, season, blog_config['focus'])
        
        # Use Claude API if available, otherwise fallback
        if self.claude_client:
            blog_data = self._generate_claude_blog_post(
                title=title,
                keywords=keywords,
                season=season,
                day_name=day_name,
                daily_theme=daily_theme,
                holiday_context=holiday_context,
                blog_angle=blog_config['angle'],
                date=date
            )
            ai_provider = "claude"
        else:
            blog_data = self._generate_fallback_blog(title, keywords, season, holiday_context)
            ai_provider = "fallback"
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=title,
            content=blog_data['html_content'],
            platform="blog",
            content_type="blog_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=9, minute=0, second=0),
            keywords=keywords,
            hashtags=[],
            image_suggestions=blog_data['image_suggestions'],
            ai_provider=ai_provider,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context,
            meta_description=blog_data['meta_description'],
            seo_score=blog_data.get('seo_score', 85)
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _generate_claude_blog_post(self, title: str, keywords: List[str], season: str,
                                  day_name: str, daily_theme: str, holiday_context: str,
                                  blog_angle: str, date: datetime) -> Dict:
        """Generate blog post using Claude API"""
        
        prompt = f"""Generate an SEO-optimized blog article for Elm Dirt's organic gardening ecommerce store.

ARTICLE DETAILS:
Title: "{title}"
Publication Date: {date.strftime('%B %d, %Y')} ({day_name})
Season: {season}
Daily Theme: {daily_theme}
Context: {holiday_context}
Blog Angle: {blog_angle}

TARGET AUDIENCE: 50+ year old home gardeners across the US
BRAND VOICE: Friendly, knowledgeable gardening neighbor sharing practical wisdom
WORD COUNT: 700-900 words
PRIMARY KEYWORDS: {', '.join(keywords[:3])}
SECONDARY KEYWORDS: {', '.join(keywords[3:6]) if len(keywords) > 3 else ''}

ELM DIRT PRODUCTS TO REFERENCE NATURALLY:
- Ancient Soil (premium worm castings and organic blend for soil health)
- Plant Juice (liquid organic fertilizer with beneficial microbes)
- Bloom Juice (specialized fertilizer for flowering and fruiting plants)
- Worm Castings (pure organic soil amendment)
- All-Purpose Soil Mix (complete potting solution)

CONTENT REQUIREMENTS:
- Write conversationally like talking to a gardening friend
- Focus specifically on {blog_angle} for this {day_name}
- Include practical, actionable advice for the current season/date
- Reference seasonal timing and current gardening tasks
- Weave in holiday context naturally if applicable: {holiday_context}
- Include specific tips that 50+ gardeners will appreciate
- Mention regional considerations for US gardeners
- End with clear call-to-action to visit Elm Dirt

STRUCTURE:
1. H1: {title}
2. Introduction acknowledging {day_name} timing and {daily_theme} focus (100-150 words)
3. H2: Main section about {blog_angle} with practical tips
4. H2: Seasonal application section with Elm Dirt product integration
5. H2: Action steps for this {day_name} and {season} timing
6. Conclusion with encouragement and CTA

SEO REQUIREMENTS:
- Primary keyword density: 1-2%
- Include semantic variations naturally
- Write a compelling meta description (150-160 characters)
- Use proper heading hierarchy

IMAGE SUGGESTIONS NEEDED:
Please suggest 3-5 specific images that would complement this article:
1. Featured image for the blog post header
2. Supporting images for each main section
3. Product images where Elm Dirt products are mentioned
4. Seasonal/action images showing the techniques described

OUTPUT FORMAT:
Return a JSON response with:
{{
  "html_content": "Complete HTML with proper tags, ready for Shopify",
  "meta_description": "SEO meta description 150-160 chars",
  "image_suggestions": ["List of 3-5 specific image descriptions"],
  "seo_score": 85-100 (estimated SEO score based on optimization)
}}

Make the HTML visually appealing with proper formatting, but clean enough for Shopify blog."""

        try:
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Try to parse JSON response
            response_text = response.content[0].text
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                try:
                    blog_data = json.loads(json_match.group())
                    return blog_data
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Parse manually if JSON parsing fails
            return self._parse_claude_response_manually(response_text, title, keywords, season, holiday_context)
            
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            return self._generate_fallback_blog(title, keywords, season, holiday_context)
    
    def _parse_claude_response_manually(self, response_text: str, title: str, keywords: List[str], season: str, holiday_context: str) -> Dict:
        """Manually parse Claude response if JSON parsing fails"""
        
        # Extract meta description
        meta_match = re.search(r'"meta_description":\s*"([^"]*)"', response_text)
        meta_description = meta_match.group(1) if meta_match else f"Expert {season} gardening advice from Elm Dirt."[:160]
        
        # Extract image suggestions
        image_matches = re.findall(r'"([^"]*image[^"]*)"', response_text, re.IGNORECASE)
        image_suggestions = image_matches[:5] if image_matches else [
            f"{season} garden showing healthy plants",
            f"Elm Dirt products in use during {season}",
            f"Before and after garden transformation in {season}",
            f"Close-up of healthy soil with organic matter"
        ]
        
        # Use the response as HTML content if it contains HTML tags
        if '<h1>' in response_text or '<h2>' in response_text:
            html_content = response_text
        else:
            # Create basic HTML structure
            html_content = f"""<h1>{title}</h1>

<p>{response_text[:500]}...</p>

<h2>{season.title()} Garden Essentials</h2>

<p>During {season}, successful gardeners focus on key practices that ensure healthy plant growth. Our organic approach emphasizes building soil health naturally.</p>

<h2>Elm Dirt Solutions for {season.title()}</h2>

<p>Our Ancient Soil and Plant Juice products are specifically designed to support your garden during {season}. These organic solutions work with nature to create thriving growing conditions.</p>

<h2>Take Action This Week</h2>

<p>Ready to transform your {season} garden? Visit our website to explore our complete line of organic gardening solutions.</p>"""
        
        return {
            'html_content': html_content,
            'meta_description': meta_description,
            'image_suggestions': image_suggestions,
            'seo_score': 85
        }
    
    def _get_daily_keywords(self, day_name: str, season: str, focus: str) -> List[str]:
        """Get keywords specific to the day and focus"""
        base_keywords = self.config.TARGET_KEYWORDS[:2]
        
        daily_keywords = {
            'Monday': ['garden planning', 'soil health', 'weekly garden tasks'] + base_keywords,
            'Tuesday': ['gardening techniques', 'plant care methods', f'{season} techniques'] + base_keywords,
            'Wednesday': ['plant nutrition', 'organic fertilizer', 'garden wisdom'] + base_keywords,
            'Thursday': ['garden problems', 'plant troubleshooting', 'garden solutions'] + base_keywords,
            'Friday': ['garden products', 'organic gardening supplies', 'elm dirt products'] + base_keywords,
            'Saturday': ['weekend gardening', 'garden projects', 'DIY gardening'] + base_keywords
        }
        
        return daily_keywords.get(day_name, base_keywords + [f'{season} gardening', focus.lower()])
    
    def _generate_fallback_blog(self, title: str, keywords: List[str], season: str, holiday_context: str) -> Dict:
        """Generate fallback blog content when Claude API is unavailable"""
        
        keyword_text = keywords[0] if keywords else "organic gardening"
        
        html_content = f"""<h1>{title}</h1>

<p>Welcome to another week of {season} gardening excellence! As we continue our journey toward healthier, more productive gardens, it's important to focus on the fundamentals that make the biggest difference in our plants' success.</p>

<h2>Why {season.title()} {keyword_text.title()} Matters</h2>

<p>During {season}, your garden needs specific attention to thrive. The right approach to {keyword_text} can make the difference between a struggling garden and one that flourishes. Our organic methods focus on building soil health naturally, creating an environment where plants can reach their full potential.</p>

<p>Context: {holiday_context}</p>

<h2>Essential {season.title()} Garden Tasks</h2>

<p>Here's what successful gardeners are doing this week:</p>

<ul>
<li>Testing and improving soil health with organic amendments</li>
<li>Applying beneficial microbes to boost plant nutrition</li>
<li>Monitoring plant health and adjusting care routines</li>
<li>Planning ahead for optimal growing conditions</li>
</ul>

<h2>Elm Dirt's Organic Solutions</h2>

<p>Our {keyword_text} products are designed specifically for {season} gardening success. Ancient Soil provides the foundation your plants need, while Plant Juice delivers essential nutrients and beneficial microbes that support healthy growth naturally.</p>

<p>Whether you're working with container plants, raised beds, or traditional garden plots, our organic approach builds lasting soil health that benefits your garden season after season.</p>

<h2>Take Action This Week</h2>

<p>Ready to transform your {season} garden? Visit our website to explore our complete line of organic gardening solutions. Your plants will thank you for choosing natural nutrition that works with nature, not against it.</p>

<p>Remember, successful gardening is about consistency and patience. Small, regular improvements lead to remarkable results over time.</p>"""

        meta_description = f"Expert {season} gardening advice from Elm Dirt. Learn essential {keyword_text} techniques for successful organic gardening this season."[:160]
        
        image_suggestions = [
            f"{season.title()} garden showing healthy plants and soil",
            f"Elm Dirt Ancient Soil being applied to garden beds",
            f"Before and after comparison of plants using organic fertilizer",
            f"Gardener working with plants during {season} season",
            f"Close-up of healthy plant roots in rich organic soil"
        ]
        
        return {
            'html_content': html_content,
            'meta_description': meta_description,
            'image_suggestions': image_suggestions,
            'seo_score': 75
        }
    
    # Continue with all the other methods...
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
                image_suggestions=[post_content['image_suggestion']],
                ai_provider="template",
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
        
        tiktok_content = self._create_tiktok_script(
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            blog_post=blog_post
        )
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=f"{day_name} TikTok Video - {daily_theme}",
            content=tiktok_content['script'],
            platform="tiktok",
            content_type="video_script",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=15, minute=0, second=0),
            keywords=blog_post.keywords[:3],
            hashtags=tiktok_content['hashtags'],
            image_suggestions=[tiktok_content['video_concept']],
            ai_provider="template",
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
        """Generate LinkedIn post"""
        
        linkedin_content = self._create_linkedin_content(
            day_name=day_name,
            daily_theme=daily_theme,
            season=season,
            holiday_context=holiday_context,
            blog_post=blog_post
        )
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=f"{day_name} LinkedIn Post - {daily_theme}",
            content=linkedin_content['content'],
            platform="linkedin",
            content_type="linkedin_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=11, minute=0, second=0),
            keywords=blog_post.keywords[:3],
            hashtags=linkedin_content['hashtags'],
            image_suggestions=[linkedin_content['image_suggestion']],
            ai_provider="template",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _generate_youtube_outline(self, week_start_date: datetime, season: str, 
                                 theme: str, holidays: List, week_id: str) -> ContentPiece:
        """Generate YouTube video outline for the week"""
        
        week_num = week_start_date.isocalendar()[1]
        title = f"Week {week_num} {season.title()} Garden Guide: {theme}"
        
        if holidays:
            primary_holiday = holidays[0]
            title = f"{primary_holiday[1]} {season.title()} Garden Special: {theme}"
        
        youtube_content = self._create_youtube_outline(
            title=title,
            season=season,
            theme=theme,
            holidays=holidays,
            week_start_date=week_start_date
        )
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=title,
            content=youtube_content['outline'],
            platform="youtube",
            content_type="video_outline",
            status=ContentStatus.DRAFT,
            scheduled_time=week_start_date.replace(hour=10, minute=0, second=0),
            keywords=self.config.TARGET_KEYWORDS[:5],
            hashtags=youtube_content['hashtags'],
            image_suggestions=[youtube_content['thumbnail_suggestion']],
            ai_provider="template",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=f"{season} - {theme}"
        )
        
        self.db_manager.save_content_piece(content_piece)
        return content_piece
    
    def _create_platform_specific_post(self, platform: str, post_type: str, date: datetime,
                                      day_name: str, daily_theme: str, season: str,
                                      holiday_context: str, blog_post: ContentPiece) -> Dict:
        """Create platform-specific post content"""
        
        post_templates = {
            'educational_tip': {
                'instagram': f"{day_name} Garden Tip!\n\n{daily_theme} focus: Did you know that {season} is perfect for improving your soil health? Here's what seasoned gardeners do:\n\n✅ Test soil pH weekly\n✅ Add organic matter regularly\n✅ Feed beneficial microbes\n\nTry our Ancient Soil for healthier plants! 🪴\n\n{holiday_context}",
                'facebook': f"{day_name} Gardening Wisdom 🌿\n\nAs we embrace {daily_theme} this {season}, here's a pro tip that will transform your garden:\n\n{season.title()} soil preparation is crucial for plant success. Our organic approach focuses on building living soil that feeds your plants naturally.\n\nWhat's your biggest {season} garden challenge? Share below! 👇\n\n{holiday_context}"
            },
            'product_spotlight': {
                'instagram': f" Product Spotlight: {day_name} Edition\n\n{daily_theme} calls for the right nutrition! Our Plant Juice contains over 250 beneficial microbes that:\n\n🌱 Boost root development\n💪 Strengthen plant immunity\n🌿 Improve nutrient uptake\n\nPerfect for {season} growing! Link in bio 🔗\n\n{holiday_context}",
                'facebook': f"{day_name} Feature: Why Our Customers Love Plant Juice 💚\n\n\"{daily_theme} has never been easier since I started using Elm Dirt products. My {season} garden is thriving!\" - Sarah from Texas\n\nOur Plant Juice works because it feeds the soil, not just the plant. The result? Healthier, more resilient gardens.\n\nReady to transform your {season} garden? 🌻\n\n{holiday_context}"
            },
            'community_question': {
                'instagram': f" {day_name} Garden Chat!\n\nIt's {daily_theme} time! We want to know:\n\nWhat's your go-to {season} garden ritual? 🤔\n\nA) Morning soil check ☀️\nB) Evening watering 🌙\nC) Weekend plant food application 🥄\nD) Daily harvest walk 🥕\n\nTell us in comments! 👇\n\n{holiday_context}",
                'facebook': f"{day_name} Community Question 🤝\n\nGardening friends, as we focus on {daily_theme} this {season}, we're curious:\n\nWhat's the ONE {season} gardening lesson you wish you'd learned sooner?\n\nShare your wisdom in the comments! Your experience could help a fellow gardener avoid common pitfalls.\n\n{holiday_context}"
            },
            'seasonal_advice': {
                'instagram': f" {day_name} {season.title()} Reminder\n\n{daily_theme} Alert! This week is perfect for:\n\n🌱 Checking soil moisture\n🌿 Feeding with organic nutrients\n🌻 Planning next month's plantings\n\n{season.title()} success starts with timing! ⏰\n\n{holiday_context}",
                'facebook': f"{season.title()} {day_name} Check-In 📅\n\nAs we embrace {daily_theme}, here's what successful gardeners are doing this week:\n\n• Monitoring plant health daily\n• Adjusting watering schedules for {season} weather\n• Preparing soil for upcoming plantings\n• Building beneficial microbe populations\n\nStay on track for {season} success! 🎯\n\n{holiday_context}"
            },
            'behind_scenes': {
                'instagram': f" Behind the Scenes: {day_name}\n\n{daily_theme} prep happening at Elm Dirt HQ! Our team is:\n\n🧪 Testing new organic blends\n📦 Packing your orders with care\n🌱 Growing trial plants with our products\n\nYour {season} garden success is our mission! 💚\n\n{holiday_context}",
                'facebook': f"From Our Garden to Yours 🏡\n\n{day_name} update from the Elm Dirt family!\n\nThis week's {daily_theme} focus has our team excited about helping you achieve {season} garden success. We're constantly testing our products in real garden conditions because your results matter to us.\n\nWhat questions can we answer about {season} gardening? 🤔\n\n{holiday_context}"
            }
        }
        
        content = post_templates.get(post_type, {}).get(platform, f"{day_name} {daily_theme} post for {platform}")
        
        # Platform-specific hashtags
        platform_hashtags = {
            'instagram': ['#ElmDirt', '#OrganicGardening', f'#{season}Garden', '#PlantFood', '#SoilHealth', 
                         '#GardenLife', '#PlantParent', '#GrowYourOwn', '#MicrobeRich', '#LivingSoil'],
            'facebook': ['#ElmDirt', '#OrganicGardening', f'#{season.title()}Gardening', '#GardenCommunity', 
                        '#SustainableLiving', '#PlantCare', '#GardenTips']
        }
        
        hashtags = platform_hashtags.get(platform, ['#ElmDirt', '#OrganicGardening'])
        
        # Image suggestions
        image_suggestions = {
            'educational_tip': f"{season} garden showing healthy soil and plants",
            'product_spotlight': f"Elm Dirt product in use in {season} garden setting",
            'community_question': f"Diverse group of gardeners in {season} garden",
            'seasonal_advice': f"{season} garden tasks being performed",
            'behind_scenes': f"Elm Dirt team working with products and plants"
        }
        
        return {
            'content': content,
            'hashtags': hashtags,
            'image_suggestion': image_suggestions.get(post_type, f"{season} garden scene")
        }
    
    def _create_tiktok_script(self, day_name: str, daily_theme: str, season: str,
                             holiday_context: str, blog_post: ContentPiece) -> Dict:
        """Create TikTok video script"""
        
        script = f"""🎬 TikTok Video Script: {day_name} {daily_theme}

HOOK (0-3 seconds):
"POV: It's {day_name} and your {season} garden needs {daily_theme.lower()} attention! 🌱"

MAIN CONTENT (3-12 seconds):
Quick cuts showing:
1. Problem: Struggling plants in {season}
2. Solution: Applying Elm Dirt products
3. Transformation: Thriving plants after treatment

CALL TO ACTION (12-15 seconds):
"Follow for more {season} garden hacks! Link in bio for organic solutions ✨"

VISUAL NOTES:
- Fast-paced editing with trending audio
- Before/after plant comparisons
- Product application demonstration
- Text overlay with key tips

TRENDING HASHTAGS: Check current gardening trends

CONTEXT: {holiday_context}"""

        hashtags = ['#ElmDirt', '#GardenTok', '#PlantTok', f'#{season}Garden', '#OrganicGardening', 
                   '#PlantParent', '#GardenHacks', '#SoilHealth', '#GrowTok', '#PlantCare']
        
        video_concept = f"Quick {season} garden transformation showing {daily_theme.lower()} techniques"
        
        return {
            'script': script,
            'hashtags': hashtags,
            'video_concept': video_concept
        }
    
    def _create_linkedin_content(self, day_name: str, daily_theme: str, season: str,
                                holiday_context: str, blog_post: ContentPiece) -> Dict:
        """Create LinkedIn post content"""
        
        content = f"""🌱 {day_name} Insights: {daily_theme} in {season.title()} Business Operations

As we navigate {daily_theme.lower()} in the gardening industry, there's a valuable lesson for all businesses:

Just like plants need the right nutrients at the right time, businesses thrive when they focus on building strong foundations rather than quick fixes.

At Elm Dirt, our {season} strategy mirrors nature's wisdom:
• Invest in soil health (company culture)
• Feed beneficial relationships (customer communities)  
• Plan for sustainable growth (long-term thinking)

The gardening industry teaches us that patience and consistent care yield the best results.

What business lessons have you learned from nature? 🌿

{holiday_context}

#BusinessStrategy #SustainableBusiness #ElmDirt #GreenIndustry #OrganicGrowth"""

        hashtags = ['#BusinessStrategy', '#SustainableBusiness', '#ElmDirt', '#GreenIndustry', 
                   '#OrganicGrowth', '#Entrepreneurship', '#SmallBusiness', '#Agriculture']
        
        image_suggestion = f"Professional photo of {season} business garden or team meeting outdoors"
        
        return {
            'content': content,
            'hashtags': hashtags,
            'image_suggestion': image_suggestion
        }
    
    def _create_youtube_outline(self, title: str, season: str, theme: str, 
                               holidays: List, week_start_date: datetime) -> Dict:
        """Create YouTube video outline"""
        
        outline = f"""🎥 YouTube Video Outline: {title}

INTRO (0-30 seconds):
- Welcome to Elm Dirt's weekly garden guide
- Preview of this week's {theme.lower()} focus
- Quick overview of {season} priorities

MAIN CONTENT (30 seconds - 8 minutes):

Segment 1: This Week's {season.title()} Focus (1-2 minutes)
- Current seasonal tasks
- Weather considerations
- Regional variations across US

Segment 2: {theme} Deep Dive (3-4 minutes)
- Practical techniques and methods
- Product demonstrations with Elm Dirt solutions
- Common mistakes to avoid

Segment 3: Weekly Action Plan (1-2 minutes)
- Monday through Saturday garden tasks
- Product application schedule
- Success metrics to track

OUTRO (8-10 minutes):
- Recap of key points
- Next week preview
- Community question for comments
- Subscribe reminder and links

HOLIDAY INTEGRATION: {"Holiday content: " + str(holidays) if holidays else "Seasonal focus"}

KEYWORDS: {season} gardening, organic fertilizer, soil health, plant nutrition

THUMBNAIL CONCEPT: Split screen showing garden transformation with Elm Dirt products"""

        hashtags = ['#ElmDirt', '#OrganicGardening', f'#{season.title()}Gardening', '#GardenGuide', 
                   '#PlantCare', '#SoilHealth', '#GardenTips', '#PlantFood', '#GrowYourOwn']
        
        thumbnail_suggestion = f"Eye-catching thumbnail with {season} garden transformation split-screen"
        
        return {
            'outline': outline,
            'hashtags': hashtags,
            'thumbnail_suggestion': thumbnail_suggestion
        }
    
    def _save_weekly_package(self, week_id: str, week_start_date: datetime, 
                            season: str, holidays: List, theme: str) -> bool:
        """Save weekly package information"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            week_end_date = week_start_date + timedelta(days=6)
            holidays_json = json.dumps([(h[0].isoformat(), h[1], h[2], h[3]) for h in holidays])
            
            cursor.execute('''
                INSERT OR REPLACE INTO weekly_packages 
                (id, week_start_date, week_end_date, season, holidays, theme, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                week_id, week_start_date.date().isoformat(), week_end_date.date().isoformat(),
                season, holidays_json, theme, 'generated', 
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving weekly package: {str(e)}")
            return False
    
    def _get_content_breakdown(self, weekly_content: List[ContentPiece]) -> Dict:
        """Get breakdown of content types generated"""
        breakdown = {}
        for content in weekly_content:
            platform = content.platform
            if platform not in breakdown:
                breakdown[platform] = 0
            breakdown[platform] += 1
        return breakdown
    
    def _content_piece_to_dict(self, content: ContentPiece) -> Dict:
        """Convert ContentPiece to dictionary for JSON serialization"""
        return {
            'id': content.id,
            'title': content.title,
            'content': content.content[:200] + "..." if len(content.content) > 200 else content.content,
            'platform': content.platform,
            'content_type': content.content_type,
            'status': content.status.value,
            'scheduled_time': content.scheduled_time.isoformat() if content.scheduled_time else None,
            'keywords': content.keywords,
            'hashtags': content.hashtags,
            'image_suggestions': content.image_suggestions,
            'ai_provider': content.ai_provider,
            'holiday_context': content.holiday_context,
            'meta_description': content.meta_description,
            'seo_score': content.seo_score
        }

class ShopifyManager:
    def __init__(self):
        self.config = Config()
        self.base_url = f"https://{self.config.SHOPIFY_STORE_URL}/admin/api/2023-04"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.config.SHOPIFY_PASSWORD
        }
    
    def publish_blog_post(self, content_piece: ContentPiece) -> Dict:
        """Publish blog post to Shopify"""
        try:
            blog_post_data = {
                "article": {
                    "title": content_piece.title,
                    "body_html": content_piece.content,
                    "published": True,
                    "tags": ", ".join(content_piece.keywords),
                    "summary": content_piece.meta_description or content_piece.title
                }
            }
            
            url = f"{self.base_url}/blogs/{self.config.SHOPIFY_BLOG_ID}/articles.json"
            response = requests.post(url, json=blog_post_data, headers=self.headers)
            
            if response.status_code == 201:
                return {"success": True, "article_id": response.json()["article"]["id"]}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error publishing to Shopify: {str(e)}")
            return {"success": False, "error": str(e)}

# Initialize global instances
db_manager = DatabaseManager(Config.DB_PATH)
content_generator = ContentGenerator(db_manager)
shopify_manager = ShopifyManager()

# Flask Routes
@app.route('/')
def home():
    """Enhanced home page with date selection and preview functionality"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Elm Dirt Content Automation</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background: #f8f9fa;
        }
        .header {
            background: linear-gradient(135deg, #4CAF50, #2E7D32);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .control-panel {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .date-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .date-input-group {
            background: #f1f3f4;
            padding: 20px;
            border-radius: 10px;
        }
        .date-input-group h3 {
            margin-top: 0;
            color: #2E7D32;
        }
        input[type="date"], input[type="datetime-local"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        .btn { 
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 8px;
            cursor: pointer; 
            margin: 5px; 
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            background: linear-gradient(135deg, #45a049, #388e3c);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .status { 
            margin: 20px 0; 
            padding: 15px; 
            border-radius: 10px; 
            font-weight: 500;
        }
        .success { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
        .error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
        .info { background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8; }
        .warning { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
        
        .results-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }
        .content-summary {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .content-preview {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-height: 600px;
            overflow-y: auto;
        }
        .content-item {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }
        .content-item h4 {
            margin: 0 0 10px 0;
            color: #2E7D32;
        }
        .preview-btn {
            background: #17a2b8;
            color: white;
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        .preview-btn:hover {
            background: #138496;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4CAF50;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border-radius: 10px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: black;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌱 Elm Dirt Content Automation Platform</h1>
        <p>Generate seasonal content with 6 daily blog posts, social media content, and video scripts</p>
    </div>
    
    <div class="control-panel">
        <h2>Content Generation</h2>
        
        <div class="date-section">
            <div class="date-input-group">
                <h3>📅 Generate for Specific Date</h3>
                <p>Select any date to generate content for that specific day, or select a Monday to generate content for the entire week.</p>
                <input type="date" id="specificDate" />
                <button class="btn" onclick="generateForDate()" id="dateBtn">
                    Generate Content
                </button>
            </div>
            
            <div class="date-input-group">
                <h3>📆 Quick Actions</h3>
                <button class="btn" onclick="generateToday()">Generate Today's Content</button>
                <button class="btn" onclick="generateThisWeek()">Generate This Week</button>
                <button class="btn" onclick="generateNextWeek()">Generate Next Week</button>
                <button class="btn" onclick="viewExistingContent()" style="background: #6f42c1;">View Existing Content</button>
            </div>
        </div>
        
        <div id="holidayInfo" class="warning" style="display: none;">
            <strong>🎉 Holiday Detection:</strong> <span id="holidayText"></span>
        </div>
    </div>
    
    <div id="status"></div>
    
    <div class="results-grid" id="resultsGrid" style="display: none;">
        <div class="content-summary">
            <h3>📊 Content Summary</h3>
            <div id="summaryContent"></div>
        </div>
        
        <div class="content-preview">
            <h3>👁️ Content Preview</h3>
            <div id="previewContent"></div>
        </div>
    </div>
    
    <!-- Modal for content preview -->
    <div id="contentModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script>
        // Set today's date as default
        document.getElementById('specificDate').valueAsDate = new Date();
        
        // Check for holidays on date change
        document.getElementById('specificDate').addEventListener('change', function() {
            checkForHolidays(this.value);
        });
        
        let generatedContent = [];
        
        function checkForHolidays(dateString) {
            const date = new Date(dateString);
            const holidays = {
                '01-01': 'New Year - Garden Planning & Resolutions',
                '02-14': 'Valentine\'s Day - Flowering Plants & Love for Gardening',
                '03-17': 'St. Patrick\'s Day - Green Plants & Irish Garden Traditions',
                '03-20': 'Spring Equinox - Spring Awakening & Soil Preparation',
                '04-22': 'Earth Day - Sustainable Gardening & Environmental Stewardship',
                '05-01': 'May Day - Spring Planting & Garden Celebrations',
                '05-08': 'Mother\'s Day Week - Garden Gifts & Family Gardening',
                '05-30': 'Memorial Day - Summer Garden Prep & Remembrance Gardens',
                '06-21': 'Summer Solstice - Peak Growing Season & Plant Care',
                '07-04': 'Independence Day - Summer Garden Maintenance & Patriotic Plants',
                '08-15': 'National Relaxation Day - Peaceful Garden Spaces',
                '09-22': 'Fall Equinox - Harvest Time & Winter Preparation',
                '10-31': 'Halloween - Fall Garden Cleanup & Decorative Plants',
                '11-11': 'Veterans Day - Remembrance Gardens & Hardy Plants',
                '11-24': 'Thanksgiving Week - Gratitude for Harvest & Garden Reflection',
                '12-21': 'Winter Solstice - Garden Planning & Indoor Plant Care',
                '12-25': 'Christmas - Holiday Plants & Winter Care'
            };
            
            const monthDay = String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
            const holidayInfo = document.getElementById('holidayInfo');
            const holidayText = document.getElementById('holidayText');
            
            if (holidays[monthDay]) {
                holidayText.textContent = holidays[monthDay];
                holidayInfo.style.display = 'block';
            } else {
                holidayInfo.style.display = 'none';
            }
        }
        
        // Check for holidays on page load
        checkForHolidays(document.getElementById('specificDate').value);
        
        async function generateForDate() {
            const dateInput = document.getElementById('specificDate');
            const date = new Date(dateInput.value);
            await generateContentForDate(date);
        }
        
        async function generateToday() {
            await generateContentForDate(new Date());
        }
        
        async function generateThisWeek() {
            const today = new Date();
            const monday = new Date(today);
            monday.setDate(today.getDate() - today.getDay() + 1);
            await generateContentForDate(monday);
        }
        
        async function generateNextWeek() {
            const today = new Date();
            const nextMonday = new Date(today);
            nextMonday.setDate(today.getDate() - today.getDay() + 8);
            await generateContentForDate(nextMonday);
        }
        
        async function generateContentForDate(date) {
            const status = document.getElementById('status');
            const resultsGrid = document.getElementById('resultsGrid');
            const dateBtn = document.getElementById('dateBtn');
            
            // Disable button and show loading
            dateBtn.disabled = true;
            dateBtn.innerHTML = '<span class="loading"></span> Generating...';
            
            status.innerHTML = '<div class="info">🤖 Generating content... This may take a few minutes.</div>';
            resultsGrid.style.display = 'none';
            
            try {
                const response = await fetch('/api/generate-content-for-date', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_date: date.toISOString() })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    generatedContent = data.content || [];
                    displayResults(data);
                    status.innerHTML = '<div class="success">✅ Content generated successfully!</div>';
                } else {
                    status.innerHTML = `<div class="error">❌ Error: ${data.error}</div>`;
                }
            } catch (error) {
                status.innerHTML = `<div class="error">❌ Network error: ${error.message}</div>`;
            } finally {
                // Re-enable button
                dateBtn.disabled = false;
                dateBtn.innerHTML = 'Generate Content';
            }
        }
        
        function displayResults(data) {
            const resultsGrid = document.getElementById('resultsGrid');
            const summaryContent = document.getElementById('summaryContent');
            const previewContent = document.getElementById('previewContent');
            
            // Summary
            summaryContent.innerHTML = `
                <p><strong>📅 Date/Week:</strong> ${data.week_start_date ? new Date(data.week_start_date).toLocaleDateString() : new Date(data.date).toLocaleDateString()}</p>
                <p><strong>🎭 Theme:</strong> ${data.theme}</p>
                <p><strong>🌸 Season:</strong> ${data.season}</p>
                <p><strong>📝 Content Pieces:</strong> ${data.content_pieces}</p>
                <p><strong>🤖 AI Provider:</strong> ${data.ai_provider}</p>
                <h4>Content Breakdown:</h4>
                <ul>
                    ${Object.entries(data.content_breakdown).map(([platform, count]) => 
                        `<li>${platform}: ${count} pieces</li>`
                    ).join('')}
                </ul>
                ${data.holidays && data.holidays.length > 0 ? `
                    <h4>🎉 Holidays This Week:</h4>
                    <ul>
                        ${data.holidays.map(([date, name, focus, theme]) => 
                            `<li><strong>${name}</strong> - ${focus}</li>`
                        ).join('')}
                    </ul>
                ` : ''}
            `;
            
            // Preview
            previewContent.innerHTML = data.content.map(content => `
                <div class="content-item">
                    <h4>${content.platform.toUpperCase()}: ${content.title}</h4>
                    <p><strong>Type:</strong> ${content.content_type}</p>
                    <p><strong>Scheduled:</strong> ${content.scheduled_time ? new Date(content.scheduled_time).toLocaleString() : 'Not scheduled'}</p>
                    ${content.seo_score ? `<p><strong>SEO Score:</strong> ${content.seo_score}/100</p>` : ''}
                    <button class="preview-btn" onclick="previewContent('${content.id}')">
                        👁️ Preview
                    </button>
                    ${content.platform === 'blog' ? `
                        <button class="preview-btn" onclick="publishContent('${content.id}')" style="background: #28a745;">
                            🚀 Publish to Shopify
                        </button>
                    ` : ''}
                </div>
            `).join('');
            
            resultsGrid.style.display = 'grid';
        }
        
        async function previewContent(contentId) {
            try {
                const response = await fetch(`/api/content/${contentId}`);
                const content = await response.json();
                
                if (content.error) {
                    alert('Error loading content: ' + content.error);
                    return;
                }
                
                const modal = document.getElementById('contentModal');
                const modalContent = document.getElementById('modalContent');
                
                modalContent.innerHTML = `
                    <h2>${content.title}</h2>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <strong>Platform:</strong> ${content.platform} | 
                        <strong>Type:</strong> ${content.content_type} | 
                        <strong>Status:</strong> ${content.status}
                        ${content.seo_score ? ` | <strong>SEO Score:</strong> ${content.seo_score}/100` : ''}
                    </div>
                    
                    ${content.meta_description ? `
                        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0;">
                            <strong>Meta Description:</strong> ${content.meta_description}
                        </div>
                    ` : ''}
                    
                    ${content.keywords && content.keywords.length > 0 ? `
                        <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
                            <strong>Keywords:</strong> ${content.keywords.join(', ')}
                        </div>
                    ` : ''}
                    
                    ${content.image_suggestions && content.image_suggestions.length > 0 ? `
                        <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 10px 0;">
                            <strong>Suggested Images:</strong>
                            <ul>
                                ${content.image_suggestions.map(img => `<li>${img}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    <div style="background: white; padding: 20px; border: 1px solid #ddd; border-radius: 8px; margin: 10px 0;">
                        <h3>Content:</h3>
                        ${content.platform === 'blog' ? 
                            content.content : 
                            `<pre style="white-space: pre-wrap; font-family: inherit;">${content.content}</pre>`
                        }
                    </div>
                    
                    ${content.hashtags && content.hashtags.length > 0 ? `
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
                            <strong>Hashtags:</strong> ${content.hashtags.join(' ')}
                        </div>
                    ` : ''}
                `;
                
                modal.style.display = 'block';
            } catch (error) {
                alert('Error loading content: ' + error.message);
            }
        }
        
        async function publishContent(contentId) {
            if (!confirm('Are you sure you want to publish this content to Shopify?')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/publish/${contentId}`, {
                    method: 'POST'
                });
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Content published successfully to Shopify!');
                } else {
                    alert('❌ Error publishing content: ' + result.error);
                }
            } catch (error) {
                alert('❌ Network error: ' + error.message);
            }
        }
        
        function closeModal() {
            document.getElementById('contentModal').style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('contentModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
        
        async function viewExistingContent() {
            const startDate = prompt('Enter start date (YYYY-MM-DD):');
            const endDate = prompt('Enter end date (YYYY-MM-DD):');
            
            if (!startDate || !endDate) return;
            
            try {
                const response = await fetch(`/api/content-by-date-range?start=${startDate}&end=${endDate}`);
                const content = await response.json();
                
                if (content.length === 0) {
                    alert('No content found for the specified date range.');
                    return;
                }
                
                // Display existing content
                const previewContent = document.getElementById('previewContent');
                previewContent.innerHTML = content.map(item => `
                    <div class="content-item">
                        <h4>${item.platform.toUpperCase()}: ${item.title}</h4>
                        <p><strong>Type:</strong> ${item.content_type}</p>
                        <p><strong>Status:</strong> ${item.status}</p>
                        <p><strong>Scheduled:</strong> ${item.scheduled_time ? new Date(item.scheduled_time).toLocaleString() : 'Not scheduled'}</p>
                        <button class="preview-btn" onclick="previewContent('${item.id}')">
                            👁️ Preview
                        </button>
                    </div>
                `).join('');
                
                document.getElementById('resultsGrid').style.display = 'grid';
                document.getElementById('summaryContent').innerHTML = `
                    <h4>Found ${content.length} pieces of content</h4>
                    <p>Date range: ${startDate} to ${endDate}</p>
                `;
            } catch (error) {
                alert('Error loading content: ' + error.message);
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/generate-content-for-date', methods=['POST'])
def api_generate_content_for_date():
    """API endpoint to generate content for a specific date"""
    try:
        data = request.json
        target_date_str = data.get('target_date')
        
        if not target_date_str:
            return jsonify({'success': False, 'error': 'target_date is required'})
        
        # Parse date
        target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
        
        # Generate content
        result = content_generator.generate_content_for_date(target_date)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/content/<content_id>')
def api_get_content(content_id):
    """Get specific content piece with full details"""
    try:
        content = db_manager.get_content_piece(content_id)
        if content:
            # Return full content details for preview
            return jsonify({
                'id': content.id,
                'title': content.title,
                'content': content.content,  # Full content
                'platform': content.platform,
                'content_type': content.content_type,
                'status': content.status.value,
                'scheduled_time': content.scheduled_time.isoformat() if content.scheduled_time else None,
                'keywords': content.keywords,
                'hashtags': content.hashtags,
                'image_suggestions': content.image_suggestions,
                'ai_provider': content.ai_provider,
                'holiday_context': content.holiday_context,
                'meta_description': content.meta_description,
                'seo_score': content.seo_score
            })
        else:
            return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/content-by-date-range')
def api_get_content_by_date_range():
    """Get content within a date range"""
    try:
        start_date_str = request.args.get('start')
        end_date_str = request.args.get('end')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start and end dates are required'}), 400
        
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str + 'T23:59:59')
        
        content_list = db_manager.get_content_by_date_range(start_date, end_date)
        return jsonify([content_generator._content_piece_to_dict(cp) for cp in content_list])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weekly-content/<week_id>')
def api_get_weekly_content(week_id):
    """Get all content for a specific week"""
    try:
        content_list = db_manager.get_weekly_content(week_id)
        return jsonify([content_generator._content_piece_to_dict(cp) for cp in content_list])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/publish/<content_id>', methods=['POST'])
def api_publish_content(content_id):
    """Publish content to appropriate platform"""
    try:
        content = db_manager.get_content_piece(content_id)
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        if content.platform == 'blog':
            result = shopify_manager.publish_blog_post(content)
            if result['success']:
                content.status = ContentStatus.PUBLISHED
                db_manager.save_content_piece(content)
            return jsonify(result)
        else:
            return jsonify({'error': f'Publishing to {content.platform} not yet implemented'}), 501
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-content-status/<content_id>', methods=['POST'])
def api_update_content_status(content_id):
    """Update content status (draft, preview, approved, etc.)"""
    try:
        data = request.json
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'status is required'}), 400
        
        content = db_manager.get_content_piece(content_id)
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        content.status = ContentStatus(new_status)
        content.updated_at = datetime.now()
        
        success = db_manager.save_content_piece(content)
        if success:
            return jsonify({'success': True, 'new_status': new_status})
        else:
            return jsonify({'error': 'Failed to update status'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'claude_available': content_generator.claude_client is not None,
        'database_connected': os.path.exists(db_manager.db_path),
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
