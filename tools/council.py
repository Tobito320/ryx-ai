# Extract Council class from ryx_tools.py

from typing import List, Dict, Optional
import requests
import json
import re

# ===================================
# Council (Multi-Model Consensus)
# ===================================

class Council:
    """
    Multi-model consensus system
    
    Runs same prompt through multiple models and compares responses
    Useful for code review, fact-checking, etc.
    """
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.available_models = self._get_available_models()
    
    def _get_available_models(self) -> List[str]:
        """Get list of installed models"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                # Filter for small models (< 10GB)
                return [m for m in models if self._is_small_model(m)]
            return []
        except:
            return []
    
    def _is_small_model(self, model_name: str) -> bool:
        """Check if model is small enough for council"""
        # Simple heuristic based on name
        small_indicators = ["7b", "6.7b", "3b", "mini", "small"]
        return any(ind in model_name.lower() for ind in small_indicators)
    
    def vote(self, prompt: str, task_type: str = "review"):
        """
        Run prompt through multiple models and collect responses
        
        task_type: 'review', 'rate', 'analyze'
        """
        if len(self.available_models) < 2:
            print("\033[1;33m⚠\033[0m Need at least 2 models for council")
            print("  Install more models with: ollama pull <model>")
            return
        
        print()
        print("\033[1;36m╭──────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  🏛️  Council Session                │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────╯\033[0m")
        print()
        print(f"\033[1;36mModels participating:\033[0m {len(self.available_models)}")
        for model in self.available_models:
            print(f"  • {model}")
        print()
        
        # Build task-specific system prompt
        if task_type == "review":
            system_prompt = """You are a code reviewer. Review this code and:
1. Rate quality (1-10)
2. List issues
3. Suggest improvements

Be concise and critical."""
        
        elif task_type == "rate":
            system_prompt = """Rate this on a scale of 1-10 and explain why.
Be honest and critical. Focus on flaws."""
        
        else:
            system_prompt = "Analyze this critically."
        
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Collect responses
        responses = []
        
        for i, model in enumerate(self.available_models, 1):
            print(f"\033[1;33m[{i}/{len(self.available_models)}]\033[0m Querying {model}...")
            
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    responses.append({
                        "model": model,
                        "response": data.get("response", "")
                    })
                    print(f"\033[1;32m✓\033[0m Got response")
                else:
                    print(f"\033[1;31m✗\033[0m Failed")
            
            except Exception as e:
                print(f"\033[1;31m✗\033[0m Error: {e}")
        
        print()
        
        # Display results
        self._display_council_results(responses, task_type)
    
    def _display_council_results(self, responses: List[Dict], task_type: str):
        """Display council voting results"""
        print("\033[1;36m╭──────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  📊 Council Results                  │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────╯\033[0m")
        print()
        
        for i, resp in enumerate(responses, 1):
            print(f"\033[1;33m[{resp['model']}]\033[0m")
            print()
            
            # Extract rating if present
            rating = self._extract_rating(resp['response'])
            if rating:
                print(f"\033[1;36mRating:\033[0m {rating}/10")
                print()
            
            # Show response
            print(resp['response'][:500])
            if len(resp['response']) > 500:
                print("...")
            
            print()
            print("-" * 60)
            print()
        
        # Consensus summary
        if len(responses) >= 2:
            print("\033[1;36m📋 Consensus:\033[0m")
            
            ratings = [self._extract_rating(r['response']) for r in responses]
            ratings = [r for r in ratings if r is not None]
            
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                print(f"  Average rating: \033[1;37m{avg_rating:.1f}/10\033[0m")
            
            print()
    
    def _extract_rating(self, text: str) -> Optional[float]:
        """Try to extract numeric rating from text"""
        import re
        
        # Look for patterns like "8/10", "Rating: 7", "Score: 6"
        patterns = [
            r'(\d+)/10',
            r'[Rr]ating:?\s*(\d+)',
            r'[Ss]core:?\s*(\d+)',
            r'(\d+)\s*out of 10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        return None