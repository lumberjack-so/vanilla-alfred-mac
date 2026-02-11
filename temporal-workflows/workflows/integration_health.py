"""
Integration Health Check Workflow

Schedule: 4am daily Europe/Budapest
"""

from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import spawn_agent, notify_slack, ping_uptime, SpawnResult


TASK = """DAILY INTEGRATION HEALTH CHECK

Verify all integrations are healthy:

1) **Whoop**: Run `python3 skills/whoop-health-analysis/scripts/whoop_auth.py status`. If expired/failing, attempt refresh.
2) **Google (gog)**: Test `gog calendar events david@szabostuban.com --from today --to today`.
3) **RescueTime**: Test API call with key from ~/.config/rescuetime/api_key.
4) **Solidtime**: Test API call to list time entries.
5) **1Password CLI**: Run `op whoami --account my.1password.eu`.

Log results to memory/integration-health.log.
DM David (D08U7C4G6TE) only if something is broken."""


@workflow.defn
class IntegrationHealthWorkflow:
    @workflow.run
    async def run(self) -> str:
        result: SpawnResult = await workflow.execute_activity(
            spawn_agent,
            args=[TASK, "ops-guardian", 300],
            start_to_close_timeout=timedelta(seconds=420),
            heartbeat_timeout=timedelta(seconds=60),
        )

        status = "✅" if result.success else "❌"
        await workflow.execute_activity(
            notify_slack,
            args=[f"[WORKFLOW] Integration Health {status}\n{result.output[:200]}"],
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            ping_uptime, args=["int-health"],
            start_to_close_timeout=timedelta(seconds=15),
        )

        if result.success:
            return result.output[:500]
        raise workflow.ApplicationError(f"Failed: {result.output[:200]}")
