#!/usr/bin/env python3
"""
Code Context Extractor - Analyzes codebase structure and provides context summary.
Helps agents quickly understand project layout, dependencies, and patterns.
Usage:
    python code_context.py [--path <project-path>] [--depth <depth>]
"""
import os
import sys
import json
from pathlib import Path
from collections import defaultdict
# Common code file extensions
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.c', '.cpp', '.h',
    '.hpp', '.rb', '.php', '.cs', '.swift', '.kt', '.scala', '.sql', '.sh', '.bash',
    '.html', '.css', '.scss', '.vue', '.svelte'
}
# Config and dependency files
DEPENDENCY_FILES = {
    'package.json': 'javascript',
    'requirements.txt': 'python',
    'pyproject.toml': 'python',
    'Pipfile': 'python',
    'go.mod': 'go',
    'Cargo.toml': 'rust',
    'pom.xml': 'java',
    'build.gradle': 'java',
    'Gemfile': 'ruby',
    'composer.json': 'php',
    '.csproj': 'csharp',
    'package-lock.json': 'javascript',
    'yarn.lock': 'javascript',
    'pnpm-lock.yaml': 'javascript'
}
# Directories to ignore
IGNORE_DIRS = {
    'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build',
    'target', '.next', '.nuxt', 'coverage', '.tox', '.mypy_cache', '.pytest_cache',
    'vendor', 'bower_components', 'env'
}
def detect_languages(root_path):
    """Detect programming languages used in the project."""
    lang_counts = defaultdict(int)
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext in CODE_EXTENSIONS:
                lang = ext.lstrip('.')
                lang_counts[lang] += 1
    return dict(sorted(lang_counts.items(), key=lambda x: -x[1]))
def find_dependency_files(root_path):
    """Find dependency and configuration files."""
    deps = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f in DEPENDENCY_FILES or Path(f).suffix in {'.lock', '.toml', '.yaml', '.yml'}:
                full_path = Path(dirpath) / f
                rel_path = full_path.relative_to(root_path)
                deps.append(str(rel_path))
    return sorted(deps)
def get_directory_structure(root_path, max_depth=3):
    """Generate a tree-like directory structure."""
    structure = []
    root = Path(root_path)
    def add_to_structure(path, prefix="", depth=0):
        if depth > max_depth:
            return
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        entries = [e for e in entries if e.name not in IGNORE_DIRS and not e.name.startswith('.')]
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            if entry.is_dir():
                structure.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if is_last else "│   "
                add_to_structure(entry, prefix + extension, depth + 1)
            else:
                structure.append(f"{prefix}{connector}{entry.name}")
    structure.append(f"{root.name}/")
    add_to_structure(root)
    return "\n".join(structure)
def find_entry_points(root_path):
    """Find likely entry point files."""
    entry_points = []
    common_entries = [
        'main.py', 'app.py', 'index.js', 'index.ts', 'main.go', 'main.rs',
        'Main.java', 'index.html', 'server.py', 'cli.py', '__main__.py'
    ]
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f in common_entries:
                full_path = Path(dirpath) / f
                rel_path = full_path.relative_to(root_path)
                entry_points.append(str(rel_path))
    return sorted(entry_points)
def count_lines_of_code(root_path):
    """Count total lines of code by language."""
    loc_by_lang = defaultdict(int)
    file_counts = defaultdict(int)
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext in CODE_EXTENSIONS:
                lang = ext.lstrip('.')
                file_counts[lang] += 1
                try:
                    with open(Path(dirpath) / f, 'r', encoding='utf-8', errors='ignore') as fp:
                        loc_by_lang[lang] += sum(1 for _ in fp)
                except:
                    pass
    return {
        lang: {'files': file_counts[lang], 'lines': loc_by_lang[lang]}
        for lang in sorted(loc_by_lang.keys(), key=lambda l: -loc_by_lang[l])
    }
def generate_context_report(root_path, max_depth=3):
    """Generate a comprehensive context report."""
    root = Path(root_path).resolve()
    report = []
    report.append("=" * 60)
    report.append(f"CODEBASE CONTEXT REPORT: {root.name}")
    report.append("=" * 60)
    report.append("")
    # Languages
    report.append("## Languages Detected")
    languages = detect_languages(root)
    for lang, count in languages.items():
        report.append(f"  - {lang}: {count} files")
    report.append("")
    # Lines of Code
    report.append("## Code Statistics")
    loc = count_lines_of_code(root)
    total_files = sum(s['files'] for s in loc.values())
    total_loc = sum(s['lines'] for s in loc.values())
    report.append(f"  Total files: {total_files}")
    report.append(f"  Total lines: {total_loc:,}")
    report.append("")
    # Entry Points
    report.append("## Likely Entry Points")
    entries = find_entry_points(root)
    if entries:
        for ep in entries:
            report.append(f"  - {ep}")
    else:
        report.append("  No standard entry points found")
    report.append("")
    # Dependency Files
    report.append("## Configuration & Dependencies")
    deps = find_dependency_files(root)
    for dep in deps[:20]:  # Limit to 20
        report.append(f"  - {dep}")
    if len(deps) > 20:
        report.append(f"  ... and {len(deps) - 20} more")
    report.append("")
    # Directory Structure
    report.append("## Directory Structure")
    report.append(get_directory_structure(root, max_depth))
    report.append("")
    return "\n".join(report)
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract codebase context')
    parser.add_argument('--path', default='.', help='Project path (default: current directory)')
    parser.add_argument('--depth', type=int, default=3, help='Directory depth (default: 3)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    if args.json:
        root = Path(args.path).resolve()
        result = {
            'project': root.name,
            'languages': detect_languages(root),
            'loc': count_lines_of_code(root),
            'entry_points': find_entry_points(root),
            'dependencies': find_dependency_files(root)
        }
        print(json.dumps(result, indent=2))
    else:
        print(generate_context_report(args.path, args.depth))
if __name__ == "__main__":
    main()
