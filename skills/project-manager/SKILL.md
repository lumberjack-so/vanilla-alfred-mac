---
name: project-manager
description: Orchestrates complex tasks by classifying user prompts, matching them to projects, delegating to subagents, and tracking progress in Plane PM and the Obsidian vault.
---

# Project Manager

## Overview

This skill enables Alfred to act as a project orchestrator, managing the full lifecycle of complex tasks from initial request to completion, leveraging subagents, Plane PM, and the Obsidian vault for tracking and knowledge retention.

## Core Capabilities

### 1. Prompt Classification
Automatically analyzes incoming user prompts to determine:
- **Domain:** Content, Coding, Architecture, Infrastructure, Finance, Vault, Operations, Briefing, General.
- **Complexity:** Quick, Medium, Substantial.
- **Action Type:** Question, Task, Discussion, Report.

This classification is crucial for intelligent routing and delegation.

### 2. Project Matching
Matches classified prompts to existing projects within the Obsidian vault (and subsequently, Plane PM). This ensures continuity and proper context for ongoing work.

### 3. Delegation to Subagents
Based on domain, complexity, and project context, delegates tasks to the most appropriate specialized subagent:
- `content-agent`: Writing, blogs, social content
- `coding-agent`: Development, debugging, scripts
- `ops-guardian`: System health, monitoring, maintenance
- `finance-auditor`: Invoices, expenses, financial analysis
- `kb-curator`: Vault organization, entity enrichment
- `briefing-butler`: Daily briefings, summaries, reports

### 4. Authorization Enforcement
Verifies that requests originate from authorized sources before initiating actions. Unauthorized requests are moved to a backlog for review.

### 5. Session & Task Tracking
Integrates with workbench sessions to:
- Create a Plane PM issue when a focus session starts (status: "in progress")
- Close the corresponding Plane PM issue when completed (status: "done")
- Records session details and associated Plane PM IDs

### 6. Artifact & Knowledge Retention
Ensures that all significant outputs, decisions, and learnings from completed sessions are properly recorded as vault events and linked within the Obsidian knowledge graph.

### 7. Plane PM Polling
Continuously monitors Plane PM for tasks that transition to a "todo" state, indicating readiness for Alfred to act upon them.

## Usage Workflow

### Quick Start: Decision Loop

The decision loop script integrates all PM capabilities:

```bash
# Process any incoming message with full routing logic
python3 ~/clawd/scripts/decision-loop.py process "user message" \
    --source slack --sender <USER_ID>

# Example: Delegated to subagent
python3 ~/clawd/scripts/decision-loop.py process "Write a blog post" \
    --source slack --sender <USER_ID> --json

# Example: Quick question (handled directly)
python3 ~/clawd/scripts/decision-loop.py process "What time is the meeting?" \
    --source slack --sender <USER_ID> --json

# Example: Unknown sender (goes to backlog)
python3 ~/clawd/scripts/decision-loop.py process "Help with coding" \
    --source email --sender stranger@example.com --json
```

The decision loop automatically:
1. Classifies the prompt (domain, complexity, action type)
2. Checks authorization
3. Matches to a project in the vault
4. Determines route: `quick`, `immediate`, or `backlog`
5. Selects the appropriate subagent if delegation needed
6. Logs the decision

### Decision Loop Response Structure

```json
{
  "decision": {
    "authorized": true,
    "route": "immediate",
    "subagent": "coding-agent",
    "classification": {
      "domain": "coding",
      "complexity": "substantial",
      "action": "task"
    },
    "session_id": "abc12345"
  },
  "action": "delegate",
  "subagent_command": {
    "agent": "coding-agent",
    "prompt": "...",
    "session_id": "abc12345"
  }
}
```

### Manual Workflow (Individual Scripts)

1.  **Classify Prompt:** Use `scripts/prompt-classifier.py classify "<prompt>"`
2.  **Match Project:** Use `scripts/prompt-classifier.py match "<prompt>"`
3.  **Check Authorization:** Use `scripts/delegation-engine.py check-auth --source <source> --sender <sender_id>`
4.  **Delegate or Act:** Use `scripts/delegation-engine.py delegate "<prompt>" --source <source> --sender <sender_id>`
5.  **Track Progress:** Monitor Plane PM via polling
6.  **Record Outcomes:** Use `workbench-session.py complete` to create vault events

## Resources

### scripts/
- **`decision-loop.py`**: Main orchestration script (recommended entry point)
- `prompt-classifier.py`: Analyzes user input
- `delegation-engine.py`: Manages subagent delegation and authorization
- `vault-plane-sync.py`: Bidirectional sync between vault and Plane PM
- `plane_client.py`: Plane PM API client
- `plane-check.py`: Quick task status checker
- `plane-poll.py`: Cron-based polling for new tasks
- `workbench-session.py`: Session lifecycle management

## Testing

Run the test suite to validate all scenarios:

```bash
python3 ~/clawd/scripts/test-decision-loop.py --verbose
```
