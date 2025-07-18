#!/usr/bin/env python3
"""
Quick test script to verify our refactored modules work correctly
"""

import sys
import os
from unittest.mock import MagicMock

# Add resources/lib to path (from tests directory)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources/lib'))

# Mock Kodi modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock() 
sys.modules['xbmcplugin'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()

def test_imports():
    """Test that all our refactored modules can be imported"""
    try:
        print("Testing module imports...")
        
        import angel_content
        print("✓ angel_content imported successfully")
        
        import angel_graphql  
        print("✓ angel_graphql imported successfully")
        
        import angel_queries
        print("✓ angel_queries imported successfully")
        
        import kodi_ui_interface
        print("✓ kodi_ui imported successfully")
        
        import angel_authentication
        print("✓ angel_authentication imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_creation():
    """Test that our refactored modules can be instantiated"""
    try:
        print("\nTesting module instantiation...")
        
        from angel_content import AngelContentManager
        # Use mock session for testing
        content_manager = AngelContentManager()
        print("✓ AngelContentManager created successfully")
        
        from kodi_ui_interface import KodiUIInterface
        ui_helper = KodiUIInterface(1, 'plugin://test')
        print("✓ KodiUIHelper created successfully")
        
        # Test that the content manager has a session
        assert content_manager.session is not None
        print("✓ Content manager has a session")
        
        return True
    except Exception as e:
        print(f"✗ Instantiation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_graphql_queries():
    """Test that GraphQL queries are properly defined"""
    try:
        print("\nTesting GraphQL queries...")
        
        import angel_queries
        
        # Check that main query templates exist
        assert hasattr(angel_queries, 'QUERIES')
        print("✓ QUERIES dictionary defined")
        
        # Check that main query keys exist
        assert 'all_projects_basic' in angel_queries.QUERIES
        print("✓ all_projects_basic query defined")
        
        assert 'project_episodes' in angel_queries.QUERIES  
        print("✓ project_episodes query defined")
        
        assert 'episode_full' in angel_queries.QUERIES
        print("✓ episode_full query defined")
        
        # Check fragments
        assert hasattr(angel_queries, 'FRAGMENTS')
        print("✓ FRAGMENTS dictionary defined")
        
        assert 'project_basic' in angel_queries.FRAGMENTS
        print("✓ project_basic fragment defined")
        
        assert 'episode_core' in angel_queries.FRAGMENTS
        print("✓ episode_core fragment defined")
        
        return True
    except Exception as e:
        print(f"✗ GraphQL queries error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=== Testing Angel Studios Addon Refactor ===\n")
    
    success = True
    success &= test_imports()
    success &= test_module_creation() 
    success &= test_graphql_queries()
    
    if success:
        print("\n🎉 All tests passed! The refactor is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
