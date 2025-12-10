#!/usr/bin/env python3
"""
Ryx AI - Autonomous Self-Improvement System

This is the core loop where Ryx improves itself.
Ryx discovers its weaknesses, researches solutions, and implements improvements.

Key principle: Ryx fixes Ryx. Copilot only monitors.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class PermissionType(Enum):
    """Types of permissions Ryx must request"""
    CLONE_REPO = "clone_repo"
    EDIT_FILE = "edit_file"
    DELETE_FILE = "delete_file"
    INSTALL_PACKAGE = "install_package"


@dataclass
class PermissionRequest:
    """A request for permission from Ryx"""
    type: PermissionType
    target: str
    reason: str
    approved: Optional[bool] = None
    response: Optional[str] = None


@dataclass
class Weakness:
    """An identified weakness in Ryx"""
    category: str
    score: int
    max_score: int
    description: str
    priority: int = 0  # Lower = higher priority


@dataclass
class RepoInfo:
    """Information about a cloned repository"""
    name: str
    path: Path
    description: str = ""
    relevant_for: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)


@dataclass
class ImprovementAttempt:
    """A single attempt to improve"""
    attempt_number: int
    action: str
    result: str  # "SUCCESS" or "FAIL"
    score_before: int
    score_after: int
    error: Optional[str] = None


@dataclass
class ImprovementLog:
    """Full log of an improvement cycle"""
    id: str
    timestamp: str
    weakness: Weakness
    repos_used: List[str] = field(default_factory=list)
    attempts: List[ImprovementAttempt] = field(default_factory=list)
    final_score: int = 0
    success: bool = False
    files_changed: List[str] = field(default_factory=list)


class SelfImprover:
    """
    The autonomous self-improvement engine.
    
    Ryx uses this to:
    1. Discover its weaknesses (benchmark)
    2. Find solutions (search repos)
    3. Implement improvements
    4. Verify improvements
    5. Document learnings
    """
    
    def __init__(self, auto_approve: bool = False):
        """
        Initialize the self-improver.
        
        Args:
            auto_approve: If True, auto-approve safe operations.
                         If False, always ask for permission.
        """
        self.project_root = PROJECT_ROOT
        self.auto_approve = auto_approve
        self.repos: List[RepoInfo] = []
        self.weaknesses: List[Weakness] = []
        self.current_log: Optional[ImprovementLog] = None
        self.pending_permissions: List[PermissionRequest] = []
        
        # Load LLM for reasoning
        from core.ollama_client import get_ollama_client
        self.llm = get_ollama_client()
        
        # Paths for logs
        self.log_dir = self.project_root / "data" / "improvement_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: SELF-DISCOVERY - Find repos without being told paths
    # ═══════════════════════════════════════════════════════════════
    
    def discover_repos(self) -> List[RepoInfo]:
        """
        Find cloned repositories without being given explicit paths.
        Ryx must figure out where repos are.
        """
        print("🔍 Discovering cloned repositories...")
        
        # Common locations to search
        search_locations = [
            Path.home() / "cloned_repositorys",  # Note: intentional typo in actual path
            Path.home() / "cloned_repositories",
            Path.home() / "repos",
            Path.home() / "projects",
            Path.home() / "code",
            Path.home() / "github",
        ]
        
        found_repos = []
        
        for location in search_locations:
            if location.exists() and location.is_dir():
                print(f"  📁 Found repo directory: {location}")
                
                # List subdirectories (each is a repo)
                for item in location.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        # Check if it's a git repo
                        if (item / ".git").exists():
                            repo_info = self._analyze_repo(item)
                            found_repos.append(repo_info)
                            print(f"    ✓ {repo_info.name}: {repo_info.description[:50]}...")
        
        if not found_repos:
            print("  ⚠️ No repos found in standard locations")
            print("  Searching more broadly...")
            
            # Try find command
            try:
                result = subprocess.run(
                    ["find", str(Path.home()), "-maxdepth", "3", "-name", ".git", "-type", "d"],
                    capture_output=True, text=True, timeout=30
                )
                for git_path in result.stdout.strip().split('\n'):
                    if git_path:
                        repo_path = Path(git_path).parent
                        if repo_path not in [r.path for r in found_repos]:
                            repo_info = self._analyze_repo(repo_path)
                            found_repos.append(repo_info)
            except Exception as e:
                print(f"  ⚠️ Find command failed: {e}")
        
        self.repos = found_repos
        print(f"\n📚 Found {len(found_repos)} repositories")
        return found_repos
    
    def _analyze_repo(self, path: Path) -> RepoInfo:
        """Analyze a repo to understand what it does"""
        name = path.name
        description = ""
        relevant_for = []
        key_files = []
        
        # Try to read README
        for readme in ["README.md", "README.rst", "README.txt", "README"]:
            readme_path = path / readme
            if readme_path.exists():
                try:
                    content = readme_path.read_text()[:500]
                    # Extract first paragraph as description
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith('#') and not line.startswith('!'):
                            description = line.strip()[:100]
                            break
                except:
                    pass
                break
        
        # Identify relevance based on repo name
        name_lower = name.lower()
        if any(x in name_lower for x in ['aider', 'code', 'edit', 'coder']):
            relevant_for.append('edit_success')
        if any(x in name_lower for x in ['heal', 'repair', 'fix', 'recover']):
            relevant_for.append('self_healing')
        if any(x in name_lower for x in ['agent', 'auto', 'swe']):
            relevant_for.append('task_completion')
        if any(x in name_lower for x in ['memory', 'context', 'rag']):
            relevant_for.append('file_discovery')
        
        # Find key Python files
        try:
            for py_file in path.rglob("*.py"):
                rel_path = py_file.relative_to(path)
                if len(str(rel_path)) < 50 and not any(x in str(rel_path) for x in ['test', 'example', '__pycache__']):
                    key_files.append(str(rel_path))
                if len(key_files) >= 10:
                    break
        except:
            pass
        
        return RepoInfo(
            name=name,
            path=path,
            description=description,
            relevant_for=relevant_for,
            key_files=key_files[:10]
        )
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: SELF-BENCHMARK - Discover weaknesses
    # ═══════════════════════════════════════════════════════════════
    
    def run_benchmark(self) -> Dict[str, Any]:
        """Run the benchmark and identify weaknesses"""
        print("\n📊 Running self-benchmark...")
        
        from scripts.benchmark import RyxBenchmark
        
        benchmark = RyxBenchmark()
        report = benchmark.run_all()
        benchmark.save_report(report)
        
        # Identify weaknesses (anything below 50% of max)
        self.weaknesses = []
        
        categories = [
            ("edit_success", report.edit_success, report.edit_max, "File editing reliability"),
            ("file_discovery", report.file_discovery, report.file_max, "Finding relevant files"),
            ("task_completion", report.task_completion, report.task_max, "Completing autonomous tasks"),
            ("self_healing", report.self_healing, report.healing_max, "Recovering from errors"),
        ]
        
        for cat, score, max_score, desc in categories:
            if score < max_score * 0.5:  # Below 50%
                weakness = Weakness(
                    category=cat,
                    score=score,
                    max_score=max_score,
                    description=desc,
                    priority=max_score - score  # Higher gap = higher priority
                )
                self.weaknesses.append(weakness)
        
        # Sort by priority (highest gap first)
        self.weaknesses.sort(key=lambda w: w.priority, reverse=True)
        
        print(f"\n🎯 Identified {len(self.weaknesses)} weaknesses:")
        for w in self.weaknesses:
            print(f"  • {w.category}: {w.score}/{w.max_score} - {w.description}")
        
        return asdict(report)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: RESEARCH - Find solutions in repos
    # ═══════════════════════════════════════════════════════════════
    
    def research_weakness(self, weakness: Weakness) -> List[Dict]:
        """Research how to fix a weakness using available repos"""
        print(f"\n🔬 Researching solutions for: {weakness.category}")
        
        findings = []
        
        # Find repos relevant to this weakness
        relevant_repos = [r for r in self.repos if weakness.category in r.relevant_for]
        
        if not relevant_repos:
            # Search all repos for keywords
            keywords = {
                "edit_success": ["edit", "replace", "patch", "diff", "coder"],
                "file_discovery": ["context", "repo", "map", "search", "find"],
                "task_completion": ["agent", "task", "execute", "plan"],
                "self_healing": ["heal", "retry", "recover", "error", "fix"],
            }
            
            for repo in self.repos:
                for kw in keywords.get(weakness.category, []):
                    if kw in repo.name.lower() or kw in repo.description.lower():
                        relevant_repos.append(repo)
                        break
        
        print(f"  Found {len(relevant_repos)} potentially relevant repos")
        
        for repo in relevant_repos:
            print(f"\n  📖 Analyzing: {repo.name}")
            
            # Search for relevant code
            finding = {
                "repo": repo.name,
                "path": str(repo.path),
                "relevant_files": [],
                "key_insights": [],
            }
            
            # Use grep to find relevant code
            search_terms = {
                "edit_success": ["def edit", "def apply", "def replace", "SequenceMatcher", "diff_match"],
                "file_discovery": ["def find", "def search", "repo_map", "context"],
                "task_completion": ["def execute", "def run_task", "agent"],
                "self_healing": ["retry", "recover", "heal", "def fix"],
            }
            
            for term in search_terms.get(weakness.category, []):
                try:
                    result = subprocess.run(
                        ["grep", "-r", "-l", term, str(repo.path)],
                        capture_output=True, text=True, timeout=10
                    )
                    for file_path in result.stdout.strip().split('\n'):
                        if file_path and '.py' in file_path and '__pycache__' not in file_path:
                            rel_path = Path(file_path).relative_to(repo.path)
                            if str(rel_path) not in finding["relevant_files"]:
                                finding["relevant_files"].append(str(rel_path))
                except:
                    pass
            
            if finding["relevant_files"]:
                findings.append(finding)
                print(f"    Found {len(finding['relevant_files'])} relevant files")
        
        if not findings:
            print("  ⚠️ No relevant code found in local repos")
            print("  Consider searching online for solutions")
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: PERMISSION SYSTEM
    # ═══════════════════════════════════════════════════════════════
    
    def request_permission(self, ptype: PermissionType, target: str, reason: str) -> bool:
        """
        Request permission for an action.
        
        Auto-approved actions (if auto_approve=True):
        - Reading files
        - Creating test files
        - Editing test files
        
        Always requires approval:
        - Editing core files
        - Cloning repos
        - Installing packages
        - Deleting files
        """
        request = PermissionRequest(
            type=ptype,
            target=target,
            reason=reason
        )
        
        # Check if auto-approvable
        if self.auto_approve:
            if ptype == PermissionType.EDIT_FILE:
                # Auto-approve edits to test files
                if 'test' in target.lower() or target.startswith('data/'):
                    request.approved = True
                    request.response = "Auto-approved (test/data file)"
                    print(f"  ✓ Auto-approved: {ptype.value} {target}")
                    return True
        
        # Need manual approval
        self.pending_permissions.append(request)
        print(f"\n🔐 PERMISSION REQUIRED")
        print(f"   Type: {ptype.value}")
        print(f"   Target: {target}")
        print(f"   Reason: {reason}")
        print(f"   Awaiting approval...")
        
        return False  # Not approved yet
    
    def approve_permission(self, index: int, approved: bool, response: str = "") -> None:
        """Approve or deny a pending permission"""
        if 0 <= index < len(self.pending_permissions):
            self.pending_permissions[index].approved = approved
            self.pending_permissions[index].response = response
    
    def get_pending_permissions(self) -> List[PermissionRequest]:
        """Get list of permissions awaiting approval"""
        return [p for p in self.pending_permissions if p.approved is None]
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: IMPLEMENT IMPROVEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def attempt_improvement(self, weakness: Weakness, findings: List[Dict]) -> ImprovementAttempt:
        """
        Attempt to implement an improvement based on research findings.
        
        This uses the LLM to:
        1. Understand the relevant code from other repos
        2. Generate an improvement for Ryx
        3. Test the improvement
        """
        print(f"\n🔧 Attempting to improve: {weakness.category}")
        
        # Get current score
        score_before = weakness.score
        
        # Build context from findings
        context_parts = []
        for finding in findings[:3]:  # Limit to top 3 repos
            repo_name = finding["repo"]
            for file_path in finding["relevant_files"][:3]:  # Limit to 3 files per repo
                full_path = Path(finding["path"]) / file_path
                if full_path.exists():
                    try:
                        content = full_path.read_text()[:2000]  # First 2000 chars
                        context_parts.append(f"# From {repo_name}/{file_path}:\n{content}")
                    except:
                        pass
        
        context = "\n\n".join(context_parts)
        
        # Use LLM to generate improvement plan (sync call via requests)
        import requests
        
        llm_prompt = f"""You are Ryx, an AI that is improving itself.

