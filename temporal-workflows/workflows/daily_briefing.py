"""
Daily Briefing Workflow

Monday: comprehensive briefing (health, calendar, email, finances, weather, news)
Tue-Sun: standard briefing (health, calendar, email, weekly goals)

Schedule: 6am daily Europe/Budapest
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import spawn_agent, notify_slack, ping_uptime, check_day_of_week, SpawnResult


MONDAY_TASK = """MONDAY COMPREHENSIVE BRIEFING

Generate David's Monday morning briefing. Read skills/monday-briefing/SKILL.md and follow precisely.

## DATA TO GATHER
1. **Weather** - Today and week ahead for Budapest
2. **Health** - Whoop data (sleep, recovery, HRV)
3. **Calendar** - Today + week overview
4. **Email** - Important unread, categorized
5. **Finances** - Account balances, pending payments
6. **Currency** - EUR/HUF rate
7. **World News** - 3-4 notable headlines

## FORMAT
Write in natural prose, not bullet lists. Conversational but efficient.
Start with a pithy observation about the day/week ahead.

## DELIVERY
Send to David's Slack DM (D08U7C4G6TE)."""

DAILY_TASK = """DAILY BRIEFING (TUE-SUN)

Generate David's daily morning briefing. Read skills/daily-briefing/SKILL.md and follow precisely.

## DATA TO GATHER
1. **Weather** - Today for Budapest
2. **Health** - Whoop sleep and recovery
3. **Calendar** - Today's events
4. **Email** - Urgent unread only
5. **Weekly Goals** - Read memory/weekly-goals.md, note progress

## FORMAT
Brief, punchy, natural prose.
Start with health/energy observation. End with the day's focus.

## DELIVERY
Send to David's Slack DM (D08U7C4G6TE)."""


@workflow.defn
class DailyBriefingWorkflow:
    @workflow.run
    async def run(self) -> str:
        day = await workflow.execute_activity(
            check_day_of_week, start_to_close_timeout=timedelta(seconds=10)
        )

        is_monday = day == 0
        task = MONDAY_TASK if is_monday else DAILY_TASK
        label = "Monday Briefing" if is_monday else "Daily Briefing"

        await workflow.execute_activity(
            notify_slack,
            args=[f"[WORKFLOW] {label} starting..."],
            start_to_close_timeout=timedelta(seconds=30),
        )

        result: SpawnResult = await workflow.execute_activity(
            spawn_agent,
            args=[task, "briefing-butler", 300],
            start_to_close_timeout=timedelta(seconds=420),
            heartbeat_timeout=timedelta(seconds=60),
        )

        if result.success:
            await workflow.execute_activity(
                notify_slack,
                args=[f"[WORKFLOW] {label} ✅ delivered"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.execute_activity(
                ping_uptime, args=["daily-briefing"],
                start_to_close_timeout=timedelta(seconds=15),
            )
            return f"{label} delivered"
        else:
            await workflow.execute_activity(
                notify_slack,
                args=[f"[WORKFLOW] {label} ❌ failed: {result.output[:200]}"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            raise workflow.ApplicationError(f"{label} failed: {result.output[:200]}")
