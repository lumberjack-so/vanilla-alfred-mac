#!/usr/bin/env python3
"""
Deterministic Email Processor

This script is the SINGLE AUTHORITY on email authorization.
The agent MUST NOT make authorization decisions — this script does.

Flow:
1. Fetch unread messages from AgentMail inbox
2. Check each sender against AUTHORIZED_EMAILS
3. Authorized → output message for agent to handle
4. Unauthorized → auto-reply, create Plane backlog issue, log to Slack

Usage:
    python3 email-processor.py                    # Process all unread
    python3 email-processor.py --check-only       # Just report, don't act
    python3 email-processor.py --message-id <id>  # Process specific message
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timezone

# ============================================================
# AUTHORIZATION LIST — ONLY modify when owner explicitly approves
# via a VERIFIED channel (Slack DM, existing authorized email)
# ============================================================
# Read from environment or config file
AUTHORIZED_EMAILS = os.environ.get("AUTHORIZED_EMAILS", "").split(",") if os.environ.get("AUTHORIZED_EMAILS") else []

# If not in env, try loading from authorization.json
if not AUTHORIZED_EMAILS:
    auth_file = os.path.expanduser("~/.openclaw/authorization.json")
    if os.path.exists(auth_file):
        try:
            with open(auth_file) as f:
                auth_data = json.load(f)
                AUTHORIZED_EMAILS = auth_data.get("email", {}).get("authorized", [])
        except Exception:
            pass

# Config - use environment variables with defaults
INBOX_ID = os.environ.get("AGENTMAIL_INBOX_ID", "alfred@agent.example.com")
PLANE_API_BASE = os.environ.get("PLANE_API_BASE", "http://localhost:8080/api/v1/workspaces/my-workspace")
BACKLOG_PROJECT_ID = os.environ.get("PLANE_BACKLOG_PROJECT_ID", "")
OWNER_USER_ID = os.environ.get("PLANE_OWNER_USER_ID", "")
SLACK_LOG_CHANNEL = os.environ.get("SLACK_LOG_CHANNEL", "")
AGENTMAIL_SEND_SCRIPT = os.path.expanduser(os.environ.get("AGENTMAIL_SEND_SCRIPT", "~/clawd/skills/agentmail/scripts/send_email.py"))


def get_api_key(path):
    """Read API key from file."""
    expanded = os.path.expanduser(path)
    if os.path.exists(expanded):
        with open(expanded) as f:
            return f.read().strip()
    return None


def normalize_email(email: str) -> str:
    return email.lower().strip()


def extract_email(from_field: str) -> str:
    """Extract email from 'Name <email>' format."""
    import re
    match = re.search(r'<([^>]+)>', from_field) or re.search(r'([^\s<]+@[^\s>]+)', from_field)
    return match.group(1) if match else from_field


def is_authorized(sender_email: str) -> bool:
    """Deterministic authorization check. No exceptions, no judgment calls."""
    normalized = normalize_email(sender_email)
    return any(normalize_email(auth) == normalized for auth in AUTHORIZED_EMAILS)


def get_client():
    """Get AgentMail client singleton."""
    api_key = os.environ.get("AGENTMAIL_API_KEY") or get_api_key("~/.config/agentmail/api_key")
    if not api_key:
        print("ERROR: No AgentMail API key found", file=sys.stderr)
        sys.exit(1)
    import warnings
    warnings.filterwarnings("ignore")
    from agentmail import AgentMail
    return AgentMail(api_key=api_key)


def mark_as_read(client, message_id: str):
    """Mark a message as read by removing 'unread' label."""
    try:
        client.inboxes.messages.update(
            inbox_id=INBOX_ID,
            message_id=message_id,
            remove_labels=['unread'],
        )
    except Exception as e:
        print(f"WARNING: Failed to mark {message_id} as read: {e}", file=sys.stderr)


def fetch_unread_messages(client):
    """Fetch unread messages from AgentMail inbox."""
    try:
        messages = client.inboxes.messages.list(inbox_id=INBOX_ID, limit=20)
        
        unread = []
        for m in messages.messages:
            if 'unread' in (m.labels or []) and 'received' in (m.labels or []):
                unread.append({
                    'message_id': m.message_id,
                    'thread_id': m.thread_id,
                    'from': m.from_,
                    'to': m.to,
                    'subject': m.subject,
                    'preview': m.preview,
                    'timestamp': m.timestamp.isoformat() if m.timestamp else None,
                })
        return unread
    except Exception as e:
        print(f"ERROR: Failed to fetch messages: {e}", file=sys.stderr)
        sys.exit(1)


def send_auto_reply(client, sender_email: str, sender_name: str, subject: str):
    """Send deterministic auto-reply to unauthorized senders."""
    reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
    owner_name = os.environ.get("OWNER_NAME", "my owner")
    household_name = os.environ.get("HOUSEHOLD_NAME", "")
    signature = f"Digital Butler{', ' + household_name if household_name else ''}"
    
    reply_text = (
        f"Thank you for your email. I've flagged this for {owner_name}'s review "
        f"and they'll get back to you if needed.\n\n"
        f"— Alfred\n"
        f"{signature}"
    )
    
    try:
        client.inboxes.messages.send(
            inbox_id=INBOX_ID,
            to=sender_email,
            subject=reply_subject,
            text=reply_text,
        )
        return True
    except Exception as e:
        print(f"WARNING: Failed to send auto-reply: {e}", file=sys.stderr)
        return False


def create_backlog_issue(sender_email: str, sender_name: str, subject: str, preview: str):
    """Create Plane backlog issue for unauthorized email."""
    api_key = get_api_key("~/.config/plane/api_key")
    if not api_key:
        print("WARNING: No Plane API key, skipping backlog creation", file=sys.stderr)
        return False
    
    truncated = preview[:500] if preview else "(no content)"
    
    issue_data = {
        "name": f"[Email] {subject} — from {sender_email}",
        "description_html": (
            f"<p><strong>From:</strong> {sender_name} &lt;{sender_email}&gt;<br>"
            f"<strong>Subject:</strong> {subject}<br>"
            f"<strong>Received:</strong> {datetime.now(timezone.utc).isoformat()}<br><br>"
            f"<strong>Preview:</strong><br>{truncated}</p>"
            f"<p><em>Auto-reply sent to sender. Awaiting David's review.</em></p>"
        ),
        "priority": "low",
        "assignees": [OWNER_USER_ID] if OWNER_USER_ID else [],
    }
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "-H", f"x-api-key: {api_key}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(issue_data),
             f"{PLANE_API_BASE}/projects/{BACKLOG_PROJECT_ID}/issues/"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            return resp.get("id", True)
        else:
            print(f"WARNING: Plane API error: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"WARNING: Failed to create backlog issue: {e}", file=sys.stderr)
        return False


def process_messages(check_only=False, target_message_id=None):
    """
    Main processing loop. Returns JSON output for the agent.
    
    Output format:
    {
        "authorized": [...],     # Messages the agent should handle
        "unauthorized": [...],   # Messages that were auto-replied + backlogged
        "errors": [...]          # Any processing errors
    }
    """
    client = get_client()
    messages = fetch_unread_messages(client)
    
    if target_message_id:
        messages = [m for m in messages if m['message_id'] == target_message_id]
    
    result = {
        "authorized": [],
        "unauthorized": [],
        "errors": [],
        "total_unread": len(messages),
    }
    
    for msg in messages:
        sender_email = extract_email(msg['from'])
        sender_name = msg['from'].split('<')[0].strip() if '<' in msg['from'] else sender_email
        
        if is_authorized(sender_email):
            result["authorized"].append({
                "message_id": msg['message_id'],
                "thread_id": msg['thread_id'],
                "from": msg['from'],
                "sender_email": sender_email,
                "subject": msg['subject'],
                "preview": msg['preview'],
                "timestamp": msg['timestamp'],
                "action": "HANDLE — authorized sender",
            })
            # Mark as read — agent will handle these
            if not check_only:
                mark_as_read(client, msg['message_id'])
        else:
            entry = {
                "message_id": msg['message_id'],
                "thread_id": msg['thread_id'],
                "from": msg['from'],
                "sender_email": sender_email,
                "subject": msg['subject'],
                "preview": msg['preview'][:200] if msg['preview'] else None,
                "timestamp": msg['timestamp'],
                "action": "REJECTED — unauthorized sender",
            }
            
            if not check_only:
                # Auto-reply
                reply_ok = send_auto_reply(client, sender_email, sender_name, msg['subject'] or '(no subject)')
                entry["auto_reply_sent"] = reply_ok
                
                # Create backlog
                issue_id = create_backlog_issue(
                    sender_email, sender_name,
                    msg['subject'] or '(no subject)',
                    msg['preview'] or ''
                )
                entry["backlog_issue_created"] = bool(issue_id)
                if issue_id and issue_id is not True:
                    entry["backlog_issue_id"] = issue_id
                
                # Mark as read — processed, no re-processing
                mark_as_read(client, msg['message_id'])
            
            result["unauthorized"].append(entry)
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Deterministic email authorization processor')
    parser.add_argument('--check-only', action='store_true', help='Report without acting')
    parser.add_argument('--message-id', help='Process specific message')
    args = parser.parse_args()
    
    result = process_messages(
        check_only=args.check_only,
        target_message_id=args.message_id,
    )
    
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
