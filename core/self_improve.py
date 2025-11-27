"""
Ryx AI - Self-Improvement System
Allows Ryx to analyze itself and suggest improvements
"""

import json
import ast
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class SelfAnalyzer:
    """Analyzes Ryx's own code for improvements"""
    
    def __init__(self):
        self.project_root = Path.home() / "ryx-ai"
        self.improvement_log = self.project_root / "data" / "improvements.json"
        self.code_analysis = self.project_root / "data" / "code_analysis.json"
        
        self.improvement_log.parent.mkdir(parents=True, exist_ok=True)
        
        self.improvements = self.load_improvements()
    
    def load_improvements(self) -> Dict:
        """Load improvement suggestions"""
        if self.improvement_log.exists():
            with open(self.improvement_log, 'r') as f:
                return json.load(f)
        return {
            "pending": [],
            "completed": [],
            "failed": []
        }
    
    def save_improvements(self):
        """Save improvement suggestions"""
        with open(self.improvement_log, 'w') as f:
            json.dump(self.improvements, f, indent=2)
    
    def analyze_codebase(self) -> Dict:
        """
        Analyze Ryx's own codebase
        
        Returns analysis of:
        - Code complexity
        - Missing features
        - Potential bugs
        - Performance bottlenecks
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": [],
            "issues": [],
            "suggestions": [],
            "stats": {}
        }
        
        # Analyze all Python files
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            
            file_analysis = self._analyze_file(py_file)
            analysis["files_analyzed"].append(str(py_file))
            
            if file_analysis["issues"]:
                analysis["issues"].extend(file_analysis["issues"])
            
            if file_analysis["suggestions"]:
                analysis["suggestions"].extend(file_analysis["suggestions"])
        
        # Save analysis
        with open(self.code_analysis, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return analysis
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file"""
        issues = []
        suggestions = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                issues.append({
                    "file": str(file_path),
                    "type": "syntax_error",
                    "line": e.lineno,
                    "message": str(e)
                })
                return {"issues": issues, "suggestions": suggestions}
            
            # Check for missing docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        suggestions.append({
                            "file": str(file_path),
                            "type": "missing_docstring",
                            "name": node.name,
                            "line": node.lineno,
                            "message": f"Function/Class '{node.name}' missing docstring"
                        })
            
            # Check for TODO/FIXME comments
            for i, line in enumerate(content.split('\n'), 1):
                if 'TODO' in line or 'FIXME' in line:
                    issues.append({
                        "file": str(file_path),
                        "type": "todo",
                        "line": i,
                        "message": line.strip()
                    })
            
            # Check file size (very large files)
            lines = len(content.split('\n'))
            if lines > 500:
                suggestions.append({
                    "file": str(file_path),
                    "type": "large_file",
                    "lines": lines,
                    "message": f"File has {lines} lines - consider splitting"
                })
            
        except Exception as e:
            issues.append({
                "file": str(file_path),
                "type": "analysis_error",
                "message": str(e)
            })
        
        return {"issues": issues, "suggestions": suggestions}
    
    def detect_missing_features(self) -> List[Dict]:
        """
        Detect missing features by analyzing:
        - User command patterns that failed
        - Incomplete implementations
        - Feature requests from logs
        """
        missing = []
        
        # Check command history for failures
        history_file = self.project_root / "data" / "history" / "commands.log"
        if history_file.exists():
            with open(history_file, 'r') as f:
                for line in f:
                    if 'FAILED' in line:
                        # Extract failed command
                        parts = line.split('FAILED: ')
                        if len(parts) > 1:
                            cmd = parts[1].strip()
                            missing.append({
                                "type": "failed_command",
                                "command": cmd,
                                "suggestion": "Implement better error handling or add feature"
                            })
        
        # Check for NotImplementedError in code
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                if 'NotImplementedError' in content or 'pass  # TODO' in content:
                    missing.append({
                        "type": "incomplete_implementation",
                        "file": str(py_file),
                        "suggestion": "Complete implementation"
                    })
            except:
                pass
        
        return missing
    
    def suggest_improvement(self, suggestion: Dict):
        """Add improvement suggestion"""
        suggestion["timestamp"] = datetime.now().isoformat()
        suggestion["status"] = "pending"
        
        self.improvements["pending"].append(suggestion)
        self.save_improvements()
    
    def mark_completed(self, improvement_id: int):
        """Mark improvement as completed"""
        if improvement_id < len(self.improvements["pending"]):
            improvement = self.improvements["pending"].pop(improvement_id)
            improvement["completed_at"] = datetime.now().isoformat()
            improvement["status"] = "completed"
            self.improvements["completed"].append(improvement)
            self.save_improvements()
    
    def generate_improvement_plan(self) -> str:
        """
        Generate human-readable improvement plan
        
        Returns markdown document with:
        - Current issues
        - Suggested improvements
        - Implementation steps
        """
        analysis = self.analyze_codebase()
        missing = self.detect_missing_features()
        
        plan = f"""# Ryx AI - Self-Improvement Plan
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 Current Status

- Files analyzed: {len(analysis['files_analyzed'])}
- Issues found: {len(analysis['issues'])}
- Suggestions: {len(analysis['suggestions'])}
- Missing features: {len(missing)}

## 🐛 Issues Found

"""
        
        if analysis['issues']:
            for issue in analysis['issues'][:10]:  # Top 10
                plan += f"### {issue.get('type', 'Unknown')}\n"
                plan += f"- **File:** `{issue.get('file', 'Unknown')}`\n"
                plan += f"- **Line:** {issue.get('line', 'N/A')}\n"
                plan += f"- **Message:** {issue.get('message', 'No details')}\n\n"
        else:
            plan += "✅ No critical issues found!\n\n"
        
        plan += "## 💡 Improvement Suggestions\n\n"
        
        if analysis['suggestions']:
            for sug in analysis['suggestions'][:10]:
                plan += f"### {sug.get('type', 'Unknown')}\n"
                plan += f"- {sug.get('message', 'No details')}\n"
                plan += f"- File: `{sug.get('file', 'Unknown')}`\n\n"
        else:
            plan += "✅ Code looks good!\n\n"
        
        plan += "## 🚀 Missing Features\n\n"
        
        if missing:
            for feat in missing[:10]:
                plan += f"### {feat['type']}\n"
                plan += f"- {feat.get('suggestion', 'No details')}\n"
                if 'file' in feat:
                    plan += f"- File: `{feat['file']}`\n"
                plan += "\n"
        else:
            plan += "✅ All features implemented!\n\n"
        
        plan += """## 📝 How to Apply Improvements

1. **Review this plan carefully**
2. **Prioritize issues by severity**
3. **Implement fixes one by one**
4. **Test after each change**
5. **Run analysis again to verify**

## 🔧 Commands

```bash
# View full analysis
cat ~/ryx-ai/data/code_analysis.json

# Re-run analysis
ryx ::improve analyze

# Apply specific improvement
ryx ::improve apply <number>
```

---
*This plan was generated automatically by Ryx's self-analysis system.*
"""
        
        return plan


