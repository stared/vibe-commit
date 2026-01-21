#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["typer", "rich", "anthropic", "google-genai"]
# ///
"""
conversation-analyzer: Extract insights from Claude Code session logs.

Analyzes conversations for:
a) Performance calibration: corrections, re-explanations, frustration signals
b) User preferences: technical choices, style, workflow patterns
c) User treatment of AI: tone, trust level, delegation patterns

Supports multiple LLM providers: Anthropic (Claude) and Google (Gemini).
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(help="Analyze Claude Code conversations for insights")
console = Console()
stderr_console = Console(stderr=True)


# Model configuration
class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


MODELS = {
    # Anthropic models (Jan 2026)
    "haiku": ("anthropic", "claude-haiku-4-5-20251015"),
    "sonnet": ("anthropic", "claude-sonnet-4-5-20250514"),
    "opus": ("anthropic", "claude-opus-4-5-20251101"),
    # Google models (Jan 2026)
    "gemini-flash": ("google", "gemini-3-flash-preview"),
    "gemini": ("google", "gemini-3-flash-preview"),  # alias
}

DEFAULT_MODEL = "gemini-flash"  # Fast and cost-effective


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None
    has_tool_use: bool = False
    thinking: Optional[str] = None


@dataclass
class Conversation:
    """A parsed conversation from session logs."""
    session_id: str
    messages: list[Message] = field(default_factory=list)
    file_path: Optional[Path] = None


def get_project_dir() -> str:
    """Get the Claude project directory name for the current working directory."""
    cwd = os.getcwd()
    # Claude normalizes path: leading dash, slashes and underscores become dashes
    return "-" + cwd.lstrip("/").replace("/", "-").replace("\\", "-").replace("_", "-")


def find_session_files(path: str) -> list[Path]:
    """Find session JSONL files from a path (file or directory)."""
    p = Path(path)

    if p.is_file() and p.suffix == ".jsonl":
        return [p]

    if p.is_dir():
        # Check if it's "." meaning current project
        if path == ".":
            claude_dir = Path.home() / ".claude" / "projects"
            project_dir = get_project_dir()
            project_path = claude_dir / project_dir
            if project_path.exists():
                return sorted(
                    [f for f in project_path.glob("*.jsonl") if not f.stem.startswith("agent-")],
                    key=lambda f: f.stat().st_mtime,
                )
            return []

        # Check if path is a Claude projects directory
        return sorted(
            [f for f in p.glob("*.jsonl") if not f.stem.startswith("agent-")],
            key=lambda f: f.stat().st_mtime,
        )

    return []


def extract_text_content(content) -> str:
    """Extract text from message content (handles string or list of blocks)."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts)

    return str(content)


def extract_thinking(content) -> Optional[str]:
    """Extract thinking content from assistant message."""
    if not isinstance(content, list):
        return None

    for item in content:
        if isinstance(item, dict) and item.get("type") == "thinking":
            return item.get("thinking", "")
    return None


def has_tool_use(content) -> bool:
    """Check if message contains tool use."""
    if not isinstance(content, list):
        return False

    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            return True
    return False


