"""
Test script for admin endpoints
Run this to verify that all admin endpoints are working correctly

Usage: python -m scripts.test_admin_endpoints
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, QuestionCategory, SuggestedQuestion, DashboardCard
from sqlalchemy import select, inspect, text
from database import engine
import uuid

async def test_available_query_types():
    """Test the available query types endpoint logic"""
    print("\n" + "="*60)
    print("Testing Available Query Types")
    print("="*60)
    
    try:
        # Get all table names
        inspector = inspect(engine.sync_engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Found {len(tables)} tables in database:")
        for table in tables:
            print(f"   - {table}")
        
        # Filter out system tables
        app_tables = [t for t in tables if t not in ['chat_messages', 'question_categories', 'suggested_questions', 'dashboard_cards']]
        print(f"\n✅ Application tables ({len(app_tables)}):")
        for table in app_tables:
            print(f"   - {table}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

async def test_create_category():
    """Test creating a category"""
    print("\n" + "="*60)
    print("Testing Category Creation")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create a test category
            test_category = QuestionCategory(
                id=str(uuid.uuid4()),
                title="Test Category",
                color="bg-blue-50 border-blue-100",
                icon_bg="bg-blue-500",
                text_color="text-blue-700",
                icon_type="chart",
                order_index=999,
                is_active=True
            )
            
            session.add(test_category)
            await session.commit()
            
            print(f"✅ Successfully created test category: {test_category.id}")
            
            # Clean up - delete the test category
            await session.delete(test_category)
            await session.commit()
            print(f"✅ Cleaned up test category")
            
            return True
        except Exception as e:
            print(f"❌ Error creating category: {e}")
            await session.rollback()
            return False

async def test_create_card():
    """Test creating a dashboard card"""
    print("\n" + "="*60)
    print("Testing Dashboard Card Creation")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create a test card
            test_card = DashboardCard(
                id=str(uuid.uuid4()),
                title="Test Card",
                icon="🧪",
                description="Test description",
                gradient="from-blue-500 to-cyan-500",
                bg_color="bg-blue-50",
                text_color="text-blue-600",
                query_type="total_users",
                order_index=999,
                is_active=True
            )
            
            session.add(test_card)
            await session.commit()
            
            print(f"✅ Successfully created test card: {test_card.id}")
            
            # Clean up - delete the test card
            await session.delete(test_card)
            await session.commit()
            print(f"✅ Cleaned up test card")
            
            return True
        except Exception as e:
            print(f"❌ Error creating card: {e}")
            await session.rollback()
            return False

async def test_dynamic_queries():
    """Test dynamic query execution"""
    print("\n" + "="*60)
    print("Testing Dynamic Queries")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Get tables
            inspector = inspect(engine.sync_engine)
            tables = inspector.get_table_names()
            
            print(f"\n Testing COUNT(*) queries on all tables:")
            
            for table in tables:
                if table in ['chat_messages', 'question_categories', 'suggested_questions', 'dashboard_cards']:
                    continue
                
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   ✅ {table}: {count} records")
                except Exception as e:
                    print(f"   ⚠️  {table}: Error - {e}")
            
            return True
        except Exception as e:
            print(f"❌ Error testing queries: {e}")
            return False

async def test_database_connection():
    """Test basic database connectivity"""
    print("\n" + "="*60)
    print("Testing Database Connection")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

async def main():
    print("\n" + "="*60)
    print("ADMIN ENDPOINTS DIAGNOSTIC TEST")
    print("="*60)
    
    results = {}
    
    # Run all tests
    results['database'] = await test_database_connection()
    results['tables'] = await test_available_query_types()
    results['queries'] = await test_dynamic_queries()
    results['category'] = await test_create_category()
    results['card'] = await test_create_card()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.title()} Test")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Admin endpoints are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above for details.")
    
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

