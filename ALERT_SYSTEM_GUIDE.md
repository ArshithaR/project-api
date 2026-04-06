# 🔔 Alert System Implementation - Complete Guide

## ✅ What's Been Implemented

### Backend Components
1. **Alert Database Model** (`app/models.py`)
   - Stores alerts with type, severity, message, timestamps
   - Links to APIs with automatic relationship
   - `to_dict()` method for JSON serialization

2. **Alert Generation Logic** (`app/routes.py`)
   - `generate_alerts_for_api(api)` function detects three alert types
   - Alert hierarchy: Offline (critical) → Error → Slow (warning)
   - Automatic resolution when conditions clear

3. **API Endpoints** (`app/routes.py`)
   - `GET /api/alerts` - Fetch active alerts for current user
   - `POST /api/alerts/<alert_id>/resolve` - Manually resolve alerts

4. **Monitoring Integration** (`app/monitor.py`)
   - Alerts are automatically generated after each API check
   - Database updates with every monitoring cycle

### Frontend Components
1. **Alerts Page** (`templates/alerts.html`)
   - Real-time alert display
   - Color-coded severity badges
   - Manual resolve buttons
   - Auto-refresh every 30 seconds

## 🚀 Testing the Alert System

### Step 1: Start the Application
```bash
cd c:\Users\Rakshitha\ R\OneDrive\Desktop\api-monitor-project
python app.py
```

The app will start at: `http://127.0.0.1:5000`

### Step 2: Create Demo APIs

#### API 1: Offline Alert (OFFLINE - Red)
1. Go to Dashboard
2. Click "Add API"
3. Name: `Non-existent API`
4. URL: `https://this-does-not-exist-12345.com`
5. Check Interval: `30`
6. Threshold: `1000ms` (default is fine)
7. Save
8. Wait ~60 seconds for monitoring to run
9. Go to Alerts page → You should see a **RED flashing badge** saying "OFFLINE"

#### API 2: Error Alert (ERROR - Red)
1. Click "Add API"
2. Name: `HTTPBin Error`
3. URL: `https://httpbin.org/status/500`
4. Check Interval: `30`
5. Save
6. Wait ~60 seconds
7. Go to Alerts page → You should see a **RED badge** saying "ERROR 500"

#### API 3: Slow Alert (SLOW - Orange/Yellow)
1. Click "Add API"
2. Name: `HTTPBin Delay`
3. URL: `https://httpbin.org/delay/3`
4. Check Interval: `30`
5. **Threshold: `1000` (2000ms works too)**
6. Save
7. Wait ~60 seconds
8. Go to Alerts page → You should see an **ORANGE badge** saying "SLOW"

### Step 3: Test Alert Features on Alerts Page
- **Color Coding**: Notice RED badges (offline/error), ORANGE badge (slow)
- **Flashing**: OFFLINE alert should have pulse animation
- **Details**: Each alert shows API name, message, timestamp, status code (for errors), response time (for slow)
- **Manual Resolve**: Click "Resolve" button to dismiss an alert
- **Auto-Refresh**: Page auto-refreshes every 30 seconds

### Step 4: Test Alert Resolution
1. Delete the non-existent API or replace its URL with a working one
2. Wait ~30-60 seconds for monitoring to run
3. Go to Alerts page
4. The offline alert should disappear (auto-resolved)
5. Or manually click "Resolve" button

## 📊 Alert Types Reference

| Alert Type | Trigger | Color | Animation | Severity |
|-----------|---------|-------|-----------|----------|
| **OFFLINE** | Connection refused, DNS failure, timeout | Red | 🔴 Flashing | Critical |
| **ERROR** | HTTP status code ≠ 200 | Red | Solid | Error |
| **SLOW** | Response time > threshold | Orange | Solid | Warning |

## 🔧 Configuration

### Default Threshold
- Default latency threshold: **1000ms** (1 second)
- For delay APIs, use higher threshold to avoid constant warnings

### Alert Detection Criteria
- **Offline**: Error messages containing: "Connection", "DNS", "refused", "Name or service not known"
- **Error**: Any HTTP status code except 200
- **Slow**: Response time exceeds configured threshold

