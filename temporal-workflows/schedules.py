"""
Register all Temporal Schedules.

Run once: python3 schedules.py
Re-run to update (deletes + recreates all schedules).

All times in UTC. Budapest = UTC+1 (CET) / UTC+2 (CEST).
February = CET, so 6am Budapest = 5am UTC.
"""

import asyncio
import logging
import sys

from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec, ScheduleCalendarSpec, ScheduleRange, SchedulePolicy, ScheduleOverlapPolicy
from datetime import timedelta

from config import TEMPORAL_ADDRESS, TASK_QUEUE

# Import workflow classes for type references
from workflows.daily_briefing import DailyBriefingWorkflow
from workflows.weekly_goals import WeeklyGoalsWorkflow
from workflows.integration_health import IntegrationHealthWorkflow
from workflows.vault_maintenance import VaultMaintenanceWorkflow
from workflows.content_publishing import N8nTutorialWorkflow, LumberjackSeoWorkflow, SeoEnrichmentWorkflow
from workflows.content_weekly import BuildLogWorkflow, WeeklyRoundupWorkflow, BuildLogHungarianWorkflow
from workflows.plane_polling import PlanePollingWorkflow
from workflows.backlog_handler import BacklogHandlerWorkflow


SCHEDULES = [
    # === DAILY ===
    {
        "id": "daily-briefing",
        "workflow": "DailyBriefingWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 5 * * *"],  # 6am Budapest (UTC+1)
        ),
        "memo": "Daily/Monday briefing at 6am Budapest",
    },
    {
        "id": "integration-health",
        "workflow": "IntegrationHealthWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 3 * * *"],  # 4am Budapest
        ),
        "memo": "Integration health check at 4am Budapest",
    },
    {
        "id": "vault-maintenance",
        "workflow": "VaultMaintenanceWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 0 * * *"],  # 1am Budapest
        ),
        "memo": "Vault maintenance pipeline at 1am Budapest",
    },
    {
        "id": "n8n-tutorial",
        "workflow": "N8nTutorialWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 8 * * *"],  # 9am Budapest
        ),
        "memo": "n8n tutorial at 9am Budapest",
    },
    {
        "id": "lumberjack-seo",
        "workflow": "LumberjackSeoWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 13 * * *"],  # 2pm Budapest
        ),
        "memo": "Lumberjack SEO article at 2pm Budapest",
    },
    {
        "id": "seo-enrichment",
        "workflow": "SeoEnrichmentWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 7,11,15,19 * * *"],  # 8am,12pm,4pm,8pm Budapest
        ),
        "memo": "SEO enrichment 4x daily",
    },

    # === WEEKLY ===
    {
        "id": "weekly-goals",
        "workflow": "WeeklyGoalsWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["5 5 * * 1"],  # Monday 6:05am Budapest
        ),
        "memo": "Weekly goals prompt Monday 6:05am Budapest",
    },
    {
        "id": "build-log",
        "workflow": "BuildLogWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 6 * * 1"],  # Monday 7am Budapest
        ),
        "memo": "Build log Monday 7am Budapest",
    },
    {
        "id": "build-log-hungarian",
        "workflow": "BuildLogHungarianWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 7 * * 1"],  # Monday 8am Budapest
        ),
        "memo": "Build log Hungarian Monday 8am Budapest",
    },
    {
        "id": "weekly-roundup",
        "workflow": "WeeklyRoundupWorkflow",
        "spec": ScheduleSpec(
            cron_expressions=["0 7 * * 2"],  # Tuesday 8am Budapest
        ),
        "memo": "Weekly roundup Tuesday 8am Budapest",
    },

    # === HIGH FREQUENCY ===
    {
        "id": "plane-polling",
        "workflow": "PlanePollingWorkflow",
        "spec": ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(minutes=15))],
        ),
        "memo": "Plane task polling every 15 min",
    },
    {
        "id": "backlog-handler",
        "workflow": "BacklogHandlerWorkflow",
        "spec": ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(minutes=15))],
        ),
        "memo": "Backlog issue handler every 15 min",
    },
]


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    logger = logging.getLogger("schedules")

    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info(f"Connected to Temporal at {TEMPORAL_ADDRESS}")

    # List existing schedules
    existing = set()
    schedules_iter = await client.list_schedules()
    async for s in schedules_iter:
        existing.add(s.id)

    for sched in SCHEDULES:
        sid = sched["id"]
        wf_name = sched["workflow"]

        # Delete if exists
        if sid in existing:
            handle = client.get_schedule_handle(sid)
            await handle.delete()
            logger.info(f"  Deleted existing schedule: {sid}")

        # Create
        await client.create_schedule(
            sid,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    wf_name,
                    id=f"{sid}",
                    task_queue=TASK_QUEUE,
                    execution_timeout=timedelta(hours=2),
                ),
                spec=sched["spec"],
                policy=SchedulePolicy(
                    overlap=ScheduleOverlapPolicy.SKIP,
                ),
            ),
        )
        logger.info(f"  ✅ Created schedule: {sid} ({sched['memo']})")

    logger.info(f"\nDone. {len(SCHEDULES)} schedules registered.")
    logger.info("View at http://localhost:8233/schedules")


if __name__ == "__main__":
    asyncio.run(main())
