#!/usr/bin/env python3
"""
Verification script for the relationship fix.
Run this after applying the fix to verify it works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_tree_sitter_parser():
    """Test the enhanced Tree-sitter parser."""
    print("🧪 Testing Tree-sitter Parser Enhancement")
    print("=" * 50)
    
    try:
        from src.code_to_graph.parsers.tree_sitter_parser import TreeSitterParser
        from src.code_to_graph.processors.chunked_processor import FileInfo
        
        # Create test Go file
        test_go_content = '''package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
    processData()
}

func processData() {
    data := getData()
    fmt.Printf("Data: %v", data)
}

func getData() string {
    return "test data"
}
'''
        
        # Write test file
        test_file = Path("test_parser.go")
        test_file.write_text(test_go_content)
        
        try:
            # Initialize parser
            parser = TreeSitterParser()
            print("✅ Tree-sitter parser initialized successfully")
            
            # Check if enhanced methods are available
            if hasattr(parser, '_create_robust_entity_mapping'):
                print("✅ Enhanced entity mapping method available")
            else:
                print("❌ Enhanced entity mapping method missing")
                return False
            
            if hasattr(parser, '_create_relationships_with_mapping'):
                print("✅ Enhanced relationship mapping method available")
            else:
                print("❌ Enhanced relationship mapping method missing")
                return False
            
            # Test parsing
            file_info = FileInfo(
                path=test_file.absolute(),
                language="go",
                size=len(test_go_content)
            )
            
            entities, relationships = parser.parse_file(file_info)
            
            print(f"📊 Parsing results:")
            print(f"   Entities: {len(entities)}")
            print(f"   Relationships: {len(relationships)}")
            
            # Check for null target_ids
            null_targets = sum(1 for r in relationships if not r.target_id)
            null_sources = sum(1 for r in relationships if not r.source_id)
            
            print(f"   Null source_ids: {null_sources}")
            print(f"   Null target_ids: {null_targets}")
            
            if null_targets == 0 and null_sources == 0:
                print("✅ No null IDs found - fix is working!")
            else:
                print("❌ Still found null IDs")
                return False
            
            # Show relationship details
            if relationships:
                print("\n🔗 Sample relationships:")
                for i, rel in enumerate(relationships[:3]):
                    print(f"   {i+1}. {rel.properties.get('source_name', 'Unknown')} -> {rel.properties.get('target_name', 'Unknown')} ({rel.relation_type})")
            
            return True
            
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
        
    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        import traceback
        print(f"   Details: {traceback.format_exc()}")
        return False

def test_intelligent_parser():
    """Test the intelligent parser integration."""
    print("\n🧠 Testing Intelligent Parser Integration")
    print("=" * 50)
    
    try:
        from src.code_to_graph.parsers.intelligent_parser import IntelligentParserFactory
        
        # Create parser
        parser = IntelligentParserFactory.create_go_optimized_parser()
        print("✅ Intelligent parser created successfully")
        
        # Check if Tree-sitter parser has enhanced methods
        if 'tree_sitter' in parser.parsers:
            ts_parser = parser.parsers['tree_sitter']
            if hasattr(ts_parser, '_create_relationships_with_mapping'):
                print("✅ Tree-sitter parser in intelligent parser has enhanced methods")
                return True
            else:
                print("❌ Tree-sitter parser in intelligent parser missing enhanced methods")
                return False
        else:
            print("⚠️  No Tree-sitter parser available in intelligent parser")
            return False
        
    except Exception as e:
        print(f"❌ Intelligent parser test failed: {e}")
        return False

def provide_usage_instructions():
    """Provide instructions for using the fix."""
    print("\n📋 How to Use the Fix")
    print("=" * 50)
    print("1. Run analysis with the fixed parser:")
    print("   code-to-graph import-graph --repo-path /path/to/your/go/project --clear-db")
    print()
    print("2. Check for relationships in Neo4j Browser (http://localhost:7474):")
    print("   MATCH ()-[r]->() RETURN count(r) as relationship_count")
    print()
    print("3. View actual relationships:")
    print("   MATCH (source:Entity)-[r:RELATES]->(target:Entity)")
    print("   RETURN source.name, r.relation_type, target.name")
    print("   ORDER BY source.name")
    print("   LIMIT 10")
    print()
    print("4. Check for external entities:")
    print("   MATCH (n:Entity) WHERE n.file_path = 'external'")
    print("   RETURN n.name, count(*) as usage_count")
    print("   ORDER BY usage_count DESC")

if __name__ == "__main__":
    print("🚀 CodeToGraph Relationship Fix Verification")
    print("=" * 60)
    
    success = True
    
    # Test Tree-sitter parser
    if not test_tree_sitter_parser():
        success = False
    
    # Test intelligent parser
    if not test_intelligent_parser():
        success = False
    
    if success:
        print("\n🎉 All tests passed! The relationship fix is working correctly.")
        provide_usage_instructions()
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure you applied the fix correctly")
        print("2. Restart any running Python processes") 
        print("3. Clear any Python cache: find . -name '__pycache__' -exec rm -rf {} +")