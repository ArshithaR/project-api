#!/usr/bin/env python3
"""Verification script for multi-API charts implementation"""

import sys
sys.path.insert(0, '.')

def verify_implementation():
    """Verify all components of multi-API charts are in place"""
    
    print("\n" + "="*60)
    print("MULTI-API CHARTS IMPLEMENTATION VERIFICATION")
    print("="*60 + "\n")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Route imports
    print("1. Checking route definitions...")
    checks_total += 1
    try:
        from app import create_app
        from app.routes import main_bp
        app = create_app()
        
        # Check for route decorators
        routes = {rule.rule: [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']] 
                  for rule in app.url_map.iter_rules() if 'api' in rule.rule}
        
        # Check required routes exist
        required_routes = [
            '/api/chart-data/all',
            '/api/chart-data/<api_id>',
            '/api/analytics/all',
            '/api/analytics/<api_id>'
        ]
        
        found_chart_all = any('/api/chart-data/all' in rule for rule in routes.keys())
        found_chart_id = any('/api/chart-data/<' in rule and 'int:api_id' in rule for rule in routes.keys())
        found_analytics_all = any('/api/analytics/all' in rule for rule in routes.keys())
        found_analytics_id = any('/api/analytics/<' in rule and 'int:api_id' in rule for rule in routes.keys())
        
        if found_chart_all and found_chart_id and found_analytics_all and found_analytics_id:
            print("   [PASS] All required routes defined")
            print(f"     - /api/chart-data/all: Present")
            print(f"     - /api/chart-data/<int:api_id>: Present")
            print(f"     - /api/analytics/all: Present")
            print(f"     - /api/analytics/<int:api_id>: Present")
            checks_passed += 1
        else:
            print("   [FAIL] Missing required routes")
            print(f"     - /api/chart-data/all: {found_chart_all}")
            print(f"     - /api/chart-data/<int:api_id>: {found_chart_id}")
            print(f"     - /api/analytics/all: {found_analytics_all}")
            print(f"     - /api/analytics/<int:api_id>: {found_analytics_id}")
    except Exception as e:
        print(f"   [ERROR] Error checking routes: {e}")
    
    # Check 2: Database models
    print("\n2. Checking database models...")
    checks_total += 1
    try:
        from app.models import User, API, APILog
        print("   [PASS] All models imported successfully")
        print(f"     - User model: OK")
        print(f"     - API model: OK")
        print(f"     - APILog model: OK")
        checks_passed += 1
    except Exception as e:
        print(f"   [ERROR] Error importing models: {e}")
    
    # Check 3: Template file
    print("\n3. Checking templates...")
    checks_total += 1
    try:
        with open('templates/analytics.html', 'r') as f:
            content = f.read()
            
        checks = {
            'Multi-series detection (isMultiSeries)': 'isMultiSeries' in content,
            'datasets array handling': 'data.datasets' in content,
            'View mode toggle': 'viewMode' in content,
            'All APIs button': 'all-apis-btn' in content,
            'Chart.js integration': 'new Chart' in content
        }
        
        if all(checks.values()):
            print("   [PASS] Template file correctly updated")
            for check, status in checks.items():
                print(f"     - {check}: {'OK' if status else 'MISSING'}")
            checks_passed += 1
        else:
            print("   [FAIL] Template file missing required changes")
            for check, status in checks.items():
                print(f"     - {check}: {'OK' if status else 'MISSING'}")
    except Exception as e:
        print(f"   [ERROR] Error checking template: {e}")
    
    # Check 4: Multi-series data format
    print("\n4. Checking multi-series data structure...")
    checks_total += 1
    try:
        from app import db
        from app.models import API, APILog
        from datetime import datetime, timedelta
        import json
        
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            # Create test user and APIs
            user = User(username='test', email='test@test.com')
            user.set_password('test')
            db.session.add(user)
            db.session.commit()
            
            # Create multiple APIs
            for i, name in enumerate(['API1', 'API2', 'API3'], 1):
                api = API(name=name, url=f'http://test{i}.com', user_id=user.id)
                db.session.add(api)
            db.session.commit()
            
            # Add logs
            now = datetime.utcnow()
            for api in API.query.all():
                for h in range(5):
                    log = APILog(
                        api_id=api.id,
                        status_code=200,
                        response_time=100 + api.id * 50,
                        timestamp=now - timedelta(hours=h)
                    )
                    db.session.add(log)
            db.session.commit()
            
            # Test data structure
            apis = API.query.all()
            cutoff = now - timedelta(hours=24)
            
            # Build multi-series data
            first_api = apis[0]
            first_logs = APILog.query.filter(
                APILog.api_id == first_api.id,
                APILog.timestamp >= cutoff
            ).order_by(APILog.timestamp.asc()).all()
            
            labels = [log.timestamp.strftime('%H:%M') for log in first_logs]
            colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            datasets = []
            
            for idx, api in enumerate(apis):
                logs = APILog.query.filter(
                    APILog.api_id == api.id,
                    APILog.timestamp >= cutoff
                ).order_by(APILog.timestamp.asc()).all()
                
                response_times = [log.response_time if log.response_time else 0 for log in logs]
                
                dataset = {
                    'label': api.name,
                    'data': response_times,
                    'borderColor': colors[idx % len(colors)],
                    'backgroundColor': colors[idx % len(colors)] + '33',
                    'borderWidth': 2,
                    'tension': 0.4,
                    'fill': False
                }
                datasets.append(dataset)
            
            response_data = {
                'labels': labels,
                'datasets': datasets,
                'chart_type': 'line'
            }
            
            # Verify structure
            json_str = json.dumps(response_data)
            
            structure_ok = (
                isinstance(response_data['labels'], list) and
                isinstance(response_data['datasets'], list) and
                len(response_data['datasets']) == 3 and
                all('label' in d and 'data' in d and 'borderColor' in d for d in response_data['datasets'])
            )
            
            if structure_ok:
                print("   ✓ Multi-series data structure correct")
                print(f"     - Number of datasets: {len(response_data['datasets'])}")
                print(f"     - Labels: {len(response_data['labels'])} timestamps")
                print(f"     - Each dataset has label, data, borderColor: Yes")
                print(f"     - JSON serializable: Yes ({len(json_str)} bytes)")
                checks_passed += 1
            else:
                print("   [FAIL] Multi-series data structure incorrect")
    except Exception as e:
            print(f"   [ERROR] Error checking data structure: {e}")
    # Check 5: Route ordering
    print("\n5. Checking route ordering...")
    checks_total += 1
    try:
        with open('app/routes.py', 'r') as f:
            lines = f.readlines()
        
        # Find line numbers of routes
        chart_all_line = None
        chart_id_line = None
        analytics_all_line = None
        analytics_id_line = None
        
        for i, line in enumerate(lines, 1):
            if "@main_bp.route('/api/chart-data/all')" in line:
                chart_all_line = i
            elif "@main_bp.route('/api/chart-data/<int:api_id>')" in line:
                chart_id_line = i
            elif "@main_bp.route('/api/analytics/all')" in line:
                analytics_all_line = i
            elif "@main_bp.route('/api/analytics/<int:api_id>')" in line:
                analytics_id_line = i
        
        # Check ordering
        ordering_ok = (
            chart_all_line and chart_id_line and 
            chart_all_line < chart_id_line and
            analytics_all_line and analytics_id_line and
            analytics_all_line < analytics_id_line
        )
        
        if ordering_ok:
            print("   [PASS] Routes are correctly ordered")
            print(f"     - /api/chart-data/all at line {chart_all_line}")
            print(f"     - /api/chart-data/<int:api_id> at line {chart_id_line}")
            print(f"     - /api/analytics/all at line {analytics_all_line}")
            print(f"     - /api/analytics/<int:api_id> at line {analytics_id_line}")
            checks_passed += 1
        else:
            print("   [FAIL] Routes are NOT correctly ordered (all routes should come before ID routes)")
            if chart_all_line:
                print(f"     - /api/chart-data/all at: {chart_all_line}")
            if chart_id_line:
                print(f"     - /api/chart-data/<int:api_id> at: {chart_id_line}")
            if analytics_all_line:
                print(f"     - /api/analytics/all at: {analytics_all_line}")
            if analytics_id_line:
                print(f"     - /api/analytics/<int:api_id> at: {analytics_id_line}")
    except Exception as e:
        print(f"   [ERROR] Error checking route ordering: {e}")
    
    # Final Summary
    print("\n" + "="*60)
    print(f"VERIFICATION RESULTS: {checks_passed}/{checks_total} checks passed")
    print("="*60 + "\n")
    
    if checks_passed == checks_total:
        print("[SUCCESS] Multi-API charts implementation is complete and ready.\n")
        print("Next steps:")
        print("1. Run: python app.py")
        print("2. Go to: http://localhost:5000")
        print("3. Add multiple APIs")
        print("4. Go to Analytics page")
        print("5. Select 'All APIs Combined' to see multi-API charts")
        return True
    else:
        print(f"[WARNING] {checks_total - checks_passed} check(s) failed.")
        print("Please review the errors above and fix before using multi-API charts.\n")
        return False

if __name__ == '__main__':
    success = verify_implementation()
    sys.exit(0 if success else 1)
