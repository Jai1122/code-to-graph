#!/usr/bin/env python3
"""
Debug Configuration Loading
===========================

This script helps debug configuration loading issues in CodeToGraph.
It tests environment variable loading, Pydantic settings, and connection status.
"""

import os
import sys
from pathlib import Path

def test_environment_variables():
    """Test if environment variables are loaded correctly."""
    print("=" * 60)
    print("🔧 ENVIRONMENT VARIABLES TEST")
    print("=" * 60)
    
    env_vars = [
        # Neo4j
        'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD', 'NEO4J_DATABASE',
        # LLM
        'LLM_PROVIDER', 'LLM_VLLM_BASE_URL', 'LLM_VLLM_API_KEY', 'LLM_VLLM_MODEL',
        # Processing
        'PROCESSING_MAX_CHUNK_SIZE', 'PROCESSING_CHUNK_STRATEGY',
        # Visualization  
        'VIZ_HOST', 'VIZ_PORT',
    ]
    
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"📄 .env file exists: {Path('.env').exists()}")
    print(f"📄 .env file size: {Path('.env').stat().st_size if Path('.env').exists() else 'N/A'} bytes")
    print()
    
    missing_vars = []
    placeholder_vars = []
    
    for var in env_vars:
        value = os.getenv(var, 'NOT SET')
        status = "✅"
        
        if value == 'NOT SET':
            status = "❌"
            missing_vars.append(var)
        elif any(placeholder in value.lower() for placeholder in ['example', 'your_', 'placeholder', 'change_me']):
            status = "⚠️ "
            placeholder_vars.append(var)
            
        print(f"{status} {var}: {value}")
    
    print()
    if missing_vars:
        print(f"❌ Missing variables: {', '.join(missing_vars)}")
    if placeholder_vars:
        print(f"⚠️  Placeholder variables (need updating): {', '.join(placeholder_vars)}")
    if not missing_vars and not placeholder_vars:
        print("✅ All environment variables are properly set!")
    
    return len(missing_vars) == 0

def test_pydantic_settings():
    """Test Pydantic settings loading."""
    print("=" * 60)
    print("🔧 PYDANTIC SETTINGS TEST")
    print("=" * 60)
    
    try:
        # Import after environment is set up
        from src.code_to_graph.core.config import settings, Neo4jSettings, LLMSettings
        
        print("✅ Settings imported successfully")
        print()
        
        # Test individual settings
        print("🗄️  Neo4j Settings:")
        neo4j = Neo4jSettings()
        print(f"   URI: {neo4j.uri}")
        print(f"   Username: {neo4j.username}")
        print(f"   Password: {'*' * len(neo4j.password) if neo4j.password else 'NOT SET'}")
        print()
        
        print("🤖 LLM Settings:")
        llm = LLMSettings()
        print(f"   Provider: {llm.provider}")
        print(f"   Base URL: {llm.vllm_base_url}")
        print(f"   Model: {llm.vllm_model}")
        print(f"   API Key: {'*' * 10 + llm.vllm_api_key[-4:] if llm.vllm_api_key and len(llm.vllm_api_key) > 4 else llm.vllm_api_key}")
        print()
        
        print("⚙️  Composite Settings:")
        print(f"   Neo4j URI: {settings.neo4j.uri}")
        print(f"   LLM Base URL: {settings.llm.vllm_base_url}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Settings loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connections():
    """Test actual connections to services."""
    print("=" * 60)
    print("🔧 CONNECTION TESTS")
    print("=" * 60)
    
    # Test Neo4j
    print("🗄️  Testing Neo4j connection...")
    try:
        from src.code_to_graph.storage.neo4j_client import Neo4jClient
        with Neo4jClient() as client:
            stats = client.get_database_stats()
            print(f"   ✅ Neo4j connected: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
    except Exception as e:
        print(f"   ❌ Neo4j failed: {str(e)[:100]}...")
    
    # Test LLM
    print("🤖 Testing LLM connection...")
    try:
        from src.code_to_graph.llm.llm_factory import LLMFactory
        if LLMFactory.check_health():
            model = LLMFactory.get_model_name()
            print(f"   ✅ LLM connected: {model}")
        else:
            print("   ❌ LLM server not responding")
    except Exception as e:
        print(f"   ❌ LLM failed: {str(e)[:100]}...")
    
    # Test Joern
    print("🔧 Testing Joern installation...")
    try:
        from src.code_to_graph.parsers.joern_parser import JoernParser
        joern = JoernParser()
        if joern.joern_path and joern.joern_path.exists():
            print(f"   ✅ Joern found: {joern.joern_path}")
        else:
            print("   ❌ Joern not found")
    except Exception as e:
        print(f"   ❌ Joern test failed: {str(e)[:100]}...")

def main():
    """Run all configuration tests."""
    print("🚀 CodeToGraph Configuration Debug Tool")
    print("This tool helps diagnose configuration loading issues.")
    print()
    
    # Ensure we're in the right directory
    if not Path("src/code_to_graph").exists():
        print("❌ Error: Run this script from the CodeToGraph root directory")
        sys.exit(1)
    
    # Add src to Python path for imports
    src_path = Path("src").absolute()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    success = True
    success &= test_environment_variables()
    success &= test_pydantic_settings()
    test_connections()
    
    print("=" * 60)
    if success:
        print("🎉 Configuration loading appears to be working correctly!")
        print("   If you're still seeing issues, the problem may be:")
        print("   1. Service connectivity (Neo4j not running, LLM server down)")
        print("   2. Firewall/network issues")
        print("   3. Authentication credentials")
    else:
        print("❌ Configuration issues detected!")
        print("   Please fix the issues above and run again.")
    print("=" * 60)

if __name__ == "__main__":
    main()