"""
Alfred Temporal Worker

Runs all workflow and activity definitions.
Start with: python3 worker.py
"""

import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from config import TEMPORAL_ADDRESS, TASK_QUEUE

# Import all activities
from activities import (
    spawn_agent, run_script, notify_slack, ping_uptime,
    check_day_of_week, load_json_state, save_json_state,
)

# Import all workflows
from workflows.daily_briefing import DailyBriefingWorkflow
from workflows.weekly_goals import WeeklyGoalsWorkflow
from workflows.integration_health import IntegrationHealthWorkflow
from workflows.vault_maintenance import VaultMaintenanceWorkflow
from workflows.content_publishing import N8nTutorialWorkflow, LumberjackSeoWorkflow, SeoEnrichmentWorkflow
from workflows.content_weekly import BuildLogWorkflow, WeeklyRoundupWorkflow, BuildLogHungarianWorkflow
from workflows.plane_polling import PlanePollingWorkflow
from workflows.backlog_handler import BacklogHandlerWorkflow

ALL_WORKFLOWS = [
    DailyBriefingWorkflow,
    WeeklyGoalsWorkflow,
    IntegrationHealthWorkflow,
    VaultMaintenanceWorkflow,
    N8nTutorialWorkflow,
    LumberjackSeoWorkflow,
    SeoEnrichmentWorkflow,
    BuildLogWorkflow,
    WeeklyRoundupWorkflow,
    BuildLogHungarianWorkflow,
    PlanePollingWorkflow,
    BacklogHandlerWorkflow,
]

ALL_ACTIVITIES = [
    spawn_agent,
    run_script,
    notify_slack,
    ping_uptime,
    check_day_of_week,
    load_json_state,
    save_json_state,
]


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("alfred-worker")

    logger.info(f"Connecting to Temporal at {TEMPORAL_ADDRESS}...")
    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info(f"Connected. Starting worker on queue '{TASK_QUEUE}'...")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=ALL_WORKFLOWS,
        activities=ALL_ACTIVITIES,
    )

    logger.info(f"Worker running. {len(ALL_WORKFLOWS)} workflows, {len(ALL_ACTIVITIES)} activities registered.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
