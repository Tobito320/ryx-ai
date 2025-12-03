"""
Ryx Commit Helper

Intelligent commit message generation and formatting.
"""

import re
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


# Conventional commit types
COMMIT_TYPES = {
    'feat': 'A new feature',
    'fix': 'A bug fix',
    'docs': 'Documentation changes',
    'style': 'Formatting, missing semicolons, etc',
    'refactor': 'Code change that neither fixes a bug nor adds a feature',
    'perf': 'Performance improvement',
    'test': 'Adding or updating tests',
    'chore': 'Maintenance tasks',
    'ci': 'CI/CD changes',
    'build': 'Build system changes',
}


class CommitHelper:
    """
    Helper for generating and formatting commit messages.
    
    Supports:
    - Conventional commit format
    - Automatic type detection
    - Scope inference from file paths
    - LLM-based message generation (optional)
    """
    
    def __init__(self, git_manager=None, llm_client=None):
        """
        Initialize CommitHelper.
        
        Args:
            git_manager: GitManager for getting diff context
            llm_client: Optional LLM client for message generation
        """
        self.git = git_manager
        self.llm = llm_client
    
    def format_message(
        self,
        message: str,
        commit_type: str = None,
        scope: str = None,
        breaking: bool = False
    ) -> str:
        """
        Format a commit message in conventional format.
        
        Args:
            message: The commit message body
            commit_type: Commit type (feat, fix, etc.)
            scope: Optional scope
            breaking: Is this a breaking change?
            
        Returns:
            Formatted commit message
        """
        # Clean up message
        message = message.strip()
        
        # If no type specified, try to detect
        if not commit_type:
            commit_type = self._detect_type(message)
        
        # Build the message
        prefix = commit_type
        if scope:
            prefix = f"{commit_type}({scope})"
        if breaking:
            prefix = f"{prefix}!"
        
        # Ensure message starts lowercase (conventional commits style)
        if message and message[0].isupper():
            message = message[0].lower() + message[1:]
        
        return f"{prefix}: {message}"
    
    def _detect_type(self, message: str) -> str:
        """Detect commit type from message content"""
        message_lower = message.lower()
        
        # Check for explicit type mentions
        for commit_type in COMMIT_TYPES:
            if message_lower.startswith(commit_type):
                return commit_type
        
        # Keyword detection
        if any(kw in message_lower for kw in ['add', 'implement', 'new', 'create']):
            return 'feat'
        if any(kw in message_lower for kw in ['fix', 'bug', 'issue', 'error', 'resolve']):
            return 'fix'
        if any(kw in message_lower for kw in ['doc', 'readme', 'comment']):
            return 'docs'
        if any(kw in message_lower for kw in ['refactor', 'clean', 'restructure']):
            return 'refactor'
        if any(kw in message_lower for kw in ['test', 'spec']):
            return 'test'
        if any(kw in message_lower for kw in ['style', 'format', 'lint']):
            return 'style'
        if any(kw in message_lower for kw in ['perf', 'speed', 'optim']):
            return 'perf'
        
        return 'chore'
    
    def infer_scope(self, files: List[str]) -> Optional[str]:
        """
        Infer commit scope from changed files.
        
        Args:
            files: List of changed file paths
            
        Returns:
            Inferred scope or None
        """
        if not files:
            return None
        
        # Get common directory
        from pathlib import Path
        
        if len(files) == 1:
            # Single file - use parent dir or filename
            path = Path(files[0])
            if len(path.parts) > 1:
                return path.parts[0]
            return path.stem
        
        # Multiple files - find common prefix
        paths = [Path(f).parts for f in files]
        common = []
        
        for parts in zip(*paths):
            if len(set(parts)) == 1:
                common.append(parts[0])
            else:
                break
        
        if common:
            return common[-1] if common[-1] != '.' else None
        
        return None
    
    def generate_from_diff(
        self,
        diff: str = None,
        files: List[str] = None,
        task_context: str = None
    ) -> str:
        """
        Generate a commit message from diff or file list.
        
        Args:
            diff: Git diff string
            files: Changed files
            task_context: Optional context about what was being done
            
        Returns:
            Generated commit message
        """
        if not diff and self.git:
            diff = self.git.get_diff(files, staged=True)
        
        if not diff:
            if files:
                return f"Update {', '.join(files[:3])}"
            return "Update files"
        
        # If LLM available, use it
        if self.llm:
            return self._generate_with_llm(diff, task_context)
        
        # Simple heuristic-based generation
        return self._generate_heuristic(diff, files)
    
    def _generate_heuristic(self, diff: str, files: List[str] = None) -> str:
        """Generate message using heuristics"""
        lines_added = diff.count('\n+') - diff.count('\n+++')
        lines_removed = diff.count('\n-') - diff.count('\n---')
        
        # Analyze diff content
        if 'def test_' in diff or 'it(' in diff or 'describe(' in diff:
            msg_type = 'test'
            action = 'add tests'
        elif lines_added > lines_removed * 2:
            msg_type = 'feat'
            action = 'add functionality'
        elif lines_removed > lines_added * 2:
            msg_type = 'refactor'
            action = 'remove unused code'
        elif 'fix' in diff.lower() or 'bug' in diff.lower():
            msg_type = 'fix'
            action = 'fix issue'
        else:
            msg_type = 'chore'
            action = 'update'
        
        # Add file context
        scope = self.infer_scope(files) if files else None
        
        message = action
        if scope:
            message = f"{action} in {scope}"
        
        return self.format_message(message, msg_type, scope)
    
    def _generate_with_llm(self, diff: str, context: str = None) -> str:
        """Generate message using LLM"""
        prompt = f"""Generate a conventional commit message for this diff.
Format: type(scope): description

Diff:
{diff[:2000]}

{"Context: " + context if context else ""}

Respond with only the commit message, nothing else."""
        
        try:
            response = self.llm.generate(prompt)
            message = response.strip()
            
            # Validate format
            if re.match(r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)(\(.+\))?:', message):
                return message
            
            # Try to format it
            return self.format_message(message)
            
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return self._generate_heuristic(diff)
    
    def suggest_messages(
        self,
        diff: str = None,
        files: List[str] = None,
        count: int = 3
    ) -> List[str]:
        """
        Suggest multiple commit message options.
        
        Args:
            diff: Git diff
            files: Changed files
            count: Number of suggestions
            
        Returns:
            List of message suggestions
        """
        suggestions = []
        
        # Basic suggestion
        suggestions.append(self.generate_from_diff(diff, files))
        
        # Add variations if we have file info
        if files:
            scope = self.infer_scope(files)
            
            # Different types
            for commit_type in ['feat', 'fix', 'refactor']:
                if len(suggestions) >= count:
                    break
                    
                msg = self.format_message(
                    f"update {scope or 'files'}",
                    commit_type,
                    scope
                )
                if msg not in suggestions:
                    suggestions.append(msg)
        
        return suggestions[:count]
