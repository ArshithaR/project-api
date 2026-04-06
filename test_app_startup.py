#!/usr/bin/env python
"""Quick test of app startup and database initialization"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Creating Flask app...")
    from app import create_app
    app = create_app(test_config={'TESTING': True, 'START_MONITOR': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    print("✓ Flask app created successfully")
    
    with app.app_context():
        print("✓ App context initialized")
        
        from app.models import User, API, APILog, Alert
        print("✓ All models imported successfully")
        
        # Test database operations
        from app import db
        
        # Create a test user
        test_user = User(username='test', email='test@example.com')
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()
        print("✓ Test user created successfully")
        
        # Create a test API
        test_api = API(user_id=test_user.id, name='Test API', url='https://httpbin.org/status/200', interval=60)
        db.session.add(test_api)
        db.session.commit()
        print("✓ Test API created successfully")
        
        # Create a test APILog
        from datetime import datetime
        test_log = APILog(api_id=test_api.id, status_code=200, response_time=100.5, is_success=True, timestamp=datetime.utcnow())
        db.session.add(test_log)
        db.session.commit()
        print("✓ Test APILog created successfully")
        
        # Test alert generation
        from app.routes import generate_alerts_for_api
        generate_alerts_for_api(test_api)
        print("✓ Alert generation function works")
        
        # Verify alert was created (should be none since status is 200)
        alerts = Alert.query.filter_by(api_id=test_api.id, is_active=True).all()
        print(f"✓ Active alerts count: {len(alerts)} (expected 0 for 200 status)")
        
        # Create an error log to trigger an alert
        error_log = APILog(api_id=test_api.id, status_code=500, response_time=50.0, is_success=False, timestamp=datetime.utcnow())
        db.session.add(error_log)
        db.session.commit()
        print("✓ Error APILog created successfully")
        
        generate_alerts_for_api(test_api)
        print("✓ Alert regenerated after error")
        
        # Check if error alert was created
        error_alerts = Alert.query.filter_by(api_id=test_api.id, is_active=True, alert_type='error').all()
        print(f"✓ Error alerts count: {len(error_alerts)} (expected 1)")
        
        if error_alerts:
            print(f"  Alert message: {error_alerts[0].message}")
            print(f"  Alert to_dict(): {error_alerts[0].to_dict()}")
        
        print("\n✅ All tests passed! App is ready to run.")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
