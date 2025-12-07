"""
Direct Executor - Main execution path for Ryx AI

Features:
- Automatic context discovery (no manual file adding!)
- Autonomous execution with confidence scoring
- Self-healing retry logic
- Bypasses supervisor for direct LLM interaction
"""

import os
import logging
from typing import Tuple
from core.ryx_brain import get_brain, Intent
from core.autonomous_brain import get_autonomous_brain
from core.auto_context import AutoContextBuilder, ContextResult

logger = logging.getLogger(__name__)


class DirectExecutor:
    """
    Direct execution path with automatic context discovery.
    
    This is what makes Ryx better than Aider/Claude Code:
    - User NEVER adds files manually
    - Ryx automatically finds and loads relevant files
    - LLM gets full context to make edits
    
    Flow:
    1. User prompt → Extract intent
    2. Auto-discover relevant files
    3. Build context with file contents
    4. Send to LLM with full context
    5. Execute autonomously (with retry)
    """
    
    def __init__(self):
        # Get base brain
        self.base_brain = get_brain()
        
        # Wrap with autonomous capabilities
        self.autonomous_brain = get_autonomous_brain(self.base_brain)
        
        # Context builder for auto file discovery
        self.context_builder = AutoContextBuilder(os.getcwd())
        
        logger.info("DirectExecutor initialized with auto-context")
    
    def execute(self, prompt: str) -> Tuple[bool, str]:
        """
        Execute a prompt autonomously with auto-discovered context.
        
        Args:
            prompt: User's request
            
        Returns:
            (success, result_message)
        """
        try:
            # First, understand the intent
            plan, confidence = self.autonomous_brain.understand_with_confidence(prompt)
            
            logger.info(f"Intent: {plan.intent.value}, Confidence: {confidence:.2f}")
            
            # Check if this query might benefit from file context
            # This is aggressive - we load context for most queries
            needs_context = self._might_need_file_context(prompt, plan.intent)
            
            if needs_context:
                context_result = self.context_builder.build_context(prompt)
                
                if context_result.files:
                    logger.info(f"Auto-loaded {len(context_result.files)} files")
                    
                    # Enhance the prompt with file context
                    enhanced_prompt = self._build_enhanced_prompt(prompt, context_result)
                    
                    # Execute with enhanced context
                    return self._execute_with_context(enhanced_prompt, plan, confidence)
            
            # For other intents, use standard execution
            success, result = self.autonomous_brain.execute_autonomously(plan, confidence)
            
            return success, result
            
        except Exception as e:
            logger.error(f"DirectExecutor error: {e}")
            return False, f"Execution failed: {e}"
    
    def _might_need_file_context(self, prompt: str, intent: Intent) -> bool:
        """
        Determine if a query might benefit from file context.
        
        We're aggressive here - better to load context than not have it.
        """
        # These intents definitely need context
        context_intents = {
            Intent.CODE_TASK, Intent.EXPLORE_REPO, Intent.FIND_FILE,
            Intent.FIND_PATH, Intent.CHAT  # Even CHAT might be about code
        }
        
        if intent in context_intents:
            # Check if prompt mentions anything code-related
            code_keywords = [
                'file', 'code', 'function', 'class', 'method', 'module',
                'fix', 'edit', 'change', 'update', 'modify', 'refactor',
                'add', 'create', 'implement', 'bug', 'error', 'issue',
                'read', 'show', 'view', 'explain', 'what', 'how', 'why',
                'ryxsurf', 'ryx', 'agent', 'brain', 'core', 'tool',
                'config', 'test', 'api', 'client', 'server', 'model',
                '.py', '.js', '.ts', 'import', 'def ', 'class '
            ]
            
            prompt_lower = prompt.lower()
            return any(kw in prompt_lower for kw in code_keywords)
        
        return False
    
    def _build_enhanced_prompt(self, original_prompt: str, context: ContextResult) -> str:
        """Build prompt with auto-discovered file context"""
        
        # System context
        enhanced = f"""I have automatically discovered and loaded relevant files for your request.

{context.to_prompt()}

User request: {original_prompt}

You can now read the file contents above and make precise edits. When editing, use exact string matching."""
        
        return enhanced
    
    def _execute_with_context(
        self, 
        enhanced_prompt: str, 
        plan, 
        confidence: float
    ) -> Tuple[bool, str]:
        """Execute with file context loaded"""
        
        # Use the brain's LLM to generate response with full context
        from core.vllm_client import VLLMClient, VLLMConfig
        
        config = VLLMConfig(base_url='http://localhost:8001')
        client = VLLMClient(config)
        
        import asyncio
        
        async def _generate():
            system_prompt = """You are Ryx, an expert coding assistant. You have access to the files shown in the context.

When asked to make changes:
1. Analyze the relevant files
2. Identify what needs to change
3. Output precise edits using this format:

<edit>
<file>path/to/file.py</file>
<old>exact text to replace</old>
<new>new text</new>
</edit>

Be surgical - only change what's necessary. Never rewrite entire files."""

            resp = await client.generate(
                prompt=enhanced_prompt,
                system=system_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            await client.close()
            return resp
        
        response = asyncio.run(_generate())
        
        if response.error:
            return False, f"LLM error: {response.error}"
        
        # Check if response contains edits
        if '<edit>' in response.response:
            return self._apply_edits(response.response)
        
        # Otherwise return the response as-is
        return True, response.response
    
    def _apply_edits(self, response: str) -> Tuple[bool, str]:
        """Parse and apply edits from LLM response"""
        import re
        
        # Parse edit blocks
        edit_pattern = r'<edit>\s*<file>(.*?)</file>\s*<old>(.*?)</old>\s*<new>(.*?)</new>\s*</edit>'
        edits = re.findall(edit_pattern, response, re.DOTALL)
        
        if not edits:
            return True, response  # No edits found, return response
        
        results = []
        from core.tools import FileTool
        file_tool = FileTool()
        
        for file_path, old_str, new_str in edits:
            file_path = file_path.strip()
            old_str = old_str.strip()
            new_str = new_str.strip()
            
            result = file_tool.edit(file_path, old_str, new_str)
            
            if result.success:
                results.append(f"✅ Edited: {file_path}")
            else:
                results.append(f"❌ Failed to edit {file_path}: {result.error}")
        
        return True, "\n".join(results)


# Global instance
_executor = None


def get_direct_executor() -> DirectExecutor:
    """Get or create direct executor"""
    global _executor
    if _executor is None:
        _executor = DirectExecutor()
    return _executor
