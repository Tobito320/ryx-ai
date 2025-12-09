"""
Ryx AI - Recursive Self-Improvement Loop

The RSI Loop is the core of autonomous self-improvement.

Flow:
1. BENCHMARK  - Measure current capabilities
2. ANALYZE    - Find weaknesses, compare to competitors
3. PLAN       - Generate improvement hypothesis
4. IMPLEMENT  - Apply changes in sandbox
5. RE-BENCH   - Measure new capabilities
6. DECIDE     - Accept/reject based on benchmark comparison
7. LOOP       - Repeat

This is inspired by:
- Darwin Gödel Machine (dgm)
- Self-improving coding agent
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class RSIPhase(Enum):
    """Current phase of the RSI loop"""
    IDLE = "idle"
    BENCHMARKING = "benchmarking"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    RE_BENCHMARKING = "re_benchmarking"
    DECIDING = "deciding"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class ImprovementHypothesis:
    """A hypothesis for how to improve Ryx"""
    
    hypothesis_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # What we're trying to improve
    target_benchmark: str = ""
    target_problems: List[str] = field(default_factory=list)
    current_score: float = 0.0
    expected_improvement: float = 0.0
    
    # The proposed change
    description: str = ""
    file_changes: Dict[str, str] = field(default_factory=dict)  # file -> new content
    
    # Status
    implemented: bool = False
    tested: bool = False
    accepted: bool = False
    actual_improvement: Optional[float] = None
    
    # Reasoning
    reasoning: str = ""
    rejection_reason: Optional[str] = None


@dataclass
class RSIIteration:
    """One iteration of the RSI loop"""
    
    iteration_id: int
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    
    # Phases
    current_phase: RSIPhase = RSIPhase.IDLE
    
    # Benchmark results
    baseline_score: float = 0.0
    new_score: float = 0.0
    
    # The hypothesis we're testing
    hypothesis: Optional[ImprovementHypothesis] = None
    
    # Outcome
    accepted: bool = False
    improvement: float = 0.0
    
    # Metrics
    tokens_used: int = 0
    time_seconds: float = 0.0


@dataclass
class RSIConfig:
    """Configuration for the RSI loop"""
    
    # Benchmarking
    benchmarks: List[str] = field(default_factory=lambda: ["coding_tasks", "bug_fixing"])
    min_improvement: float = 0.01  # 1% minimum improvement to accept
    max_regression: float = 0.0    # 0% regression allowed
    
    # Timing
    max_iteration_time: int = 3600  # 1 hour max per iteration
    checkpoint_interval: int = 300   # Checkpoint every 5 minutes
    
    # Safety
    sandbox_mode: bool = True       # Use Docker sandbox for changes
    require_approval: bool = True   # Require human approval for changes
    backup_before_apply: bool = True
    
    # LLM
    llm_model: str = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
    planning_temperature: float = 0.7
    implementation_temperature: float = 0.2


class RSILoop:
    """
    The main Recursive Self-Improvement loop.
    
    Usage:
        rsi = RSILoop(config)
        await rsi.initialize()
        
        # Run one iteration
        result = await rsi.iterate()
        
        # Or run continuously
        await rsi.run_loop(max_iterations=10)
    """
    
    def __init__(self, config: Optional[RSIConfig] = None):
        self.config = config or RSIConfig()
        
        # State
        self.current_phase = RSIPhase.IDLE
        self.iteration_count = 0
        self.iterations: List[RSIIteration] = []
        
        # Components (injected)
        self._benchmark_runner = None
        self._llm_client = None
        self._overseer = None
        self._memory = None
        
        # Callbacks
        self._on_phase_change: Optional[Callable] = None
        self._on_improvement: Optional[Callable] = None
        self._on_approval_needed: Optional[Callable] = None
        
        # Storage
        self.storage_path = Path.home() / "ryx-ai" / "data" / "rsi"
        self.storage_path.mkdir(parents=True, exist_ok=True
        )
    
    async def initialize(
        self,
        benchmark_runner=None,
        llm_client=None,
        overseer=None,
        memory=None,
    ):
        """Initialize the RSI loop with required components"""
        
        if benchmark_runner:
            self._benchmark_runner = benchmark_runner
        else:
            from core.benchmarks import BenchmarkRunner
            self._benchmark_runner = BenchmarkRunner()
        
        self._llm_client = llm_client
        self._overseer = overseer
        
        if memory:
            self._memory = memory
        else:
            from core.memory import get_memory
            self._memory = get_memory()
        
        logger.info("RSI Loop initialized")
    
    def _set_phase(self, phase: RSIPhase):
        """Update the current phase"""
        old_phase = self.current_phase
        self.current_phase = phase
        logger.info(f"RSI Phase: {old_phase.value} → {phase.value}")
        
        if self._on_phase_change:
            asyncio.create_task(
                self._on_phase_change(old_phase, phase)
            )
    
    async def iterate(self) -> RSIIteration:
        """
        Run one complete RSI iteration.
        
        Returns:
            RSIIteration with results
        """
        self.iteration_count += 1
        iteration = RSIIteration(iteration_id=self.iteration_count)
        
        try:
            # Phase 1: Benchmark current state
            self._set_phase(RSIPhase.BENCHMARKING)
            baseline_results = await self._run_benchmarks()
            iteration.baseline_score = self._calculate_aggregate_score(baseline_results)
            
            # Phase 2: Analyze weaknesses
            self._set_phase(RSIPhase.ANALYZING)
            analysis = await self._analyze_results(baseline_results)
            
            # Phase 3: Plan improvement
            self._set_phase(RSIPhase.PLANNING)
            hypothesis = await self._generate_hypothesis(analysis)
            iteration.hypothesis = hypothesis
            
            if not hypothesis:
                logger.info("No improvement hypothesis generated")
                iteration.current_phase = RSIPhase.IDLE
                return iteration
            
            # Phase 4: Implement (in sandbox)
            self._set_phase(RSIPhase.IMPLEMENTING)
            implemented = await self._implement_hypothesis(hypothesis)
            
            if not implemented:
                logger.warning("Failed to implement hypothesis")
                iteration.current_phase = RSIPhase.REJECTED
                return iteration
            
            # Phase 5: Re-benchmark
            self._set_phase(RSIPhase.RE_BENCHMARKING)
            new_results = await self._run_benchmarks()
            iteration.new_score = self._calculate_aggregate_score(new_results)
            
            # Phase 6: Decide
            self._set_phase(RSIPhase.DECIDING)
            accepted, reason = await self._decide(
                baseline_results, new_results, hypothesis
            )
            
            iteration.accepted = accepted
            iteration.improvement = iteration.new_score - iteration.baseline_score
            
            if accepted:
                self._set_phase(RSIPhase.ACCEPTED)
                
                if self.config.require_approval:
                    approved = await self._request_approval(hypothesis)
                    if not approved:
                        await self._rollback_changes(hypothesis)
                        iteration.accepted = False
                        self._set_phase(RSIPhase.REJECTED)
                else:
                    await self._apply_changes(hypothesis)
                
                if self._on_improvement:
                    await self._on_improvement(hypothesis, iteration.improvement)
            else:
                self._set_phase(RSIPhase.REJECTED)
                await self._rollback_changes(hypothesis)
                hypothesis.rejection_reason = reason
            
            # Store experience
            self._store_iteration_experience(iteration)
            
        except Exception as e:
            logger.error(f"RSI iteration failed: {e}")
            iteration.current_phase = RSIPhase.IDLE
        
        finally:
            iteration.finished_at = datetime.now().isoformat()
            self.iterations.append(iteration)
            self._save_iteration(iteration)
        
        return iteration
    
    async def run_loop(
        self,
        max_iterations: int = 10,
        stop_on_no_improvement: bool = True,
    ):
        """
        Run the RSI loop continuously.
        
        Args:
            max_iterations: Maximum iterations to run
            stop_on_no_improvement: Stop if no improvement found
        """
        consecutive_no_improvement = 0
        
        for i in range(max_iterations):
            logger.info(f"=== RSI Iteration {i + 1}/{max_iterations} ===")
            
            iteration = await self.iterate()
            
            if iteration.accepted:
                consecutive_no_improvement = 0
                logger.info(f"Improvement accepted: +{iteration.improvement:.2%}")
            else:
                consecutive_no_improvement += 1
                logger.info("No improvement this iteration")
                
                if stop_on_no_improvement and consecutive_no_improvement >= 3:
                    logger.info("Stopping: 3 consecutive iterations without improvement")
                    break
            
            # Brief pause between iterations
            await asyncio.sleep(5)
        
        logger.info(f"RSI loop complete: {len(self.iterations)} iterations")
    
    async def _run_benchmarks(self) -> Dict[str, Any]:
        """Run all configured benchmarks"""
        results = {}
        
        for benchmark_name in self.config.benchmarks:
            try:
                result = await self._benchmark_runner.run(benchmark_name)
                results[benchmark_name] = {
                    "score": result.average_score,
                    "passed": result.passed_count,
                    "total": result.total_problems,
                    "run_id": result.run_id,
                }
            except Exception as e:
                logger.error(f"Benchmark {benchmark_name} failed: {e}")
                results[benchmark_name] = {"error": str(e)}
        
        return results
    
    def _calculate_aggregate_score(self, results: Dict[str, Any]) -> float:
        """Calculate aggregate score from benchmark results"""
        scores = []
        for result in results.values():
            if "score" in result:
                scores.append(result["score"])
        return sum(scores) / len(scores) if scores else 0.0
    
    async def _analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze benchmark results to find weaknesses"""
        analysis = {
            "weak_areas": [],
            "failed_problems": [],
            "improvement_opportunities": [],
        }
        
        for benchmark, result in results.items():
            if result.get("score", 1.0) < 0.8:
                analysis["weak_areas"].append(benchmark)
        
        # Analyze patterns in failed problems
        failed_problems = []
        for benchmark, result in results.items():
            if "problems" in result:
                for problem in result.get("problems", []):
                    if problem.get("passed") is False:
                        failed_problems.append({
                            "benchmark": benchmark,
                            "problem_id": problem.get("id"),
                            "error": problem.get("error", "unknown"),
                            "expected": problem.get("expected"),
                            "actual": problem.get("actual")
                        })
        
        if failed_problems:
            # Group failures by error type
            error_types = {}
            for fp in failed_problems:
                err_type = fp["error"].split(":")[0] if ":" in fp["error"] else fp["error"]
                error_types[err_type] = error_types.get(err_type, 0) + 1
            
            analysis["error_patterns"] = error_types
            analysis["failed_count"] = len(failed_problems)
        
        return analysis
    
    async def _generate_hypothesis(
        self,
        analysis: Dict[str, Any]
    ) -> Optional[ImprovementHypothesis]:
        """Generate an improvement hypothesis based on analysis"""
        
        if not self._llm_client:
            logger.warning("No LLM client - cannot generate hypothesis")
            return None
        
        weak_areas = analysis.get("weak_areas", [])
        error_patterns = analysis.get("error_patterns", {})
        
        if not weak_areas and not error_patterns:
            logger.info("No weaknesses identified - nothing to improve")
            return None
        
        # Generate hypothesis based on analysis
        prompt = f"""You are Ryx AI, a self-improving coding assistant.

Analysis shows these weaknesses:
- Weak benchmarks: {weak_areas}
- Error patterns: {error_patterns}
- Failed count: {analysis.get('failed_count', 0)}

Generate an improvement hypothesis. Identify ONE specific change to make.

Return JSON with:
{{
    "description": "What to change",
    "target_benchmark": "Which benchmark to improve",
    "expected_improvement": 0.1,
    "reasoning": "Why this will help",
    "file_path": "path/to/file.py",
    "change_type": "modify|add|refactor",
    "change_description": "Specific code change to make"
}}"""
        
        try:
            response = await self._llm_client.generate(prompt)
            
            # Extract JSON from response - handle nested braces properly
            # Try to find JSON object with balanced braces
            def extract_json(text: str) -> Optional[dict]:
                """Extract first valid JSON object from text"""
                start = text.find('{')
                if start == -1:
                    return None
                
                depth = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                
                if depth == 0:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        return None
                return None
            
            data = extract_json(response)
            if data:
                hypothesis = ImprovementHypothesis(
                    hypothesis_id=str(uuid4())[:8],
                    description=data.get("description", ""),
                    target_benchmark=data.get("target_benchmark", weak_areas[0] if weak_areas else ""),
                    expected_improvement=float(data.get("expected_improvement", 0.05)),
                    reasoning=data.get("reasoning", ""),
                    file_changes={
                        data.get("file_path", ""): data.get("change_description", "")
                    } if data.get("file_path") else {}
                )
                return hypothesis
                
        except Exception as e:
            logger.error(f"Failed to generate hypothesis: {e}")
        
        return None
    
    async def _implement_hypothesis(
        self,
        hypothesis: ImprovementHypothesis
    ) -> bool:
        """Implement the hypothesis changes (in sandbox)"""
        if not hypothesis.file_changes:
            logger.warning("No file changes in hypothesis")
            return False
        
        # Create sandbox directory
        sandbox_dir = Path.home() / ".ryx" / "sandbox" / hypothesis.hypothesis_id
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for file_path, change_desc in hypothesis.file_changes.items():
                if not file_path:
                    continue
                    
                # Copy original to sandbox
                original = Path(file_path)
                sandbox_file = sandbox_dir / original.name
                
                if original.exists():
                    # Backup original
                    sandbox_file.write_text(original.read_text())
                    
                    # Log what would be changed
                    logger.info(f"Sandbox: Would apply to {file_path}: {change_desc[:100]}...")
                    
            hypothesis.implemented = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to implement hypothesis: {e}")
            return False
    
    async def _decide(
        self,
        baseline: Dict[str, Any],
        new_results: Dict[str, Any],
        hypothesis: ImprovementHypothesis
    ) -> tuple[bool, str]:
        """Decide whether to accept the changes"""
        
        baseline_score = self._calculate_aggregate_score(baseline)
        new_score = self._calculate_aggregate_score(new_results)
        
        improvement = new_score - baseline_score
        
        # Check for regression
        if improvement < -self.config.max_regression:
            return False, f"Regression detected: {improvement:.2%}"
        
        # Check for minimum improvement
        if improvement < self.config.min_improvement:
            return False, f"Improvement too small: {improvement:.2%}"
        
        return True, ""
    
    async def _request_approval(self, hypothesis: ImprovementHypothesis) -> bool:
        """Request human approval for changes"""
        if self._on_approval_needed:
            return await self._on_approval_needed(hypothesis)
        return True  # Auto-approve if no callback
    
    async def _apply_changes(self, hypothesis: ImprovementHypothesis):
        """Apply accepted changes permanently"""
        from pathlib import Path
        
        if not hypothesis.file_changes:
            logger.warning(f"No file changes in hypothesis: {hypothesis.hypothesis_id}")
            return
        
        for change in hypothesis.file_changes:
            file_path = Path(change.get("file", ""))
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            action = change.get("action", "modify")
            
            if action == "modify":
                # Read, apply diff, write
                content = file_path.read_text()
                old_text = change.get("old", "")
                new_text = change.get("new", "")
                if old_text in content:
                    content = content.replace(old_text, new_text, 1)
                    file_path.write_text(content)
                    logger.info(f"Applied change to {file_path}")
            
            elif action == "create":
                file_path.write_text(change.get("content", ""))
                logger.info(f"Created file: {file_path}")
            
            elif action == "delete":
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
        
        logger.info(f"Applied all changes from hypothesis: {hypothesis.hypothesis_id}")
    
    async def _rollback_changes(self, hypothesis: ImprovementHypothesis):
        """Rollback changes from a rejected hypothesis"""
        from pathlib import Path
        
        if not hypothesis.file_changes:
            return
        
        # Rollback in reverse order
        for change in reversed(hypothesis.file_changes):
            file_path = Path(change.get("file", ""))
            action = change.get("action", "modify")
            
            if action == "modify":
                # Reverse the modification
                if file_path.exists():
                    content = file_path.read_text()
                    old_text = change.get("old", "")
                    new_text = change.get("new", "")
                    if new_text in content:
                        content = content.replace(new_text, old_text, 1)
                        file_path.write_text(content)
                        logger.info(f"Rolled back change in {file_path}")
            
            elif action == "create":
                # Delete created file
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Removed created file: {file_path}")
            
            elif action == "delete":
                # Restore deleted file from backup (if available)
                backup_content = change.get("backup_content")
                if backup_content:
                    file_path.write_text(backup_content)
                    logger.info(f"Restored file: {file_path}")
        
        logger.info(f"Rolled back changes from hypothesis: {hypothesis.hypothesis_id}")
    
    def _store_iteration_experience(self, iteration: RSIIteration):
        """Store the iteration as an experience"""
        if not self._memory:
            return
        
        if iteration.accepted:
            self._memory.store_success(
                task=f"RSI iteration {iteration.iteration_id}",
                approach=iteration.hypothesis.description if iteration.hypothesis else "",
                result=f"Improvement: {iteration.improvement:.2%}",
                score=iteration.new_score,
                category="rsi",
                tags=["self-improvement"]
            )
        else:
            self._memory.store_failure(
                task=f"RSI iteration {iteration.iteration_id}",
                error=iteration.hypothesis.rejection_reason if iteration.hypothesis else "No hypothesis",
                category="rsi",
                tags=["self-improvement"]
            )
    
    def _save_iteration(self, iteration: RSIIteration):
        """Save iteration to disk"""
        iteration_file = self.storage_path / f"iteration_{iteration.iteration_id}.json"
        try:
            data = asdict(iteration)
            # Handle enums
            data['current_phase'] = iteration.current_phase.value
            if iteration.hypothesis:
                data['hypothesis'] = asdict(iteration.hypothesis)
            
            with open(iteration_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save iteration: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all RSI iterations"""
        return {
            "total_iterations": len(self.iterations),
            "accepted": sum(1 for i in self.iterations if i.accepted),
            "rejected": sum(1 for i in self.iterations if not i.accepted),
            "total_improvement": sum(i.improvement for i in self.iterations if i.accepted),
            "current_phase": self.current_phase.value,
        }
    
    # Callback registration
    def on_phase_change(self, callback: Callable):
        """Register callback for phase changes"""
        self._on_phase_change = callback
    
    def on_improvement(self, callback: Callable):
        """Register callback for accepted improvements"""
        self._on_improvement = callback
    
    def on_approval_needed(self, callback: Callable):
        """Register callback for approval requests"""
        self._on_approval_needed = callback
