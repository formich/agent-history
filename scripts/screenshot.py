"""Render docs/screenshot.svg from a fake, generated set of sessions.

    uv run --with 'textual>=1.0' python scripts/screenshot.py [query]

No real conversation data is used: everything below is invented.
"""
import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKE_HOME = "/home/alex"

SESSIONS = [
    # (hours ago, duration min, cwd, branch, title, [(role, text), ...])
    (1, 35, "code/shop-api", "fix/rate-limit-429", "Rate limiter returns 429 too early",
     [("u", "Users report 429s on /v2/orders even under the limit. Can you find out why?"),
      ("a", "The limiter keys on `X-Forwarded-For`, but behind the load balancer every request "
            "shares the LB's IP. I'll switch the key to the authenticated client id and add a test."),
      ("u", "Good. Also make the window configurable per plan."),
      ("a", "Done: `RATE_LIMIT_WINDOW` now comes from the plan table. **12 tests pass**, including "
            "a new one for burst traffic."),
      ("u", "Open a PR please")]),
    (3, 20, "code/worktrees/web-dashboard/charts-dark-mode", "feat/charts-dark-mode",
     "Dark mode for dashboard charts",
     [("u", "Charts are unreadable in dark mode, axis labels disappear"),
      ("a", "Axis and grid colors were hard-coded to `#333`. I moved them to theme tokens and "
            "checked contrast on both surfaces.")]),
    (5, 50, "code/infra", "main", "Terraform plan shows drift on S3 buckets",
     [("u", "terraform plan wants to recreate the logs bucket, why?"),
      ("a", "Someone enabled object lock from the console. I imported the setting into state "
            "instead of recreating the bucket.")]),
    (8, 10, "", "", "Explain Python asyncio TaskGroup",
     [("u", "What's the difference between asyncio.gather and TaskGroup?"),
      ("a", "`TaskGroup` cancels the remaining tasks as soon as one fails, and raises an "
            "`ExceptionGroup`. `gather` keeps going unless you pass `return_exceptions=False`...")]),
    (26, 90, "code/shop-api", "feat/webhooks", "Webhook retries with exponential backoff",
     [("u", "Add retries to outgoing webhooks, max 5 attempts"),
      ("a", "Implemented with jittered exponential backoff, persisted in the jobs table so "
            "retries survive a restart.")]),
    (30, 15, "dotfiles", "main", "zsh startup is slow",
     [("u", "My shell takes 2 seconds to start"),
      ("a", "`nvm` is loaded eagerly. I made it lazy: startup is now 140 ms.")]),
    (52, 40, "code/worktrees/web-dashboard/csv-export", "feat/csv-export", "CSV export for reports",
     [("u", "Users want to export the monthly report as CSV"),
      ("a", "Added an export button that streams rows, so large reports don't load in memory.")]),
    (75, 25, "code/infra", "chore/k8s-1-31", "Upgrade cluster to Kubernetes 1.31",
     [("u", "Plan the k8s upgrade for staging"),
      ("a", "Two deprecated APIs are still in use (`flowcontrol/v1beta3`). Here's the plan...")]),
    (100, 60, "code/mobile-app", "fix/push-ios", "Push notifications missing on iOS",
     [("u", "iOS users don't get push notifications since Friday"),
      ("a", "The APNs certificate expired on Friday. I added a check that alerts 30 days ahead.")]),
    (170, 30, "code/shop-api", "main", "Slow query on orders list",
     [("u", "GET /orders takes 4s for big customers"),
      ("a", "Missing composite index on `(customer_id, created_at)`. Down to 80 ms.")]),
    (200, 20, "code/old-prototype", "main", "Prototype auth flow",
     [("u", "Sketch a magic-link login"), ("a", "Here's a minimal version with signed tokens.")]),
    (400, 45, "code/web-dashboard", "main", "Set up Playwright tests",
     [("u", "Add end-to-end tests for login and billing"),
      ("a", "Added Playwright with two specs and a CI job.")]),
]
CODEX = {"Rate limiter returns 429 too early", "zsh startup is slow", "Upgrade cluster to Kubernetes 1.31"}
PI = {"Explain Python asyncio TaskGroup", "Prototype auth flow"}
STARRED = {"Webhook retries with exponential backoff": "★ Webhooks v2 design"}
MISSING = {"code/old-prototype"}


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build(tmp: Path) -> None:
    now = datetime.now(timezone.utc)
    for hours, minutes, rel, branch, title, msgs in SESSIONS:
        cwd = f"{FAKE_HOME}/{rel}".rstrip("/")
        sid = str(uuid.uuid4())
        end = now - timedelta(hours=hours)
        start = end - timedelta(minutes=minutes)
        step = (end - start) / max(1, len(msgs) - 1)
        if title in PI:
            write_pi(tmp, sid, cwd, title, msgs, start, step)
            continue
        if title in CODEX:
            write_codex(tmp, sid, cwd, branch, title, msgs, start, step)
            continue
        folder = tmp / "claude" / "projects" / cwd.replace("/", "-")
        folder.mkdir(parents=True, exist_ok=True)
        lines = [{"type": "ai-title", "aiTitle": title, "sessionId": sid}]
        if title in STARRED:
            lines.append({"type": "custom-title", "customTitle": STARRED[title][2:], "sessionId": sid})
        for n, (role, text) in enumerate(msgs):
            ts = iso(start + step * n)
            if role == "u":
                lines.append({"type": "user", "timestamp": ts, "cwd": cwd, "gitBranch": branch,
                              "sessionId": sid, "message": {"role": "user", "content": text}})
            else:
                lines.append({"type": "assistant", "timestamp": ts, "sessionId": sid,
                              "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": text}]}})
        (folder / f"{sid}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def write_codex(tmp, sid, cwd, branch, title, msgs, start, step):
    day = tmp / "codex" / "sessions" / start.strftime("%Y/%m/%d")
    day.mkdir(parents=True, exist_ok=True)
    lines = [{"timestamp": iso(start), "type": "session_meta",
              "payload": {"id": sid, "cwd": cwd, "source": "cli", "git": {"branch": branch}}}]
    for n, (role, text) in enumerate(msgs):
        kind = "input_text" if role == "u" else "output_text"
        lines.append({"timestamp": iso(start + step * n), "type": "response_item",
                      "payload": {"type": "message", "role": "user" if role == "u" else "assistant",
                                  "content": [{"type": kind, "text": text}]}})
    name = f"rollout-{start:%Y-%m-%dT%H-%M-%S}-{sid}.jsonl"
    (day / name).write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    with open(tmp / "codex" / "session_index.jsonl", "a") as fh:
        fh.write(json.dumps({"id": sid, "thread_name": title}) + "\n")


def write_pi(tmp, sid, cwd, title, msgs, start, step):
    folder = tmp / "pi" / "sessions" / ("--" + cwd.strip("/").replace("/", "-") + "--")
    folder.mkdir(parents=True, exist_ok=True)
    lines = [{"type": "session", "version": 3, "id": sid, "timestamp": iso(start), "cwd": cwd}]
    parent = None
    for n, (role, text) in enumerate(msgs):
        eid = f"{n:08x}"
        content = text if role == "u" else [{"type": "text", "text": text}]
        lines.append({"type": "message", "id": eid, "parentId": parent, "timestamp": iso(start + step * n),
                      "message": {"role": "user" if role == "u" else "assistant", "content": content}})
        parent = eid
    name = f"{start:%Y-%m-%dT%H-%M-%S-000Z}_{sid}.jsonl"
    (folder / name).write_text("\n".join(json.dumps(x) for x in lines) + "\n")


async def shoot(query: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        build(tmp)
        os.environ.update(HOME=FAKE_HOME, CLAUDE_CONFIG_DIR=str(tmp / "claude"),
                          CODEX_HOME=str(tmp / "codex"), PI_CODING_AGENT_DIR=str(tmp / "pi"),
                          XDG_CACHE_HOME=str(tmp / "cache"),
                          AGENT_HISTORY_LANG="en", AGENT_HISTORY_ROOTS="code")
        ch = SourceFileLoader("ah", str(ROOT / "agent-history")).load_module()
        original = ch.enrich

        def enrich(i):  # the fake folders don't exist on this machine
            original(i)
            i["exists"] = not any(m in (i["cwd"] or "") for m in MISSING)

        ch.enrich = enrich
        app = ch.AgentHistory(query)
        async with app.run_test(size=(150, 42)) as pilot:
            await pilot.pause(0.5)
            await pilot.press("down")
            await pilot.pause(0.5)
            out = ROOT / "docs" / ("screenshot.svg" if not query else "screenshot-search.svg")
            out.parent.mkdir(exist_ok=True)
            app.save_screenshot(str(out))
            print("wrote", out)


if __name__ == "__main__":
    asyncio.run(shoot(" ".join(sys.argv[1:])))
