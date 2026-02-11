"""
Weekly Goals Workflow

Prompt David to set 3 non-negotiables for the week.
Schedule: Monday 6:05am Europe/Budapest (5 min after briefing)
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import spawn_agent, notify_slack, SpawnResult


TASK = """WEEKLY GOALS PROMPT

It's Monday 6:05am. David just received his Monday Briefing.
Prompt him to set his 3 non-negotiables for the week.
Read the weekly-goals skill first. Keep the prompt short and punchy.
Send to David's Slack DM (D08U7C4G6TE).
Save to memory/weekly-goals.md."""


@workflow.defn
class WeeklyGoalsWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent,
            args=[TASK, "briefing-butler", 120],
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=60),
        )

        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack,
            args=[f"[WORKFLOW] Weekly Goals {status}"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        if result.success:
            return "Goals prompt sent"
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")
