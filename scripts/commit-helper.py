#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Commit helper script for Claude Code.

Provides git information and formats commit messages with user prompts.

Usage:
    uv run scripts/commit-helper.py status          # Show git status summary
    uv run scripts/commit-helper.py format-message  # Format a commit message template
    uv run scripts/commit-helper.py --help          # Show help
"""

import subprocess
import sys
import argparse


def run_git(*args: str) -> str:
    """Run a git command and return output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_status_summary() -> None:
    """Print a summary of git status."""
    print("=== Git Status Summary ===\n")

    # Staged changes
    staged = run_git("diff", "--staged", "--name-only")
    if staged:
        print("Staged files:")
        for f in staged.split("\n"):
            print(f"  + {f}")
    else:
        print("No staged changes.")

    print()

    # Unstaged changes
    unstaged = run_git("diff", "--name-only")
    if unstaged:
        print("Unstaged changes:")
        for f in unstaged.split("\n"):
            print(f"  ~ {f}")

    # Untracked files
    untracked = run_git("ls-files", "--others", "--exclude-standard")
    if untracked:
        print("\nUntracked files:")
        for f in untracked.split("\n"):
            print(f"  ? {f}")

    # Stats
    print("\n=== Change Statistics ===")
    stats = run_git("diff", "--staged", "--stat")
    if stats:
        print(stats)
    else:
        print("No staged changes to show stats for.")


def format_message_template() -> None:
    """Print a commit message template."""
    template = '''<brief summary under 50 chars>

User prompts:
- "<first user prompt>"
- "<second user prompt>"
- "<add more as needed>"

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>'''

    print("=== Commit Message Template ===\n")
    print(template)
    print("\n=== Instructions ===")
    print("1. Replace <brief summary> with a concise description")
    print("2. List ALL user prompts from the conversation")
    print("3. Keep the footer as-is")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Commit helper for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("status", help="Show git status summary")
    subparsers.add_parser("format-message", help="Show commit message template")

    args = parser.parse_args()

    if args.command == "status":
        get_status_summary()
    elif args.command == "format-message":
        format_message_template()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
