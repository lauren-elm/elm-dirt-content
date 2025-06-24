# Fixed version with proper string handling

from flask import Flask, request, jsonify, make_response
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

blog_generation_status = {}

class BlogStatus(Enum):
    GENERATING = "generating"
    COMPLETE = "complete" 
    FAILED = "failed"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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
        self.setup_enhanced_database()  # Enhanced schema for blog data
    
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

    def setup_enhanced_database(self):
        """Initialize enhanced database schema for blog enhancements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Add enhanced columns to content_pieces table if they don't exist
        enhanced_columns = [
            ('meta_title', 'TEXT'),
            ('schema_markup', 'TEXT'),
            ('word_count', 'INTEGER'),
            ('reading_time', 'TEXT'),
            ('image_suggestions_json', 'TEXT'),
            ('seo_keywords', 'TEXT'),
            ('blog_tags', 'TEXT'),
            ('featured_image_url', 'TEXT')
        ]
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(content_pieces)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        for column_name, column_type in enhanced_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE content_pieces ADD COLUMN {column_name} {column_type}")
                    logger.info(f"Added column {column_name} to content_pieces table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.error(f"Error adding column {column_name}: {str(e)}")
        
        # Create enhanced blog metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blog_metadata (
                id TEXT PRIMARY KEY,
                content_piece_id TEXT NOT NULL,
                meta_title TEXT,
                meta_description TEXT,
                schema_markup TEXT,
                word_count INTEGER,
                reading_time TEXT,
                seo_score INTEGER,
                keyword_density REAL,
                internal_links_count INTEGER,
                external_links_count INTEGER,
                image_count INTEGER,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (content_piece_id) REFERENCES content_pieces (id)
            )
        ''')
        
        # Create image suggestions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_suggestions (
                id TEXT PRIMARY KEY,
                content_piece_id TEXT NOT NULL,
                position TEXT NOT NULL,
                description TEXT NOT NULL,
                alt_text TEXT NOT NULL,
                style TEXT,
                priority TEXT,
                size TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (content_piece_id) REFERENCES content_pieces (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Enhanced database schema initialized successfully")

    def save_enhanced_content_piece(self, content: ContentPiece) -> bool:
        """Save enhanced content piece with all blog metadata"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract enhanced attributes with defaults
            meta_title = getattr(content, 'meta_title', content.title)
            schema_markup = getattr(content, 'schema_markup', '{}')
            word_count = getattr(content, 'word_count', 0)
            reading_time = getattr(content, 'reading_time', 'Unknown')
            image_suggestions = getattr(content, 'image_suggestions', [])
            
            # Convert image suggestions to JSON string
            image_suggestions_json = json.dumps(image_suggestions) if image_suggestions else '[]'
            
            # Insert main content piece
            cursor.execute('''
                INSERT OR REPLACE INTO content_pieces 
                (id, title, content, platform, content_type, status, scheduled_time, 
                 keywords, hashtags, image_suggestion, ai_provider, created_at, 
                 updated_at, week_id, holiday_context, meta_description, meta_title, 
                 schema_markup, word_count, reading_time, image_suggestions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content.id, content.title, content.content, content.platform,
                content.content_type, content.status.value, 
                content.scheduled_time.isoformat() if content.scheduled_time else None,
                json.dumps(content.keywords), json.dumps(content.hashtags),
                content.image_suggestion, content.ai_provider, 
                content.created_at.isoformat(), content.updated_at.isoformat(),
                content.week_id, content.holiday_context, content.meta_description,
                meta_title, schema_markup, word_count, reading_time, image_suggestions_json
            ))
            
            # Save enhanced blog metadata if it's a blog post
            if content.platform == 'blog':
                self._save_blog_metadata(cursor, content, meta_title, schema_markup, 
                                       word_count, reading_time)
                
                # Save image suggestions
                if image_suggestions:
                    self._save_image_suggestions(cursor, content.id, image_suggestions)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving enhanced content piece: {str(e)}")
            return False

    def _save_blog_metadata(self, cursor, content: ContentPiece, meta_title: str, 
                           schema_markup: str, word_count: int, reading_time: str):
        """Save detailed blog metadata"""
        try:
            # Extract SEO metrics
            content_text = content.content
            keyword_density = self._calculate_keyword_density(content_text, content.keywords)
            internal_links_count = content_text.count('href="/') + content_text.count("href='/")
            external_links_count = content_text.count('href="http') - content_text.count('elmdirt.com')
            image_count = content_text.count('<img')
            
            # Calculate basic SEO score
            seo_score = self._calculate_seo_score(content, meta_title, word_count, 
                                                keyword_density, internal_links_count)
            
            cursor.execute('''
                INSERT OR REPLACE INTO blog_metadata 
                (id, content_piece_id, meta_title, meta_description, schema_markup,
                 word_count, reading_time, seo_score, keyword_density, 
                 internal_links_count, external_links_count, image_count,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"meta_{content.id}", content.id, meta_title, content.meta_description,
                schema_markup, word_count, reading_time, seo_score, keyword_density,
                internal_links_count, external_links_count, image_count,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
        except Exception as e:
            logger.error(f"Error saving blog metadata: {str(e)}")

    def _save_image_suggestions(self, cursor, content_id: str, image_suggestions: List):
        """Save image suggestions to database"""
        try:
            for i, img_suggestion in enumerate(image_suggestions):
                if isinstance(img_suggestion, dict):
                    cursor.execute('''
                        INSERT OR REPLACE INTO image_suggestions
                        (id, content_piece_id, position, description, alt_text, 
                         style, priority, size, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        f"img_{content_id}_{i}", content_id,
                        img_suggestion.get('position', f'image_{i}'),
                        img_suggestion.get('description', ''),
                        img_suggestion.get('alt_text', ''),
                        img_suggestion.get('style', 'standard'),
                        img_suggestion.get('priority', 'medium'),
                        img_suggestion.get('size', '800x600px'),
                        datetime.now().isoformat()
                    ))
                    
        except Exception as e:
            logger.error(f"Error saving image suggestions: {str(e)}")

    def _calculate_keyword_density(self, content: str, keywords: List[str]) -> float:
        """Calculate keyword density for SEO analysis"""
        try:
            if not content or not keywords:
                return 0.0
            
            # Clean content text
            text = re.sub(r'<[^>]+>', '', content.lower())
            word_count = len(text.split())
            
            if word_count == 0:
                return 0.0
            
            # Count keyword occurrences
            keyword_count = 0
            for keyword in keywords:
                keyword_count += text.count(keyword.lower())
            
            return (keyword_count / word_count) * 100
            
        except Exception as e:
            logger.error(f"Error calculating keyword density: {str(e)}")
            return 0.0

    def _calculate_seo_score(self, content: ContentPiece, meta_title: str, 
                           word_count: int, keyword_density: float, 
                           internal_links_count: int) -> int:
        """Calculate basic SEO score (0-100)"""
        try:
            score = 0
            
            # Title optimization (20 points)
            if meta_title and 30 <= len(meta_title) <= 60:
                score += 20
            elif meta_title:
                score += 10
            
            # Meta description (15 points)
            if content.meta_description and 120 <= len(content.meta_description) <= 160:
                score += 15
            elif content.meta_description:
                score += 8
            
            # Content length (20 points)
            if word_count >= 1500:
                score += 20
            elif word_count >= 1000:
                score += 15
            elif word_count >= 500:
                score += 10
            
            # Keyword density (15 points) - optimal range 1-3%
            if 1.0 <= keyword_density <= 3.0:
                score += 15
            elif 0.5 <= keyword_density <= 5.0:
                score += 10
            elif keyword_density > 0:
                score += 5
            
            # Internal links (10 points)
            if internal_links_count >= 3:
                score += 10
            elif internal_links_count >= 1:
                score += 5
            
            # Headers structure (10 points)
            if '<h2>' in content.content and '<h3>' in content.content:
                score += 10
            elif '<h2>' in content.content:
                score += 5
            
            # Images with alt text (10 points)
            img_count = content.content.count('<img')
            alt_count = content.content.count('alt="')
            if img_count > 0 and alt_count == img_count:
                score += 10
            elif alt_count > 0:
                score += 5
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Error calculating SEO score: {str(e)}")
            return 0

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

    def get_blog_analytics(self, week_id: str = None) -> Dict:
        """Get blog analytics and SEO metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_clause = ""
            params = []
            if week_id:
                where_clause = "WHERE cp.week_id = ?"
                params = [week_id]
            
            # Get blog performance metrics
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_blogs,
                    AVG(bm.word_count) as avg_word_count,
                    AVG(bm.seo_score) as avg_seo_score,
                    AVG(bm.keyword_density) as avg_keyword_density,
                    AVG(bm.internal_links_count) as avg_internal_links,
                    AVG(bm.image_count) as avg_images
                FROM content_pieces cp
                LEFT JOIN blog_metadata bm ON cp.id = bm.content_piece_id
                {where_clause} AND cp.platform = 'blog'
            ''', params)
            
            blog_stats = cursor.fetchone()
            conn.close()
            
            return {
                'blog_performance': {
                    'total_blogs': blog_stats[0] if blog_stats else 0,
                    'avg_word_count': round(blog_stats[1] if blog_stats and blog_stats[1] else 0),
                    'avg_seo_score': round(blog_stats[2] if blog_stats and blog_stats[2] else 0, 1),
                    'avg_keyword_density': round(blog_stats[3] if blog_stats and blog_stats[3] else 0, 2),
                    'avg_internal_links': round(blog_stats[4] if blog_stats and blog_stats[4] else 0, 1),
                    'avg_images': round(blog_stats[5] if blog_stats and blog_stats[5] else 0, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving blog analytics: {str(e)}")
            return {}
    
    def _row_to_content_piece(self, row) -> ContentPiece:
        """Convert database row to ContentPiece object"""
        content_piece = ContentPiece(
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
        
        # Add enhanced attributes if they exist in the row
        if len(row) > 16:
            content_piece.meta_title = row[16]
        if len(row) > 17:
            content_piece.schema_markup = row[17]
        if len(row) > 18:
            content_piece.word_count = row[18] or 0
        if len(row) > 19:
            content_piece.reading_time = row[19] or 'Unknown'
        if len(row) > 20:
            try:
                content_piece.image_suggestions = json.loads(row[20]) if row[20] else []
            except (json.JSONDecodeError, TypeError):
                content_piece.image_suggestions = []
        
        return content_piece

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
        """Generate content using Claude API with better error handling"""
        try:
            payload = {
                'model': 'claude-3-5-sonnet-20241022',
                'max_tokens': min(max_tokens, 8000),  # Claude 3.5 Sonnet max is 8192
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }],
                'temperature': 0.7  # Add some creativity
            }
        
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=240  # Give Claude more time
            )
        
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
            
                # Check if response was truncated due to token limit
                if 'usage' in result:
                    output_tokens = result['usage'].get('output_tokens', 0)
                    logger.info(f"Claude used {output_tokens} output tokens")
                    if output_tokens >= max_tokens * 0.95:  # Near token limit
                        logger.warning("Claude response may be truncated due to token limit")
            
                return content
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

class BlogIdeaGenerator:
    def __init__(self, claude_client):
        self.claude_client = claude_client
        self.config = Config()
        
    def generate_seasonal_blog_ideas(self, season: str, date: datetime) -> List[str]:
        """Generate blog ideas using the project prompt for seasonal relevance"""
        
        # Determine seasonal context
        month = date.month
        seasonal_contexts = {
            'spring': {
                'months': [3, 4, 5],
                'focus': 'soil preparation, planting, early growth',
                'challenges': 'late frosts, soil warming, seed starting'
            },
            'summer': {
                'months': [6, 7, 8], 
                'focus': 'maintenance, watering, harvest',
                'challenges': 'heat stress, drought, pest management'
            },
            'fall': {
                'months': [9, 10, 11],
                'focus': 'harvest, preparation, soil building',
                'challenges': 'first frost, winter prep, cleanup'
            },
            'winter': {
                'months': [12, 1, 2],
                'focus': 'planning, indoor growing, tool maintenance', 
                'challenges': 'cold protection, houseplant care, garden planning'
            }
        }
        
        context = seasonal_contexts.get(season, seasonal_contexts['spring'])
        
        # Use the project prompt for generating blog ideas
        blog_ideas_prompt = f"""Generate blog article ideas for my ecommerce Shopify store, focusing on optimizing bestselling products and collections for organic search traffic.

CONTEXT:
- Company: Elm Dirt - Premium organic soil amendments and gardening products
- Target Audience: 40+ year old home gardeners across the United States
- Current Season: {season.title()}
- Current Month: {date.strftime('%B')}
- Seasonal Focus: {context['focus']}
- Common Challenges: {context['challenges']}

BESTSELLING PRODUCTS (from Orders CSV context):
- Ancient Soil (organic worm castings blend) - 482 reviews, top seller
- Plant Juice (liquid organic fertilizer) - 1,626 reviews
- Bloom Juice (flowering plant fertilizer) - 363 reviews
- All-Purpose Soil Mix - 15 reviews
- Worm Castings - 34 reviews

SEMRUSH KEYWORDS (high value for {season}):
- "organic fertilizer" (600 vol, 40 KD, Commercial)
- "{season} gardening" (400 vol, 35 KD, Commercial/Informational) 
- "soil amendments" (300 vol, 30 KD, Commercial)
- "plant nutrition" (250 vol, 28 KD, Informational)
- "garden soil health" (200 vol, 25 KD, Informational)

BRAND VOICE: Expert but approachable tone for 50+ year old home gardeners across the US

Task: Suggest 5 blog article titles with a 2-3 sentence description of each article's essence that would be perfect for {season} {date.strftime('%B')} content.

Requirements:
- Incorporate keywords naturally into titles and descriptions
- Base ideas on seasonal gardening needs and challenges
- Align with user intents (Commercial, Informational)
- Focus on practical, actionable advice for mature gardeners
- Naturally mention Elm Dirt products where relevant

Deliverable Format:
Title: [Blog Post Title]
Essence: [2-3 sentence description]"""

        try:
            if self.claude_client:
                response = self.claude_client.generate_content(blog_ideas_prompt, max_tokens=2000)
                if response:
                    return self._parse_blog_ideas_from_response(response)
            
            # Fallback to curated seasonal ideas
            return self._get_curated_seasonal_ideas(season, date)
            
        except Exception as e:
            logger.error(f"Error generating blog ideas: {str(e)}")
            return self._get_curated_seasonal_ideas(season, date)
    
    def _parse_blog_ideas_from_response(self, response: str) -> List[str]:
        """Parse blog titles from Claude's response"""
        titles = []
        lines = response.split('\n')
        
        for line in lines:
            if line.strip().startswith('Title:'):
                title = line.replace('Title:', '').strip()
                if title and len(title) > 10:  # Basic validation
                    titles.append(title)
        
        # If parsing fails, extract any lines that look like titles
        if not titles:
            for line in lines:
                line = line.strip()
                if (len(line) > 20 and len(line) < 100 and 
                    any(keyword in line.lower() for keyword in ['garden', 'soil', 'plant', 'grow', 'organic']) and
                    not line.startswith(('The', 'A ', 'An ', 'This', 'These', 'For', 'In '))):
                    titles.append(line)
        
        return titles[:5] if titles else []
    
    def _get_curated_seasonal_ideas(self, season: str, date: datetime) -> List[str]:
        """Fallback curated ideas organized by season and timing"""
        
        month = date.month
        
        seasonal_ideas = {
            'spring': {
                3: [  # March
                    "Spring Soil Preparation: Testing and Amending for Garden Success",
                    "Why Your Garden Needs Ancient Soil This Spring: The Living Soil Advantage", 
                    "Early Spring Garden Tasks That Set You Up for Success",
                    "Organic Soil Amendments vs Chemical Fertilizers: What Mature Gardeners Need to Know",
                    "Building Soil Biology: How Worm Castings Transform Your Garden"
                ],
                4: [  # April  
                    "April Planting Guide: Timing Your Garden for Optimal Growth",
                    "Plant Juice for Spring Seedlings: Gentle Nutrition That Works",
                    "Preventing Common Spring Garden Problems with Soil Health",
                    "Container Gardening Success: Soil Mix Secrets for Mature Gardeners", 
                    "Spring Fertilizing Schedule: When and How to Feed Your Garden"
                ],
                5: [  # May
                    "Late Spring Garden Boost: Maximizing Growing Season Potential",
                    "Bloom Juice for Spring Flowers: Getting More Blooms Naturally",
                    "Transplant Shock Prevention: Soil Strategies That Work",
                    "May Garden Maintenance: Essential Tasks for Busy Gardeners",
                    "Building Disease Resistance Through Healthy Soil Biology"
                ]
            },
            'summer': {
                6: [  # June
                    "Summer Soil Management: Keeping Plants Healthy in the Heat", 
                    "Water-Wise Gardening: How Organic Matter Reduces Watering Needs",
                    "June Garden Care: Nutrition Strategies for Peak Growing Season",
                    "Beat the Summer Slump: Plant Juice for Heat-Stressed Gardens",
                    "Mulching and Soil Health: Summer Protection Strategies"
                ],
                7: [  # July
                    "Mid-Summer Garden Revival: Organic Solutions for Tired Plants",
                    "Bloom Juice for Summer Flowers: Extending the Flowering Season", 
                    "July Heat Wave Survival: Soil Strategies That Protect Plants",
                    "Container Garden Care in Summer: Soil and Nutrition Tips",
                    "Summer Pest Management Through Healthy Soil Biology"
                ],
                8: [  # August
                    "Late Summer Garden Success: Preparing for Fall Transitions",
                    "August Soil Building: Setting Up for Fall Planting Season",
                    "Summer Harvest Care: Nutrition for Continuous Production",
                    "Heat Stress Recovery: How Ancient Soil Helps Plants Bounce Back",
                    "Planning Fall Gardens: Soil Preparation in Late Summer"
                ]
            },
            'fall': {
                9: [  # September
                    "Fall Garden Transitions: Soil Care for Season Extension",
                    "September Planting Success: Cool Season Crops and Soil Prep",
                    "Extending the Growing Season with Healthy Soil Biology",
                    "Fall Fertilizing: Why Plant Juice Works Better Than Synthetics", 
                    "Harvest Season Nutrition: Keeping Plants Productive Longer"
                ],
                10: [  # October
                    "October Soil Building: Foundation Work for Next Year's Garden",
                    "Fall Cleanup and Soil Health: What to Leave and What to Remove",
                    "Compost and Worm Castings: Fall Soil Amendment Strategies",
                    "Preparing Garden Beds for Winter: Organic Matter Matters",
                    "Fall Planting Guide: Trees, Shrubs, and Soil Preparation"
                ],
                11: [  # November  
                    "Winter Garden Preparation: Soil Protection Strategies",
                    "November Garden Tasks: Building Soil for Spring Success",
                    "Cover Crops and Green Manures: Natural Soil Building",
                    "Protecting Soil Biology Through Winter: Organic Approaches",
                    "Late Fall Soil Care: Ancient Soil Application Timing"
                ]
            },
            'winter': {
                12: [  # December
                    "Winter Garden Planning: Soil Health as Your Foundation",
                    "Houseplant Care in Winter: Container Soil and Nutrition", 
                    "December Garden Reflection: Learning from This Year's Soil Care",
                    "Indoor Growing Success: Soil Mix Recipes for Winter Gardens",
                    "Planning Next Year's Garden: Soil Improvement Strategies"
                ],
                1: [  # January
                    "New Year Garden Resolutions: Start with Soil Health",
                    "January Planning: Mapping Your Garden's Soil Improvement",
                    "Winter Houseplant Care: Plant Juice for Indoor Success",
                    "Seed Starting Prep: Soil Mix Secrets for Healthy Seedlings", 
                    "Garden Tool Care and Soil Testing: Winter Maintenance Tasks"
                ],
                2: [  # February
                    "February Garden Prep: Early Soil Care for Spring Success",
                    "Seed Starting Success: Ancient Soil for Healthy Transplants",
                    "Late Winter Garden Tasks: Soil Preparation Strategies",
                    "Planning Your Best Garden Yet: Soil Health as Priority One",
                    "Indoor Growing Tips: Winter Container Garden Success"
                ]
            }
        }
        
        # Get ideas for current month, with fallback to season defaults
        month_ideas = seasonal_ideas.get(season, {}).get(month, [])
        if not month_ideas:
            # Fallback to any month in the season
            season_months = seasonal_ideas.get(season, {})
            for month_key in season_months:
                if season_months[month_key]:
                    month_ideas = season_months[month_key]
                    break
        
        return month_ideas[:5] if month_ideas else [
            f"Essential {season.title()} Garden Guide: Soil Health Fundamentals",
            f"{season.title()} Organic Gardening: Plant Nutrition That Works", 
            f"Seasonal Garden Care: {season.title()} Soil Management Tips",
            f"Building Healthy Soil for {season.title()} Success",
            f"{season.title()} Garden Planning: Start with Ancient Soil"
        ]

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
    
    self.blog_idea_generator = BlogIdeaGenerator(self.claude_client)
    
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
                
                # Generate 1 enhanced blog post per day
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

    def generate_single_day_content(self, selected_date: datetime) -> Dict:
        """Generate content for a single day only"""
        try:
            day_id = f"day_{selected_date.strftime('%Y_%m_%d')}"
            season = self.holiday_manager.get_seasonal_focus(selected_date)
            holidays = self.holiday_manager.get_week_holidays(selected_date)
            theme = self.holiday_manager.get_week_theme(selected_date)
        
            logger.info(f"Generating single day content for {selected_date.strftime('%Y-%m-%d')}")
        
            daily_content = []
            day_name = selected_date.strftime('%A')
        
            # Generate 1 enhanced blog post
            daily_blog = self._generate_daily_blog_post(
                date=selected_date,
                day_name=day_name,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=day_id
            )
            daily_content.append(daily_blog)
        
            # Generate daily social content package (8 pieces)
            daily_social = self._generate_daily_content_package(
                date=selected_date,
                day_name=day_name,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=day_id,
                blog_post=daily_blog
            )
            daily_content.extend(daily_social)
        
            return {
                'success': True,
                'day_id': day_id,
                'selected_date': selected_date.isoformat(),
                'season': season,
                'theme': theme,
                'holidays': [(h[0].isoformat(), h[1], h[2], h[3]) for h in holidays],
                'content_pieces': len(daily_content),
                'content_breakdown': self._get_content_breakdown(daily_content),
                'content': [self._content_piece_to_dict(cp) for cp in daily_content]
            }
        
        except Exception as e:
            logger.error(f"Error generating single day content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_social_only_content(self, selected_date: datetime) -> Dict:
        """Generate only social media content (fast)"""
        day_id = f"social_{selected_date.strftime('%Y_%m_%d')}"
        season = self.holiday_manager.get_seasonal_focus(selected_date)
        holidays = self.holiday_manager.get_week_holidays(selected_date)
        theme = self.holiday_manager.get_week_theme(selected_date)
        day_name = selected_date.strftime('%A')

        logger.info(f"Generating social-only content for {selected_date.strftime('%Y-%m-%d')}")

        # Create dummy blog post first (outside try block)
        dummy_blog = ContentPiece(
            id="dummy",
            title=f"{day_name} Garden Focus",
            content="Garden content",
            platform="blog",
            content_type="reference",
            status=ContentStatus.DRAFT,
            scheduled_time=selected_date,
            keywords=self._get_seasonal_keywords(season)[:3],
            hashtags=[],
            image_suggestion="",
            ai_provider="reference",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        try:
            social_content = []

            # Generate social content package (8 pieces)
            social_package = self._generate_daily_content_package(
                date=selected_date,
                day_name=day_name,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=day_id,
                blog_post=dummy_blog
            )
            social_content.extend(social_package)
            logger.info(f"Generated {len(social_content)} social content pieces")

            return {
                'success': True,
                'day_id': day_id,
                'selected_date': selected_date.isoformat(),
                'season': season,
                'theme': theme,
                'content_pieces': len(social_content),
                'content_breakdown': self._get_content_breakdown(social_content),
                'content': [self._content_piece_to_dict(cp) for cp in social_content]
            }

        except Exception as e:
            logger.error(f"Error generating social content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_blog_only_content(self, selected_date: datetime) -> Dict:
        """Generate only blog content (can take longer)"""
        try:
            day_id = f"blog_{selected_date.strftime('%Y_%m_%d')}"
            season = self.holiday_manager.get_seasonal_focus(selected_date)
            holidays = self.holiday_manager.get_week_holidays(selected_date)
            theme = self.holiday_manager.get_week_theme(selected_date)
        
            logger.info(f"Generating blog-only content for {selected_date.strftime('%Y-%m-%d')}")
        
            day_name = selected_date.strftime('%A')
        
            # Generate enhanced blog post with more time allowed
            blog_post = self._generate_daily_blog_post(
                date=selected_date,
                day_name=day_name,
                season=season,
                theme=theme,
                holidays=holidays,
                week_id=day_id
            )
        
            return {
                'success': True,
                'day_id': day_id,
                'selected_date': selected_date.isoformat(),
                'season': season,
                'theme': theme,
                'blog_post': self._content_piece_to_dict(blog_post)
            }
        
        except Exception as e:
            logger.error(f"Error generating blog content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    
    def _generate_daily_blog_post(self, date: datetime, day_name: str, season: str, 
                                  theme: str, holidays: List, week_id: str) -> ContentPiece:
        """Generate a daily blog post using enhanced Claude API or fallback"""
        
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
        
        # Generate blog content using enhanced Claude API or fallback
        if self.claude_client:
            blog_result = self._generate_blog_with_claude(blog_title, keywords, season, holiday_context)
        else:
            blog_result = self._get_enhanced_fallback_blog(blog_title, season, holiday_context, keywords)
        
        content_piece = ContentPiece(
            id=str(uuid.uuid4()),
            title=blog_result['title'],
            content=blog_result['content'],
            platform="blog",
            content_type="daily_blog_post",
            status=ContentStatus.DRAFT,
            scheduled_time=date.replace(hour=8, minute=0, second=0),  # 8am daily
            keywords=keywords,
            hashtags=[],  # Blogs don't typically use hashtags
            image_suggestion=str(blog_result.get('image_suggestions', [])),
            ai_provider="claude" if self.claude_client else "fallback",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            week_id=week_id,
            holiday_context=holiday_context,
            meta_description=blog_result.get('meta_description', '')
        )
        
        # Store additional blog data as attributes
        content_piece.meta_title = blog_result.get('meta_title', blog_title)
        content_piece.schema_markup = blog_result.get('schema_markup', '{}')
        content_piece.word_count = blog_result.get('word_count', 0)
        content_piece.reading_time = blog_result.get('reading_time', 'Unknown')
        content_piece.image_suggestions = blog_result.get('image_suggestions', [])
        
        self.db_manager.save_enhanced_content_piece(content_piece)
        return content_piece

    
    def _generate_blog_with_claude(self, blog_title, keywords, season, holiday_context):
        """Generate enhanced blog with Claude AI using the project prompt"""
    
        prompt = f"""Generate an SEO-optimized blog article in HTML for the title '{blog_title}'. Generate the ENTIRE HTML document in one response without stopping or asking for continuation. Put in image placeholders and suggest what images to use with this blog post.

CONTEXT:
- Season: {season}
- Holiday Context: {holiday_context}
- Company: Elm Dirt - Premium organic soil amendments and gardening products
- Target: Home gardeners aged 35-65 across the United States
- Brand Products: Ancient Soil, Plant Juice, Bloom Juice, Worm Castings
- Keywords: {', '.join(keywords)}

CONTENT REQUIREMENTS:
- 1500-2000 words minimum for comprehensive coverage
- Expert but approachable tone with colloquial elements for 50+ gardeners
- Include practical, actionable advice with specific steps
- Naturally mention Elm Dirt products where relevant with benefits
- Focus on organic, sustainable gardening methods
- Include seasonal timing and regional considerations

HTML STRUCTURE REQUIREMENTS:
- Complete HTML document with proper head and body sections
- Include meta title (50-60 characters), meta description (150-160 characters)
- Use Elm Dirt brand colors (#114817, #4eb155, #c9d393, #fec962) and Poppins font family
- Include engaging introduction (2-3 paragraphs)
- 5-7 main sections with descriptive H2 headings
- 2-3 subsections with H3 headings under each main section
- Use bullet points (ul/li) for actionable tips and lists
- Include pull quotes for key insights
- Naturally mention Elm Dirt products with benefits
- Add product highlight boxes for Elm Dirt products
- Add JSON-LD schema markup for SEO
- Add product highlight boxes for Elm Dirt products with links
- Include image placeholders with detailed descriptions
- Add call-to-action sections linking to product pages

PRODUCT INTEGRATION:
- Link to relevant product pages: /products/ancient-soil, /products/plant-juice, etc.

IMAGE REQUIREMENTS:
- Include 3-5 image placeholders with detailed alt text
- Specify image placement and descriptions
- Include suggested dimensions and style

CRITICAL INSTRUCTIONS:
1. Create the COMPLETE HTML document from <!DOCTYPE html> to </html>
2. Do NOT stop mid-generation or ask "would you like me to continue"
3. Generate ALL content in this single response
4. Include 1000+ words of gardening content
5. Must end with </html> tag
6. MUST include the 4 image placeholders in the specified format

OUTPUT FORMAT: Return complete HTML document starting with <!DOCTYPE html> and including all necessary CSS, content, and schema markup."""

        try:
            if self.claude_client:
                logger.info("Starting Claude AI generation...")
                blog_response = self.claude_client.generate_content(prompt, max_tokens=6000)
        
                if blog_response and len(blog_response) > 1000:
                    logger.info(f"Claude generated {len(blog_response)} characters")
                
                    if '<!DOCTYPE html>' in blog_response and '</html>' in blog_response:
                        logger.info("Claude provided complete HTML blog!")
                        return self._parse_claude_blog_response(blog_response, blog_title, season, keywords)
                    else:
                        logger.warning("Claude response incomplete, using enhanced fallback")
        
            logger.info("Using enhanced fallback for high-quality blog")
            return self._get_enhanced_fallback_blog(blog_title, season, holiday_context, keywords)

        except Exception as e:
            logger.error(f"Error with Claude: {str(e)}")
            return self._get_enhanced_fallback_blog(blog_title, season, holiday_context, keywords)

    def _try_fix_incomplete_html(self, partial_html):
        """Try to fix incomplete HTML from Claude"""
        try:
            # If we have a good start but incomplete end, try to close it properly
            if not partial_html.endswith('</html>'):
                # Look for unclosed tags and try to close them
                if '</body>' not in partial_html:
                    partial_html += '\n</body>'
                if '</html>' not in partial_html:
                    partial_html += '\n</html>'
            
                logger.info("Attempted to fix incomplete HTML")
                return partial_html
        
            return partial_html
        except Exception as e:
            logger.error(f"Error fixing HTML: {str(e)}")
            return None
    
    def _parse_claude_blog_response(self, claude_response, original_title, season, keywords):
        """Parse Claude response and extract components"""
        try:
            content = claude_response.strip()
        
            # Extract meta information
            meta_title = self._extract_meta_title(content, original_title)
            meta_description = self._extract_meta_description(content, original_title, season)
        
            # Count words (remove HTML tags for accurate count)
            text_content = re.sub(r'<[^>]+>', '', content)
            word_count = len(text_content.split())
        
            return {
                'title': original_title,
                'meta_title': meta_title,
                'content': content,  # This is the complete HTML
                'meta_description': meta_description,
                'keywords': ', '.join(keywords),
                'schema_markup': self._extract_schema_from_html(content),
                'image_suggestions': self._generate_image_suggestions(original_title, content, season),
                'word_count': word_count,
                'reading_time': f"{word_count // 200 + 1} min read"
            }
        
        except Exception as e:
            logger.error(f"Error parsing Claude blog response: {str(e)}")
            return self._get_enhanced_fallback_blog(original_title, season, holiday_context, keywords)

    def _extract_schema_from_html(self, html_content):
        """Extract JSON-LD schema from HTML content"""
        try:
            # Look for JSON-LD script tag
            start_marker = '<script type="application/ld+json">'
            end_marker = '</script>'
        
            start_pos = html_content.find(start_marker)
            if start_pos != -1:
                start_pos += len(start_marker)
                end_pos = html_content.find(end_marker, start_pos)
                if end_pos != -1:
                    return html_content[start_pos:end_pos].strip()
        
            return "{}"
        except Exception as e:
            logger.error(f"Error extracting schema: {str(e)}")
            return "{}"

    def _get_enhanced_fallback_blog(self, title, season, holiday_context, keywords):
        """Generate enhanced fallback blog with complete HTML structure"""
    
        meta_title = f"{title} | Expert {season.title()} Gardening Guide | Elm Dirt"
        if len(meta_title) > 60:
            meta_title = f"{title[:30]}... | Elm Dirt Guide"
          
        meta_description = f"Expert guide to {title.lower()} with proven organic methods for {season} gardening success. Professional tips for sustainable garden care."
        if len(meta_description) > 160:
            meta_description = meta_description[:157] + "..."
    
        # Generate comprehensive content
        content_html = self._generate_comprehensive_blog_content(title, season, holiday_context, keywords)
    
        # Wrap in complete HTML template
        full_html = self._wrap_content_in_enhanced_template(
            content_html, title, meta_title, meta_description, keywords, season, holiday_context
        )
    
        # Generate schema and image suggestions
        schema_markup = self._generate_blog_schema(title, content_html, season, keywords)
        image_suggestions = self._generate_image_suggestions(title, content_html, season)
    
        # Verify it's complete HTML
        if not full_html.strip().startswith('<!DOCTYPE html>') or not full_html.strip().endswith('</html>'):
            logger.error("Fallback HTML is incomplete!")
    
        return {
            'title': title,
            'meta_title': meta_title,
            'content': full_html,
            'meta_description': meta_description,
            'keywords': ', '.join(keywords),
            'schema_markup': schema_markup,
            'image_suggestions': image_suggestions,
            'word_count': len(content_html.split()),
            'reading_time': f"{len(content_html.split()) // 200 + 1} min read"
        }

    def _wrap_content_in_enhanced_template(self, content_body, title, meta_title, meta_description, keywords, season, holiday_context):
        """Wrap content in enhanced HTML template with brand styling"""
    
        schema_markup = self._generate_blog_schema(title, content_body, season, keywords)
        keywords_str = ', '.join(keywords) if isinstance(keywords, list) else str(keywords)
    
        # Create the HTML template using string concatenation to avoid f-string issues
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>{meta_title}</title>',
            f'    <meta name="description" content="{meta_description}">',
            f'    <meta name="keywords" content="{keywords_str}">',
            '',
            '    <style>',
            '        body { font-family: Poppins, sans-serif; margin: 0; padding: 20px; background: #f9f7f5; color: #333; line-height: 1.6; }',
            '        .container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }',
            '        .blog-header { text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #c9d393, #e8f4e0); margin: -30px -30px 40px -30px; border-radius: 15px 15px 0 0; }',
            '        .blog-header h1 { font-size: 2.5rem; color: #114817; margin-bottom: 15px; font-weight: 700; }',
            '        h2 { color: #114817; font-size: 1.8rem; margin-top: 40px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #4eb155; }',
            '        h3 { color: #0a2b0d; font-size: 1.4rem; margin-top: 30px; margin-bottom: 15px; }',
            '        p { margin-bottom: 18px; font-size: 1.05rem; }',
            '        ul, ol { margin-bottom: 20px; padding-left: 25px; }',
            '        li { margin-bottom: 10px; }',
            '        .pull-quote { font-size: 1.2rem; color: #114817; font-style: italic; font-weight: 500; padding: 20px 35px; border-left: 4px solid #fec962; margin: 30px 0; background: #f9f7f5; border-radius: 0 10px 10px 0; }',
            '        .product-highlight { background: linear-gradient(135deg, #c9d393, #e8f4e0); padding: 20px; border-radius: 12px; margin: 25px 0; border: 1px solid rgba(17, 72, 23, 0.1); }',
            '        .product-highlight h4 { margin-top: 0; color: #114817; font-size: 1.2rem; }',
            '        .cta-box { background: linear-gradient(135deg, #114817, #0a2b0d); color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 40px 0; }',
            '        .cta-button { display: inline-block; background: #fec962; color: #3a2313; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 15px; }',
            '        strong { color: #114817; font-weight: 600; }',
            '        @media (max-width: 768px) { .blog-header h1 { font-size: 2rem; } }',
            '    </style>',
            '',
            '    <script type="application/ld+json">',
            schema_markup,
            '    </script>',
            '</head>',
            '<body>',
            '    <div class="container">',
            '        <div class="blog-header">',
            f'            <h1>{title}</h1>',
            f'            <p>Expert gardening advice for {season} success with organic methods and sustainable practices</p>',
            '        </div>',
            '',
            '        <div class="main-content">',
            content_body,
            '        ',
            '            <div class="cta-box">',
            f'                <h3>Ready to Transform Your {season.title()} Garden?</h3>',
            f'                <p>Explore our complete line of organic soil amendments and plant nutrition products designed for {season} gardening success.</p>',
            f'                <a href="/collections/soil-amendments" class="cta-button">Shop {season.title()} Solutions</a>',
            '            </div>',
            '        </div>',
            '    </div>',
            '</body>',
            '</html>'
        ]
        
        return '\n'.join(html_parts)
        
    def _generate_comprehensive_blog_content(self, title, season, holiday_context, keywords):
        """Generate comprehensive blog content with integrated image placeholders"""
    
        # Generate season-specific intro
        season_intros = {
           'spring': "Spring has arrived, and it's time to awaken your garden from its winter slumber! As any experienced gardener knows, successful spring gardening starts with understanding your soil's needs and preparing for the growing season ahead.",
           'summer': "Summer gardening brings both opportunities and challenges. The key to thriving plants during the hottest months lies in smart soil management and understanding how to support your garden through heat stress.",
           'fall': "Fall is nature's time for preparation and reflection. Smart gardeners use this season to build soil health and set the foundation for next year's incredible growing season.",
           'winter': "Winter might seem quiet in the garden, but it's actually the perfect time for planning, soil building, and nurturing your indoor plants while dreaming of spring."
        }
    
        intro = season_intros.get(season, "Every season in the garden teaches us something new about working with nature's rhythms and building healthy, productive growing spaces.")
    
        # Build content sections with integrated images
        content_sections = [
            f'<p>{intro}</p>',
            '',
            f'<p>Whether you are a seasoned gardener or just beginning your {season} gardening journey, this comprehensive guide will provide you with proven strategies, expert insights, and practical techniques that make the difference between a struggling garden and a thriving ecosystem.</p>',
            '',
            # HERO IMAGE
            self._create_image_placeholder(
                position='hero',
                description=f"Wide shot of a thriving {season} garden showcasing healthy plants and rich soil",
                alt_text=f"{title} - {season} gardening guide",
                size='1200x600px'
            ),
            '',
            '<div class="pull-quote">',
            '    "The health of your plants is a direct reflection of the health of your soil ecosystem."',
            '</div>',
            '',
            f'<h2>Understanding {season.title()} Garden Fundamentals</h2>',
            '',
            f'<p>Every season presents unique opportunities and challenges for home gardeners. During {season}, your plants have specific environmental needs that must be met for optimal growth, health, and productivity.</p>',
            '',
            f'<p><strong>Key considerations for {season} gardening include:</strong></p>',
            '',
            '<ul>',
            '<li><strong>Soil temperature and moisture management</strong> for optimal root development</li>',
            '<li><strong>Seasonal pest and disease prevention</strong> using integrated organic methods</li>',
            '<li><strong>Proper nutrition timing</strong> and organic fertilizer application schedules</li>',
            '<li><strong>Weather protection strategies</strong> and microclimate creation</li>',
            '<li><strong>Harvest timing optimization</strong> for peak nutrition and flavor</li>',
            '</ul>',
            '',
            f'<h2>Building Living Soil: The Foundation of {season.title()} Success</h2>',
            '',
            # SOIL IMAGE
            self._create_image_placeholder(
                position='soil_closeup',
                description="Close-up of rich, dark organic soil showing texture and beneficial organisms",
                alt_text="Rich organic garden soil with visible texture",
                size='800x600px'
            ),
            '',
            '<p>The secret to any thriving garden lies beneath the surface in the complex ecosystem of living soil. <strong>Healthy, biologically active soil provides the stable foundation</strong> that supports vigorous plant growth, natural pest resistance, and abundant harvests.</p>',
            '',
            '<h3>Essential Components of Healthy Soil</h3>',
            '',
            '<p>Understanding what makes soil truly alive helps us make better decisions about amendments and care practices.</p>',
            '',
            '<ul>',
            '<li><strong>Beneficial Microorganisms:</strong> Billions of bacteria, fungi, and other microbes that break down organic matter and protect plant roots</li>',
            '<li><strong>Optimal pH Balance:</strong> Proper soil acidity/alkalinity (typically 6.0-7.0) for maximum nutrient availability</li>',
            '<li><strong>Soil Structure:</strong> Well-aggregated soil with proper drainage and moisture retention</li>',
            '<li><strong>Organic Matter Content:</strong> Decomposed materials that feed soil life and improve water retention</li>',
            '</ul>',
            '',
            '<div class="product-highlight">',
            '    <h4>🌱 Ancient Soil</h4>',
            f'    <p>Our premium blend combines worm castings, biochar, sea kelp meal, aged bat guano, and volcanic azomite to create a complete, living soil ecosystem that supports optimal plant health from the ground up. Perfect for {season} soil building.</p>',
            '</div>',
            '',
            f'<h2>Organic {season.title()} Management Strategies</h2>',
            '',
            # GARDENER ACTION IMAGE
            self._create_image_placeholder(
                position='gardening_action',
                description=f"Gardener applying organic soil amendments in {season} garden",
                alt_text=f"Organic gardening techniques for {season}",
                size='800x600px'
            ),
            '',
            f'<p>Implementing proven organic gardening practices during {season} helps build long-term soil health while producing safe, nutritious food for your family.</p>',
            '',
            '<h3>Integrated Pest Management</h3>',
            '',
            '<p><strong>Prevention is always more effective</strong> than treatment when dealing with garden pests. Healthy plants in nutrient-rich soil naturally resist pest damage through stronger immune systems and better root development.</p>',
            '',
            '<h3>Seasonal Nutrition Management</h3>',
            '',
            '<p>Plants have varying nutritional requirements throughout their growth cycles. <strong>Understanding when and how to provide proper nutrition</strong> ensures optimal development without waste or environmental impact.</p>',
           '',
            '<div class="product-highlight">',
            '    <h4>🌿 Plant Juice</h4>',
            f'    <p>Our micronutrient and probiotic formula provides over 250 beneficial microorganisms that work continuously to break down organic matter and make nutrients available when plants need them most. Ideal for {season} feeding schedules.</p>',
           '</div>',
           '',
           f'<h2>Essential {season.title()} Maintenance Schedule</h2>',
           '',
            f'<p>Consistent attention to key maintenance tasks throughout {season} ensures your garden continues to thrive and produce at its maximum potential.</p>',
            '',
            '<h3>Weekly Garden Tasks</h3>',
            '',
           '<ul>',
            '<li><strong>Soil Moisture Monitoring:</strong> Check soil 2-3 inches deep and adjust watering as needed</li>',
            '<li><strong>Plant Health Inspection:</strong> Look for early signs of pest or disease issues</li>',
            '<li><strong>Growth Assessment:</strong> Monitor plant development and adjust support as needed</li>',
            '<li><strong>Harvest Planning:</strong> Identify crops approaching harvest time</li>',
            '</ul>',
            '',
            '<h3>Monthly Soil Health Activities</h3>',
           '',
            '<ul>',
            '<li><strong>Organic Matter Addition:</strong> Apply compost or worm castings as needed</li>',
            '<li><strong>Soil Biology Support:</strong> Add beneficial microorganisms through liquid fertilizers</li>',
            '<li><strong>pH Monitoring:</strong> Test and adjust soil pH if necessary</li>',
            '<li><strong>Nutrient Assessment:</strong> Evaluate plant health and feeding schedules</li>',
            '</ul>',
            '',
            '<div class="product-highlight">',
            '    <h4>🌸 Bloom Juice</h4>',
            f'    <p>Specially formulated for flowering and fruiting plants, Bloom Juice provides the phosphorus, calcium, and micronutrients needed for abundant {season} blooms and harvests.</p>',
           '</div>',
           '',
           # RESULTS IMAGE
           self._create_image_placeholder(
              position='garden_results',
              description=f"Healthy thriving {season} garden showing results of organic care",
              alt_text=f"Successful {season} garden with organic methods",
              size='800x600px'
            ),
           '',
           f'<h2>Troubleshooting Common {season.title()} Challenges</h2>',
           '',
           f'<p>Every gardener faces challenges, but understanding common {season} issues helps you respond quickly and effectively.</p>',
           '',
           '<h3>Environmental Stress Management</h3>',
           '',
           f'<p>Weather fluctuations during {season} can stress plants. Building soil health creates a buffer that helps plants cope with environmental challenges more effectively.</p>',
          '',
           '<h3>Natural Problem Prevention</h3>',
           '',
           '<p>The best defense against garden problems is creating conditions where plants can thrive naturally. Strong, healthy plants grown in living soil resist many common issues.</p>',
           '',
           f'<h2>Your Path to {season.title()} Garden Success</h2>',
           '',
           f'<p><strong>Success in {season} gardening comes from understanding that healthy gardens are living ecosystems</strong> where soil organisms, plants, and gardeners work together in harmony. By focusing on soil health first and implementing organic practices, you will create a garden that produces abundantly this {season} and continues to improve year after year.</p>',
           '',
          f'<p>The investment you make in building soil health will pay dividends not just this {season}, but for many seasons to come as your garden ecosystem matures and flourishes. Remember, every small step toward organic, sustainable gardening practices contributes to both your family health and environmental stewardship.</p>',
           '',
           '<p>Start with one improvement this week - whether it is adding organic matter to your soil, switching to organic fertilizers, or simply observing your garden more closely. Your plants will respond positively, and you will gain confidence in your ability to work with nature rather than against it.</p>'
        ]
    
        return '\n'.join(content_sections)

    
    def _extract_meta_title(self, content, original_title):
        """Extract or generate SEO-optimized meta title"""
        if '<title>' in content:
            start = content.find('<title>') + 7
            end = content.find('</title>')
            if end > start:
                return content[start:end].strip()
        
        # Generate optimized meta title (50-60 characters)
        base_title = original_title[:35] if len(original_title) > 35 else original_title
        return f"{base_title} | Expert Guide | Elm Dirt"

    def _extract_meta_description(self, content, original_title, season):
        """Extract or generate SEO-optimized meta description"""
        if 'meta name="description"' in content:
            start = content.find('content="', content.find('meta name="description"')) + 9
            end = content.find('"', start)
            if end > start:
                return content[start:end].strip()
        
        # Generate fallback meta description
        return f"Expert guide to {original_title.lower()} with proven organic methods for {season} gardening success. Professional tips and sustainable practices."

    def _generate_blog_schema(self, title, content, season, keywords):
        """Generate comprehensive JSON-LD schema markup"""
        
        # Extract description for schema
        if '<p>' in content:
            start = content.find('<p>') + 3
            end = content.find('</p>')
            if end > start:
                description = content[start:end].strip()
                # Clean HTML tags
                description = re.sub(r'<[^>]+>', '', description)
                if len(description) > 160:
                    description = description[:157] + "..."
            else:
                description = f"Expert guide to {title.lower()} for {season} gardening success."
        else:
            description = f"Expert guide to {title.lower()} for {season} gardening success."
        
        schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": description,
            "author": {
                "@type": "Organization",
                "name": "Elm Dirt",
                "url": "https://elmdirt.com"
            },
            "publisher": {
                "@type": "Organization",
                "name": "Elm Dirt",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://cdn.shopify.com/s/files/1/0463/8261/2640/files/elm-dirt-logo.png"
                }
            },
            "datePublished": datetime.now().strftime('%Y-%m-%d'),
            "dateModified": datetime.now().strftime('%Y-%m-%d'),
            "keywords": keywords if isinstance(keywords, str) else ', '.join(keywords),
            "wordCount": len(content.split()),
            "inLanguage": "en-US"
        }
        
        return json.dumps(schema, indent=2)

    def _generate_image_suggestions(self, title, content, season):
        """Generate detailed image suggestions for the blog post"""
        
        suggestions = [
            {
                'position': 'hero',
                'description': f"Wide shot of a thriving {season} garden showcasing healthy plants and rich soil",
                'alt_text': f"{title} - {season} gardening guide",
                'style': 'landscape',
                'priority': 'high',
                'size': '1200x600px'
            },
            {
                'position': 'section_1',
                'description': f"Close-up of rich, dark organic soil with visible texture and beneficial organisms",
                'alt_text': 'Healthy organic garden soil with rich texture',
                'style': 'close-up',
                'priority': 'high',
                'size': '800x600px'
            },
            {
                'position': 'product_section',
                'description': f"Gardener applying Elm Dirt products to {season} garden bed",
                'alt_text': 'Application of organic soil amendments in garden',
                'style': 'action shot',
                'priority': 'medium',
                'size': '800x600px'
            }
        ]
        
        return suggestions

    def _generate_daily_blog_title(self, date: datetime, day_name: str, season: str, theme: str, holidays: List) -> str:
        """Generate seasonally relevant blog post titles using Claude AI or curated ideas"""
        
        # Check for holidays first (keep existing holiday logic)
        for holiday_date, holiday_name, gardening_focus, content_theme in holidays:
            if holiday_date.date() == date.date():
                return f"{holiday_name} Garden Guide: {content_theme} for {season.title()} Success"
    
        # Generate or get seasonal blog ideas
        try:
            seasonal_ideas = self.blog_idea_generator.generate_seasonal_blog_ideas(season, date)
        
            if seasonal_ideas:
                # Use a deterministic selection based on the date to ensure consistency
                # This ensures the same date always gets the same title
                title_index = (date.day - 1) % len(seasonal_ideas)
                selected_title = seasonal_ideas[title_index]
            
                logger.info(f"Selected blog title for {date.strftime('%B %d')}: {selected_title}")
                return selected_title
        
        except Exception as e:
            logger.error(f"Error getting seasonal blog ideas: {str(e)}")
    
        # Final fallback to essential seasonal topics
        fallback_titles = {
            'spring': [
                 "Spring Soil Preparation: Your Complete Success Guide",
                 "Why Ancient Soil Transforms Spring Gardens", 
                 "Plant Juice for Spring Growth: Organic Nutrition That Works",
                 "Spring Garden Success: Building Healthy Soil Biology",
                 "Essential Spring Tasks: Soil Health Fundamentals"
            ],
             'summer': [
                 "Summer Garden Care: Soil Strategies for Heat Success",
                 "Beat Summer Heat: How Healthy Soil Protects Plants",
                 "Bloom Juice for Summer Gardens: Continuous Flowering Tips", 
                 "Summer Soil Management: Water-Wise Organic Strategies",
                 "Mid-Summer Plant Nutrition: Organic Solutions That Work"
             ],
             'fall': [
                 "Fall Soil Building: Foundation for Next Year's Success",
                 "Autumn Garden Care: Organic Soil Preparation Guide",
                 "Fall Planting Success: Soil Health Strategies",
                 "October Garden Tasks: Building Living Soil",
                 "Preparing Garden Soil for Winter: Organic Approaches"
             ],
             'winter': [
                 "Winter Garden Planning: Start with Soil Health",
                 "Indoor Growing Success: Container Soil Strategies", 
                 "Houseplant Care: Plant Juice for Winter Growth",
                 "Planning Your Best Garden: Soil Improvement Guide",
                 "Winter Soil Care: Organic Matter and Amendments"
             ]
         }
    
        fallback_list = fallback_titles.get(season, fallback_titles['spring'])
        title_index = (date.day - 1) % len(fallback_list)
        return fallback_list[title_index]
    
    def get_related_blog_suggestions(self, current_title: str, season: str) -> List[str]:
        """Generate related article suggestions based on current blog topic"""
    
        if not self.claude_client:
            return self._get_fallback_related_suggestions(current_title, season)
    
        related_prompt = f"""Based on the blog article title "{current_title}" for a {season} gardening blog, suggest 3 related article ideas that would interest 40+ year old home gardeners.

Context:
- Company: Elm Dirt - Organic soil amendments and plant nutrition
- Products: Ancient Soil, Plant Juice, Bloom Juice, Worm Castings
- Season: {season}
- Audience: Experienced home gardeners aged 40+

Requirements:
- Topics should complement but not duplicate the main article
- Focus on practical, actionable advice
- Include organic/sustainable approaches
- Naturally incorporate Elm Dirt products where relevant

Format: Just list 3 title suggestions, one per line."""

        try:
            response = self.claude_client.generate_content(related_prompt, max_tokens=500)
            if response:
                suggestions = [line.strip() for line in response.split('\n') if line.strip() and len(line.strip()) > 10]
                return suggestions[:3]
        except Exception as e:
            logger.error(f"Error generating related suggestions: {str(e)}")
    
        return self._get_fallback_related_suggestions(current_title, season)

    def _get_fallback_related_suggestions(self, current_title: str, season: str) -> List[str]:
        """Fallback related article suggestions"""
    
        # Analyze current title for topic focus
        title_lower = current_title.lower()
    
        if 'soil' in title_lower:
            return [
                f"Plant Nutrition Basics: Feeding Your {season.title()} Garden Naturally",
                f"Compost vs Worm Castings: Which is Better for {season.title()}?",
                f"Common {season.title()} Soil Problems and Organic Solutions"
            ]
        elif 'plant' in title_lower or 'nutrition' in title_lower:
            return [
                f"Soil Testing Made Simple: {season.title()} Garden Assessment",
                f"Organic vs Synthetic Fertilizers: Best Choice for {season.title()}",
                f"Building Soil Biology for Long-Term {season.title()} Success" 
            ]
        elif 'bloom' in title_lower or 'flower' in title_lower:
            return [
                f"Container Flower Gardening: {season.title()} Soil and Care Tips",
                f"Extending Bloom Time: Organic Nutrition Strategies",
                f"Pollinator-Friendly {season.title()} Gardens: Soil to Success"
            ]
        else:
            return [
                f"Essential {season.title()} Garden Tasks: Month-by-Month Guide",
                f"Organic Garden Success: Building Healthy Soil Biology",
                f"Ancient Soil vs Regular Compost: The Difference Makers"
            ]

    def _generate_daily_content_package(self, date: datetime, day_name: str, season: str, 
                                       theme: str, holidays: List, week_id: str, 
                                       blog_post: ContentPiece) -> List[ContentPiece]:
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
            post_types = ['educational_tip', 'product_spotlight', 'community_question', 'seasonal_advice']
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
            
            self.db_manager.save_enhanced_content_piece(content_piece)
            posts.append(content_piece)
        
        return posts

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
            
            hashtags = ['organicgardening', 'elmdirt', 'plantcare', f'{season}gardening', 'gardenlife', 'growyourown']
        
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
            
            hashtags = ['organicgardening', 'elmdirt', 'sustainablegardening', 'gardenlife', f'{season}gardening']
        
        return {
            'content': content,
            'hashtags': hashtags,
            'image_suggestion': f"{season.title()} garden photo featuring {post_type.replace('_', ' ')} for {platform}",
            'post_type': post_type
        }

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
        
        self.db_manager.save_enhanced_content_piece(content_piece)
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
        
        self.db_manager.save_enhanced_content_piece(content_piece)
        return content_piece

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
- Welcome and channel introduction
- What viewers will learn in this complete guide
- Why {season} gardening matters for {video_focus}
- Quick preview of Elm Dirt products we will discuss

SECTION 1: FOUNDATION KNOWLEDGE (3-15 minutes)
- Understanding {season} growing conditions
- Soil preparation essentials for {season}
- Common mistakes to avoid this {season}
- Why organic methods work better long-term

SECTION 2: SOIL HEALTH DEEP DIVE (15-25 minutes)
- The science of living soil
- How Ancient Soil transforms your garden
- Worm castings and natural fertilizer benefits
- Building soil biology for {season} success
- Demonstration: Testing and improving your soil

SECTION 3: PLANT NUTRITION MASTERY (25-35 minutes)
- Plant Juice: liquid nutrition that works
- When and how to feed plants in {season}
- Bloom Juice for flowering and fruiting plants
- Organic feeding schedules that actually work
- Demonstration: Proper application techniques

SECTION 4: SEASONAL STRATEGIES (35-45 minutes)
- {season.title()}-specific growing techniques
- Problem-solving common {season} challenges
- Water management for {season} conditions
- Pest and disease prevention naturally
- Regional considerations across the US

SECTION 5: ADVANCED TECHNIQUES (45-55 minutes)
- Companion planting for {season}
- Succession planting strategies
- Container gardening optimization
- Greenhouse and indoor growing tips
- Scaling up: from hobby to market garden

WRAP-UP & Q&A (55-60 minutes)
- Key takeaways for {season} success
- Viewer questions from comments
- Next week topic preview
- Where to find Elm Dirt products
- Subscribe and notification bell reminder

RESOURCES MENTIONED:
- Elm Dirt Ancient Soil
- Plant Juice liquid fertilizer
- Bloom Juice for flowering plants
- Worm Castings
- Seasonal planting calendar
- Soil testing guide

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
        
        self.db_manager.save_enhanced_content_piece(content_piece)
        return content_piece

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
        content_dict = {
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
        
        # Add enhanced attributes if they exist
        if hasattr(content_piece, 'meta_title'):
            content_dict['meta_title'] = content_piece.meta_title
        if hasattr(content_piece, 'schema_markup'):
            content_dict['schema_markup'] = content_piece.schema_markup
        if hasattr(content_piece, 'word_count'):
            content_dict['word_count'] = content_piece.word_count
        if hasattr(content_piece, 'reading_time'):
            content_dict['reading_time'] = content_piece.reading_time
        if hasattr(content_piece, 'image_suggestions'):
            content_dict['image_suggestions'] = content_piece.image_suggestions
        
        return content_dict
    
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

# Initialize core services
db_manager = DatabaseManager(Config.DB_PATH)
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
        .api-status { margin: 1rem 0; padding: 1rem; border-radius: 8px; }
        .api-enabled { background: #d1e7dd; color: #0f5132; border-left: 4px solid #198754; }
        .api-disabled { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
        .content-preview { margin-top: 2rem; }
        .content-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; margin-top: 1rem; }
        .content-card { background: white; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.5rem; transition: all 0.3s ease; }
        .content-card:hover { border-color: #4eb155; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .loading { text-align: center; padding: 2rem; color: #666; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #4eb155; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 1rem; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .success-message { background: #d1e7dd; color: #0f5132; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .error-message { background: #f8d7da; color: #721c24; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 Elm Dirt Content Automation</h1>
            <p>Generate 56 pieces of weekly content with enhanced blogs, Claude AI and holiday awareness</p>
        </div>
        <div class="main-content">
            <div id="api-status-notice" class="api-status">
                <strong>🔄 Checking API Status...</strong> Verifying Claude API connection...
            </div>
            <div class="calendar-section">
                <h2 class="section-title">📅 Daily Content Generator</h2>
                <div class="calendar-controls">
                    <div class="week-selector">
                        <label for="week-date">Select Date:</label>
                        <input type="date" id="week-date" />
                    </div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                       <button class="generate-btn" id="social-btn">
                           🚀 Generate Social Media Content (8 pieces)
                       </button>
                       <button class="generate-btn" id="blog-btn" style="background: linear-gradient(135deg, #843648, #6d2a3a);">
                           📝 Generate Enhanced Blog Post (HTML)
                       </button>

                    </div>
                </div>
                <div class="info-box" style="background: #e8f4fd; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4eb155;">
                    <strong>💡 Pro Tip:</strong> Generate social media content first (fast), then create your blog post separately (allows for longer, higher-quality generation).
                </div>
            </div>
            <div class="content-preview" id="content-preview" style="display: none;">
                <h2 class="section-title">📝 Generated Content</h2>
                <div id="content-grid" class="content-grid"></div>
            </div>
        </div>
    </div>
   <script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded successfully');

    function displayBlogContent(blogPost) {
        const contentGrid = document.getElementById('content-grid');
        const contentPreview = document.getElementById('content-preview');
        
        // Show the content preview section
        contentPreview.style.display = 'block';
        
        // Clear existing content
        contentGrid.innerHTML = '';
        
        // Add success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = 'Enhanced blog post generated! Word count: ' + (blogPost.word_count || 'Unknown') + ' words';
        contentGrid.appendChild(successDiv);
        
        // Create blog display card
        const blogCard = document.createElement('div');
        blogCard.className = 'content-card';
        blogCard.style.gridColumn = '1 / -1';
        
        const blogId = 'blog-' + Math.random().toString(36).substr(2, 9);
        
        // Build the content safely using createElement
        const titleDiv = document.createElement('div');
        titleDiv.innerHTML = '<h3>' + blogPost.title + ' <span style="background: #4eb155; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem;">CLAUDE AI</span></h3>';
        
        const gridDiv = document.createElement('div');
        gridDiv.style.display = 'grid';
        gridDiv.style.gridTemplateColumns = '1fr 1fr';
        gridDiv.style.gap = '20px';
        gridDiv.style.margin = '20px 0';
        
        // Preview section
        const previewDiv = document.createElement('div');
        previewDiv.innerHTML = '<h4>Blog Preview</h4>';
        const iframe = document.createElement('iframe');
        iframe.srcdoc = blogPost.content;
        iframe.width = '100%';
        iframe.height = '400';
        iframe.style.border = '1px solid #ddd';
        iframe.style.borderRadius = '5px';
        previewDiv.appendChild(iframe);
        
        // HTML code section
        const codeDiv = document.createElement('div');
        codeDiv.innerHTML = '<h4>HTML Code (Copy to Shopify)</h4>';
        const textarea = document.createElement('textarea');
        textarea.id = blogId;
        textarea.value = blogPost.content;
        textarea.readOnly = true;
        textarea.style.width = '100%';
        textarea.style.height = '400px';
        textarea.style.fontFamily = 'monospace';
        textarea.style.fontSize = '10px';
        textarea.style.border = '1px solid #ddd';
        textarea.style.borderRadius = '5px';
        textarea.style.padding = '10px';
        
        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copy HTML to Clipboard';
        copyBtn.style.background = '#4eb155';
        copyBtn.style.color = 'white';
        copyBtn.style.border = 'none';
        copyBtn.style.padding = '10px 20px';
        copyBtn.style.borderRadius = '5px';
        copyBtn.style.cursor = 'pointer';
        copyBtn.style.fontWeight = 'bold';
        copyBtn.style.marginTop = '10px';
        copyBtn.style.width = '100%';
        copyBtn.onclick = function() {
            textarea.select();
            document.execCommand('copy');
            alert('HTML copied to clipboard!');
        };
        
        codeDiv.appendChild(textarea);
        codeDiv.appendChild(copyBtn);
        
        gridDiv.appendChild(previewDiv);
        gridDiv.appendChild(codeDiv);
        
        blogCard.appendChild(titleDiv);
        blogCard.appendChild(gridDiv);
        contentGrid.appendChild(blogCard);
    }
    
    function setDefaultDate() {
        const today = new Date();
        const dateInput = document.getElementById('week-date');
        if (dateInput) {
            dateInput.value = today.toISOString().split('T')[0];
            console.log('Default date set');
        }
    }
    
    async function checkAPIStatus() {
        try {
            const response = await fetch('/api/check-claude-status');
            const result = await response.json();
            const statusNotice = document.getElementById('api-status-notice');
            
            if (result.claude_enabled) {
                statusNotice.className = 'api-status api-enabled';
                statusNotice.innerHTML = '<strong>✅ Claude AI Enabled</strong>';
            } else {
                statusNotice.className = 'api-status api-disabled';
                statusNotice.innerHTML = '<strong>⚠️ Claude AI Disabled</strong>';
            }
        } catch (error) {
            console.log('API check failed:', error);
        }
    }
    
   async function generateSocialContent() {
        console.log('Social button clicked!');
        const dateInput = document.getElementById('week-date');
        const socialBtn = document.getElementById('social-btn');
        const contentPreview = document.getElementById('content-preview');
        const contentGrid = document.getElementById('content-grid');
    
        if (!dateInput.value) {
            alert('Please select a date');
            return;
        }
    
        const originalText = socialBtn.textContent;
        socialBtn.disabled = true;
        socialBtn.textContent = '🔄 Generating Social Content...';
    
        // Show loading immediately
        contentPreview.style.display = 'block';
        contentGrid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating social media content...</p></div>';
    
        try {
            const response = await fetch('/api/generate-social-content', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_date: dateInput.value })
            });
        
            if (!response.ok) {
                throw new Error('Server responded with status: ' + response.status);
            }
        
            const result = await response.json();
        
            if (result.success) {
                displaySocialContent(result);
            } else {
                throw new Error(result.error || 'Failed to generate social content');
            }
        } catch (error) {
            console.error('Error:', error);
            contentGrid.innerHTML = '<div class="error-message">❌ Error generating social content: ' + error.message + '</div>';
        } finally {
            socialBtn.disabled = false;
            socialBtn.textContent = originalText;
        }
    }

    function displaySocialContent(result) {
        const contentGrid = document.getElementById('content-grid');
    
        // Clear existing content
        contentGrid.innerHTML = '';
    
        // Add success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = 'Generated ' + result.content_pieces + ' social media posts for ' + result.selected_date;
        contentGrid.appendChild(successDiv);
    
        // Simple list display for now
        result.content.forEach(function(post, index) {
            const postCard = document.createElement('div');
            postCard.className = 'content-card';
        
            const postTitle = document.createElement('h4');
            postTitle.textContent = post.platform.toUpperCase() + ' - ' + post.title;
            postCard.appendChild(postTitle);
        
            const postContent = document.createElement('div');
            postContent.style.cssText = 'background: #f8f9fa; padding: 15px; border-radius: 5px; white-space: pre-wrap; margin: 10px 0;';
            postContent.textContent = post.content;
            postCard.appendChild(postContent);
        
            if (post.hashtags && post.hashtags.length > 0) {
                const hashtags = document.createElement('div');
                hashtags.style.cssText = 'color: #4eb155; font-weight: bold; margin-top: 10px;';
                hashtags.textContent = '#' + post.hashtags.join(' #');
                postCard.appendChild(hashtags);
            }
        
            contentGrid.appendChild(postCard);
        });
    }
    
    async function generateBlogContent() {
    console.log('Blog button clicked!');
    
    const dateInput = document.getElementById('week-date');
    const blogBtn = document.getElementById('blog-btn');
    const contentPreview = document.getElementById('content-preview');
    const contentGrid = document.getElementById('content-grid');
    
    if (!dateInput.value) {
        alert('Please select a date');
        return;
    }
    
    blogBtn.disabled = true;
    blogBtn.textContent = '🔄 Generating Enhanced Blog...';
    
    // Show loading message immediately
    contentPreview.style.display = 'block';
    contentGrid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating enhanced HTML blog post...</p><p>Using Claude AI for high-quality content</p><p>This may take 30-60 seconds for best results</p><p>Please wait, do not refresh the page...</p></div>';
    
    try {
        // Start generation
        const response = await fetch('/api/generate-blog-content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_date: dateInput.value })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Start polling for status
            pollBlogStatus(result.blog_id, contentGrid);
        } else {
            throw new Error(result.error || 'Failed to start blog generation');
        }
        
    } catch (error) {
        console.error('Error:', error);
        contentGrid.innerHTML = `<div class="error-message">❌ Error: ${error.message}</div>`;
    } finally {
        blogBtn.disabled = false;
        blogBtn.textContent = '📝 Generate Enhanced Blog Post (HTML)';
    }
}

async function pollBlogStatus(blogId, contentGrid) {
    try {
        const response = await fetch(`/api/blog-status/${blogId}`);
        const result = await response.json();
        
        if (result.success) {
            if (result.status === 'generating') {
                // Update progress
                contentGrid.innerHTML = `<div class="loading"><div class="spinner"></div><p>${result.progress}</p><p>Claude AI is crafting high-quality content...</p><p>Estimated time remaining: 30-45 seconds</p></div>`;
                
                // Poll again in 3 seconds
                setTimeout(() => pollBlogStatus(blogId, contentGrid), 3000);
                
            } else if (result.status === 'complete') {
                // Blog is ready!
                displayBlogContent(result.blog_post);
                
            } else if (result.status === 'failed') {
                contentGrid.innerHTML = `<div class="error-message">❌ Blog generation failed: ${result.error}</div>`;
            }
        }
    } catch (error) {
        console.error('Polling error:', error);
        contentGrid.innerHTML = `<div class="error-message">❌ Error checking status: ${error.message}</div>`;
    }
}
    
    setDefaultDate();
    checkAPIStatus();
    
    const socialBtn = document.getElementById('social-btn');
    const blogBtn = document.getElementById('blog-btn');
    
    if (socialBtn) {
        socialBtn.addEventListener('click', generateSocialContent);
        console.log('Social button listener attached');
    }
    
    if (blogBtn) {
        blogBtn.addEventListener('click', generateBlogContent);
        console.log('Blog button listener attached');
    }
});
</script>
</body>
</html>'''
    
@app.route('/api/check-claude-status')
def check_claude_status():
    """Check if Claude API is enabled and working"""
    claude_enabled = bool(content_generator.claude_client)
    
    return jsonify({
        'claude_enabled': claude_enabled,
        'api_key_configured': Config.CLAUDE_API_KEY != 'your_claude_api_key_here',
        'fallback_mode': not claude_enabled
    })

@app.route('/api/generate-weekly-content', methods=['POST'])
def generate_weekly_content():
    """Generate content for a single day instead of full week"""
    data = request.json
    
    try:
        date_str = data.get('week_start_date')
        if not date_str:
            return jsonify({
                'success': False,
                'error': 'week_start_date is required (YYYY-MM-DD format)'
            }), 400
        
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Generate content for just the selected day
        result = content_generator.generate_single_day_content(selected_date)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error generating daily content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-social-content', methods=['POST'])
def generate_social_content():
    """Generate only social media content (fast)"""
    data = request.json
    
    try:
        logger.info("=== SOCIAL CONTENT GENERATION START ===")
        date_str = data.get('selected_date')
        logger.info(f"Date received: {date_str}")
        
        if not date_str:
            return jsonify({
                'success': False,
                'error': 'selected_date is required (YYYY-MM-DD format)'
            }), 400
        
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        logger.info(f"Date parsed successfully: {selected_date}")
        
        # Generate only social content (no blog)
        logger.info("Starting social content generation...")
        result = content_generator.generate_social_only_content(selected_date)
        logger.info(f"Social content generation completed. Success: {result.get('success')}")
        
        # Add content count info for better feedback
        if result.get('success'):
            result['message'] = f"Generated {result.get('content_pieces', 0)} social media posts successfully!"
            result['breakdown_summary'] = f"Created content for {selected_date.strftime('%A, %B %d, %Y')}"
        
        return jsonify(result)
        
    except ValueError as e:
        logger.error(f"Date parsing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error generating social content: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-blog-content', methods=['POST'])
def generate_blog_content():
    """Generate only blog content (can take longer)"""
    data = request.json
    blog_id = None  # Define it early so it's available in except block 
    
    try:
        logger.info("=== BLOG GENERATION START ===")
        date_str = data.get('selected_date')
        logger.info(f"Date received: {date_str}")
        
        if not date_str:
            return jsonify({
                'success': False,
                'error': 'selected_date is required (YYYY-MM-DD format)'
            }), 400
        
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        blog_id = f"blog_{selected_date.strftime('%Y_%m_%d')}_{int(datetime.now().timestamp())}"
        
        # Start generation status
        blog_generation_status[blog_id] = {
            'status': BlogStatus.GENERATING,
            'progress': 'Starting Claude AI generation...',
            'blog_post': None,
            'error': None
        }
        
        # Start Claude generation in a separate thread
        import threading
        thread = threading.Thread(
            target=generate_claude_blog_background,
            args=(blog_id, selected_date)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with status
        return jsonify({
            'success': True,
            'blog_id': blog_id,
            'status': 'generating',
            'message': 'Claude AI is generating your high-quality blog post...',
            'estimated_time': '45-60 seconds'
        })
        
    except Exception as e:
        logger.error(f"Error starting blog generation: {str(e)}")
        logger.error(f"Error in blog generation route: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_claude_blog_background(blog_id: str, selected_date: datetime):
    """Generate blog with Claude in background thread"""
    try:
        # Update status
        blog_generation_status[blog_id]['progress'] = 'Claude AI is writing your blog...'
        
        day_name = selected_date.strftime('%A')
        season = content_generator.holiday_manager.get_seasonal_focus(selected_date)
        holidays = content_generator.holiday_manager.get_week_holidays(selected_date)
        theme = content_generator.holiday_manager.get_week_theme(selected_date)
        
        # Generate the blog post with Claude
        blog_post = content_generator._generate_daily_blog_post(
            date=selected_date,
            day_name=day_name,
            season=season,
            theme=theme,
            holidays=holidays,
            week_id=f"blog_{selected_date.strftime('%Y_%m_%d')}"
        )
        
        # Mark as complete
        blog_generation_status[blog_id] = {
            'status': BlogStatus.COMPLETE,
            'progress': 'Blog generation complete!',
            'blog_post': content_generator._content_piece_to_dict(blog_post),
            'error': None
        }
        
        logger.info(f"Blog {blog_id} generated successfully with Claude")
        
    except Exception as e:
        logger.error(f"Background blog generation failed: {str(e)}")
        blog_generation_status[blog_id] = {
            'status': BlogStatus.FAILED,
            'progress': 'Generation failed',
            'blog_post': None,
            'error': str(e)
        }

@app.route('/api/blog-status/<blog_id>')
def check_blog_status(blog_id):
    """Check status of blog generation"""
    if blog_id not in blog_generation_status:
        return jsonify({
            'success': False,
            'error': 'Blog ID not found'
        }), 404
    
    status_info = blog_generation_status[blog_id]
    
    return jsonify({
        'success': True,
        'status': status_info['status'].value,
        'progress': status_info['progress'],
        'blog_post': status_info['blog_post'],
        'error': status_info['error']
    })

@app.route('/api/test-enhanced-blog')
def test_enhanced_blog():
    """Test endpoint for enhanced blog generation"""
    try:
        # Test parameters
        test_title = "Spring Garden Soil Preparation: Your Complete Success Guide"
        test_season = "spring"
        test_keywords = ["spring gardening", "soil preparation", "organic gardening", "garden success"]
        test_holiday_context = "Spring Equinox - soil awakening and garden preparation"
        
        # Generate enhanced blog
        if content_generator.claude_client:
            blog_result = content_generator._generate_blog_with_claude(
                test_title, test_keywords, test_season, test_holiday_context
            )
            generation_method = "claude_ai"
        else:
            blog_result = content_generator._get_enhanced_fallback_blog(
                test_title, test_season, test_holiday_context, test_keywords
            )
            generation_method = "enhanced_fallback"
        
        return jsonify({
            'success': True,
            'generation_method': generation_method,
            'blog_result': {
                'title': blog_result['title'],
                'meta_title': blog_result.get('meta_title', ''),
                'meta_description': blog_result['meta_description'],
                'keywords': blog_result['keywords'],
                'word_count': blog_result['word_count'],
                'reading_time': blog_result['reading_time'],
                'has_schema': bool(blog_result.get('schema_markup')),
                'has_images': bool(blog_result.get('image_suggestions')),
                'image_count': len(blog_result.get('image_suggestions', [])),
                'content_preview': blog_result['content'][:500] + '...' if len(blog_result['content']) > 500 else blog_result['content'],
                'full_content_length': len(blog_result['content'])
            },
            'features': {
                'enhanced_html': True,
                'brand_styling': True,
                'seo_optimized': True,
                'schema_markup': True,
                'image_suggestions': True,
                'responsive_design': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/preview-enhanced-blog')
def preview_enhanced_blog():
    """Preview enhanced blog in browser"""
    try:
        # Generate sample blog
        test_title = "Transform Your Garden with Living Soil This Spring"
        test_season = "spring"
        test_keywords = ["living soil", "spring gardening", "organic amendments", "soil health"]
        test_holiday_context = "Spring gardening preparation and soil health"
        
        blog_result = content_generator._get_enhanced_fallback_blog(
            test_title, test_season, test_holiday_context, test_keywords
        )
        
        # Return the complete HTML for preview
        return blog_result['content']
        
    except Exception as e:
        return f"""<html><body><h1>Error Preview</h1><p>{str(e)}</p></body></html>"""

@app.route('/api/blog-analytics/<week_id>')
def get_blog_analytics(week_id):
    """Get detailed blog analytics for a week"""
    try:
        analytics = db_manager.get_blog_analytics(week_id=week_id)
        
        return jsonify({
            'success': True,
            'week_id': week_id,
            'analytics': analytics,
            'generated_at': datetime.now().isoformat()
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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    claude_enabled = bool(content_generator.claude_client)
    
    # Check database status
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        enhanced_tables = ['blog_metadata', 'image_suggestions']
        enhanced_schema_ready = all(table in tables for table in enhanced_tables)
        conn.close()
    except Exception as e:
        enhanced_schema_ready = False
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.1.0 Enhanced',
        'mode': 'claude_ai' if claude_enabled else 'enhanced_fallback_templates',
        'content_schedule': '56 pieces per week (including 6 enhanced daily blogs)',
        'enhanced_features': {
            'enhanced_html_blogs': True,
            'seo_optimization': True,
            'schema_markup': True,
            'image_suggestions': True,
            'blog_analytics': enhanced_schema_ready,
            'brand_styling': True,
            'responsive_design': True
        },
        'features': {
            'weekly_calendar': True,
            'holiday_awareness': True,
            'content_preview': True,
            'database_storage': True,
            'bulk_generation': True,
            'claude_ai_integration': claude_enabled,
            'daily_blog_posts': True,
            'html_formatted_blogs': True,
            'enhanced_database': enhanced_schema_ready
        },
        'services': {
            'claude_api': 'enabled' if claude_enabled else 'disabled',
            'shopify_api': 'configured' if Config.SHOPIFY_PASSWORD != 'your_shopify_password' else 'not_configured',
            'database': 'connected',
            'enhanced_database': 'ready' if enhanced_schema_ready else 'basic'
        }
    }
    
    return jsonify(health_status)

@app.route('/export')
def export_page():
    """Enhanced export page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Content Export</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f8f9fa; }
            .header { background: linear-gradient(135deg, #114817, #4eb155); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem; }
            .section { background: white; padding: 30px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { padding: 15px 30px; margin: 10px; background: #4eb155; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; }
            .btn:hover { background: #3e8e41; }
            .btn:disabled { background: #6c757d; cursor: not-allowed; }
            .info-box { background: #e8f4fd; border-left: 4px solid #4eb155; padding: 15px; margin: 15px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌱 Enhanced Content Export</h1>
            <p>Export your enhanced content with HTML blogs, SEO optimization, and more!</p>
        </div>
        
        <div class="section">
            <h2>📋 Export Enhanced Content</h2>
            <div class="info-box">
                <strong>🆕 Enhanced Features:</strong><br>
                • Complete HTML blogs with CSS styling<br>
                • SEO optimization with meta tags and schema markup<br>
                • Detailed image suggestions with specifications<br>
                • Brand-compliant styling and responsive design
            </div>
            
            <input type="date" id="exportDate" onchange="updateDateInfo()">
            <button class="btn" id="exportBtn" onclick="exportContent()">🚀 Export Enhanced Content</button>
            <button class="btn" onclick="testEnhanced()">🧪 Test Enhanced Features</button>
            
            <div id="dateInfo" style="display: none; margin-top: 15px; padding: 15px; background: #fff3cd; border-radius: 8px;"></div>
            
            <div id="exportResults" style="display: none; margin-top: 20px; padding: 20px; background: #d1e7dd; border-radius: 8px; border-left: 4px solid #198754;">
                <h3>✅ Export Complete!</h3>
                <p>Your content has been generated and opened in a new window for review.</p>
            </div>
        </div>

        <script>
        // Set today's date as default
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('exportDate').value = new Date().toISOString().split('T')[0];
            updateDateInfo();
        });

        function updateDateInfo() {
            const dateInput = document.getElementById('exportDate');
            const dateInfo = document.getElementById('dateInfo');
            
            if (dateInput && dateInput.value) {
                const selectedDate = new Date(dateInput.value + 'T12:00:00');
                const dayOfWeek = selectedDate.getDay();
                const dayName = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][dayOfWeek];
                
                dateInfo.innerHTML = '<h3>📅 Export Content for ' + dayName + '</h3><p><strong>Will Generate:</strong> 1 Enhanced HTML Blog + 3 Instagram + 3 Facebook + 3 TikTok + 1 YouTube Outline = 11 pieces total</p>';
                dateInfo.style.display = 'block';
            }
        }

        async function exportContent() {
            console.log('Export button clicked!');
            
            const dateStr = document.getElementById('exportDate').value;
            if (!dateStr) {
                alert('Please select a date');
                return;
            }
            
            const exportBtn = document.getElementById('exportBtn');
            const originalText = exportBtn.textContent;
            exportBtn.disabled = true;
            exportBtn.textContent = '🔄 Generating Content...';
            
            try {
                console.log('Making API call to /api/export-content');
                const response = await fetch('/api/export-content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ export_date: dateStr })
                });
                
                console.log('API response status:', response.status);
                const result = await response.json();
                console.log('API result:', result);
                
                if (result.success) {
                    displayExportedContent(result);
                    document.getElementById('exportResults').style.display = 'block';
                } else {
                    throw new Error(result.error || 'Failed to export content');
                }
            } catch (error) {
                console.error('Export error:', error);
                alert('Error exporting content: ' + error.message);
            } finally {
                exportBtn.disabled = false;
                exportBtn.textContent = originalText;
            }
        }

        function displayExportedContent(result) {
            console.log('Displaying exported content');
            
            const newWindow = window.open('', '_blank', 'width=1200,height=800,scrollbars=yes');
            
            if (!newWindow) {
                alert('Please allow popups for this site to view the exported content.');
                return;
            }
            
            const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Exported Content - ` + result.export_date + `</title>
                <style>
                    body { font-family: 'Poppins', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
                    .header { background: linear-gradient(135deg, #114817, #4eb155); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem; }
                    .content-section { background: white; margin: 20px 0; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .content-title { color: #114817; font-size: 1.5rem; margin-bottom: 15px; border-bottom: 2px solid #4eb155; padding-bottom: 10px; }
                    .content-meta { background: #e8f4fd; padding: 10px 15px; border-radius: 5px; margin: 10px 0; font-size: 0.9rem; }
                    .blog-content { border: 2px solid #c9d393; border-radius: 8px; padding: 15px; margin: 15px 0; max-height: 400px; overflow-y: auto; }
                    .social-post { background: #f8f9fa; border-left: 4px solid #4eb155; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }
                    .hashtags { color: #4eb155; font-weight: bold; }
                    .breakdown { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; }
                    .breakdown-item { background: #4eb155; color: white; padding: 10px; border-radius: 8px; text-align: center; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🌱 Exported Content</h1>
                    <p>Generated for ` + result.export_date + ` • ` + result.content_count + ` pieces total</p>
                </div>
                
                <div class="content-section">
                    <h2>📊 Content Breakdown</h2>
                    <div class="breakdown">
                        <div class="breakdown-item">
                            <strong>` + result.content_breakdown.blog_posts + `</strong><br>Blog Post
                        </div>
                        <div class="breakdown-item">
                            <strong>` + result.content_breakdown.instagram_posts + `</strong><br>Instagram
                        </div>
                        <div class="breakdown-item">
                            <strong>` + result.content_breakdown.facebook_posts + `</strong><br>Facebook
                        </div>
                        <div class="breakdown-item">
                            <strong>` + result.content_breakdown.tiktok_posts + `</strong><br>TikTok
                        </div>
                        <div class="breakdown-item">
                            <strong>` + result.content_breakdown.youtube_outlines + `</strong><br>YouTube
                        </div>
                    </div>
                </div>
                
                ` + generateContentHTML(result.content) + `
                
            </body>
            </html>`;
            
            newWindow.document.write(htmlContent);
            newWindow.document.close();
        }

        function generateContentHTML(contentArray) {
            let html = '';
            
            contentArray.forEach((content, index) => {
                const platform = content.platform.toUpperCase();
                const contentType = content.content_type.replace('_', ' ').toUpperCase();
                
                html += `
                <div class="content-section">
                    <div class="content-title">
                        ` + (platform === 'BLOG' ? '📝' : platform === 'INSTAGRAM' ? '📸' : platform === 'FACEBOOK' ? '👥' : platform === 'TIKTOK' ? '🎵' : '🎥') + ` 
                        ` + content.title + `
                    </div>
                    
                    <div class="content-meta">
                        <strong>Platform:</strong> ` + platform + ` • 
                        <strong>Type:</strong> ` + contentType + ` • 
                        <strong>Scheduled:</strong> ` + new Date(content.scheduled_time).toLocaleString() + `
                        ` + (content.keywords && content.keywords.length > 0 ? ` • <strong>Keywords:</strong> ` + content.keywords.join(', ') : '') + `
                    </div>
                    
                    ` + (platform === 'BLOG' ? 
                        `<div class="blog-content">
                            <iframe srcdoc="` + content.content.replace(/"/g, '&quot;') + `" width="100%" height="400" style="border: none; border-radius: 5px;"></iframe>
                        </div>` :
                        `<div class="social-post">
                            <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">` + content.content + `</pre>
                            ` + (content.hashtags && content.hashtags.length > 0 ? 
                                `<div class="hashtags" style="margin-top: 10px;">#` + content.hashtags.join(' #') + `</div>` : '') + `
                        </div>`
                    ) + `
                    
                    ` + (content.image_suggestion ? 
                        `<div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>📷 Image Suggestion:</strong> ` + content.image_suggestion + `
                        </div>` : '') + `
                </div>`;
            });
            
            return html;
        }

        function testEnhanced() {
            window.open('/api/preview-enhanced-blog', '_blank');
        }
        </script>
    </body>
    </html>
    '''
                         
@app.route('/api/export-content', methods=['POST'])
def export_content():
    """Export enhanced content for a specific date"""
    try:
        data = request.json
        export_date_str = data.get('export_date')
        
        if not export_date_str:
            return jsonify({
                'success': False,
                'error': 'export_date is required (YYYY-MM-DD format)'
            }), 400
        
        export_date = datetime.strptime(export_date_str, '%Y-%m-%d')
        
        # Generate content for the selected date
        exported_content = []
        
        # 1. Generate 1 HTML Blog Post
        blog_post = content_generator._generate_daily_blog_post(
            date=export_date,
            day_name=export_date.strftime('%A'),
            season=content_generator.holiday_manager.get_seasonal_focus(export_date),
            theme=content_generator.holiday_manager.get_week_theme(export_date),
            holidays=content_generator.holiday_manager.get_week_holidays(export_date),
            week_id=f"export_{export_date.strftime('%Y_%m_%d')}"
        )
        exported_content.append(blog_post)
        
        # 2. Generate 3 Instagram Posts
        instagram_posts = content_generator._generate_platform_posts(
            platform='instagram',
            count=3,
            date=export_date,
            day_name=export_date.strftime('%A'),
            daily_theme=f"{export_date.strftime('%A')} Focus",
            season=content_generator.holiday_manager.get_seasonal_focus(export_date),
            holiday_context=f"{export_date.strftime('%A')} gardening",
            week_id=f"export_{export_date.strftime('%Y_%m_%d')}",
            blog_post=blog_post
        )
        exported_content.extend(instagram_posts)
        
        # 3. Generate 3 Facebook Posts
        facebook_posts = content_generator._generate_platform_posts(
            platform='facebook',
            count=3,
            date=export_date,
            day_name=export_date.strftime('%A'),
            daily_theme=f"{export_date.strftime('%A')} Focus",
            season=content_generator.holiday_manager.get_seasonal_focus(export_date),
            holiday_context=f"{export_date.strftime('%A')} gardening",
            week_id=f"export_{export_date.strftime('%Y_%m_%d')}",
            blog_post=blog_post
        )
        exported_content.extend(facebook_posts)
        
        # 4. Generate 3 TikTok Posts
        for i in range(3):
            tiktok_post = content_generator._generate_tiktok_video_script(
                date=export_date.replace(hour=9+i*3),  # Different times
                day_name=export_date.strftime('%A'),
                daily_theme=f"TikTok Focus {i+1}",
                season=content_generator.holiday_manager.get_seasonal_focus(export_date),
                holiday_context=f"{export_date.strftime('%A')} gardening tip {i+1}",
                week_id=f"export_{export_date.strftime('%Y_%m_%d')}",
                blog_post=blog_post
            )
            exported_content.append(tiktok_post)
        
        # 5. Generate 1 YouTube Outline
        youtube_outline = content_generator._generate_youtube_outline(
            week_start_date=export_date,
            season=content_generator.holiday_manager.get_seasonal_focus(export_date),
            theme=f"{export_date.strftime('%A')} Special Focus",
            holidays=content_generator.holiday_manager.get_week_holidays(export_date),
            week_id=f"export_{export_date.strftime('%Y_%m_%d')}"
        )
        exported_content.append(youtube_outline)
        
        # Convert to serializable format
        export_data = {
            'success': True,
            'export_date': export_date_str,
            'content_count': len(exported_content),
            'content_breakdown': {
                'blog_posts': 1,
                'instagram_posts': 3,
                'facebook_posts': 3,
                'tiktok_posts': 3,
                'youtube_outlines': 1
            },
            'content': [content_generator._content_piece_to_dict(cp) for cp in exported_content]
        }
        
        return jsonify(export_data)
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error exporting content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
            
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
            '/export',
            '/api/check-claude-status',
            '/api/generate-weekly-content',
            '/api/test-enhanced-blog',
            '/api/preview-enhanced-blog',
            '/api/blog-analytics/<week_id>',
            '/api/content/<content_id>',
            '/api/export-content'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    error_message = str(error)
    logger.error("Internal server error: " + error_message)
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'Please check the logs for more details'
    }), 500

# Main application entry point
if __name__ == '__main__':
    logger.info("Starting Enhanced Elm Dirt Content Automation Platform v3.1")
    logger.info(f"Claude API: {'Enabled' if content_generator.claude_client else 'Disabled (using enhanced fallback)'}")
    logger.info("Enhanced Features: Complete HTML blogs, SEO optimization, schema markup, image suggestions")
    logger.info("Content Schedule: 56 pieces per week including 6 enhanced daily blog posts")
    logger.info("Database: SQLite with enhanced schema for blog metadata")
    logger.info("Endpoints: Web interface and enhanced API routes configured")
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 5000))
    
    # Run the application
    app.run(debug=False, host='0.0.0.0', port=port)      

# Complete Enhanced Elm Dirt Content Automation Platform
