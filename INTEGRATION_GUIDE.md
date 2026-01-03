# OCC Integration Guide (Administrator)

This guide is for **system administrators** setting up data source connections.

For end-user documentation, see **README.md**.

---

## Overview

The fetch_data.py script uses **environment variables** for configuration. This keeps credentials out of the code.

```
┌─────────────────────────────────────────────────────────────┐
│                    Environment Variables                     │
│                                                             │
│   SNOW_ENABLED=true                                         │
│   SNOW_URL=https://your-instance.service-now.com/...       │
│   SNOW_USER=your_username                                   │
│   SNOW_PASS=your_password                                   │
│   ...                                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      fetch_data.py                          │
│                                                             │
│   - Reads environment variables                             │
│   - Fetches data from each enabled source                   │
│   - Retries on failure (3 attempts with backoff)           │
│   - Writes to data.json with fetchStatus                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values

3. Source the environment and run:
   ```bash
   source .env && python3 fetch_data.py
   ```

4. Set up cron (see Cron Setup section below)

---

## 1. ServiceNow

### Find Your URL

**Option A: REST API (Recommended)**
```
https://YOUR-INSTANCE.service-now.com/api/now/table/incident
```

**Option B: Report URL**
If you have a saved report, get its URL:
1. Open your ServiceNow report
2. Copy the URL from browser
3. Check if report can export as JSON/CSV

### Configuration

```python
'servicenow': {
    'enabled': True,
    'url': 'https://YOUR-INSTANCE.service-now.com/api/now/table/incident',
    'username': 'your_api_user',
    'password': 'your_api_password',
},
```

### Implement the Fetcher

Edit the `fetch_servicenow()` function in `fetch_data.py`:

```python
def fetch_servicenow():
    if not CONFIG['servicenow']['enabled']:
        return None

    cfg = CONFIG['servicenow']

    # Fetch incidents by priority
    url = f"{cfg['url']}?sysparm_query=active=true&sysparm_fields=priority,state"
    response = fetch_url(url, cfg['username'], cfg['password'])
    data = json.loads(response)

    # Count by priority
    incidents = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'total': 0}
    for record in data.get('result', []):
        priority = record.get('priority', '4')
        if priority == '1':
            incidents['critical'] += 1
        elif priority == '2':
            incidents['high'] += 1
        elif priority == '3':
            incidents['medium'] += 1
        else:
            incidents['low'] += 1
        incidents['total'] += 1

    return {
        'incidents': incidents,
        'requests': {'open': 0, 'pending': 0, 'completed_today': 0},  # Add similar logic
        'changes': {'scheduled': 0, 'in_progress': 0, 'pending_approval': 0},
        'slt': {'incident_response': 95.0, 'incident_resolution': 90.0, 'request_fulfillment': 92.0}
    }
```

### Test It

```bash
# Test API access
curl -u 'username:password' \
  'https://YOUR-INSTANCE.service-now.com/api/now/table/incident?sysparm_limit=1'
```

---

## 2. BUMS (Unix Monitoring System)

### Find Your URL

1. Open the BUMS webpage you normally use
2. Copy the URL from browser
3. Check the page source (View Source) to understand the data format

### Configuration

```python
'bums': {
    'enabled': True,
    'url': 'http://your-bums-server/status',
    'username': 'your_username',
    'password': 'your_password',
},
```

### Implement the Fetcher

The implementation depends on your BUMS output format:

**If BUMS returns JSON:**
```python
def fetch_bums():
    if not CONFIG['bums']['enabled']:
        return None

    cfg = CONFIG['bums']
    response = fetch_url(cfg['url'], cfg['username'], cfg['password'])
    data = json.loads(response)

    # Adjust parsing based on your JSON structure
    servers_up = sum(1 for s in data['servers'] if s['status'] == 'up')
    servers_down = sum(1 for s in data['servers'] if s['status'] == 'down')

    down_list = [
        {'name': s['hostname'], 'since': s['last_seen']}
        for s in data['servers'] if s['status'] == 'down'
    ]

    return {
        'servers': {
            'total': len(data['servers']),
            'up': servers_up,
            'down': servers_down,
            'down_list': down_list
        },
        'filesystem': {
            'alerts': 0,
            'alert_list': []
        }
    }
