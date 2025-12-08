"""
Ryx AI - Enhanced Executor

This is the upgraded execution layer that incorporates:
1. ReliableEditor - Multi-strategy edit matching (from Aider)
2. SelfHealing - Automatic error recovery with retries (from healing-agent)
3. RepoMap - Semantic code understanding (from Aider)
4. AutoContext - Automatic file discovery

The goal: Make Ryx 210% as reliable and 110% as powerful as Claude Code CLI.

Key improvements:
- Edits rarely fail (multiple fallback strategies)
- Errors auto-recover (3 retries with reflection)
- File discovery is smarter (uses code structure, not just file names)
- No manual file adding ever needed
"""

import os
import re
import logging
import asyncio
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from core.ryx_brain import get_brain, Intent
from core.autonomous_brain import get_autonomous_brain
from core.auto_context import AutoContextBuilder, ContextResult
from core.reliable_editor import get_editor, EditResult
from core.self_healing import healing, SelfHealingExecutor, capture_error_context
from core.repo_map import get_repo_map

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of an enhanced execution"""
    success: bool
    output: str
    edits_applied: int = 0
    edits_failed: int = 0
    files_discovered: int = 0
    retries_used: int = 0
    strategy_breakdown: Dict[str, int] = None
    
    def __post_init__(self):
        if self.strategy_breakdown is None:
            self.strategy_breakdown = {}


class EnhancedExecutor:
    """
    The brain of Ryx - orchestrates all components for reliable execution.
    
    This is what makes Ryx better than Claude Code:
    1. NEVER asks user to add files manually
    2. Edits succeed even when LLM output is imperfect
    3. Errors are recovered automatically
    4. Learns from mistakes
    
    Usage:
        executor = EnhancedExecutor()
        result = executor.execute("fix the vllm timeout issue")
        print(result.output)
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        
        # Core components
        self.brain = get_brain()
        self.autonomous_brain = get_autonomous_brain(self.brain)
        self.context_builder = AutoContextBuilder(str(self.project_root))
        self.editor = get_editor(str(self.project_root))
        self.repo_map = get_repo_map(str(self.project_root))
        
        # Scan repo on init
        self.repo_map.scan()
        
        logger.info(f"EnhancedExecutor initialized for {self.project_root}")
        logger.info(f"RepoMap: {len(self.repo_map.files)} files indexed")
    
    @healing(max_retries=3, log_errors=True)
    def execute(self, prompt: str) -> ExecutionResult:
        """
        Execute a user prompt with full enhancement.
        
        Args:
            prompt: Natural language request
            
        Returns:
            ExecutionResult with details
        """
        result = ExecutionResult(success=False, output="")
        
        # Step 1: Understand intent
        plan, confidence = self.autonomous_brain.understand_with_confidence(prompt)
        logger.info(f"Intent: {plan.intent.value}, Confidence: {confidence:.2f}")
        
        # Step 2: Auto-discover relevant files
        if self._needs_file_context(prompt, plan.intent):
            context = self.context_builder.build_context(prompt)
            result.files_discovered = len(context.files)
            
            if context.files:
                logger.info(f"Auto-loaded {len(context.files)} files")
                
                # Step 3: Execute with context
                success, output = self._execute_with_context(prompt, context, plan)
                result.success = success
                result.output = output
                
                # Parse edit stats from output
                result.edits_applied = output.count("✅")
                result.edits_failed = output.count("❌")
                
                return result
        
        # Step 4: For non-code tasks, use standard execution
        success, output = self.autonomous_brain.execute_autonomously(plan, confidence)
        result.success = success
        result.output = output
        
        return result
    
    def _needs_file_context(self, prompt: str, intent: Intent) -> bool:
        """Determine if this query needs file context"""
        prompt_lower = prompt.lower()
        
        # Keywords that indicate code/file work
        code_keywords = [
            'file', 'code', 'function', 'class', 'method', 'module',
            'fix', 'edit', 'change', 'update', 'modify', 'refactor',
            'add', 'create', 'implement', 'bug', 'error', 'issue',
            'read', 'show', 'view', 'explain', 'analyze', 'check',
            'ryxsurf', 'ryx', 'agent', 'brain', 'core', 'tool',
            'config', 'test', 'api', 'client', 'server', 'model',
            '.py', '.js', '.ts', 'import', 'def ', 'class '
        ]
        
        if any(kw in prompt_lower for kw in code_keywords):
            return True
        
        # Intent-based
        context_intents = {
            Intent.CODE_TASK, Intent.EXPLORE_REPO, Intent.FIND_FILE,
            Intent.FIND_PATH, Intent.CHAT
        }
        
        return intent in context_intents
    
    def _execute_with_context(
        self, 
        prompt: str, 
        context: ContextResult,
        plan
    ) -> Tuple[bool, str]:
        """Execute with file context loaded"""
        from core.vllm_client import VLLMClient, VLLMConfig
        
        # Build enhanced prompt
        enhanced_prompt = self._build_enhanced_prompt(prompt, context)
        
        # Call LLM
        config = VLLMConfig(base_url='http://localhost:8001')
        client = VLLMClient(config)
        
        async def _generate():
            system_prompt = self._get_system_prompt()
            
            resp = await client.generate(
                prompt=enhanced_prompt,
                system=system_prompt,
                max_tokens=2500,
                temperature=0.3
            )
            await client.close()
            return resp
        
        response = asyncio.run(_generate())
        
        if response.error:
            return False, f"LLM error: {response.error}"
        
        # Process response
        return self._process_response(response.response)
    
    def _build_enhanced_prompt(self, prompt: str, context: ContextResult) -> str:
        """Build prompt with context"""
        # For RyxSurf development, always mention the main files
        hint = ""
        if "action" in prompt.lower() or "browser" in prompt.lower() or "method" in prompt.lower():
            hint = """
HINT: For browser actions, the main file is ryxsurf/src/ai/actions.py (BrowserActions class).
For browser UI methods, use ryxsurf/src/core/browser.py (Browser class).
"""
        
        return f"""I have automatically discovered and loaded relevant files for your request.

{context.to_prompt()}
{hint}
User request: {prompt}

CRITICAL INSTRUCTIONS FOR EDITING:
1. The <old> text MUST be copied EXACTLY from the file content above - character for character
2. Do NOT paraphrase, reformat, or summarize the <old> text
3. Include enough context in <old> to be unique (usually 3-10 lines)
4. For adding new code, use the END of an existing function/method as your <old> anchor
5. Pick a simple, short anchor point - don't try to match huge blocks

For edits, use this format:
<edit>
<file>path/to/file.py</file>
<old>
EXACT lines copied from file above
</old>
<new>
same lines plus your additions
</new>
</edit>

If you cannot find suitable anchor text, say "I cannot find the right location" instead of guessing."""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for code tasks"""
        return """You are Ryx, an expert coding assistant. You ALWAYS attempt to make edits when asked.

