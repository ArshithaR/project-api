#!/usr/bin/env python3
"""Quick test of multi-API charts feature"""
from app import create_app, db
from app.models import User, API, APILog
from datetime import datetime, timedelta

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    db.drop_all()
    db.create_all()
    
    user = User(username='testuser', email='test@example.com')
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()
    
    api1 = API(name='GitHub', url='https://api.github.com', interval=60, user_id=user.id)
    api2 = API(name='Google', url='https://www.google.com', interval=60, user_id=user.id)
    db.session.add_all([api1, api2])
    db.session.commit()
    
    now = datetime.utcnow()
    for api_idx, api in enumerate([api1, api2], 1):
        for h in range(5):
            ts = now - timedelta(hours=5-h)
            log = APILog(api_id=api.id, status_code=200, response_time=100+api_idx*50+h*10, timestamp=ts)
            db.session.add(log)
    db.session.commit()
    
    client = app.test_client()
    from flask_login import login_user
    with app.test_request_context():
        login_user(user)
    
    print('Testing /api/chart-data/all endpoint...')
    response = client.get('/api/chart-data/all?hours=24&type=line')
    data = response.get_json()
    print('Status: ' + str(response.status_code))
    print('Has labels: ' + str('labels' in data))
    print('Has datasets: ' + str('datasets' in data))
    print('Number of datasets: ' + str(len(data.get('datasets', []))))
    if data.get('datasets'):
        for ds in data['datasets']:
            print('  - ' + ds['label'] + ': ' + str(len(ds['data'])) + ' data points, color: ' + ds['borderColor'])
