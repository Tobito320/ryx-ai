"""
Ryx AI - AI Command Interpreter

Uses LLM to understand user intent and return structured actions.
NO hardcoded patterns, keywords, or regex. Pure AI understanding.
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class AIAction:
    """Structured action returned by AI interpretation"""
    action_type: str  # 'start_service', 'stop_service', 'status', 'chat', 'file_op', 'search', etc.
    target: Optional[str] = None  # Service name, file path, search query, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""
    original_prompt: str = ""


class AICommandInterpreter:
    """
    Interprets user commands using AI - no hardcoded patterns.
    
    The LLM decides what the user wants based on context and natural language.
    """
    
    INTERPRETATION_PROMPT = '''You are a command interpreter for Ryx AI, a local AI assistant.
Your job is to understand what the user wants and return a structured JSON action.

Available actions:
- start_service: Start a service (target: "ryxhub", "session", "backend", "frontend")
- stop_service: Stop a service (target: service name)
- service_status: Check service status (target: optional service name)
- open_file: Open/edit a file (target: file description or path)
- find_file: Find/locate a file (target: what to find)
- search_web: Search the web (target: search query)
- run_command: Execute a shell command (target: command, parameters.confirm: true/false)
- chat: General conversation (target: null)
- code_help: Help with code (target: description of what's needed)
- system_task: System maintenance task (target: "health", "cleanup", "logs", etc.)
- self_heal: Clean up AI knowledge/cache to improve performance (target: null, parameters.aggressive: true/false)
- remember: Store something in long-term memory (target: what to remember, parameters.type: "preference"/"fact"/"task")
- recall: Recall information from memory (target: what to recall)

Respond with ONLY a JSON object (no markdown, no explanation):
{{"action_type": "<action>", "target": "<target or null>", "parameters": {{}}, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

Examples:
User: "start ryxhub" -> {{"action_type": "start_service", "target": "ryxhub", "parameters": {{}}, "confidence": 1.0, "reasoning": "User wants to start RyxHub service"}}
User: "can you please start the web interface" -> {{"action_type": "start_service", "target": "ryxhub", "parameters": {{}}, "confidence": 0.95, "reasoning": "Web interface refers to RyxHub"}}
User: "fire up the hub" -> {{"action_type": "start_service", "target": "ryxhub", "parameters": {{}}, "confidence": 0.9, "reasoning": "Hub is RyxHub, fire up means start"}}
User: "strat ryxhb" -> {{"action_type": "start_service", "target": "ryxhub", "parameters": {{}}, "confidence": 0.85, "reasoning": "Typos for start ryxhub"}}
User: "what's the weather" -> {{"action_type": "search_web", "target": "current weather", "parameters": {{}}, "confidence": 0.9, "reasoning": "Weather query needs web search"}}
User: "open my hyprland config" -> {{"action_type": "open_file", "target": "hyprland config", "parameters": {{}}, "confidence": 0.95, "reasoning": "User wants to open hyprland configuration"}}
User: "how are you" -> {{"action_type": "chat", "target": null, "parameters": {{}}, "confidence": 1.0, "reasoning": "General greeting/conversation"}}
User: "fix your brain" -> {{"action_type": "self_heal", "target": null, "parameters": {{}}, "confidence": 0.95, "reasoning": "User wants AI to clean up its knowledge"}}
User: "clean up your knowledge" -> {{"action_type": "self_heal", "target": null, "parameters": {{}}, "confidence": 0.95, "reasoning": "User wants cache cleanup"}}
User: "you're getting dumb, fix yourself" -> {{"action_type": "self_heal", "target": null, "parameters": {{"aggressive": true}}, "confidence": 0.9, "reasoning": "User frustrated, needs aggressive cleanup"}}
User: "remember that I prefer nvim" -> {{"action_type": "remember", "target": "user prefers nvim as editor", "parameters": {{"type": "preference", "key": "editor", "value": "nvim"}}, "confidence": 0.95, "reasoning": "User wants to store editor preference"}}
User: "my project is at ~/code/myapp" -> {{"action_type": "remember", "target": "project location ~/code/myapp", "parameters": {{"type": "fact"}}, "confidence": 0.9, "reasoning": "User sharing project location to remember"}}
User: "what do you know about me" -> {{"action_type": "recall", "target": "user profile and preferences", "parameters": {{}}, "confidence": 0.9, "reasoning": "User wants to see stored memories"}}

User prompt: "{prompt}"
'''

    def __init__(self, ollama_client=None):
        """
        Initialize interpreter.
        
        Args:
            ollama_client: OllamaClient instance for AI queries
        """
        self.ollama = ollama_client
        self._ensure_client()
    
    def _ensure_client(self):
        """Ensure we have an Ollama client"""
        if self.ollama is None:
            from core.ollama_client import OllamaClient
            self.ollama = OllamaClient()
    
    def interpret(self, prompt: str, context: Optional[Dict] = None) -> AIAction:
        """
        Interpret user prompt using AI.
        
        Args:
            prompt: User's natural language input
            context: Optional conversation context
            
        Returns:
            AIAction with structured interpretation
        """
        self._ensure_client()
        
        # Build the interpretation prompt
        full_prompt = self.INTERPRETATION_PROMPT.format(prompt=prompt)
        
        # Add context if available
        if context:
            context_str = f"\nContext: {json.dumps(context)}\n"
            full_prompt = full_prompt.replace('User prompt:', f'{context_str}User prompt:')
        
        # Query AI for interpretation
        response = self.ollama.generate(
            prompt=full_prompt,
            model="qwen2.5:3b",  # 3B model for better interpretation
            system="You are a JSON command parser. Return ONLY valid JSON, no markdown or explanation.",
            max_tokens=200
        )
        
        if response.error:
            # On error, default to chat
            return AIAction(
                action_type="chat",
                original_prompt=prompt,
                reasoning=f"AI interpretation failed: {response.error}"
            )
        
        # Parse JSON response
        try:
            # Clean response (remove markdown if present)
            clean_response = response.response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip()
            
            data = json.loads(clean_response)
            
            return AIAction(
                action_type=data.get("action_type", "chat"),
                target=data.get("target"),
                parameters=data.get("parameters", {}),
                confidence=data.get("confidence", 0.8),
                reasoning=data.get("reasoning", ""),
                original_prompt=prompt
            )
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract action from text
            return self._fallback_parse(response.response, prompt)
    
    def _fallback_parse(self, response: str, prompt: str) -> AIAction:
        """
        Fallback parsing when JSON fails.
        Uses simple text analysis of AI response.
        """
        response_lower = response.lower()
        
        # Check if AI mentioned specific actions in its response
        if "start" in response_lower and ("ryxhub" in response_lower or "service" in response_lower):
            return AIAction(
                action_type="start_service",
                target="ryxhub",
                confidence=0.7,
                reasoning="Fallback: detected start service intent",
                original_prompt=prompt
            )
        elif "stop" in response_lower and ("ryxhub" in response_lower or "service" in response_lower):
            return AIAction(
                action_type="stop_service", 
                target="ryxhub",
                confidence=0.7,
                reasoning="Fallback: detected stop service intent",
                original_prompt=prompt
            )
        
        # Default to chat
        return AIAction(
            action_type="chat",
            original_prompt=prompt,
            confidence=0.5,
            reasoning="Fallback: could not parse AI response, defaulting to chat"
        )


# Global interpreter instance
_interpreter: Optional[AICommandInterpreter] = None


def get_interpreter() -> AICommandInterpreter:
    """Get or create global interpreter instance"""
    global _interpreter
    if _interpreter is None:
        _interpreter = AICommandInterpreter()
    return _interpreter


def interpret_command(prompt: str, context: Optional[Dict] = None) -> AIAction:
    """
    Convenience function to interpret a command.
    
    Args:
        prompt: User's natural language input
        context: Optional conversation context
        
    Returns:
        AIAction with structured interpretation
    """
    return get_interpreter().interpret(prompt, context)
