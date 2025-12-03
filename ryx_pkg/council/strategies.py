"""
Ryx AI - Voting Strategies

Different strategies for aggregating council votes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .council import CouncilVote, VoteType, ConsensusResult


class VotingStrategy(ABC):
    """Base class for voting strategies"""
    
    @abstractmethod
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        """Aggregate votes into a result"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""
        pass


class MajorityVoting(VotingStrategy):
    """
    Simple majority voting.
    
    Approval if more than threshold % vote approve/conditional.
    """
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
    
    @property
    def name(self) -> str:
        return "majority"
    
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        if not votes:
            return self._empty_result()
        
        vote_count = self._count_votes(votes)
        total = len(votes)
        
        approve_count = vote_count["approve"] + vote_count["conditional"]
        approval_rate = approve_count / total
        
        approved = approval_rate > self.threshold
        avg_confidence = sum(v.confidence for v in votes) / total
        
        return ConsensusResult(
            approved=approved,
            vote_count=vote_count,
            confidence=avg_confidence,
            votes=votes,
            consensus_type=self.name,
            summary=f"Majority vote: {approve_count}/{total} approved",
            issues=self._collect_issues(votes),
            suggestions=self._collect_suggestions(votes)
        )
    
    def _count_votes(self, votes: List[CouncilVote]) -> Dict[str, int]:
        count = {"approve": 0, "reject": 0, "abstain": 0, "conditional": 0}
        for vote in votes:
            count[vote.vote.value] += 1
        return count
    
    def _collect_issues(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(issue for v in votes for issue in v.issues))
    
    def _collect_suggestions(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(s for v in votes for s in v.suggestions))
    
    def _empty_result(self) -> ConsensusResult:
        return ConsensusResult(
            approved=False,
            vote_count={},
            confidence=0.0,
            summary="No votes"
        )


class WeightedVoting(VotingStrategy):
    """
    Weighted voting based on model confidence and performance.
    
    Each vote is weighted by the model's confidence and optionally
    by historical accuracy.
    """
    
    def __init__(
        self,
        threshold: float = 0.5,
        model_weights: Optional[Dict[str, float]] = None
    ):
        self.threshold = threshold
        self.model_weights = model_weights or {}
    
    @property
    def name(self) -> str:
        return "weighted"
    
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        if not votes:
            return self._empty_result()
        
        # Calculate weighted scores
        approve_weight = 0.0
        reject_weight = 0.0
        total_weight = 0.0
        
        for vote in votes:
            # Base weight from confidence
            weight = vote.confidence
            
            # Apply model-specific weight if available
            model_weight = self.model_weights.get(vote.model, 1.0)
            weight *= model_weight
            
            total_weight += weight
            
            if vote.vote in [VoteType.APPROVE, VoteType.CONDITIONAL]:
                approve_weight += weight
            elif vote.vote == VoteType.REJECT:
                reject_weight += weight
        
        # Calculate approval
        if total_weight > 0:
            approval_rate = approve_weight / total_weight
        else:
            approval_rate = 0.0
        
        approved = approval_rate > self.threshold
        
        vote_count = {"approve": 0, "reject": 0, "abstain": 0, "conditional": 0}
        for vote in votes:
            vote_count[vote.vote.value] += 1
        
        return ConsensusResult(
            approved=approved,
            vote_count=vote_count,
            confidence=approval_rate,
            votes=votes,
            consensus_type=self.name,
            summary=f"Weighted vote: {approval_rate:.1%} approval",
            issues=self._collect_issues(votes),
            suggestions=self._collect_suggestions(votes)
        )
    
    def _collect_issues(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(issue for v in votes for issue in v.issues))
    
    def _collect_suggestions(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(s for v in votes for s in v.suggestions))
    
    def _empty_result(self) -> ConsensusResult:
        return ConsensusResult(
            approved=False,
            vote_count={},
            confidence=0.0,
            summary="No votes"
        )


class UnanimousVoting(VotingStrategy):
    """
    Unanimous voting - all must approve.
    
    Used for security-critical decisions where any dissent should block.
    """
    
    @property
    def name(self) -> str:
        return "unanimous"
    
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        if not votes:
            return self._empty_result()
        
        vote_count = {"approve": 0, "reject": 0, "abstain": 0, "conditional": 0}
        for vote in votes:
            vote_count[vote.vote.value] += 1
        
        # Reject if any reject vote
        has_reject = vote_count["reject"] > 0
        all_approve = vote_count["approve"] + vote_count["conditional"] == len(votes)
        
        approved = all_approve and not has_reject
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        
        return ConsensusResult(
            approved=approved,
            vote_count=vote_count,
            confidence=avg_confidence if approved else 0.0,
            votes=votes,
            consensus_type=self.name,
            summary="Unanimous" if approved else "Blocked by dissent",
            issues=self._collect_issues(votes),
            suggestions=self._collect_suggestions(votes)
        )
    
    def _collect_issues(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(issue for v in votes for issue in v.issues))
    
    def _collect_suggestions(self, votes: List[CouncilVote]) -> List[str]:
        return list(set(s for v in votes for s in v.suggestions))
    
    def _empty_result(self) -> ConsensusResult:
        return ConsensusResult(
            approved=False,
            vote_count={},
            confidence=0.0,
            summary="No votes"
        )


class QuorumVoting(VotingStrategy):
    """
    Quorum voting - requires minimum number of votes.
    
    Only considers result valid if enough models participated.
    """
    
    def __init__(self, min_quorum: int = 2, threshold: float = 0.5):
        self.min_quorum = min_quorum
        self.threshold = threshold
    
    @property
    def name(self) -> str:
        return "quorum"
    
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        if len(votes) < self.min_quorum:
            return ConsensusResult(
                approved=False,
                vote_count={},
                confidence=0.0,
                summary=f"Quorum not met ({len(votes)}/{self.min_quorum})"
            )
        
        # Use majority logic once quorum is met
        majority = MajorityVoting(self.threshold)
        result = majority.aggregate(votes)
        result.consensus_type = self.name
        return result


class VetoVoting(VotingStrategy):
    """
    Veto voting - specific models can veto.
    
    Used when certain expert models should have override power.
    """
    
    def __init__(
        self,
        veto_models: Optional[List[str]] = None,
        threshold: float = 0.5
    ):
        self.veto_models = veto_models or []
        self.threshold = threshold
    
    @property
    def name(self) -> str:
        return "veto"
    
    def aggregate(self, votes: List[CouncilVote]) -> ConsensusResult:
        if not votes:
            return self._empty_result()
        
        # Check for veto
        veto_vote = None
        for vote in votes:
            if vote.model in self.veto_models and vote.vote == VoteType.REJECT:
                veto_vote = vote
                break
        
        if veto_vote:
            return ConsensusResult(
                approved=False,
                vote_count=self._count_votes(votes),
                confidence=0.0,
                votes=votes,
                consensus_type=self.name,
                summary=f"Vetoed by {veto_vote.model}",
                issues=veto_vote.issues,
                suggestions=veto_vote.suggestions
            )
        
        # No veto - use majority
        majority = MajorityVoting(self.threshold)
        result = majority.aggregate(votes)
        result.consensus_type = self.name
        return result
    
    def _count_votes(self, votes: List[CouncilVote]) -> Dict[str, int]:
        count = {"approve": 0, "reject": 0, "abstain": 0, "conditional": 0}
        for vote in votes:
            count[vote.vote.value] += 1
        return count
    
    def _empty_result(self) -> ConsensusResult:
        return ConsensusResult(
            approved=False,
            vote_count={},
            confidence=0.0,
            summary="No votes"
        )
