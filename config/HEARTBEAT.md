# HEARTBEAT.md — Vault Stewardship

Every 30 minutes, 24/7. Your domain is the Obsidian vault at `~/alfred/alfred` (or your configured vault location).

## Core Mission

My core mission during heartbeats is to ensure infrastructure health AND the vault's health by *delegating* stewardship tasks to the `kb-curator` subagent and focusing on overall system readiness.

**Vault path**: Set `VAULT_PATH` environment variable or update references to `~/alfred/alfred` to your actual vault location.

## Heartbeat Action for Main Agent (Alfred)

During a heartbeat, the main Alfred agent will:

1.  **Run infrastructure health check FIRST:**
    ```bash
    ~/clawd/scripts/infra-health-check.sh
    ```
    If ANY failures are detected:
    - **Docker down:** Restart Docker Desktop (`osascript -e 'quit app "Docker Desktop"'`, wait 5s, `open -a "Docker Desktop"`, wait for daemon)
    - **Temporal containers down:** `cd ~/services/temporal && docker compose up -d`
    - **AutoKitteh down:** `cd ~/services/autokitteh && nohup ak up > ak.log 2>&1 &`
    - **Google OAuth expired:** Alert your human immediately — requires interactive re-auth (`gog auth <your-email>`)
    - **Log all fixes to #alfred-logs** and notify David if anything critical was down
2.  **Check for user input or urgent system events.**
3.  **Verify `kb-curator` cron jobs are enabled and active.** (Vault Ontology Scanner, Skill Read Audit, Vault Enrichment, Vault Fixes, Vault Interlinking, Conversation Extraction, KB Sync Nightly)
4.  **If idle and no urgent tasks, trigger `kb-curator` for an immediate vault audit/enrichment cycle if its last scheduled run was more than 1 hour ago.** This ensures continuous maintenance without waiting for the next cron.

## Delegated Vault Stewardship (handled by `kb-curator` subagent)

The `kb-curator` subagent is responsible for these tasks, executed via its scheduled cron jobs:

| Task | Minimum Output |
|------|----------------|
| **Enrich** | 1 thin entity expanded (< 200 → 300+ words) |
| **Interlink** | 5 new meaningful wikilinks added |
| **Organize** | 3 files fixed (frontmatter, location, or structure) |
| **Research** | 1 new entity created from recent conversations |
| **Audit** | 3 files checked, issues fixed in-place |
| **Projects** | Status updated on 2-3 active projects |
| **Conversation Extraction** | Extract structured info from conversation archives |
| **KB Sync Nightly** | Full vault sync for embedding, clustering, and relationships |

**Task Details (for `kb-curator`):**

*   **Enrich:** `~/clawd/scripts/find-thin-entities.sh | head -5` - Pick one, web search for context, expand with facts, dates, relationships, cite sources.
*   **Interlink:** Pick 3-5 recent entities. Add `[[wikilinks]]` in body text, update `related:` frontmatter.
*   **Organize:** Move files, fix broken/missing frontmatter, address orphans.
*   **Research:** Scan recent conversations for unrecorded topics, create new entities following ontology, search before creating.
*   **Audit:** `find /Users/administrator/alfred/alfred -name "*.md" -type f | awk 'BEGIN{srand()} {print rand()"	"$0}' | sort -n | cut -f2 | head -3` - Check description, dates, links, fix in-place.
*   **Projects (weekly):** `python3 ~/clawd/scripts/project-status.py --active` - Flag stale, update status, move completed/paused.

## Constraints
- **Ontology is fixed** — person, org, proj, evt, loc, learn, doc, acct, asset, proc
- **Cite sources** — When adding facts from research, note where they came from
- **Search before creating** — No duplicates

## State Tracking

Log completed work in `memory/vault-stewardship.json`:
```json
{
  "lastScan": "2026-02-01T07:00:00Z",
  "recentlyImproved": [
    {"file": "person/jane-doe.md", "action": "enriched", "date": "2026-02-01T07:00:00Z"},
    {"file": "391 files", "action": "removed spurious cluster links", "date": "2026-02-01T06:57:00Z"}
  ],
  "stats": {
    "totalEntities": 1410,
    "thinEntities": 6,
    "activeProjects": 29
  }
}
```

No `pendingIssues` — if you found it, you fixed it.

## Plane PM Integration

Check Plane for tasks requiring attention:

```bash
# Quick check for tasks in 'todo' state
python3 ~/clawd/scripts/plane-check.py --todo

# Poll for tasks ready for delegation (tracks state)
python3 ~/clawd/scripts/plane-poll.py --delegate
```

**Automated polling:** Cron job runs every 15 minutes to check for new tasks.

**What to look for:**
- Tasks moved from **backlog → todo** = ready for delegation
- Tasks in **in_progress** with no recent activity = may be stale
- New tasks from external sources (email, etc.) in backlog

**When to act:**
- If a todo task exists and you have capacity, delegate it to the appropriate subagent
- Use `python3 ~/clawd/scripts/delegation-engine.py delegate "task description" --source plane --sender system`
- Sync any significant vault changes to Plane

**Plane URLs:**
- Dashboard: http://localhost:8080 or http://ssd.tail5ec603.ts.net:8080
- Workspace: `ugly-code-llc`

**Webhook (when available):**
- Hook: `~/.openclaw/hooks/plane-state-change.ts`
- Triggers wake on backlog → todo transitions

## Metrics (weekly)
```bash
~/clawd/scripts/vault-health.sh
```
Track: entity counts, link density, thin entity count.

## When the Main Agent (Alfred) Should Reach Out
- Interesting discovery your human should know about
- Question requiring human judgment (merge/delete decisions)
- Significant enrichment worth celebrating

Otherwise, if nothing needs attention, the main agent replies `HEARTBEAT_OK` after ensuring subagent activity.

## Anti-Patterns (for all agents)
❌ "Flagged for later" — Fix it now
❌ "HEARTBEAT_OK" when you could've done work (or delegated it) — Do the work
❌ "Too conservative during quiet hours" — Background work by subagents is always fine
❌ "Checked but didn't change anything" — If nothing needed changing, pick a different task, or ensure subagents are active.
