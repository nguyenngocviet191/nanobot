"""Agents monitoring command for nanobot management dashboard."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.bus.events import OutboundMessage
from nanobot.command.router import CommandContext


def get_agents_status(workspace_path: Path) -> list[dict[str, Any]]:
    """Get status of all agents based on session activity."""
    sessions_dir = workspace_path / "sessions"
    
    if not sessions_dir.exists():
        return []
    
    agents = []
    now = datetime.now()
    
    for session_file in sessions_dir.glob("*.jsonl"):
        try:
            with open(session_file, encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    data = json.loads(first_line)
                    if data.get("_type") == "metadata":
                        updated_at_str = data.get("updated_at")
                        if updated_at_str:
                            updated_at = datetime.fromisoformat(updated_at_str)
                            age_seconds = (now - updated_at).total_seconds()
                            
                            if age_seconds < 300:
                                status = "🟢 online"
                            elif age_seconds < 3600:
                                status = "🟡 away"
                            else:
                                status = "⚫ offline"
                            
                            key = data.get("key", session_file.stem.replace("_", ":", 1))
                            channel = key.split(":")[0] if ":" in key else key
                            
                            agents.append({
                                "channel": channel,
                                "status": status,
                                "last_seen": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                                "age": _format_age(age_seconds)
                            })
        except Exception:
            continue
    
    return sorted(agents, key=lambda x: x["channel"])


def get_active_tasks(workspace_path: Path) -> list[dict[str, Any]]:
    """Get active cron jobs/tasks."""
    cron_path = workspace_path / "cron" / "jobs.json"
    
    if not cron_path.exists():
        return []
    
    try:
        with open(cron_path, encoding="utf-8") as f:
            data = json.load(f)
        
        tasks = []
        for job in data.get("jobs", []):
            state = job.get("state", {})
            next_run = state.get("nextRunAtMs")
            
            tasks.append({
                "name": job.get("name", "unknown"),
                "enabled": "✅" if job.get("enabled") else "❌",
                "schedule": _format_schedule(job.get("schedule", {})),
                "next_run": datetime.fromtimestamp(next_run/1000).strftime("%Y-%m-%d %H:%M") if next_run else "N/A",
            })
        return tasks
    except Exception:
        return []


def _format_age(seconds: float) -> str:
    """Format age in human readable format."""
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds/3600)}h ago"
    else:
        return f"{int(seconds/86400)}d ago"


def _format_schedule(schedule: dict) -> str:
    """Format schedule in human readable format."""
    kind = schedule.get("kind")
    if kind == "every":
        ms = schedule.get("everyMs", 0)
        if ms >= 3600000:
            return f"every {ms/3600000}h"
        elif ms >= 60000:
            return f"every {ms/60000}m"
        else:
            return f"every {ms/1000}s"
    elif kind == "cron":
        return f"cron: {schedule.get('expr', '')}"
    return kind or "unknown"


def build_agents_content(workspace_path: Path) -> str:
    """Build text content for agents dashboard."""
    lines = ["🤖 Nanobot Management Dashboard", ""]
    
    # Agent status
    agents = get_agents_status(workspace_path)
    if agents:
        lines.append("📡 Agent Status")
        lines.append("-" * 40)
        for agent in agents:
            lines.append(f"{agent['status']} {agent['channel']} — {agent['last_seen']} ({agent['age']})")
        lines.append("")
    else:
        lines.append("📡 Agent Status: No agents found")
        lines.append("")
    
    # Active tasks
    tasks = get_active_tasks(workspace_path)
    if tasks:
        lines.append("📋 Active Tasks / Cron Jobs")
        lines.append("-" * 40)
        for task in tasks:
            lines.append(f"{task['enabled']} {task['name']} — {task['schedule']} → {task['next_run']}")
        lines.append("")
    else:
        lines.append("📋 Active Tasks: None")
        lines.append("")
    
    return "\n".join(lines)


async def cmd_agents(ctx: CommandContext) -> OutboundMessage:
    """Show agents status dashboard."""
    # Get workspace from loop context
    workspace_path = ctx.loop.workspace
    
    content = build_agents_content(workspace_path)
    
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content=content,
        metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
    )
