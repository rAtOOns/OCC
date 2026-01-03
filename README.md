# OCC - Unix Dashboard

A unified operations dashboard that displays real-time status from multiple monitoring systems.

---

## Quick Start

### Option 1: Easy Setup (Recommended)

Run the interactive setup wizard:
```bash
cd /path/to/OCC
python3 setup.py
```

The wizard will guide you through configuring each data source.

### Option 2: Manual Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials

3. Start the dashboard:
   ```bash
   ./start.sh
   ```

Then open: **http://localhost:8080**

---

## Dashboard Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Unix Dashboard                    ● Operational       Updated 2m ago      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   ServiceNow    │  │      BUMS       │  │   SolarWinds    │             │
│  │   Incidents &   │  │  Server Status  │  │   CPU/Memory    │             │
│  │   SLT Metrics   │  │  & Filesystem   │  │     Alerts      │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │    AAP Jobs     │  │  Audit Report   │  │    Tenable      │             │
│  │  Ansible Job    │  │ Config Changes  │  │ Vulnerabilities │             │
│  │    Results      │  │   Detection     │  │   & Compliance  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Each Card Shows

### ServiceNow
| Metric | Description |
|--------|-------------|
| Critical/High/Medium/Low | Open incidents by priority |
| Requests | Open service requests |
| Scheduled/Pending | Change requests status |
| Response % | SLT for incident response time |
| Resolution % | SLT for incident resolution time |

### BUMS (Unix Monitoring)
| Metric | Description |
|--------|-------------|
| Up/Down/Total | Server availability counts |
| Servers Down | List of currently down servers |
| Filesystem Alerts | Disks approaching capacity (>80%) |

### SolarWinds
| Metric | Description |
|--------|-------------|
| CPU Critical/Warning | Servers with high CPU usage |
| Memory Critical/Warning | Servers with high memory usage |
| Active Alerts | List of current performance alerts |

### AAP Jobs (Ansible)
| Metric | Description |
|--------|-------------|
| Passed/Failed | Job execution results |
| Success % | Overall job success rate |
| Failed Jobs | List of recently failed jobs with errors |

### Audit Report
| Metric | Description |
|--------|-------------|
| Config Changes | Number of configuration file changes |
| Recent Changes | List of modified files (ssh, passwd, sudoers, etc.) |

### Tenable
| Metric | Description |
|--------|-------------|
| Critical/High/Medium | Vulnerability counts by severity |
| Compliance % | Passed/Failed compliance checks |
| Scan Failures | Hosts that failed to scan |

---

## Status Indicators

### Header Status
| Status | Meaning |
|--------|---------|
| ● Operational | All systems normal |
| ● Warnings | Minor issues detected |
| ● Critical Issues | Immediate attention required |

### Card Badges
| Badge | Meaning |
|-------|---------|
| ✓ Healthy | No issues |
| ! Warning | Minor issues |
| ✕ Critical | Urgent issues |
| Mock | Using sample data (not live) |
| Error | Failed to fetch from source |

### Color Coding
| Color | Meaning |
|-------|---------|
| Green | Good / Healthy |
| Orange | Warning / Review needed |
| Red | Critical / Action required |
| Blue | Informational |

---

## Using the Dashboard

### Click Cards for Details
Click any card to open the original source system (ServiceNow, BUMS, etc.) for more details.

### Manual Refresh
Click the **Refresh** button in the header to fetch latest data immediately.

### Auto Refresh
The dashboard automatically refreshes every **60 seconds**.

### Keyboard Navigation
- **Tab**: Navigate between cards
- **Enter**: Open selected card's source

---

## Warnings & Alerts

### Stale Data Warning
If you see a yellow banner saying "Data may be outdated":
- The data hasn't been updated in over 10 minutes
- Click "Refresh Now" to try fetching fresh data
- Contact admin if issue persists

### Error Banner
If you see a red error banner:
- Failed to load data.json
- Check if the server is running
- Click "Retry" to attempt again

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard won't load | Check if server is running: `python3 -m http.server 8080` |
| Data shows "Mock" | Data sources not configured - contact admin |
| Stale data warning | Cron job may have stopped - check fetch.log |
| Card shows "Error" | Source API unreachable - check network |
| Can't click cards | Source URLs not configured |

---

## File Structure

```
OCC/
├── index.html          # Dashboard (open in browser)
├── data.json           # Current data (auto-updated)
├── fetch_data.py       # Data fetcher (runs via cron)
├── start.sh            # Quick start script
├── .env.example        # Configuration template
├── README.md           # This file (User Guide)
└── INTEGRATION_GUIDE.md # Admin setup guide
```

---

## For Administrators

See **INTEGRATION_GUIDE.md** for:
- Configuring data source connections
- Setting up credentials
- Cron job setup
- Troubleshooting API connections

---

## Support

If the dashboard shows incorrect data or errors:
1. Note which card is affected
2. Check the "Updated" timestamp in the header
3. Try clicking Refresh
4. Contact your system administrator
