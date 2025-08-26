#!/usr/bin/env python3
"""
Test Joern Detection Logic
==========================

This script tests the enhanced Joern detection logic without circular import issues.
"""

import os
import shutil
from pathlib import Path

def test_joern_detection():
    """Test the enhanced Joern detection logic."""
    print("=" * 60)
    print("🔧 JOERN DETECTION TEST")
    print("=" * 60)
    
    current_dir = Path(".")
    
    # Test patterns that the new detection logic checks
    search_patterns = [
        # Standard installations
        current_dir / "joern-cli" / "joern",
        current_dir / "joern" / "joern", 
        current_dir / "joern" / "bin" / "joern",
        
        # Tools directory patterns (for your test machine)
        current_dir / "tools" / "joern",
        current_dir / "tools" / "joern-cli" / "joern",
        current_dir / "tools" / "joern" / "bin" / "joern",
        current_dir / "tools" / "bin" / "joern",
        
        # Alternative directory patterns
        current_dir / "bin" / "joern",
        current_dir / "external" / "joern" / "joern",
        current_dir / "vendor" / "joern" / "joern",
    ]
    
    print(f"📁 Current directory: {current_dir.absolute()}")
    print(f"🏠 JOERN_HOME environment variable: {os.getenv('JOERN_HOME', 'NOT SET')}")
    print()
    
    # Check each pattern
    found_joern = []
    for pattern in search_patterns:
        if pattern.exists() and pattern.is_file():
            print(f"✅ FOUND: {pattern}")
            found_joern.append(pattern)
        else:
            print(f"❌ NOT FOUND: {pattern}")
    
    print()
    
    # Check if joern is in PATH
    joern_executable = shutil.which("joern")
    if joern_executable:
        print(f"✅ Joern found in PATH: {joern_executable}")
        found_joern.append(Path(joern_executable))
    else:
        print("❌ Joern not found in PATH")
    
    print()
    
    # Check for recursive search in tools directory
    tools_dir = current_dir / "tools"
    if tools_dir.exists():
        print(f"🔍 Searching recursively in {tools_dir}...")
        joern_candidates = list(tools_dir.rglob("joern"))
        for candidate in joern_candidates:
            if candidate.is_file() and candidate.name == "joern":
                print(f"✅ RECURSIVE FIND: {candidate}")
                found_joern.append(candidate)
    else:
        print("❌ Tools directory doesn't exist")
    
    print()
    print("=" * 60)
    if found_joern:
        print("🎉 JOERN DETECTION SUCCESSFUL!")
        print(f"Found {len(found_joern)} potential Joern installation(s):")
        for joern_path in found_joern:
            print(f"  - {joern_path}")
            print(f"    Parent directory: {joern_path.parent}")
            if joern_path.exists():
                try:
                    stat = joern_path.stat()
                    print(f"    Executable: {bool(stat.st_mode & 0o111)}")
                    print(f"    Size: {stat.st_size} bytes")
                except Exception as e:
                    print(f"    Error checking file: {e}")
    else:
        print("❌ JOERN NOT FOUND")
        print("Solutions for your test machine:")
        print("  1. Create tools/joern executable")
        print("  2. Set JOERN_HOME environment variable")
        print("  3. Add joern to system PATH")
        print("  4. Install joern in standard location")
    print("=" * 60)

if __name__ == "__main__":
    test_joern_detection()