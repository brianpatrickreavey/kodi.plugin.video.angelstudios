#!/usr/bin/env python3
"""
Development shell for Angel Studios Kodi addon.
Automatically imports commonly used libraries and project modules.

Usage: python tools/dev_shell.py
"""

import sys
import os
import requests
import bs4
import logging
from importlib import reload

# Pretty print function with syntax highlighting
import json
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalTrueColorFormatter
from pygments.styles import get_style_by_name

# Try to import GraphQL library
try:
    from gql import gql, Client
    from gql.transport.requests import RequestsHTTPTransport
    GQL_AVAILABLE = True
except ImportError:
    GQL_AVAILABLE = False
    print("⚠ gql library not available. Install with: pip install gql[requests]")

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Mock Kodi modules for development
class MockXBMC:
    LOGINFO = 1
    LOGERROR = 3
    LOGDEBUG = 0
    
    @staticmethod
    def log(msg, level=1):
        level_names = {0: 'DEBUG', 1: 'INFO', 3: 'ERROR'}
        print(f"[{level_names.get(level, 'LOG')}] {msg}")

class MockXBMCAddon:
    @staticmethod
    def Addon():
        return MockAddon()

class MockAddon:
    def getAddonInfo(self, info_type):
        if info_type == 'id':
            return 'plugin.video.angelstudios'
        return ''

class MockXBMCVFS:
    @staticmethod
    def translatePath(path):
        # Convert Kodi special paths to regular paths for development
        if 'special://profile' in path:
            home_dir = os.path.expanduser('~')
            dev_cache = os.path.join(home_dir, '.kodi_dev_cache')
            return path.replace('special://profile', dev_cache)
        return path
    
    @staticmethod
    def exists(path):
        return os.path.exists(path)
    
    @staticmethod
    def mkdirs(path):
        os.makedirs(path, exist_ok=True)

# Patch sys.modules to provide mock Kodi modules
sys.modules['xbmc'] = MockXBMC()
sys.modules['xbmcaddon'] = MockXBMCAddon()
sys.modules['xbmcvfs'] = MockXBMCVFS()

def pp(payload):
    """Pretty print JSON payload with syntax highlighting"""
    print(highlight(json.dumps(payload, indent=2), JsonLexer(), TerminalTrueColorFormatter(style=get_style_by_name('lightbulb'))))

print("=" * 50)
print("Angel Studios Kodi Addon - Development Shell")
print("=" * 50)