def parse_session_file(file_path: Path) -> Conversation:
    """Parse a JSONL session file into a Conversation."""
    conversation = Conversation(
        session_id=file_path.stem,
        file_path=file_path,
    )

    with open(file_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")

            if entry_type == "user":
                message_data = entry.get("message", {})
                content = message_data.get("content", "")
                text = extract_text_content(content)

                # Skip system reminders
                if text.strip().startswith("<system-reminder>"):
                    continue

                conversation.messages.append(Message(
                    role="user",
                    content=text,
                    timestamp=entry.get("timestamp"),
                ))

            elif entry_type == "assistant":
                message_data = entry.get("message", {})
                content = message_data.get("content", [])
                text = extract_text_content(content)
                thinking = extract_thinking(content)
                tool_use = has_tool_use(content)

                conversation.messages.append(Message(
                    role="assistant",
                    content=text,
                    timestamp=entry.get("timestamp"),
                    has_tool_use=tool_use,
                    thinking=thinking,
                ))

    return conversation


def format_conversation_for_analysis(conversation: Conversation, include_thinking: bool = False) -> str:
    """Format conversation as readable text for analysis."""
    lines = []
    for msg in conversation.messages:
        role_label = "USER" if msg.role == "user" else "ASSISTANT"
        lines.append(f"### {role_label}")
        if msg.timestamp:
            lines.append(f"*{msg.timestamp}*")
        lines.append("")
        lines.append(msg.content)
        if include_thinking and msg.thinking:
            lines.append("")
            lines.append(f"<thinking>{msg.thinking[:500]}...</thinking>")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


ANALYSIS_PROMPT = """Analyze this Claude Code conversation. Output concise Markdown that can directly improve a CLAUDE.md instructions file.

## Format

### What went wrong
Bullet points of AI mistakes, misunderstandings, or rejected approaches. Include the user's correction. Be specific.

### User preferences
Concrete rules the AI should follow for this user. Write as direct instructions (e.g., "Use uv, not python3"). Only include things with clear evidence.

### What worked well
Brief notes on successful interactions worth reinforcing.

### Other observations
Anything else relevant for calibrating AI behavior with this user.

## Rules
- No JSON, no classifications, no scores
- Dense, actionable information only
- Quote user when it adds clarity
- Skip sections if empty
- **DO NOT FABRICATE**: Only state what the user explicitly said. If user said "don't use X", write "don't use X" - do NOT invent "use Y instead" unless Y was explicitly mentioned. Never invent tool names, model names, versions, or alternatives.

---

CONVERSATION TO ANALYZE:

"""


def resolve_model(model_name: str) -> tuple[str, str]:
    """Resolve model shortcut to (provider, model_id)."""
    if model_name in MODELS:
        return MODELS[model_name]
    # Assume it's a full model ID - detect provider
    if model_name.startswith("claude-"):
        return ("anthropic", model_name)
    if model_name.startswith("gemini-"):
        return ("google", model_name)
    # Default to trying as anthropic
    return ("anthropic", model_name)


def analyze_with_anthropic(conversation_text: str, model_id: str) -> str:
    """Use Anthropic Claude API to analyze the conversation."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model_id,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": ANALYSIS_PROMPT + conversation_text}
        ]
    )

    return message.content[0].text


def analyze_with_google(conversation_text: str, model_id: str) -> str:
    """Use Google Gemini API to analyze the conversation."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_id,
        contents=ANALYSIS_PROMPT + conversation_text,
    )

    return response.text


