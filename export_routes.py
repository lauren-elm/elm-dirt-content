from flask import Blueprint, jsonify, make_response, request
from shopify_export import ShopifyCSVExporter, CopyPasteGenerator
from datetime import datetime

# Create blueprint for export routes
export_bp = Blueprint('export', __name__)

@export_bp.route('/api/export/csv', methods=['POST'])
def export_blogs_csv():
    """Download CSV file for Shopify import"""
    try:
        # Get blog posts from request
        data = request.get_json()
        blog_posts = data.get('blog_posts', [])
        week_id = data.get('week_id', datetime.now().strftime('%Y-W%U'))
        
        if not blog_posts:
            return jsonify({'error': 'No blog posts provided'}), 400
        
        # Generate CSV
        exporter = ShopifyCSVExporter()
        csv_content = exporter.export_to_csv_string(blog_posts)
        
        # Create response with CSV download
        response = make_response(csv_content)
        response.headers['Content-Disposition'] = f'attachment; filename=elm_dirt_blogs_week_{week_id}.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@export_bp.route('/api/export/copy-paste', methods=['POST'])
def export_copy_paste():
    """Generate copy-paste interface for other content"""
    try:
        # Get content from request
        data = request.get_json()
        content_pieces = data.get('content_pieces', [])
        week_id = data.get('week_id', datetime.now().strftime('%Y-W%U'))
        
        # Filter out blog posts (those go in CSV)
        social_posts = [cp for cp in content_pieces if cp.get('platform', '').lower() != 'blog']
        
        if not social_posts:
            return "<h2>No social media content found for copy-paste.</h2>"
        
        # Generate HTML interface
        generator = CopyPasteGenerator()
        html_content = generator.generate_social_content_html(social_posts, week_id)
        
        return html_content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@export_bp.route('/api/export/test')
def test_export():
    """Test endpoint to verify export functionality"""
    sample_data = [
        {
            'title': 'Test Blog Post',
            'content': '<h2>Sample Content</h2><p>This is a test blog post.</p>',
            'meta_description': 'Test meta description',
            'keywords': 'gardening, test, organic',
            'platform': 'blog'
        },
        {
            'title': 'Social Media Post',
            'content': 'Check out our latest gardening tips! 🌱 #gardening #organic',
            'keywords': ['gardening', 'organic', 'tips'],
            'platform': 'instagram'
        }
    ]
    
    return jsonify({
        'message': 'Export functionality is working!',
        'sample_data': sample_data,
        'endpoints': [
            '/api/export/csv (POST)',
            '/api/export/copy-paste (POST)',
            '/api/export/test (GET)'
        ]
    })
