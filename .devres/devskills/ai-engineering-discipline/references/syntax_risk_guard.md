# Syntax Risk Guard

## Edit discipline

Use surgical edits. Touch only lines required by the task.

Before editing existing files:

1. Read the current file content.
2. Identify the smallest safe edit.
3. Preserve existing style and line endings.
4. Avoid unrelated formatting changes.

After editing:

1. Check syntax or structure with the appropriate tool when available.
2. For JSON, validate parsing.
3. For JavaScript/TypeScript, run the project parser/linter/test when available.
4. For Markdown, check headings, tables, links, and fenced blocks.

## Large-file rule

For large files, avoid whole-file rewrites. Prefer targeted replacement or split content into smaller modules.

## Failure rule

If an edit fails, reread the file before retrying. Do not repeatedly patch stale context.
