from flask import Blueprint, jsonify, request
from shopify_export import CopyPasteGenerator
from datetime import datetime

# Create blueprint for export routes
export_bp = Blueprint('export', __name__)

@export_bp.route('/api/export/copy-paste', methods=['POST'])
def export_all_content():
    """Generate copy-paste interface for ALL weekly content"""
    try:
        # Get content from request
        data = request.get_json()
        content_pieces = data.get('content_pieces', [])
        week_id = data.get('week_id', datetime.now().strftime('%Y-W%U'))
        
        if not content_pieces:
            return "<h2>No content found for this week.</h2>"
        
        # Generate comprehensive HTML interface
        generator = CopyPasteGenerator()
        html_content = generator.generate_all_content_html(content_pieces, week_id)
        
        return html_content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@export_bp.route('/api/export/test')
def test_export():
    """Test endpoint with sample weekly content"""
    sample_weekly_content = [
        {
            'title': 'Spring Garden Preparation: Getting Your Soil Ready',
            'content': '''<h2>Preparing Your Garden for Spring Success</h2>
<p>As winter fades and spring approaches, it's time to start thinking about preparing your garden for the growing season. The foundation of any successful garden starts with healthy, well-prepared soil.</p>

<h3>Essential Steps for Soil Preparation</h3>
<ul>
<li>Test your soil pH levels</li>
<li>Add organic matter like compost or aged manure</li>
<li>Remove any weeds or debris from winter</li>
<li>Consider adding beneficial microorganisms</li>
</ul>

<p>Our Ancient Soil blend provides the perfect foundation with worm castings, biochar, and essential nutrients that create a living soil ecosystem for your plants.</p>''',
            'meta_description': 'Essential spring garden preparation tips including soil testing, organic amendments, and creating healthy growing conditions for your plants.',
            'keywords': 'spring gardening, soil preparation, organic gardening, compost, garden soil',
            'platform': 'blog',
            'scheduled_time': '2025-03-15 09:00:00'
        },
        {
            'title': 'Instagram Post - Spring Soil Tips',
            'content': '''Spring is here! 🌱 Time to give your garden the foundation it deserves.

Our Ancient Soil blend transforms ordinary dirt into a thriving ecosystem:
✨ Living microorganisms
🪱 Premium worm castings  
🌿 Biochar for water retention
🌱 Essential nutrients plants crave

Ready to see the difference? Your plants will thank you! 

#SpringGardening #OrganicSoil #GardenLife #ElmDirt #HealthySoil''',
            'keywords': ['SpringGardening', 'OrganicSoil', 'GardenLife', 'ElmDirt', 'HealthySoil'],
            'platform': 'instagram',
            'scheduled_time': '2025-03-15 14:00:00'
        },
        {
            'title': 'Facebook Post - Community Garden Story',
            'content': '''Did you know that healthy soil is home to billions of microorganisms? 🔬

Just one teaspoon of healthy garden soil contains more living organisms than there are people on Earth! That's why we're passionate about creating soil amendments that support this incredible underground ecosystem.

Our customers have seen amazing results when they switch to living soil:
- 40% better water retention
- Stronger, more resilient plants
- Reduced need for synthetic fertilizers
- Healthier vegetables and flowers

What's your biggest gardening challenge this
