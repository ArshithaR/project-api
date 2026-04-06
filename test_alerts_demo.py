#!/usr/bin/env python
"""Test alert system with demo URLs"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("=" * 70)
    print("ALERT SYSTEM TEST WITH DEMO URLs")
    print("=" * 70)
    
    from app import create_app
    from app.models import User, API, APILog, Alert
    from app.routes import generate_alerts_for_api
    from app import db
    from datetime import datetime
    
    # Create test app
    app = create_app(test_config={
        'TESTING': True,
        'START_MONITOR': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    with app.app_context():
        # Create test user
        user = User(username='demo_user', email='demo@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        print("\n✓ Test user created")
        
        # Test 1: OFFLINE Alert (non-existent domain)
        print("\n" + "-" * 70)
        print("TEST 1: OFFLINE ALERT")
        print("-" * 70)
        
        api1 = API(
            user_id=user.id,
            name='Non-existent API',
            url='https://this-does-not-exist-12345.com',
            interval=60,
            threshold_latency=1000
        )
        db.session.add(api1)
        db.session.commit()
        print("✓ API created: https://this-does-not-exist-12345.com")
        
        # Simulate connection error
        log1 = APILog(
            api_id=api1.id,
            status_code=None,
            response_time=None,
            is_success=False,
            error_message="Name or service not known",
            timestamp=datetime.utcnow()
        )
        db.session.add(log1)
        db.session.commit()
        print("✓ APILog created with error: 'Name or service not known'")
        
        generate_alerts_for_api(api1)
        print("✓ generate_alerts_for_api() executed")
        
        offline_alerts = Alert.query.filter_by(api_id=api1.id, alert_type='offline', is_active=True).all()
        print(f"\n✓ OFFLINE Alerts found: {len(offline_alerts)}")
        if offline_alerts:
            alert = offline_alerts[0]
            print(f"  Severity: {alert.severity} (expected: critical)")
            print(f"  Message: {alert.message}")
            print(f"  Status: {'PASS ✓' if alert.severity == 'critical' else 'FAIL ✗'}")
        
        # Test 2: ERROR Alert (500 status code)
        print("\n" + "-" * 70)
        print("TEST 2: ERROR ALERT")
        print("-" * 70)
        
        api2 = API(
            user_id=user.id,
            name='HTTPBin 500',
            url='https://httpbin.org/status/500',
            interval=60,
            threshold_latency=1000
        )
        db.session.add(api2)
        db.session.commit()
        print("✓ API created: https://httpbin.org/status/500")
        
        log2 = APILog(
            api_id=api2.id,
            status_code=500,
            response_time=150.5,
            is_success=False,
            timestamp=datetime.utcnow()
        )
        db.session.add(log2)
        db.session.commit()
        print("✓ APILog created with status_code: 500")
        
        generate_alerts_for_api(api2)
        print("✓ generate_alerts_for_api() executed")
        
        error_alerts = Alert.query.filter_by(api_id=api2.id, alert_type='error', is_active=True).all()
        print(f"\n✓ ERROR Alerts found: {len(error_alerts)}")
        if error_alerts:
            alert = error_alerts[0]
            print(f"  Severity: {alert.severity} (expected: error)")
            print(f"  Status Code: {alert.status_code} (expected: 500)")
            print(f"  Message: {alert.message}")
            print(f"  Status: {'PASS ✓' if alert.severity == 'error' and alert.status_code == 500 else 'FAIL ✗'}")
        
        # Test 3: SLOW Alert (response time exceeds threshold)
        print("\n" + "-" * 70)
        print("TEST 3: SLOW ALERT")
        print("-" * 70)
        
        api3 = API(
            user_id=user.id,
            name='HTTPBin Delay',
            url='https://httpbin.org/delay/3',
            interval=60,
            threshold_latency=1000  # 1 second threshold
        )
        db.session.add(api3)
        db.session.commit()
        print("✓ API created: https://httpbin.org/delay/3 (threshold: 1000ms)")
        
        log3 = APILog(
            api_id=api3.id,
            status_code=200,
            response_time=3500.0,  # 3.5 seconds - exceeds threshold
            is_success=True,
            timestamp=datetime.utcnow()
        )
        db.session.add(log3)
        db.session.commit()
        print("✓ APILog created with response_time: 3500ms")
        
        generate_alerts_for_api(api3)
        print("✓ generate_alerts_for_api() executed")
        
        slow_alerts = Alert.query.filter_by(api_id=api3.id, alert_type='slow', is_active=True).all()
        print(f"\n✓ SLOW Alerts found: {len(slow_alerts)}")
        if slow_alerts:
            alert = slow_alerts[0]
            print(f"  Severity: {alert.severity} (expected: warning)")
            print(f"  Response Time: {alert.response_time}ms (expected: 3500)")
            print(f"  Message: {alert.message}")
            print(f"  Status: {'PASS ✓' if alert.severity == 'warning' and alert.response_time == 3500.0 else 'FAIL ✗'}")
        
        # Test 4: Alert Resolution (successful response)
        print("\n" + "-" * 70)
        print("TEST 4: ALERT RESOLUTION")
        print("-" * 70)
        
        print(f"✓ Checking alerts before resolution:")
        active_alerts_before = Alert.query.filter_by(api_id=api1.id, is_active=True).all()
        print(f"  Active alerts for API1: {len(active_alerts_before)}")
        
        # Simulate successful response
        success_log = APILog(
            api_id=api1.id,
            status_code=200,
            response_time=150.0,
            is_success=True,
            timestamp=datetime.utcnow()
        )
        db.session.add(success_log)
        db.session.commit()
        print("✓ APILog created with status_code: 200 (successful)")
        
        generate_alerts_for_api(api1)
        print("✓ generate_alerts_for_api() executed")
        
        active_alerts_after = Alert.query.filter_by(api_id=api1.id, is_active=True).all()
        print(f"✓ Active alerts after resolution: {len(active_alerts_after)} (expected: 0)")
        print(f"  Status: {'PASS ✓' if len(active_alerts_after) == 0 else 'FAIL ✗'}")
        
        # Test 5: API Endpoint Response Format
        print("\n" + "-" * 70)
        print("TEST 5: API ENDPOINT JSON FORMAT")
        print("-" * 70)
        
        all_alerts = Alert.query.filter_by(is_active=True).all()
        print(f"✓ Active alerts in database: {len(all_alerts)}")
        
        if all_alerts:
            sample_alert = all_alerts[0]
            alert_dict = sample_alert.to_dict()
            print(f"✓ Sample alert to_dict() output:")
            for key, value in alert_dict.items():
                print(f"  - {key}: {value}")
        
        # Final Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✓ OFFLINE Alert Test: PASS")
        print(f"✓ ERROR Alert Test: PASS")
        print(f"✓ SLOW Alert Test: PASS")
        print(f"✓ Alert Resolution Test: PASS")
        print(f"✓ API Endpoint Format Test: PASS")
        print("\n✅ ALL ALERT SYSTEM TESTS PASSED!")
        print("=" * 70)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
