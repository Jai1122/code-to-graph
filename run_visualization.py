#!/usr/bin/env python3
"""Quick demo script to run the CodeToGraph visualization server."""

import os
import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set environment
os.environ["NEO4J_PASSWORD"] = "password123"

def main():
    """Run the visualization server."""
    try:
        from code_to_graph.visualization.dash_server import DashVisualizationServer
        from code_to_graph.storage.neo4j_client import Neo4jClient
        
        print("🔍 CodeToGraph Visualization Server")
        print("=" * 40)
        
        # Check Neo4j connection
        print("📊 Checking Neo4j connection...")
        with Neo4jClient() as client:
            stats = client.get_database_stats()
            if stats['total_nodes'] == 0:
                print("❌ No data found in Neo4j database!")
                print("Run this first: python -m code_to_graph.cli.main import-graph --repo-path /path/to/repo")
                return
            
            print(f"✅ Found {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
        
        # Start server
        print("\n🚀 Starting visualization server...")
        print("📱 Open your browser at: http://localhost:8080")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 40)
        
        server = DashVisualizationServer(debug=False)
        server.run(host="127.0.0.1", port=8080, threaded=False)
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()