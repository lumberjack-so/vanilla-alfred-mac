"""
Backlog Issue Handler Workflow

Check Plane for backlog issues assigned to Alfred in Todo state.
Schedule: every 15 minutes
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import run_script, spawn_agent, notify_slack, ScriptResult, SpawnResult


TASK = """BACKLOG CHECK: Run `python3 ~/clawd/scripts/backlog-handler.py` to check for Plane Backlog issues assigned to Alfred in Todo state. If any found, read issue details + comments, handle the request (reply via AgentMail if email task), then mark Done. Log all actions to #alfred-logs (C0ACVH414JC)."""


@workflow.defn
class BacklogHandlerWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent,
            args=[TASK, "alfred", 120],
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=60),
        )

        if result.success and ("no actionable" in result.output.lower() or "heartbeat_ok" in result.output.lower()):
            return "No backlog issues"

        if result.success:
            await workflow.execute_activity(
                notify_slack, args=[f"[WORKFLOW] Backlog Handler\n{result.output[:300]}"],
                start_to_close_timeout=timedelta(seconds=30),
            )
        return result.output[:500] if result.success else f"Failed: {result.output[:200]}"
