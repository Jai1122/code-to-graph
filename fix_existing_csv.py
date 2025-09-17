#!/usr/bin/env python3
"""
Script to fix null target_ids in existing CSV files.
"""

import csv
import sys
from pathlib import Path

def fix_existing_csv():
    """Fix null target_ids in existing relationship CSV."""
    
    relationships_csv = Path("data/export/graph_relationships.csv")
    nodes_csv = Path("data/export/graph_nodes.csv")
    
    if not relationships_csv.exists() or not nodes_csv.exists():
        print("❌ CSV files not found. Run analysis first.")
        return
    
    # Load entity mappings
    entities = {}
    with open(nodes_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities[row['name']] = row['id']
    
    print(f"📋 Loaded {len(entities)} entities")
    
    # Fix relationships
    fixed_relationships = []
    null_count = 0
    fixed_count = 0
    
    with open(relationships_csv, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            if not row['target_id'] or row['target_id'].lower() == 'null':
                null_count += 1
                
                # Try to extract target name from properties
                props = row.get('properties', '')
                target_name = None
                
                if 'target_name' in props:
                    # Extract target_name from properties string
                    import re
                    match = re.search(r"'target_name': '([^']+)'", props)
                    if match:
                        target_name = match.group(1)
                
                if target_name and target_name in entities:
                    row['target_id'] = entities[target_name]
                    fixed_count += 1
                    print(f"✅ Fixed: {target_name} -> {entities[target_name]}")
                else:
                    # Create external entity
                    if target_name:
                        external_id = f"external_{abs(hash(target_name))}"
                        row['target_id'] = external_id
                        entities[target_name] = external_id
                        fixed_count += 1
                        print(f"🆕 Created external: {target_name} -> {external_id}")
            
            fixed_relationships.append(row)
    
    # Write fixed CSV
    backup_file = relationships_csv.with_suffix('.csv.backup')
    relationships_csv.rename(backup_file)
    
    with open(relationships_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fixed_relationships)
    
    print(f"📊 Results: {null_count} null target_ids found, {fixed_count} fixed")
    print(f"💾 Backup saved to: {backup_file}")
    print(f"✅ Fixed CSV saved to: {relationships_csv}")

if __name__ == "__main__":
    fix_existing_csv()
