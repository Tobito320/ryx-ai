"""
Ryx AI - Pattern Learner

Learns patterns from cloned repositories to improve Ryx's capabilities.
When Ryx encounters a weakness, it can:
1. Search cloned repos for similar solutions
2. Extract the pattern
3. Apply it to Ryx's codebase

This is the "learn from others" component of self-improvement.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Pattern:
    """A learned pattern from another codebase"""
    name: str
    source_repo: str
    source_file: str
    description: str
    code_snippet: str
    applicable_to: List[str]  # What problems this solves
    extracted_at: str


class PatternLearner:
    """
    Learns patterns from cloned repositories.
    
    Repos we learn from:
    - aider: Edit reliability, RepoMap
    - browser-use: Browser automation
    - gpt-pilot: Agent architecture
    - OpenHands: Multi-agent coding
    - healing-agent: Self-healing
    """
    
    REPOS_DIR = Path.home() / "cloned_repositorys"
    PATTERNS_FILE = Path.home() / "ryx-ai" / "data" / "learned_patterns.json"
    
    # Key repos and what we learn from them
    REPO_FOCUSES = {
        "aider": ["edit", "search_replace", "repomap", "coder"],
        "browser-use": ["agent", "browser", "action", "dom"],
        "gpt-pilot": ["agent", "developer", "architect"],
        "openhands-ai": ["agent", "sandbox", "runtime"],
        "healing-agent": ["heal", "recover", "retry"],
        "build-your-claude-code-from-scratch": ["tool", "context", "todo"],
    }
    
    def __init__(self):
        self.patterns: List[Pattern] = []
        self._load_patterns()
    
    def _load_patterns(self):
        """Load previously learned patterns"""
        if self.PATTERNS_FILE.exists():
            try:
                data = json.loads(self.PATTERNS_FILE.read_text())
                for p in data.get("patterns", []):
                    self.patterns.append(Pattern(**p))
            except:
                pass
    
    def _save_patterns(self):
        """Save learned patterns"""
        self.PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"patterns": [p.__dict__ for p in self.patterns]}
        self.PATTERNS_FILE.write_text(json.dumps(data, indent=2))
    
    def find_relevant_code(self, problem: str, keywords: List[str] = None) -> List[Tuple[str, str, str]]:
        """
        Find relevant code in cloned repos for a given problem.
        
        Args:
            problem: Description of the problem
            keywords: Specific keywords to search for
            
        Returns:
            List of (repo, file, code_snippet) tuples
        """
        results = []
        
        if not self.REPOS_DIR.exists():
            return results
        
        # Extract keywords from problem if not provided
        if not keywords:
            keywords = self._extract_keywords(problem)
        
        # Search each relevant repo
        for repo_name, focus_areas in self.REPO_FOCUSES.items():
            repo_path = self.REPOS_DIR / repo_name
            if not repo_path.exists():
                continue
            
            # Check if this repo is relevant
            relevant = any(kw.lower() in fa for kw in keywords for fa in focus_areas)
            if not relevant:
                continue
            
            # Search Python files
            for py_file in repo_path.rglob("*.py"):
                if "__pycache__" in str(py_file) or "test" in str(py_file).lower():
                    continue
                
                try:
                    content = py_file.read_text()
                    
                    # Check if file contains relevant keywords
                    content_lower = content.lower()
                    matches = sum(1 for kw in keywords if kw.lower() in content_lower)
                    
                    if matches >= 2:  # At least 2 keyword matches
                        # Extract relevant snippet
                        snippet = self._extract_snippet(content, keywords)
                        if snippet:
                            rel_path = str(py_file.relative_to(repo_path))
                            results.append((repo_name, rel_path, snippet))
                            
                            if len(results) >= 10:  # Limit results
                                return results
                except:
                    pass
        
        return results
    
    def _extract_keywords(self, problem: str) -> List[str]:
        """Extract keywords from problem description"""
        # Common code-related words to look for
        code_words = [
            "edit", "file", "search", "replace", "fix", "bug", "error",
            "agent", "tool", "context", "browser", "action", "dom",
            "heal", "recover", "retry", "todo", "task", "async",
            "prompt", "llm", "model", "response", "parse"
        ]
        
        problem_lower = problem.lower()
        found = [w for w in code_words if w in problem_lower]
        
        # Also extract potential identifiers
        words = re.findall(r'\b\w+\b', problem)
        found.extend([w for w in words if len(w) > 4 and w.lower() not in ["with", "that", "this", "from"]])
        
        return list(set(found))[:10]
    
    def _extract_snippet(self, content: str, keywords: List[str], max_lines: int = 50) -> Optional[str]:
        """Extract relevant code snippet around keyword matches"""
        lines = content.split('\n')
        
        # Find lines with keyword matches
        match_lines = []
        for i, line in enumerate(lines):
            if any(kw.lower() in line.lower() for kw in keywords):
                match_lines.append(i)
        
        if not match_lines:
            return None
        
        # Take context around first match cluster
        start = max(0, match_lines[0] - 5)
        end = min(len(lines), match_lines[0] + max_lines)
        
        snippet = '\n'.join(lines[start:end])
        
        # Skip if too short or just imports
        if len(snippet) < 100 or snippet.count('import') > snippet.count('def'):
            return None
        
        return snippet
    
    def learn_pattern(self, name: str, problem: str, repo: str, file_path: str, snippet: str):
        """Learn and save a new pattern"""
        from datetime import datetime
        
        pattern = Pattern(
            name=name,
            source_repo=repo,
            source_file=file_path,
            description=problem,
            code_snippet=snippet[:2000],  # Limit size
            applicable_to=self._extract_keywords(problem),
            extracted_at=datetime.now().isoformat()
        )
        
        self.patterns.append(pattern)
        self._save_patterns()
        
        return pattern
    
    def get_pattern_for_problem(self, problem: str) -> Optional[Pattern]:
        """Find a previously learned pattern that might help"""
        keywords = self._extract_keywords(problem)
        
        best_match = None
        best_score = 0
        
        for pattern in self.patterns:
            # Score based on keyword overlap
            overlap = len(set(keywords) & set(pattern.applicable_to))
            if overlap > best_score:
                best_score = overlap
                best_match = pattern
        
        return best_match if best_score >= 2 else None
    
    def suggest_improvements(self, weakness: str) -> Dict:
        """
        Analyze a weakness and suggest improvements based on learned patterns.
        
        Args:
            weakness: Description of what Ryx can't do well
            
        Returns:
            Dict with suggestions and relevant code examples
        """
        result = {
            "weakness": weakness,
            "relevant_patterns": [],
            "relevant_code": [],
            "suggestions": []
        }
        
        # Check existing patterns
        pattern = self.get_pattern_for_problem(weakness)
        if pattern:
            result["relevant_patterns"].append({
                "name": pattern.name,
                "source": f"{pattern.source_repo}/{pattern.source_file}",
                "snippet": pattern.code_snippet[:500]
            })
        
        # Search for new relevant code
        code_results = self.find_relevant_code(weakness)
        for repo, file, snippet in code_results[:3]:
            result["relevant_code"].append({
                "repo": repo,
                "file": file,
                "snippet": snippet[:500]
            })
        
        # Generate suggestions
        if result["relevant_code"]:
            result["suggestions"].append(
                f"Found {len(result['relevant_code'])} relevant code examples. "
                "Consider adapting their approaches."
            )
        
        if "edit" in weakness.lower() or "file" in weakness.lower():
            result["suggestions"].append(
                "Aider's search_replace.py has robust fuzzy matching. "
                "Consider using diff_match_patch library."
            )
        
        if "agent" in weakness.lower() or "autonomous" in weakness.lower():
            result["suggestions"].append(
                "browser-use has a sophisticated agent loop with thinking. "
                "OpenHands uses multi-agent architecture."
            )
        
        return result


# Quick test
if __name__ == "__main__":
    learner = PatternLearner()
    
    # Test finding relevant code
    results = learner.find_relevant_code("edit file reliability")
    print(f"Found {len(results)} relevant code snippets:")
    for repo, file, snippet in results[:3]:
        print(f"  - {repo}/{file}: {len(snippet)} chars")
