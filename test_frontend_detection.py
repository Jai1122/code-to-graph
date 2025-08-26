#!/usr/bin/env python3
"""
Test Frontend Detection Logic
============================

This script tests the Joern frontend detection logic directly.
"""

import os
from pathlib import Path

def find_frontend_executable(joern_path: Path, frontend_name: str):
    """Replicate the frontend detection logic."""
    if not joern_path:
        return None
    
    # Common paths where frontends might be located
    search_paths = [
        # Standard Joern installation structure
        joern_path / "bin" / frontend_name,
        joern_path / frontend_name,
        
        # Alternative structures
        joern_path / "joern-cli" / "bin" / frontend_name,
        joern_path / "joern-cli" / frontend_name,
        
        # Tools directory variations
        joern_path / "tools" / frontend_name,
        joern_path / "tools" / "bin" / frontend_name,
        
        # Parent directory patterns (if joern_path points to subdirectory)
        joern_path.parent / "bin" / frontend_name,
        joern_path.parent / frontend_name,
    ]
    
    print(f"🔍 Searching for {frontend_name} in {joern_path}")
    
    # Check each possible path
    for i, path in enumerate(search_paths, 1):
        print(f"  {i}. Checking: {path}")
        if path.exists() and path.is_file():
            # Check if it's executable
            try:
                if path.stat().st_mode & 0o111:  # Check execute permission
                    print(f"     ✅ FOUND (executable): {path}")
                    return path
                else:
                    print(f"     ⚠️  Found but not executable: {path}")
            except Exception as e:
                print(f"     ❌ Error checking: {e}")
        else:
            if path.exists():
                file_type = "file" if path.is_file() else "directory" if path.is_dir() else "unknown"
                print(f"     ❌ exists ({file_type})")
            else:
                print(f"     ❌ not found")
    
    # Search recursively in the Joern installation directory
    print(f"🔍 Recursive search in {joern_path}...")
    if joern_path.exists():
        found_recursive = []
        for candidate in joern_path.rglob(frontend_name):
            if candidate.is_file():
                try:
                    if candidate.stat().st_mode & 0o111:
                        print(f"     ✅ RECURSIVE FIND: {candidate}")
                        found_recursive.append(candidate)
                except Exception:
                    continue
        
        if found_recursive:
            return found_recursive[0]  # Return the first one found
    
    print(f"     ❌ {frontend_name} not found anywhere")
    return None

def test_frontend_detection():
    """Test the frontend detection."""
    print("=" * 70)
    print("🔧 FRONTEND DETECTION TEST")
    print("=" * 70)
    
    # Detect Joern path (simplified logic)
    current_dir = Path(".")
    joern_search_patterns = [
        current_dir / "joern-cli" / "joern",
        current_dir / "joern" / "joern", 
        current_dir / "tools" / "joern",
        current_dir / "tools" / "joern-cli" / "joern",
    ]
    
    joern_path = None
    print("🏠 Finding Joern installation...")
    for pattern in joern_search_patterns:
        print(f"  Checking: {pattern}")
        if pattern.exists() and pattern.is_file():
            joern_path = pattern.parent
            print(f"  ✅ Found Joern at: {joern_path}")
            break
        else:
            print(f"  ❌ Not found")
    
    if not joern_path:
        print("❌ No Joern installation found!")
        return
    
    print()
    print(f"📂 Joern root directory: {joern_path}")
    print()
    
    # Test frontend detection for different languages
    frontends_to_test = [
        ("go", "gosrc2cpg"),
        ("java", "javasrc2cpg"), 
        ("python", "pysrc2cpg"),
        ("javascript", "jssrc2cpg"),
    ]
    
    results = {}
    
    for language, frontend in frontends_to_test:
        print(f"🔧 Testing {language} frontend ({frontend}):")
        frontend_path = find_frontend_executable(joern_path, frontend)
        results[language] = frontend_path
        print()
    
    print("=" * 70)
    print("📊 SUMMARY:")
    for language, frontend_path in results.items():
        status = "✅ FOUND" if frontend_path else "❌ NOT FOUND"
        path_info = f" at {frontend_path}" if frontend_path else ""
        print(f"  {language}: {status}{path_info}")
    
    print("=" * 70)
    
    # Show what would happen on your test machine
    print()
    print("💡 FOR YOUR TEST MACHINE (tools/ directory):")
    print("If your Joern is in ./tools/, ensure the structure is:")
    print("  ./tools/gosrc2cpg          # Direct in tools")
    print("  ./tools/bin/gosrc2cpg      # In tools/bin")
    print("  ./tools/joern-cli/gosrc2cpg # In tools/joern-cli")
    print()
    print("The detection logic will search these paths:")
    tools_path = Path("./tools")
    if tools_path.exists():
        print(f"  Your tools directory exists: {tools_path.absolute()}")
    else:
        print(f"  Your tools directory would be: {tools_path.absolute()}")
    
    example_paths = [
        tools_path / "bin" / "gosrc2cpg",
        tools_path / "gosrc2cpg",
        tools_path / "joern-cli" / "bin" / "gosrc2cpg",
        tools_path / "joern-cli" / "gosrc2cpg",
    ]
    
    for path in example_paths:
        status = "EXISTS" if path.exists() else "MISSING"
        print(f"  - {path} ({status})")

if __name__ == "__main__":
    test_frontend_detection()