```

**If BUMS returns HTML (needs parsing):**
```python
import re

def fetch_bums():
    if not CONFIG['bums']['enabled']:
        return None

    cfg = CONFIG['bums']
    html = fetch_url(cfg['url'], cfg['username'], cfg['password'])

    # Example: Parse HTML table
    # Adjust regex/parsing based on actual HTML structure

    # Find server rows (example pattern)
    server_pattern = r'<tr.*?<td>(srv-[^<]+)</td>.*?<td>(UP|DOWN)</td>'
    matches = re.findall(server_pattern, html, re.DOTALL)

    servers_up = sum(1 for _, status in matches if status == 'UP')
    servers_down = sum(1 for _, status in matches if status == 'DOWN')

    down_list = [
        {'name': name, 'since': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
        for name, status in matches if status == 'DOWN'
    ]

    return {
        'servers': {
            'total': len(matches),
            'up': servers_up,
            'down': servers_down,
            'down_list': down_list
        },
        'filesystem': {
            'alerts': 0,
            'alert_list': []
        }
    }
```

### Test It

```bash
# Test with curl (add auth if needed)
curl -u 'username:password' 'http://your-bums-server/status'

# Save output to analyze
curl -u 'username:password' 'http://your-bums-server/status' > bums_sample.html
```

---

## 3. SolarWinds

### Find Your URL

**Option A: SolarWinds Orion API**
```
https://your-solarwinds:17778/SolarWinds/InformationService/v3/Json/Query
```

**Option B: Existing Dashboard URL**
If you only have dashboard access, check if there's an export or API endpoint.

### Configuration

```python
'solarwinds': {
    'enabled': True,
    'url': 'https://your-solarwinds:17778/SolarWinds/InformationService/v3/Json/Query',
    'username': 'your_username',
    'password': 'your_password',
},
```

### Implement the Fetcher

```python
def fetch_solarwinds():
    if not CONFIG['solarwinds']['enabled']:
        return None

    cfg = CONFIG['solarwinds']

    # SolarWinds SWQL query for active alerts
    query = "SELECT AlertActive.AlertObjectID, AlertActive.ObjectName, AlertActive.Severity FROM Orion.AlertActive"

    # POST request with query
    import urllib.request
    import base64

    request_data = json.dumps({'query': query}).encode('utf-8')

    req = urllib.request.Request(cfg['url'], data=request_data)
    req.add_header('Content-Type', 'application/json')
    credentials = base64.b64encode(f"{cfg['username']}:{cfg['password']}".encode()).decode()
    req.add_header('Authorization', f'Basic {credentials}')

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))

    # Parse alerts
    cpu_critical = 0
    cpu_warning = 0
    cpu_alerts = []

    for alert in data.get('results', []):
        # Adjust based on your alert structure
        if 'CPU' in alert.get('ObjectName', ''):
            severity = 'critical' if alert.get('Severity', 0) >= 2 else 'warning'
            if severity == 'critical':
                cpu_critical += 1
            else:
                cpu_warning += 1
            cpu_alerts.append({
                'node': alert['ObjectName'],
                'cpu': 95,  # Get actual value from alert details
                'severity': severity
            })

    return {
        'cpu_alerts': {
            'critical': cpu_critical,
            'warning': cpu_warning,
            'alert_list': cpu_alerts[:10]  # Limit to 10
        },
        'memory_alerts': {
            'critical': 0,
            'warning': 0,
            'alert_list': []
        }
    }
