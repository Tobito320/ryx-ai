"""
Test IntentParser Fix for Informational Find Queries

This module tests the heuristic that prefers 'locate' for informational 'find'
queries. The fix addresses the issue where queries like "where can I find the
open source license?" were incorrectly returning 'execute' due to 'open source'
triggering the execute action.

The heuristic checks if:
1. Query contains 'find' or 'where'
2. Query is question-like (ends with '?' or contains question words)
3. No explicit execute verbs are present (run, execute, launch, start, edit)

If all conditions are met, the action is set to 'locate'.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.intent_parser import IntentParser


class TestInformationalFindQueries:
    """Test the heuristic for informational 'find' queries."""

    def test_open_source_license_question(self):
        """
        Reproducing failing case: "where can I find the open source license?"
        
        This query should return 'locate' or 'chat', NOT 'execute'.
        The 'open' in 'open source' should not trigger execute action.
        """
        parser = IntentParser()
        intent = parser.parse("where can I find the open source license?")
        
        # Should be 'locate' due to 'find' and 'where' keywords in a question
        # Should NOT be 'execute' despite 'open' in 'open source'
        assert intent.action in ('locate', 'chat'), (
            f"Expected action 'locate' or 'chat', but got '{intent.action}'. "
            "The 'open' in 'open source' should not trigger execute action."
        )

    def test_find_with_question_mark(self):
        """Questions with 'find' and '?' should return 'locate'."""
        parser = IntentParser()
        intent = parser.parse("where can I find the documentation?")
        assert intent.action in ('locate', 'chat')

    def test_find_with_question_word(self):
        """Questions with 'find' and question words should return 'locate'."""
        parser = IntentParser()
        intent = parser.parse("how can I find the config file")
        assert intent.action in ('locate', 'chat')

    def test_where_with_question_mark(self):
        """Questions with 'where' and '?' should return 'locate'."""
        parser = IntentParser()
        intent = parser.parse("where is the license file?")
        assert intent.action in ('locate', 'chat')

    def test_find_with_explicit_edit_verb(self):
        """If explicit execute verb 'edit' is present, should return 'execute'."""
        parser = IntentParser()
        intent = parser.parse("where can I find the file to edit?")
        # 'edit' is an explicit execute verb, so execute should win
        assert intent.action == 'execute'

    def test_find_with_explicit_run_verb(self):
        """If explicit execute verb 'run' is present, should return 'execute'."""
        parser = IntentParser()
        intent = parser.parse("where can I find the script to run?")
        # 'run' is an explicit execute verb, so execute should win
        assert intent.action == 'execute'

    def test_simple_find_without_question(self):
        """Simple 'find' without question indicators should still work."""
        parser = IntentParser()
        intent = parser.parse("find config file")
        # Should return 'locate' due to 'find' keyword
        assert intent.action == 'locate'

    def test_non_question_with_open_keyword(self):
        """Non-question prompts with 'open' should return 'execute'."""
        parser = IntentParser()
        intent = parser.parse("open the config file")
        # Should return 'execute' because it's not a question
        assert intent.action == 'execute'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
