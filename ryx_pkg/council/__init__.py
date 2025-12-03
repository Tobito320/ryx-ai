"""
Ryx AI - LLM Council System

Multi-model consensus for critical decisions.
Inspired by patterns from Claude Code and Aider.
"""

from .council import LLMCouncil, CouncilConfig, CouncilVote, ConsensusResult
from .strategies import VotingStrategy, MajorityVoting, WeightedVoting, UnanimousVoting

__all__ = [
    'LLMCouncil',
    'CouncilConfig',
    'CouncilVote',
    'ConsensusResult',
    'VotingStrategy',
    'MajorityVoting',
    'WeightedVoting',
    'UnanimousVoting',
]
