#!/usr/bin/env python3
"""
Ryx AI - Code Quality Checker
Checks code quality, identifies issues, and suggests improvements
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ast
from typing import List, Dict, Any
from collections import defaultdict


class CodeQualityChecker:
    """Check Python code quality"""

    def __init__(self, project_root: Path) -> None:
        """Initialize code quality checker with project root"""
        self.project_root = project_root
        self.issues = defaultdict(list)
        self.stats = {
            'total_files': 0,
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
        }

    def check_file(self, file_path: Path) -> Dict[str, Any]:
        """Check a single Python file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {
                'file': str(file_path),
                'error': f"Syntax error: {e}",
                'issues': []
            }

        issues = []

        # Count lines
        lines = content.split('\n')
        self.stats['total_lines'] += len(lines)

        # Check for common issues
        for node in ast.walk(tree):
            # Count functions and classes
            if isinstance(node, ast.FunctionDef):
                self.stats['total_functions'] += 1

                # Check docstrings
                if not ast.get_docstring(node):
                    issues.append({
                        'type': 'missing_docstring',
                        'line': node.lineno,
                        'message': f"Function '{node.name}' missing docstring"
                    })

                # Check function length
                if hasattr(node, 'end_lineno'):
                    func_length = node.end_lineno - node.lineno
                    if func_length > 100:
                        issues.append({
                            'type': 'long_function',
                            'line': node.lineno,
                            'message': f"Function '{node.name}' is {func_length} lines (consider refactoring)"
                        })

            elif isinstance(node, ast.ClassDef):
                self.stats['total_classes'] += 1

                # Check class docstrings
                if not ast.get_docstring(node):
                    issues.append({
                        'type': 'missing_docstring',
                        'line': node.lineno,
                        'message': f"Class '{node.name}' missing docstring"
                    })

        return {
            'file': str(file_path.relative_to(self.project_root)),
            'lines': len(lines),
            'issues': issues
        }

    def check_all_files(self) -> List[Dict[str, Any]]:
        """Check all Python files in project"""
        results = []

        python_files = list(self.project_root.rglob("*.py"))
        self.stats['total_files'] = len(python_files)

        for py_file in python_files:
            # Skip venv and __pycache__
            if '.venv' in str(py_file) or '__pycache__' in str(py_file):
                continue

            result = self.check_file(py_file)
            results.append(result)

        return results

    def format_report(self, results: List[Dict[str, Any]]) -> str:
        """Format quality check report"""
        lines = []
        lines.append("")
        lines.append("=" * 60)
        lines.append("Ryx AI - Code Quality Report")
        lines.append("=" * 60)
        lines.append("")

        # Statistics
        lines.append("Statistics:")
        lines.append(f"  Total files: {self.stats['total_files']}")
        lines.append(f"  Total lines: {self.stats['total_lines']:,}")
        lines.append(f"  Total functions: {self.stats['total_functions']}")
        lines.append(f"  Total classes: {self.stats['total_classes']}")
        lines.append("")

        # Issues by type
        issue_counts = defaultdict(int)
        for result in results:
            for issue in result['issues']:
                issue_counts[issue['type']] += 1

        if issue_counts:
            lines.append("Issues by Type:")
            for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {issue_type}: {count}")
            lines.append("")

        # Files with issues
        files_with_issues = [r for r in results if r['issues']]
        if files_with_issues:
            lines.append(f"Files with Issues ({len(files_with_issues)}):")
            for result in sorted(files_with_issues, key=lambda x: len(x['issues']), reverse=True)[:10]:
                lines.append(f"\n  {result['file']} ({len(result['issues'])} issues)")
                for issue in result['issues'][:3]:  # Show first 3
                    lines.append(f"    Line {issue['line']}: {issue['message']}")
                if len(result['issues']) > 3:
                    lines.append(f"    ... and {len(result['issues']) - 3} more")
            lines.append("")

        # Quality Score
        total_possible_issues = self.stats['total_functions'] + self.stats['total_classes']
        total_actual_issues = sum(issue_counts.values())

        if total_possible_issues > 0:
            quality_score = max(0, 100 - (total_actual_issues / total_possible_issues * 100))
            lines.append(f"Quality Score: {quality_score:.1f}/100")
        else:
            lines.append("Quality Score: N/A")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    """Run code quality check"""
    project_root = Path(__file__).parent.parent

    print("Analyzing code quality...")
    print()

    checker = CodeQualityChecker(project_root)
    results = checker.check_all_files()

    report = checker.format_report(results)
    print(report)

    # Save report to file
    report_file = project_root / "data" / "code_quality_report.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
