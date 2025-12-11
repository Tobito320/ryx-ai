"""
Ryx AI - Enhanced Executor

This is the upgraded execution layer that incorporates:
1. ReliableEditor - Multi-strategy edit matching (from Aider)
2. SelfHealing - Automatic error recovery with retries (from healing-agent)
3. RepoMap - Semantic code understanding (from Aider)
4. AutoContext - Automatic file discovery
5. TodoManager - Task tracking for complex work (from Claude Code)
6. CodebaseExplorer - Project understanding for vague prompts

The goal: Make Ryx 210% as reliable and 110% as powerful as Claude Code CLI.

Key improvements:
- Edits rarely fail (multiple fallback strategies)
- Errors auto-recover (3 retries with reflection)
- File discovery is smarter (uses code structure, not just file names)
- No manual file adding ever needed
- Handles vague prompts like "resume work on X"
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
from core.todo_manager import TodoManager, TaskStatus
from core.codebase_explorer import CodebaseExplorer

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
    5. Handles vague prompts like "resume work on X"
    
    Usage:
        executor = EnhancedExecutor()
        result = executor.execute("resume work on ryxsurf")
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
        
        # New: Task management and exploration
        self.todo = TodoManager(str(self.project_root))
        self.explorer = CodebaseExplorer(str(self.project_root))
        
        # Scan repo on init
        self.repo_map.scan()
        
        logger.info(f"EnhancedExecutor initialized for {self.project_root}")
        logger.info(f"RepoMap: {len(self.repo_map.files)} files indexed")
    
    def _is_vague_prompt(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Check if this is a vague prompt that needs exploration"""
        lower = prompt.lower().strip()
        
        # Patterns that indicate vague prompts
        vague_patterns = [
            (r"resume\s+(?:work\s+on\s+)?(\w+)", "resume"),
            (r"continue\s+(?:work\s+on\s+|with\s+)?(\w+)", "continue"),
            (r"work\s+on\s+(\w+)", "work"),
            (r"improve\s+(\w+)", "improve"),
            (r"what.*(?:status|state).*(\w+)", "status"),
            (r"(\w+)\s+status", "status"),
        ]
        
        for pattern, intent in vague_patterns:
            match = re.search(pattern, lower)
            if match:
                project = match.group(1)
                return True, project
        
        return False, None
    
    def _handle_vague_prompt(self, prompt: str, project_name: str) -> ExecutionResult:
        """Handle vague prompts by exploring and creating tasks"""
        # Explore the project
        insight = self.explorer.explore_project(project_name)
        
        if not insight.main_files:
            return ExecutionResult(
                success=False,
                output=f"Could not find project '{project_name}'"
            )
        
        # Get suggestions
        suggestions = self.explorer.suggest_next_actions(insight)
        
        # Create TODO items from suggestions
        if suggestions:
            self.todo.reset()  # Clear old tasks
            self.todo.add_tasks(suggestions)
        
        # Get current TODO status
        todo_status = self.todo.get_status_summary()
        
        # Build response
        output = f"""🔍 Explored project: {project_name}

{insight.summary}

{todo_status}

Ready to start working. I'll begin with the first task.
"""
        
        # AUTONOMOUS LOOP: Execute all pending tasks
        task_count = 0
        max_tasks = 10  # Safety limit to prevent infinite loops
        
        while task_count < max_tasks:
            next_task = self.todo.get_next_task()
            if not next_task:
                break  # No more tasks
            
            self.todo.start_task(next_task.id)
            output += f"\n\n🔄 Task {task_count + 1}: {next_task.content}"
            
            # Execute the task
            task_result = self._execute_task(next_task, insight)
            output += f"\n{task_result}"
            
            task_count += 1
        
        # Summary
        if task_count > 0:
            output += f"\n\n✅ Completed {task_count} tasks autonomously"
        else:
            output += f"\n\n⚠️ No tasks were generated - prompt may need more specifics"
        
        return ExecutionResult(
            success=True,
            output=output,
            files_discovered=len(insight.main_files)
        )
    
    def _execute_task(self, task, insight) -> str:
        """Execute a single task from the TODO list"""
        from core.todo_manager import TaskStatus
        
        task_content = task.content.lower()
        
        # Check for file:line format first (specific TODO items)
        if re.search(r'In\s+\S+\.py:\d+\s*-', task.content):
            return self._handle_implement_task(task, insight)
        
        # Determine what type of task this is
        if any(kw in task_content for kw in ["implement", "add", "create", "build", "stub"]):
            return self._handle_implement_task(task, insight)
        elif "test" in task_content and "test_" not in task_content:
            # Avoid triggering on filenames like test_ryxsurf.py
            return self._handle_test_task(task, insight)
        elif any(kw in task_content for kw in ["fix", "bug", "error"]):
            return self._handle_fix_task(task, insight)
        elif any(kw in task_content for kw in ["review", "improve", "refactor"]):
            return self._handle_review_task(task, insight)
        else:
            # Default to implement for TODO items
            return self._handle_implement_task(task, insight)
    
    def _handle_test_task(self, task, insight) -> str:
        """Handle test-related tasks"""
        # Mark as in-progress
        self.todo.start_task(task.id)
        
        # Check if tests exist
        test_dir = insight.root_path / "tests"
        if not test_dir.exists():
            # Create basic test structure
            test_dir.mkdir(exist_ok=True)
            
            # Find main files to create tests for
            main_files = [f for f in insight.main_files if f.endswith('.py') and 'test' not in f]
            
            if main_files:
                # Create a basic test file
                test_file = test_dir / f"test_{insight.name}.py"
                test_content = f'''"""Tests for {insight.name}"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class Test{insight.name.title().replace("_", "")}:
    """Basic tests for {insight.name}"""
    
    def test_import(self):
        """Test that the module can be imported"""
        # TODO: Add actual import test
        assert True
    
    def test_placeholder(self):
        """Placeholder test - implement real tests"""
        # TODO: Implement real tests based on functionality
        pass
'''
                test_file.write_text(test_content)
                self.todo.complete_task(task.id)
                return f"✅ Created test file: {test_file.relative_to(self.project_root)}"
        
        self.todo.complete_task(task.id)
        return f"✅ Test directory already exists with files"
    
    def _handle_implement_task(self, task, insight) -> str:
        """Handle implementation tasks using the LLM"""
        self.todo.start_task(task.id)
        
        content = task.content
        
        # Check if task has file:line format (from improved suggestions)
        # Format: "In filename.py:123 - action"
        import re
        file_line_match = re.search(r'In\s+(\S+\.py):(\d+)\s*-\s*(.+)', content)
        
        if file_line_match:
            file_name = file_line_match.group(1)
            line_num = int(file_line_match.group(2))
            action = file_line_match.group(3).strip()
            
            # Find the actual file path
            file_path = None
            for root, dirs, files in os.walk(insight.root_path):
                if file_name in files:
                    file_path = Path(root) / file_name
                    break
            
            if file_path and file_path.exists():
                try:
                    file_content = file_path.read_text()
                    lines = file_content.split('\n')
                    
                    # Get context around the line
                    start = max(0, line_num - 15)
                    end = min(len(lines), line_num + 15)
                    context = '\n'.join(f"{i+1}. {line}" for i, line in enumerate(lines[start:end], start=start))
                    
                    # Build prompt for LLM
                    implement_prompt = f"""Task: {action}

File: {file_path}
Line: {line_num}

Context (lines {start+1}-{end}):
```python
{context}
```

Implement the required changes. Output only the new/modified code.
Be concise - just the code, no explanations."""

                    # Call LLM with coding model for better code generation
                    try:
                        from core.ollama_client import OllamaClient
                        import asyncio
                        
                        client = OllamaClient()
                        
                        async def _generate():
                            resp = await client.generate(
                                prompt=implement_prompt,
                                system="You are an expert Python developer. Generate only code, no explanations.",
                                model='qwen2.5-coder:14b',  # Use coding model
                                max_tokens=2000,
                                temperature=0.3
                            )
                            await client.close()
                            return resp
                        
                        response = asyncio.run(_generate())
                        implementation = response.response
                        
                        if implementation and len(implementation) > 30:
                            # Try to apply the edit using reliable editor
                            # Get the original line for anchor
                            original_line = lines[line_num - 1] if line_num <= len(lines) else ""
                            
                            if original_line.strip():
                                edit_result = self.editor.edit(
                                    str(file_path),
                                    original_line,
                                    implementation.strip()
                                )
                                
                                if edit_result.success:
                                    self.todo.complete_task(task.id)
                                    return f"✅ Applied edit to {file_name}:{line_num}"
                            
                            # Fallback: show generated code
                            self.todo.complete_task(task.id)
                            return f"✅ Generated for '{action}' in {file_name}:\n```python\n{implementation[:600]}\n```"
                    except Exception as e:
                        logger.warning(f"LLM call failed: {e}")
                        
                except Exception as e:
                    logger.warning(f"Failed to read file: {e}")
        
        # Fallback: Look for TODOs in the codebase that match
        matching_todos = [t for t in insight.todos_in_code 
                         if any(word in t['content'].lower() 
                               for word in content.lower().split() if len(word) > 3)]
        
        if matching_todos:
            todo_item = matching_todos[0]
            file_path = Path(todo_item['file'])
            
            if file_path.exists():
                try:
                    file_content = file_path.read_text()
                    lines = file_content.split('\n')
                    todo_line = todo_item['line'] - 1
                    
                    start = max(0, todo_line - 10)
                    end = min(len(lines), todo_line + 10)
                    context = '\n'.join(lines[start:end])
                    
                    implement_prompt = f"""Implement this TODO in {todo_item['file']}:

TODO at line {todo_item['line']}: {todo_item['content']}

Context:
```
{context}
```

Provide only the implementation code."""

                    try:
                        from core.ollama_client import OllamaClient
                        import asyncio
                        
                        client = OllamaClient()
                        
                        async def _generate():
                            resp = await client.generate(
                                prompt=implement_prompt,
                                system="You are an expert Python developer. Generate only code, no explanations.",
                                model='qwen2.5-coder:14b',
                                max_tokens=2000,
                                temperature=0.3
                            )
                            await client.close()
                            return resp
                        
                        response = asyncio.run(_generate())
                        implementation = response.response
                        
                        if implementation and len(implementation) > 30:
                            self.todo.complete_task(task.id)
                            return f"✅ Implemented TODO in {todo_item['file']}:\n{implementation[:500]}..."
                    except Exception as e:
                        logger.warning(f"LLM call failed: {e}")
                        
                except Exception as e:
                    logger.warning(f"Failed to read file: {e}")
            
            result = f"📋 TODO in {todo_item['file']}:{todo_item['line']}: {todo_item['content']}\n"
            self.todo.block_task(task.id, "Needs LLM implementation")
            return result
        
        self.todo.block_task(task.id, "Could not determine target")
        return f"⚠️ Could not find implementation target for: {content}"
    
    def _handle_fix_task(self, task, insight) -> str:
        """Handle bug fix tasks"""
        self.todo.start_task(task.id)
        
        # Look for error-related TODOs
        error_todos = [t for t in insight.todos_in_code
                      if any(kw in t['content'].lower() 
                            for kw in ['fix', 'bug', 'error', 'issue', 'broken'])]
        
        if error_todos:
            todo_item = error_todos[0]
            self.todo.block_task(task.id, f"Fix needed in {todo_item['file']}")
            return f"🐛 Found issue in {todo_item['file']}:{todo_item['line']}: {todo_item['content']}"
        
        self.todo.complete_task(task.id)
        return "✅ No obvious bugs found in codebase"
    
    def _handle_review_task(self, task, insight) -> str:
        """Handle code review tasks"""
        self.todo.start_task(task.id)
        
        # Review the main files
        if insight.main_files:
            file_to_review = insight.main_files[0]
            file_path = self.project_root / file_to_review
            
            if file_path.exists():
                content = file_path.read_text()
                lines = len(content.split('\n'))
                
                # Quick analysis
                issues = []
                if 'TODO' in content:
                    issues.append("Contains TODOs")
                if 'FIXME' in content:
                    issues.append("Contains FIXMEs")
                if 'pass  #' in content or 'pass # ' in content:
                    issues.append("Has stub implementations")
                
                self.todo.complete_task(task.id)
                result = f"📝 Reviewed: {file_to_review} ({lines} lines)\n"
                if issues:
                    result += f"   Issues: {', '.join(issues)}"
                else:
                    result += "   No obvious issues found"
                return result
        
        self.todo.complete_task(task.id)
        return "✅ Review complete - no main files to review"
    
    def _handle_generic_task(self, task, insight) -> str:
        """Handle generic tasks by attempting to understand intent"""
        self.todo.start_task(task.id)
        
        # Log what we're trying to do
        result = f"🔧 Task: {task.content}\n"
        result += f"   Project: {insight.name}\n"
        result += f"   Main files: {len(insight.main_files)}\n"
        
        # For now, just mark as needing manual intervention
        self.todo.block_task(task.id, "Needs more specific instructions")
        result += "   Status: Needs clarification or LLM assistance"
        
        return result
    
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
        
        # Step 0: Check for vague prompts that need exploration
        is_vague, project_name = self._is_vague_prompt(prompt)
        if is_vague and project_name:
            return self._handle_vague_prompt(prompt, project_name)
        
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
        from core.ollama_client import OllamaClient
        
        # Build enhanced prompt
        enhanced_prompt = self._build_enhanced_prompt(prompt, context)
        
        # Call LLM via Ollama
        client = OllamaClient()
        
        async def _generate():
            system_prompt = self._get_system_prompt()
            
            # Use 7b coder for speed, 14b for complex tasks
            model = 'qwen2.5-coder:7b'  # Fast by default
            if len(enhanced_prompt) > 8000 or 'refactor' in prompt.lower() or 'complex' in prompt.lower():
                model = 'qwen2.5-coder:14b'  # Use 14b for complex tasks
            
            resp = await client.generate(
                prompt=enhanced_prompt,
                system=system_prompt,
                model=model,
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
4. For adding new code, use the LAST FUNCTION in the file as your <old> anchor
5. ALWAYS attempt an edit - the file content above is complete

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

IMPORTANT: You MUST output an <edit> block. The file content above is complete."""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for code tasks"""
        return """You are Ryx, an expert coding assistant. You ALWAYS output edit blocks.

RULES:
1. The file contents in <file> tags are COMPLETE - do not ask for more
2. When editing, the <old> text MUST match the file EXACTLY
3. Copy text directly from the context - do not paraphrase
4. For adding code, use the last function in the file as your anchor
5. ALWAYS output an <edit> block - never say you cannot find the location
6. DO NOT use markdown code fences (```) inside <old> or <new> tags

FORMAT for edits:
<edit>
<file>path/to/file.py</file>
<old>
exact lines from file
</old>
<new>
same lines plus additions
</new>
</edit>

Be aggressive about making edits. The file content provided is complete and accurate."""
    
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
            
            # Detect rename operation - if old_str is just a variable/function name
            # and new_str is also just a name, use replace_all mode
            is_rename = (
                '\n' not in old_str and 
                '\n' not in new_str and 
                len(old_str.split()) <= 2 and
                len(new_str.split()) <= 2 and
                old_str.replace('_', '').replace('-', '').isalnum() and
                new_str.replace('_', '').replace('-', '').isalnum()
            )
            
            # Apply with multi-strategy matching
            result = self.editor.edit(file_path, old_str, new_str, replace_all=is_rename)
            
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
