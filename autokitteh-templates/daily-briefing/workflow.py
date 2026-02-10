#!/usr/bin/env python3
"""
Daily Briefing Workflow

Generates morning briefing and sends to user via Alfred.
Comprehensive on Mondays, lightweight other days.
"""

import os
import requests
from datetime import datetime, timedelta

OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "http://localhost:18789")
GATEWAY_PASSWORD = os.environ["GATEWAY_PASSWORD"]


def main():
    """Generate and send daily briefing."""
    today = datetime.now()
    is_monday = today.weekday() == 0
    
    # Spawn briefing-butler subagent
    spawn_subagent(
        agent="briefing-butler",
        instruction=f"Generate {'comprehensive' if is_monday else 'light'} daily briefing for {today.strftime('%Y-%m-%d')}",
        context={
            "date": today.isoformat(),
            "day_of_week": today.strftime("%A"),
            "is_monday": is_monday
        }
    )


def spawn_subagent(agent, instruction, context):
    """Spawn a subagent via OpenClaw gateway."""
    response = requests.post(
        f"{OPENCLAW_URL}/tools/invoke",
        headers={"Authorization": f"Bearer {GATEWAY_PASSWORD}"},
        json={
            "tool": "sessions_spawn",
            "args": {
                "agent": agent,
                "instruction": instruction,
                "context": context
            }
        }
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    main()
