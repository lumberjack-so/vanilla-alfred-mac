"""
Shared configuration for all Temporal workflows.

PLACEHOLDERS will be replaced by the install script with actual deployment values.
"""

GATEWAY_URL = "{{GATEWAY_URL}}"
GATEWAY_TOKEN = "{{GATEWAY_TOKEN}}"
TEMPORAL_ADDRESS = "localhost:7233"
TASK_QUEUE = "alfred-workflows"

SLACK_LOGS = "{{SLACK_LOGS_CHANNEL}}"
DAVID_DM = "{{DAVID_DM_CHANNEL}}"

VAULT_PATH = "{{VAULT_PATH}}"

UPTIME_PUSHES = {
    "daily-briefing": "{{UPTIME_KUMA_URL}}/api/push/daily-briefing?status=up&msg=OK",
    "conv-extraction": "{{UPTIME_KUMA_URL}}/api/push/conv-extraction?status=up&msg=OK",
    "vault-ontology": "{{UPTIME_KUMA_URL}}/api/push/vault-ontology?status=up&msg=OK",
    "kb-sync": "{{UPTIME_KUMA_URL}}/api/push/kb-sync?status=up&msg=OK",
    "int-health": "{{UPTIME_KUMA_URL}}/api/push/int-health?status=up&msg=OK",
    "lj-seo-article": "{{UPTIME_KUMA_URL}}/api/push/lj-seo-article?status=up&msg=OK",
    "n8n-tutorial": "{{UPTIME_KUMA_URL}}/api/push/n8n-tutorial?status=up&msg=OK",
    "plane-poll": "{{UPTIME_KUMA_URL}}/api/push/plane-poll?status=up&msg=OK",
}