def analyze_conversation(conversation_text: str, model_name: str) -> str:
    """Analyze conversation using the specified model."""
    provider, model_id = resolve_model(model_name)

    if provider == "anthropic":
        return analyze_with_anthropic(conversation_text, model_id)
    elif provider == "google":
        return analyze_with_google(conversation_text, model_id)
    else:
        raise ValueError(f"Unknown provider: {provider}")


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to JSONL file, folder, or '.' for current project"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file path (default: stdout)"),
    model: str = typer.Option(DEFAULT_MODEL, "-m", "--model", help=f"Model to use: {', '.join(MODELS.keys())} or full ID"),
    include_thinking: bool = typer.Option(False, "--thinking", help="Include assistant thinking in output"),
    session_index: Optional[int] = typer.Option(None, "-s", "--session", help="Session index to analyze (default: latest)"),
):
    """Analyze conversation(s) for insights on AI performance, user preferences, and interaction patterns."""

    files = find_session_files(path)

    if not files:
        console.print(f"[red]No session files found at: {path}[/red]")
        raise typer.Exit(1)

    # Select session
    if session_index is not None:
        if session_index < 0 or session_index >= len(files):
            console.print(f"[red]Invalid session index. Available: 0-{len(files)-1}[/red]")
            raise typer.Exit(1)
        selected_file = files[session_index]
    else:
        selected_file = files[-1]  # Latest by default

    stderr_console.print(f"[blue]Analyzing: {selected_file.name}[/blue]")

    # Parse conversation
    conversation = parse_session_file(selected_file)

    if not conversation.messages:
        console.print("[yellow]No messages found in session[/yellow]")
        raise typer.Exit(1)

    stderr_console.print(f"[blue]Found {len(conversation.messages)} messages[/blue]")

    # Generate analysis
    provider, model_id = resolve_model(model)
    stderr_console.print(f"[blue]Using model: {model_id} ({provider})[/blue]")

    conversation_text = format_conversation_for_analysis(conversation, include_thinking)
    analysis = analyze_conversation(conversation_text, model)

    output_lines = [
        f"# Conversation Analysis",
        f"",
        f"**Session:** `{conversation.session_id}`  ",
        f"**File:** `{selected_file}`  ",
        f"**Messages:** {len(conversation.messages)}",
        f"",
        analysis,
    ]

    output_text = "\n".join(output_lines)

    if output:
        Path(output).write_text(output_text)
        stderr_console.print(f"[green]Analysis written to: {output}[/green]")
    else:
        print(output_text)


@app.command()
def models():
    """List available models for analysis."""
    console.print("\n[bold]Available models:[/bold]\n")
    console.print(f"  [green]Default: {DEFAULT_MODEL}[/green]\n")

    console.print("  [bold]Anthropic (Claude):[/bold]")
    console.print("    haiku    → claude-haiku-4-5-20251015  (fast, cheap)")
    console.print("    sonnet   → claude-sonnet-4-5-20250514 (balanced)")
    console.print("    opus     → claude-opus-4-5-20251101   (most capable)")
    console.print("    [dim]Requires: ANTHROPIC_API_KEY[/dim]\n")

    console.print("  [bold]Google (Gemini):[/bold]")
    console.print("    gemini-flash → gemini-3-flash-preview (fast, cheap)")
    console.print("    gemini       → gemini-3-flash-preview (alias)")
    console.print("    [dim]Requires: GOOGLE_API_KEY or GEMINI_API_KEY[/dim]\n")

    console.print("  [dim]Or use full model ID: -m claude-haiku-4-5-20251015[/dim]")


@app.command()
def list_sessions(
    path: str = typer.Argument(".", help="Path to folder or '.' for current project"),
):
    """List available session files."""
    files = find_session_files(path)

    if not files:
        console.print(f"[yellow]No sessions found[/yellow]")
        return

    console.print(f"\n[bold]Available sessions ({len(files)}):[/bold]\n")

    for i, f in enumerate(files):
        stat = f.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        size_kb = stat.st_size / 1024
        console.print(f"  [{i}] {f.name}  ({size_kb:.1f} KB, {mtime})")

    console.print(f"\n[dim]Use: ./conversation-analyzer.py analyze . -s INDEX[/dim]")


@app.command()
def export(
    path: str = typer.Argument(..., help="Path to JSONL file, folder, or '.' for current project"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file path"),
    session_index: Optional[int] = typer.Option(None, "-s", "--session", help="Session index"),
    include_thinking: bool = typer.Option(False, "--thinking", help="Include thinking"),
):
    """Export conversation as readable markdown (for manual analysis or other LLMs)."""
    files = find_session_files(path)

    if not files:
        console.print(f"[red]No session files found[/red]")
        raise typer.Exit(1)

    selected_file = files[session_index] if session_index is not None else files[-1]
    conversation = parse_session_file(selected_file)

    text = format_conversation_for_analysis(conversation, include_thinking)

    if output:
        Path(output).write_text(text)
        console.print(f"[green]Exported to: {output}[/green]")
    else:
        print(text)


if __name__ == "__main__":
    app()
