#!/usr/bin/env python3
"""
Backlog Issue Handler

Checks Plane Backlog project for issues:
- Assigned to Alfred (12c5c442-d3b0-44ab-a9fe-8b9937096e7b)
- In Todo state

For each matching issue, outputs structured JSON with:
- Issue details (title, description)
- All comments
- Original email info (parsed from title/description)

This script does NOT handle the issues — it outputs what needs handling.
Alfred (the agent) reads the output and acts on it.

Usage:
    backlog-handler.py              # Check for actionable issues
    backlog-handler.py --dry-run    # Show without marking
    backlog-handler.py --json       # JSON output only
"""

import argparse
import json
import sys
import requests
from pathlib import Path

API_KEY = open(Path.home() / ".config/plane/api_key").read().strip()
BASE = "http://localhost:8080/api/v1"
WORKSPACE = "ugly-code-llc"
BACKLOG_PROJECT = "d3f71a25-17da-490b-afe7-a0eea21488e9"
ALFRED_ID = "12c5c442-d3b0-44ab-a9fe-8b9937096e7b"
HEADERS = {"X-API-Key": API_KEY}


def get_states():
    """Get project states."""
    r = requests.get(f"{BASE}/workspaces/{WORKSPACE}/projects/{BACKLOG_PROJECT}/states/", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data if isinstance(data, list) else [])


def get_todo_state_id():
    """Find the Todo state ID."""
    states = get_states()
    for s in states:
        if s.get("name", "").lower() == "todo":
            return s["id"]
    return None


def get_done_state_id():
    """Find the Done state ID."""
    states = get_states()
    for s in states:
        if s.get("name", "").lower() == "done":
            return s["id"]
    return None


def get_actionable_issues():
    """Get issues assigned to Alfred in Todo state."""
    todo_id = get_todo_state_id()
    if not todo_id:
        return []

    r = requests.get(
        f"{BASE}/workspaces/{WORKSPACE}/projects/{BACKLOG_PROJECT}/issues/",
        headers=HEADERS,
    )
    r.raise_for_status()
    issues = r.json().get("results", [])

    actionable = []
    for issue in issues:
        state_id = issue.get("state")
        assignees = issue.get("assignees", [])

        if state_id == todo_id and ALFRED_ID in assignees:
            actionable.append(issue)

    return actionable


def get_comments(issue_id):
    """Get all comments on an issue."""
    r = requests.get(
        f"{BASE}/workspaces/{WORKSPACE}/projects/{BACKLOG_PROJECT}/issues/{issue_id}/comments/",
        headers=HEADERS,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results", data if isinstance(data, list) else [])
    return results


def mark_done(issue_id):
    """Move issue to Done state."""
    done_id = get_done_state_id()
    if not done_id:
        return False
    r = requests.patch(
        f"{BASE}/workspaces/{WORKSPACE}/projects/{BACKLOG_PROJECT}/issues/{issue_id}/",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"state": done_id},
    )
    return r.status_code == 200


def main():
    parser = argparse.ArgumentParser(description="Backlog issue handler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    issues = get_actionable_issues()

    if not issues:
        output = {"actionable": [], "count": 0}
        print(json.dumps(output, indent=2))
        return

    results = []
    for issue in issues:
        comments = get_comments(issue["id"])
        comment_texts = []
        for c in comments:
            body = c.get("comment_html", c.get("comment", ""))
            actor = c.get("actor_detail", {}).get("display_name", "unknown")
            comment_texts.append({"author": actor, "body": body})

        results.append({
            "issue_id": issue["id"],
            "title": issue.get("name", ""),
            "description": issue.get("description_html", issue.get("description", "")),
            "comments": comment_texts,
            "assignees": issue.get("assignees", []),
            "created_at": issue.get("created_at", ""),
        })

    output = {"actionable": results, "count": len(results)}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
