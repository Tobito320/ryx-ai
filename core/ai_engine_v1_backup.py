"""
Ryx AI - Core AI Engine
Handles model selection, loading, and inference
"""

import json
import time
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ModelSpec:
    """Model specification with metadata"""
    name: str
    size: str
    use_case: str
    max_latency_ms: int
    priority: int

class AIEngine:
    """V1 AI Engine for model management and inference (backup)"""

    def __init__(self) -> None:
        """Initialize AI engine with model specs and configuration"""
        self.config_dir = Path.home() / "ryx-ai" / "configs"
        self.models_config = self.load_config("models.json")
        self.settings = self.load_config("settings.json")
        
        self.ollama_url = "http://localhost:11434"
        self.current_model = None
        self.model_specs = self.parse_model_specs()
        
    def load_config(self, filename: str) -> Dict:
        """Load configuration file"""
        config_path = self.config_dir / filename
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def parse_model_specs(self) -> Dict[str, ModelSpec]:
        """Parse model specifications"""
        specs = {}
        for name, config in self.models_config["models"].items():
            specs[name] = ModelSpec(**config)
        return specs
    
    def select_model(self, query: str, context: Dict = None) -> str:
        """
        Intelligently select model based on query complexity
        
        Simple query -> fast model
        Complex query -> powerful model
        """
        if not self.models_config.get("auto_select", True):
            # Use default from settings
            default = self.settings["ai"]["default_model"]
            return self.model_specs[default].name
        
        # Analyze query complexity
        complexity = self.analyze_complexity(query, context)
        
        if complexity < 0.3:
            return self.model_specs["fast"].name
        elif complexity < 0.7:
            return self.model_specs["balanced"].name
        else:
            return self.model_specs["powerful"].name
    
    def analyze_complexity(self, query: str, context: Dict = None) -> float:
        """
        Analyze query complexity (0.0 - 1.0)
        
        Factors:
        - Query length
        - Keywords indicating complexity
        - Context size
        """
        score = 0.0
        
        # Length factor
        words = query.split()
        if len(words) < 5:
            score += 0.1
        elif len(words) < 15:
            score += 0.3
        else:
            score += 0.5
        
        # Complexity keywords
        complex_keywords = [
            "explain", "analyze", "compare", "refactor",
            "optimize", "debug", "architect", "design"
        ]
        
        simple_keywords = [
            "open", "find", "show", "list", "get"
        ]
        
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in complex_keywords):
            score += 0.4
        
        if any(kw in query_lower for kw in simple_keywords):
            score -= 0.2
        
        # Context factor
        if context and len(str(context)) > 1000:
            score += 0.3
        
        return max(0.0, min(1.0, score))
    
    def query(self, 
              prompt: str, 
              system_context: str = "",
              model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the AI model
        
        Returns:
            {
                "response": str,
                "model": str,
                "latency_ms": int,
                "cached": bool
            }
        """
        start_time = time.time()
        
        # Select model
        if model_override:
            model_name = model_override
        else:
            model_name = self.select_model(prompt, {"system": system_context})
        
        # Build system prompt
        system_prompt = self.build_system_prompt(system_context)
        
        # Make request
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\nUser: {prompt}",
                    "stream": False,
                    "options": {
                        "temperature": self.settings["ai"]["temperature"],
                        "num_predict": self.settings["ai"]["max_tokens"]
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "response": f"Error: AI service returned {response.status_code}",
                    "model": model_name,
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "cached": False,
                    "error": True
                }
            
            data = response.json()
            ai_response = data.get("response", "")
            
            # Post-process for compactness
            if self.settings["ai"]["compact_responses"]:
                ai_response = self.make_compact(ai_response)
            
            return {
                "response": ai_response,
                "model": model_name,
                "latency_ms": int((time.time() - start_time) * 1000),
                "cached": False,
                "error": False
            }
            
        except requests.exceptions.ConnectionError:
            return {
                "response": "Error: Cannot connect to Ollama. Is it running?",
                "model": None,
                "latency_ms": 0,
                "cached": False,
                "error": True
            }
        except Exception as e:
            return {
                "response": f"Error: {str(e)}",
                "model": model_name,
                "latency_ms": int((time.time() - start_time) * 1000),
                "cached": False,
                "error": True
            }
    
    def build_system_prompt(self, context: str = "") -> str:
        """Build compact system prompt"""
        base = """You are Ryx, an ultra-efficient Arch Linux CLI assistant.

CRITICAL RULES:
1. Be EXTREMELY COMPACT - no fluff, no repetition
2. For file operations: give EXACT bash commands in ```bash blocks
3. For questions: answer in 1-2 sentences max
4. NEVER explain what you're doing - just do it
5. Use full paths always

"""
        
        if context:
            base += f"CONTEXT:\n{context}\n\n"
        
        return base
    
    def make_compact(self, response: str) -> str:
        """
        Remove verbosity from AI responses
        
        Before: "I'll help you open the Hyprland config. Let me find it..."
        After: "```bash\nnvim ~/.config/hyprland/hyprland.conf\n```"
        """
        # Remove common filler phrases
        fillers = [
            "I'll help you",
            "Let me",
            "I can",
            "I will",
            "Sure,",
            "Certainly,",
            "Of course,",
            "Here's how",
            "You can"
        ]
        
        lines = response.split('\n')
        cleaned = []
        
        for line in lines:
            # Skip lines that are just filler
            if any(filler in line for filler in fillers) and len(line) < 100:
                continue
            cleaned.append(line)
        
        return '\n'.join(cleaned).strip()
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> list:
        """List installed models"""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except:
            return []


# ===================================
# Response Formatter
# ===================================

class ResponseFormatter:
    """Format AI responses for beautiful terminal output"""
    
    @staticmethod
    def format_cli(response: str, show_model: bool = False) -> str:
        """
        Format response for CLI mode
        
        Extracts bash commands and highlights them
        """
        lines = response.split('\n')
        output = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if not in_code_block:
                    output.append('')  # Add newline after code block
                continue
            
            if in_code_block:
                # This is a command - highlight it
                output.append(f"  \033[1;36m{line}\033[0m")
            elif line.strip():
                # Regular text
                output.append(f"\033[0;37m{line}\033[0m")
        
        return '\n'.join(output)
    
    @staticmethod
    def extract_commands(response: str) -> list:
        """Extract bash commands from response"""
        commands = []
        in_code_block = False
        current_block = []
        
        for line in response.split('\n'):
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of block
                    if current_block:
                        commands.append('\n'.join(current_block))
                        current_block = []
                in_code_block = not in_code_block
                continue
            
            if in_code_block and line.strip():
                current_block.append(line.strip())
        
        return commands