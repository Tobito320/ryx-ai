"""
Ryx AI - LLM Council

Multi-model consensus system for critical decisions.

Use cases:
1. Code review - multiple models review the same code
2. Security checks - consensus on safety of operations
3. Complex reasoning - when one model might be wrong
4. Quality assurance - verify LLM outputs before execution
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Types of council votes"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    CONDITIONAL = "conditional"  # Approve with conditions


@dataclass
class CouncilConfig:
    """Configuration for the council"""
    # Models to use
    models: List[str] = field(default_factory=lambda: [
        "qwen2.5-coder:7b",
        "deepseek-coder:6.7b", 
        "codellama:7b"
    ])
    
    # Voting settings
    min_votes: int = 2
    timeout_seconds: int = 30
    require_consensus: bool = False  # Require unanimous approval
    consensus_threshold: float = 0.6  # % needed to pass
    
    # Cost optimization
    only_on_uncertainty: bool = True  # Only activate when uncertain
    uncertainty_threshold: float = 0.7  # Confidence below this triggers council
    max_parallel: int = 3
    
    # Ollama settings
    ollama_url: str = "http://localhost:11434"


@dataclass
class CouncilVote:
    """A vote from a council member"""
    model: str
    vote: VoteType
    confidence: float  # 0.0 - 1.0
    reasoning: str
    suggestions: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    rating: Optional[float] = None  # 1-10 scale if applicable
    response_time_ms: int = 0


@dataclass
class ConsensusResult:
    """Result of a council vote"""
    approved: bool
    vote_count: Dict[str, int]  # VoteType -> count
    confidence: float  # Aggregate confidence
    votes: List[CouncilVote] = field(default_factory=list)
    consensus_type: str = "majority"  # majority, unanimous, weighted
    summary: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class LLMCouncil:
    """
    Multi-model consensus system.
    
    The council runs the same prompt through multiple models and
    aggregates their responses to make better decisions.
    
    Architecture:
    ```
    ┌─────────────────────────────────────────────┐
    │              Council Session                 │
    │  ┌────────────────────────────────────────┐ │
    │  │           Task/Question                 │ │
    │  └────────────────┬───────────────────────┘ │
    │                   │                         │
    │    ┌──────────────┼──────────────┐          │
    │    ▼              ▼              ▼          │
    │ ┌──────┐     ┌──────┐     ┌──────┐         │
    │ │Model1│     │Model2│     │Model3│         │
    │ │(qwen)│     │(deep)│     │(code)│         │
    │ └──┬───┘     └──┬───┘     └──┬───┘         │
    │    │            │            │              │
    │    ▼            ▼            ▼              │
    │ ┌──────┐     ┌──────┐     ┌──────┐         │
    │ │ Vote │     │ Vote │     │ Vote │         │
    │ └──┬───┘     └──┬───┘     └──┬───┘         │
    │    │            │            │              │
    │    └────────────┼────────────┘              │
    │                 ▼                           │
    │    ┌───────────────────────┐                │
    │    │   Vote Aggregation    │                │
    │    │   (Voting Strategy)   │                │
    │    └───────────┬───────────┘                │
    │                ▼                            │
    │    ┌───────────────────────┐                │
    │    │   Consensus Result    │                │
    │    └───────────────────────┘                │
    └─────────────────────────────────────────────┘
    ```
    """
    
    def __init__(
        self,
        config: Optional[CouncilConfig] = None,
        ollama_client = None
    ):
        self.config = config or CouncilConfig()
        self.ollama = ollama_client
        self._available_models: Optional[List[str]] = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_parallel)
    
    def get_available_models(self) -> List[str]:
        """Get list of installed models suitable for council"""
        if self._available_models is not None:
            return self._available_models
        
        try:
            import requests
            response = requests.get(
                f"{self.config.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                all_models = [m["name"] for m in data.get("models", [])]
                
                # Filter for suitable models (not too large)
                self._available_models = [
                    m for m in all_models 
                    if self._is_suitable_model(m)
                ]
                return self._available_models
        except Exception as e:
            logger.warning(f"Failed to get models: {e}")
        
        return self.config.models[:self.config.min_votes]
    
    def _is_suitable_model(self, model_name: str) -> bool:
        """Check if model is suitable for council (not too large)"""
        # Exclude very large models to keep council fast
        large_indicators = ["70b", "32b", "72b", "33b"]
        return not any(ind in model_name.lower() for ind in large_indicators)
    
    def vote(
        self,
        prompt: str,
        task_type: str = "review",
        context: Optional[Dict[str, Any]] = None
    ) -> ConsensusResult:
        """
        Run a council vote on a prompt.
        
        Args:
            prompt: The question/task for the council
            task_type: Type of task (review, security, quality, general)
            context: Additional context for the models
        
        Returns:
            ConsensusResult with aggregated votes
        """
        models = self._select_models()
        if len(models) < self.config.min_votes:
            logger.warning(f"Not enough models for council (need {self.config.min_votes})")
            return ConsensusResult(
                approved=True,  # Default to approve if no council
                vote_count={"approve": 0},
                confidence=0.0,
                summary="Insufficient models for council"
            )
        
        # Build system prompt based on task type
        system_prompt = self._get_system_prompt(task_type)
        full_prompt = self._build_prompt(prompt, context, task_type)
        
        # Collect votes in parallel
        votes = self._collect_votes(models, system_prompt, full_prompt)
        
        # Aggregate results
        return self._aggregate_votes(votes, task_type)
    
    def review_code(
        self,
        code: str,
        language: str = "python",
        focus: Optional[List[str]] = None
    ) -> ConsensusResult:
        """
        Specialized code review by council.
        
        Args:
            code: The code to review
            language: Programming language
            focus: Specific areas to focus on (security, performance, style)
        """
        focus_str = ", ".join(focus) if focus else "quality, correctness, style"
        
        prompt = f"""Review this {language} code, focusing on: {focus_str}

