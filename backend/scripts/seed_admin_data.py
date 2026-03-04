"""
Seed script to populate initial admin data:
- Question Categories
- Suggested Questions
- Dashboard Cards

Run this script to quickly set up the system with default data.
Usage: python -m scripts.seed_admin_data
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, QuestionCategory, SuggestedQuestion, DashboardCard
import uuid

# Default Question Categories
DEFAULT_CATEGORIES = [
    {
        'id': str(uuid.uuid4()),
        'title': 'Market Analysis',
        'color': 'bg-blue-50 border-blue-100',
        'icon_bg': 'bg-blue-500',
        'text_color': 'text-blue-700',
        'icon_type': 'chart',
        'order_index': 0,
        'is_active': True
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'Investor Insights',
        'color': 'bg-purple-50 border-purple-100',
        'icon_bg': 'bg-purple-500',
        'text_color': 'text-purple-700',
        'icon_type': 'users',
        'order_index': 1,
        'is_active': True
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'Property Trends',
        'color': 'bg-green-50 border-green-100',
        'icon_bg': 'bg-green-500',
        'text_color': 'text-green-700',
        'icon_type': 'building',
        'order_index': 2,
        'is_active': True
    }
]

# Default Suggested Questions
DEFAULT_QUESTIONS = [
    # Market Analysis questions
    {
        'category_title': 'Market Analysis',
        'questions': [
            'Give me a market overview for the last 12 months',
            'Which regions showed the highest auction activity?',
            'Show me the top-performing properties by final bid',
            'What are the bidding trends over the last 6 months',
            'Compare auction performance across different regions',
            'What is the average sale price by property type?'
        ]
    },
    # Investor Insights questions
    {
        'category_title': 'Investor Insights',
        'questions': [
            'Which investors have been most active recently',
            'Show me the top investors by total bid amount',
            'What is the average bid per investor?',
            'Which investors have the highest success rate?',
            'How many new investors joined in the last quarter?',
            'Show bidding patterns by investor location'
        ]
    },
    # Property Trends questions
    {
        'category_title': 'Property Trends',
        'questions': [
            'What are the most popular property types?',
            'Show me properties with the highest ROI',
            'What is the average days on market for properties?',
            'Compare property values by location',
            'What are the fastest-selling property types?',
            'Show me property distribution by size'
        ]
    }
]

# Default Dashboard Cards
DEFAULT_CARDS = [
    {
        'title': 'Total Properties',
        'icon': '🏠',
        'description': 'Available for auction',
        'gradient': 'from-blue-500 to-cyan-500',
        'bg_color': 'bg-blue-50',
        'text_color': 'text-blue-600',
        'query_type': 'total_properties',
        'order_index': 0,
        'is_active': True
    },
    {
        'title': 'Active Auctions',
        'icon': '🏛️',
        'description': 'Live & upcoming',
        'gradient': 'from-purple-500 to-indigo-500',
        'bg_color': 'bg-purple-50',
        'text_color': 'text-purple-600',
        'query_type': 'total_auctions',
        'order_index': 1,
        'is_active': True
    },
    {
        'title': 'Total Bids',
        'icon': '💰',
        'description': 'Placed by investors',
        'gradient': 'from-green-500 to-emerald-500',
        'bg_color': 'bg-green-50',
        'text_color': 'text-green-600',
        'query_type': 'total_bids',
        'order_index': 2,
        'is_active': True
    },
    {
        'title': 'Live Auctions',
        'icon': '🔴',
        'description': 'Currently active',
        'gradient': 'from-red-500 to-rose-500',
        'bg_color': 'bg-red-50',
        'text_color': 'text-red-600',
        'query_type': 'live_auctions',
        'order_index': 3,
        'is_active': True
    },
    {
        'title': 'Upcoming',
        'icon': '📅',
        'description': 'Scheduled soon',
        'gradient': 'from-orange-500 to-amber-500',
        'bg_color': 'bg-orange-50',
        'text_color': 'text-orange-600',
        'query_type': 'upcoming_auctions',
        'order_index': 4,
        'is_active': True
    },
    {
        'title': 'Total Investors',
        'icon': '👥',
        'description': 'Registered users',
        'gradient': 'from-slate-500 to-gray-500',
        'bg_color': 'bg-slate-50',
        'text_color': 'text-slate-600',
        'query_type': 'total_investors',
        'order_index': 5,
        'is_active': True
    },
    {
        'title': 'Active Investors',
        'icon': '🟢',
        'description': 'Bid in past 6 months',
        'gradient': 'from-emerald-500 to-teal-500',
        'bg_color': 'bg-emerald-50',
        'text_color': 'text-emerald-600',
        'query_type': 'active_investors',
        'order_index': 6,
        'is_active': True
    },
    {
        'title': 'Inactive Investors',
        'icon': '⚪',
        'description': 'No bids in 6 months',
        'gradient': 'from-gray-400 to-slate-400',
        'bg_color': 'bg-gray-50',
        'text_color': 'text-gray-600',
        'query_type': 'inactive_investors',
        'order_index': 7,
        'is_active': True
    }
]


async def seed_data():
    """Seed the database with default admin data"""
    async with AsyncSessionLocal() as session:
        try:
            print("🌱 Starting seed process...")
            
            # Create categories
            print("\n📁 Creating question categories...")
            category_map = {}
            for cat_data in DEFAULT_CATEGORIES:
                category = QuestionCategory(**cat_data)
                session.add(category)
                category_map[cat_data['title']] = cat_data['id']
                print(f"  ✓ Created category: {cat_data['title']}")
            
            await session.commit()
            
            # Create questions
            print("\n❓ Creating suggested questions...")
            for question_group in DEFAULT_QUESTIONS:
                category_id = category_map.get(question_group['category_title'])
                if not category_id:
                    print(f"  ⚠️  Category not found: {question_group['category_title']}")
                    continue
                
                for idx, question_text in enumerate(question_group['questions']):
                    question = SuggestedQuestion(
                        id=str(uuid.uuid4()),
                        category_id=category_id,
                        question_text=question_text,
                        order_index=idx,
                        is_active=True
                    )
                    session.add(question)
                    print(f"  ✓ Created question in '{question_group['category_title']}': {question_text[:50]}...")
            
            await session.commit()
            
            # Create dashboard cards
            print("\n📊 Creating dashboard cards...")
            for card_data in DEFAULT_CARDS:
                card = DashboardCard(
                    id=str(uuid.uuid4()),
                    **card_data
                )
                session.add(card)
                print(f"  ✓ Created card: {card_data['title']}")
            
            await session.commit()
            
            print("\n✅ Seed process completed successfully!")
            print(f"   - Created {len(DEFAULT_CATEGORIES)} categories")
            print(f"   - Created {sum(len(q['questions']) for q in DEFAULT_QUESTIONS)} questions")
            print(f"   - Created {len(DEFAULT_CARDS)} dashboard cards")
            
        except Exception as e:
            print(f"\n❌ Error during seed: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Admin Data Seeder")
    print("=" * 60)
    asyncio.run(seed_data())

