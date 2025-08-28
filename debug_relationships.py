#!/usr/bin/env python3
"""
Debug script for investigating null source_id and target_id in relationships CSV.
Run this script to diagnose relationship ID mapping issues.
"""

import csv
import json
from pathlib import Path

def analyze_csv_files():
    """Analyze the generated CSV files to identify null ID issues."""
    
    print("🔍 RELATIONSHIP ID DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Check if CSV files exist
    nodes_csv = Path("data/export/graph_nodes.csv")
    rels_csv = Path("data/export/graph_relationships.csv")
    
    if not nodes_csv.exists():
        print("❌ graph_nodes.csv not found. Run analysis first.")
        return
        
    if not rels_csv.exists():
        print("❌ graph_relationships.csv not found. Run analysis first.")
        return
    
    # Analyze nodes CSV
    print("\n📄 NODES ANALYSIS:")
    print("-" * 30)
    
    entities = {}
    entity_names = set()
    null_ids = 0
    
    with open(nodes_csv, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            entity_id = row['id']
            entity_name = row['name']
            entity_type = row['type']
            
            if not entity_id or entity_id.lower() == 'null':
                null_ids += 1
                print(f"  ❌ Row {i+1}: NULL ID for entity '{entity_name}' ({entity_type})")
            
            entities[entity_id] = {
                'name': entity_name,
                'type': entity_type,
                'file_path': row['file_path']
            }
            entity_names.add(entity_name)
    
    print(f"✅ Total entities: {len(entities)}")
    print(f"✅ Unique entity names: {len(entity_names)}")
    if null_ids > 0:
        print(f"❌ Entities with NULL IDs: {null_ids}")
    
    # Show sample entities
    print("\n📋 Sample entities:")
    for i, (entity_id, entity) in enumerate(entities.items()):
        if i < 5:  # Show first 5
            print(f"  {i+1}. ID: {entity_id} | Name: '{entity['name']}' | Type: {entity['type']}")
    
    # Analyze relationships CSV
    print("\n🔗 RELATIONSHIPS ANALYSIS:")
    print("-" * 30)
    
    null_source_ids = 0
    null_target_ids = 0
    valid_relationships = 0
    invalid_relationships = 0
    source_names = set()
    target_names = set()
    
    with open(rels_csv, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rel_id = row['id']
            source_id = row['source_id']
            target_id = row['target_id']
            relation_type = row['relation_type']
            
            # Check for null IDs
            if not source_id or source_id.lower() == 'null':
                null_source_ids += 1
                print(f"  ❌ Row {i+1}: NULL source_id for relationship {rel_id}")
                
            if not target_id or target_id.lower() == 'null':
                null_target_ids += 1
                print(f"  ❌ Row {i+1}: NULL target_id for relationship {rel_id}")
            
            # Check if IDs exist in entities
            if source_id and source_id in entities:
                source_name = entities[source_id]['name']
                source_names.add(source_name)
            else:
                source_name = "UNKNOWN"
                
            if target_id and target_id in entities:
                target_name = entities[target_id]['name']  
                target_names.add(target_name)
            else:
                target_name = "UNKNOWN"
            
            if source_id and target_id and source_id in entities and target_id in entities:
                valid_relationships += 1
            else:
                invalid_relationships += 1
                print(f"  ❌ Row {i+1}: Invalid relationship - {source_name} --[{relation_type}]--> {target_name}")
                if source_id and source_id not in entities:
                    print(f"      └─ Source ID '{source_id}' not found in entities")
                if target_id and target_id not in entities:
                    print(f"      └─ Target ID '{target_id}' not found in entities")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total relationships in CSV: {null_source_ids + null_target_ids + valid_relationships + invalid_relationships}")
    print(f"  Valid relationships: {valid_relationships}")
    print(f"  Invalid relationships: {invalid_relationships}")
    print(f"  NULL source_ids: {null_source_ids}")  
    print(f"  NULL target_ids: {null_target_ids}")
    print(f"  Unique source names: {len(source_names)}")
    print(f"  Unique target names: {len(target_names)}")
    
    # Show name mapping analysis
    print(f"\n🔍 NAME MAPPING ANALYSIS:")
    print("-" * 30)
    
    # Check if relationship source/target names match entity names
    missing_sources = source_names - entity_names
    missing_targets = target_names - entity_names
    
    if missing_sources:
        print(f"❌ Source names not found in entities: {missing_sources}")
    if missing_targets:
        print(f"❌ Target names not found in entities: {missing_targets}")
        
    if not missing_sources and not missing_targets and null_source_ids == 0 and null_target_ids == 0:
        print("✅ All relationship names match entity names")
    
    # Additional debugging info
    print(f"\n🧪 DEBUG RECOMMENDATIONS:")
    print("-" * 30)
    
    if null_source_ids > 0 or null_target_ids > 0:
        print("1. Entity name-to-ID mapping is failing during relationship creation")
        print("2. Check tree-sitter parser logs for debug output about entity mapping")
        print("3. Run with: LOG_LEVEL=DEBUG code-to-graph analyze --repo-path YOUR_REPO")
        print("4. Look for logs like 'Available entity names' and 'Found source_id/target_id'")
    
    if invalid_relationships > 0:
        print("5. Some relationship source/target names don't match any entity names")
        print("6. This could be due to name extraction logic in the parser")
        print("7. Check if external entities are being created properly")

if __name__ == "__main__":
    analyze_csv_files()