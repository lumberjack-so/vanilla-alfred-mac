# Email Handling - AgentMail Integration

**Purpose:** Handle incoming emails via AgentMail with authorization checks.

## Architecture

```
AgentMail → Webhook (via Tailscale) → Relay (port 18790) 
  → OpenClaw Hook → email-processor.py → Authorization Check
    → Authorized: Wake Alfred
    → Unauthorized: Auto-reply + Create backlog issue
```

## Authorization

**Only authorized senders trigger Alfred directly.**

Configured in: `~/.openclaw/authorization.json`

```json
{
  "version": "1.0",
  "authorizedEmails": [
    "user@example.com"
  ]
}
```

## Email Processor

Located: `~/clawd/scripts/email-processor.py`

**What it does:**
1. Fetch unread messages from AgentMail
2. Check sender against authorization list
3. **Authorized**: Output for Alfred to handle
4. **Unauthorized**: Auto-reply + create Plane backlog issue

**Run manually:**
```bash
export AGENTMAIL_API_KEY="$(cat ~/.config/agentmail/api_key)"
python3 ~/clawd/scripts/email-processor.py
```

## Responding to Emails

Use the agentmail skill to send replies:

```python
import os
import subprocess

def send_email_reply(to, subject, body, in_reply_to=None):
    """Send email via AgentMail."""
    api_key = open(os.path.expanduser("~/.config/agentmail/api_key")).read().strip()
    
    script = os.path.expanduser("~/clawd/skills/agentmail/scripts/send_email.py")
    
    env = os.environ.copy()
    env["AGENTMAIL_API_KEY"] = api_key
    
    subprocess.run([
        "python3", script,
        "--to", to,
        "--subject", subject,
        "--body", body
    ], env=env)
```

## Webhook Setup

**Relay server:** `~/clawd/scripts/agentmail-relay.py`

Listens on port 18790 and forwards to OpenClaw with proper auth.

**Start relay:**
```bash
nohup python3 ~/clawd/scripts/agentmail-relay.py > ~/clawd/logs/agentmail-relay.log 2>&1 &
```

**Tailscale funnel:**
```bash
tailscale funnel --bg --https 8443 18790
```

**AgentMail webhook URL:**
```
https://{your-machine}.ts.net:8443/webhook
```

## Email Transform Hook

Located: `~/.openclaw/hooks/email-notify.ts`

Transforms webhook payload into agent message:

```typescript
export default function transform(payload: any) {
  const { from, subject, preview, message_id } = payload;
  
  // Check authorization
  const authorized = checkAuthorization(from);
  
  if (authorized) {
    return {
      message: `Email from authorized sender: ${from}\n\nSubject: ${subject}\n\n${preview}`,
      metadata: {
        messageId: message_id,
        from: from,
        subject: subject
      }
    };
  } else {
    // Handle via backlog
    return null;  // Don't wake Alfred
  }
}
```

## Backlog Workflow

For unauthorized emails:

1. **Auto-reply** sent to sender
2. **Plane issue** created in Backlog project
3. **Logged** to Slack #alfred-logs
4. **No action** until human reviews

## Authorization Management

**Add authorized email:**
```bash
# Edit authorization.json
cat > ~/.openclaw/authorization.json <<EOF
{
  "version": "1.0",
  "authorizedEmails": [
    "user@example.com",
    "newuser@example.com"
  ],
  "lastModified": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

**Check authorization:**
```bash
python3 ~/clawd/scripts/email-processor.py --check-only
```

## Email Templates

**Auto-reply for unauthorized senders:**
```
Thank you for your email. I've flagged this for review and will get back to you if needed.

— Alfred
Digital Butler
```

**Authorized sender response:**
```
Hi {name},

{custom response}

Best regards,
Alfred
On behalf of {owner}
```

## Best Practices

1. **Keep authorization list small** - Only trusted senders
2. **Review backlog daily** - Check unauthorized emails
3. **Use templates** - Consistent, professional responses
4. **Log everything** - Track all email interactions
5. **Test webhooks** - Verify Tailscale funnel is active

## Troubleshooting

**Emails not arriving:**
```bash
# Check relay is running
pgrep -f agentmail-relay.py

# Check Tailscale funnel
tailscale funnel status

# Test webhook manually
curl -X POST https://{your-machine}.ts.net:8443/webhook \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","subject":"Test","preview":"Test message"}'
```

**Check logs:**
```bash
tail -f ~/clawd/logs/agentmail-relay.log
tail -f ~/.openclaw/logs/gateway.log
```

## AgentMail API

**Inbox ID:** Your alfred@agent.yourdomain.com
**API Base:** https://api.agentmail.to/v0
**Docs:** https://docs.agentmail.to

**Python client:**
```bash
pip install agentmail
```

```python
from agentmail import AgentMail
client = AgentMail(api_key="your_key")

# List messages
messages = client.inboxes.messages.list(inbox_id="your_inbox")

# Send message
client.inboxes.messages.send(
    inbox_id="your_inbox",
    to="recipient@example.com",
    subject="Hello",
    text="Message body"
)
```