class SelfImprover:
    """
    Handles actual code improvements
    
    SAFETY: Only suggests improvements, never applies automatically
    """
    
    def __init__(self):
        self.analyzer = SelfAnalyzer()
        self.ai = None  # Will be initialized when needed
    
    def init_ai(self):
        """Lazy init AI engine"""
        if not self.ai:
            from core.ai_engine import AIEngine
            self.ai = AIEngine()
    
    def analyze_and_report(self) -> str:
        """Run full analysis and generate report"""
        print("\033[1;36m▸\033[0m Analyzing Ryx codebase...")
        
        plan = self.analyzer.generate_improvement_plan()
        
        # Save to file
        report_path = Path.home() / "ryx-ai" / "data" / "improvement_plan.md"
        with open(report_path, 'w') as f:
            f.write(plan)
        
        print(f"\033[1;32m✓\033[0m Analysis complete")
        print(f"\033[1;37m📄 Report:\033[0m {report_path}")
        print()
        
        return plan
    
    def suggest_fix(self, issue: Dict) -> Optional[str]:
        """
        Use AI to suggest fix for an issue
        
        Returns: Suggested code fix
        """
        self.init_ai()
        
        prompt = f"""Analyze this code issue and suggest a fix:

Issue Type: {issue.get('type', 'Unknown')}
File: {issue.get('file', 'Unknown')}
Line: {issue.get('line', 'N/A')}
Message: {issue.get('message', 'No details')}

Provide:
1. Brief explanation of the issue
2. Suggested fix (code)
3. Why this fix is better

Be concise and practical."""
        
        response = self.ai.query(prompt)
        
        if not response["error"]:
            return response["response"]
        
        return None
    
    def interactive_improve(self):
        """Interactive improvement session"""
        print()
        print("\033[1;36m╭──────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Ryx Self-Improvement Session       │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────╯\033[0m")
        print()
        
        plan = self.analyze_and_report()
        
        print(plan[:500] + "...")  # Show first 500 chars
        print()
        print("\033[1;33mFull report saved to:\033[0m")
        print("  ~/ryx-ai/data/improvement_plan.md")
        print()
        print("\033[1;36mWhat would you like to do?\033[0m")
        print("  1. View full report")
        print("  2. Get AI suggestions for top issues")
        print("  3. Exit")
        print()
        
        choice = input("\033[1mChoice [1-3]: \033[0m").strip()
        
        if choice == "1":
            # Open report in editor
            import subprocess
            subprocess.run(["less", str(Path.home() / "ryx-ai" / "data" / "improvement_plan.md")])
        
        elif choice == "2":
            self.suggest_fixes_interactive()
        
        print()
    
    def suggest_fixes_interactive(self):
        """Interactively suggest fixes"""
        analysis = json.loads(
            (Path.home() / "ryx-ai" / "data" / "code_analysis.json").read_text()
        )
        
        issues = analysis.get("issues", [])
        
        if not issues:
            print("\033[1;32m✓\033[0m No issues found!")
            return
        
        print()
        print(f"\033[1;36mFound {len(issues)} issues. Getting AI suggestions...\033[0m")
        print()
        
        for i, issue in enumerate(issues[:5], 1):  # Top 5 issues
            print(f"\033[1;33m[{i}/{min(5, len(issues))}]\033[0m {issue.get('message', 'Unknown issue')}")
            print()
            
            fix = self.suggest_fix(issue)
            if fix:
                print(fix)
            else:
                print("\033[1;31m✗\033[0m Could not generate suggestion")
            
            print()
            print("-" * 60)
            print()


# ===================================
# CLI Integration
# ===================================

def handle_improve_command(args: list):
    """Handle ::improve command"""
    improver = SelfImprover()
    
    if not args or args[0] == "analyze":
        improver.analyze_and_report()
    
    elif args[0] == "interactive":
        improver.interactive_improve()
    
    elif args[0] == "suggest":
        improver.suggest_fixes_interactive()
    
    else:
        print("\033[1;31m✗\033[0m Unknown subcommand")
        print("\033[1;37mUsage:\033[0m")
        print("  ryx ::improve analyze     - Run analysis")
        print("  ryx ::improve interactive - Interactive session")
        print("  ryx ::improve suggest     - Get AI suggestions")