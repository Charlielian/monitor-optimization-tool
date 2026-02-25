#!/usr/bin/env python3
"""
Route Verification Script

This script verifies that all routes are accessible after the refactoring.
It tests all URL patterns to ensure backward compatibility.

Task: 9. Checkpoint - 确保所有路由正常工作
"""

import sys
import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def verify_routes():
    """Verify all routes are registered correctly"""
    
    print("=" * 60)
    print("🔍 Route Verification - Task 9 Checkpoint")
    print("=" * 60)
    print()
    
    # Create the Flask app
    try:
        app = create_app()
        print("✓ Flask app created successfully")
    except Exception as e:
        print(f"✗ Failed to create Flask app: {e}")
        return False
    
    # Get all registered routes
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
                'path': str(rule)
            })
    
    # Sort routes by path for better readability
    routes.sort(key=lambda x: x['path'])
    
    # Expected route categories
    expected_routes = {
        'Authentication': [
            '/login',
            '/logout',
        ],
        'Main Business': [
            '/',  # dashboard
            '/cell',
            '/monitor',
            '/scenarios',
            '/api/performance/log',
            '/api/scenarios/cells',
        ],
        'Admin': [
            '/admin',
            '/admin/add_user',
            '/admin/delete_user',
            '/admin/change_password',
            '/admin/get_user_permissions',
            '/admin/update_user_permissions',
            '/admin/reset_user_permissions',
        ],
        'Alarm (ZTE)': [
            '/alarm',
            '/export/current_alarms.xlsx',
            '/export/historical_alarms.xlsx',
        ],
        'Alarm (Nokia)': [
            '/alarm_nokia',
            '/export/current_alarms_nokia.xlsx',
            '/export/historical_alarms_nokia.xlsx',
        ],
        'Grid Monitoring': [
            '/grid',
            '/grid/<grid_id>',
            '/api/grid/autocomplete',
            '/grid/export/traffic_degraded',
            '/grid/export/no_traffic_increased',
        ],
        'Export': [
            '/export/traffic.csv',
            '/export/top.csv',
            '/export/monitor.csv',
            '/export/monitor.xlsx',
            '/export/monitor_xlsx_full',
            '/export/latest_metrics.xlsx',
            '/export/cell_data.xlsx',
            '/export/top_utilization.xlsx',
            '/scenarios/download_template',
            '/scenarios/export_cells',
        ],
        'System': [
            '/health',
            '/test_navigation',
        ],
        'API v1': [
            '/api/v1/health',
            '/api/v1/performance/log',
        ],
    }
    
    # Flatten expected routes for checking
    all_expected = []
    for category, paths in expected_routes.items():
        all_expected.extend(paths)
    
    # Check each category
    print("\n📋 Route Verification by Category:")
    print("-" * 60)
    
    total_found = 0
    total_expected = 0
    missing_routes = []
    
    for category, expected_paths in expected_routes.items():
        print(f"\n{category}:")
        found_count = 0
        
        for expected_path in expected_paths:
            # Find matching route (handle dynamic segments)
            found = False
            for route in routes:
                route_path = route['path']
                # Simple matching (exact or with dynamic segments)
                if route_path == expected_path or \
                   (expected_path.replace('<', '').replace('>', '') in route_path.replace('<', '').replace('>', '')):
                    found = True
                    found_count += 1
                    print(f"  ✓ {expected_path:45} [{route['methods']:15}] -> {route['endpoint']}")
                    break
            
            if not found:
                print(f"  ✗ {expected_path:45} [MISSING]")
                missing_routes.append(expected_path)
        
        total_found += found_count
        total_expected += len(expected_paths)
        print(f"  Found: {found_count}/{len(expected_paths)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary:")
    print("=" * 60)
    print(f"Total routes registered: {len(routes)}")
    print(f"Expected routes found: {total_found}/{total_expected}")
    
    if missing_routes:
        print(f"\n⚠️  Missing routes ({len(missing_routes)}):")
        for route in missing_routes:
            print(f"  - {route}")
    
    # Check for unexpected routes (might be okay, just informational)
    registered_paths = [r['path'] for r in routes]
    unexpected = []
    for route in routes:
        path = route['path']
        # Check if this path matches any expected pattern
        is_expected = False
        for exp_path in all_expected:
            if path == exp_path or \
               (exp_path.replace('<', '').replace('>', '') in path.replace('<', '').replace('>', '')):
                is_expected = True
                break
        if not is_expected:
            unexpected.append(route)
    
    if unexpected:
        print(f"\nℹ️  Additional routes (not in expected list):")
        for route in unexpected:
            print(f"  + {route['path']:45} [{route['methods']:15}] -> {route['endpoint']}")
    
    # Final verdict
    print("\n" + "=" * 60)
    if missing_routes:
        print("❌ VERIFICATION FAILED: Some expected routes are missing")
        print("=" * 60)
        return False
    else:
        print("✅ VERIFICATION PASSED: All expected routes are registered")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = verify_routes()
    sys.exit(0 if success else 1)
