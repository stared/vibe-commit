# Development Process Notes

## Commit Message Guidelines

When using `/commit` with user prompt tracking:

1. **Exclude meta-commands**: Don't include `/commit` itself as it doesn't affect file changes
2. **Only include prompts that led to actual changes**: Focus on user requests that resulted in code/file modifications
3. **Avoid repetition**: Don't list the same command multiple times

### Example

Bad:
```
User prompts:
- "/commit"
- "My bad, I created it in a wrong folder."
- "I moved them out. Check again"
- "Yes" (to add .DS_Store to .gitignore)
- "/commit"
```

Good:
```
User prompts:
- "Yes" (to add .DS_Store to .gitignore)
```

The good version only includes prompts that directly resulted in file changes being committed.
