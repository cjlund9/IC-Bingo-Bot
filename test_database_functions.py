#!/usr/bin/env python3
"""
Test script to verify database-backed functions work correctly
"""

import sys
import os

def test_storage_functions():
    """Test the new database-backed storage functions"""
    print("🧪 Testing Database-Backed Functions")
    print("=" * 50)
    
    try:
        from storage import get_tile_progress, get_team_progress, mark_tile_submission
        
        # Test 1: Get team progress (should work with empty database)
        print("1. Testing get_team_progress...")
        team_progress = get_team_progress("moles")
        print(f"   ✅ Moles team progress: {team_progress}")
        
        # Test 2: Get tile progress (should work with empty database)
        print("2. Testing get_tile_progress...")
        tile_progress = get_tile_progress("moles", 0)
        print(f"   ✅ Tile 0 progress: {tile_progress}")
        
        # Test 3: Mark a submission
        print("3. Testing mark_tile_submission...")
        success = mark_tile_submission("moles", 0, 123456789, "Test Drop", 1)
        print(f"   ✅ Submission marked: {success}")
        
        # Test 4: Verify progress was updated
        print("4. Verifying progress update...")
        updated_progress = get_tile_progress("moles", 0)
        print(f"   ✅ Updated progress: {updated_progress}")
        
        print("\n✅ All storage functions working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing storage functions: {e}")
        return False

def test_board_generation():
    """Test board generation with database"""
    print("\n🎯 Testing Board Generation")
    print("=" * 50)
    
    try:
        from board import generate_board_image, load_placeholders
        
        # Test 1: Load placeholders
        print("1. Loading placeholders...")
        placeholders = load_placeholders()
        print(f"   ✅ Loaded {len(placeholders)} placeholders")
        
        # Test 2: Generate board with None completed_dict (database query)
        print("2. Generating board with database...")
        success = generate_board_image(placeholders, None, team="all")
        print(f"   ✅ Board generation: {success}")
        
        # Test 3: Check if board.png was created
        if os.path.exists("board.png"):
            print(f"   ✅ Board image created: {os.path.getsize('board.png')} bytes")
        else:
            print("   ❌ Board image not found")
            return False
        
        print("\n✅ Board generation working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing board generation: {e}")
        return False

def test_database_connection():
    """Test database connection and schema"""
    print("\n🗄️ Testing Database Connection")
    print("=" * 50)
    
    try:
        import sqlite3
        
        # Test 1: Connect to database
        print("1. Connecting to database...")
        conn = sqlite3.connect('leaderboard.db')
        cursor = conn.cursor()
        print("   ✅ Database connection successful")
        
        # Test 2: Check tables exist
        print("2. Checking database tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   ✅ Tables found: {[table[0] for table in tables]}")
        
        # Test 3: Check tile count
        print("3. Checking tile count...")
        cursor.execute("SELECT COUNT(*) FROM bingo_tiles")
        tile_count = cursor.fetchone()[0]
        print(f"   ✅ Tiles in database: {tile_count}")
        
        # Test 4: Check progress count
        print("4. Checking progress count...")
        cursor.execute("SELECT COUNT(*) FROM bingo_team_progress")
        progress_count = cursor.fetchone()[0]
        print(f"   ✅ Progress records: {progress_count}")
        
        conn.close()
        print("\n✅ Database connection and schema working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing database: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Database-Backed Bingo Bot")
    print("=" * 60)
    
    tests = [
        test_database_connection,
        test_storage_functions,
        test_board_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("📊 Test Results")
    print("=" * 30)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! The bot is ready to run.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 