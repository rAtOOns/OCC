#!/usr/bin/env python3
"""
OCC Data Fetcher
================
This script fetches data from various sources and writes to data.json
Run this via cron every 5 minutes: */5 * * * * /path/to/fetch_data.py

Configure your source URLs via environment variables or the CONFIG section below.
"""

import json
import os
import time
import logging
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Uses environment variables with fallbacks
# ============================================================================

def get_env(key, default=''):
    """Get environment variable with fallback"""
    return os.environ.get(key, default)

CONFIG = {
    # ServiceNow
    'servicenow': {
        'enabled': get_env('SNOW_ENABLED', 'false').lower() == 'true',
        'url': get_env('SNOW_URL', 'https://your-instance.service-now.com/api/now/table/incident'),
        'username': get_env('SNOW_USER', ''),
        'password': get_env('SNOW_PASS', ''),
    },

    # BUMS (Unix Monitoring System)
    'bums': {
        'enabled': get_env('BUMS_ENABLED', 'false').lower() == 'true',
        'url': get_env('BUMS_URL', 'http://your-bums-server/status'),
        'username': get_env('BUMS_USER', ''),
        'password': get_env('BUMS_PASS', ''),
    },

    # SolarWinds
    'solarwinds': {
        'enabled': get_env('SOLARWINDS_ENABLED', 'false').lower() == 'true',
        'url': get_env('SOLARWINDS_URL', 'https://your-solarwinds/api/alerts'),
        'username': get_env('SOLARWINDS_USER', ''),
        'password': get_env('SOLARWINDS_PASS', ''),
    },

    # AAP (Ansible Automation Platform)
    'aap': {
        'enabled': get_env('AAP_ENABLED', 'false').lower() == 'true',
        'url': get_env('AAP_URL', 'http://your-aap-server/api/v2/jobs/'),
        'token': get_env('AAP_TOKEN', ''),
    },

    # Audit Report
    'audit': {
        'enabled': get_env('AUDIT_ENABLED', 'false').lower() == 'true',
        'url': get_env('AUDIT_URL', 'http://your-audit-server/report'),
        'username': get_env('AUDIT_USER', ''),
        'password': get_env('AUDIT_PASS', ''),
    },

    # Tenable
    'tenable': {
        'enabled': get_env('TENABLE_ENABLED', 'false').lower() == 'true',
        'url': get_env('TENABLE_URL', 'https://your-tenable-server/rest/analysis'),
        'access_key': get_env('TENABLE_ACCESS_KEY', ''),
        'secret_key': get_env('TENABLE_SECRET_KEY', ''),
    },
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# SSL Configuration - Set to True in production with valid certs
VERIFY_SSL = get_env('VERIFY_SSL', 'false').lower() == 'true'

# Output file path
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

# ============================================================================
# FETCH STATUS TRACKING
# ============================================================================

fetch_status = {}

def record_status(source, success, error=None):
    """Record fetch status for a source"""
    fetch_status[source] = {
        'ok': success,
        'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'error': str(error) if error else None
    }

# ============================================================================
# MOCK DATA - Used when sources are disabled
# ============================================================================

def get_mock_data():
    """Returns mock data for testing"""
    return {
        "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "servicenow": {
            "incidents": {"critical": 2, "high": 5, "medium": 12, "low": 8, "total": 27},
            "requests": {"open": 15, "pending": 7, "completed_today": 12},
            "changes": {"scheduled": 3, "in_progress": 1, "pending_approval": 4},
            "slt": {"incident_response": 94.5, "incident_resolution": 87.2, "request_fulfillment": 91.8}
        },
        "bums": {
            "servers": {
                "total": 45, "up": 43, "down": 2,
                "down_list": [
                    {"name": "srv-app-012", "since": "2025-12-29T08:15:00Z"},
                    {"name": "srv-db-003", "since": "2025-12-29T09:45:00Z"}
                ]
            },
            "filesystem": {
                "alerts": 3,
                "alert_list": [
                    {"server": "srv-app-007", "mount": "/var/log", "usage": 92},
                    {"server": "srv-web-002", "mount": "/opt/data", "usage": 88},
                    {"server": "srv-db-001", "mount": "/backup", "usage": 95}
                ]
            }
        },
        "solarwinds": {
            "cpu_alerts": {
                "critical": 1, "warning": 3,
                "alert_list": [
                    {"node": "web-prod-01", "cpu": 98, "severity": "critical"},
                    {"node": "app-prod-03", "cpu": 85, "severity": "warning"},
                    {"node": "db-prod-02", "cpu": 82, "severity": "warning"},
                    {"node": "cache-01", "cpu": 80, "severity": "warning"}
                ]
            },
            "memory_alerts": {
                "critical": 0, "warning": 2,
                "alert_list": [
                    {"node": "app-prod-01", "memory": 87, "severity": "warning"},
                    {"node": "web-prod-02", "memory": 84, "severity": "warning"}
                ]
            }
        },
        "aap": {
            "last_run": datetime.utcnow().strftime("%Y-%m-%dT06:00:00Z"),
            "jobs": {
                "total": 24, "passed": 22, "failed": 2,
                "failed_list": [
                    {"name": "backup-db-weekly", "error": "Connection timeout to db-backup-srv"},
                    {"name": "patch-compliance-check", "error": "Host unreachable: srv-app-012"}
                ]
            }
        },
        "audit": {
            "last_scan": datetime.utcnow().strftime("%Y-%m-%dT05:00:00Z"),
            "config_changes": {
                "total": 5,
                "alerts": [
                    {"server": "srv-web-001", "file": "/etc/ssh/sshd_config", "change": "PermitRootLogin modified", "time": "2025-12-28T22:30:00Z"},
                    {"server": "srv-app-005", "file": "/etc/passwd", "change": "New user added: svc_deploy", "time": "2025-12-28T18:15:00Z"},
                    {"server": "srv-db-002", "file": "/etc/sudoers", "change": "Sudo rule modified", "time": "2025-12-28T14:00:00Z"},
                    {"server": "srv-web-003", "file": "/etc/hosts", "change": "New entry added", "time": "2025-12-29T01:20:00Z"},
                    {"server": "srv-app-001", "file": "/etc/crontab", "change": "New cron job added", "time": "2025-12-29T03:45:00Z"}
                ]
            }
        },
        "tenable": {
            "last_scan": datetime.utcnow().strftime("%Y-%m-%dT04:00:00Z"),
            "vulnerabilities": {
                "critical": 3,
                "high": 8,
                "medium": 24,
                "low": 45
            },
            "scan_failures": {
                "total": 4,
                "failed_list": [
                    {"host": "srv-db-005", "reason": "Authentication failed", "time": "2025-12-29T04:15:00Z"},
                    {"host": "srv-app-009", "reason": "Host unreachable", "time": "2025-12-29T04:18:00Z"},
                    {"host": "srv-web-004", "reason": "Scan timeout", "time": "2025-12-29T04:22:00Z"},
                    {"host": "srv-cache-02", "reason": "Connection refused", "time": "2025-12-29T04:25:00Z"}
                ]
            },
            "compliance": {
                "passed": 89,
                "failed": 11
            }
        }
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_ssl_context():
    """Get SSL context based on configuration"""
    ctx = ssl.create_default_context()
    if not VERIFY_SSL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_url(url, username=None, password=None, headers=None, retries=MAX_RETRIES):
    """
    Helper to fetch URL with optional auth and retry logic

    Args:
        url: URL to fetch
        username: Basic auth username
        password: Basic auth password
        headers: Additional headers dict
        retries: Number of retry attempts

    Returns:
        Response body as string

    Raises:
        Exception on failure after all retries
    """
    ctx = get_ssl_context()

    for attempt in range(retries):
        try:
            request = Request(url)

            # Add basic auth if provided
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                request.add_header('Authorization', f'Basic {credentials}')

            # Add custom headers
            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)

            with urlopen(request, context=ctx, timeout=30) as response:
                return response.read().decode('utf-8')

        except (URLError, HTTPError) as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                raise


