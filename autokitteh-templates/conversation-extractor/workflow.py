"""
Conversation Extractor for AutoKitteh
Processes OpenClaw conversation archives and extracts entities to Alfred KB.
Uses durable workflows for reliable processing with automatic recovery.
"""

import os
import json
import subprocess
import re
import shutil
from datetime import datetime
from pathlib import Path

# Configuration - uses environment variables
HOME_DIR = os.path.expanduser("~")
OPENCLAW_DIR = os.environ.get("OPENCLAW_DIR", f"{HOME_DIR}/.openclaw")
VAULT_PATH = os.environ.get("VAULT_PATH", f"{HOME_DIR}/alfred/alfred")
CLAWD_DIR = os.environ.get("CLAWD_DIR", f"{HOME_DIR}/clawd")
STATE_FILE = f"{CLAWD_DIR}/.conversation-extractor-state.json"
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:18789")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_LOGS_CHANNEL", "")

# Limits
MAX_MESSAGES_PER_CONVERSATION = 200
MAX_CONVERSATIONS_PER_RUN = 25  # Process batch at a time to avoid overwhelming


def load_state() -> dict:
    """Load processing state from disk."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed": [], "failed": [], "last_run": None}


def save_state(state: dict) -> bool:
    """Save processing state to disk."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)
    return True


def discover_conversations() -> list:
    """Discover all conversation JSONL files from OpenClaw agents."""
    conversations = []
    agents_dir = os.path.join(OPENCLAW_DIR, "agents")
    
    if not os.path.exists(agents_dir):
        print(f"No agents directory at {agents_dir}")
        return conversations
    
    for agent_name in os.listdir(agents_dir):
        agent_dir = os.path.join(agents_dir, agent_name)
        if not os.path.isdir(agent_dir):
            continue
        
        sessions_dir = os.path.join(agent_dir, "sessions")
        if not os.path.exists(sessions_dir):
            continue
        
        for filename in os.listdir(sessions_dir):
            if not filename.endswith(".jsonl"):
                continue
            
            session_file = os.path.join(sessions_dir, filename)
            session_id = filename[:-6]  # Remove .jsonl
            
            # Count messages
            msg_count = 0
            try:
                with open(session_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("type") == "message":
                                msg_count += 1
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
            
            conversations.append({
                "agent": agent_name,
                "session_id": session_id,
                "path": session_file,
                "message_count": msg_count,
            })
    
    return conversations


def extract_conversation_text(path: str, max_messages: int = 100) -> str:
    """Extract conversation text from JSONL file."""
    messages = []
    with open(path) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("type") == "message":
                    msg = entry.get("message", {})
                    role = msg.get("role", "unknown")
                    content = msg.get("content", [])
                    
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    
                    if text_parts:
                        messages.append(f"{role.upper()}: {' '.join(text_parts)}")
            except json.JSONDecodeError:
                continue
            
            if len(messages) >= max_messages:
                break
    
    return "\\n\\n".join(messages)


def process_single_conversation(conv: dict) -> dict:
    """Process a single conversation via kb-curator subagent."""
    path = conv["path"]
    agent = conv["agent"]
    session_id = conv["session_id"]
    
    print(f"Processing: {agent}/{session_id} ({conv['message_count']} messages)")
    
    # Extract conversation text
    text = extract_conversation_text(path, max_messages=100)
    if len(text) < 100:
        return {"status": "skipped", "reason": "too_short", "agent": agent, "session_id": session_id}
    
    # Truncate for prompt
    if len(text) > 50000:
        text = text[:50000] + "\\n\\n[TRUNCATED]"
    
    prompt = f"""CONVERSATION EXTRACTION TASK

Extract structured entities from this conversation archive into the Alfred KB vault.

Conversation: {agent}/{session_id}
Messages: {conv['message_count']}

## ⚠️ CRITICAL: NAME VALIDATION (READ THIS FIRST)

**VALID entity names** — create these:
- `person/john-smith` — Real human names
- `org/anthropic` — Real company names  
- `proj/alfred-os` — Established project names
- `learn/technical-concept` — Clear technical concepts

**INVALID names** — NEVER create:
- Fragment names: `why-alfred`, `use-google`, `your-kid`, `the-butler`
- Sentence fragments: `the-async-handling-would-need`, `alfred-doesnt-just-execute`
- Verb phrases: `building-alfred`, `added-user`, `store-data`
- Names starting with: `why-`, `use-`, `get-`, `your-`, `the-`, `so-`, `new-`, `as-`, `to-`, `in-`, `for-`

**VALIDATION RULE**: Before creating any entity, ask yourself:
"Is this a real proper noun that someone would recognize?"
- YES → create it
- NO → skip it

**If unsure, DO NOT CREATE IT. Empty arrays are acceptable.**

## Content Rules
- Minimum 300 words for any new entity
- No stubs
- Search existing entities first

## Skip Entirely If:
- Conversation is cron job output / heartbeat / system check
- No real named people, orgs, or projects exist
- You would need to create fragment-named entities

## Conversation Text
```
{text}
```

Return JSON (empty arrays are fine):
{{"entities_created": [], "entities_updated": [], "event_file": null}}
"""

    try:
        # Use /tools/invoke with sessions_spawn tool
        payload = {
            "tool": "sessions_spawn",
            "args": {
                "task": prompt,
                "agentId": "kb-curator",
                "model": "google/gemini-3-flash",
                "cleanup": "delete",
                "runTimeoutSeconds": 300
            }
        }
        
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                f"{GATEWAY_URL}/tools/invoke",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {GATEWAY_TOKEN}",
                "-d", json.dumps(payload)
            ],
            capture_output=True,
            text=True,
            timeout=330
        )
        
        if result.returncode != 0:
            return {"status": "error", "reason": "curl_failed", "agent": agent, "session_id": session_id}
        
        # Check if API returned success
        try:
            response = json.loads(result.stdout)
            if response.get("ok"):
                return {"status": "success", "agent": agent, "session_id": session_id}
            else:
                return {"status": "error", "reason": response.get("error", "api_error"), "agent": agent, "session_id": session_id}
        except json.JSONDecodeError:
            return {"status": "error", "reason": f"invalid_response: {result.stdout[:100]}", "agent": agent, "session_id": session_id}
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "timeout", "agent": agent, "session_id": session_id}
    except Exception as e:
        return {"status": "error", "reason": str(e), "agent": agent, "session_id": session_id}