# Import your project modules (mocks are already in place)
try:
    from . import angel_studios_authentication
    from resources.lib import angel_graphql
    from resources.lib import angel_content
    print("✓ Project modules loaded (angel_authentication, angel_graphql, angel_content)")
    
    # Add a helper function for easy testing
    def test_auth(username=None, password=None):
        """Helper function to test authentication in dev environment"""
        # First, try to get an existing session (without credentials)
        print("Checking for existing valid session...")
        try:
            session = angel_studios_authentication.get_authenticated_session()
            if session and angel_studios_authentication.is_session_valid(session):
                print("✓ Using existing valid session!")
                return session
            else:
                print("ℹ No valid existing session found")
        except Exception as e:
            print(f"ℹ Could not load existing session: {e}")
        
        # If no valid session exists, prompt for credentials
        if not username:
            username = input("Enter Angel.com username: ")
        if not password:
            import getpass
            password = getpass.getpass("Enter Angel.com password: ")
        
        print("Attempting authentication...")
        try:
            session = angel_studios_authentication.get_authenticated_session(username, password)
            print("✓ Authentication successful!")
            return session
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return None
    
    def force_reauth(username=None, password=None):
        """Force reauthentication by clearing session files first"""
        print("Clearing existing session files...")
        try:
            session_file = angel_studios_authentication.get_session_file()
            if os.path.exists(session_file):
                os.remove(session_file)
                print(f"✓ Removed session file: {session_file}")
            else:
                print("ℹ No existing session file found")
        except Exception as e:
            print(f"⚠ Error clearing session file: {e}")
        
        print("Starting fresh authentication...")
        return test_auth(username, password)
    
    def clear_sessions():
        """Clear all session files without reauthenticating"""
        try:
            session_file = angel_studios_authentication.get_session_file()
            if os.path.exists(session_file):
                os.remove(session_file)
                print(f"✓ Cleared session file: {session_file}")
                return True
            else:
                print("ℹ No session file to clear")
                return False
        except Exception as e:
            print(f"✗ Error clearing session file: {e}")
            return False
    
    # GraphQL helper functions
    def create_graphql_client(session, endpoint_url="https://api.angelstudios.com/graphql"):
        """Create a GraphQL client using an authenticated session"""
        if not GQL_AVAILABLE:
            print("✗ gql library not available. Install with: pip install gql[requests]")
            return None
        
        try:
            # Create transport with session's cookies and headers
            transport = RequestsHTTPTransport(
                url=endpoint_url,
                cookies=session.cookies,
                headers=dict(session.headers),
                use_json=True
            )
            
            # Try to fetch schema, fall back gracefully if not available
            try:
                client = Client(transport=transport, fetch_schema_from_transport=True)
                print(f"✓ GraphQL client created with schema from {endpoint_url}")
            except Exception:
                client = Client(transport=transport, fetch_schema_from_transport=False)
                print(f"✓ GraphQL client created without schema from {endpoint_url}")
            
            return client
        except Exception as e:
            print(f"✗ Error creating GraphQL client: {e}")
            return None
    
    def graphql_query(session_or_client, query_string, variables=None, endpoint_url="https://api.angelstudios.com/graphql"):
        """Execute a GraphQL query using either a session or gql client"""
        if isinstance(session_or_client, requests.Session):
            # Use simple requests approach
            try:
                response = session_or_client.post(
                    endpoint_url,
                    json={
                        "query": query_string,
                        "variables": variables or {}
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
                
                if 'errors' in result:
                    print(f"⚠ GraphQL errors: {result['errors']}")
                
                return result
            except Exception as e:
                print(f"✗ GraphQL query failed: {e}")
                return None
        
        elif GQL_AVAILABLE and hasattr(session_or_client, 'execute'):
            # Use gql client
            try:
                query = gql(query_string)
                result = session_or_client.execute(query, variable_values=variables or {})
                return result
            except Exception as e:
                print(f"✗ GraphQL query failed: {e}")
                return None
        
        else:
            print("✗ Invalid client or session provided")
            return None
    
    def quick_graphql(query_string, variables=None, endpoint_url="https://api.angelstudios.com/graphql"):
        """Quick GraphQL query using current authenticated session"""
        try:
            session = angel_studios_authentication.get_authenticated_session()
            return graphql_query(session, query_string, variables, endpoint_url)
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return None
    
    def quick_graphql_dict(query_dict, endpoint_url="https://api.angelstudios.com/graphql"):
        """Quick GraphQL query using a complete query dictionary"""
        try:
            session = angel_studios_authentication.get_authenticated_session()
            print(f"📡 Sending GraphQL request to: {endpoint_url}")
            print(f"📋 Operation: {query_dict.get('operationName', 'Unknown')}")
            
            response = session.post(
                endpoint_url,
                json=query_dict,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"📋 Response headers: {dict(response.headers)}")
                print(f"📄 Response text: {response.text[:1000]}...")
                
            response.raise_for_status()
            result = response.json()
            
            if 'errors' in result:
                print(f"⚠ GraphQL errors: {result['errors']}")
            
            return result
        except requests.exceptions.RequestException as e:
            print(f"✗ HTTP request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode failed: {e}")
            print(f"📄 Raw response: {response.text[:500]}...")
            return None
        except Exception as e:
            print(f"✗ GraphQL query failed: {e}")
            return None
    
    # Import GraphQL queries from dedicated module
    get_episode_m3u8_query = angel_graphql.get_episode_m3u8_query
    get_episode_basic_query = angel_graphql.get_episode_basic_query  
    get_project_episodes_query = angel_graphql.get_project_episodes_query
    get_minimal_episode_query = angel_graphql.get_minimal_episode_query
    get_all_projects_query = angel_graphql.get_all_projects_query
    get_all_projects_basic_query = angel_graphql.get_all_projects_basic_query
    get_project_catalog_query = angel_graphql.get_project_catalog_query
    get_content_by_state_query = angel_graphql.get_content_by_state_query
    get_early_access_content_query = angel_graphql.get_early_access_content_query
    get_public_content_query = angel_graphql.get_public_content_query
    build_query = angel_graphql.build_query
    create_query_dict = angel_graphql.create_query_dict
    
    if GQL_AVAILABLE:
        print("✓ Helper functions available: test_auth(), force_reauth(), clear_sessions()")
        print("✓ GraphQL functions available: create_graphql_client(), graphql_query(), quick_graphql(), quick_graphql_dict()")
    else:
        print("✓ Helper functions available: test_auth(), force_reauth(), clear_sessions()")
        print("⚠ GraphQL functions available but limited (install gql for full features)")
        print("  - graphql_query() (requests-based)")
        print("  - quick_graphql() (requests-based)")
        print("  - quick_graphql_dict() (requests-based)")
    
except ImportError as e:
    print(f"⚠ Could not import angel_authentication module: {e}")

# Try to import main module
try:
    import main
    print("✓ Main module loaded")
except ImportError as e:
    print(f"⚠ Could not import main module: {e}")

print("\nAvailable imports:")
print("  - sys, os, json")
print("  - requests, bs4 (BeautifulSoup)")
print("  - pp (pprint)")
if GQL_AVAILABLE:
    print("  - gql, Client, RequestsHTTPTransport (GraphQL)")
if 'angel_authentication' in locals():
    print("  - angel_authentication (from resources.lib)")
    print("  - angel_graphql (from resources.lib)")
    print("  - test_auth() (helper for testing authentication)")
    print("  - force_reauth() (clear sessions and reauthenticate)")
    print("  - clear_sessions() (clear session files only)")
    if GQL_AVAILABLE:
        print("  - create_graphql_client() (create gql client with session)")
    print("  - graphql_query() (execute GraphQL queries)")
    print("  - quick_graphql() (quick GraphQL with auto-auth)")
    print("  - quick_graphql_dict() (quick GraphQL with complete dict)")
    print("  - get_episode_m3u8_query() (full episode + project data)")
    print("  - get_episode_basic_query() (basic episode data only)")
    print("  - get_project_episodes_query() (all episodes for project)")  
    print("  - get_minimal_episode_query() (minimal episode data)")
    print("  - get_all_projects_query() (all 147 projects + episodes)")
    print("  - get_all_projects_basic_query() (all projects, no episodes)")
    print("  - get_project_catalog_query() (smart catalog query)")
    print("  - get_content_by_state_query() (filter by EARLY_ACCESS, PUBLIC)")
    print("  - get_early_access_content_query() (early access only)")
    print("  - get_public_content_query() (public content only)")
    print("  - build_query() (custom query builder)")
    print("  - create_query_dict() (create query dictionary)")
else:
    print("  - angel_authentication (unavailable)")
    print("  - angel_graphql (unavailable)")
if 'main' in locals():
    print("  - main (project main module)")
else:
    print("  - main (unavailable)")

print("\nUseful variables:")
print("  - project_root:", project_root)

print("\n Initializing AngelContentManager as cm...")
cm = angel_content.AngelContentManager()

print("\nStarting interactive shell...")
print("-" * 50)

if __name__ == "__main__":
    # Enable readline and tab completion
    try:
        import readline
        import rlcompleter
        readline.set_completer(rlcompleter.Completer(locals()).complete)
        readline.parse_and_bind("tab: complete")
        print("✓ Tab completion enabled")
    except ImportError:
        print("⚠ Readline not available - no tab completion")
    
    import code
    code.interact(local=locals())
