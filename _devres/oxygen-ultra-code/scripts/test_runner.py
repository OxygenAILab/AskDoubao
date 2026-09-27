#!/usr/bin/env python3
"""
Smart Test Runner - Runs tests and aggregates errors for systematic debugging.
Automatically detects test frameworks, runs tests, and extracts actionable error information.
Usage:
    python test_runner.py [--path <project-path>] [--framework <framework>] [--test-file <file>]
"""
import os
import sys
import json
import subprocess
import re
from pathlib import Path
from collections import defaultdict
# Test framework detection patterns
FRAMEWORK_PATTERNS = {
    'pytest': ['pytest.ini', 'conftest.py', 'pyproject.toml'],
    'jest': ['jest.config.js', 'jest.config.ts', 'package.json'],
    'vitest': ['vitest.config.ts', 'vitest.config.js'],
    'go-test': ['go.mod'],
    'cargo-test': ['Cargo.toml'],
    'maven': ['pom.xml'],
    'gradle': ['build.gradle', 'build.gradle.kts'],
    'npm-test': ['package.json']
}
# Error patterns for common test frameworks
ERROR_PATTERNS = {
    'pytest': {
        'failed': r'FAILED',
        'error': r'ERROR',
        'assertion': r'AssertionError',
        'file_line': r'^([a-zA-Z0-9_./-]+.py):(\d+):',
        'exception': r'^E\s+(.+)$',
        'summary': r'=+ (.+?) in [\d.]+s =+'
    },
    'jest': {
        'failed': r'✕',
        'error': r'●',
        'expect': r'Expected:',
        'received': r'Received:',
        'file_line': r'^\s+at\s+.+?\(([a-zA-Z0-9_./-]+.(js|ts|jsx|tsx)):(\d+):(\d+)\)',
        'summary': r'Tests:\s+(\d+) failed'
    }
}
def detect_framework(path):
    """Detect test framework used in the project."""
    detected = []
    root = Path(path)
    for framework, indicators in FRAMEWORK_PATTERNS.items():
        for indicator in indicators:
            if (root / indicator).exists():
                detected.append(framework)
                break
    return detected
def get_test_command(framework, test_file=None, test_name=None):
    """Get the appropriate test command for the framework."""
    commands = {
        'pytest': ['python', '-m', 'pytest', '-v', '--tb=short'],
        'jest': ['npx', 'jest', '--verbose', '--no-coverage'],
        'vitest': ['npx', 'vitest', 'run', '--reporter=verbose'],
        'go-test': ['go', 'test', '-v', './...'],
        'cargo-test': ['cargo', 'test'],
        'maven': ['mvn', 'test'],
        'gradle': ['./gradlew', 'test'],
        'npm-test': ['npm', 'test']
    }
    cmd = commands.get(framework, [])
    if test_file and framework in ['pytest', 'jest', 'vitest']:
        cmd.append(test_file)
    if test_name and framework == 'pytest':
        cmd.append(f'-k {test_name}')
    return cmd
def parse_test_output(output, framework):
    """Parse test output and extract errors."""
    errors = []
    lines = output.split('\n')
    current_error = None
    if framework == 'pytest':
        for i, line in enumerate(lines):
            if 'FAILED' in line or 'ERROR' in line:
                match = re.search(r'^([a-zA-Z0-9_./-]+.py)::([a-zA-Z0-9_]+)', line)
                if match:
                    current_error = {
                        'file': match.group(1),
                        'test': match.group(2),
                        'type': 'FAILED' if 'FAILED' in line else 'ERROR',
                        'message': '',
                        'traceback': []
                    }
                    errors.append(current_error)
            elif current_error and line.startswith('E '):
                current_error['message'] += line[2:] + '\n'
            elif current_error and line.strip():
                current_error['traceback'].append(line)
    elif framework in ['jest', 'vitest']:
        for i, line in enumerate(lines):
            if '●' in line:
                current_error = {
                    'test': line.replace('●', '').strip(),
                    'type': 'FAILED',
                    'message': '',
                    'file': '',
                    'line': 0
                }
                errors.append(current_error)
            elif current_error and ('Expected:' in line or 'Received:' in line or 'Error:' in line):
                current_error['message'] += line + '\n'
            elif current_error:
                match = re.search(r'\(([a-zA-Z0-9_./-]+.(js|ts|jsx|tsx)):(\d+):(\d+)\)', line)
                if match:
                    current_error['file'] = match.group(1)
                    current_error['line'] = int(match.group(3))
    return errors
def run_tests(path='.', framework=None, test_file=None, test_name=None):
    """Run tests and return structured results."""
    # Auto-detect framework if not specified
    if not framework:
        frameworks = detect_framework(path)
        if not frameworks:
            return {'success': False, 'error': 'No test framework detected'}
        framework = frameworks[0]
    cmd = get_test_command(framework, test_file, test_name)
    if not cmd:
        return {'success': False, 'error': f'Unknown framework: {framework}'}
    try:
        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=300
        )
        output = result.stdout + result.stderr
        errors = parse_test_output(output, framework)
        # Extract summary
        summary_match = re.search(r'(\d+) passed,?\s*(\d+) failed', output)
        if not summary_match:
            summary_match = re.search(r'Tests:\s+(\d+) failed', output)
        return {
            'success': result.returncode == 0,
            'framework': framework,
            'command': ' '.join(cmd),
            'returncode': result.returncode,
            'errors': errors,
            'error_count': len(errors),
            'output': output[-5000:] if len(output) > 5000 else output,  # Last 5000 chars
            'output_truncated': len(output) > 5000
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Tests timed out after 300 seconds'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
def format_error_report(results):
    """Format test results into a human-readable error report."""
    report = []
    report.append("=" * 60)
    report.append("TEST RESULTS SUMMARY")
    report.append("=" * 60)
    report.append(f"Framework: {results.get('framework', 'unknown')}")
    report.append(f"Command: {results.get('command', '')}")
    report.append("")
    if results['success']:
        report.append("✅ ALL TESTS PASSED")
        return "\n".join(report)
    report.append(f"❌ TESTS FAILED - {results['error_count']} error(s)")
    report.append("")
    for i, error in enumerate(results['errors'], 1):
        report.append(f"--- Error {i} ---")
        report.append(f"File: {error.get('file', 'unknown')}")
        report.append(f"Test: {error.get('test', 'unknown')}")
        report.append(f"Type: {error.get('type', 'FAILED')}")
        report.append("")
        report.append("Message:")
        report.append(error.get('message', 'No message extracted').strip())
        report.append("")
    report.append("---")
    report.append("Debugging Suggestions:")
    report.append("1. Start with the first error (cascading failures are common)")
    report.append("2. Read the error message carefully")
    report.append("3. Check the file and line number mentioned")
    report.append("4. Reproduce with a single test first")
    report.append("5. Fix one error at a time and re-run tests")
    return "\n".join(report)
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Smart test runner')
    parser.add_argument('--path', default='.', help='Project path')
    parser.add_argument('--framework', help='Test framework (auto-detect if not specified)')
    parser.add_argument('--test-file', help='Run specific test file')
    parser.add_argument('--test-name', help='Run specific test name')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    results = run_tests(args.path, args.framework, args.test_file, args.test_name)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_error_report(results))
    sys.exit(0 if results.get('success') else 1)
if __name__ == "__main__":
    main()
