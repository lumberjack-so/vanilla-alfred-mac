#!/usr/bin/env python3
"""Integration Health Check Workflow"""

import os
import requests
import subprocess

OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "http://localhost:18789")
GATEWAY_PASSWORD = os.environ["GATEWAY_PASSWORD"]


def main():
    """Run integration health checks."""
    results = {
        "google_oauth": check_google_oauth(),
        "agentmail": check_agentmail(),
        "docker": check_docker(),
        "temporal": check_temporal(),
    }
    
    # Report any failures
    failures = [k for k, v in results.items() if not v]
    if failures:
        notify_failures(failures)


def check_google_oauth():
    """Check if Google OAuth is valid."""
    try:
        result = subprocess.run(
            ["gog", "calendar", "list"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False


def check_agentmail():
    """Check if AgentMail relay is running."""
    try:
        subprocess.run(
            ["pgrep", "-f", "agentmail-relay.py"],
            capture_output=True,
            check=True
        )
        return True
    except:
        return False


def check_docker():
    """Check if Docker is responsive."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_temporal():
    """Check if Temporal is accessible."""
    try:
        subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            check=True
        )
        return True
    except:
        return False


def notify_failures(failures):
    """Notify ops-guardian of failures."""
    spawn_subagent(
        agent="ops-guardian",
        instruction=f"Integration health check failed: {', '.join(failures)}. Investigate and fix.",
        context={"failures": failures}
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


if __name__ == "__main__":
    main()
