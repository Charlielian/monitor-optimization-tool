#!/usr/bin/env python3
"""
Script to fix all endpoint references in template files after Blueprint refactoring
"""

import os
import re

# Mapping of old endpoints to new Blueprint-prefixed endpoints
# Format: (old_endpoint, new_endpoint)
# NOTE: login and logout are NOT in blueprints, they remain in app.py
ENDPOINT_MAPPINGS = [
    # Main blueprint
    ('dashboard', 'main.dashboard'),
    ('monitor', 'main.monitor'),
    ('cell', 'main.cell'),
    ('scenarios', 'main.scenarios'),
    
    # Admin blueprint
    ('admin_add_user', 'admin.admin_add_user'),
    ('admin_delete_user', 'admin.admin_delete_user'),
    ('admin_change_password', 'admin.admin_change_password'),
    ('admin_get_user_permissions', 'admin.admin_get_user_permissions'),
    ('admin_update_user_permissions', 'admin.admin_update_user_permissions'),
    ('admin_reset_user_permissions', 'admin.admin_reset_user_permissions'),
    ('admin', 'admin.admin'),
    
    # Alarm blueprint
    ('alarm_nokia', 'alarm.alarm_nokia'),  # Must come before 'alarm'
    ('alarm', 'alarm.alarm'),
    ('export_current_alarms_nokia', 'alarm.export_current_alarms_nokia'),
    ('export_historical_alarms_nokia', 'alarm.export_historical_alarms_nokia'),
    ('export_current_alarms', 'alarm.export_current_alarms'),
    ('export_historical_alarms', 'alarm.export_historical_alarms'),
    
    # Grid blueprint
    ('grid_detail', 'grid.grid_detail'),  # Must come before 'grid'
    ('grid_autocomplete', 'grid.grid_autocomplete'),
    ('grid', 'grid.grid'),
    ('export_traffic_degraded', 'grid.export_traffic_degraded'),
    ('export_no_traffic_increased', 'grid.export_no_traffic_increased'),
    
    # Export blueprint
    ('export_top_utilization', 'export.export_top_utilization'),
    ('export_scenario_cells', 'export.export_scenario_cells'),
    ('export_cell_data', 'export.export_cell_data'),
    ('export_latest_metrics', 'export.export_latest_metrics'),
    ('export_monitor_xlsx_full', 'export.export_monitor_xlsx_full'),
    ('export_monitor_xlsx', 'export.export_monitor_xlsx'),
    ('export_monitor', 'export.export_monitor'),
    ('export_traffic', 'export.export_traffic'),
    ('export_top', 'export.export_top'),
    ('download_cell_template', 'export.download_cell_template'),
]

def fix_template_file(filepath):
    """Fix endpoint references in a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    for old_endpoint, new_endpoint in ENDPOINT_MAPPINGS:
        # Pattern to match url_for with the old endpoint (with or without parameters)
        # Matches: url_for('old_endpoint') or url_for("old_endpoint")
        # Also matches: url_for('old_endpoint', param=value)
        # DOTALL flag allows . to match newlines for multi-line url_for calls
        pattern = rf"url_for\(['\"]({re.escape(old_endpoint)})['\"](.*?)\)"
        
        def replacer(match):
            params = match.group(2)
            return f"url_for('{new_endpoint}'{params})"
        
        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        if new_content != content:
            matches = len(re.findall(pattern, content, flags=re.DOTALL))
            changes_made += matches
            content = new_content
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes_made
    
    return 0

def main():
    """Fix all template files"""
    templates_dir = 'templates'
    total_changes = 0
    files_modified = 0
    
    print("=" * 70)
    print("Fixing Template Endpoint References (with parameters)")
    print("=" * 70)
    
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            changes = fix_template_file(filepath)
            if changes > 0:
                print(f"✓ {filename:30} - {changes} changes")
                total_changes += changes
                files_modified += 1
    
    print("=" * 70)
    print(f"Summary: {files_modified} files modified, {total_changes} total changes")
    print("=" * 70)

if __name__ == "__main__":
    main()
