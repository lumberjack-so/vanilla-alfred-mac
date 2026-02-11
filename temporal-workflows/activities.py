"""
Shared Temporal activities for Alfred workflows.

Activities are the building blocks — each one does exactly one thing.
Workflows compose them into pipelines.
"""

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from temporalio import activity

from config import GATEWAY_URL, GATEWAY_TOKEN, SLACK_LOGS, UPTIME_PUSHES

HEADERS = {
    "Authorization": f"Bearer {GATEWAY_TOKEN}",
    "Content-Type": "application/json",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SpawnResult:
    success: bool
    output: str
    session_key: Optional[str] = None


@dataclass
class ScriptResult:
    success: bool
    output: str
    exit_code: int = 0


# =============================================================================
# CORE ACTIVITIES
# =============================================================================

@activity.defn
async def spawn_agent(task: str, agent: str = "kb-curator", timeout: int = 300) -> SpawnResult:
    """Spawn an OpenClaw subagent and wait for completion."""
    activity.logger.info(f"Spawning {agent} (timeout={timeout}s)")

    # Spawn
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/tools/invoke",
            headers=HEADERS,
            json={
                "tool": "sessions_spawn",
                "args": {
                    "task": task,
                    "agentId": agent,
                    "cleanup": "delete",
                    "runTimeoutSeconds": timeout,
                },
            },
            timeout=timeout + 60,
        )
        result = resp.json()
    except Exception as e:
        return SpawnResult(success=False, output=f"Spawn request failed: {e}")

    if not result.get("ok"):
        return SpawnResult(success=False, output=f"Spawn failed: {result.get('error', 'unknown')}")

    details = result.get("result", {}).get("details", {})
    session_key = details.get("childSessionKey", "")
    if not session_key:
        # Might have completed already — check for inline result
        summary = details.get("summary", "")
        if summary:
            return SpawnResult(success=True, output=summary, session_key="completed-inline")
        return SpawnResult(success=False, output="No childSessionKey in spawn response")

    activity.logger.info(f"Spawned session: {session_key}")

    # Poll for completion
    deadline = time.time() + timeout
    while time.time() < deadline:
        activity.heartbeat()
        time.sleep(15)

        try:
            hist = requests.post(
                f"{GATEWAY_URL}/tools/invoke",
                headers=HEADERS,
                json={
                    "tool": "sessions_history",
                    "args": {
                        "sessionKey": session_key,
                        "limit": 5,
                        "includeTools": False,
                    },
                },
                timeout=15,
            ).json()
        except Exception:
            continue

        if not hist.get("ok"):
            error_msg = str(hist.get("error", ""))
            if "not found" in error_msg.lower():
                return SpawnResult(success=True, output="Session completed (cleaned up)", session_key=session_key)
            continue

        messages = hist.get("result", {}).get("details", {}).get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    text = "\n".join(
                        c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                    )
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                if len(text.strip()) > 20:
                    return SpawnResult(success=True, output=text.strip()[:50000], session_key=session_key)

    return SpawnResult(success=False, output=f"Timed out after {timeout}s", session_key=session_key)


@activity.defn
async def run_script(command: str, timeout: int = 120) -> ScriptResult:
    """Run a shell command and return output."""
    activity.logger.info(f"Running: {command[:100]}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()[:2000] or f"Exit code {result.returncode}"
            return ScriptResult(success=False, output=error, exit_code=result.returncode)
        return ScriptResult(success=True, output=output[:50000], exit_code=0)
    except subprocess.TimeoutExpired:
        return ScriptResult(success=False, output=f"Timed out after {timeout}s", exit_code=-1)
    except Exception as e:
        return ScriptResult(success=False, output=str(e), exit_code=-1)


@activity.defn
async def notify_slack(message: str, channel: str = SLACK_LOGS) -> bool:
    """Send a message to Slack."""
    try:
        requests.post(
            f"{GATEWAY_URL}/tools/invoke",
            headers=HEADERS,
            json={
                "tool": "message",
                "args": {"action": "send", "channel": "slack", "target": channel, "message": message},
            },
            timeout=30,
        )
        return True
    except Exception:
        return False


@activity.defn
async def ping_uptime(key: str) -> bool:
    """Ping an Uptime Kuma push endpoint."""
    url = UPTIME_PUSHES.get(key)
    if not url:
        return False
    try:
        requests.get(url, timeout=10)
        return True
    except Exception:
        return False


@activity.defn
async def check_day_of_week() -> int:
    """Return current day of week (0=Monday) in Budapest timezone."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Budapest"))
    return now.weekday()


@activity.defn
async def load_json_state(path: str) -> dict:
    """Load a JSON state file."""
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {}


@activity.defn
async def save_json_state(path: str, data: dict) -> bool:
    """Save a JSON state file."""
    Path(path).write_text(json.dumps(data, indent=2, default=str))
    return True
