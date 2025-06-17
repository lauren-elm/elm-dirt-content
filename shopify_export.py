import csv
import io
from datetime import datetime
from typing import List
import re

class CopyPasteGenerator:
    """Generate copy-paste ready content for ALL platforms"""
    
    def generate_all_content_html(self, content_pieces: List, week_id: str, export_type: str = 'daily') -> str:
        """Generate comprehensive copy-paste interface for all weekly content"""
    
        # Organize content by platform
        blog_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'blog']
        instagram_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'instagram']
        facebook_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'facebook']
        email_content = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'email']
        pinterest_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'pinterest']
        twitter_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() == 'twitter']
    
        # Add export type info to the header
        export_info = "Weekly Export" if export_type == 'weekly' else "Daily Export"
    
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{export_info} - {week_id}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f8f9fa;
                    line-height: 1.6;
                }}
                .header {{
                    background: linear-gradient(135deg, #114817, #4eb155);
                    color: white;
                    padding: 2rem;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 2rem;
                }}
                .export-type {{
                    background: rgba(255,255,255,0.2);
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    display: inline-block;
                    margin-top: 1rem;
                    font-weight: bold;
                }}
                .platform-section {{
                    background: white;
                    margin: 2rem 0;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .platform-header {{
                    padding: 1.5rem;
                    font-size: 1.5rem;
                    font-weight: bold;
                    color: white;
                    margin: 0;
                }}
                .blog-header {{ background: #114817; }}
                .instagram-header {{ background: #E4405F; }}
                .facebook-header {{ background: #1877F2; }}
                .email-header {{ background: #34495e; }}
                .pinterest-header {{ background: #BD081C; }}
                .twitter-header {{ background: #1DA1F2; }}
            
                .content-item {{
                    padding: 2rem;
                    border-bottom: 1px solid #eee;
                }}
                .content-item:last-child {{
                    border-bottom: none;
                }}
                .copy-section {{
                    margin: 1rem 0;
                }}
                .copy-box {{
                    background: #f8f9fa;
                    border: 2px dashed #ddd;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    font-family: 'Monaco', 'Consolas', monospace;
                    font-size: 14px;
                    white-space: pre-wrap;
                    position: relative;
                }}
                .copy-box:hover {{
                    background: #e8f5e8;
                    border-color: #4eb155;
                    transform: translateY(-2px);
                }}
                .copy-box::after {{
                    content: "📋 Click to copy";
                    position: absolute;
                    top: 5px;
                    right: 10px;
                    font-size: 12px;
                    color: #666;
                    opacity: 0;
                    transition: opacity 0.3s;
                }}
                .copy-box:hover::after {{
                    opacity: 1;
                }}
                .html-content {{
                    max-height: 300px;
                    overflow-y: auto;
                    font-size: 12px;
                }}
                .meta-info {{
                    background: #e8f4fd;
                    padding: 1rem;
                    border-radius: 5px;
                    margin: 1rem 0;
                    font-size: 14px;
                }}
                .label {{
                    font-weight: bold;
                    display: block;
                    margin: 1rem 0 0.5rem 0;
                    color: #333;
                }}
                .success-message {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #4eb155;
                    color: white;
                    padding: 1rem 1.5rem;
                    border-radius: 5px;
                    display: none;
                    z-index: 1000;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                .summary-stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                    margin: 2rem 0;
                }}
                .stat-card {{
                    background: white;
                    padding: 1.5rem;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .stat-number {{
                    font-size: 2rem;
                    font-weight: bold;
                    color: #4eb155;
                }}
                .instructions {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 1.5rem;
                    border-radius: 10px;
                    margin: 2rem 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌱 Elm Dirt Content Export</h1>
                <p>Date: {week_id} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <div class="export-type">{export_info}</div>
                <p>💡 Click any gray box to copy its content to your clipboard</p>
            </div>
        
            <div class="instructions">
                <h3>📋 How to Use This Interface:</h3>
                <ol>
                    <li><strong>Click any gray box</strong> to automatically copy content to your clipboard</li>
                    <li><strong>Each section</strong> represents a different platform (Shopify blogs, Instagram, Facebook, etc.)</li>
                    <li><strong>For blogs:</strong> Copy title, HTML content, and meta description into Shopify</li>
                    <li><strong>For social media:</strong> Copy the text content and hashtags</li>
                    <li><strong>For emails:</strong> Copy subject line and body separately</li>
                    <li><strong>Schedule timing:</strong> Use the suggested publish times for optimal engagement</li>
                </ol>
            </div>

            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{len(blog_posts)}</div>
                    <div>Blog Posts</div>
                  </div>
                <div class="stat-card">
                    <div class="stat-number">{len(instagram_posts)}</div>
                    <div>Instagram Posts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(facebook_posts)}</div>
                    <div>Facebook Posts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(email_content)}</div>
                    <div>Email Content</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(pinterest_posts)}</div>
                    <div>Pinterest Posts</div>
                </div>
            </div>
        
            {self._generate_platform_section("📝 Shopify Blog Posts", blog_posts, "blog")}
            {self._generate_platform_section("📱 Instagram Posts", instagram_posts, "instagram")}
            {self._generate_platform_section("👥 Facebook Posts", facebook_posts, "facebook")}
            {self._generate_platform_section("📧 Email Content", email_content, "email")}
            {self._generate_platform_section("📌 Pinterest Posts", pinterest_posts, "pinterest")}
            {self._generate_platform_section("🐦 Twitter Posts", twitter_posts, "twitter")}
            
            <div class="success-message" id="success-message">
                ✅ Copied to clipboard!
            </div>
        
            <script>
                let copyCount = 0;
            
                function copyToClipboard(elementId) {{
                    const element = document.getElementById(elementId);
                    const text = element.innerText;
                
                    navigator.clipboard.writeText(text).then(function() {{
                        showSuccessMessage();
                        trackCopy();
                    }}).catch(function(err) {{
                        // Fallback for older browsers
                        const textArea = document.createElement('textarea');
                        textArea.value = text;
                        document.body.appendChild(textArea);
                        textArea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        showSuccessMessage();
                        trackCopy();
                    }});
                }}
                
                function showSuccessMessage() {{
                    const message = document.getElementById('success-message');
                    message.style.display = 'block';
                    setTimeout(() => {{
                        message.style.display = 'none';
                    }}, 2000);
                }}
                
                function trackCopy() {{
                    copyCount++;
                    if (copyCount === 5) {{
                        showCustomMessage("🎉 You're on a roll! Keep going!");
                    }} else if (copyCount === 10) {{
                        showCustomMessage("💪 Content master! Almost done!");
                    }}
                }}
            
                function showCustomMessage(msg) {{
                    const message = document.getElementById('success-message');
                    const originalText = message.innerText;
                    message.innerText = msg;
                    message.style.display = 'block';
                    setTimeout(() => {{
                        message.style.display = 'none';
                        message.innerText = originalText;
                    }}, 3000);
                }}
            </script>
        </body>
        </html>
        """
    
    def _generate_platform_section(self, title: str, posts: List, platform: str) -> str:
        """Generate HTML section for specific platform"""
        if not posts:
            return f"""
            <div class="platform-section">
                <h2 class="platform-header {platform}-header">{title}</h2>
                <div class="content-item">
                    <p>No {platform} content generated for this week.</p>
                </div>
            </div>
            """
        
        posts_html = ""
        for i, post in enumerate(posts, 1):
            posts_html += self._generate_content_item(post, platform, i)
        
        return f"""
        <div class="platform-section">
            <h2 class="platform-header {platform}-header">{title}</h2>
            {posts_html}
        </div>
        """
    
    def _generate_content_item(self, post: dict, platform: str, index: int) -> str:
        """Generate HTML for individual content item"""
        title = post.get('title', f'{platform.title()} Post {index}')
        content = post.get('content', '')
        keywords = post.get('keywords', [])
        scheduled_time = post.get('scheduled_time', '')
        meta_description = post.get('meta_description', '')
        
        # Format keywords
        if isinstance(keywords, list):
            keywords_str = ', '.join(keywords)
        else:
            keywords_str = str(keywords)
        
        # Platform-specific formatting
        if platform == 'blog':
            return self._generate_blog_item(post, index)
        elif platform == 'email':
            return self._generate_email_item(post, index)
        else:
            return self._generate_social_item(post, platform, index)
    
    def _generate_blog_item(self, post: dict, index: int) -> str:
        """Generate blog post item with Shopify-specific fields"""
        title = post.get('title', f'Blog Post {index}')
        content = post.get('content', '')
        meta_description = post.get('meta_description', '')
        keywords = post.get('keywords', '')
        scheduled_time = post.get('scheduled_time', '')
        
        return f"""
        <div class="content-item">
            <h3>{title}</h3>
            
            <div class="meta-info">
                <strong>📅 Suggested Publish:</strong> {scheduled_time}<br>
                <strong>🏷️ Tags for Shopify:</strong> {keywords}<br>
                <strong>📝 Word Count:</strong> ~{len(content.split())} words
            </div>
            
            <div class="copy-section">
                <span class="label">📋 Blog Title (Copy for Shopify):</span>
                <div class="copy-box" onclick="copyToClipboard('blog-title-{index}')" id="blog-title-{index}">{title}</div>
                
                <span class="label">📋 HTML Content (Copy for Shopify Blog Editor):</span>
                <div class="copy-box html-content" onclick="copyToClipboard('blog-content-{index}')" id="blog-content-{index}">{content.replace('<', '&lt;').replace('>', '&gt;')}</div>
                
                <span class="label">📋 Meta Description (Copy for Shopify SEO):</span>
                <div class="copy-box" onclick="copyToClipboard('blog-meta-{index}')" id="blog-meta-{index}">{meta_description}</div>
                
                <span class="label">📋 Tags (Copy for Shopify Tags Field):</span>
                <div class="copy-box" onclick="copyToClipboard('blog-tags-{index}')" id="blog-tags-{index}">{keywords}</div>
            </div>
        </div>
        """
    
    def _generate_email_item(self, post: dict, index: int) -> str:
        """Generate email content item"""
        content = post.get('content', '')
        
        # Extract subject line from content if it exists
        lines = content.split('\n')
        subject_line = "Weekly Garden Update"
        email_body = content
        
        for line in lines:
            if line.startswith('Subject:'):
                subject_line = line.replace('Subject:', '').strip()
                email_body = '\n'.join(lines[1:]).strip()
                break
        
        return f"""
        <div class="content-item">
            <h3>📧 Email Newsletter #{index}</h3>
            
            <div class="meta-info">
                <strong>📅 Suggested Send:</strong> {post.get('scheduled_time', 'Weekly newsletter day')}<br>
                <strong>📊 Estimated Read Time:</strong> {len(email_body.split()) // 200 + 1} minutes
            </div>
            
            <div class="copy-section">
                <span class="label">📋 Subject Line:</span>
                <div class="copy-box" onclick="copyToClipboard('email-subject-{index}')" id="email-subject-{index}">{subject_line}</div>
                
                <span class="label">📋 Email Body:</span>
                <div class="copy-box html-content" onclick="copyToClipboard('email-body-{index}')" id="email-body-{index}">{email_body}</div>
            </div>
        </div>
        """
    
    def _generate_social_item(self, post: dict, platform: str, index: int) -> str:
        """Generate social media content item"""
        title = post.get('title', f'{platform.title()} Post {index}')
        content = post.get('content', '')
        keywords = post.get('keywords', [])
        scheduled_time = post.get('scheduled_time', '')
        
        # Format hashtags for social media
        if isinstance(keywords, list):
            hashtags = ' '.join([f'#{tag.replace(" ", "")}' for tag in keywords])
        else:
            hashtags = str(keywords)
        
        return f"""
        <div class="content-item">
            <h3>{title}</h3>
            
            <div class="meta-info">
                <strong>📅 Suggested Post Time:</strong> {scheduled_time}<br>
                <strong>📱 Platform:</strong> {platform.title()}<br>
                <strong>📊 Character Count:</strong> {len(content)} characters
            </div>
            
            <div class="copy-section">
                <span class="label">📋 {platform.title()} Post Content:</span>
                <div class="copy-box" onclick="copyToClipboard('{platform}-content-{index}')" id="{platform}-content-{index}">{content}</div>
                
                {f'<span class="label">📋 Hashtags:</span><div class="copy-box" onclick="copyToClipboard(\'{platform}-hashtags-{index}\')" id="{platform}-hashtags-{index}">{hashtags}</div>' if hashtags else ''}
            </div>
        </div>
        """
