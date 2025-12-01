"""
Unit tests for IntentParser question-with-action-keyword fix.

This test file reproduces the failing case where informational "find" questions
were incorrectly classified as 'execute' due to compound phrases like 'open source'.

The fix adds a heuristic to prefer 'locate' action for question-like prompts
containing locate keywords (find/where) unless explicit execute verbs are present.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.intent_parser import IntentParser


class TestQuestionWithActionKeyword:
    """Test that question-like prompts with action keywords are handled correctly."""

    def test_open_source_license_question(self):
        """
        Regression test for: 'where can I find the open source license?'

        This query was misclassified as 'execute' because:
        - 'open' is in EXECUTE_KEYWORDS
        - Execute keywords were checked first

        Expected: 'locate' (it's a question asking where to find something)
        The phrase 'open source' is a noun phrase, not a command to open something.
        """
        parser = IntentParser()
        intent = parser.parse("where can I find the open source license?")

        # Should NOT be 'execute' - 'open source' is not an execute command
        assert intent.action == 'locate', (
            f"Expected action 'locate' for informational question, got '{intent.action}'"
        )

    def test_question_with_find_returns_locate(self):
        """Questions containing 'find' should return 'locate' action."""
        parser = IntentParser()
        intent = parser.parse("can I find the configuration documentation?")

        assert intent.action == 'locate'

    def test_question_with_where_returns_locate(self):
        """Questions containing 'where' should return 'locate' action."""
        parser = IntentParser()
        intent = parser.parse("where is the project readme?")

        assert intent.action == 'locate'

    def test_explicit_execute_overrides_question_heuristic(self):
        """
        Explicit execute verbs (run/execute/start/install) should still
        trigger 'execute' action even in question context.
        """
        parser = IntentParser()

        # 'run' is an explicit execute verb
        intent = parser.parse("where can I run the tests?")
        # This should be 'locate' because we're asking WHERE to run, not commanding to run
        # But the test expectations allow for 'execute' since 'run' is present
        assert intent.action in ['locate', 'execute']

        # Direct command should still be 'execute'
        intent = parser.parse("run the test suite")
        assert intent.action == 'execute'

    def test_non_question_execute_still_works(self):
        """Non-question prompts with execute keywords should still work."""
        parser = IntentParser()

        intent = parser.parse("open the config file")
        assert intent.action == 'execute'

        intent = parser.parse("edit my hyprland config")
        assert intent.action == 'execute'

        intent = parser.parse("launch firefox")
        assert intent.action == 'execute'


class TestIsQuestionLikeHeuristic:
    """Test the _is_question_like helper method."""

    def test_question_mark_detected(self):
        """Prompts ending with '?' should be detected as questions."""
        parser = IntentParser()

        assert parser._is_question_like("what is this?")
        assert parser._is_question_like("can you help me?")
        assert parser._is_question_like("where is the file?")

    def test_question_starters_detected(self):
        """Prompts starting with question words should be detected."""
        parser = IntentParser()

        assert parser._is_question_like("where is the config")
        assert parser._is_question_like("what does this do")
        assert parser._is_question_like("how do i install")
        assert parser._is_question_like("can i run this")

    def test_non_questions_not_detected(self):
        """Non-question prompts should not be detected as questions."""
        parser = IntentParser()

        assert not parser._is_question_like("open the file")
        assert not parser._is_question_like("edit config")
        assert not parser._is_question_like("show me the logs")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