```{language}
{code}
```

Provide:
1. Rating (1-10)
2. Issues found
3. Suggestions for improvement
4. Security concerns (if any)"""

        return self.vote(prompt, task_type="review")
    
    def check_security(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> ConsensusResult:
        """
        Security check by council.
        
        Used before executing potentially dangerous operations.
        """
        prompt = f"""Security Review Required:

Operation: {operation}

Context:
{json.dumps(context, indent=2)}

Evaluate:
1. Is this operation safe?
2. What are the risks?
3. Should it be allowed?

Vote: APPROVE, REJECT, or CONDITIONAL"""

        return self.vote(prompt, task_type="security", context=context)
    
    def verify_output(
        self,
        task: str,
        output: str,
        expected: Optional[str] = None
    ) -> ConsensusResult:
        """
        Verify LLM output before using it.
        
        Useful for catching hallucinations and errors.
        """
        prompt = f"""Verify this LLM output:

Task: {task}

Output:
{output}
"""
        if expected:
            prompt += f"\nExpected format/content: {expected}"
        
        prompt += """

Check for:
1. Hallucinations (made-up facts, non-existent files/packages)
2. Logical errors
3. Completeness
4. Correctness

Vote: APPROVE if output is good, REJECT if problematic."""

        return self.vote(prompt, task_type="quality")
    
    def _select_models(self) -> List[str]:
        """Select models for this council session"""
        available = self.get_available_models()
        
        # Prefer configured models if available
        selected = []
        for model in self.config.models:
            if model in available and len(selected) < self.config.max_parallel:
                selected.append(model)
        
        # Fill with other available models if needed
        for model in available:
            if model not in selected and len(selected) < self.config.min_votes:
                selected.append(model)
        
        return selected[:self.config.max_parallel]
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get system prompt for task type"""
        prompts = {
            "review": """You are a code reviewer on a council. Your job is to:
1. Rate code quality (1-10)
2. Identify issues and bugs
3. Suggest improvements
4. Be critical but constructive

Always respond with valid JSON:
{
  "vote": "approve|reject|conditional",
  "confidence": 0.0-1.0,
  "rating": 1-10,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1"],
  "reasoning": "why you voted this way"
}""",
            
            "security": """You are a security reviewer on a council. Your job is to:
1. Identify security risks
2. Evaluate if operations are safe
3. Suggest safer alternatives
4. Be paranoid - when in doubt, reject

Always respond with valid JSON:
{
  "vote": "approve|reject|conditional",
  "confidence": 0.0-1.0,
  "issues": ["security concern"],
  "suggestions": ["safer alternative"],
  "reasoning": "security analysis"
}""",
            
            "quality": """You are a quality reviewer on a council. Your job is to:
1. Check for hallucinations (made-up facts)
2. Verify correctness
3. Ensure completeness
4. Be skeptical of claims

Always respond with valid JSON:
{
  "vote": "approve|reject|conditional",
  "confidence": 0.0-1.0,
  "issues": ["quality issue"],
  "suggestions": ["improvement"],
  "reasoning": "quality analysis"
}""",
            
            "general": """You are a reviewer on a council. Analyze the given content and vote.

Always respond with valid JSON:
{
  "vote": "approve|reject|conditional",
  "confidence": 0.0-1.0,
  "issues": [],
  "suggestions": [],
  "reasoning": "your analysis"
}"""
        }
        
        return prompts.get(task_type, prompts["general"])
    
    def _build_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]],
        task_type: str
    ) -> str:
        """Build the full prompt for models"""
        full_prompt = prompt
        
        if context:
            full_prompt += f"\n\nAdditional Context:\n{json.dumps(context, indent=2)}"
        
        return full_prompt
    
    def _collect_votes(
        self,
        models: List[str],
        system_prompt: str,
        prompt: str
    ) -> List[CouncilVote]:
        """Collect votes from all models in parallel"""
        import requests
        import time
        
        votes = []
        
        def query_model(model: str) -> Optional[CouncilVote]:
            start = time.time()
            try:
                response = requests.post(
                    f"{self.config.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 500
                        }
                    },
                    timeout=self.config.timeout_seconds
                )
                
                duration_ms = int((time.time() - start) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_vote(
                        model,
                        data.get("response", ""),
                        duration_ms
                    )
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
            
            return None
        
        # Submit all queries
        futures = {
            self._executor.submit(query_model, model): model
            for model in models
        }
        
        # Collect results
        for future in as_completed(futures, timeout=self.config.timeout_seconds + 5):
            try:
                vote = future.result()
                if vote:
                    votes.append(vote)
            except Exception as e:
                logger.warning(f"Vote collection error: {e}")
        
        return votes
    
    def _parse_vote(
        self,
        model: str,
        response: str,
        duration_ms: int
    ) -> CouncilVote:
        """Parse model response into a vote"""
        # Try to extract JSON
        try:
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Try parsing whole response
                data = json.loads(response)
            
            vote_str = data.get("vote", "abstain").lower()
            vote_map = {
                "approve": VoteType.APPROVE,
                "reject": VoteType.REJECT,
                "abstain": VoteType.ABSTAIN,
                "conditional": VoteType.CONDITIONAL,
                "yes": VoteType.APPROVE,
                "no": VoteType.REJECT,
            }
            
            return CouncilVote(
                model=model,
                vote=vote_map.get(vote_str, VoteType.ABSTAIN),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("suggestions", []),
                issues=data.get("issues", []),
                rating=data.get("rating"),
                response_time_ms=duration_ms
            )
            
        except (json.JSONDecodeError, ValueError):
            # Parse from text
            return self._parse_vote_from_text(model, response, duration_ms)
    
    def _parse_vote_from_text(
        self,
        model: str,
        text: str,
        duration_ms: int
    ) -> CouncilVote:
        """Parse vote from unstructured text"""
        text_lower = text.lower()
        
        # Determine vote from keywords
        if any(w in text_lower for w in ["reject", "not safe", "dangerous", "no"]):
            vote = VoteType.REJECT
        elif any(w in text_lower for w in ["conditional", "with changes", "if"]):
            vote = VoteType.CONDITIONAL
        elif any(w in text_lower for w in ["approve", "safe", "good", "yes"]):
            vote = VoteType.APPROVE
        else:
            vote = VoteType.ABSTAIN
        
        # Try to extract rating
        rating = None
        rating_match = re.search(r'(\d+)/10|rating:?\s*(\d+)', text_lower)
        if rating_match:
            rating = float(rating_match.group(1) or rating_match.group(2))
        
        return CouncilVote(
            model=model,
            vote=vote,
            confidence=0.5,  # Unknown confidence
            reasoning=text[:500],
            rating=rating,
            response_time_ms=duration_ms
        )
    
    def _aggregate_votes(
        self,
        votes: List[CouncilVote],
        task_type: str
    ) -> ConsensusResult:
        """Aggregate votes into consensus result"""
        if not votes:
            return ConsensusResult(
                approved=False,
                vote_count={},
                confidence=0.0,
                summary="No votes received"
            )
        
        # Count votes
        vote_count = {
            "approve": 0,
            "reject": 0,
            "abstain": 0,
            "conditional": 0
        }
        
        for vote in votes:
            vote_count[vote.vote.value] += 1
        
        # Calculate approval
        total_votes = len(votes)
        approve_count = vote_count["approve"] + vote_count["conditional"]
        reject_count = vote_count["reject"]
        
        if self.config.require_consensus:
            approved = reject_count == 0 and approve_count > 0
            consensus_type = "unanimous"
        else:
            approval_rate = approve_count / total_votes if total_votes > 0 else 0
            approved = approval_rate >= self.config.consensus_threshold
            consensus_type = "majority"
        
        # Aggregate confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        
        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []
        for vote in votes:
            all_issues.extend(vote.issues)
            all_suggestions.extend(vote.suggestions)
        
        # Deduplicate
        issues = list(set(all_issues))
        suggestions = list(set(all_suggestions))
        
        # Generate summary
        summary = self._generate_summary(votes, approved, task_type)
        
        return ConsensusResult(
            approved=approved,
            vote_count=vote_count,
            confidence=avg_confidence,
            votes=votes,
            consensus_type=consensus_type,
            summary=summary,
            issues=issues,
            suggestions=suggestions
        )
    
    def _generate_summary(
        self,
        votes: List[CouncilVote],
        approved: bool,
        task_type: str
    ) -> str:
        """Generate human-readable summary"""
        total = len(votes)
        approve = sum(1 for v in votes if v.vote in [VoteType.APPROVE, VoteType.CONDITIONAL])
        reject = sum(1 for v in votes if v.vote == VoteType.REJECT)
        
        status = "✅ APPROVED" if approved else "❌ REJECTED"
        
        # Average rating if available
        ratings = [v.rating for v in votes if v.rating is not None]
        rating_str = f", avg rating: {sum(ratings)/len(ratings):.1f}/10" if ratings else ""
        
        return f"{status} ({approve}/{total} approve, {reject}/{total} reject{rating_str})"
    
    def should_activate(self, confidence: float) -> bool:
        """Determine if council should be activated based on confidence"""
        if not self.config.only_on_uncertainty:
            return True
        return confidence < self.config.uncertainty_threshold
