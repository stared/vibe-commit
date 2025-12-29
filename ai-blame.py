#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["typer", "rich"]
# ///
"""
ai-blame: Show AI conversation context for git commits.
"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

app = typer.Typer(
    name="ai-blame",
    help="Show AI conversation context for git commits.",
    add_completion=False,
)
console = Console()


def get_commit_session_id(commit: str) -> Optional[str]:
    """Extract AI-Session-ID from commit message."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit],
            capture_output=True, text=True, check=True,
        )
        match = re.search(r"AI-Session-ID:\s*([a-f0-9-]+)", result.stdout)
        return match.group(1) if match else None
    except subprocess.CalledProcessError:
        return None


def get_project_dir() -> str:
    """Get encoded project directory name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        project_path = result.stdout.strip()
    except subprocess.CalledProcessError:
        project_path = os.getcwd()
    return project_path.replace("/", "-").replace("_", "-")


def find_session_file(session_id: str) -> Optional[Path]:
    """Find the session JSONL file."""
    claude_dir = Path.home() / ".claude" / "projects"
    project_dir = get_project_dir()
    session_file = claude_dir / project_dir / f"{session_id}.jsonl"
    if session_file.exists():
        return session_file
    for proj_dir in claude_dir.iterdir():
        if proj_dir.is_dir():
            candidate = proj_dir / f"{session_id}.jsonl"
            if candidate.exists():
                return candidate
    return None


def get_commit_info(commit: str) -> dict:
    """Get commit metadata."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H%n%s%n%an%n%aI", commit],
            capture_output=True, text=True, check=True,
        )
        lines = result.stdout.strip().split("\n")
        return {"hash": lines[0], "subject": lines[1], "author": lines[2], "date": lines[3]}
    except subprocess.CalledProcessError:
        return {}


def get_commit_timestamp(commit: str) -> Optional[datetime]:
    """Get commit timestamp as datetime."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", commit],
            capture_output=True, text=True, check=True,
        )
        return datetime.fromisoformat(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def get_previous_commit(commit: str) -> Optional[str]:
    """Get the previous commit hash, or None if first commit."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", f"{commit}^"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def get_commit_stats(commit: str) -> dict:
    """Get file change statistics."""
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", f"{commit}^..{commit}"],
            capture_output=True, text=True, check=True,
        )
        stats = {}
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 3:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    stats[parts[2]] = {"added": added, "deleted": deleted}
        return stats
    except subprocess.CalledProcessError:
        return {}


def extract_user_content(message: dict) -> Optional[str]:
    """Extract readable content from user message."""
    content = message.get("content", "")
    if isinstance(content, str):
        if content.startswith("<command-message>"):
            return None
        return content.strip() if content.strip() else None
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if not text.startswith("#"):
                    texts.append(text)
        return "\n".join(texts).strip() if texts else None
    return None


def extract_assistant_content(message: dict) -> list:
    """Extract content from assistant message."""
    content = message.get("content", [])
    results = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    results.append({"type": "text", "content": item.get("text", "")})
                elif item.get("type") == "tool_use":
                    results.append({
                        "type": "tool",
                        "name": item.get("name", ""),
                        "input": item.get("input", {}),
                    })
    return results


