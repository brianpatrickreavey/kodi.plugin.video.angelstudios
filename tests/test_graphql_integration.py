#!/usr/bin/env python3
"""
Test script for GraphQL integration in Angel Studios Kodi addon.
This tests that all the GraphQL query builders work correctly.
"""

import sys
import os

# Add project paths (from tests directory)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
lib_dir = os.path.join(parent_dir, 'resources', 'lib')

sys.path.insert(0, parent_dir)
sys.path.insert(0, lib_dir)

# Mock Kodi modules
from unittest.mock import MagicMock

sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcplugin'] = MagicMock()

def test_graphql_queries():
    """Test GraphQL query builders"""
    print("=" * 60)
    print("Testing GraphQL Query Builders")
    print("=" * 60)
    
    try:
        from resources.lib import angel_graphql
        print("✓ angel_graphql module imported")
        
        # Test basic projects query
        basic_query = angel_graphql.get_all_projects_basic_query()
        assert 'operationName' in basic_query
        assert 'query' in basic_query
        assert 'variables' in basic_query
        print("✓ Basic projects query: OK")
        
        # Test detailed projects query
        detailed_query = angel_graphql.get_all_projects_query()
        assert 'operationName' in detailed_query
        assert len(detailed_query['query']) > len(basic_query['query'])  # Should be more detailed
        print("✓ Detailed projects query: OK")
        
        # Test episode queries
        episode_query = angel_graphql.get_episode_basic_query('test-guid')
        assert episode_query['variables']['guid'] == 'test-guid'
        print("✓ Episode basic query: OK")
        
        # Test project episodes query  
        project_query = angel_graphql.get_project_episodes_query('test-project')
        assert project_query['variables']['projectSlug'] == 'test-project'
        print("✓ Project episodes query: OK")
        
        # Test content filtering queries
        early_access_query = angel_graphql.get_early_access_content_query()
        assert early_access_query['variables']['contentStates'] == ['EARLY_ACCESS']
        print("✓ Early access content query: OK")
        
        public_query = angel_graphql.get_public_content_query()
        assert public_query['variables']['contentStates'] == ['PUBLIC']
        print("✓ Public content query: OK")
        
        # Test custom content states
        custom_query = angel_graphql.get_content_by_state_query(['EARLY_ACCESS', 'PUBLIC'])
        assert 'EARLY_ACCESS' in custom_query['variables']['contentStates']
        assert 'PUBLIC' in custom_query['variables']['contentStates']
        print("✓ Custom content states query: OK")
        
        # Test M3U8 episode query
        m3u8_query = angel_graphql.get_episode_m3u8_query('episode-guid', 'project-slug')
        assert m3u8_query['variables']['guid'] == 'episode-guid'
        assert m3u8_query['variables']['projectSlug'] == 'project-slug'
        print("✓ M3U8 episode query: OK")
        
        # Test minimal episode query
        minimal_query = angel_graphql.get_minimal_episode_query('test-guid')
        assert minimal_query['variables']['guid'] == 'test-guid'
        print("✓ Minimal episode query: OK")
        
        print("\n🎉 All GraphQL query builders working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing GraphQL queries: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_content_manager():
    """Test AngelContentManager initialization"""
    print("\n" + "=" * 60)
    print("Testing AngelContentManager")
    print("=" * 60)
    
    try:
        from resources.lib import angel_content
        print("✓ angel_content module imported")
        
        # Test content manager initialization (without authentication)
        content_manager = angel_content.AngelContentManager(session=None)
        assert content_manager.api_url == "https://api.angelstudios.com/graphql"
        assert content_manager.base_url == "https://www.angel.com"
        print("✓ AngelContentManager created successfully")
        
        # Test helper methods
        url = content_manager._get_cloudinary_url("test/path")
        assert "images.angelstudios.com" in url
        assert "test/path" in url
        print("✓ Cloudinary URL helper: OK")
        
        print("\n🎉 AngelContentManager working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing content manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_helper():
    """Test KodiUIHelper initialization"""
    print("\n" + "=" * 60)
    print("Testing KodiUIHelper")
    print("=" * 60)
    
    try:
        from . import kodi_ui_interface
        print("✓ kodi_ui module imported")
        
        # Test UI helper initialization
        ui_helper = kodi_ui_interface.KodiUIHelper(1, 'plugin://test')
        assert ui_helper.handle == 1
        assert ui_helper.base_url == 'plugin://test'
        print("✓ KodiUIHelper created successfully")
        
        # Test URL creation
        url = ui_helper.create_plugin_url(action='test', param='value')
        assert 'action=test' in url
        assert 'param=value' in url
        print("✓ Plugin URL creation: OK")
        
        print("\n🎉 KodiUIHelper working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing UI helper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_module():
    """Test main module imports"""
    print("\n" + "=" * 60)
    print("Testing Main Module")
    print("=" * 60)
    
    try:
        # Test that main can be imported (with mocked sys.argv)
        original_argv = sys.argv
        sys.argv = ['plugin://plugin.video.angelstudios', '1', '']
        
        import main
        print("✓ main module imported successfully")
        
        # Restore sys.argv
        sys.argv = original_argv
        
        print("\n🎉 Main module working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing main module: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Angel Studios Kodi Addon - GraphQL Integration Test")
    print(f"Project directory: {os.path.abspath('.')}")
    
    tests = [
        test_graphql_queries,
        test_content_manager,
        test_ui_helper,
        test_main_module
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! GraphQL integration is working correctly.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
