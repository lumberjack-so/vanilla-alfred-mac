"""
Plane Task Polling Workflow

Check Plane for tasks in 'todo' state, delegate to subagents.
Schedule: every 15 minutes
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import run_script, spawn_agent, notify_slack, ping_uptime, ScriptResult, SpawnResult


@workflow.defn
class PlanePollingWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: ScriptResult = await workflow.execute_activity(
            run_script,
            args=["python3 /Users/administrator/clawd/scripts/plane-poll.py --delegate 2>&1"],
            start_to_close_timeout=timedelta(seconds=120),
        )

        await workflow.execute_activity(
            ping_uptime, args=["plane-poll"],
            start_to_close_timeout=timedelta(seconds=15),
        )

        if "No tasks" in result.output or not result.output.strip():
            return "No tasks"

        await workflow.execute_activity(
            notify_slack, args=[f"[WORKFLOW] Plane Polling\n{result.output[:300]}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        return result.output[:500]
