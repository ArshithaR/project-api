# Quick Test Guide - Multi-API Charts

## Quick Start (5 minutes)

### Step 1: Start the Application
```bash
cd c:\Users\Rakshitha R\OneDrive\Desktop\api-monitor-project
python app.py
```
Then open: http://localhost:5000

### Step 2: Register or Login
- Create account or login with existing credentials

### Step 3: Add Test APIs (if not already present)
From Dashboard → Add API:

**API 1: GitHub**
- Name: `GitHub`
- URL: `https://api.github.com`
- Interval: 60 seconds

**API 2: Google**
- Name: `Google`
- URL: `https://www.google.com`
- Interval: 60 seconds

**API 3: Kubernetes**
- Name: `Kubernetes`
- URL: `https://kubernetes.default.svc`
- Interval: 60 seconds

### Step 4: View Multi-API Charts
1. Click **📈 Analytics & Charts**
2. Toggle to **🔗 All APIs Combined**
3. Select Chart Type: **📈 Line Chart** (or Bar/Area)
4. Wait for chart to render

### What You Should See
A **single chart** with **3 colored lines**:
- **Red line**: GitHub API response times
- **Blue line**: Google API response times  
- **Yellow line**: Kubernetes API response times

All on the same canvas with shared timestamps!

## Testing Each Chart Type

### Line Chart
```
Select: 🔗 All APIs Combined
Chart Type: 📈 Line Chart
Result: 3 colored lines showing performance over time
```

### Area Chart
```
Select: 🔗 All APIs Combined
Chart Type: 📊 Area Chart
Result: 3 filled areas with semi-transparent colors
```

### Bar Chart
```
Select: 🔗 All APIs Combined
Chart Type: 📊 Bar Chart
Result: Grouped bars for each API, one set per time period
```

### Pie Chart
```
Select: 🔗 All APIs Combined
Chart Type: 🥧 Pie Chart
Result: Per-API request count breakdown
```

## Testing Individual API View (Backwards Compatibility)

1. Toggle back to **📌 Individual API**
2. Click on **GitHub**
3. Select **📈 Line Chart**
4. Should see single line (not multi-series)
5. Should see status distribution chart below

## Data Verification

### Check Backend Data Structure
Run the test:
```bash
python test_data_structure.py
```

Expected output:
- 3 APIs in database
- 72 total logs (24 per API)
- Multi-series datasets with matching data points
- All JSON serializable

### Check Routes in Python Shell
```python
from app import create_app, db
from app.models import API, APILog

app = create_app()

with app.app_context():
    # Check APIs
    apis = API.query.all()
    print(f"Total APIs: {len(apis)}")
    for api in apis:
        print(f"  - {api.name}: {len(api.logs)} logs")
    
    # Sample output:
    # Total APIs: 3
    #   - GitHub: 24 logs
    #   - Google: 48 logs
    #   - Kubernetes: 36 logs
```

## Browser Console Debugging (F12 Developer Tools)

### View Raw API Response
1. Open Browser DevTools (F12)
2. Go to **Network** tab
3. Refresh page while in "All APIs Combined" mode
4. Find request to `/api/chart-data/all`
5. Click it and view **Response** tab

Should see JSON like:
```json
{
  "labels": ["14:00", "14:15", "14:30", ...],
  "datasets": [
    {
      "label": "GitHub",
      "data": [282, 290, 285, ...],
      "borderColor": "#FF6384"
    },
    {
      "label": "Google",
      "data": [465, 470, 468, ...],
      "borderColor": "#36A2EB"
    },
    {
      "label": "Kubernetes",
      "data": [195, 198, 192, ...],
      "borderColor": "#FFCE56"
    }
  ]
}
```

### Check Console for Errors
1. Open DevTools (F12)
2. Go to **Console** tab
3. Expand any errors
4. Look for JavaScript errors related to chart rendering

## Expected Behavior Summary

| Feature | Expected Result |
|---------|-----------------|
| Individual API + Line Chart | Single colored line with status pie chart |
| All APIs Combined + Line Chart | 3 colored lines on one chart |
| All APIs Combined + Bar Chart | Grouped bars for each API |
| All APIs Combined + Area Chart | Filled areas for each API |
| All APIs Combined + Pie Chart | Per-API proportion pie chart |
| Metrics Display (Individual) | Single API stats |
| Metrics Display (Combined) | Aggregated + per-API breakdown |
| Time Range Switching | Chart updates smoothly |

## Troubleshooting

### Chart Not Showing
1. Check Browser Console (F12) for JS errors
2. Check Network tab for failed `/api/chart-data/all` request
3. Verify databases has APIs: Run `python test_data_structure.py`

### Only One Line Showing
1. Make sure you're in "All APIs Combined" mode
2. Make sure you have 2+ APIs created
3. Check that each API has logs (wait 60 seconds)

### Wrong Response Times
1. Response times vary naturally based on actual API calls
2. First 60 seconds after adding API: no logs yet
3. Check latest logs: Dashboard → View Logs

### Colors Not Showing
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh page (Ctrl+Shift+R)
3. Check that chartType matches dataset colors

## Success Indicators

✓ Multi-series chart renders without errors
✓ Each API has different color
✓ All lines/bars show different values
✓ Timeline is synchronized across APIs
✓ Switching chart types works
✓ Switching between Individual/All modes works
✓ Analytics page loads quickly (<2 seconds)

## Performance Notes

- **Typical load time**: < 1 second
- **Chart render time**: < 500ms after data loads
- **Database query**: Uses indexes for fast filtering
- **Data points per chart**: Up to 168 (7 days × 24 hours)
- **Max APIs displayed**: 6 (with distinct colors)

---

**Ready to test?** Start the app and try "All APIs Combined" mode!
