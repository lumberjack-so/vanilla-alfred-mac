"""
Content Publishing Workflows

- n8n Tutorial: 9am daily
- Lumberjack SEO Article: 2pm daily
- Lumberjack SEO Enrichment: 8am, 12pm, 4pm, 8pm daily

Schedule: separate Temporal schedules for each
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import spawn_agent, notify_slack, ping_uptime, SpawnResult


N8N_TASK = """N8N TUTORIAL OF THE DAY

Generate and publish today's n8n tutorial to Ghost (lumberjack.so).

## DIFFICULTY ROTATION
Monday=L1, Tuesday=L2, Wednesday=L3, Thursday=L4, Friday=L5, Sat/Sun=Random

## STEPS
1. Query Notion DB 1b03b878b81580eb9509ffc3f4585b3c for next workflow (Code not empty, Source not empty, Checkbox=false, Level matches today)
2. Fetch the n8n.io template page from Source URL
3. Generate 2000-word tutorial following skills/n8n-tutorial-daily/SKILL.md
4. Publish to Ghost as PUBLISHED (Author: Alfred ID 6841c8c87c66997a44d4690c, Tags: n8n + tool names + 'n8n Tutorial of the Day', use ?source=html)
5. Update Notion: Checkbox=true, Landing page=Ghost URL

Credentials: Notion ~/.config/notion/token, Ghost ~/.config/ghost/ghost-jwt.sh"""

SEO_TASK = """LUMBERJACK SEO DAILY ARTICLE

Write and publish today's SEO article for lumberjack.so.

1. Read skills/lumberjack-seo/SKILL.md
2. Get today's article from Google Sheet 1hVyosquVBeiqSJDuQcea94HlJrTfVsLJN3wUEDo6ZuU (Date=today, get Headline/Primary Keyword/Article Type/Words target)
3. Research: recent news, 2-3 sources, YouTube videos, related lumberjack.so articles
4. Write in Alfred voice, SEO optimized, target word count
5. Publish to Ghost (Author: Alfred, Status: published, Newsletter: OFF, Tags: topic + 'SEO')
6. Update Google Sheet: Status='Published', Published URL=Ghost URL

Credentials: Ghost ~/.config/ghost/ghost-jwt.sh, gog CLI david@szabostuban.com"""

SEO_ENRICHMENT_TASK = """LUMBERJACK SEO ENRICHMENT

Read skills/geo-seo/SKILL.md FIRST. Apply GEO/SEO principles.

Enrich 2 existing articles on lumberjack.so for better SEO.

CRITICAL: NEVER delete existing content — only ADD.

What to add: internal links (2-3), external links (1-2), YouTube embeds, updated stats, FAQ section (3-4 questions), meta description, alt text.

Process:
1. Get Ghost JWT: ~/.config/ghost/ghost-jwt.sh
2. List recent published posts, pick 2 not enriched in last 7 days (check ~/clawd/memory/seo-enrichment-log.json)
3. For each: read HTML, find related articles to interlink, web search for resources, add content
4. Update via Ghost API (PUT with ?source=html)
5. Update tracking file ~/clawd/memory/seo-enrichment-log.json
6. VERIFY: word count after >= before"""


@workflow.defn
class N8nTutorialWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[N8N_TASK, "content-lumberjack", 600],
            start_to_close_timeout=timedelta(seconds=720),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] n8n Tutorial {status}\n{result.output[:200]}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            await workflow.execute_activity(ping_uptime, args=["n8n-tutorial"], start_to_close_timeout=timedelta(seconds=15))
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")


@workflow.defn
class LumberjackSeoWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[SEO_TASK, "content-lumberjack", 600],
            start_to_close_timeout=timedelta(seconds=720),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] Lumberjack SEO {status}\n{result.output[:200]}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            await workflow.execute_activity(ping_uptime, args=["lj-seo-article"], start_to_close_timeout=timedelta(seconds=15))
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")


@workflow.defn
class SeoEnrichmentWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[SEO_ENRICHMENT_TASK, "content-lumberjack", 600],
            start_to_close_timeout=timedelta(seconds=720),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] SEO Enrichment {status}\n{result.output[:200]}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")
