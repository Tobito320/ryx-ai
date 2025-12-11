#!/usr/bin/env python3
"""
ONLINE LEARNER - Breaks Ryx's learning cap

When local repos aren't enough, search online for solutions.
Uses GitHub API and web scraping to find code patterns.

This is what makes Ryx truly autonomous.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CodePattern:
    """A code pattern found online"""
    source: str  # github repo, stackoverflow, etc
    url: str
    code: str
    description: str
    relevance_score: float
    language: str = "python"


@dataclass 
class LearningResult:
    """Result of online learning attempt"""
    query: str
    patterns_found: List[CodePattern]
    success: bool
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class OnlineLearner:
    """
    Searches online for code patterns when local repos aren't enough.
    
    Strategy:
    1. GitHub Code Search (best for specific patterns)
    2. GitHub Repo Search (good for finding similar projects)
    3. Clone relevant repos for deeper analysis
    """
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("/home/tobi/ryx-ai/data/online_learning")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cloned_repos_dir = Path("/home/tobi/cloned_repositorys")
        self.cloned_repos_dir.mkdir(parents=True, exist_ok=True)
        
    def search_github_code(self, query: str, language: str = "python", max_results: int = 10) -> List[CodePattern]:
        """Search GitHub for code patterns using gh CLI"""
        patterns = []
        
        try:
            # Use gh CLI for code search
            cmd = [
                "gh", "search", "code", query,
                "--language", language,
                "--limit", str(max_results),
                "--json", "path,repository,textMatches"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                results = json.loads(result.stdout)
                
                for item in results:
                    repo = item.get("repository", {}).get("nameWithOwner", "unknown")
                    path = item.get("path", "")
                    matches = item.get("textMatches", [])
                    
                    for match in matches[:2]:  # Limit matches per file
                        fragment = match.get("fragment", "")
                        if fragment:
                            patterns.append(CodePattern(
                                source="github_code_search",
                                url=f"https://github.com/{repo}/blob/main/{path}",
                                code=fragment,
                                description=f"From {repo}/{path}",
                                relevance_score=0.8,
                                language=language
                            ))
                            
        except subprocess.TimeoutExpired:
            print("  ⚠️ GitHub search timed out")
        except Exception as e:
            print(f"  ⚠️ GitHub search error: {e}")
            
        return patterns
    
    def search_github_repos(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for relevant GitHub repositories"""
        repos = []
        
        try:
            cmd = [
                "gh", "search", "repos", query,
                "--limit", str(max_results),
                "--json", "fullName,description,stargazersCount"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                repos = json.loads(result.stdout)
                
        except Exception as e:
            print(f"  ⚠️ Repo search error: {e}")
            
        return repos
    
    def clone_repo(self, repo_name: str) -> Optional[Path]:
        """Clone a repository for deeper analysis"""
        repo_path = self.cloned_repos_dir / repo_name.replace("/", "_")
        
        if repo_path.exists():
            print(f"  📁 Repo already exists: {repo_name}")
            return repo_path
            
        try:
            print(f"  📥 Cloning {repo_name}...")
            cmd = ["gh", "repo", "clone", repo_name, str(repo_path), "--", "--depth", "1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"  ✅ Cloned {repo_name}")
                return repo_path
            else:
                print(f"  ❌ Clone failed: {result.stderr[:100]}")
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ Clone timed out for {repo_name}")
        except Exception as e:
            print(f"  ❌ Clone error: {e}")
            
        return None
    
    def extract_patterns_from_repo(self, repo_path: Path, search_terms: List[str]) -> List[CodePattern]:
        """Extract relevant code patterns from a cloned repo"""
        patterns = []
        
        if not repo_path.exists():
            return patterns
            
        for term in search_terms:
            try:
                # Use ripgrep for fast search
                cmd = ["rg", "-l", "-i", term, str(repo_path), "--type", "py"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    files = result.stdout.strip().split("\n")[:5]  # Limit files
                    
                    for file_path in files:
                        if file_path:
                            # Get context around matches
                            ctx_cmd = ["rg", "-C", "5", "-i", term, file_path]
                            ctx_result = subprocess.run(ctx_cmd, capture_output=True, text=True, timeout=5)
                            
                            if ctx_result.stdout:
                                patterns.append(CodePattern(
                                    source="cloned_repo",
                                    url=file_path,
                                    code=ctx_result.stdout[:1000],
                                    description=f"Pattern '{term}' from {Path(file_path).name}",
                                    relevance_score=0.9,
                                    language="python"
                                ))
                                
            except Exception as e:
                pass
                
        return patterns
    
    def learn_from_weakness(self, weakness_name: str, weakness_description: str = "") -> LearningResult:
        """
        Main entry point: Learn how to fix a weakness from online sources.
        
        Strategy:
        1. Try known good repos first (Aider, SWE-agent, etc.)
        2. Search GitHub for more repos if needed
        3. Clone and extract patterns
        """
        print(f"\n🌐 ONLINE LEARNING: {weakness_name}")
        print("="*60)
        
        all_patterns = []
        
        # KNOWN GOOD REPOS for different weaknesses
        known_repos = {
            "file_discovery": ["Aider-AI/aider", "OpenDevin/OpenDevin"],
            "edit_success": ["Aider-AI/aider", "princeton-nlp/SWE-agent"],
            "task_completion": ["gpt-engineer-org/gpt-engineer", "OpenDevin/OpenDevin"],
            "intent_detection": ["langchain-ai/langchain"],
            "self_healing": ["OpenDevin/OpenDevin"],
            "default": ["Aider-AI/aider"],
        }
        
        # Step 1: Clone known good repos
        print("\n📍 Step 1: Checking known good repos...")
        target_repos = known_repos.get(weakness_name, known_repos["default"])
        
        for repo_name in target_repos[:2]:
            print(f"  📦 {repo_name}")
            repo_path = self.clone_repo(repo_name)
            if repo_path:
                search_terms = weakness_name.replace("_", " ").split() + [weakness_name]
                patterns = self.extract_patterns_from_repo(repo_path, search_terms)
                all_patterns.extend(patterns)
                print(f"    Found {len(patterns)} patterns")
        
        # Step 2: Search GitHub for more if needed
        if len(all_patterns) < 3:
            print("\n📍 Step 2: Searching GitHub for more...")
            base_terms = weakness_name.replace("_", " ")
            repos = self.search_github_repos(f"python {base_terms}", max_results=3)
            
            for repo in repos[:2]:
                name = repo.get("fullName", "")
                if name and name not in target_repos:
                    print(f"  📦 {name}")
                    repo_path = self.clone_repo(name)
                    if repo_path:
                        patterns = self.extract_patterns_from_repo(repo_path, [weakness_name])
                        all_patterns.extend(patterns)
        
        # Deduplicate patterns
        seen_codes = set()
        unique_patterns = []
        for p in all_patterns:
            key = p.code[:100]
            if key not in seen_codes:
                seen_codes.add(key)
                unique_patterns.append(p)
        
        unique_patterns.sort(key=lambda x: x.relevance_score, reverse=True)
        
        result = LearningResult(
            query=weakness_name,
            patterns_found=unique_patterns[:10],
            success=len(unique_patterns) > 0,
            source="github"
        )
        
        # Cache the result
        cache_file = self.cache_dir / f"{weakness_name}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(cache_file, 'w') as f:
            json.dump({
                "query": result.query,
                "patterns_count": len(result.patterns_found),
                "success": result.success,
                "timestamp": result.timestamp,
                "patterns": [
                    {"source": p.source, "url": p.url, "code": p.code[:500], "desc": p.description}
                    for p in result.patterns_found
                ]
            }, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"  LEARNING COMPLETE: Found {len(unique_patterns)} patterns")
        print(f"  Cached to: {cache_file.name}")
        print(f"{'='*60}")
        
        return result


def learn_online(weakness: str, description: str = "") -> LearningResult:
    """Quick helper to learn from online sources"""
    learner = OnlineLearner()
    return learner.learn_from_weakness(weakness, description or weakness)


if __name__ == "__main__":
    # Test the online learner
    learner = OnlineLearner()
    
    # Test with a real weakness
    result = learner.learn_from_weakness(
        "file_discovery",
        "finding files by semantic meaning and content"
    )
    
    print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Patterns found: {len(result.patterns_found)}")
    
    if result.patterns_found:
        print("\nTop pattern:")
        p = result.patterns_found[0]
        print(f"  Source: {p.source}")
        print(f"  URL: {p.url}")
        print(f"  Code preview: {p.code[:200]}...")
