#!/usr/bin/env python3
"""
Vault Maintenance Workflow

Nightly vault enrichment and cleanup via kb-curator subagent.
"""

import os
import requests

OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "http://localhost:18789")
GATEWAY_PASSWORD = os.environ["GATEWAY_PASSWORD"]


def main():
    """Run vault maintenance tasks."""
    spawn_subagent(
        agent="kb-curator",
        instruction="Run nightly vault maintenance: enrich thin entities, add wikilinks, fix structure issues",
        context={
            "mode": "maintenance",
            "tasks": ["enrich", "interlink", "organize", "audit"]
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
