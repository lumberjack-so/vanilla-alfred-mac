# Remind Me - Reminders & Notifications

**⚠️ NOTE:** This skill needs to be rewritten for Temporal Python SDK workflows.  
The AutoKitteh implementation below is deprecated.

**Purpose:** Schedule reminders and notifications for future times.

## Usage

Create reminders using Temporal workflows (durable, survives restarts):

```python
import datetime
import requests

# Schedule a reminder
def schedule_reminder(message, when_iso):
    """
    Schedule a reminder via AutoKitteh.
    
    Args:
        message: What to remind about
        when_iso: ISO timestamp (e.g., "2024-12-25T09:00:00Z")
    """
    # This would trigger an AutoKitteh workflow
    # that wakes Alfred at the specified time
    pass

# Examples
schedule_reminder("Meeting with John", "2024-02-10T14:00:00Z")
schedule_reminder("Call dentist", "2024-02-11T09:30:00Z")
```

## Quick Syntax

When user says: "Remind me to X in Y"

**Parse the time:**
- "in 10 minutes" → now + 10 minutes
- "in 2 hours" → now + 2 hours
- "tomorrow at 9am" → next day at 9:00
- "next Monday" → upcoming Monday at 9:00 (default)
- "on Dec 25" → specific date at 9:00 (default)

**Convert to ISO 8601:**
```python
from datetime import datetime, timedelta
import pytz

tz = pytz.timezone("{{USER_TIMEZONE}}")
now = datetime.now(tz)

# "in 10 minutes"
reminder_time = now + timedelta(minutes=10)

# "tomorrow at 9am"
reminder_time = (now + timedelta(days=1)).replace(hour=9, minute=0)

# Convert to ISO
iso_time = reminder_time.isoformat()
```

## Implementation via AutoKitteh

Create a one-shot workflow:

```python
# ~/clawd/autokitteh-projects/reminder-{id}/workflow.py

import os
import time
import requests
from datetime import datetime

# Scheduled time (passed as env var)
SCHEDULED_TIME = os.environ.get("SCHEDULED_TIME")
MESSAGE = os.environ.get("MESSAGE")
TARGET_USER = os.environ.get("TARGET_USER")

def main():
    # Wait until scheduled time
    scheduled_dt = datetime.fromisoformat(SCHEDULED_TIME)
    now = datetime.now(scheduled_dt.tzinfo)
    
    wait_seconds = (scheduled_dt - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    
    # Send reminder via OpenClaw
    send_reminder(MESSAGE, TARGET_USER)

def send_reminder(message, user):
    # Wake Alfred via OpenClaw gateway
    gateway_url = "http://localhost:18789/tools/invoke"
    gateway_password = os.environ.get("GATEWAY_PASSWORD")
    
    payload = {
        "tool": "message",
        "args": {
            "action": "send",
            "target": user,
            "message": f"⏰ Reminder: {message}"
        }
    }
    
    requests.post(
        gateway_url,
        json=payload,
        headers={"Authorization": f"Bearer {gateway_password}"}
    )

if __name__ == "__main__":
    main()
```

## Deployment

```bash
# Create workflow directory
REMINDER_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
mkdir -p ~/clawd/autokitteh-projects/reminder-$REMINDER_ID

# Create workflow config
cat > ~/clawd/autokitteh-projects/reminder-$REMINDER_ID/autokitteh.yaml <<EOF
version: v1
project: reminder-$REMINDER_ID
triggers:
  - schedule: "once"
connections:
  - name: openclaw-gateway
    url: http://localhost:18789
EOF

# Deploy
cd ~/clawd/autokitteh-projects/reminder-$REMINDER_ID
ak deploy .
```

## User-Friendly Response

When reminder is set:
```
✓ I'll remind you: "{message}"
  Time: {human_readable_time}
  ({relative_time} from now)
```

Examples:
```
✓ I'll remind you: "Call dentist"
  Time: Tomorrow at 9:30 AM
  (in 18 hours)
```

## Recurring Reminders

For recurring reminders, use cron schedule:

```bash
# Every Monday at 9am
schedule: "0 9 * * 1"

# Daily at 7am
schedule: "0 7 * * *"

# Every hour
schedule: "0 * * * *"
```

## Storage

Track active reminders in:
```json
// ~/clawd/memory/reminders.json
{
  "active": [
    {
      "id": "reminder-abc123",
      "message": "Call dentist",
      "scheduled": "2024-02-11T09:30:00Z",
      "created": "2024-02-10T15:20:00Z",
      "status": "pending"
    }
  ]
}
```

## Cancellation

```bash
# List active reminders
cat ~/clawd/memory/reminders.json

# Cancel reminder
ak session stop {reminder-id}
```

## Integration with Calendar

Sync reminders to Google Calendar as events:
```bash
gog calendar add "Reminder: Call dentist" \
  --start "2024-02-11T09:30:00Z" \
  --account user@example.com
```