```

### Test It

```bash
# Test SolarWinds API
curl -k -u 'username:password' \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"query": "SELECT TOP 5 NodeID, Caption FROM Orion.Nodes"}' \
  'https://your-solarwinds:17778/SolarWinds/InformationService/v3/Json/Query'
```

---

## 4. AAP (Ansible Automation Platform)

### Find Your URL

AAP/Ansible Tower API:
```
https://your-aap-server/api/v2/jobs/
```

Or if you have a webpage showing job results, use that URL.

### Configuration

```python
'aap': {
    'enabled': True,
    'url': 'https://your-aap-server/api/v2/jobs/',
    'token': 'your_api_token',  # or use username/password
},
```

### Implement the Fetcher

**Using AAP API:**
```python
def fetch_aap():
    if not CONFIG['aap']['enabled']:
        return None

    cfg = CONFIG['aap']

    # Get jobs from last 24 hours
    from datetime import datetime, timedelta
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"{cfg['url']}?created__gt={yesterday}&order_by=-created"

    # Add token auth
    import urllib.request
    req = urllib.request.Request(url)
    req.add_header('Authorization', f"Bearer {cfg['token']}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))

    jobs = data.get('results', [])
    passed = sum(1 for j in jobs if j['status'] == 'successful')
    failed = sum(1 for j in jobs if j['status'] == 'failed')

    failed_list = [
        {'name': j['name'], 'error': j.get('result_stdout', 'Unknown error')[:100]}
        for j in jobs if j['status'] == 'failed'
    ][:5]

    return {
        'last_run': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'jobs': {
            'total': len(jobs),
            'passed': passed,
            'failed': failed,
            'failed_list': failed_list
        }
    }
```

**Using AAP webpage (HTML parsing):**
```python
def fetch_aap():
    if not CONFIG['aap']['enabled']:
        return None

    cfg = CONFIG['aap']
    html = fetch_url(cfg['url'], cfg.get('username'), cfg.get('password'))

    # Parse based on your webpage structure
    # Example: count PASS/FAIL keywords
    import re

    passed = len(re.findall(r'\bPASS\b', html, re.IGNORECASE))
    failed = len(re.findall(r'\bFAIL\b', html, re.IGNORECASE))

    # Extract failed job names (adjust regex for your format)
    failed_pattern = r'FAIL.*?Job:\s*([^\n<]+)'
    failed_matches = re.findall(failed_pattern, html)

    failed_list = [{'name': name.strip(), 'error': 'Check AAP for details'} for name in failed_matches[:5]]

    return {
        'last_run': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'jobs': {
            'total': passed + failed,
            'passed': passed,
            'failed': failed,
            'failed_list': failed_list
        }
    }
```

### Test It

```bash
# Test AAP API
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  'https://your-aap-server/api/v2/jobs/?page_size=5'
```

---

## 5. Audit Report

### Find Your URL

The audit report webpage from your AAP job output.

### Configuration

```python
'audit': {
    'enabled': True,
    'url': 'http://your-audit-server/report',
    'username': 'your_username',
    'password': 'your_password',
},
```

### Implement the Fetcher

```python
def fetch_audit():
    if not CONFIG['audit']['enabled']:
        return None

    cfg = CONFIG['audit']
    html = fetch_url(cfg['url'], cfg.get('username'), cfg.get('password'))

    # Parse based on your audit report format
    # Example: Look for config file changes
    import re

    # Pattern example: "srv-web-001: /etc/ssh/sshd_config modified"
    change_pattern = r'(srv-[\w-]+):\s*(/[\w/\.]+)\s+(modified|changed|added|removed)'
    matches = re.findall(change_pattern, html, re.IGNORECASE)

    alerts = [
        {
            'server': server,
            'file': filepath,
            'change': action.capitalize(),
            'time': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        for server, filepath, action in matches
    ][:10]

    return {
        'last_scan': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'config_changes': {
            'total': len(alerts),
            'alerts': alerts
        }
    }
```

### Test It

```bash
# Download sample output to analyze
curl -u 'username:password' 'http://your-audit-server/report' > audit_sample.html

# Check the format
head -100 audit_sample.html
```

---

## 6. Tenable

### Environment Variables

```bash
export TENABLE_ENABLED=true
export TENABLE_URL=https://your-tenable-server/rest/analysis
export TENABLE_ACCESS_KEY=your_access_key
export TENABLE_SECRET_KEY=your_secret_key
```

### Getting API Keys

1. Log into Tenable.sc or Tenable.io
2. Go to Settings > API Keys
3. Generate new Access Key and Secret Key
4. Store them securely in your `.env` file

### Implementation Notes

The fetch_tenable() function uses the Tenable REST API to fetch:
- Vulnerability counts by severity (Critical, High, Medium, Low)
- Scan failure information
- Compliance percentages

Adjust the parsing logic based on your Tenable version (Tenable.sc vs Tenable.io).

### Test It

```bash
# Test Tenable API
curl -k -H "X-ApiKeys: accessKey=YOUR_KEY;secretKey=YOUR_SECRET" \
  'https://your-tenable-server/rest/analysis'
```

---

## Setting Up Cron

Once all sources are configured and tested:

### Option 1: Using a wrapper script (Recommended)

Create a wrapper script `run_fetch.sh`:
```bash
#!/bin/bash
cd /path/to/OCC
source .env
python3 fetch_data.py >> fetch.log 2>&1
```

Make it executable and add to cron:
```bash
chmod +x /path/to/OCC/run_fetch.sh
crontab -e

# Add this line (runs every 5 minutes)
*/5 * * * * /path/to/OCC/run_fetch.sh
```

### Option 2: Inline environment variables

```bash
crontab -e

# Add this line with all env vars inline
*/5 * * * * SNOW_ENABLED=true SNOW_URL=... /path/to/OCC/fetch_data.py >> /path/to/OCC/fetch.log 2>&1
```

---

## Troubleshooting

### Check Connectivity

```bash
# Test each URL
curl -v 'http://your-url'

# With authentication
curl -u 'user:pass' 'http://your-url'

# Ignore SSL errors (if self-signed cert)
curl -k 'https://your-url'
```

### Debug the Script

```bash
# Run manually and see output
python3 /path/to/fetch_data.py

# Check the output file
cat /path/to/OCC/data.json | python3 -m json.tool
```

### Common Issues

| Issue | Solution |
|-------|----------|
| SSL certificate error | Set `verify_mode = ssl.CERT_NONE` in fetch_url() |
| Authentication fails | Check username/password, try in browser first |
| Timeout | Increase timeout in fetch_url() |
| Parsing fails | Save HTML output, analyze structure, adjust regex |
| Permission denied | Check file permissions, run as correct user |

---

## Quick Checklist

### Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Edit `.env` with your credentials

### Data Sources
- [ ] ServiceNow - URL and credentials configured
- [ ] BUMS - URL and credentials configured
- [ ] SolarWinds - URL and credentials configured
- [ ] AAP - URL and API token configured
- [ ] Audit Report - URL and credentials configured
- [ ] Tenable - URL and API keys configured

### Testing
- [ ] Test each source with curl commands
- [ ] Run `source .env && python3 fetch_data.py`
- [ ] Verify data.json is updated
- [ ] Check fetchStatus shows "ok" for each source

### Deployment
- [ ] Set up cron job (see Cron Setup section)
- [ ] Start web server: `./start.sh`
- [ ] Verify dashboard loads at http://localhost:8080
- [ ] Confirm auto-refresh is working

---

## Need Help?

1. Save sample output from each source:
   ```bash
   curl -u 'user:pass' 'http://source-url' > sample_output.html
   ```

2. Share the sample format (redact sensitive data)

3. I can help write the specific parsing logic for your format