def notify_slack(message: str) -> bool:
    """Send notification to Slack logs channel."""
    if not SLACK_CHANNEL:
        print(f"[NOTIFY] {message}")
        return True
        
    payload = {
        "tool": "message",
        "args": {
            "action": "send",
            "channel": "slack",
            "target": SLACK_CHANNEL,
            "message": message
        }
    }
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"{GATEWAY_URL}/tools/invoke",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {GATEWAY_TOKEN}",
        "-d", json.dumps(payload)
    ], timeout=30)
    return True


def ping_uptime_kuma() -> bool:
    """Ping Uptime Kuma heartbeat."""
    uptime_url = os.environ.get("UPTIME_PUSH_CONV_URL", "http://localhost:3001/api/push/conv-extraction?status=up&msg=OK")
    subprocess.run(["curl", "-s", uptime_url], timeout=10)
    return True


# Garbage detection patterns
GARBAGE_PATTERNS = [
    r"^(why|use|get|your|the|so|new|as|to|in|for|with|from|about|building|added|store|apple)-",
    r"-(doesnt|expired|failed|blocked|pending|or-email|at-that|as-4th|by-locking)",
    r"^[a-z]+-[a-z]+-[a-z]+-[a-z]+-[a-z]+-[a-z]+-[a-z]+",
]