def parse_session(session_file: Path, include_responses: bool = False) -> list:
    """Parse session file and extract conversation."""
    messages = []
    with open(session_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            is_meta = entry.get("isMeta", False)
            user_type = entry.get("userType")
            timestamp = entry.get("timestamp", "")

            if entry_type == "user" and user_type == "external" and not is_meta:
                msg = entry.get("message", {})
                content = extract_user_content(msg)
                if content:
                    messages.append({
                        "type": "prompt",
                        "content": content,
                        "timestamp": timestamp,
                        "files_changed": [],
                    })

            elif entry_type == "assistant":
                msg = entry.get("message", {})
                assistant_content = extract_assistant_content(msg)
                for item in assistant_content:
                    if item["type"] == "tool" and item["name"] in ("Edit", "Write"):
                        file_path = item["input"].get("file_path", "")
                        if file_path and messages and messages[-1]["type"] == "prompt":
                            try:
                                rel_path = os.path.relpath(file_path)
                            except ValueError:
                                rel_path = file_path
                            if rel_path not in messages[-1]["files_changed"]:
                                messages[-1]["files_changed"].append(rel_path)

                if include_responses:
                    texts = [i["content"] for i in assistant_content if i["type"] == "text" and i["content"].strip()]
                    if texts:
                        messages.append({"type": "response", "content": "\n".join(texts), "timestamp": timestamp})
    return messages


def format_time(ts: str) -> str:
    """Format timestamp to HH:MM."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, AttributeError):
        return ts[:5] if ts else ""


def format_diff(added: int, deleted: int) -> Text:
    """Format diff stats with colors."""
    t = Text()
    t.append(f"+{added}", style="bold green")
    t.append(" ", style="white")
    t.append(f"-{deleted}", style="bold red")
    return t


@app.command()
def blame(
    commit: str = typer.Argument("HEAD", help="Commit hash or reference"),
    responses: bool = typer.Option(False, "--responses", "-r", help="Include AI responses"),
    all_prompts: bool = typer.Option(False, "--all", "-a", help="Show all prompts from session, not just time-windowed"),
):
    """Show AI conversation context for a git commit."""
    commit_info = get_commit_info(commit)
    if not commit_info:
        console.print(f"[red]Error:[/red] Commit not found: {commit}")
        raise typer.Exit(1)

    session_id = get_commit_session_id(commit)
    if not session_id:
        console.print(f"[red]Error:[/red] No AI-Session-ID in commit {commit}")
        raise typer.Exit(1)

    session_file = find_session_file(session_id)
    if not session_file:
        console.print(f"[red]Error:[/red] Session file not found: {session_id}")
        raise typer.Exit(1)

    # Get time window for this commit
    commit_time = get_commit_timestamp(commit)
    prev_commit = get_previous_commit(commit)
    prev_time = get_commit_timestamp(prev_commit) if prev_commit else None

    commit_stats = get_commit_stats(commit)
    messages = parse_session(session_file, responses)

    # Header: compact single line
    header = Text()
    header.append(commit_info['hash'][:8], style="bold yellow")
    header.append(" ", style="white")
    header.append(commit_info['subject'], style="bold white")
    header.append(" • ", style="dim")
    header.append(commit_info['author'], style="cyan")
    header.append(f" ({commit_info['date'][:10]})", style="dim")
    console.print(header)
    console.print(Text(f"Session: {session_id}", style="dim"))
    console.print()

    # Files table: compact, no borders
    if commit_stats:
        file_table = Table(box=None, padding=(0, 1), show_header=False, pad_edge=False)
        file_table.add_column("File", style="white")
        file_table.add_column("Diff", justify="right")

        total_add, total_del = 0, 0
        for fname, stats in sorted(commit_stats.items()):
            file_table.add_row(fname, format_diff(stats["added"], stats["deleted"]))
            total_add += stats["added"]
            total_del += stats["deleted"]

        console.print(file_table)

        total = Text()
        total.append("Total: ", style="dim")
        total.append_text(format_diff(total_add, total_del))
        console.print(total)
        console.print()

    # Conversation: simple flow, no indentation
    console.print(Text("Prompts", style="bold underline"))
    console.print()

    prompt_num = 0
    for msg in messages:
        if msg["type"] == "prompt":
            # Time-based filtering: show prompts between previous commit and this commit
            if not all_prompts and commit_time:
                msg_time = parse_timestamp(msg["timestamp"])
                if msg_time:
                    # Skip if after this commit
                    if msg_time > commit_time:
                        continue
                    # Skip if before or at previous commit time
                    if prev_time and msg_time <= prev_time:
                        continue

            prompt_num += 1
            time_str = format_time(msg["timestamp"])

            # Header line: number and time
            header = Text()
            header.append(f"#{prompt_num}", style="dim")
            header.append(f" {time_str}", style="dim cyan")
            console.print(header)

            # Content: plain text, no markup interpretation
            console.print(Text(msg["content"], style="white"))

            # Files changed (only those in this commit, for reference)
            files = [f for f in msg.get("files_changed", []) if f in commit_stats]
            if files:
                for f in files:
                    file_line = Text()
                    file_line.append("→ ", style="dim")
                    file_line.append(f, style="bold yellow")
                    s = commit_stats[f]
                    file_line.append(f" +{s['added']}", style="bold green")
                    file_line.append(f" -{s['deleted']}", style="bold red")
                    console.print(file_line)

            console.print()

        elif msg["type"] == "response" and responses:
            time_str = format_time(msg["timestamp"])
            console.print(Text(f"↳ AI {time_str}", style="dim magenta"))
            console.print(Text(msg["content"], style="dim"))
            console.print()

    console.print(Text(f"{prompt_num} prompts • {session_file}", style="dim"))


@app.command()
def session_info():
    """Output current session ID and Claude version for commits."""
    claude_dir = Path.home() / ".claude" / "projects"
    project_path = claude_dir / get_project_dir()

    session_id = None
    session_file = None
    model = "unknown"

    if project_path.exists():
        sessions = [(f.stat().st_mtime, f) for f in project_path.glob("*.jsonl") if not f.stem.startswith("agent-")]
        if sessions:
            sessions.sort(reverse=True)
            session_file = sessions[0][1]
            session_id = session_file.stem

            # Get model from session file
            with open(session_file, "r") as f:
                for line in f:
                    if '"model":' in line:
                        try:
                            entry = json.loads(line)
                            msg = entry.get("message", {})
                            if "model" in msg:
                                model = msg["model"]
                                break
                        except json.JSONDecodeError:
                            continue

    # Get version
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True)
        version = result.stdout.strip().split()[0]
    except (subprocess.CalledProcessError, IndexError):
        version = "unknown"

    # Output
    if session_id:
        console.print(f"AI-Session-ID: {session_id}")
    console.print(f"AI Agent: Claude Code {version} <noreply@anthropic.com>")
    console.print(f"Model: {model}")


@app.command()
def list_sessions(
    limit: int = typer.Option(10, "--limit", "-n", help="Max sessions to show"),
):
    """List recent AI sessions for current project."""
    claude_dir = Path.home() / ".claude" / "projects"
    project_path = claude_dir / get_project_dir()

    if not project_path.exists():
        console.print("[yellow]No sessions found.[/yellow]")
        raise typer.Exit(0)

    sessions = [(f.stat().st_mtime, f) for f in project_path.glob("*.jsonl") if not f.stem.startswith("agent-")]
    sessions.sort(reverse=True)

    table = Table(box=box.SIMPLE, padding=(0, 1))
    table.add_column("Session", style="cyan")
    table.add_column("Modified", style="dim")
    table.add_column("Size", justify="right")

    for mtime, f in sessions[:limit]:
        dt = datetime.fromtimestamp(mtime)
        table.add_row(f.stem, dt.strftime("%Y-%m-%d %H:%M"), f"{f.stat().st_size/1024:.0f}KB")

    console.print(table)


if __name__ == "__main__":
    app()
