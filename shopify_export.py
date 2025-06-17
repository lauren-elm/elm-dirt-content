import csv
import io
from datetime import datetime
from typing import List
import re

class ShopifyCSVExporter:
    """Export blog posts as CSV files for Shopify bulk import"""
    
    def __init__(self):
        self.shopify_csv_headers = [
            'Title',
            'Content',
            'Excerpt', 
            'Handle',
            'Published',
            'Tags',
            'Author',
            'Created At',
            'Updated At',
            'Status',
            'SEO Title',
            'SEO Description'
        ]
    
    def export_to_csv_string(self, blog_posts: List) -> str:
        """Export blog posts to CSV string for download"""
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Write headers
        writer.writerow(self.shopify_csv_headers)
        
        # Write blog post data
        for blog_post in blog_posts:
            row = [
                blog_post.get('title', ''),
                self._clean_html_for_csv(blog_post.get('content', '')),
                blog_post.get('meta_description', 'Expert gardening advice from Elm Dirt'),
                self._generate_handle(blog_post.get('title', '')),
                'FALSE',  # Set to draft initially
                blog_post.get('keywords', 'gardening, organic, tips'),
                'Elm Dirt Team',
                blog_post.get('scheduled_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'draft',  # Import as drafts
                blog_post.get('title', ''),
                blog_post.get('meta_description', blog_post.get('title', ''))
            ]
            writer.writerow(row)
        
        return csv_buffer.getvalue()
    
    def _clean_html_for_csv(self, html_content: str) -> str:
        """Clean HTML content for CSV export"""
        return html_content.replace('"', '""')
    
    def _generate_handle(self, title: str) -> str:
        """Generate SEO-friendly handle"""
        if not title:
            return 'blog-post'
        handle = title.lower()
        handle = re.sub(r'[^a-z0-9\s-]', '', handle)
        handle = re.sub(r'\s+', '-', handle)
        handle = re.sub(r'-+', '-', handle)
        return handle.strip('-')[:255]

class CopyPasteGenerator:
    """Generate copy-paste ready content for other platforms"""
    
    def generate_social_content_html(self, social_posts: List, week_id: str) -> str:
        """Generate HTML with copy-paste interface for social content"""
        
        posts_html = ""
        for i, post in enumerate(social_posts, 1):
            platform = post.get('platform', 'social').upper()
            title = post.get('title', f'Post {i}')
            content = post.get('content', '')
            keywords = post.get('keywords', [])
            
            posts_html += f"""
            <div class="content-block">
                <h3>📱 {platform}: {title}</h3>
                <div class="copy-section">
                    <label>Content to copy:</label>
                    <div class="copy-box" onclick="copyToClipboard('content-{i}')" id="content-{i}">
{content}
                    </div>
                    {"<label>Hashtags/Keywords:</label>" if keywords else ""}
                    {"<div class=\"copy-box\" onclick=\"copyToClipboard('tags-" + str(i) + "')\" id=\"tags-" + str(i) + "\">" + (", ".join(keywords) if isinstance(keywords, list) else str(keywords)) + "</div>" if keywords else ""}
                </div>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Content Export - Week {week_id}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f8f9fa;
                }}
                .header {{
                    background: linear-gradient(135deg, #114817, #4eb155);
                    color: white;
                    padding: 2rem;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 2rem;
                }}
                .content-block {{
                    background: white;
                    margin: 2rem 0;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .copy-box {{
                    background: #f8f9fa;
                    border: 2px dashed #ddd;
                    padding: 1rem;
                    margin: 1rem 0;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    font-family: monospace;
                    font-size: 14px;
                    white-space: pre-wrap;
                    max-height: 200px;
                    overflow-y: auto;
                }}
                .copy-box:hover {{
                    background: #e8f5e8;
                    border-color: #4eb155;
                }}
                .copy-section {{
                    margin: 1rem 0;
                }}
                label {{
                    font-weight: bold;
                    display: block;
                    margin-top: 1rem;
                }}
                .success-message {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #4eb155;
                    color: white;
                    padding: 1rem;
                    border-radius: 5px;
                    display: none;
                    z-index: 1000;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌱 Elm Dirt Content Export</h1>
                <p>Week: {week_id} | Generated: {datetime.now().strftime('%B %d, %Y')}</p>
                <p>💡 Click any gray box to copy its content to your clipboard</p>
            </div>
            
            {posts_html}
            
            <div class="success-message" id="success-message">
                ✅ Copied to clipboard!
            </div>
            
            <script>
                function copyToClipboard(elementId) {{
                    const element = document.getElementById(elementId);
                    const text = element.innerText;
                    
                    navigator.clipboard.writeText(text).then(function() {{
                        showSuccessMessage();
                    }}).catch(function(err) {{
                        // Fallback for older browsers
                        const textArea = document.createElement('textarea');
                        textArea.value = text;
                        document.body.appendChild(textArea);
                        textArea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        showSuccessMessage();
                    }});
                }}
                
                function showSuccessMessage() {{
                    const message = document.getElementById('success-message');
                    message.style.display = 'block';
                    setTimeout(() => {{
                        message.style.display = 'none';
                    }}, 2000);
                }}
            </script>
        </body>
        </html>
        """
