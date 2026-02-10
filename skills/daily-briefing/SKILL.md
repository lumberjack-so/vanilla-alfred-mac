---
name: daily-briefing
description: Generate a daily briefing covering health, schedule, email digest, and weekly goal progress.
metadata: {"clawdbot":{"emoji":"☀️"}}
---

# Daily Briefing

A concise, butler-style daily briefing. Runs Tuesday through Sunday at 6:05am local time. Monday has its own more comprehensive briefing.

## When to Use

- **Automatic via cron:** Tuesday–Sunday at 6:05am
- **On request:** "daily briefing", "what's today look like", "prep me for today"

## Data Sources

### 1. Weather
```bash
curl -s "wttr.in/<CITY>?format=%C+%t,+feels+%f"
```

### 2. Health Data (if integrated)
If you have a health tracking integration (Whoop, Oura, Apple Health), fetch:
- Today's recovery percentage
- HRV, RHR
- Sleep quality

**If health data fails:** Try once more after 10 seconds. If still failing, note "Health data temporarily unavailable" and continue.

### 3. Today's Calendar
```bash
gog calendar events <email> --from <today-start> --to <today-end> --account <email> --json
```
Focus on TODAY only. Apply ownership rules if multiple calendar sources.

### 4. Tomorrow Preview (brief)
Glance at tomorrow's calendar to mention anything that needs prep.

### 5. Today's Email
```bash
gog gmail search 'newer_than:1d' --max 30 --account <email>
```
Only surface:
- Real humans who emailed
- Revenue notifications
- Critical issues (shutdowns, expirations)

### 6. Finances (if using Stripe)
```bash
STRIPE_KEY=$(cat ~/.config/stripe/api_key)

# Balance
curl -s -u "$STRIPE_KEY:" https://api.stripe.com/v1/balance | \
  jq '{available: .available[0].amount, pending: .pending[0].amount}'

# Open invoices
curl -s -u "$STRIPE_KEY:" "https://api.stripe.com/v1/invoices?status=open" | \
  jq '.data[] | {customer_email, total: (.total/100), due_date: .due_date, status}'
```

Report:
- Current balance (available + pending)
- Any open invoices with amounts and due dates
- Flag overdue invoices

### 7. Weekly Goals
Read from `memory/weekly-goals.md`. Show current status and progress.

## Formatting Rules

### Tone
- Butler-like, warm, unhurried
- Natural prose — full sentences
- Low dopamine — no emojis, no hype
- Shorter than Monday briefing

### Typography
- **Bold** for times, key items, percentages
- *Italic* for emphasis, event names
- Numbers always as digits: **63%**, **6am**, **11:00**

### Length
- Aim for ~300–400 words
- Skip sections if nothing to report

## Output Structure

```markdown
# [Day] Briefing

**[Date]**

[One sentence on weather.]

---

**Your health.** [Recovery %, brief note. 1-2 sentences max.]

---

**Your day.**

[Walk through today's schedule in natural prose. Mention if afternoon/evening is open.]

[Brief note on tomorrow if relevant prep needed.]

---

**Your emails.** [Humans who wrote, revenue, critical issues. If nothing: "Nothing urgent in email today."]

---

**Your finances.** [Balance. Open invoices. If nothing: "No open invoices."]

---

**Your weekly goals.**

This is day [X] of the week. Here's where you stand:

**1.** [Goal 1] — *status*
**2.** [Goal 2] — *status*  
**3.** [Goal 3] — *status*

[Brief encouragement if behind.]

---

**Reward reminder:** [The weekly reward, if goals on track.]

---

[Closing line — "That's your [day], sir." or similar.]
```

## Day-Specific Notes

### Tuesday
- Day 1 of goals — set expectations
- Reference that Monday briefing covered the full week

### Wednesday
- Often a deep work day
- First real check on goal progress

### Thursday
- Mid-week — honest check on progress
- If behind, help problem-solve

### Friday
- End of work week feel
- Push to close out goals before weekend

### Saturday
- Lighter tone, weekend mode
- Still track goals

### Sunday
- Week wrap-up preview
- Final push on incomplete goals

## Delivery

- **Channel:** Direct message to your human
- **Schedule:** Tuesday–Sunday, 6:05am local timezone
- **Cron:** `5 6 * * 2-0`
