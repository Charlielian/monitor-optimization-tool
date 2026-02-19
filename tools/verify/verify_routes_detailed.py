#!/usr/bin/env python3
"""
Detailed Route Verification Script

This script performs detailed verification of routes including:
1. Route registration check
2. Blueprint assignment verification
3. Route conflict detection
4. Endpoint correctness validation

Task: 9. Checkpoint - 确保所有路由正常工作
"""

import sys
import logging
from app import create_app
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(levelname)s: %(message)s'
)

def verify_routes_detailed():
    """Perform detailed route verification"""
    
    print("=" * 70)
    print("🔍 Detailed Route Verification - Task 9 Checkpoint")
    print("=" * 70)
    print()
    
    # Create the Flask app
    try:
        app = create_app()
        print("✓ Flask app created successfully\n")
    except Exception as e:
        print(f"✗ Failed to create Flask app: {e}")
        return False
    
    # Expected blueprint assignments
    expected_blueprints = {
        'main': [
            '/', '/cell', '/monitor', '/scenarios',
            '/api/performance/log', '/api/scenarios/cells'
        ],
        'admin': [
            '/admin', '/admin/add_user', '/admin/delete_user',
            '/admin/change_password', '/admin/get_user_permissions',
            '/admin/update_user_permissions', '/admin/reset_user_permissions'
        ],
        'alarm': [
            '/alarm', '/alarm_nokia',
            '/export/current_alarms.xlsx', '/export/historical_alarms.xlsx',
            '/export/current_alarms_nokia.xlsx', '/export/historical_alarms_nokia.xlsx'
        ],
        'grid': [
            '/grid', '/grid/<grid_id>', '/api/grid/autocomplete',
            '/grid/export/traffic_degraded', '/grid/export/no_traffic_increased'
        ],
        'export': [
            '/export/traffic.csv', '/export/top.csv',
            '/export/monitor.csv', '/export/monitor.xlsx',
            '/export/monitor_xlsx_full', '/export/latest_metrics.xlsx',
            '/export/cell_data.xlsx', '/export/top_utilization.xlsx',
            '/export/scenarios/download_template', '/export/scenarios/export_cells'
        ],
    }
    
    # Collect all routes
    routes_by_blueprint = {}
    all_routes = []
    
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        
        # Extract blueprint name from endpoint
        blueprint_name = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'app'
        
        route_info = {
            'path': str(rule),
            'endpoint': rule.endpoint,
            'methods': sorted(rule.methods - {'HEAD', 'OPTIONS'}),
            'blueprint': blueprint_name
        }
        
        all_routes.append(route_info)
        
        if blueprint_name not in routes_by_blueprint:
            routes_by_blueprint[blueprint_name] = []
        routes_by_blueprint[blueprint_name].append(route_info)
    
    # Verify blueprint assignments
    print("📋 Blueprint Assignment Verification:")
    print("-" * 70)
    
    issues = []
    
    for blueprint, expected_paths in expected_blueprints.items():
        print(f"\n{blueprint.upper()} Blueprint:")
        
        for expected_path in expected_paths:
            # Find the route
            found = False
            correct_blueprint = False
            
            for route in all_routes:
                # Match path exactly (no fuzzy matching for root route)
                if route['path'] == expected_path:
                    found = True
                    if route['blueprint'] == blueprint:
                        correct_blueprint = True
                        print(f"  ✓ {expected_path:45} -> {route['endpoint']}")
                    else:
                        print(f"  ⚠️  {expected_path:45} -> {route['endpoint']} (wrong blueprint: {route['blueprint']})")
                        issues.append(f"Route {expected_path} is in {route['blueprint']} blueprint, expected {blueprint}")
                    break
            
            if not found:
                print(f"  ✗ {expected_path:45} [MISSING]")
                issues.append(f"Route {expected_path} not found")
    
    # Check for route conflicts (same path, different endpoints)
    print("\n\n🔍 Route Conflict Detection:")
    print("-" * 70)
    
    path_to_routes = {}
    for route in all_routes:
        path = route['path']
        if path not in path_to_routes:
            path_to_routes[path] = []
        path_to_routes[path].append(route)
    
    conflicts = []
    for path, routes in path_to_routes.items():
        if len(routes) > 1:
            # Check if they have overlapping methods
            methods_by_endpoint = {}
            for route in routes:
                endpoint = route['endpoint']
                methods = set(route['methods'])
                if endpoint not in methods_by_endpoint:
                    methods_by_endpoint[endpoint] = methods
                else:
                    methods_by_endpoint[endpoint].update(methods)
            
            # Check for conflicts
            all_methods = set()
            for methods in methods_by_endpoint.values():
                if all_methods & methods:
                    conflicts.append({
                        'path': path,
                        'routes': routes
                    })
                    break
                all_methods.update(methods)
    
    if conflicts:
        print("⚠️  Found route conflicts:")
        for conflict in conflicts:
            print(f"\n  Path: {conflict['path']}")
            for route in conflict['routes']:
                print(f"    - {route['endpoint']:40} [{','.join(route['methods'])}]")
        issues.extend([f"Route conflict at {c['path']}" for c in conflicts])
    else:
        print("✓ No route conflicts detected")
    
    # Check critical routes
    print("\n\n🎯 Critical Route Verification:")
    print("-" * 70)
    
    critical_routes = {
        '/': 'Dashboard (main page)',
        '/login': 'Login page',
        '/logout': 'Logout',
        '/admin': 'Admin dashboard',
        '/alarm': 'ZTE alarm monitoring',
        '/alarm_nokia': 'Nokia alarm monitoring',
        '/grid': 'Grid monitoring',
        '/cell': 'Cell query',
        '/monitor': 'Monitoring page',
        '/scenarios': 'Scenario management',
    }
    
    for path, description in critical_routes.items():
        found = any(r['path'] == path for r in all_routes)
        if found:
            route = next(r for r in all_routes if r['path'] == path)
            print(f"  ✓ {path:20} - {description:30} [{route['endpoint']}]")
        else:
            print(f"  ✗ {path:20} - {description:30} [MISSING]")
            issues.append(f"Critical route {path} ({description}) not found")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("📊 Verification Summary:")
    print("=" * 70)
    print(f"Total routes registered: {len(all_routes)}")
    print(f"Blueprints found: {', '.join(sorted(routes_by_blueprint.keys()))}")
    print(f"Issues found: {len(issues)}")
    
    if issues:
        print(f"\n⚠️  Issues detected:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print("\n" + "=" * 70)
        print("❌ VERIFICATION FAILED")
        print("=" * 70)
        return False
    else:
        print("\n" + "=" * 70)
        print("✅ VERIFICATION PASSED: All routes are correctly registered")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = verify_routes_detailed()
    sys.exit(0 if success else 1)
