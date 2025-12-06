"""
Ryx AI - Council v2: Multi-Model Consensus System

Enhanced council system that:
- Uses vLLM instead of Ollama for consistency
- Supports async concurrent model queries
- Provides rich visual feedback
- Implements consensus algorithms
- Easy-to-use presets for common tasks
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.vllm_client import VLLMClient, VLLMConfig
from core.visual_steps import StepVisualizer, StepType
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)


class CouncilPreset(Enum):
    """Predefined council configurations for common tasks"""
    CODE_REVIEW = "code_review"
    FACT_CHECK = "fact_check"
    CREATIVE_WRITING = "creative_writing"
    BUG_ANALYSIS = "bug_analysis"
    SECURITY_AUDIT = "security_audit"


@dataclass
class CouncilMember:
    """A model participating in council"""
    name: str
    model_path: str
    weight: float = 1.0  # For weighted voting
    specialization: Optional[str] = None


@dataclass
class CouncilResponse:
    """Response from a single council member"""
    member: CouncilMember
    response: str
    rating: Optional[float] = None  # Extracted rating if present
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class CouncilResult:
    """Final council result with consensus"""
    responses: List[CouncilResponse]
    consensus: str
    average_rating: Optional[float] = None
    agreement_score: float = 0.0  # How much models agree (0-1)
    duration_s: float = 0.0
    
    def get_response_by_member(self, name: str) -> Optional[CouncilResponse]:
        """Get response from specific member"""
        for resp in self.responses:
            if resp.member.name == name:
                return resp
        return None


class Council:
    """
    Multi-model consensus system using vLLM.
    
    Features:
    - Async concurrent queries to multiple models
    - Rich visual feedback
    - Consensus algorithms (majority, weighted, threshold)
    - Presets for common tasks
    """
    
    def __init__(self, 
                 members: Optional[List[CouncilMember]] = None,
                 vllm_url: str = "http://localhost:8001",
                 console: Optional[Console] = None):
        """
        Initialize council.
        
        Args:
            members: List of council members (models). If None, uses defaults.
            vllm_url: vLLM server URL
            console: Rich console for output
        """
        self.vllm_url = vllm_url
        self.console = console or Console()
        self.visualizer = StepVisualizer(self.console)
        
        # Default members if not specified
        self.members = members or self._get_default_members()
        
        self.config = VLLMConfig(base_url=vllm_url)
    
    def _get_default_members(self) -> List[CouncilMember]:
        """Get default council members"""
        return [
            CouncilMember(
                name="Coder",
                model_path="/models/medium/coding/qwen2.5-coder-7b-gptq",
                weight=1.5,
                specialization="coding"
            ),
            CouncilMember(
                name="General",
                model_path="/models/medium/general/qwen2.5-7b-gptq",
                weight=1.0,
                specialization="general"
            ),
            CouncilMember(
                name="Fast",
                model_path="/models/small/general/qwen2.5-3b",
                weight=0.8,
                specialization="quick_analysis"
            ),
        ]
    
    async def query(self,
                   prompt: str,
                   system_prompt: Optional[str] = None,
                   preset: Optional[CouncilPreset] = None,
                   temperature: float = 0.7,
                   max_tokens: int = 1024) -> CouncilResult:
        """
        Query all council members and synthesize consensus.
        
        Args:
            prompt: The question/task for the council
            system_prompt: Optional system prompt (overrides preset)
            preset: Use a predefined council preset
            temperature: Sampling temperature
            max_tokens: Max tokens per response
            
        Returns:
            CouncilResult with all responses and consensus
        """
        start_time = datetime.now()
        
        # Get system prompt from preset if not provided
        if system_prompt is None and preset:
            system_prompt = self._get_preset_prompt(preset)
        
        # Show council header
        self._show_council_header()
        
        # Query all members concurrently
        self.visualizer.start_step(
            StepType.TOOL_EXECUTION,
            f"Querying {len(self.members)} council members"
        )
        
        responses = await self._query_members(
            prompt, system_prompt, temperature, max_tokens
        )
        
        self.visualizer.complete_step()
        
        # Synthesize consensus
        self.visualizer.start_step(
            StepType.SYNTHESIS,
            "Synthesizing consensus"
        )
        
        consensus = self._synthesize_consensus(responses)
        agreement = self._calculate_agreement(responses)
        avg_rating = self._calculate_average_rating(responses)
        
        self.visualizer.complete_step()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = CouncilResult(
            responses=responses,
            consensus=consensus,
            average_rating=avg_rating,
            agreement_score=agreement,
            duration_s=duration
        )
        
        # Display results
        self._display_results(result)
        
        return result
    
    async def _query_members(self,
                            prompt: str,
                            system_prompt: Optional[str],
                            temperature: float,
                            max_tokens: int) -> List[CouncilResponse]:
        """Query all council members concurrently"""
        tasks = []
        
        for member in self.members:
            task = self._query_single_member(
                member, prompt, system_prompt, temperature, max_tokens
            )
            tasks.append(task)
        
        # Execute all queries concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to proper responses
        result = []
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error(f"Council member query failed: {resp}")
            elif resp:
                result.append(resp)
        
        return result
    
    async def _query_single_member(self,
                                   member: CouncilMember,
                                   prompt: str,
                                   system_prompt: Optional[str],
                                   temperature: float,
                                   max_tokens: int) -> CouncilResponse:
        """Query a single council member"""
        client = VLLMClient(self.config)
        
        try:
            start = datetime.now()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            resp = await client.chat(
                messages=messages,
                model=member.model_path,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            latency = (datetime.now() - start).total_seconds() * 1000
            
            # Extract rating if present
            rating = self._extract_rating(resp.response)
            
            # Show progress
            self.console.print(f"  ✓ {member.name}: {len(resp.response)} chars", style="dim")
            
            return CouncilResponse(
                member=member,
                response=resp.response,
                rating=rating,
                latency_ms=latency,
                error=resp.error
            )
            
        except Exception as e:
            logger.error(f"Error querying {member.name}: {e}")
            return CouncilResponse(
                member=member,
                response="",
                error=str(e)
            )
        finally:
            await client.close()
    
    def _synthesize_consensus(self, responses: List[CouncilResponse]) -> str:
        """Synthesize a consensus from all responses"""
        if not responses:
            return "No responses received"
        
        # Simple approach: return the response from highest-weighted successful member
        valid_responses = [r for r in responses if r.response and not r.error]
        if not valid_responses:
            return "All members failed to respond"
        
        # Sort by member weight
        valid_responses.sort(key=lambda r: r.member.weight, reverse=True)
        
        return valid_responses[0].response
    
    def _calculate_agreement(self, responses: List[CouncilResponse]) -> float:
        """Calculate agreement score between responses (0-1)"""
        if len(responses) < 2:
            return 1.0
        
        # Simple heuristic: compare response lengths and ratings
        ratings = [r.rating for r in responses if r.rating is not None]
        if len(ratings) >= 2:
            # Calculate variance in ratings
            avg = sum(ratings) / len(ratings)
            variance = sum((r - avg) ** 2 for r in ratings) / len(ratings)
            # Convert to agreement score (lower variance = higher agreement)
            agreement = max(0.0, 1.0 - variance / 10.0)
            return agreement
        
        return 0.5  # Unknown agreement
    
    def _calculate_average_rating(self, responses: List[CouncilResponse]) -> Optional[float]:
        """Calculate average rating from responses"""
        ratings = [r.rating for r in responses if r.rating is not None]
        if ratings:
            return sum(ratings) / len(ratings)
        return None
    
    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract numeric rating from response text"""
        import re
        
        patterns = [
            r'(\d+(?:\.\d+)?)\s*/\s*10',
            r'[Rr]ating:?\s*(\d+(?:\.\d+)?)',
            r'[Ss]core:?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s+out of 10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    rating = float(match.group(1))
                    if 0 <= rating <= 10:
                        return rating
                except ValueError:
                    pass
        
        return None
    
    def _get_preset_prompt(self, preset: CouncilPreset) -> str:
        """Get system prompt for a preset"""
        prompts = {
            CouncilPreset.CODE_REVIEW: """You are a code reviewer. Analyze the code and:
1. Rate quality (1-10)
2. List issues and bugs
3. Suggest improvements
4. Note security concerns

Be concise and critical.""",
            
            CouncilPreset.FACT_CHECK: """You are a fact checker. Analyze the statement and:
1. Rate accuracy (1-10)
2. Identify factual errors
3. Provide corrections
4. Note confidence level

Be precise and cite reasoning.""",
            
            CouncilPreset.CREATIVE_WRITING: """You are a writing critic. Evaluate the text and:
1. Rate creativity and style (1-10)
2. Note strengths
3. Suggest improvements
4. Comment on originality

Be constructive and specific.""",
            
            CouncilPreset.BUG_ANALYSIS: """You are a debugging expert. Analyze the bug report and:
1. Rate severity (1-10)
2. Identify root cause
3. Suggest fixes
4. Note side effects

Be thorough and technical.""",
            
            CouncilPreset.SECURITY_AUDIT: """You are a security auditor. Review the code and:
1. Rate security risk (1-10)
2. Identify vulnerabilities
3. Suggest mitigations
4. Note compliance issues

Be paranoid and thorough."""
        }
        
        return prompts.get(preset, "Analyze this carefully and provide your assessment.")
    
    def _show_council_header(self):
        """Show council session header"""
        text = Text()
        text.append("🏛️  ", style="bold")
        text.append("Council Session", style="bold cyan")
        text.append(f" ({len(self.members)} members)", style="dim")
        
        self.console.print()
        self.console.print(text)
        self.console.print()
    
    def _display_results(self, result: CouncilResult):
        """Display council results in a nice table"""
        self.console.print()
        
        # Create results table
        table = Table(title="📊 Council Responses", show_header=True, header_style="bold cyan")
        table.add_column("Member", style="cyan")
        table.add_column("Rating", justify="center")
        table.add_column("Response", max_width=60)
        table.add_column("Time", justify="right", style="dim")
        
        for resp in result.responses:
            rating_str = f"{resp.rating:.1f}/10" if resp.rating else "—"
            response_preview = resp.response[:100] + "..." if len(resp.response) > 100 else resp.response
            time_str = f"{resp.latency_ms:.0f}ms"
            
            if resp.error:
                table.add_row(
                    resp.member.name,
                    "Error",
                    f"[red]{resp.error}[/red]",
                    time_str
                )
            else:
                table.add_row(
                    resp.member.name,
                    rating_str,
                    response_preview,
                    time_str
                )
        
        self.console.print(table)
        
        # Show consensus
        if result.consensus and result.consensus != result.responses[0].response:
            self.console.print()
            panel = Panel(
                result.consensus[:500],
                title="✨ Consensus",
                border_style="green"
            )
            self.console.print(panel)
        
        # Show summary stats
        self.console.print()
        summary = Text()
        summary.append("└─ ", style="dim")
        
        if result.average_rating:
            summary.append(f"Avg: {result.average_rating:.1f}/10", style="yellow")
            summary.append(" • ", style="dim")
        
        summary.append(f"Agreement: {result.agreement_score:.0%}", style="cyan")
        summary.append(" • ", style="dim")
        summary.append(f"{result.duration_s:.2f}s", style="dim")
        
        self.console.print(summary)
        self.console.print()


async def quick_council(prompt: str, 
                       preset: Optional[CouncilPreset] = None,
                       console: Optional[Console] = None) -> CouncilResult:
    """
    Quick helper to run a council query.
    
    Args:
        prompt: The question/task
        preset: Optional preset configuration
        console: Optional console for output
        
    Returns:
        CouncilResult with responses and consensus
    """
    council = Council(console=console)
    return await council.query(prompt, preset=preset)