RULES:
1. The file contents in <file> tags are the ONLY source of truth
2. When editing, the <old> text MUST match the file EXACTLY
3. Copy text directly from the context - do not paraphrase
4. For adding code, use the last few lines of an existing function/block as your anchor
5. Always try to make the edit - only say "cannot find" if the file content is clearly missing
6. DO NOT use markdown code fences (```) inside <old> or <new> tags

FORMAT for edits (NO code fences!):
<edit>
<file>path/to/file.py</file>
<old>
exact lines from file
</old>
<new>
same lines plus additions
</new>
</edit>

Be aggressive about finding anchor points. Look for unique strings like function names, class names, or specific values."""
    
    def _process_response(self, response: str) -> Tuple[bool, str]:
        """Process LLM response and apply any edits"""
        
        # Clean up common LLM output issues
        response = self._clean_llm_response(response)
        
        # Parse edit blocks
        edit_pattern = r'<edit>\s*<file>(.*?)</file>\s*<old>(.*?)</old>\s*<new>(.*?)</new>\s*</edit>'
        edits = re.findall(edit_pattern, response, re.DOTALL)
        
        if not edits:
            # No edits - return the response as explanation
            return True, response
        
        # Apply edits using reliable editor
        results = []
        all_success = True
        applied_to_files = set()  # Track which files we've edited
        
        for file_path, old_str, new_str in edits:
            file_path = file_path.strip()
            old_str = self._clean_code_block(old_str.strip())
            new_str = self._clean_code_block(new_str.strip())
            
            # Skip duplicate edits to same file (LLM sometimes generates multiple)
            edit_key = f"{file_path}:{hash(new_str)}"
            if edit_key in applied_to_files:
                logger.debug(f"Skipping duplicate edit to {file_path}")
                continue
            
            # Apply with multi-strategy matching
            result = self.editor.edit(file_path, old_str, new_str)
            
            if result.success:
                applied_to_files.add(edit_key)
                strategy = result.strategy_used or "unknown"
                results.append(f"✅ Edited: {file_path} ({strategy})")
                logger.info(f"Edit applied to {file_path} using {strategy}")
            else:
                results.append(f"❌ Failed: {file_path} - {result.message}")
                all_success = False
                logger.warning(f"Edit failed for {file_path}: {result.message}")
        
        return all_success, "\n".join(results)
    
    def _clean_llm_response(self, response: str) -> str:
        """Clean common LLM output issues"""
        # Remove markdown code fences from inside tags
        response = re.sub(r'<old>\s*```\w*\n?', '<old>', response)
        response = re.sub(r'\n?```\s*</old>', '</old>', response)
        response = re.sub(r'<new>\s*```\w*\n?', '<new>', response)
        response = re.sub(r'\n?```\s*</new>', '</new>', response)
        return response
    
    def _clean_code_block(self, code: str) -> str:
        """Remove markdown code fences from code"""
        # Remove leading ```python or ```
        code = re.sub(r'^```\w*\n?', '', code)
        # Remove trailing ```
        code = re.sub(r'\n?```$', '', code)
        return code
        
        return all_success, "\n".join(results)
    
    def find_symbols(self, name: str) -> List[Dict]:
        """Find symbols by name (for debugging/exploration)"""
        symbols = self.repo_map.find_symbol(name)
        return [
            {
                'name': s.name,
                'kind': s.kind,
                'file': s.file,
                'line': s.line,
                'signature': s.signature
            }
            for s in symbols
        ]
    
    def get_repo_summary(self) -> str:
        """Get a summary of the repository structure"""
        return self.repo_map.get_summary(max_files=30)


# Global instance
_enhanced_executor: Optional[EnhancedExecutor] = None


def get_enhanced_executor(project_root: str = None) -> EnhancedExecutor:
    """Get or create the enhanced executor"""
    global _enhanced_executor
    if _enhanced_executor is None:
        _enhanced_executor = EnhancedExecutor(project_root)
    return _enhanced_executor


def execute(prompt: str) -> ExecutionResult:
    """Convenience function for quick execution"""
    return get_enhanced_executor().execute(prompt)
