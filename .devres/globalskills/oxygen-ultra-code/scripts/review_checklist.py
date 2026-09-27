#!/usr/bin/env python3
"""
Code Review Checklist Generator - Generates structured review checklists based on file type and change scope.
Usage:
    python review_checklist.py [--files <changed-files>] [--type <change-type>]
"""
import os
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict
# File type categories
FILE_CATEGORIES = {
    'python': ['.py'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    'go': ['.go'],
    'rust': ['.rs'],
    'java': ['.java'],
    'sql': ['.sql'],
    'config': ['.yaml', '.yml', '.json', '.toml', '.ini', '.env'],
    'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
    'ci': ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile'],
    'docs': ['.md', '.rst', '.txt']
}
# Change types
CHANGE_TYPES = ['feature', 'bugfix', 'refactor', 'security', 'performance', 'docs', 'config']
# Checklist items by category
CHECKLISTS = {
    'general': [
        ('CRITICAL', 'Does this change introduce any hardcoded secrets, credentials, or API keys?'),
        ('CRITICAL', 'Are there any SQL injection, XSS, or other injection vulnerabilities?'),
        ('HIGH', 'Are all inputs properly validated and sanitized?'),
        ('HIGH', 'Are error conditions handled properly?'),
        ('HIGH', 'Are there any race conditions or concurrency issues?'),
        ('MEDIUM', 'Is the code readable and appropriately commented?'),
        ('MEDIUM', 'Are there appropriate tests for new functionality?'),
        ('MEDIUM', 'Do variable/function names clearly describe their purpose?'),
        ('MEDIUM', 'Is there any duplicated code that could be refactored?'),
        ('LOW', 'Are magic numbers extracted to named constants?'),
        ('LOW', 'Are there any leftover debug statements or TODO comments?'),
    ],
    'security': [
        ('CRITICAL', 'Is authentication/authorization correctly implemented?'),
        ('CRITICAL', 'Is sensitive data (PII, passwords, keys) properly protected?'),
        ('CRITICAL', 'Are crypto algorithms/parameters up to date and secure?'),
        ('HIGH', 'Are there proper CORS settings if this is an API?'),
        ('HIGH', 'Are dependencies checked for known vulnerabilities?'),
        ('HIGH', 'Is user input properly escaped in output?'),
        ('MEDIUM', 'Are there rate limits on sensitive endpoints?'),
        ('MEDIUM', 'Are logs free of sensitive data?'),
    ],
    'performance': [
        ('HIGH', 'Are there any O(n²) or worse algorithms on large datasets?'),
        ('HIGH', 'Are there N+1 database query patterns?'),
        ('HIGH', 'Are database queries properly indexed?'),
        ('MEDIUM', 'Are there appropriate caching opportunities?'),
        ('MEDIUM', 'Are resources (connections, files, memory) properly released?'),
        ('MEDIUM', 'Are there blocking operations in async/non-blocking paths?'),
        ('LOW', 'Are there unnecessary allocations in hot paths?'),
    ],
    'testing': [
        ('HIGH', 'Do tests cover happy paths AND error cases?'),
        ('HIGH', 'Are edge cases and boundary conditions tested?'),
        ('MEDIUM', 'Are tests deterministic (no flakiness, no time dependencies)?'),
        ('MEDIUM', 'Do tests properly isolate external dependencies?'),
        ('MEDIUM', 'Are there regression tests for fixed bugs?'),
        ('LOW', 'Do tests have descriptive names that explain expected behavior?'),
    ],
    'python': [
        ('HIGH', 'Are mutable default arguments avoided?'),
        ('HIGH', 'Are exceptions properly caught (not bare except:)?'),
        ('MEDIUM', 'Are context managers used for resource management?'),
        ('MEDIUM', 'Are type hints used appropriately?'),
        ('MEDIUM', 'Is pathlib used instead of os.path for path manipulation?'),
        ('LOW', 'Are list/dict comprehensions used appropriately (not too complex)?'),
    ],
    'javascript': [
        ('HIGH', 'Is === used instead of == for comparisons?'),
        ('HIGH', 'Are promises properly awaited/caught (no unhandled rejections)?'),
        ('MEDIUM', 'Are let/const used instead of var?'),
        ('MEDIUM', 'Is proper error handling in async code?'),
        ('MEDIUM', 'Are React hooks dependencies correct?'),
        ('LOW', 'Are optional chaining/nullish coalescing used appropriately?'),
    ],
    'sql': [
        ('CRITICAL', 'Are queries parameterized (no string concatenation)?'),
        ('HIGH', 'Are there proper indexes for WHERE/JOIN/ORDER BY columns?'),
        ('HIGH', 'Are transactions used where appropriate?'),
        ('MEDIUM', 'Is SELECT * avoided (explicit columns only)?'),
        ('MEDIUM', 'Is LIMIT used with ORDER BY for deterministic results?'),
        ('MEDIUM', 'Are N+1 query patterns avoided?'),
    ],
    'api': [
        ('HIGH', 'Is the API backwards compatible (no breaking changes)?'),
        ('HIGH', 'Are all API responses properly typed and documented?'),
        ('MEDIUM', 'Are API errors returned with appropriate status codes?'),
        ('MEDIUM', 'Is pagination provided for collection endpoints?'),
        ('MEDIUM', 'Is API versioning considered?'),
    ]
}
def categorize_files(files):
    """Categorize changed files by type."""
    categories = defaultdict(list)
    for f in files:
        path = Path(f)
        categorized = False
        # Check for special filenames first
        if path.name == 'Dockerfile':
            categories['docker'].append(f)
            categorized = True
        if '.github/workflows' in str(path):
            categories['ci'].append(f)
            categorized = True
        # Check by extension
        ext = path.suffix.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if ext in extensions:
                categories[category].append(f)
                categorized = True
                break
        if not categorized:
            categories['other'].append(f)
    return dict(categories)
def generate_checklist(files=None, change_type='feature'):
    """Generate a code review checklist based on files and change type."""
    checklist = []
    checklist.append("=" * 60)
    checklist.append("CODE REVIEW CHECKLIST")
    checklist.append("=" * 60)
    if files:
        categories = categorize_files(files)
        checklist.append(f"\nChanged files ({len(files)} total):")
        for cat, cat_files in categories.items():
            checklist.append(f"\n  [{cat.upper()}] ({len(cat_files)} files)")
            for f in cat_files[:10]:
                checklist.append(f"    - {f}")
            if len(cat_files) > 10:
                checklist.append(f"    ... and {len(cat_files) - 10} more")
    checklist.append(f"\nChange type: {change_type}")
    checklist.append("\n" + "-" * 60)
    # Add general checklist
    checklist.append("\n📋 GENERAL CHECKS")
    for severity, item in CHECKLISTS['general']:
        marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else '⚪'
        checklist.append(f"  {marker} [{severity}] {item}")
    # Add security checks for security-sensitive changes
    if change_type in ['security', 'feature', 'bugfix']:
        checklist.append("\n🔒 SECURITY CHECKS")
        for severity, item in CHECKLISTS['security']:
            marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
            checklist.append(f"  {marker} [{severity}] {item}")
    # Add performance checks
    if change_type in ['performance', 'feature', 'refactor']:
        checklist.append("\n⚡ PERFORMANCE CHECKS")
        for severity, item in CHECKLISTS['performance']:
            marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
            checklist.append(f"  {marker} [{severity}] {item}")
    # Add testing checks
    if change_type not in ['docs', 'config']:
        checklist.append("\n🧪 TESTING CHECKS")
        for severity, item in CHECKLISTS['testing']:
            marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
            checklist.append(f"  {marker} [{severity}] {item}")
    # Add language-specific checks
    if files:
        categories = categorize_files(files)
        if 'python' in categories:
            checklist.append("\n🐍 PYTHON-SPECIFIC CHECKS")
            for severity, item in CHECKLISTS['python']:
                marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
                checklist.append(f"  {marker} [{severity}] {item}")
        if 'javascript' in categories:
            checklist.append("\n📜 JAVASCRIPT/TYPESCRIPT CHECKS")
            for severity, item in CHECKLISTS['javascript']:
                marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
                checklist.append(f"  {marker} [{severity}] {item}")
        if 'sql' in categories:
            checklist.append("\n🗄️ SQL CHECKS")
            for severity, item in CHECKLISTS['sql']:
                marker = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
                checklist.append(f"  {marker} [{severity}] {item}")
    checklist.append("\n" + "-" * 60)
    checklist.append("\n💡 REVIEW TIPS:")
    checklist.append("  1. Review high-level design before looking at code details")
    checklist.append("  2. Focus on actual bugs and issues, not style preferences")
    checklist.append("  3. Consider the impact if this code fails in production")
    checklist.append("  4. Be constructive - suggest fixes, not just problems")
    checklist.append("  5. If you can't understand it in 5 minutes, it's too complex")
    return "\n".join(checklist)
def main():
    parser = argparse.ArgumentParser(description='Generate code review checklist')
    parser.add_argument('--files', nargs='*', help='List of changed files')
    parser.add_argument('--type', default='feature', choices=CHANGE_TYPES, help='Type of change')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    if args.json:
        categories = categorize_files(args.files) if args.files else {}
        result = {
            'change_type': args.type,
            'file_count': len(args.files) if args.files else 0,
            'categories': categories,
            'checklists': CHECKLISTS
        }
        print(json.dumps(result, indent=2))
    else:
        print(generate_checklist(args.files, args.type))
if __name__ == "__main__":
    main()
