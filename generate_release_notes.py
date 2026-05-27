#!/usr/bin/env python3
"""
generate_release_notes.py — Generate CHANGELOG entries from unmerged stage→master commits.

Uses the Claude Agent SDK (Haiku) to group related commits and produce
human-readable release notes, then prepends them to CHANGELOG.md.

Usage:
    python generate_release_notes.py
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone

import jsonschema
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ResultMessage


def log_event(event: str, **kwargs) -> None:
    record = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "event": event,
        **kwargs,
    }
    print(json.dumps(record), file=sys.stderr)


# ── constants ────────────────────────────────────────────────────────────

ALLOWED_TOOLS = [
    "Bash(git log *)",
    "Bash(git fetch origin master:master)",
    "Bash(git show *)",
    "Bash(git diff *)",
    "Bash(git rev-list *)",
]
MAX_TURNS = 10
MODEL = "claude-haiku-4-5"
CHANGELOG_PATH = "CHANGELOG.md"
JIRA_BASE_URL = "https://welltech.atlassian.net/jira/software/c/projects/ECSE/boards/"

RELEASE_NOTES_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "commit_shas"],
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Concise human-readable summary of the change (no ticket ID prefix)",
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Jira ticket ID (e.g. ECSE-1588) if present, omit otherwise",
                    },
                    "commit_shas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "description": "Full 40-char SHA(s) of every commit this item covers",
                    },
                },
            },
        },
    },
}

AGENT_PROMPT = """\
You are a release-notes generator for a Python/AWS Lambda microservice.

Below are the commits on `stage` that have NOT been merged into `master`.
Produce a JSON object matching the provided output schema.

Rules:
- If several commits relate to the same ticket or task (e.g. same ECSE-XXXX prefix, \
or clearly the same logical change like sequential fixes), merge them into ONE item.
- Each `title` must be a concise, human-readable summary — not a raw commit message. \
Do NOT include the ticket ID in the title; put it in the `ticket_id` field instead.
- If the commit message(s) contain a Jira ticket ID (e.g. ECSE-1588), set `ticket_id` \
to that value (e.g. "ECSE-1588"). Omit the field entirely if no ticket is referenced.
- `commit_shas` must list the FULL 40-character SHA of every commit covered by that item.
- You may use the Bash tools to inspect commits further (git log, git show) if needed.
- Do NOT invent commits. Only reference SHAs from the list below.
- Pure formatting/linting commits (e.g. "Apply ruff") should be grouped with the \
nearest related change, or listed as "Code formatting cleanup" if standalone.

Commits (newest first):
{commits_log}

Full SHAs (same order):
{shas_list}
"""


# ── git helpers ──────────────────────────────────────────────────────────


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def fetch_master() -> None:
    log_event("fetch_master", status="start")
    run_git("fetch", "origin", "master:master")
    log_event("fetch_master", status="ok")


def get_unmerged_shas() -> list[str]:
    output = run_git("rev-list", "master..stage")
    return [s for s in output.splitlines() if s]


def get_unmerged_log() -> str:
    return run_git(
        "log",
        "--format=%H %s",
        "master..stage",
    )


# ── agent loop ───────────────────────────────────────────────────────────


async def run_agent(commits_log: str, shas: list[str]) -> tuple[dict, dict]:
    prompt = AGENT_PROMPT.format(
        commits_log=commits_log,
        shas_list="\n".join(shas),
    )

    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=MAX_TURNS,
        allowed_tools=ALLOWED_TOOLS,
        output_format={"type": "json_schema", "schema": RELEASE_NOTES_SCHEMA},
    )

    turn = 0
    result_data = None
    stats: dict = {"turns_used": 0, "cost": None, "is_error": False}

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            turn += 1
            stats["turns_used"] = turn
            usage = message.usage or {}
            log_event(
                "agent_turn",
                turn=turn,
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
            )

        elif isinstance(message, ResultMessage):
            if message.subtype == "success" and message.structured_output:
                result_data = message.structured_output
            else:
                stats["is_error"] = True
            log_event(
                "agent_result",
                subtype=message.subtype,
                total_cost_usd=message.total_cost_usd,
                is_error=message.subtype != "success",
            )
            stats["cost"] = message.total_cost_usd
            stats["turns_used"] = turn

    if result_data is None:
        stats["is_error"] = True
        raise RuntimeError("Agent produced no structured output")

    return result_data, stats


# ── verify ───────────────────────────────────────────────────────────────


def verify(data: dict, shas: list[str]) -> None:
    jsonschema.validate(data, RELEASE_NOTES_SCHEMA)

    covered = set()
    for item in data["items"]:
        for sha in item["commit_shas"]:
            covered.add(sha)

    missing = set(shas) - covered
    if missing:
        short = [s[:7] for s in sorted(missing)]
        raise RuntimeError(f"SHAs not covered by release notes: {short}")


# ── persist ──────────────────────────────────────────────────────────────


def build_section(data: dict) -> str:
    today = date.today().isoformat()
    lines = [f"## {today}", ""]

    # Ticket-linked items first, then unlinked
    items = sorted(
        data["items"], key=lambda x: (not bool(x.get("ticket_id")), x.get("ticket_id") or "")
    )

    for item in items:
        ticket_id = item.get("ticket_id")
        if ticket_id:
            url = f"{JIRA_BASE_URL}{ticket_id}"
            lines.append(f"- [{ticket_id}]({url}) — {item['title']}")
        else:
            lines.append(f"- {item['title']}")

    lines.append("")
    return "\n".join(lines)


def prepend_changelog(section: str) -> None:
    try:
        with open(CHANGELOG_PATH, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = ""

    if existing.startswith("# "):
        first_nl = existing.index("\n")
        header = existing[: first_nl + 1] + "\n"
        body = existing[first_nl + 1 :].lstrip("\n")
    else:
        header = "# Changelog\n\n"
        body = existing

    with open(CHANGELOG_PATH, "w") as f:
        f.write(header + section + body)


# ── main ─────────────────────────────────────────────────────────────────


async def main() -> None:
    start = time.monotonic()
    stats: dict = {}

    try:
        # 1. Pre-check
        fetch_master()
        shas = get_unmerged_shas()
        if not shas:
            log_event("pre_check", status="nothing_to_release")
            sys.exit(1)

        log_event("pre_check", status="ok", unmerged_commits=len(shas))
        commits_log = get_unmerged_log()

        # 2. Agent loop
        data, stats = await run_agent(commits_log, shas)

        # 3. Verify
        verify(data, shas)
        log_event("verify", status="ok", items=len(data["items"]))

        # 4. Persist
        section = build_section(data)
        prepend_changelog(section)
        log_event("persist", status="ok", changelog=CHANGELOG_PATH)

    except Exception as exc:
        stats.setdefault("is_error", True)
        log_event("error", message=str(exc))
        sys.exit(1)

    finally:
        stats["duration_seconds"] = round(time.monotonic() - start, 2)
        cost = stats.get("cost")
        cost_str = f"${cost:.4f}" if cost is not None else "n/a"
        status = "ERROR" if stats.get("is_error") else "ok"
        print(
            f"\n-- FINISHED --\n"
            f" Status:   {status}\n"
            f" Duration: {stats['duration_seconds']}s\n"
            f" Turns:    {stats.get('turns_used', 0)}/{MAX_TURNS}\n"
            f" Cost:     {cost_str}\n"
        )


if __name__ == "__main__":
    asyncio.run(main())
