#!/usr/bin/env python3
"""Test multi-API chart data structure and endpoints"""

import sys
from datetime import datetime, timedelta
sys.path.insert(0, '.')

from app import create_app, db
from app.models import User, API, APILog

def test_multi_api_charts():
    """Test multi-series chart data structure"""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.app_context():
        # Create test database
        db.drop_all()
        db.create_all()
        
        # Create test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        
        # Create multiple test APIs
        api1 = API(name='GitHub', url='https://api.github.com', interval=60, user_id=user.id)
        api2 = API(name='Google', url='https://www.google.com', interval=60, user_id=user.id)
        api3 = API(name='Kubernetes', url='https://kubernetes.default.svc', interval=60, user_id=user.id)
        
        db.session.add_all([api1, api2, api3])
        db.session.commit()
        
        # Add sample logs for each API
        now = datetime.utcnow()
        for api_idx, api in enumerate([api1, api2, api3], 1):
            for hour in range(24):
                timestamp = now - timedelta(hours=24-hour)
                response_time = 200 + (api_idx * 100) + (hour % 5) * 10
                status_code = 200 if (hour + api_idx) % 3 != 0 else 500
                
                log = APILog(
                    api_id=api.id,
                    status_code=status_code,
                    response_time=response_time,
                    timestamp=timestamp
                )
                db.session.add(log)
        
        db.session.commit()
        
        # Test client with authenticated context
        client = app.test_client()
        
        # Login within a request context
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
        
        print("\n=== Testing Multi-API Chart Endpoints ===\n")
        
        # Test single API endpoint
        print("1. Testing single API chart endpoint (/api/chart-data/1)...")
        response = client.get('/api/chart-data/1?hours=24&type=line')
        data = response.get_json()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'labels' in data, "Missing 'labels' in single API response"
        assert 'response_times' in data, "Missing 'response_times' in single API response"
        print("   ✓ Single API endpoint returns correct structure")
        print(f"   - Labels: {len(data['labels'])} timestamps")
        print(f"   - Response times: {len(data['response_times'])} values")
        
        # Test multi-API endpoint
        print("\n2. Testing multi-API chart endpoint (/api/chart-data/all)...")
        response = client.get('/api/chart-data/all?hours=24&type=line')
        data = response.get_json()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'labels' in data, "Missing 'labels' in multi-API response"
        assert 'datasets' in data, "Missing 'datasets' in multi-API response"
        assert isinstance(data['datasets'], list), "datasets should be an array"
        assert len(data['datasets']) == 3, f"Expected 3 datasets, got {len(data['datasets'])}"
        
        print("   ✓ Multi-API endpoint returns Chart.js multi-series format")
        print(f"   - Labels: {len(data['labels'])} shared timestamps")
        print(f"   - Datasets: {len(data['datasets'])} APIs")
        
        # Verify each dataset
        for i, dataset in enumerate(data['datasets'], 1):
            print(f"   - API {i}: {dataset['label']}")
            print(f"     * Data points: {len(dataset['data'])}")
            print(f"     * Border color: {dataset.get('borderColor', 'N/A')}")
            assert 'label' in dataset, f"Dataset {i} missing 'label'"
            assert 'data' in dataset, f"Dataset {i} missing 'data'"
            assert 'borderColor' in dataset, f"Dataset {i} missing 'borderColor'"
            assert len(dataset['data']) == len(data['labels']), \
                f"Dataset {i} data length mismatch: {len(dataset['data'])} != {len(data['labels'])}"
        
        # Test bar chart format
        print("\n3. Testing bar chart multi-series format (/api/chart-data/all?type=bar)...")
        response = client.get('/api/chart-data/all?hours=24&type=bar')
        data = response.get_json()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'datasets' in data, "Missing 'datasets' in bar chart response"
        print("   ✓ Bar chart returns multi-series format")
        print(f"   - Datasets: {len(data['datasets'])} APIs")
        
        # Test analytics endpoint
        print("\n4. Testing multi-API analytics endpoint (/api/analytics/all)...")
        response = client.get('/api/analytics/all?hours=24')
        data = response.get_json()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'total_requests' in data, "Missing 'total_requests'"
        assert 'apis' in data, "Missing 'apis' array in multi-API analytics"
        assert len(data['apis']) == 3, f"Expected 3 APIs in analytics, got {len(data['apis'])}"
        
        print("   ✓ Multi-API analytics returns per-API breakdown")
        print(f"   - Total requests: {data['total_requests']}")
        print(f"   - Success: {data['success_count']}")
        print(f"   - Failed: {data['failure_count']}")
        print(f"   - APIs tracked: {len(data['apis'])}")
        
        for api_data in data['apis']:
            print(f"     * {api_data['name']}: {api_data['requests']} requests, {api_data['uptime']}% uptime")
        
        print("\n=== All Multi-API Tests Passed! ===")
        print("\nSummary:")
        print("✓ Single API chart endpoint works correctly")
        print("✓ Multi-API chart endpoint returns Chart.js multi-series format")
        print("✓ Each API is a separate dataset with color assignment")
        print("✓ Multi-API analytics shows per-API breakdown")
        print("\n✓ Frontend can now display all APIs together with different colors")

if __name__ == '__main__':
    test_multi_api_charts()