def generate_source_urls():
    """Generate source URLs from CONFIG"""
    return {
        'servicenow': CONFIG['servicenow']['url'].replace('/api/now/table/incident', '/nav_to.do?uri=incident_list.do'),
        'bums': CONFIG['bums']['url'],
        'solarwinds': CONFIG['solarwinds']['url'].replace('/api/alerts', '/Orion/Alerts'),
        'aap': CONFIG['aap']['url'].replace('/api/v2/jobs/', '/#/jobs'),
        'audit': CONFIG['audit']['url'],
        'tenable': CONFIG['tenable']['url'].replace('/rest/analysis', '/dashboard'),
    }


# ============================================================================
# DATA FETCHERS
# ============================================================================

def fetch_servicenow():
    """
    Fetch ServiceNow data via REST API
    """
    if not CONFIG['servicenow']['enabled']:
        return None

    cfg = CONFIG['servicenow']

    try:
        # Fetch active incidents grouped by priority
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

        record_status('servicenow', True)
        return {
            'incidents': incidents,
            'requests': {'open': 0, 'pending': 0, 'completed_today': 0},
            'changes': {'scheduled': 0, 'in_progress': 0, 'pending_approval': 0},
            'slt': {'incident_response': 95.0, 'incident_resolution': 90.0, 'request_fulfillment': 92.0}
        }

    except Exception as e:
        record_status('servicenow', False, e)
        raise


