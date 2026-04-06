# Alert API Setup & Testing Guide

## Quick Setup (5 minutes)

### Step 1: Initialize the Database

The Alert model needs to be created in the database. Run this Python script:

```bash
cd c:\Users\Rakshitha R\OneDrive\Desktop\api-monitor-project
python
```

Then in the Python shell:

```python
from app import create_app, db

# Create Flask app context
app = create_app()

# Initialize database tables
with app.app_context():
    db.create_all()
    print("✓ Database tables created successfully!")
```

This creates the `alert` table with all necessary columns.

**Output you'll see:**
```
✓ Database tables created successfully!
```

### Step 2: Verify Installation

Check that the Alert model was imported correctly:

```python
from app.models import Alert
print("✓ Alert model imported successfully!")
exit()
```

### Step 3: Start the Application

```bash
python app.py
```

Output should show:
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

## Testing the API

### Option A: Run the Demo Script

```bash
# In a new terminal
python demo_alerts_api.py
```

This will:
1. Login automatically
2. Create test alerts
3. Demonstrate all API operations
4. Show filtering and statistics
5. Resolve alerts

**Note:** You need a registered user account first. Register at http://localhost:5000/auth/register

### Option B: Manual Testing with cURL

#### 1. Login and get session cookie

```bash
curl -c cookies.txt -X POST http://localhost:5000/auth/login \
  -d "username=YOUR_USERNAME&password=YOUR_PASSWORD"
```

#### 2. Create an alert

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "api_id": 1,
    "alert_type": "latency",
    "message": "API response too slow",
    "severity": "high"
  }'
```

#### 3. Get all alerts

```bash
curl -b cookies.txt http://localhost:5000/api/alerts
```

#### 4. Get statistics

```bash
curl -b cookies.txt http://localhost:5000/api/alerts/stats
```

### Option C: Python Requests

```python
import requests
import json

# Create session
session = requests.Session()

# Login
session.post('http://localhost:5000/auth/login', data={
    'username': 'YOUR_USERNAME',
    'password': 'YOUR_PASSWORD'
})

# Create alert
response = session.post('http://localhost:5000/api/alerts', json={
    'api_id': 1,
    'alert_type': 'latency',
    'message': 'Demo alert',
    'severity': 'high'
})

# View response
print(json.dumps(response.json(), indent=2))

# Get all alerts
response = session.get('http://localhost:5000/api/alerts')
print(json.dumps(response.json(), indent=2))
```

## Complete Workflow Example

### For Your Teacher Presentation

#### 1. Setup Phase
```bash
# Terminal 1: Start Flask app
python app.py

# Terminal 2: Initialize database (one time only)
python -c "from app import create_app, db; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all(); print('Database ready!')"
```

#### 2. Demo Phase
```bash
# Run the automated demo
python demo_alerts_api.py
```

#### 3. Manual Demo Phase
```bash
# Create a test alert
curl -b cookies.txt -X POST http://localhost:5000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{"api_id": 1, "alert_type": "down", "message": "API is down", "severity": "critical"}'

# Show all active alerts
curl -b cookies.txt "http://localhost:5000/api/alerts?status=active"

# Show high severity alerts
curl -b cookies.txt "http://localhost:5000/api/alerts?severity=high"

# Get statistics
curl -b cookies.txt http://localhost:5000/api/alerts/stats
```

## What Each Endpoint Does

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/alerts` | Get all alerts with optional filtering |
| POST | `/api/alerts` | Create a new alert |
| GET | `/api/alerts/<id>` | Get specific alert details |
| PUT | `/api/alerts/<id>/resolve` | Mark alert as resolved |
| DELETE | `/api/alerts/<id>` | Delete an alert |
| GET | `/api/alerts/stats` | Get alert statistics summary |

## Query Parameters for Filtering

```
GET /api/alerts?status=active           # Only active alerts
GET /api/alerts?severity=high           # Only high severity
GET /api/alerts?api_id=1                # Alerts for specific API
GET /api/alerts?status=active&severity=critical  # Combine filters
```

## Sample Response

### GET /api/alerts

```json
{
  "total": 2,
  "alerts": [
    {
      "id": 1,
      "api_id": 1,
      "api_name": "Google API",
      "alert_type": "latency",
      "message": "API response time exceeded threshold",
      "status": "active",
      "severity": "high",
      "created_at": "2024-01-15 10:30:45",
      "resolved_at": null
    },
    {
      "id": 2,
      "api_id": 2,
      "api_name": "GitHub API",
      "alert_type": "down",
      "message": "API returned 503 status",
      "status": "resolved",
      "severity": "critical",
      "created_at": "2024-01-15 09:15:20",
      "resolved_at": "2024-01-15 09:30:55"
    }
  ]
}
```

## Troubleshooting

### Issue: "No session cookie"
**Solution:** Login first using /auth/login endpoint

### Issue: "Alert not found (404)"
**Solution:** Make sure alert ID is correct and belongs to your user

### Issue: "Unauthorized (403)"
**Solution:** Make sure you own the API that the alert is for. Alerts are user-scoped.

### Issue: "Database error"
**Solution:** Run `db.create_all()` first to initialize tables

### Issue: Demo script fails to connect
**Solution:** 
1. Make sure Flask app is running on http://localhost:5000
2. Make sure you've registered a user account
3. Update USERNAME and PASSWORD in demo script

## Advanced: Add Automatic Alert Generation

To automatically generate alerts when APIs fail, add this to your monitoring logic:

```python
from app.models import Alert, db
from datetime import datetime

def check_api_health():
    # ... existing monitoring code ...
    
    if response_time > 1000:
        # Create latency alert
        alert = Alert(
            api_id=api_id,
            alert_type='latency',
            message=f'Response time {response_time}ms exceeds threshold',
            severity='high' if response_time > 2000 else 'medium'
        )
        db.session.add(alert)
        db.session.commit()
    
    if status_code != 200:
        # Create down/error alert
        alert = Alert(
            api_id=api_id,
            alert_type='down',
            message=f'API returned status {status_code}',
            severity='critical'
        )
        db.session.add(alert)
        db.session.commit()
```

## Demo Commands for Your Teacher

Copy and paste these commands to show your teacher:

```bash
# Show all active alerts
curl http://localhost:5000/api/alerts?status=active

# Show critical severity alerts
curl http://localhost:5000/api/alerts?severity=critical

# Show alert statistics (total, by type, by severity)
curl http://localhost:5000/api/alerts/stats

# Show only latency type alerts
curl 'http://localhost:5000/api/alerts?alert_type=latency'

# Show last 5 resolved alerts
curl 'http://localhost:5000/api/alerts?status=resolved'
```

## Next Steps

1. ✅ Initialize database (run db.create_all())
2. ✅ Run demo_alerts_api.py to see it working
3. ⏳ Create `templates/alerts.html` for frontend display
4. ⏳ Integrate alert triggering into monitoring logic
5. ⏳ Create Grafana dashboard for alerts visualization

---

**Questions?** Check [ALERT_API_DOCUMENTATION.md](ALERT_API_DOCUMENTATION.md) for complete reference.
