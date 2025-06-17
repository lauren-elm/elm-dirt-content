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
        // Check API status on page load
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
                } else {# Enhanced Elm Dirt Content Automation Platform
# Complete version with daily blog posts, Claude API integration, and HTML formatting

from flask import Flask, request, jsonify
from flask_cors import CORS
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
                'model': 'claude-3-sonnet-20240229',
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
            f"Lifestyle shot: Experienced gardener (50+) working in well-maintained organic garden",
            f"Product in use: Plant Juice being applied to plants with visible healthy growth results",
            f"Soil health demonstration: Cross-section of healthy soil showing earthworms and organic matter",
            f"Harvest/bloom shots: Abundant flowers or vegetables showing results of organic methods",
            f"Garden tools and products: Elm Dirt products arranged with quality garden tools and fresh harvest"
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

# Initialize services
db_manager = DatabaseManager(Config.DB_PATH)
content_generator = ContentGenerator(db_manager)

# Web Interface
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
