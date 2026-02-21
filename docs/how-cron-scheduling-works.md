# How Cron Scheduling Works in BriefBot

## Overview

BriefBot can schedule recurring research jobs that run automatically via the OS scheduler (Windows Task Scheduler or Unix crontab). Scheduled jobs run the research pipeline headlessly, supplement results with WebSearch via Claude Code CLI, generate a report, and email it.

## How a Job Gets Created

When the user runs:

```
python briefbot.py "AI news" --schedule "0 6 * * *" --email user@example.com
```

Three things happen:

1. **Job record created** in `~/.config/briefbot/jobs.json` — stores topic, schedule, email, flags, and the Python executable path
2. **Cron expression validated** — parsed by `cron_parse.py`, which supports standard 5-field format (minute, hour, day-of-month, month, day-of-week)
3. **Registered with OS scheduler**:
   - **Windows**: Calls `schtasks /Create` to create a Task Scheduler entry
   - **Linux/macOS**: Adds a tagged line to the user's crontab

## How a Scheduled Job Runs

At the scheduled time, the OS executes:

```
python run_job.py <job_id>
```

`run_job.py` does the following:

1. Loads job config from `~/.config/briefbot/jobs.json`
2. Loads API keys from `~/.config/briefbot/.env`
3. Runs the full research pipeline (Reddit/X/YouTube/LinkedIn API calls)
4. Normalizes, scores, deduplicates, and renders results
5. **Invokes Claude Code CLI** (`claude -p --allowedTools WebSearch`) to supplement with web search results
6. Optionally generates an MP3 audio briefing (ElevenLabs or edge-tts)
7. Emails the combined report via SMTP
8. Updates job run status (success/error, run count, last run time)
9. Logs everything to `~/.config/briefbot/logs/<job_id>.log`

## WebSearch via Claude Code CLI

Scheduled jobs invoke `claude -p` (non-interactive print mode) to perform web search. This works as follows:

1. `run_job.py` builds a prompt with the topic, date range, and a summary of existing API results
2. Runs `claude -p --allowedTools WebSearch` with the prompt piped via stdin
3. Claude performs WebSearch and returns structured results
4. Results are appended to the report before saving/emailing

**Requirement**: The `claude` CLI must be installed and on PATH for this to work. If it's not available, the job still runs — it just skips the WebSearch supplement and logs a note.

## Job Management

- `--list-jobs` — shows all registered jobs with status and next run time
- `--delete-job cu_XXXXXX` — removes from both the OS scheduler and the job registry

## Key Files

| File | Purpose |
|---|---|
| `scripts/run_job.py` | Headless job runner, invoked by OS scheduler |
| `scripts/lib/claude_search.py` | Claude Code CLI integration for WebSearch |
| `scripts/lib/scheduler.py` | Registers/unregisters with crontab or schtasks |
| `scripts/lib/jobs.py` | Job registry CRUD (`~/.config/briefbot/jobs.json`) |
| `scripts/lib/cron_parse.py` | Cron expression parser + Windows schtasks translation |
| `scripts/lib/email_sender.py` | SMTP email with markdown-to-HTML |


