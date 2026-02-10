"""
Plane Task Polling Workflow

Check Plane PM for tasks moved to 'todo' state that need delegation.
Spawns appropriate subagents to handle tasks.

Schedule: */15 * * * * (every 15 minutes)
"""

import requests
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# =============================================================================
# CONFIGURATION - Uses environment variables
# =============================================================================

HOME_DIR = os.path.expanduser("~")
CLAWD_DIR = os.environ.get("CLAWD_DIR", f"{HOME_DIR}/clawd")

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:18789")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN", "")

STATE_FILE = Path(f"{CLAWD_DIR}/.plane-polling-state.json")
SLACK_CHANNEL = os.environ.get("SLACK_LOGS_CHANNEL", "")  # Set in config

UPTIME_PUSH = os.environ.get("UPTIME_PUSH_URL", "http://localhost:3001/api/push/plane-poll?status=up&msg=OK")

# =============================================================================
# OPENCLAW INTEGRATION
# =============================================================================

def spawn_alfred(task: str, agent: str = "alfred", timeout: int = 300) -> dict:
    """Spawn an isolated agent session."""
    response = requests.post(
        f"{GATEWAY_URL}/tools/invoke",
        headers={
            "Authorization": f"Bearer {GATEWAY_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "tool": "sessions_spawn",
            "args": {
                "task": task,
                "agentId": agent,
                "cleanup": "delete",
                "runTimeoutSeconds": timeout
            }
        },
        timeout=timeout + 60
    )
    return response.json()


def notify_slack(message: str):
    """Send notification to Slack."""
    if not SLACK_CHANNEL:
        print(f"[NOTIFY] {message}")
        return
    
    requests.post(
        f"{GATEWAY_URL}/tools/invoke",
        headers={
            "Authorization": f"Bearer {GATEWAY_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "tool": "message",
            "args": {
                "action": "send",
                "channel": "slack",
                "target": SLACK_CHANNEL,
                "message": message
            }
        },
        timeout=30
    )


def ping_uptime():
    """Ping Uptime Kuma."""
    try:
        requests.get(UPTIME_PUSH, timeout=10)
    except Exception:
        pass

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_poll": None,
        "delegated_tasks": [],
        "known_todo_ids": []
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

# =============================================================================
# PLANE INTEGRATION
# =============================================================================

def get_todo_tasks() -> Optional[List[Dict]]:
    """Get tasks in 'todo' state from Plane. Returns None on failure, [] on no tasks."""
    try:
        result = subprocess.run(
            ["python3", f"{CLAWD_DIR}/scripts/plane-check.py", "--todo", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
            print(f"plane-check.py failed: {error_msg}")
            return None  # Explicit failure, not "no tasks"
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting todo tasks: {e}")
        return None


def delegate_task(task: Dict) -> Optional[Dict]:
    """Delegate a task to appropriate subagent."""
    task_id = task.get("id", "unknown")
    task_name = task.get("name", "Untitled")
    task_desc = task.get("description", "")
    
    # Use delegation engine to pick subagent
    try:
        result = subprocess.run(
            [
                "python3", f"{CLAWD_DIR}/scripts/delegation-engine.py",
                "delegate", task_name,
                "--source", "plane",
                "--sender", "system",
                "--json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            delegation = json.loads(result.stdout)
            agent = delegation.get("agent", "alfred")
            
            # Spawn the subagent
            spawn_result = spawn_alfred(
                task=f"""PLANE TASK: {task_name}

{task_desc}

Task ID: {task_id}

Complete this task. When done, update the Plane issue to 'done' state.""",
                agent=agent,
                timeout=600
            )
            
            return {
                "task_id": task_id,
                "task_name": task_name,
                "agent": agent,
                "result": spawn_result
            }
    except Exception as e:
        print(f"Delegation error: {e}")
        return None


def update_task_status(task_id: str, status: str = "in_progress"):
    """Update task status in Plane."""
    try:
        subprocess.run(
            [
                "python3", f"{CLAWD_DIR}/scripts/plane-client.py",
                "update-status", task_id, status
            ],
            capture_output=True,
            timeout=30
        )
    except Exception:
        pass

# =============================================================================
# MAIN WORKFLOW
# =============================================================================

def poll_and_delegate():
    """Check for todo tasks and delegate them."""
    state = load_state()
    now = datetime.now()
    
    # Get current todo tasks
    todo_tasks = get_todo_tasks()
    
    if todo_tasks is None:
        # Failed to check — this is an error, not "no tasks"
        notify_slack("[WORKFLOW] plane-polling ❌\\nFailed to fetch tasks from Plane. Check plane-check.py and Plane API.")
        state["last_poll"] = now.isoformat()
        state["last_error"] = now.isoformat()
        save_state(state)
        raise RuntimeError("Failed to fetch tasks from Plane")
    
    if not todo_tasks:
        # Genuinely no tasks — quiet success
        ping_uptime()
        state["last_poll"] = now.isoformat()
        save_state(state)
        return
    
    # Find new tasks (not already known/delegated)
    known_ids = set(state.get("known_todo_ids", []))
    new_tasks = [t for t in todo_tasks if t.get("id") not in known_ids]
    
    if not new_tasks:
        # No new tasks
        ping_uptime()
        state["last_poll"] = now.isoformat()
        save_state(state)
        return
    
    # Delegate new tasks
    delegated = []
    for task in new_tasks:
        print(f"Delegating: {task.get('name')}")
        
        # Mark as in_progress immediately
        update_task_status(task.get("id"), "in_progress")
        
        # Delegate
        result = delegate_task(task)
        if result:
            delegated.append(result)
            state["known_todo_ids"].append(task.get("id"))
    
    # Update state
    state["last_poll"] = now.isoformat()
    state["delegated_tasks"].extend(delegated)
    save_state(state)
    
    # Log to Slack only if we delegated something
    if delegated:
        summary = "\\n".join(
            f"• {d['task_name']} → {d['agent']}"
            for d in delegated
        )
        notify_slack(f"[WORKFLOW] plane-polling\\n{len(delegated)} tasks delegated:\\n{summary}")
    
    ping_uptime()

# =============================================================================
# ENTRY POINTS
# =============================================================================

def on_schedule(event):
    """Every 15 min poll."""
    poll_and_delegate()


def on_webhook(event):
    """Manual trigger."""
    print(f"[{datetime.now()}] Webhook triggered...")
    poll_and_delegate()
    print(f"[{datetime.now()}] Complete.")