Your weakness: {weakness.category} - {weakness.description}
Current score: {weakness.score}/{weakness.max_score}

Here is code from other successful projects that handle this well:

{context[:4000]}

Based on this, suggest ONE specific code change to improve Ryx's {weakness.category}.

Format your response as:
FILE: <path to file in Ryx to modify>
SEARCH: <exact text to find>
REPLACE: <exact text to replace with>
EXPLANATION: <brief explanation>
"""
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:14b",
                    "prompt": llm_prompt,
                    "stream": False,
                    "options": {"num_predict": 1000}
                },
                timeout=120
            )
            response_text = resp.json().get("response", "")
            print(f"\n  LLM Response:\n{response_text[:500]}...")
        except Exception as e:
            print(f"\n  ⚠️ LLM call failed: {e}")
            response_text = ""
        
        # Parse response and attempt edit
        # (This is where the actual improvement would happen)
        
        attempt = ImprovementAttempt(
            attempt_number=1,
            action=f"Analyzed {len(findings)} repos, generated improvement plan",
            result="PENDING",
            score_before=score_before,
            score_after=score_before,
        )
        
        return attempt
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════
    
    def run_improvement_cycle(self) -> ImprovementLog:
        """
        Run a full self-improvement cycle.
        
        1. Discover repos
        2. Run benchmark
        3. Pick highest-priority weakness
        4. Research solutions
        5. Attempt improvement
        6. Verify and document
        """
        print("═" * 60)
        print("  RYX AUTONOMOUS SELF-IMPROVEMENT")
        print("═" * 60)
        
        # Step 1: Discover repos
        self.discover_repos()
        
        # Step 2: Benchmark
        benchmark_result = self.run_benchmark()
        
        if not self.weaknesses:
            print("\n✅ No significant weaknesses found!")
            return None
        
        # Step 3: Pick top weakness
        weakness = self.weaknesses[0]
        print(f"\n🎯 Focusing on: {weakness.category} ({weakness.score}/{weakness.max_score})")
        
        # Step 4: Research
        findings = self.research_weakness(weakness)
        
        # Step 5: Attempt improvement
        if findings:
            attempt = self.attempt_improvement(weakness, findings)
            print(f"\n📝 Attempt result: {attempt.result}")
        else:
            print("\n⚠️ No findings to base improvement on")
            print("   Need to search online for solutions")
        
        # Create log
        log = ImprovementLog(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now().isoformat(),
            weakness=weakness,
            repos_used=[f["repo"] for f in findings],
            final_score=weakness.score,
            success=False
        )
        
        # Save log
        log_path = self.log_dir / f"{log.id}.json"
        with open(log_path, 'w') as f:
            json.dump(asdict(log), f, indent=2, default=str)
        
        print(f"\n📄 Log saved to: {log_path}")
        
        return log


def main():
    """Run the self-improvement system"""
    improver = SelfImprover(auto_approve=False)
    improver.run_improvement_cycle()


if __name__ == "__main__":
    main()
