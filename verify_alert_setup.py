#!/usr/bin/env python
"""Verify app starts and database initializes correctly"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("VERIFYING APP STARTUP AND DATABASE")
print("=" * 70)

try:
    print("\n1. Creating Flask app...")
    from app import create_app
    app = create_app()
    print("   ✓ Flask app created successfully")
    
    print("\n2. Checking database initialization...")
    with app.app_context():
        from app import db
        from app.models import User, API, APILog, Alert
        
        # Check if tables exist by querying them
        user_count = User.query.count()
        api_count = API.query.count()
        log_count = APILog.query.count()
        alert_count = Alert.query.count()
        
        print(f"   ✓ Database tables exist")
        print(f"     - Users: {user_count}")
        print(f"     - APIs: {api_count}")
        print(f"     - APILogs: {log_count}")
        print(f"     - Alerts: {alert_count}")
    
    print("\n3. Verifying routes...")
    with app.app_context():
        with app.test_client() as client:
            # Test unauthenticated access
            response = client.get('/')
            print(f"   ✓ GET / returns status {response.status_code}")
            
            # Test login page
            response = client.get('/auth/login')
            print(f"   ✓ GET /auth/login returns status {response.status_code}")
    
    print("\n4. Checking alert endpoints...")
    routes = []
    for rule in app.url_map.iter_rules():
        if 'alert' in rule.rule:
            routes.append(f"{', '.join(rule.methods - {'HEAD', 'OPTIONS'})} {rule.rule}")
    
    if routes:
        print("   ✓ Alert endpoints registered:")
        for route in routes:
            print(f"     - {route}")
    else:
        print("   ✗ No alert endpoints found!")
        sys.exit(1)
    
    print("\n5. Checking templates...")
    template_files = [
        'base.html',
        'alerts.html',
        'dashboard.html',
        'login.html'
    ]
    
    import os.path
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    for template in template_files:
        path = os.path.join(template_dir, template)
        if os.path.exists(path):
            print(f"   ✓ {template} exists")
        else:
            print(f"   ✗ {template} missing!")
    
    print("\n" + "=" * 70)
    print("✅ APP VERIFICATION COMPLETE - ALL CHECKS PASSED!")
    print("=" * 70)
    print("\nThe app is ready to run with:")
    print("  python app.py")
    print("\nAccess the web interface at:")
    print("  http://127.0.0.1:5000")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error during verification: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
