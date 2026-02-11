"""
Vault Maintenance Pipeline Workflow

6-step nightly pipeline for Alfred's Obsidian knowledge base.
Schedule: 1am daily Europe/Budapest
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        spawn_agent, run_script, notify_slack, ping_uptime,
        save_json_state, SpawnResult, ScriptResult,
    )

import json

VAULT = "/Users/administrator/alfred/alfred"
STATE_FILE = "/Users/administrator/clawd/.vault-maintenance-state.json"

CONVERSATION_EXTRACTION_TASK = f"""CONVERSATION EXTRACTION

Extract structured information from conversation archives into the Alfred KB vault.

1. Check /Users/administrator/clawd/.last_conversation_extraction for last run timestamp.
2. Find conversations in {VAULT}/_archive/conversations/ newer than last extraction.
3. If none new, report "No new conversations" and update timestamp.
4. For new conversations: extract entities following STRICT ontology.
5. CRITICAL: Search before creating — no duplicates.
6. Write new entities with proper frontmatter.
7. Update tracking file.

Report: conversations checked, entities extracted."""

FIXES_TASK = f"""VAULT STRUCTURAL FIXES

Find and fix 10 files in {VAULT} with structural issues.
Check: missing/broken YAML frontmatter, wrong type fields, files in wrong folders, empty stubs.
Use `find {VAULT} -name "*.md" -type f | shuf | head -20` for random files.
Fix in-place using FULL PATHS."""

INTERLINKING_TASK = f"""VAULT INTERLINKING

Add 20 meaningful wikilinks between related entities in {VAULT}.
1. Pick 10 recently modified entities
2. Identify related entities that should be linked
3. Add [[wikilinks]] in body + update related: frontmatter
4. Only meaningful links
Use FULL PATHS."""


@workflow.defn
class VaultMaintenanceWorkflow:
    @workflow.run
    async def run(self) -> str:
        results = []
        failures = []

        await workflow.execute_activity(
            notify_slack, args=["🔧 Vault Maintenance Pipeline starting (6 steps)..."],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 1: Conversation Extraction
        r = await self._spawn_step("Conversation Extraction", CONVERSATION_EXTRACTION_TASK, "kb-curator", 300)
        (results if r[0] else failures).append(r)
        if r[0]:
            await workflow.execute_activity(ping_uptime, args=["conv-extraction"], start_to_close_timeout=timedelta(seconds=15))

        # Step 2: Ontology Scan
        r = await self._ontology_scan()
        (results if r[0] else failures).append(r)
        if r[0]:
            await workflow.execute_activity(ping_uptime, args=["vault-ontology"], start_to_close_timeout=timedelta(seconds=15))

        # Step 3: Enrichment
        r = await self._enrichment()
        (results if r[0] else failures).append(r)

        # Step 4: Fixes
        r = await self._spawn_step("Fixes", FIXES_TASK, "kb-curator", 300)
        (results if r[0] else failures).append(r)

        # Step 5: KB Sync
        r = await self._kb_sync()
        (results if r[0] else failures).append(r)
        if r[0]:
            await workflow.execute_activity(ping_uptime, args=["kb-sync"], start_to_close_timeout=timedelta(seconds=15))

        # Step 6: Interlinking
        r = await self._spawn_step("Interlinking", INTERLINKING_TASK, "kb-curator", 300)
        (results if r[0] else failures).append(r)

        # Summary
        passed = sum(1 for r in results + failures if r[0])
        failed = sum(1 for r in results + failures if not r[0])
        lines = [f"Vault Maintenance: ✅ {passed}/{passed+failed}"]
        for ok, name, msg in results:
            lines.append(f"  ✓ {name}: {msg[:80]}")
        for ok, name, msg in failures:
            lines.append(f"  ✗ {name}: {msg[:80]}")
        summary = "\n".join(lines)

        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] vault-maintenance\n{summary}"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        from datetime import datetime as dt
        state = {
            "last_run": dt.now().isoformat(),
            "steps": {name: {"success": ok, "output": msg[:200]} for ok, name, msg in results + failures},
        }
        await workflow.execute_activity(
            save_json_state, args=[STATE_FILE, state],
            start_to_close_timeout=timedelta(seconds=10),
        )

        if failures:
            raise workflow.ApplicationError(f"{failed} steps failed")
        return summary

    async def _spawn_step(self, name: str, task: str, agent: str, timeout: int) -> tuple:
        try:
            result: SpawnResult = await workflow.execute_activity(
                spawn_agent, args=[task, agent, timeout],
                start_to_close_timeout=timedelta(seconds=timeout + 120),
                heartbeat_timeout=timedelta(seconds=60),
            )
            if result.success:
                return (True, name, result.output[:500])
            await workflow.execute_activity(
                notify_slack, args=[f"❌ {name} FAILED: {result.output[:200]}"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return (False, name, result.output[:500])
        except Exception as e:
            return (False, name, str(e)[:500])

    async def _ontology_scan(self) -> tuple:
        name = "Ontology Scan"
        scan: ScriptResult = await workflow.execute_activity(
            run_script,
            args=[
                "cd /Users/administrator/clawd/scripts && source time-tracker/.venv/bin/activate && "
                "python3 vault-ontology-scanner.py --json > /tmp/vault-ontology-scan.json 2>/dev/null && "
                "python3 -c \"import json; d=json.load(open('/tmp/vault-ontology-scan.json')); "
                "from collections import Counter; issues=d.get('issues',[]); "
                "cats=Counter(i.get('category','?') for i in issues); "
                "by_cat={}; "
                "[by_cat.setdefault(i.get('category','?'),[]).append(i) for i in issues if len(by_cat.get(i.get('category','?'),[]))<5]; "
                "print(json.dumps({'total':len(issues),'counts':dict(cats),'samples':by_cat}))\""
            ],
            start_to_close_timeout=timedelta(seconds=300),
        )
        if not scan.success:
            return (False, name, f"Scanner failed: {scan.output[:200]}")
        try:
            summary = json.loads(scan.output)
        except Exception:
            return (False, name, f"Parse error: {scan.output[:200]}")

        total = summary.get("total", 0)
        if total == 0:
            return (True, name, "Clean — no issues")

        summary_json = json.dumps(summary, indent=2)[:8000]
        task = f"""VAULT ONTOLOGY FIX

Scanner found {total} issues. Fix from this summary:

```json
{summary_json}
```

Full scan at /tmp/vault-ontology-scan.json.
DUPLICATES→merge, BROKEN YAML→fix, MISSING TYPE→add, MISMATCHES→move/fix.
Use FULL PATHS (vault at {VAULT})."""
        return await self._spawn_step(name, task, "kb-curator", 300)

    async def _enrichment(self) -> tuple:
        name = "Enrichment"
        thin: ScriptResult = await workflow.execute_activity(
            run_script,
            args=["/Users/administrator/clawd/scripts/find-thin-entities.sh | head -10"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if not thin.success or not thin.output.strip():
            return (True, name, "No thin entities found")

        task = f"""VAULT ENRICHMENT

Thin entities (<200 words):

{thin.output}

Pick 5. For each: read file (FULL PATH under {VAULT}/), web search, add facts/dates/relationships/citations, expand to 300+ words."""
        return await self._spawn_step(name, task, "kb-curator", 600)

    async def _kb_sync(self) -> tuple:
        name = "KB Sync"
        result: ScriptResult = await workflow.execute_activity(
            run_script,
            args=["python3 /Users/administrator/clawd/scripts/kb-sync.py 2>&1"],
            start_to_close_timeout=timedelta(seconds=2400),
        )
        return (result.success, name, result.output[:500])