def cleanup_recent_garbage() -> dict:
    """Find and archive any garbage entities created in last hour."""
    vault = Path(VAULT_PATH)
    archive = vault / "_archive" / "garbage-auto"
    entity_dirs = ["person", "org", "proj", "learn", "evt"]
    
    garbage = []
    for dir_name in entity_dirs:
        dir_path = vault / dir_name
        if not dir_path.exists():
            continue
        
        for file in dir_path.glob("*.md"):
            # Check if modified in last hour
            import time
            if time.time() - file.stat().st_mtime > 3600:
                continue
            
            filename = file.stem
            for pattern in GARBAGE_PATTERNS:
                if re.search(pattern, filename, re.IGNORECASE):
                    garbage.append(file)
                    break
    
    if not garbage:
        return {"cleaned": 0}
    
    # Archive garbage
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = archive / timestamp
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    cleaned = 0
    for file in garbage:
        try:
            dest = archive_dir / file.name
            shutil.move(str(file), str(dest))
            cleaned += 1
            print(f"Archived garbage: {file.name}")
        except Exception as e:
            print(f"Failed to archive {file}: {e}")
    
    return {"cleaned": cleaned, "archive": str(archive_dir)}


def start_extraction(event):
    """Webhook trigger for manual extraction."""
    print(f"Manual extraction triggered: {event}")
    result = run_extraction(limit=10)
    return result


def scheduled_extraction(event):
    """Scheduled daily extraction."""
    print(f"Scheduled extraction: {event}")
    result = run_extraction(limit=MAX_CONVERSATIONS_PER_RUN)
    return result


def run_extraction(limit: int = 50) -> dict:
    """Main extraction workflow."""
    state = load_state()
    # Ensure processed is a list
    if not isinstance(state.get("processed"), list):
        state["processed"] = []
    if not isinstance(state.get("failed"), list):
        state["failed"] = []
    processed_ids = set(state["processed"])
    
    # Discover conversations
    all_convs = discover_conversations()
    print(f"Discovered {len(all_convs)} total conversations")
    
    # Filter
    to_process = []
    for c in all_convs:
        conv_id = f"{c['agent']}/{c['session_id']}"
        if conv_id not in processed_ids:
            if 5 <= c["message_count"] <= MAX_MESSAGES_PER_CONVERSATION:
                to_process.append(c)
                if len(to_process) >= limit:
                    break
    
    print(f"Processing {len(to_process)} conversations")
    
    if not to_process:
        print("Nothing to process")
        return {"success": 0, "error": 0, "skipped": 0, "total": 0}
    
    # Process each conversation
    results = {"success": 0, "error": 0, "skipped": 0}
    for conv in to_process:
        conv_id = f"{conv['agent']}/{conv['session_id']}"
        
        result = process_single_conversation(conv)
        
        if result["status"] == "success":
            results["success"] += 1
            state["processed"].append(conv_id)
        elif result["status"] == "skipped":
            results["skipped"] += 1
            state["processed"].append(conv_id)
        else:
            results["error"] += 1
            if "failed" not in state:
                state["failed"] = []
            state["failed"].append({
                "id": conv_id,
                "error": result.get("reason", "unknown"),
                "timestamp": datetime.now().isoformat()
            })
    
    # Save state
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    # Notify
    notify_slack(
        f"[CRON] Conversation Extraction\\n"
        f"Why: {'Manual' if limit < MAX_CONVERSATIONS_PER_RUN else 'Scheduled'} extraction\\n"
        f"Result: {results['success']} extracted, {results['skipped']} skipped, {results['error']} errors"
    )
    
    # Cleanup any garbage that slipped through
    cleanup_result = cleanup_recent_garbage()
    if cleanup_result.get("cleaned", 0) > 0:
        print(f"Post-extraction cleanup: archived {cleanup_result['cleaned']} garbage entities")
    
    # Ping Uptime Kuma
    ping_uptime_kuma()
    
    print(f"Extraction complete: {results}")
    results["total"] = len(to_process)
    results["garbage_cleaned"] = cleanup_result.get("cleaned", 0)
    return results