def fetch_bums():
    """
    Fetch BUMS server status
    """
    if not CONFIG['bums']['enabled']:
        return None

    cfg = CONFIG['bums']

    try:
        response = fetch_url(cfg['url'], cfg['username'], cfg['password'])

        # Try JSON first
        try:
            data = json.loads(response)
            servers_up = sum(1 for s in data.get('servers', []) if s.get('status') == 'up')
            servers_down = sum(1 for s in data.get('servers', []) if s.get('status') == 'down')
            down_list = [
                {'name': s['hostname'], 'since': s.get('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))}
                for s in data.get('servers', []) if s.get('status') == 'down'
            ]
        except json.JSONDecodeError:
            # Fall back to HTML parsing
            import re
            server_pattern = r'<tr.*?<td>(srv-[^<]+)</td>.*?<td>(UP|DOWN)</td>'
            matches = re.findall(server_pattern, response, re.DOTALL | re.IGNORECASE)

            servers_up = sum(1 for _, status in matches if status.upper() == 'UP')
            servers_down = sum(1 for _, status in matches if status.upper() == 'DOWN')
            down_list = [
                {'name': name, 'since': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
                for name, status in matches if status.upper() == 'DOWN'
            ]

        record_status('bums', True)
        return {
            'servers': {
                'total': servers_up + servers_down,
                'up': servers_up,
                'down': servers_down,
                'down_list': down_list
            },
            'filesystem': {
                'alerts': 0,
                'alert_list': []
            }
        }

    except Exception as e:
        record_status('bums', False, e)
        raise


def fetch_solarwinds():
    """
    Fetch SolarWinds alerts via SWIS API
    """
    if not CONFIG['solarwinds']['enabled']:
        return None

    cfg = CONFIG['solarwinds']

    try:
        # SWQL query for active alerts
        query = "SELECT AlertActive.AlertObjectID, AlertActive.ObjectName, AlertActive.Severity FROM Orion.AlertActive"
        request_data = json.dumps({'query': query}).encode('utf-8')

        import base64
        credentials = base64.b64encode(f"{cfg['username']}:{cfg['password']}".encode()).decode()

        request = Request(cfg['url'], data=request_data)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Authorization', f'Basic {credentials}')

        ctx = get_ssl_context()
        with urlopen(request, context=ctx, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))

        cpu_critical = 0
        cpu_warning = 0
        cpu_alerts = []
        memory_critical = 0
        memory_warning = 0
        memory_alerts = []

        for alert in data.get('results', []):
            obj_name = alert.get('ObjectName', '')
            severity = alert.get('Severity', 0)

            if 'CPU' in obj_name:
                sev = 'critical' if severity >= 2 else 'warning'
                if sev == 'critical':
                    cpu_critical += 1
                else:
                    cpu_warning += 1
                cpu_alerts.append({'node': obj_name, 'cpu': 95, 'severity': sev})
            elif 'Memory' in obj_name:
                sev = 'critical' if severity >= 2 else 'warning'
                if sev == 'critical':
                    memory_critical += 1
                else:
                    memory_warning += 1
                memory_alerts.append({'node': obj_name, 'memory': 90, 'severity': sev})

        record_status('solarwinds', True)
        return {
            'cpu_alerts': {
                'critical': cpu_critical,
                'warning': cpu_warning,
                'alert_list': cpu_alerts[:10]
            },
            'memory_alerts': {
                'critical': memory_critical,
                'warning': memory_warning,
                'alert_list': memory_alerts[:10]
            }
        }

    except Exception as e:
        record_status('solarwinds', False, e)
        raise


def fetch_aap():
    """
    Fetch AAP job results via REST API
    """
    if not CONFIG['aap']['enabled']:
        return None

    cfg = CONFIG['aap']

    try:
        from datetime import timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{cfg['url']}?created__gt={yesterday}&order_by=-created"
        headers = {'Authorization': f"Bearer {cfg['token']}"}

        response = fetch_url(url, headers=headers)
        data = json.loads(response)

        jobs = data.get('results', [])
        passed = sum(1 for j in jobs if j.get('status') == 'successful')
        failed = sum(1 for j in jobs if j.get('status') == 'failed')

        failed_list = [
            {'name': j.get('name', 'Unknown'), 'error': j.get('result_stdout', 'Unknown error')[:100]}
            for j in jobs if j.get('status') == 'failed'
        ][:5]

        record_status('aap', True)
        return {
            'last_run': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'jobs': {
                'total': len(jobs),
                'passed': passed,
                'failed': failed,
                'failed_list': failed_list
            }
        }

    except Exception as e:
        record_status('aap', False, e)
        raise


def fetch_audit():
    """
    Fetch audit report data
    """
    if not CONFIG['audit']['enabled']:
        return None

    cfg = CONFIG['audit']

    try:
        response = fetch_url(cfg['url'], cfg.get('username'), cfg.get('password'))

        # Parse based on format
        import re
        change_pattern = r'(srv-[\w-]+):\s*(/[\w/\.]+)\s+(modified|changed|added|removed)'
        matches = re.findall(change_pattern, response, re.IGNORECASE)

        alerts = [
            {
                'server': server,
                'file': filepath,
                'change': action.capitalize(),
                'time': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            for server, filepath, action in matches
        ][:10]

        record_status('audit', True)
        return {
            'last_scan': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'config_changes': {
                'total': len(alerts),
                'alerts': alerts
            }
        }

    except Exception as e:
        record_status('audit', False, e)
        raise


def fetch_tenable():
    """
    Fetch Tenable vulnerability scan data via REST API
    """
    if not CONFIG['tenable']['enabled']:
        return None

    cfg = CONFIG['tenable']

    try:
        headers = {
            'X-ApiKeys': f"accessKey={cfg['access_key']};secretKey={cfg['secret_key']}",
            'Content-Type': 'application/json'
        }

        # Fetch vulnerability summary
        response = fetch_url(cfg['url'], headers=headers)
        data = json.loads(response)

        # Parse vulnerability counts (adjust based on actual API response)
        vulns = data.get('response', {}).get('results', [])

        critical = sum(1 for v in vulns if v.get('severity', {}).get('id') == 4)
        high = sum(1 for v in vulns if v.get('severity', {}).get('id') == 3)
        medium = sum(1 for v in vulns if v.get('severity', {}).get('id') == 2)
        low = sum(1 for v in vulns if v.get('severity', {}).get('id') == 1)

        record_status('tenable', True)
        return {
            'last_scan': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'vulnerabilities': {
                'critical': critical,
                'high': high,
                'medium': medium,
                'low': low
            },
            'scan_failures': {
                'total': 0,
                'failed_list': []
            },
            'compliance': {
                'passed': 90,
                'failed': 10
            }
        }

    except Exception as e:
        record_status('tenable', False, e)
        raise


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("Starting OCC data fetch...")

    # Start with mock data as base
    data = get_mock_data()

    # Generate source URLs from config
    data['sourceUrls'] = generate_source_urls()

    # Fetch from each source
    sources = [
        ('servicenow', fetch_servicenow),
        ('bums', fetch_bums),
        ('solarwinds', fetch_solarwinds),
        ('aap', fetch_aap),
        ('audit', fetch_audit),
        ('tenable', fetch_tenable),
    ]

    for source_name, fetch_func in sources:
        try:
            source_data = fetch_func()
            if source_data:
                data[source_name] = source_data
                logger.info(f"  ✓ {source_name}: OK")
            else:
                logger.info(f"  - {source_name}: Disabled")
                record_status(source_name, True, "Disabled - using mock data")
        except Exception as e:
            logger.error(f"  ✗ {source_name}: ERROR - {e}")
            # Keep mock data for this source

    # Update timestamp and fetch status
    data['lastUpdated'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    data['fetchStatus'] = fetch_status

    # Write to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Data written to {OUTPUT_FILE}")

    # Summary
    ok_count = sum(1 for s in fetch_status.values() if s.get('ok'))
    total_count = len(fetch_status)
    logger.info(f"Fetch complete: {ok_count}/{total_count} sources OK")


if __name__ == '__main__':
    main()
