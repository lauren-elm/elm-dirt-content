from flask import Blueprint, jsonify, request
from shopify_export import CopyPasteGenerator
from datetime import datetime

# Create blueprint for export routes
export_bp = Blueprint('export', __name__)

@export_bp.route('/api/export/copy-paste', methods=['POST'])
def export_all_content():
    """Generate copy-paste interface for date-based content"""
    try:
        data = request.get_json()
        content_pieces = data.get('content_pieces', [])
        week_id = data.get('week_id', datetime.now().strftime('%Y-%m-%d'))
        export_type = data.get('export_type', 'daily')
        
        if not content_pieces:
            return f"""
            <html>
            <head><title>No Content Found</title></head>
            <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
                <h2>No content found for the selected date</h2>
                <p>Try selecting a different date or check your content generation settings.</p>
                <button onclick="window.close()" style="padding: 10px 20px; background: #4eb155; color: white; border: none; border-radius: 5px;">Close</button>
            </body>
            </html>
            """
        
        # Generate comprehensive HTML interface
        generator = CopyPasteGenerator()
        html_content = generator.generate_all_content_html(content_pieces, week_id, export_type)
        
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

What's your biggest gardening challenge this spring? Let us know in the comments! We love helping fellow gardeners succeed. 🌱''',
            'keywords': ['soil health', 'microorganisms', 'organic gardening', 'sustainable gardening'],
            'platform': 'facebook',
            'scheduled_time': '2025-03-16 10:00:00'
        },
        {
            'title': 'Email Newsletter - Weekly Garden Update',
            'content': '''Subject: Your Spring Garden Checklist (Plus 20% Off Ancient Soil!)

Hello Fellow Gardener! 🌱

Spring is officially here, and your garden is calling! Whether you're a seasoned grower or just getting started, this week is perfect for laying the groundwork for your best garden yet.

THIS WEEK'S GARDEN TASKS:
□ Test soil pH (ideal range: 6.0-7.0 for most vegetables)
□ Add organic matter to garden beds
□ Start seeds indoors for warm-season crops
□ Clean and organize garden tools
□ Plan your garden layout for companion planting

FEATURED PRODUCT: Ancient Soil
This week only, save 20% on our best-selling Ancient Soil blend. Perfect for:
- Revitalizing tired garden beds
- Starting seedlings with premium nutrition
- Improving soil structure and water retention

Customer Spotlight:
"I've been using Ancient Soil for two seasons now, and the difference is incredible. My tomatoes have never been more productive!" - Sarah K., Illinois

SPRING PLANTING REMINDER:
Remember to check your last frost date before transplanting seedlings outdoors. Most areas are still 2-4 weeks away from safe planting time for tender crops.

Happy Gardening!
The Elm Dirt Team

P.S. Reply to this email with photos of your spring prep - we love seeing your gardens come to life!''',
            'keywords': ['spring gardening', 'garden checklist', 'soil preparation', 'organic amendments'],
            'platform': 'email',
            'scheduled_time': '2025-03-17 08:00:00'
        },
        {
            'title': 'Pinterest Pin - Soil Amendment Guide',
            'content': '''🌱 ULTIMATE SOIL AMENDMENT GUIDE 🌱

Transform your garden soil naturally:

ORGANIC MATTER:
- Compost (homemade or bagged)
- Aged manure (cow, chicken, rabbit)
- Leaf mold
- Worm castings ⭐

SOIL CONDITIONERS:
- Biochar (improves structure)
- Perlite (drainage)
- Vermiculite (water retention)
- Coconut coir

NATURAL FERTILIZERS:
- Bone meal (phosphorus)
- Blood meal (nitrogen)
- Kelp meal (trace minerals)
- Ancient Soil blend (all-in-one)

💡 PRO TIP: Test your soil first, then amend based on results!

Save this pin for your spring garden prep! 📌

#OrganicGardening #SoilHealth #GardenTips #SpringGardening #HealthySoil #GardenPrep''',
            'keywords': ['soil amendment', 'organic gardening', 'garden tips', 'spring prep', 'soil health'],
            'platform': 'pinterest',
            'scheduled_time': '2025-03-18 11:00:00'
        }
    ]
    
    return jsonify({
        'message': 'Sample weekly content generated!',
        'content_count': len(sample_weekly_content),
        'platforms': list(set([item['platform'] for item in sample_weekly_content])),
        'test_url': '/api/export/copy-paste (POST with this data)'
    })