## 📝 Demo URLs Perfect For Testing

1. **Offline** → `https://this-does-not-exist-12345.com` (non-existent domain)
2. **Error (500)** → `https://httpbin.org/status/500` (server error)
3. **Error (404)** → `https://httpbin.org/status/404` (not found)
4. **Slow** → `https://httpbin.org/delay/3` (3 second delay)
5. **Success** → `https://httpbin.org/status/200` (always works)

## 🎯 Expected Behavior

### First Alert Creation
- Takes ~60 seconds after API check completes
- Monitor runs every 30 seconds, alert checks each iteration
- Alerts page shows all active alerts automatically

### Alert Auto-Resolution
- When API recovers (returns 200), alert automatically resolves
- `resolved_at` timestamp updates
- Alert disappears from active list

### Alert Hierarchy
- If API goes OFFLINE → all other alerts resolve
- If API returns ERROR → OFFLINE alert resolves
- If API is SLOW → ERROR and OFFLINE alerts resolve (if any)

## 📱 API Response Examples

### GET /api/alerts
```json
{
  "alerts": [
    {
      "id": 1,
      "api_id": 1,
      "api_name": "Non-existent API",
      "alert_type": "offline",
      "severity": "critical",
      "message": "API \"Non-existent API\" is OFFLINE - Connection failed",
      "status_code": null,
      "response_time": null,
      "is_active": true,
      "created_at": "2026-04-04T15:35:56.466540",
      "resolved_at": null
    },
    {
      "id": 2,
      "api_id": 2,
      "api_name": "HTTPBin Error",
      "alert_type": "error",
      "severity": "error",
      "message": "API \"HTTPBin Error\" returned error status: 500",
      "status_code": 500,
      "response_time": null,
      "is_active": true,
      "created_at": "2026-04-04T15:35:56.466540",
      "resolved_at": null
    }
  ],
  "count": 2
}
```

## 🧪 Testing Checklist

- [ ] App starts without errors
- [ ] Can create test APIs
- [ ] Dashboard shows APIs
- [ ] Monitoring runs and creates APILogs
- [ ] OFFLINE alert appears for non-existent domain
- [ ] ERROR alert appears for status 500
- [ ] SLOW alert appears when response time exceeds threshold
- [ ] Alerts page shows all active alerts
- [ ] Red badges appear for offline/error
- [ ] Orange badge appears for slow
- [ ] Flashing animation works on offline alert
- [ ] Manual resolve button works
- [ ] Alert auto-resolves when API recovers (200)
- [ ] Page auto-refreshes every 30 seconds
- [ ] Timestamp shows correct alert creation time

## 🐛 Troubleshooting

### Alerts Not Appearing
1. Ensure API check interval is set to 30 seconds or less
2. Wait at least 60 seconds after creating API
3. Check browser console for JavaScript errors
4. Verify `/api/alerts` endpoint returns data (open in DevTools)

### Alerts Not Resolving
1. Check if API actually returns 200 status code
2. Verify threshold_latency value (for SLOW alerts)
3. Check database for alert records

### Page Not Auto-Refreshing
1. Check JavaScript console for errors
2. Verify CORS is not blocking requests
3. Hard-refresh page (Ctrl+F5)

## 📚 Files Modified

- ✅ `app/models.py` - Added Alert model
- ✅ `app/routes.py` - Added alert endpoints and logic
- ✅ `app/monitor.py` - Integrated alert generation
- ✅ `templates/alerts.html` - Complete redesign with real-time alerts
- ✅ Database automatically extends with Alert table on startup

## ✨ Next Steps (Optional Enhancements)

1. **Email Notifications** - Send email when critical alerts trigger
2. **Slack Integration** - Post alerts to Slack channel
3. **Alert History** - Show resolved alerts with resolution time
4. **Alert Settings** - Allow users to configure alert thresholds per API
5. **WebSocket Updates** - Real-time push instead of polling
6. **Alert Rules** - Custom alert conditions and triggers

---

### 🎉 Alert System is Ready to Use!
Start the app, create test APIs, and watch the alerts appear in real-time.
