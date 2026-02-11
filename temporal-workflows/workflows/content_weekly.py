"""
Content Weekly Workflows

- Alfred Build Log: Monday 7am
- Weekly Roundup: Tuesday 8am
- Build Log Hungarian: Monday 8am

Schedule: separate Temporal schedules
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import spawn_agent, notify_slack, SpawnResult


BUILD_LOG_TASK = """ALFRED'S WEEKLY BUILD LOG

Write and publish this week's build log for lumberjack.so.

1. Read skills/lumberjack-build-log/SKILL.md
2. Review: memory/YYYY-MM-DD.md (past 7 days), #alfred-logs, new skills, cron changes
3. Write 800-1,200 words: main feature, secondary improvements, technical enhancements, learnings, next week
4. Sanitize: remove private family info, financials, internal URLs/creds
5. Add links to published articles and external tools
6. Publish to Ghost (Author: Alfred ID 6841c8c87c66997a44d4690c, Status: published, Newsletter: OFF, Tags: Build Log, Alfred, Building in Public)

Credentials: Ghost ~/.config/ghost/ghost-jwt.sh"""

ROUNDUP_TASK = """LUMBERJACK WEEKLY ROUNDUP & THOUGHT LEADERSHIP

1. Read skills/lumberjack-weekly-roundup/SKILL.md
2. Research: X/Twitter for AI/agents/automation/vibe coding trends, Hacker News front page
3. Select 1-2 timely topics connecting to Lumberjack themes
4. Check Obsidian vault for relevant past notes
5. Form opinion (builder-first, pragmatic + Alfred's dry wit)
6. Write 1,500-2,500 words: provocative title, thesis, context, conventional wisdom, our take, uncomfortable truth, implications
7. Build content roundup table from Ghost posts published in past 7 days
8. Publish to Ghost (Author: Alfred, Status: published, Newsletter: ON, Tags: Weekly Roundup, Thought Leadership, [topic])

Credentials: Ghost ~/.config/ghost/ghost-jwt.sh"""

HUNGARIAN_TASK = """Translate my latest English build log to Hungarian and send to 'alfred-hu' newsletter subscribers.

1. Find most recent build log post (tag: Build Log, from today/yesterday)
2. Translate to natural Hungarian, maintaining voice
3. Send as email-only post (email_only: true) to newsletter slug 'alfred-hu'
4. Do NOT publish to blog
5. Title: 'Alfred Építési Napló - [date in Hungarian]'"""


@workflow.defn
class BuildLogWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[BUILD_LOG_TASK, "content-lumberjack", 300],
            start_to_close_timeout=timedelta(seconds=420),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] Build Log {status}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")


@workflow.defn
class WeeklyRoundupWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[ROUNDUP_TASK, "content-lumberjack", 900],
            start_to_close_timeout=timedelta(seconds=1020),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] Weekly Roundup {status}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")


@workflow.defn
class BuildLogHungarianWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent, args=[HUNGARIAN_TASK, "content-localization", 300],
            start_to_close_timeout=timedelta(seconds=420),
            heartbeat_timeout=timedelta(seconds=60),
        )
        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] Build Log HU {status}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        if result.success:
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")
