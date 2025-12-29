---
name: commit-with-prompts
description: Automatically includes user prompts in git commit messages. Use when the user mentions committing, wants to commit changes, asks to save their work to git, or says "commit this".
allowed-tools: Bash(git:*), Read, Grep
---

# Commit with User Prompts

This skill ensures that all git commits include the user prompts that led to the changes.

## When to Activate

Activate when the user:
- Says "commit", "commit this", "commit the changes"
- Asks to "save to git" or "push the changes"
- Mentions wanting to record their work
- Says "let's commit" or similar

## Instructions

1. **Extract User Prompts**: Look back through the entire conversation history and collect ALL user messages/prompts that led to the changes being committed. Include them in chronological order.

2. **Analyze Changes**: Run these commands to understand what's being committed:
   ```bash
   git status
   git diff --staged
   ```
   If nothing is staged, run `git diff` to see unstaged changes and ask if the user wants to stage them.

3. **Generate Commit Message**: Create a commit message in this format:
   ```
   <brief summary of changes>

   User prompts:
   - "<first user prompt>"
   - "<second user prompt>"
   - ...

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   ```

4. **Execute Commit**: Use a HEREDOC to ensure proper formatting:
   ```bash
   git add -A && git commit -m "$(cat <<'EOF'
   <your commit message here>
   EOF
   )"
   ```

## Rules

- Include ALL user prompts from this conversation, not just the last one
- Keep the summary line under 50 characters
- Preserve the exact wording of user prompts (can abbreviate very long ones with "...")
- If there are no changes to commit, inform the user
- Always show the proposed commit message before executing
